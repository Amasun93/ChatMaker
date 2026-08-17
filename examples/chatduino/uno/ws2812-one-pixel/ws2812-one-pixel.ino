#include <DFRobot_NeoPixel.h>

const uint8_t PIXEL_PIN = 6;
DFRobot_NeoPixel pixels;

void setup() {
  pixels.begin(PIXEL_PIN, 1, 32, NEO_GRB + NEO_KHZ800);
  pixels.setPixelColor(0, 0, 48, 0);
  pixels.show();
}

void loop() {}
