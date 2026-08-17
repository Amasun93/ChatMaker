#include <MPython.h>

DFRobot_NeoPixel strip;

void setup() {
  strip.begin(P8, 8);
  strip.setRangeColor(0, 7, 0x002800);
}

void loop() {}
