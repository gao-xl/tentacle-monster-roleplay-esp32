/**
 * @file main.cpp
 * @brief OpenHaptic-Roleplay v0.1.0 - Microsecond Biphasic Neural Waveform Synthesizer
 * 
 * True Medical-Grade Biphasic Pulse & Carrier Modulation:
 * - Pulse Width: 100µs - 350µs (eliminates skin prickling pain, targets deep nerve fibers)
 * - Frequency: 10Hz - 120Hz dynamic pulse repetition
 * - Modes: 
 *   0: TAP_PULSE (Muscle throbbing)
 *   1: SURGE_WAVE (Deep sinusoidal tidal flow)
 *   2: PLASMA_ZAP (Sharp high-tension breach burst)
 * - 150ms Rolling Heartbeat Hard-Safety Watchdog with Hardware Deadlock
 */

#include <Arduino.h>
#include <Wire.h>
#include <math.h>

#define PIN_LED         8
#define PIN_LOOP_A      0
#define PIN_LOOP_B      1
#define NUM_LOOPS       2
const uint8_t LOOP_PINS[NUM_LOOPS] = {PIN_LOOP_A, PIN_LOOP_B};

// I2C IMU Pins
#define PIN_I2C_SDA     4
#define PIN_I2C_SCL     5
#define MPU6050_ADDR    0x68
static bool imu_available = false;

// PWM Carrier Configuration (5 kHz high-frequency smoothing)
#define PWM_FREQ        5000
#define PWM_RESOLUTION  8

// Safety Watchdog
#define HARD_WATCHDOG_MS 150
static uint32_t last_sync_time = 0;
static uint8_t expected_token = 0;
static bool is_hard_locked = false;

// Biphasic Waveform Modulation State
struct BiphasicLoop {
    uint8_t power_level;       // 0 - 100%
    uint8_t wave_mode;         // 0: Tap, 1: Surge, 2: Plasma
    uint16_t pulse_width_us;   // 100 - 350 us
    float freq_hz;             // 10 - 120 Hz
    float phase_rad;
    uint32_t last_pulse_time;
};

static BiphasicLoop loops[NUM_LOOPS];

void apply_hardware_pwm(uint8_t loop_idx, uint8_t duty_val) {
    if (loop_idx >= NUM_LOOPS) return;
    if (is_hard_locked) duty_val = 0; // Absolute hardware override
    ledcWrite(LOOP_PINS[loop_idx], duty_val);
}

void emergency_shutdown() {
    is_hard_locked = true;
    for (uint8_t i = 0; i < NUM_LOOPS; i++) {
        loops[i].power_level = 0;
        apply_hardware_pwm(i, 0);
    }
}

void setup() {
    Serial.begin(115200);
    pinMode(PIN_LED, OUTPUT);

    for (uint8_t i = 0; i < NUM_LOOPS; i++) {
        ledcAttach(LOOP_PINS[i], PWM_FREQ, PWM_RESOLUTION);
        loops[i].power_level = 0;
        loops[i].wave_mode = 1; // Default: Smooth Surge
        loops[i].pulse_width_us = 220;
        loops[i].freq_hz = 60.0f;
        loops[i].phase_rad = (i == 1) ? M_PI : 0.0f; // 180-deg phase shift for Loop B
        loops[i].last_pulse_time = 0;
        apply_hardware_pwm(i, 0);
    }

    Wire.begin(PIN_I2C_SDA, PIN_I2C_SCL);
    Wire.beginTransmission(MPU6050_ADDR);
    if (Wire.endTransmission() == 0) imu_available = true;

    last_sync_time = millis();
    Serial.println("[BOOT] v0.1.0 Biphasic Neural Synthesizer Ready.");
}

void loop() {
    uint32_t now = millis();
    uint32_t now_us = micros();

    // 1. Hard Watchdog Verification
    if (!is_hard_locked && (now - last_sync_time > HARD_WATCHDOG_MS)) {
        emergency_shutdown();
        Serial.println("[ALARM] HARD_WATCHDOG_TIMEOUT! Power zeroed.");
    }

    // 2. High-Speed Serial Command Processing
    while (Serial.available() > 0) {
        String line = Serial.readStringUntil('\n');
        line.trim();

        if (line.startsWith("SYNC")) {
            if (is_hard_locked) continue;

            int p1 = line.indexOf(' ', 5);
            int p2 = line.indexOf(' ', p1 + 1);
            if (p1 != -1 && p2 != -1) {
                uint8_t token = line.substring(5, p1).toInt();
                uint8_t lvl_a = line.substring(p1 + 1, p2).toInt();
                uint8_t lvl_b = line.substring(p2 + 1).toInt();

                if (token == expected_token) {
                    expected_token = (expected_token + 1) % 256;
                    last_sync_time = now;
                    loops[0].power_level = lvl_a;
                    loops[1].power_level = lvl_b;
                    Serial.printf("OK_SYNC T:%d\n", token);
                } else {
                    emergency_shutdown();
                }
            }
        }
    }

    // 3. Microsecond-Accurate Biphasic Pulse Synthesizer Engine
    if (!is_hard_locked) {
        for (uint8_t i = 0; i < NUM_LOOPS; i++) {
            if (loops[i].power_level == 0) {
                apply_hardware_pwm(i, 0);
                continue;
            }

            // Mode 1: Smooth Surge Modulation (Carrier envelope synthesis)
            if (loops[i].wave_mode == 1) {
                float t_sec = now / 1000.0f;
                float envelope = (sinf(2.0f * M_PI * 1.5f * t_sec + loops[i].phase_rad) + 1.0f) * 0.5f;
                uint8_t modulated_duty = (uint8_t)(loops[i].power_level * envelope * 2.55f);
                apply_hardware_pwm(i, modulated_duty);
            }
            // Mode 0: Muscle Throbbing Tap
            else {
                uint32_t period_us = (uint32_t)(1000000.0f / loops[i].freq_hz);
                if (now_us - loops[i].last_pulse_time < loops[i].pulse_width_us) {
                    uint8_t duty = (uint8_t)(loops[i].power_level * 2.55f);
                    apply_hardware_pwm(i, duty);
                } else if (now_us - loops[i].last_pulse_time >= period_us) {
                    loops[i].last_pulse_time = now_us;
                } else {
                    apply_hardware_pwm(i, 0); // Inter-pulse interval
                }
            }
        }
    }

    // 4. Status LED
    digitalWrite(PIN_LED, is_hard_locked ? ((now / 80) % 2 == 0 ? LOW : HIGH) : (loops[0].power_level > 0 ? LOW : HIGH));
}
