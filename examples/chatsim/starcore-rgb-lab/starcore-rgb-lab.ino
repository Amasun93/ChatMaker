#include <MPython.h>
#include "light.h"

constexpr int button = P8;
constexpr int knob = P0;
constexpr int lampPins[] = {P9, P15, P23};
constexpr int shifts[] = {16, 8, 0};

void setup() {
    pinMode(button, INPUT);  // IDMS-0001 drives HIGH when held.
    for (int channel = 0; channel < 3; channel++) {
        ledcSetup(channel, 5000, 8);
        ledcWrite(channel, 255);
        ledcAttachPin(lampPins[channel], channel);
    }
}

void loop() {
    const uint32_t pwm = starcore_light_pwm(digitalRead(button) == HIGH, analogRead(knob));
    for (int channel = 0; channel < 3; channel++) {
        ledcWrite(channel, (pwm >> shifts[channel]) & 255);
    }
    delay(10);
}
