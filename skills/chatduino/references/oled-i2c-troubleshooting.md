# I2C 扫描、OLED 黑屏与中文显示

先确认是四针 `GND/VCC/SCL/SDA` 的 I2C 屏、具体控制器和供电范围。只凭“0.96 寸 OLED”不能判断 SSD1306、SH1106、地址或分辨率。

## 黑屏时按这个顺序

1. 断电核对 VCC、GND、SCL、SDA 和模块电压，不先换库。
2. 运行对应板卡的只读 I2C 扫描。常见 `0x3C/0x3D` 只是线索，以扫描结果为准。
3. 没扫到地址：检查供电、共地、插头方向、SDA/SCL 线序和接口电压。
4. 扫到地址但仍黑屏：再核对控制器、分辨率、驱动和地址。
5. 英文正常而中文异常：进入下面对应板卡的中文字库路线，不再重复改接线。

Nano/Uno 的 SDA=A4、SCL=A5，可用下面的完整只读扫描程序：

```cpp
#include <Wire.h>

void setup() {
  Serial.begin(115200);
  Wire.begin();
  Serial.println("AVR_I2C_SCAN_READY");
}

void loop() {
  int found = 0;
  for (uint8_t address = 1; address < 127; ++address) {
    Wire.beginTransmission(address);
    uint8_t error = Wire.endTransmission();
    if (error == 0) {
      Serial.print("I2C_FOUND=0x");
      if (address < 16) Serial.print('0');
      Serial.println(address, HEX);
      ++found;
    }
  }
  if (found == 0) Serial.println("I2C_NONE_FOUND");
  delay(3000);
}
```

星核板 IDMD-0021 整体插入匹配电压的空闲 I2C 接口，接口背后共用 P20(SDA)/P19(SCL)：

```cpp
#include <MPython.h>

void setup() {
  Serial.begin(115200);
  Wire.begin(P20, P19);  // SDA, SCL
  Serial.println("STARCORE_I2C_SCAN_READY");
}

void loop() {
  int found = 0;
  for (uint8_t address = 1; address < 127; ++address) {
    Wire.beginTransmission(address);
    uint8_t error = Wire.endTransmission();
    if (error == 0) {
      Serial.printf("I2C_FOUND=0x%02X\n", address);
      ++found;
    }
  }
  if (found == 0) Serial.println("I2C_NONE_FOUND");
  delay(3000);
}
```

扫描只读取地址，不写模块配置。它能区分“总线上看不到设备”和“看到了设备但显示仍异常”，不能证明控制器型号或显示效果。

## Nano / Uno 中文

确认普通 SSD1306 128×64 和地址后，可以选择 U8g2 的 UTF-8 字体路线。Nano/Uno 内存很小，优先用页面缓冲构造器（名称中的 `_1_`）和只覆盖目标文字的字体；不要塞入完整大型中文字库。

下面示例所用 `u8g2_font_unifont_t_chinese2` 只覆盖有限常用字。若目标文字不在其中，应选择或生成只包含本项目字符的 U8g2 字体子集，再真实编译检查 Flash/RAM。

```cpp
#include <Wire.h>
#include <U8g2lib.h>

U8G2_SSD1306_128X64_NONAME_1_HW_I2C oled(U8G2_R0, U8X8_PIN_NONE);

void setup() {
  oled.begin();
  oled.enableUTF8Print();
  oled.setFont(u8g2_font_unifont_t_chinese2);
}

void loop() {
  oled.firstPage();
  do {
    oled.setCursor(0, 24);
    oled.print("世界你好");
  } while (oled.nextPage());
  delay(1000);
}
```

这条 U8g2 路线只适用于 Nano、Uno 或其他已确认兼容的普通 SSD1306 项目，不能复制到下面的星核板路线。

## 星核板 IDMC-0001 + IDMD-0021 中文

星核板在 Mind+ 中使用“掌控板”Arduino/C++ 目标。代码只包含 `MPython.h`，使用它提供的全局 `display`；不要添加 U8g2、`DFRobot_SSD1306_I2C.h` 或第二个 SSD1306 对象。

```cpp
#include <MPython.h>

void setup() {
  Serial.begin(115200);
  display.begin(0x3C);
  display.setCursorLine(1);
  display.printLine("你好");
  Serial.println("STARCORE_OLED_CJK_APP_READY");
}

void loop() {}
```

这个目标的中文不是从代码里的点阵数组读取，而是从 Flash 地址 `0x400000` 读取 `Noto_Sans_CJK_SC_Light16.xbf`。正确流程是：

```text
1. 在 Mind+ 桌面版选择掌控板和上传模式。
2. 先做一个只显示“你好”的最小图形化项目。
3. 点击上传，让 Mind+ 检查并在需要时把 Noto_Sans_CJK_SC_Light16.xbf 写入 0x400000。
4. 第一次字库写入可能明显慢于普通程序上传，等待 Mind+ 完整结束。
5. 再上传 ChatMaker 生成的 MPython.h Arduino/C++ 程序。
6. 亲眼看到外接 OLED 的目标中文后，才能标记中文显示通过。
```

ChatMaker 当前的普通应用固件上传只保证应用程序，不保证写入 `0x400000` 字库。因此“编译通过”“应用上传完成”和“中文实物显示正确”必须分开记录。英文正常但中文为空白或乱码时，先补做上述 Mind+ 字库上传；U8g2 不是这条链路的修复方案。
