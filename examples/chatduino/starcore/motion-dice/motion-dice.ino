#include <MPython.h>

// 星核板 v4.2.2 板载 QMI8658 + 外接 1.3 寸 I2C OLED + 板载无源蜂鸣器。
// OLED 接 P19(SCL)、P20(SDA)、3V3、GND；不要把 display 当成星核板自带屏幕。
const int OLED_ADDRESS = 0x3C;
const float SHAKE_THRESHOLD_MG = 1350.0f;
const unsigned long ROLL_COOLDOWN_MS = 900;

unsigned long lastRollAt = 0;
unsigned long lastTelemetryAt = 0;
int diceValue = 1;

void showDice(const char* title, int value) {
  display.setCursorLine(1);
  display.printLine(title);
  char valueLine[18];
  snprintf(valueLine, sizeof(valueLine), "DICE: %d", value);
  display.setCursorLine(2);
  display.printLine(valueLine);
}

void rollDice(const char* reason) {
  diceValue = random(1, 7);
  showDice("SHAKE DICE", diceValue);
  buzz.freq(880, 90);
  Serial.printf("DICE_ROLL:{\"value\":%d,\"reason\":\"%s\"}\n", diceValue, reason);
  lastRollAt = millis();
}

void setup() {
  Serial.begin(115200);
  mPython.begin();
  display.begin(OLED_ADDRESS);
  buzz.off();
  randomSeed((unsigned long)(accelerometer.getStrength() * 1000.0f) + micros());
  showDice("SHAKE DICE", diceValue);
  Serial.println("STARCORE_MOTION_DICE_READY");
}

void loop() {
  const float strength = accelerometer.getStrength();
  if (millis() - lastTelemetryAt >= 120) {
    Serial.printf("ACCEL:{\"x_mg\":%.0f,\"y_mg\":%.0f,\"z_mg\":%.0f,\"strength_mg\":%.0f}\n",
                  accelerometer.getX(), accelerometer.getY(),
                  accelerometer.getZ(), strength);
    lastTelemetryAt = millis();
  }
  const bool buttonRoll = buttonA.isPressed() || buttonB.isPressed();
  const bool cooldownReady = millis() - lastRollAt >= ROLL_COOLDOWN_MS;
  if (cooldownReady && (strength >= SHAKE_THRESHOLD_MG || buttonRoll)) {
    rollDice(buttonRoll ? "button" : "shake");
  }
  delay(30);
}
