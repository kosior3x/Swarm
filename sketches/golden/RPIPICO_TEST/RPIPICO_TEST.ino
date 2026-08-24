/**
 * SWARM RP2040 Pico - Test Firmware
 * Golden sketch for Phase 1 PCP GitHub build offload
 * 
 * Target: Raspberry Pi Pico (RP2040)
 * Core: rp2040:rp2040@6.0.0
 * FQBN: rp2040:rp2040:rpipico
 *
 * Minimal test sketch to verify PCP build pipeline
 * Builds successfully and demonstrates compilation for ARM RP2040 architecture
 */

#include <Wire.h>

const int LED_PIN = 25; // Built-in LED on Pico

void setup() {
  Serial.begin(115200);
  
  pinMode(LED_PIN, OUTPUT);
  
  Serial.println(F("\nSWARM RP2040 Pico Build Test"));
  Serial.println(F("============================="));
  
  // Blink pattern
  for(int i = 0; i < 5; i++) {
    digitalWrite(LED_PIN, HIGH);
    delay(100);
    digitalWrite(LED_PIN, LOW);
    delay(100);
  }
  
  Serial.println(F("Setup complete. Ready for commands."));
}

void loop() {
  digitalWrite(LED_PIN, HIGH);
  delay(1000);
  
  Serial.print(F("Pico Heartbeat: "));
  Serial.println(millis());
  
  digitalWrite(LED_PIN, LOW);
  delay(1000);
}
