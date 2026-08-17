#include <DFRobot_Servo.h>

const uint8_t SERVO_PIN = 9;
const uint8_t BUTTON_PIN = 2;
Servo servo;

void setup() {
  pinMode(BUTTON_PIN, INPUT_PULLUP);
  servo.attach(SERVO_PIN);
}

void loop() {
  servo.angle(digitalRead(BUTTON_PIN) == LOW ? 90 : 20);
  delay(20);
}
