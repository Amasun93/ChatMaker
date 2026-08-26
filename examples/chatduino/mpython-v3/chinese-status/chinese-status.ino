#include <MPython.h>

void setup() {
  Serial.begin(115200);
  mPython.begin();

  // 只绘制一次，避免循环清屏造成明显闪烁。
  mPython.display.fillScreen(GUI_Black);
  mPython.display.drawTextCN(0, "掌控板3.0", GUI_White);
  mPython.display.drawTextCN(1, "ChatMaker就绪", GUI_Green);
  mPython.display.drawTextCN(2, "等待创意项目", GUI_Cyan);
  mPython.display.show();
  Serial.println("MPYTHON_V3_CHINESE_STATUS_READY");
}

void loop() {
  delay(1000);
}
