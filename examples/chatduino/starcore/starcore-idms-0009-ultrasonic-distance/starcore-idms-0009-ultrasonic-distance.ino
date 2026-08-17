#include <MPython.h>
#include <DFRobot_URM10.h>

// 可调参数：保持在来源建议的 80-120ms 区间。
const unsigned long READ_INTERVAL_MS = 100;

DFRobot_URM10 ultrasonic;
unsigned long lastReadMs = 0;

void setup() {
  Serial.begin(115200);
  Serial.println("STARCORE_ULTRASONIC_READY");
}

void loop() {
  unsigned long now = millis();
  if (now - lastReadMs < READ_INTERVAL_MS) return;
  lastReadMs = now;

  float distanceCm = ultrasonic.getDistanceCM(P_H, P_O);
  if (distanceCm > 0) {
    Serial.print("DISTANCE_CM=");
    Serial.println(distanceCm);
  } else {
    Serial.println("NO_ECHO");  // 零表示超时或失败，不当作 0cm。
  }
}
