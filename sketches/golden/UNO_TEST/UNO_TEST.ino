/**
 * SWARM UNO R3 - Test Firmware
 * Golden sketch for Phase 1 PCP GitHub build offload
 * 
 * Target: Arduino UNO R3
 * Core: arduino:avr@1.8.8
 * FQBN: arduino:avr:uno
 *
 * Minimal test sketch to verify PCP build pipeline
 * Builds successfully and demonstrates compilation for AVR architecture
 */

#include <Wire.h>

// LED pin for status indication
const int LED_PIN = 13;

void setup() {
  Serial.begin(9600);
  pinMode(LED_PIN, OUTPUT);
  
  Serial.println(F("SWARM UNO R3 Build Test"));
  Serial.println(F("======================"));
  
  // Blink to indicate setup complete
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
  
  Serial.print(F("UNO Heartbeat: "));
  Serial.println(millis());
  
  digitalWrite(LED_PIN, LOW);
  delay(1000);
}
