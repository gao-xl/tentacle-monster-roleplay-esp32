/**
 * @file main.cpp
 * @brief OpenHaptic-Roleplay Dual-Circuit Independent Firmware for ESP32-C3 SuperMini
 * 
 * True Dual-Loop Independent Hardware Architecture:
 * - Loop A (Channel 0 / Pads 1-2): Driven by GPIO 0 (LEDC Channel 0, Timer 0)
 * - Loop B (Channel 1 / Pads 3-4): Driven by GPIO 1 (LEDC Channel 1, Timer 1)
 * - Atomic Dual Setting: 'DUAL <lvl_a> <lvl_b>'
 * - Spatial Traveling Flow: 'FLOW <freq> <phase_deg> <min> <max>'
 * - Independent HIT Decay & Waveform Oscillators
 * - 2000ms Dual-Safety Watchdog & Emergency STOP
 * - I2C Gyroscope IMU (MPU6050 on SDA=GPIO4, SCL=GPIO5)
 */

#include <Arduino.h>
#include <Wire.h>
#include <math.h>

#define PIN_LED         8    // Onboard Status LED (Active LOW)

// Dual Independent Circuit Pinout
#define PIN_LOOP_A      0    // Loop A (Pads 1-2: Core / Upper)
#define PIN_LOOP_B      1    // Loop B (Pads 3-4: Legs / Lower)
#define NUM_LOOPS       2

const uint8_t LOOP_PINS[NUM_LOOPS] = {PIN_LOOP_A, PIN_LOOP_B};

// I2C IMU Pins
#define PIN_I2C_SDA     4
#define PIN_I2C_SCL     5
#define MPU6050_ADDR    0x68
static bool imu_available = false;

// PWM Configuration (1 kHz, 8-bit resolution 0-255)
#define PWM_FREQ        1000
#define PWM_RESOLUTION  8

// Safety Watchdog
#define WATCHDOG_TIMEOUT_MS 2000
static uint32_t last_cmd_time = 0;
static bool watchdog_triggered = false;

// Dual Circuit Independent State Structure
struct LoopState {
    uint8_t target_level;      // 0 - 100%
    float current_level;       // 0.0 - 100.0%
    
    // Independent HIT Decay Mode
    bool in_hit_mode;
    float decay_rate_per_ms;
    
    // Independent Wave Oscillation Mode
    bool in_wave_mode;
    float wave_freq;
    uint8_t wave_min;
    uint8_t wave_max;
    float phase_offset_rad;    // Spatial phase shift (e.g. 180 deg for alternating flow)
    uint32_t wave_start_time;
};

static LoopState loops[NUM_LOOPS];

// Prototypes
void apply_loop_pwm(uint8_t loop_idx, uint8_t level_percent);
void process_command(String cmd);
void emergency_stop_dual();
void init_imu();
void read_and_report_imu();

void setup() {
    Serial.begin(115200);
    
    pinMode(PIN_LED, OUTPUT);
    digitalWrite(PIN_LED, HIGH);

    // Initialize Dual Independent LEDC PWM Channels
    for (uint8_t i = 0; i < NUM_LOOPS; i++) {
        ledcAttach(LOOP_PINS[i], PWM_FREQ, PWM_RESOLUTION);
        loops[i].target_level = 0;
        loops[i].current_level = 0.0f;
        loops[i].in_hit_mode = false;
        loops[i].in_wave_mode = false;
        loops[i].phase_offset_rad = 0.0f;
        apply_loop_pwm(i, 0);
    }

    init_imu();
    last_cmd_time = millis();
    
    // Triple Boot Blink
    for (int k = 0; k < 3; k++) {
        digitalWrite(PIN_LED, LOW);
        delay(80);
        digitalWrite(PIN_LED, HIGH);
        delay(80);
    }

    Serial.println("[BOOT] OpenHaptic ESP32-C3 Dual-Circuit Independent Controller Ready.");
    Serial.println("[BOOT] Loop A (Pads 1-2) -> GPIO0 | Loop B (Pads 3-4) -> GPIO1");
}

void init_imu() {
    Wire.begin(PIN_I2C_SDA, PIN_I2C_SCL);
    Wire.beginTransmission(MPU6050_ADDR);
    if (Wire.endTransmission() == 0) {
        Wire.beginTransmission(MPU6050_ADDR);
        Wire.write(0x6B);
        Wire.write(0);
        Wire.endTransmission(true);
        imu_available = true;
    } else {
        imu_available = false;
    }
}

