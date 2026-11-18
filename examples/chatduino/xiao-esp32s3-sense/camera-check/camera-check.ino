#include <esp_camera.h>

bool cameraReady = false;

void setup() {
  Serial.begin(115200);
  camera_config_t camera{};
  camera.ledc_channel = LEDC_CHANNEL_0;
  camera.ledc_timer = LEDC_TIMER_0;
  camera.pin_d0 = 15;
  camera.pin_d1 = 17;
  camera.pin_d2 = 18;
  camera.pin_d3 = 16;
  camera.pin_d4 = 14;
  camera.pin_d5 = 12;
  camera.pin_d6 = 11;
  camera.pin_d7 = 48;
  camera.pin_xclk = 10;
  camera.pin_pclk = 13;
  camera.pin_vsync = 38;
  camera.pin_href = 47;
  camera.pin_sccb_sda = 40;
  camera.pin_sccb_scl = 39;
  camera.pin_pwdn = -1;
  camera.pin_reset = -1;
  camera.xclk_freq_hz = 20000000;
  camera.pixel_format = PIXFORMAT_JPEG;
  camera.frame_size = FRAMESIZE_QVGA;
  camera.jpeg_quality = 12;
  camera.fb_count = 1;
  camera.fb_location = CAMERA_FB_IN_PSRAM;
  camera.grab_mode = CAMERA_GRAB_WHEN_EMPTY;
  const esp_err_t result = esp_camera_init(&camera);
  cameraReady = (result == ESP_OK);
  if (!cameraReady) {
    Serial.printf("Camera init failed: 0x%x\n", result);
  }
}

void loop() {
  if (cameraReady) {
    camera_fb_t* frame = esp_camera_fb_get();
    if (frame && frame->len > 0) {
      Serial.printf("CHATMAKER_BOARD_ID:seeed-xiao-esp32s3-sense frame_bytes=%u\n",
                    static_cast<unsigned>(frame->len));
    } else {
      Serial.println("Camera did not return an image");
    }
    if (frame) {
      esp_camera_fb_return(frame);
    }
  } else {
    Serial.println("Check the Sense camera board and ribbon cable with USB unplugged");
  }
  delay(3000);
}
