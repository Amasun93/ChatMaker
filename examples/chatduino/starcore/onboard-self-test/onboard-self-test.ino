#include <MPython.h>

void setup() {
  Serial.begin(115200);
  mPython.begin();
  buzz.off();
  delay(200);

  Serial.println("STARCORE_SELF_TEST_READY");
  buzz.freq(880);
  delay(120);
  buzz.off();
  Serial.println("BUZZER_COMMAND_COMPLETE");
}

void loop() {
  Serial.printf(
      "STARCORE_SELF_TEST:{\"button_a\":%d,\"button_b\":%d,"
      "\"x_mg\":%.0f,\"y_mg\":%.0f,\"z_mg\":%.0f,"
      "\"strength_mg\":%.0f}\n",
      buttonA.isPressed() ? 1 : 0,
      buttonB.isPressed() ? 1 : 0,
      accelerometer.getX(),
      accelerometer.getY(),
      accelerometer.getZ(),
      accelerometer.getStrength());
  delay(250);
}
