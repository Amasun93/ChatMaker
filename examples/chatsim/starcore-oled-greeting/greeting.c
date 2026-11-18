#include "greeting.h"
#include <string.h>

// Rows from the UNO R3 ChatSim lesson. A set bit marks one OLED pixel.
static const uint16_t glyphs[4][16] = {
    { // 你
      0x0000, 0x0440, 0x0440, 0x0880, 0x08fe, 0x1112, 0x3014, 0x5014,
      0x1094, 0x1112, 0x1112, 0x1211, 0x1411, 0x1010, 0x10e0, 0x0000,
    },
    { // 好
      0x0000, 0x0800, 0x08fe, 0x1004, 0x1008, 0x1010, 0x7f10, 0x2210,
      0x23ff, 0x1410, 0x0c10, 0x0a10, 0x0910, 0x1010, 0x60e0, 0x0000,
    },
    { // 再
      0x0000, 0x0000, 0x3ffe, 0x0080, 0x0080, 0x0ff8, 0x0888, 0x0888,
      0x0ff8, 0x0888, 0x0888, 0x7fff, 0x0808, 0x0808, 0x0830, 0x0000,
    },
    { // 见
      0x0000, 0x0000, 0x0ff8, 0x0808, 0x0808, 0x0888, 0x0888, 0x0888,
      0x08a8, 0x08a8, 0x0928, 0x0921, 0x0221, 0x0c21, 0x301e, 0x0000,
    },
};

static uint8_t pixels[GREETING_WIDTH * GREETING_HEIGHT / 8];
static int last_level = -1;

static void draw_glyph(int index, int left) {
    for (int row = 0; row < 32; row++) {
        const uint16_t strokes = glyphs[index][row / 2];
        for (int column = 0; column < 32; column++) {
            if (!(strokes & (0x8000u >> (column / 2)))) continue;
            const int x = left + column;
            const int y = 16 + row;
            pixels[y * (GREETING_WIDTH / 8) + x / 8] |= 0x80u >> (x % 8);
        }
    }
}

int greeting_update(int input_level) {
    if (input_level == last_level) return 0;
    last_level = input_level;
    const int first_glyph = input_level == 0 ? 0 : 2;
    memset(pixels, 0, sizeof(pixels));
    draw_glyph(first_glyph, 30);
    draw_glyph(first_glyph + 1, 66);
    return 1;
}

const uint8_t *greeting_pixels(void) {
    return pixels;
}
