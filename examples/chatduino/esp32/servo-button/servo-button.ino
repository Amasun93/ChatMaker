#include <ESP32Servo.h>

const uint8_t SERVO_PIN = 18;
const uint8_t BUTTON_PIN = 23;
Servo servo;

void setup() {
  pinMode(BUTTON_PIN, INPUT_PULLUP);
  servo.setPeriodHertz(50);
  servo.attach(SERVO_PIN, 500, 2400);
}

void loop() {
  servo.write(digitalRead(BUTTON_PIN) == LOW ? 90 : 20);
  delay(20);
}
