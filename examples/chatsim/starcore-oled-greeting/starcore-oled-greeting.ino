#include <MPython.h>
#include "greeting.h"

// Starcore's built-in A key is P5/GPIO0, active LOW.
constexpr uint8_t buttonAInput = 0;

void setup() {
    pinMode(buttonAInput, INPUT_PULLUP);
    display.begin(0x3c);
}

void loop() {
    if (greeting_update(digitalRead(buttonAInput))) {
        display.drawImage(0, 0, GREETING_WIDTH, GREETING_HEIGHT, greeting_pixels());
    }
    delay(5);
}
