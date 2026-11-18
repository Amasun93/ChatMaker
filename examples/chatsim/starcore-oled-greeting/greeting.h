#pragma once

#include <stdint.h>

#define GREETING_WIDTH 128
#define GREETING_HEIGHT 64

#ifdef __cplusplus
extern "C" {
#endif

int greeting_update(int input_level);
const uint8_t *greeting_pixels(void);

#ifdef __cplusplus
}
#endif
