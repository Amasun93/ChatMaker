#include <MPython.h>

// 可调参数：若已确认当前模块地址是 0x3D，可在这里修改。
const int OLED_ADDRESS = 0x3C;

void setup() {
  Serial.begin(115200);
  display.begin(OLED_ADDRESS);
  display.setCursorLine(1);
  display.printLine("Starcore ready");
  display.setCursorLine(2);
  display.printLine("ChatMaker");
  Serial.println("STARCORE_OLED_READY");
}

void loop() {
  // 固定欢迎画面不需要反复刷新。
}
