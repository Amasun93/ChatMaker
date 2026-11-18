// Use ChatMaker's Waveshare ESP32-S3-Touch-LCD-2.8 V2 (CST3530) profile.
#include <Display_ST7789.h>
#include <LVGL_Driver.h>
#include "greeting_ui.h"

void setup() {
    pinMode(7, OUTPUT);
    digitalWrite(7, HIGH);
    Backlight_Init();
    LCD_Init();
    Lvgl_Init();
    greeting_ui_create();
}

void loop() {
    Lvgl_Loop();
    delay(5);
}
