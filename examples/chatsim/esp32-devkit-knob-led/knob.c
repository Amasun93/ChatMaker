#include "knob.h"

int knob_pwm(int sample) {
    if (sample < 0) {
        sample = 0;
    } else if (sample > 4095) {
        sample = 4095;
    }
    return (sample * 255 + 2047) / 4095;
}
