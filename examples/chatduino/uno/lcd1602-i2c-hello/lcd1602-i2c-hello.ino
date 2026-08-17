#include <Wire.h>
#include <LiquidCrystal_PCF8574.h>

LiquidCrystal_PCF8574 lcd(0x27);

void setup() {
  Wire.begin();
  lcd.begin(16, 2);
  lcd.setBacklight(255);
  lcd.setCursor(0, 0);
  lcd.print("ChatMaker ready");
  lcd.setCursor(0, 1);
  lcd.print("Uno + LCD1602 ");
}

void loop() {}