void loop() {
    uint32_t now = millis();

    // 1. Read Serial Command Stream
    while (Serial.available() > 0) {
        String line = Serial.readStringUntil('\n');
        line.trim();
        if (line.length() > 0) {
            process_command(line);
            last_cmd_time = now;
            watchdog_triggered = false;
        }
    }

    // 2. Safety Watchdog Verification
    if (!watchdog_triggered && (now - last_cmd_time > WATCHDOG_TIMEOUT_MS)) {
        watchdog_triggered = true;
        emergency_stop_dual();
        Serial.println("[WARN] Watchdog timeout: Dual circuits safely zeroed.");
    }

    // 3. Update Dual Channel Dynamics (100 Hz Loop)
    static uint32_t last_tick = 0;
    if (now - last_tick >= 10) {
        float dt = (now - last_tick);
        last_tick = now;

        for (uint8_t i = 0; i < NUM_LOOPS; i++) {
            if (loops[i].in_hit_mode) {
                loops[i].current_level -= loops[i].decay_rate_per_ms * dt;
                if (loops[i].current_level <= 0.0f) {
                    loops[i].current_level = 0.0f;
                    loops[i].in_hit_mode = false;
                }
                apply_loop_pwm(i, (uint8_t)loops[i].current_level);
            } else if (loops[i].in_wave_mode) {
                float elapsed_sec = (now - loops[i].wave_start_time) / 1000.0f;
                float angle = 2.0f * M_PI * loops[i].wave_freq * elapsed_sec + loops[i].phase_offset_rad;
                float sin_val = (sinf(angle) + 1.0f) / 2.0f; // 0.0 to 1.0
                float range = loops[i].wave_max - loops[i].wave_min;
                loops[i].current_level = loops[i].wave_min + (range * sin_val);
                apply_loop_pwm(i, (uint8_t)loops[i].current_level);
            }
        }
    }

    // 4. Report IMU Telemetry (20 Hz)
    static uint32_t last_imu_time = 0;
    if (imu_available && (now - last_imu_time >= 50)) {
        last_imu_time = now;
        read_and_report_imu();
    }

    // 5. LED Status Indication
    if (watchdog_triggered) {
        digitalWrite(PIN_LED, ((now / 200) % 2 == 0) ? LOW : HIGH);
    } else {
        bool active = (loops[0].current_level > 0 || loops[1].current_level > 0);
        digitalWrite(PIN_LED, active ? LOW : HIGH);
    }

    delay(2);
}

void read_and_report_imu() {
    Wire.beginTransmission(MPU6050_ADDR);
    Wire.write(0x3B);
    if (Wire.endTransmission(false) == 0 && Wire.requestFrom((uint8_t)MPU6050_ADDR, (uint8_t)14, (uint8_t)true) == 14) {
        int16_t ax = Wire.read() << 8 | Wire.read();
        int16_t ay = Wire.read() << 8 | Wire.read();
        int16_t az = Wire.read() << 8 | Wire.read();
        Wire.read(); Wire.read();
        int16_t gx = Wire.read() << 8 | Wire.read();
        int16_t gy = Wire.read() << 8 | Wire.read();
        int16_t gz = Wire.read() << 8 | Wire.read();

        float roll = atan2f((float)ay, (float)az) * 180.0f / M_PI;
        float pitch = atan2f(-(float)ax, sqrtf((float)ay * ay + (float)az * az)) * 180.0f / M_PI;
        float accel_g = sqrtf((float)ax*ax + (float)ay*ay + (float)az*az) / 16384.0f;

        Serial.printf("IMU %.1f %.1f 0.0 %.2f\n", roll, pitch, accel_g);
    }
}

void apply_loop_pwm(uint8_t loop_idx, uint8_t level_percent) {
    if (loop_idx >= NUM_LOOPS) return;
    if (level_percent > 100) level_percent = 100;
    uint32_t duty = (uint32_t)map(level_percent, 0, 100, 0, 255);
    ledcWrite(LOOP_PINS[loop_idx], duty);
}

