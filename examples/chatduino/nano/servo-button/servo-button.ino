#include <DFRobot_Servo.h>

const uint8_t SERVO_PIN = 9;
const uint8_t BUTTON_PIN = 2;
Servo servo;

void setup() {
  pinMode(BUTTON_PIN, INPUT_PULLUP);
  Serial.begin(9600);
  servo.attach(SERVO_PIN);
  servo.angle(20);
  Serial.println("SERVO_BUTTON_READY");
}

void loop() {
  bool pressed = digitalRead(BUTTON_PIN) == LOW;
  servo.angle(pressed ? 90 : 20);
  delay(20);
}
