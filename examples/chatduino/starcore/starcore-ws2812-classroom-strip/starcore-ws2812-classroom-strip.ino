#include <MPython.h>

// 可调参数：先按实物灯珠数量修改，初次测试保持低亮度。
const int LED_PIN = P8;
const int LED_COUNT = 8;
const int BRIGHTNESS = 32;
const unsigned long COLOR_HOLD_MS = 1500;

DFRobot_NeoPixel strip;
unsigned long lastChangeMs = 0;
int colorIndex = 0;

const uint32_t SAFE_COLORS[] = {
  0x200000,  // 暗红
  0x002000,  // 暗绿
  0x000020,  // 暗蓝
  0x000000   // 熄灭
};

void showColor(uint32_t color) {
  strip.setRangeColor(0, LED_COUNT - 1, color);
  strip.show();
}

void setup() {
  Serial.begin(115200);
  strip.begin(LED_PIN, LED_COUNT, BRIGHTNESS, NEO_GRB + NEO_KHZ800);
  strip.clear();
  strip.show();
  Serial.println("STARCORE_WS2812_READY");
}

void loop() {
  unsigned long now = millis();
  if (now - lastChangeMs < COLOR_HOLD_MS) return;
  lastChangeMs = now;

  showColor(SAFE_COLORS[colorIndex]);
  Serial.printf("COLOR_STEP=%d\n", colorIndex);
  colorIndex = (colorIndex + 1) % 4;
}
