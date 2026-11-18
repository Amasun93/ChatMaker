#include <Wire.h>
#include <avr/pgmspace.h>

// UNO R3 with a SSD1306 128 x 64 I2C OLED at address 0x3c.
// Button on D2 to GND, with the board's internal pull-up.
constexpr uint8_t buttonPin = 2;
constexpr uint8_t oledAddress = 0x3c;
constexpr uint8_t transferSize = 16;

enum class Message : uint8_t { Hello, Goodbye };

// Four hand-drawn 16 x 16 glyphs stored in flash. Each row starts at the high bit.
const uint16_t glyphs[4][16] PROGMEM = {
  { // 你
    0x0000, 0x0440, 0x0440, 0x0880, 0x08fe, 0x1112, 0x3014, 0x5014,
    0x1094, 0x1112, 0x1112, 0x1211, 0x1411, 0x1010, 0x10e0, 0x0000,
  },
  { // 好
    0x0000, 0x0800, 0x08fe, 0x1004, 0x1008, 0x1010, 0x7f10, 0x2210,
    0x23ff, 0x1410, 0x0c10, 0x0a10, 0x0910, 0x1010, 0x60e0, 0x0000,
  },
  { // 再
    0x0000, 0x0000, 0x3ffe, 0x0080, 0x0080, 0x0ff8, 0x0888, 0x0888,
    0x0ff8, 0x0888, 0x0888, 0x7fff, 0x0808, 0x0808, 0x0830, 0x0000,
  },
  { // 见
    0x0000, 0x0000, 0x0ff8, 0x0808, 0x0808, 0x0888, 0x0888, 0x0888,
    0x08a8, 0x08a8, 0x0928, 0x0921, 0x0221, 0x0c21, 0x301e, 0x0000,
  },
};

void setWindow(uint8_t left, uint8_t right, uint8_t firstPage, uint8_t lastPage) {
  const uint8_t commands[] = {0x21, left, right, 0x22, firstPage, lastPage};
  Wire.beginTransmission(oledAddress);
  Wire.write(0x00);  // Commands follow.
  Wire.write(commands, sizeof(commands));
  Wire.endTransmission();
}

void beginPixels() {
  Wire.beginTransmission(oledAddress);
  Wire.write(0x40);  // Display RAM bytes follow.
}

void clearDisplay() {
  setWindow(0, 127, 0, 7);
  for (uint8_t block = 0; block < 64; block++) {
    beginPixels();
    for (uint8_t i = 0; i < transferSize; i++) Wire.write(uint8_t(0));
    Wire.endTransmission();
  }
}

void startDisplay() {
  const uint8_t configure[] = {
    0xae,              // Display off during setup.
    0xd5, 0x80,        // Display clock.
    0xa8, 0x3f,        // 64 rows.
    0xd3, 0x00, 0x40,  // No vertical offset.
    0x8d, 0x14,        // Enable the OLED charge pump.
    0x20, 0x00,        // Horizontal RAM addressing.
    0xa1, 0xc8,        // Module orientation.
    0xda, 0x12, 0x81, 0xcf, 0xd9, 0xf1, 0xdb, 0x40,
    0xa4, 0xa6,        // Show RAM pixels with normal polarity.
  };
  Wire.beginTransmission(oledAddress);
  Wire.write(0x00);
  Wire.write(configure, sizeof(configure));
  Wire.endTransmission();
  clearDisplay();
  Wire.beginTransmission(oledAddress);
  Wire.write(0x00);
  Wire.write(0xaf);    // Display on.
  Wire.endTransmission();
}

uint8_t glyphStrip(uint8_t glyph, uint8_t x, uint8_t page) {
  uint8_t pixels = 0;
  for (uint8_t y = 0; y < 8; y++) {
    const uint16_t row = pgm_read_word(&glyphs[glyph][(page * 8 + y) / 2]);
    if (row & (0x8000u >> (x / 2))) pixels |= 1 << y;
  }
  return pixels;
}

void showMessage(Message message) {
  const uint8_t firstGlyph = message == Message::Hello ? 0 : 2;
  // Center two 32 x 32 glyphs and leave a four-pixel gap.
  setWindow(30, 97, 2, 5);
  for (uint8_t page = 0; page < 4; page++) {
    for (uint8_t offset = 0; offset < 68; offset += transferSize) {
      beginPixels();
      for (uint8_t x = offset; x < 68 && x < offset + transferSize; x++) {
        uint8_t pixels = 0;
        if (x < 32) pixels = glyphStrip(firstGlyph, x, page);
        else if (x >= 36) pixels = glyphStrip(firstGlyph + 1, x - 36, page);
        Wire.write(pixels);
      }
      Wire.endTransmission();
    }
  }
}

bool lastPressed;

void setup() {
  pinMode(buttonPin, INPUT_PULLUP);
  Wire.begin();
  delay(20);
  startDisplay();
  lastPressed = digitalRead(buttonPin) == LOW;
  showMessage(lastPressed ? Message::Hello : Message::Goodbye);
}

void loop() {
  const bool pressed = digitalRead(buttonPin) == LOW;
  if (lastPressed == pressed) return;
  lastPressed = pressed;
  showMessage(pressed ? Message::Hello : Message::Goodbye);
}
