#include <MPython.h>

// 可调参数：按钮接到 P8；消抖时间越大，过滤抖动越强。
const int BUTTON_PIN = P8;
const unsigned long DEBOUNCE_MS = 30;

int lastRawState = LOW;
int stableState = LOW;
unsigned long lastChangeMs = 0;

void setup() {
  Serial.begin(115200);
  pinMode(BUTTON_PIN, INPUT);  // 三线有源按钮：按下 HIGH，松开 LOW。
  lastRawState = digitalRead(BUTTON_PIN);
  stableState = lastRawState;
  Serial.println("STARCORE_BUTTON_READY");
}

void loop() {
  int rawState = digitalRead(BUTTON_PIN);
  unsigned long now = millis();
  if (rawState != lastRawState) {
    lastRawState = rawState;
    lastChangeMs = now;
  }
  if (rawState != stableState && now - lastChangeMs >= DEBOUNCE_MS) {
    stableState = rawState;
    Serial.println(stableState == HIGH ? "PRESSED" : "RELEASED");
  }
}
