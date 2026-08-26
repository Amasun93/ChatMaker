#include <DFRobot_SSD1306_I2C.h>

const uint8_t OLED_ADDRESS = 0x3C;
DFRobot_SSD1306_I2C oled;

void setup() {
  Serial.begin(115200);
  oled.begin(OLED_ADDRESS);
  oled.fillScreen(0);
  oled.setCursorLine(1);
  oled.printLine("STARDUST");
  oled.setCursorLine(2);
  oled.printLine("ChatMaker OK");
  oled.setCursorLine(3);
  oled.printLine("OLED 1.3 inch");
  oled.setCursorLine(4);
  oled.printLine("Address 0x3C");
  Serial.println("STARDUST_OLED_READY");
}

void loop() {
  static unsigned long lastReport = 0;
  if (millis() - lastReport >= 2000) {
    lastReport = millis();
    Serial.println("STARDUST_ALIVE");
  }
}
