// Uses the official ST7789/LVGL drivers selected for V1 (CST328) or V2 (CST3530).
#include <Display_ST7789.h>
#include <LVGL_Driver.h>

static lv_obj_t *timeLabel;
static lv_obj_t *stateLabel;
static uint32_t remaining = 60000;
static uint32_t lastTick = 0;
static uint32_t lastPaint = 0;
static bool running = false;

static void updateLabels() {
  uint32_t seconds = (remaining + 999) / 1000;
  char value[16];
  snprintf(value, sizeof(value), "%02lu:%02lu", (unsigned long)(seconds/60), (unsigned long)(seconds%60));
  lv_label_set_text(timeLabel, value);
  lv_label_set_text(stateLabel, remaining == 0 ? "Time is up" : running ? "Running" : "Ready / Paused");
}
static void onStart(lv_event_t *) {
  if (remaining == 0) remaining = 60000;
  running = true; lastTick = millis(); updateLabels();
}
static void onPause(lv_event_t *) {
  running = false; updateLabels();
}
static void onReset(lv_event_t *) {
  running = false; remaining = 60000; updateLabels();
}
static void addButton(const char *text, int y, lv_event_cb_t callback, uint32_t color) {
  lv_obj_t *button = lv_btn_create(lv_scr_act());
  lv_obj_set_size(button, 200, 44); lv_obj_set_pos(button, 20, y);
  lv_obj_set_style_bg_color(button, lv_color_hex(color), 0);
  lv_obj_add_event_cb(button, callback, LV_EVENT_CLICKED, nullptr);
  lv_obj_t *label = lv_label_create(button); lv_label_set_text(label, text); lv_obj_center(label);
}
void setup() {
  Serial.begin(115200);
  pinMode(7, OUTPUT); digitalWrite(7, HIGH);
  Backlight_Init(); LCD_Init(); Lvgl_Init();
  lv_obj_clean(lv_scr_act());
  lv_obj_set_style_bg_color(lv_scr_act(), lv_color_hex(0x101828), 0);
  lv_obj_set_style_text_color(lv_scr_act(), lv_color_white(), 0);
  lv_obj_t *title = lv_label_create(lv_scr_act());
  lv_label_set_text(title, "ChatMaker Class Timer"); lv_obj_align(title, LV_ALIGN_TOP_MID, 0, 16);
  timeLabel = lv_label_create(lv_scr_act());
  lv_obj_align(timeLabel, LV_ALIGN_TOP_MID, 0, 60);
  stateLabel = lv_label_create(lv_scr_act());
  lv_obj_align(stateLabel, LV_ALIGN_TOP_MID, 0, 100);
  addButton("START", 150, onStart, 0x087F5B);
  addButton("PAUSE", 202, onPause, 0x245EA8);
  addButton("RESET", 254, onReset, 0x8F3A58);
  lastTick = millis(); updateLabels();
  Serial.println("CHATMAKER_WAVESHARE_TIMER_READY");
}
void loop() {
  uint32_t now = millis(), elapsed = now - lastTick; lastTick = now;
  if (running) {
    remaining = elapsed >= remaining ? 0 : remaining - elapsed;
    if (remaining == 0) running = false;
  }
  if (now - lastPaint >= 100) { lastPaint = now; updateLabels(); }
  Lvgl_Loop();
  if (Serial.available() && Serial.read() == '?') {
    Serial.printf("CHATMAKER_WAVESHARE_TIMER_READY remaining_ms=%lu running=%d\n", (unsigned long)remaining, running);
  }
  delay(5);
}