void emergency_stop_dual() {
    for (uint8_t i = 0; i < NUM_LOOPS; i++) {
        loops[i].target_level = 0;
        loops[i].current_level = 0.0f;
        loops[i].in_hit_mode = false;
        loops[i].in_wave_mode = false;
        apply_loop_pwm(i, 0);
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
        emergency_stop_dual();
        Serial.println("OK STOPPED_DUAL");
        return;
    }

    if (op == "STATUS") {
        Serial.printf("STATUS LOOP_A(Pads1-2):%.0f%% LOOP_B(Pads3-4):%.0f%% WD:%s\n", 
                      loops[0].current_level, loops[1].current_level, watchdog_triggered ? "TRIGGERED" : "OK");
        return;
    }

    // DUAL <level_a> <level_b> (Atomic setting of both independent loops)
    if (op == "DUAL") {
        int second_space = cmd.indexOf(' ', first_space + 1);
        if (second_space != -1) {
            uint8_t lvl_a = cmd.substring(first_space + 1, second_space).toInt();
            uint8_t lvl_b = cmd.substring(second_space + 1).toInt();
            for (int i=0; i<2; i++) { loops[i].in_hit_mode = false; loops[i].in_wave_mode = false; }
            loops[0].current_level = lvl_a; loops[1].current_level = lvl_b;
            apply_loop_pwm(0, lvl_a); apply_loop_pwm(1, lvl_b);
            Serial.printf("OK DUAL A=%d B=%d\n", lvl_a, lvl_b);
            return;
        }
    }

    // FLOW <freq_hz> <phase_deg> <min> <max> (Traveling wave across Loop A & B)
    // Example: FLOW 1.5 180 15 65 (Loop A and Loop B oscillate 180-deg out of phase)
    if (op == "FLOW") {
        int p1 = cmd.indexOf(' ', first_space + 1);
        int p2 = cmd.indexOf(' ', p1 + 1);
        int p3 = cmd.indexOf(' ', p2 + 1);
        if (p1 != -1 && p2 != -1 && p3 != -1) {
            float freq = cmd.substring(first_space + 1, p1).toFloat();
            float phase_deg = cmd.substring(p1 + 1, p2).toFloat();
            uint8_t min_lvl = cmd.substring(p2 + 1, p3).toInt();
            uint8_t max_lvl = cmd.substring(p3 + 1).toInt();

            uint32_t t_now = millis();
            // Loop A: 0 deg phase
            loops[0].in_hit_mode = false; loops[0].in_wave_mode = true;
            loops[0].wave_freq = freq; loops[0].wave_min = min_lvl; loops[0].wave_max = max_lvl;
            loops[0].phase_offset_rad = 0.0f; loops[0].wave_start_time = t_now;

            // Loop B: shifted by phase_deg
            loops[1].in_hit_mode = false; loops[1].in_wave_mode = true;
            loops[1].wave_freq = freq; loops[1].wave_min = min_lvl; loops[1].wave_max = max_lvl;
            loops[1].phase_offset_rad = (phase_deg * M_PI) / 180.0f; loops[1].wave_start_time = t_now;

            Serial.printf("OK FLOW freq=%.2f phase=%.0f min=%d max=%d\n", freq, phase_deg, min_lvl, max_lvl);
            return;
        }
    }

    // SET <ch 0|1> <level 0-100>
    if (op == "SET") {
        int second_space = cmd.indexOf(' ', first_space + 1);
        if (second_space != -1) {
            uint8_t ch = cmd.substring(first_space + 1, second_space).toInt();
            uint8_t level = cmd.substring(second_space + 1).toInt();
            if (ch < NUM_LOOPS) {
                loops[ch].in_hit_mode = false; loops[ch].in_wave_mode = false;
                loops[ch].current_level = level;
                apply_loop_pwm(ch, level);
                Serial.printf("OK SET LOOP_%c %d\n", ch == 0 ? 'A' : 'B', level);
                return;
            }
        }
    }

    // HIT <ch 0|1> <power 0-100> [decay_ms]
    if (op == "HIT") {
        int p1 = cmd.indexOf(' ', first_space + 1);
        int p2 = cmd.indexOf(' ', p1 + 1);
        if (p1 != -1) {
            uint8_t ch = cmd.substring(first_space + 1, p2 == -1 ? cmd.length() : p2).toInt();
            uint8_t power = (p2 == -1) ? 50 : cmd.substring(p2 + 1).toInt();
            if (ch < NUM_LOOPS) {
                loops[ch].in_wave_mode = false; loops[ch].in_hit_mode = true;
                loops[ch].current_level = power;
                loops[ch].decay_rate_per_ms = (float)power / 400.0f;
                apply_loop_pwm(ch, power);
                Serial.printf("OK HIT LOOP_%c %d\n", ch == 0 ? 'A' : 'B', power);
                return;
            }
        }
    }

    Serial.printf("ERR UNKNOWN_CMD %s\n", op.c_str());
}
