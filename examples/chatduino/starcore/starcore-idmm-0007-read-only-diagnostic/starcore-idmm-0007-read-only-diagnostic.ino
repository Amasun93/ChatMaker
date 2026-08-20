#include <MPython.h>

// 9600 只是只读观察的起点，不代表已确认模块协议。
const unsigned long MONITOR_BAUD = 9600;
const int SERVO_BUS_RX = P26;  // 接 IDMM-0007 TXD。
const int SERVO_BUS_TX_UNUSED = P23;  // 诊断时模块 RXD 不接此脚。

HardwareSerial ServoBus(1);

void setup() {
  Serial.begin(115200);
  ServoBus.begin(MONITOR_BAUD, SERIAL_8N1, SERVO_BUS_RX, SERVO_BUS_TX_UNUSED);
  Serial.println("IDMM0007_RX_ONLY_READY");
  Serial.println("NO_MOTION_COMMAND_WILL_BE_SENT");
}

void loop() {
  while (ServoBus.available()) {
    uint8_t value = ServoBus.read();
    Serial.printf("%02X ", value);
  }
}
