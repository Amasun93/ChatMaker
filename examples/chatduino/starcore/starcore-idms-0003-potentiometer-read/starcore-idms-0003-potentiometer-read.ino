#include <MPython.h>

// 可调参数：P0 是课堂默认模拟输入；输出间隔单位是毫秒。
const int POT_PIN = P0;
const unsigned long READ_INTERVAL_MS = 200;
unsigned long lastReadMs = 0;

void setup() {
  Serial.begin(115200);
  Serial.println("STARCORE_POT_READY");
}

void loop() {
  unsigned long now = millis();
  if (now - lastReadMs < READ_INTERVAL_MS) return;
  lastReadMs = now;
  int rawValue = analogRead(POT_PIN);
  Serial.print("POT_RAW=");
  Serial.println(rawValue);  // 先看原始范围，再决定是否映射成百分比。
}
