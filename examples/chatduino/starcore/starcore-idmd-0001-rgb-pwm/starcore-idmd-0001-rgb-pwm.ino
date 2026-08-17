#include <MPython.h>

// 可调参数：三种颜色切换间隔与亮度（0=灭，255=最亮）。
const unsigned long COLOR_INTERVAL_MS = 800;
const int COLOR_BRIGHTNESS = 96;
const int RED_PIN = P13;
const int GREEN_PIN = P14;
const int BLUE_PIN = P15;
const int RED_CHANNEL = 0;
const int GREEN_CHANNEL = 1;
const int BLUE_CHANNEL = 2;
const int PWM_FREQUENCY_HZ = 5000;
const int PWM_RESOLUTION_BITS = 8;

unsigned long lastColorChangeMs = 0;
int colorIndex = 0;

void setBrightness(int channel, int brightness) {
  // IDMD-0001 是共阳模块，必须反相：255 表示关，0 表示最亮。
  ledcWrite(channel, 255 - brightness);
}

void showColor(int index) {
  setBrightness(RED_CHANNEL, index == 0 ? COLOR_BRIGHTNESS : 0);
  setBrightness(GREEN_CHANNEL, index == 1 ? COLOR_BRIGHTNESS : 0);
  setBrightness(BLUE_CHANNEL, index == 2 ? COLOR_BRIGHTNESS : 0);
}

void setup() {
  Serial.begin(115200);
  ledcSetup(RED_CHANNEL, PWM_FREQUENCY_HZ, PWM_RESOLUTION_BITS);
  ledcSetup(GREEN_CHANNEL, PWM_FREQUENCY_HZ, PWM_RESOLUTION_BITS);
  ledcSetup(BLUE_CHANNEL, PWM_FREQUENCY_HZ, PWM_RESOLUTION_BITS);
  ledcAttachPin(RED_PIN, RED_CHANNEL);
  ledcAttachPin(GREEN_PIN, GREEN_CHANNEL);
  ledcAttachPin(BLUE_PIN, BLUE_CHANNEL);
  setBrightness(RED_CHANNEL, 0);
  setBrightness(GREEN_CHANNEL, 0);
  setBrightness(BLUE_CHANNEL, 0);
  Serial.println("STARCORE_RGB_READY");
}

void loop() {
  unsigned long now = millis();
  if (now - lastColorChangeMs < COLOR_INTERVAL_MS) return;
  lastColorChangeMs = now;
  showColor(colorIndex);
  Serial.print("COLOR_INDEX=");
  Serial.println(colorIndex);
  colorIndex = (colorIndex + 1) % 3;
}
