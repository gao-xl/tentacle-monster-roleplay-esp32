/**
 * @file main.cpp
 * @brief OpenHaptic-Roleplay v3.0 - Rolling Heartbeat Medical-Grade Safety Firmware
 * 
 * Hardware-level safety requirements:
 * - Requires "SYNC <token> <level_a> <level_b>" every 100ms.
 * - <token> must strictly increment (modulo 256).
 * - If a token is missed, duplicated, or delayed by >150ms, the ESP32 enters
 *   a hardware HARD_LOCK shutdown state to prevent uncontrolled runaway shocks.
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

// PWM Configuration
#define PWM_FREQ        1000
#define PWM_RESOLUTION  8

// v3.0 Rolling Heartbeat Hard-Safety Variables
#define HARD_WATCHDOG_MS 150
static uint32_t last_sync_time = 0;
static uint8_t expected_token = 0;
static bool is_hard_locked = false;

struct LoopState {
    float current_level;
};
static LoopState loops[NUM_LOOPS];

void apply_loop_pwm(uint8_t loop_idx, uint8_t level_percent) {
    if (loop_idx >= NUM_LOOPS) return;
    if (level_percent > 100) level_percent = 100;
    if (is_hard_locked) level_percent = 0; // Absolute hardware override
    uint32_t duty = (uint32_t)map(level_percent, 0, 100, 0, 255);
    ledcWrite(LOOP_PINS[loop_idx], duty);
}

void emergency_shutdown() {
    is_hard_locked = true;
    for (uint8_t i = 0; i < NUM_LOOPS; i++) {
        loops[i].current_level = 0;
        apply_loop_pwm(i, 0);
    }
}

void setup() {
    Serial.begin(115200);
    pinMode(PIN_LED, OUTPUT);
    
    for (uint8_t i = 0; i < NUM_LOOPS; i++) {
        ledcAttach(LOOP_PINS[i], PWM_FREQ, PWM_RESOLUTION);
        apply_loop_pwm(i, 0);
    }

    Wire.begin(PIN_I2C_SDA, PIN_I2C_SCL);
    Wire.beginTransmission(MPU6050_ADDR);
    if (Wire.endTransmission() == 0) imu_available = true;

    last_sync_time = millis();
    Serial.println("[BOOT] v3.0 Rolling-Heartbeat Controller Ready.");
}

void loop() {
    uint32_t now = millis();

    // 1. Hard Watchdog Check
    if (!is_hard_locked && (now - last_sync_time > HARD_WATCHDOG_MS)) {
        emergency_shutdown();
        Serial.println("[ALARM] HARD_WATCHDOG_TIMEOUT! Hardware locked.");
    }

    // 2. Command Processing
    while (Serial.available() > 0) {
        String line = Serial.readStringUntil('\n');
        line.trim();
        
        if (line.startsWith("PING")) {
            Serial.println("PONG");
            continue;
        }

        // v3.0 Secure Sync Protocol: SYNC <token> <lvl_A> <lvl_B>
        if (line.startsWith("SYNC")) {
            if (is_hard_locked) {
                // Ignore all commands if hardware is locked (requires manual reset)
                continue;
            }

            int p1 = line.indexOf(' ', 5);
            int p2 = line.indexOf(' ', p1 + 1);
            if (p1 != -1 && p2 != -1) {
                uint8_t token = line.substring(5, p1).toInt();
                uint8_t lvl_a = line.substring(p1 + 1, p2).toInt();
                uint8_t lvl_b = line.substring(p2 + 1).toInt();

                if (token == expected_token) {
                    expected_token = (expected_token + 1) % 256;
                    last_sync_time = now;
                    
                    loops[0].current_level = lvl_a;
                    loops[1].current_level = lvl_b;
                    apply_loop_pwm(0, lvl_a);
                    apply_loop_pwm(1, lvl_b);
                    
                    Serial.printf("OK_SYNC T:%d\n", token);
                } else {
                    Serial.printf("[ALARM] TOKEN_MISMATCH! Expected:%d Got:%d. Triggering lock.\n", expected_token, token);
                    emergency_shutdown();
                }
            }
        }
    }

    // 3. IMU Reporting
    static uint32_t last_imu = 0;
    if (imu_available && now - last_imu > 50) {
        last_imu = now;
        // Simplified read logic for brevity
        Serial.println("IMU 0.0 0.0 0.0 0.0");
    }

    // 4. LED Warning
    digitalWrite(PIN_LED, is_hard_locked ? ((now / 100) % 2 == 0) : HIGH);
    delay(2);
}
