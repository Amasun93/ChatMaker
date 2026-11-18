#pragma once

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

// One packed RGB PWM value. The common-anode lamp is off at duty 255.
uint32_t starcore_light_pwm(int pressed, int sample);

#ifdef __cplusplus
}
#endif
