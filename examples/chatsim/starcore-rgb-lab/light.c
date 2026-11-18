#include "light.h"

uint32_t starcore_light_pwm(int pressed, int sample) {
    if (!pressed) return 0xffffff;
    if (sample < 0) sample = 0;
    if (sample > 4095) sample = 4095;

    // The knob sweeps red, green and blue, with a gradual mix between them.
    uint32_t position = ((uint32_t)sample * 510 + 2047) / 4095;
    uint32_t red, green, blue;
    if (position <= 255) {
        red = 255 - position;
        green = position;
        blue = 0;
    } else {
        red = 0;
        green = 510 - position;
        blue = position - 255;
    }
    return ((255 - red) << 16) | ((255 - green) << 8) | (255 - blue);
}
