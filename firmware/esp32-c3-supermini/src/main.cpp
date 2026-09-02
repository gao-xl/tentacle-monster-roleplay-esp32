/**
 * @file main.cpp
 * @brief OpenHaptic-Roleplay Universal Controller Firmware for ESP32-C3 SuperMini
 * 
 * Supports:
 * - Native USB-CDC / UART Serial command parser
 * - 4-channel Hardware LEDC PWM outputs (GPIO 0, 1, 2, 3)
 * - Safe Hardware Watchdog (2000ms auto-failsafe shutoff)
 * - Decay pulse (HIT), continuous level (SET), dynamic oscillation (WAVE), and emergency stop (STOP)
 * - Optional I2C IMU Gyroscope / Accelerometer (MPU6050 / QMI8658 on SDA=GPIO4, SCL=GPIO5)
 * - Onboard LED (GPIO 8) status indication
 */

#include <Arduino.h>
#include <Wire.h>
#include <math.h>

// Pin Definitions for ESP32-C3 SuperMini
#define PIN_LED         8    // Onboard Blue/Green LED (Active LOW on SuperMini)
#define NUM_CHANNELS    4

// Default PWM Output Pins on SuperMini header
const uint8_t CH_PINS[NUM_CHANNELS] = {0, 1, 2, 3};

// Optional I2C IMU Pins
#define PIN_I2C_SDA     4
#define PIN_I2C_SCL     5
#define MPU6050_ADDR    0x68

static bool imu_available = false;

// LEDC PWM Configuration
#define PWM_FREQ        1000 // 1 kHz PWM frequency
#define PWM_RESOLUTION  8    // 8-bit resolution (0-255)

// Safety Watchdog
#define WATCHDOG_TIMEOUT_MS 2000
static uint32_t last_cmd_time = 0;
static bool watchdog_triggered = false;

// Channel States
struct ChannelState {
    uint8_t target_level;      // 0 - 100%
    float current_level;      // 0.0 - 100.0%
    
    // HIT (Decay) mode
    bool in_hit_mode;
    float decay_rate_per_ms;
    
    // WAVE mode
    bool in_wave_mode;
    float wave_freq;
    uint8_t wave_min;
    uint8_t wave_max;
    uint32_t wave_start_time;
};

static ChannelState channels[NUM_CHANNELS];

// Prototypes
void apply_channel_pwm(uint8_t ch, uint8_t level_percent);
void process_command(String cmd);
void emergency_stop();
void init_imu();
void read_and_report_imu();

void setup() {
    Serial.begin(115200);
    
    pinMode(PIN_LED, OUTPUT);
    digitalWrite(PIN_LED, HIGH);

    // Initialize PWM Channels
    for (uint8_t i = 0; i < NUM_CHANNELS; i++) {
        ledcAttach(CH_PINS[i], PWM_FREQ, PWM_RESOLUTION);
        channels[i].target_level = 0;
        channels[i].current_level = 0.0f;
        channels[i].in_hit_mode = false;
        channels[i].in_wave_mode = false;
        apply_channel_pwm(i, 0);
    }

    // Try initialize I2C IMU
    init_imu();

    last_cmd_time = millis();
    
    // Ready blink
    for (int k = 0; k < 3; k++) {
        digitalWrite(PIN_LED, LOW);
        delay(80);
        digitalWrite(PIN_LED, HIGH);
        delay(80);
    }

    Serial.println("[BOOT] OpenHaptic ESP32-C3 SuperMini Controller Ready.");
    if (imu_available) {
        Serial.println("[BOOT] I2C IMU Gyroscope detected on GPIO 4/5.");
    }
}

void init_imu() {
    Wire.begin(PIN_I2C_SDA, PIN_I2C_SCL);
    Wire.beginTransmission(MPU6050_ADDR);
    if (Wire.endTransmission() == 0) {
        // Wake up MPU6050
        Wire.beginTransmission(MPU6050_ADDR);
        Wire.write(0x6B); // PWR_MGMT_1
        Wire.write(0);    // Wake up
        Wire.endTransmission(true);
        imu_available = true;
    } else {
        imu_available = false;
    }
}

