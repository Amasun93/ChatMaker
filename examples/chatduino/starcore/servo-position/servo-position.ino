#include <MPython.h>
#include <DFRobot_Servo.h>

Servo servo;

void setup() {
  servo.attach(P9);
  servo.angle(90);
}

void loop() {}
