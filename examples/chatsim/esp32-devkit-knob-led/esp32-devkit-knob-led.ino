#include "knob.h"

constexpr int knobPin = 34;
constexpr int ledPin = 18;

void setup() {
    analogReadResolution(12);
    pinMode(ledPin, OUTPUT);
}

void loop() {
    analogWrite(ledPin, knob_pwm(analogRead(knobPin)));
    delay(5);
}
