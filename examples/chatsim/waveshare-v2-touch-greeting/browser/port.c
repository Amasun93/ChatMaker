#include "greeting_ui.h"

#define WIDTH 240
#define HEIGHT 320

static lv_color_t draw_pixels[WIDTH * 24];
static uint8_t rgba[WIDTH * HEIGHT * 4];
static lv_disp_draw_buf_t draw_buffer;
static lv_disp_drv_t display_driver;
static lv_indev_drv_t pointer_driver;
static lv_indev_data_t input;
static lv_obj_t *button;
static uint32_t generation;

static void flush(lv_disp_drv_t *driver, const lv_area_t *area, lv_color_t *color) {
    for (int y = area->y1; y <= area->y2; y++) {
        for (int x = area->x1; x <= area->x2; x++, color++) {
            uint8_t *pixel = &rgba[(y * WIDTH + x) * 4];
            pixel[0] = color->ch.red;
            pixel[1] = color->ch.green;
            pixel[2] = color->ch.blue;
            pixel[3] = 255;
        }
    }
    generation++;
    lv_disp_flush_ready(driver);
}

static void read_pointer(lv_indev_drv_t *driver, lv_indev_data_t *sample) {
    (void)driver;
    *sample = input;
}

void demo_start(void) {
    lv_init();
    lv_disp_draw_buf_init(&draw_buffer, draw_pixels, NULL, WIDTH * 24);
    lv_disp_drv_init(&display_driver);
    display_driver.hor_res = WIDTH;
    display_driver.ver_res = HEIGHT;
    display_driver.flush_cb = flush;
    display_driver.draw_buf = &draw_buffer;
    lv_disp_drv_register(&display_driver);

    lv_indev_drv_init(&pointer_driver);
    pointer_driver.type = LV_INDEV_TYPE_POINTER;
    pointer_driver.read_cb = read_pointer;
    lv_indev_drv_register(&pointer_driver);
    button = greeting_ui_create();
    lv_refr_now(NULL);
}

uint8_t *demo_pixels(void) { return rgba; }
uint32_t demo_generation(void) { return generation; }

void demo_pointer(int x, int y, int pressed) {
    input.point.x = x;
    input.point.y = y;
    input.state = pressed ? LV_INDEV_STATE_PR : LV_INDEV_STATE_REL;
    lv_timer_ready(pointer_driver.read_timer);
    lv_timer_handler();
    lv_refr_now(NULL);
}

void demo_key(int pressed) {
    lv_area_t area;
    lv_obj_get_coords(button, &area);
    demo_pointer((area.x1 + area.x2) / 2, (area.y1 + area.y2) / 2, pressed);
}
