#include <MPython.h>

void setup() {
  Serial.begin(115200);
  mPython.begin();

  // Static drawing: do not clear and redraw the whole OLED in loop().
  display.setCursorLine(1);
  display.printLine("掌控板就绪");
  display.setCursorLine(2);
  display.printLine("ChatMaker");

  Serial.println("MPYTHON_CLASSIC_CHINESE_STATUS_READY");
}

void loop() {
  Serial.println("MPYTHON_CLASSIC_HEARTBEAT");
  delay(1000);
}
