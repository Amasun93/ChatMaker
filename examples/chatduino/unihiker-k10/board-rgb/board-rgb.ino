#include <Adafruit_NeoPixel.h>

Adafruit_NeoPixel pixels(3, 46, NEO_GRB + NEO_KHZ800);

void setup() {
  Serial.begin(115200);
  pixels.begin();
  pixels.setBrightness(16);
}

void loop() {
  for (uint8_t index = 0; index < pixels.numPixels(); ++index) {
    pixels.clear();
    pixels.setPixelColor(index, pixels.Color(0, 80, 0));
    pixels.show();
    delay(250);
  }
  Serial.println("CHATMAKER_BOARD_ID:unihiker-k10");
}
