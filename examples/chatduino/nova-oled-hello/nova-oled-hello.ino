#include <Wire.h>
#include <U8g2lib.h>

// Confirm the module is SSD1306 128x64, I2C 0x3C, SDA21/SCL22 before use.
U8G2_SSD1306_128X64_NONAME_F_HW_I2C display(U8G2_R0, U8X8_PIN_NONE);

void setup() {
  Serial.begin(115200);
  Wire.begin(21, 22);
  display.begin();
  display.enableUTF8Print();
  display.clearBuffer();
  display.setFont(u8g2_font_unifont_t_chinese2);
  display.setCursor(40, 30);
  display.print("你好");
  display.setFont(u8g2_font_6x10_tf);
  display.setCursor(32, 52);
  display.print("ChatMaker");
  display.sendBuffer();
}

void loop() {
  Serial.println("NOVA_OLED_HELLO_DONE");
  delay(2000);
}
