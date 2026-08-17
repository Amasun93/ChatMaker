#include <MPython.h>
#include <DFRobot_LiquidCrystal_I2C.h>

DFRobot_LiquidCrystal_I2C lcd;

void setup() {
  lcd.begin(0x27);  // Only after confirming the address and safe I2C voltage.
  lcd.print(0, 0, "StarCore ready");
  lcd.print(0, 1, "LCD1602 I2C");
}

void loop() {}
