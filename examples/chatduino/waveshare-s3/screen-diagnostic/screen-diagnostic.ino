// Build only with the revision-selected ChatMaker Waveshare environment.
#include <Display_ST7789.h>
#include <LVGL_Driver.h>

void setup() {
  Serial.begin(115200);
  pinMode(7, OUTPUT); digitalWrite(7, HIGH);
  Backlight_Init(); LCD_Init(); Lvgl_Init();
  lv_obj_clean(lv_scr_act());
  lv_obj_set_style_bg_color(lv_scr_act(), lv_color_hex(0x103050), 0);
  lv_obj_t *label = lv_label_create(lv_scr_act());
  lv_label_set_text(label, "ChatMaker\nWaveshare S3\n240 x 320\nDisplay ready");
  lv_obj_set_style_text_color(label, lv_color_white(), 0);
  lv_obj_set_style_text_align(label, LV_TEXT_ALIGN_CENTER, 0);
  lv_obj_center(label);
  Serial.println("CHATMAKER_WAVESHARE_SCREEN_READY");
}
void loop() {
  Lvgl_Loop();
  if (Serial.available() && Serial.read() == '?') {
    Serial.println("CHATMAKER_WAVESHARE_SCREEN_READY");
  }
  delay(5);
}
