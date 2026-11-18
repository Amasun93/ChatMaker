#include "greeting_ui.h"

LV_FONT_DECLARE(chatsim_greeting_62);
LV_FONT_DECLARE(chatsim_button_27);

static void update_greeting(lv_event_t *event) {
    lv_event_code_t code = lv_event_get_code(event);
    bool pressed = code == LV_EVENT_PRESSED;
    if (!pressed && code != LV_EVENT_RELEASED && code != LV_EVENT_PRESS_LOST) return;

    lv_obj_t *message = lv_event_get_user_data(event);
    lv_label_set_text_static(message, pressed ? "你好" : "再见");
    lv_obj_set_style_text_color(message, lv_color_hex(pressed ? 0xb5f5d9 : 0xf1f8f5), 0);
}

lv_obj_t *greeting_ui_create(void) {
    lv_obj_t *screen = lv_scr_act();
    lv_obj_clean(screen);
    lv_obj_clear_flag(screen, LV_OBJ_FLAG_SCROLLABLE);
    lv_obj_set_style_bg_color(screen, lv_color_hex(0x122824), 0);
    lv_obj_set_style_bg_opa(screen, LV_OPA_COVER, 0);

    lv_obj_t *message = lv_label_create(screen);
    lv_obj_set_style_text_font(message, &chatsim_greeting_62, 0);
    lv_obj_set_style_text_color(message, lv_color_hex(0xf1f8f5), 0);
    lv_label_set_text_static(message, "再见");
    lv_obj_align(message, LV_ALIGN_TOP_MID, 0, 65);

    lv_obj_t *button = lv_btn_create(screen);
    lv_obj_remove_style_all(button);
    lv_obj_clear_flag(button, LV_OBJ_FLAG_SCROLLABLE);
    lv_obj_set_size(button, 176, 63);
    lv_obj_align(button, LV_ALIGN_BOTTOM_MID, 0, -49);
    lv_obj_set_style_radius(button, 15, 0);
    lv_obj_set_style_bg_opa(button, LV_OPA_COVER, 0);
    lv_obj_set_style_bg_color(button, lv_color_hex(0x256b58), 0);
    lv_obj_set_style_bg_color(button, lv_color_hex(0x337e68), LV_STATE_PRESSED);
    lv_obj_set_style_border_width(button, 1, 0);
    lv_obj_set_style_border_color(button, lv_color_hex(0x468e77), 0);
    lv_obj_add_event_cb(button, update_greeting, LV_EVENT_ALL, message);

    lv_obj_t *label = lv_label_create(button);
    lv_obj_set_style_text_color(label, lv_color_white(), 0);
    lv_obj_set_style_text_font(label, &chatsim_button_27, 0);
    lv_label_set_text_static(label, "按住我");
    lv_obj_center(label);
    return button;
}