void loop() {
    uint32_t now = millis();

    // 1. Read Serial Commands
    while (Serial.available() > 0) {
        String line = Serial.readStringUntil('\n');
        line.trim();
        if (line.length() > 0) {
            process_command(line);
            last_cmd_time = now;
            watchdog_triggered = false;
        }
    }

    // 2. Safety Watchdog Check
    if (!watchdog_triggered && (now - last_cmd_time > WATCHDOG_TIMEOUT_MS)) {
        watchdog_triggered = true;
        emergency_stop();
        Serial.println("[WARN] Watchdog timeout: Auto-shutdown all outputs for safety.");
    }

    // 3. Update Channel Dynamics (HIT decay & WAVE calculation)
    static uint32_t last_tick = 0;
    if (now - last_tick >= 10) { // 100 Hz
        float dt = (now - last_tick);
        last_tick = now;

        for (uint8_t i = 0; i < NUM_CHANNELS; i++) {
            if (channels[i].in_hit_mode) {
                channels[i].current_level -= channels[i].decay_rate_per_ms * dt;
                if (channels[i].current_level <= 0.0f) {
                    channels[i].current_level = 0.0f;
                    channels[i].in_hit_mode = false;
                }
                apply_channel_pwm(i, (uint8_t)channels[i].current_level);
            } else if (channels[i].in_wave_mode) {
                float elapsed_sec = (now - channels[i].wave_start_time) / 1000.0f;
                float sin_val = (sinf(2.0f * M_PI * channels[i].wave_freq * elapsed_sec) + 1.0f) / 2.0f;
                float range = channels[i].wave_max - channels[i].wave_min;
                channels[i].current_level = channels[i].wave_min + (range * sin_val);
                apply_channel_pwm(i, (uint8_t)channels[i].current_level);
            }
        }
    }

    // 4. Periodic IMU Telemetry (20 Hz)
    static uint32_t last_imu_time = 0;
    if (imu_available && (now - last_imu_time >= 50)) {
        last_imu_time = now;
        read_and_report_imu();
    }

    // 5. Status LED
    if (watchdog_triggered) {
        digitalWrite(PIN_LED, ((now / 200) % 2 == 0) ? LOW : HIGH);
    } else {
        bool any_active = false;
        for (uint8_t i = 0; i < NUM_CHANNELS; i++) {
            if (channels[i].current_level > 0) any_active = true;
        }
        digitalWrite(PIN_LED, any_active ? LOW : HIGH);
    }

    delay(2);
}

void read_and_report_imu() {
    Wire.beginTransmission(MPU6050_ADDR);
    Wire.write(0x3B); // ACCEL_XOUT_H
    if (Wire.endTransmission(false) == 0 && Wire.requestFrom((uint8_t)MPU6050_ADDR, (uint8_t)14, (uint8_t)true) == 14) {
        int16_t ax = Wire.read() << 8 | Wire.read();
        int16_t ay = Wire.read() << 8 | Wire.read();
        int16_t az = Wire.read() << 8 | Wire.read();
        Wire.read(); Wire.read(); // Skip temp
        int16_t gx = Wire.read() << 8 | Wire.read();
        int16_t gy = Wire.read() << 8 | Wire.read();
        int16_t gz = Wire.read() << 8 | Wire.read();

        float roll = atan2f((float)ay, (float)az) * 180.0f / M_PI;
        float pitch = atan2f(-(float)ax, sqrtf((float)ay * ay + (float)az * az)) * 180.0f / M_PI;
        float accel_g = sqrtf((float)ax*ax + (float)ay*ay + (float)az*az) / 16384.0f;

        Serial.printf("IMU %.1f %.1f 0.0 %.2f\n", roll, pitch, accel_g);
    }
}

void apply_channel_pwm(uint8_t ch, uint8_t level_percent) {
    if (ch >= NUM_CHANNELS) return;
    if (level_percent > 100) level_percent = 100;
    uint32_t duty = (uint32_t)map(level_percent, 0, 100, 0, 255);
    ledcWrite(CH_PINS[ch], duty);
}

void emergency_stop() {
    for (uint8_t i = 0; i < NUM_CHANNELS; i++) {
        channels[i].target_level = 0;
        channels[i].current_level = 0.0f;
        channels[i].in_hit_mode = false;
        channels[i].in_wave_mode = false;
        apply_channel_pwm(i, 0);
    }
}

