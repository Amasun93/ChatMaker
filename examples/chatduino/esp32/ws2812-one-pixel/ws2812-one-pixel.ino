#include <Adafruit_NeoPixel.h>

Adafruit_NeoPixel pixels(1, 27, NEO_GRB + NEO_KHZ800);

void setup() {
  pixels.begin();
  pixels.setBrightness(32);
  pixels.setPixelColor(0, pixels.Color(0, 48, 0));
  pixels.show();
}

void loop() {}
