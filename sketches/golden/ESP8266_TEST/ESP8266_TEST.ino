/**
 * SWARM ESP8266 - Test Firmware
 * Golden sketch for Phase 1 PCP GitHub build offload
 * 
 * Target: ESP8266 NodeMCU v2
 * Core: esp8266:esp8266@3.1.2
 * FQBN: esp8266:esp8266:nodemcuv2
 *
 * Minimal test sketch to verify PCP build pipeline
 * Builds successfully and demonstrates compilation for Xtensa architecture
 */

#include <ESP8266WiFi.h>

const int LED_PIN = D4; // GPIO2 on NodeMCU

void setup() {
  Serial.begin(115200);
  delay(100);
  
  pinMode(LED_PIN, OUTPUT);
  
  Serial.println(F("\n\nSWARM ESP8266 Build Test"));
  Serial.println(F("======================="));
  
  // Blink pattern
  for(int i = 0; i < 5; i++) {
    digitalWrite(LED_PIN, LOW);
    delay(100);
    digitalWrite(LED_PIN, HIGH);
    delay(100);
  }
  
  Serial.println(F("Setup complete. Ready for commands."));
}

void loop() {
  digitalWrite(LED_PIN, LOW);
  delay(1000);
  
  Serial.print(F("ESP8266 Heartbeat: "));
  Serial.println(millis());
  
  digitalWrite(LED_PIN, HIGH);
  delay(1000);
}
