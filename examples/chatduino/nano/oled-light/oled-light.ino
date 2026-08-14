#include <DFRobot_SSD1306_I2C.h>

const uint8_t LIGHT_PIN = A0;
DFRobot_SSD1306_I2C oled;

void setup() {
  Serial.begin(9600);
  oled.begin(0x3c);
  oled.fillScreen(0);
  oled.setCursorLine(1);
  oled.printLine("Light sensor");
}

void loop() {
  int lightValue = analogRead(LIGHT_PIN);
  oled.setCursorLine(2);
  oled.printLine(lightValue);
  Serial.println(lightValue);
  delay(200);
}
