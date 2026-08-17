#include <MPython.h>
#include <DFRobot_URM10.h>

DFRobot_URM10 ultrasonic;

void setup() {
  Serial.begin(115200);
}

void loop() {
  float distanceCm = ultrasonic.getDistanceCM(P_H, P_O);
  if (distanceCm > 0) Serial.println(distanceCm);
  else Serial.println("NO_ECHO");
  delay(100);
}
