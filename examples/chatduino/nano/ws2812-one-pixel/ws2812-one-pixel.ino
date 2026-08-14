#include <DFRobot_NeoPixel.h>

const uint8_t PIXEL_PIN = 6;
const uint16_t PIXEL_COUNT = 1;
const uint8_t SAFE_BRIGHTNESS = 32;
DFRobot_NeoPixel pixels;

void setup() {
  Serial.begin(9600);
  pixels.begin(PIXEL_PIN, PIXEL_COUNT, SAFE_BRIGHTNESS, NEO_GRB + NEO_KHZ800);
  pixels.clear();
  pixels.show();
  Serial.println("WS2812_PIXEL_READY");
}

void loop() {
  pixels.setPixelColor(0, 64, 0, 0);
  pixels.show();
  delay(700);
  pixels.setPixelColor(0, 0, 64, 0);
  pixels.show();
  delay(700);
  pixels.setPixelColor(0, 0, 0, 64);
  pixels.show();
  delay(700);
  pixels.clear();
  pixels.show();
  delay(700);
}
