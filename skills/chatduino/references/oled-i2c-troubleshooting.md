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

`DFRobot_SSD1306_I2C` 在 Nano、Uno、星辰板这类 ATmega328P 板上可以用于已经验证过的英文状态页，但它的 `printLine("中文")` 路线依赖 ESP32 Flash `0x400000` 的外置字库；AVR 没有这块字库，因此不能直接显示中文，常见结果是整行空白。不要把“英文显示正常”推广成“该库支持 AVR 中文”。

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

另一条可控路线是用 `Wire` 直接写 SSD1306 页寻址数据，并把当前项目实际需要的 16×16 中文点阵放在 `PROGMEM`。同一程序只能让一套驱动负责寻址方式和旋转方向：选择 raw `Wire` 后，不要再先调用 `DFRobot_SSD1306_I2C.begin()`，否则两个初始化策略混用可能造成错位或乱码。无论选择 U8g2 子集还是 `PROGMEM` 点阵，都必须真实编译检查 Flash/RAM，并由用户肉眼确认目标文字。

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

这个目标的中文不是从代码里的点阵数组读取，而是从 Flash 地址 `0x400000` 读取 `Noto_Sans_CJK_SC_Light16.xbf`。ChatMaker 和 Mind+ 的正确流程都是先读 `0x400000` 的 4 字节标记：若为 `GUIX`，保留已有字库；若不是，才把经过 SHA-256 校验的字库与应用固件一起写入。ChatMaker 的上传结果会分别返回 `font_checked` 与 `font_asset_written`，前者不能代替肉眼显示验收。

```text
1. 先运行 prepare-environment，让托管环境从 Mind+ 国内官方设备包取得并校验字库；已有 Mind+ 1.8/2 也可复用其官方字库。
2. 确认板卡身份和唯一有线端口后上传。
3. 首次缺字库时会多写约 1.9 MB；已有 GUIX 标记时不会重复写。
4. 亲眼看到外接 OLED 的目标中文后，才能标记中文显示通过。
```

若字库、esptool、bootloader 或 partitions 文件缺失/哈希不符，ChatMaker 会在应用烧录前停止并提示重新准备环境，不会把“应用上传成功”伪装成“中文已可用”。`font_checked`、`font_asset_written`、应用上传和中文肉眼显示必须分开记录；U8g2 不是这条链路的修复方案。

## 默认显示习惯

- 字库已经验证时，屏幕提示优先使用简短、清楚的中文；字库尚未验证时保留明确的英文兼容文本，并说明原因，不假装中文已经可用。
- 固定欢迎页只在 `setup()` 中绘制一次。动态数值只在内容变化时更新，或使用适中的固定间隔刷新。
- 不要在高速 `loop()` 中反复清空并重画整屏。必须更新时优先只改变化区域，避免明显闪烁。
