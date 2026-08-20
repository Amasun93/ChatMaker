#include <MPython.h>
#include <DFRobot_Servo.h>

// 可调参数：必须先按真实机构缩小范围，避免夹手和顶住限位。
const int SERVO_PIN = P9;
const int SAFE_ANGLE = 90;
const int TEST_ANGLES[] = {60, 90, 120, 90};
const int TEST_ANGLE_COUNT = 4;
const unsigned long MOVE_INTERVAL_MS = 2500;

Servo classroomServo;
unsigned long lastMoveMs = 0;
int nextAngleIndex = 0;

void setup() {
  Serial.begin(115200);
  classroomServo.attach(SERVO_PIN);
  classroomServo.angle(SAFE_ANGLE);
  Serial.println("STARCORE_SG90_READY");
}

void loop() {
  unsigned long now = millis();
  if (now - lastMoveMs < MOVE_INTERVAL_MS) return;
  lastMoveMs = now;

  int angle = TEST_ANGLES[nextAngleIndex];
  classroomServo.angle(angle);
  Serial.printf("SERVO_ANGLE=%d\n", angle);
  nextAngleIndex = (nextAngleIndex + 1) % TEST_ANGLE_COUNT;
}