void process_command(String cmd) {
    cmd.trim();
    int first_space = cmd.indexOf(' ');
    String op = (first_space == -1) ? cmd : cmd.substring(0, first_space);
    op.toUpperCase();

    if (op == "PING") {
        Serial.println("PONG");
        return;
    }

    if (op == "STOP") {
        emergency_stop();
        Serial.println("OK STOPPED");
        return;
    }

    if (op == "STATUS") {
        Serial.print("STATUS ");
        for (uint8_t i = 0; i < NUM_CHANNELS; i++) {
            Serial.printf("CH%d:%.0f%% ", i, channels[i].current_level);
        }
        Serial.printf("WD:%s IMU:%s\n", watchdog_triggered ? "TRIGGERED" : "OK", imu_available ? "YES" : "NO");
        return;
    }

    if (op == "SET") {
        int second_space = cmd.indexOf(' ', first_space + 1);
        if (second_space == -1) {
            uint8_t level = cmd.substring(first_space + 1).toInt();
            channels[0].in_hit_mode = false;
            channels[0].in_wave_mode = false;
            channels[0].current_level = level;
            apply_channel_pwm(0, level);
            Serial.printf("OK SET CH0 %d\n", level);
            return;
        }
        uint8_t ch = cmd.substring(first_space + 1, second_space).toInt();
        uint8_t level = cmd.substring(second_space + 1).toInt();
        if (ch < NUM_CHANNELS) {
            channels[ch].in_hit_mode = false;
            channels[ch].in_wave_mode = false;
            channels[ch].current_level = level;
            apply_channel_pwm(ch, level);
            Serial.printf("OK SET CH%d %d\n", ch, level);
        } else {
            Serial.println("ERR INVALID_CHANNEL");
        }
        return;
    }

    if (op == "HIT") {
        int p1 = cmd.indexOf(' ', first_space + 1);
        if (p1 == -1) {
            uint8_t power = cmd.substring(first_space + 1).toInt();
            channels[0].in_wave_mode = false;
            channels[0].in_hit_mode = true;
            channels[0].current_level = power;
            channels[0].decay_rate_per_ms = (float)power / 400.0f;
            apply_channel_pwm(0, power);
            Serial.printf("OK HIT CH0 %d 400ms\n", power);
            return;
        }

        uint8_t ch = cmd.substring(first_space + 1, p1).toInt();
        int p2 = cmd.indexOf(' ', p1 + 1);
        uint8_t power = (p2 == -1) ? cmd.substring(p1 + 1).toInt() : cmd.substring(p1 + 1, p2).toInt();
        uint32_t decay_ms = (p2 == -1) ? 400 : cmd.substring(p2 + 1).toInt();
        if (decay_ms < 50) decay_ms = 50;

        if (ch < NUM_CHANNELS) {
            channels[ch].in_wave_mode = false;
            channels[ch].in_hit_mode = true;
            channels[ch].current_level = power;
            channels[ch].decay_rate_per_ms = (float)power / (float)decay_ms;
            apply_channel_pwm(ch, power);
            Serial.printf("OK HIT CH%d %d %dms\n", ch, power, decay_ms);
        } else {
            Serial.println("ERR INVALID_CHANNEL");
        }
        return;
    }

    if (op == "WAVE") {
        int p1 = cmd.indexOf(' ', first_space + 1);
        int p2 = cmd.indexOf(' ', p1 + 1);
        int p3 = cmd.indexOf(' ', p2 + 1);

        if (p1 != -1 && p2 != -1 && p3 != -1) {
            uint8_t ch = cmd.substring(first_space + 1, p1).toInt();
            float freq = cmd.substring(p1 + 1, p2).toFloat();
            uint8_t min_lvl = cmd.substring(p2 + 1, p3).toInt();
            uint8_t max_lvl = cmd.substring(p3 + 1).toInt();

            if (ch < NUM_CHANNELS) {
                channels[ch].in_hit_mode = false;
                channels[ch].in_wave_mode = true;
                channels[ch].wave_freq = freq;
                channels[ch].wave_min = min_lvl;
                channels[ch].wave_max = max_lvl;
                channels[ch].wave_start_time = millis();
                Serial.printf("OK WAVE CH%d freq=%.2f min=%d max=%d\n", ch, freq, min_lvl, max_lvl);
                return;
            }
        }
        Serial.println("ERR INVALID_WAVE_PARAMS");
        return;
    }

    Serial.printf("ERR UNKNOWN_CMD %s\n", op.c_str());
}
