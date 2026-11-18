// Waveshare ESP32-S3-Touch-LCD-2.8 V2 only. Raw ST7789 + QMI8658, no LVGL loop.
#include <Display_ST7789.h>
#include <Gyro_QMI8658.h>
#include <algorithm>

constexpr int width = LCD_WIDTH;
constexpr int height = 192;
constexpr int top = (LCD_HEIGHT - height) / 2;
constexpr int radius = 9;
constexpr uint16_t background = 0x6108;  // RGB565 values in SPI byte order.
constexpr uint16_t dot = 0xF407;
constexpr uint32_t framePeriodUs = 33000;
constexpr int historySize = 120;
static uint16_t frame[width * height];
static uint32_t frameIntervals[historySize];
static uint32_t lastFrame;
static int nextSample;
static int samples;
static int x = width / 2;
static int y = height / 2;
static bool imuAck;
static bool imuReadOk;

static int16_t readAxis(const uint8_t *bytes) {
  return static_cast<int16_t>(uint16_t(bytes[0]) | (uint16_t(bytes[1]) << 8));
}

static bool readTilt() {
  // Keep the time-sensitive path quiet even if I2C stops responding.
  Wire.beginTransmission(QMI8658_L_SLAVE_ADDRESS);
  Wire.write(QMI8658_AX_L);
  if (Wire.endTransmission(false) != 0) return false;
  constexpr uint8_t count = 4;
  if (Wire.requestFrom(uint8_t(QMI8658_L_SLAVE_ADDRESS), count) != count) return false;
  uint8_t data[count];
  if (Wire.readBytes(data, count) != count) return false;
  const int ax = readAxis(data);
  const int ay = readAxis(data + 2);
  x = constrain(width / 2 + ay / 72, radius, width - radius - 1);
  y = constrain(height / 2 - ax / 72, radius, height - radius - 1);
  return true;
}

static void paint() {
  std::fill_n(frame, width * height, background);
  for (int dy = -radius; dy <= radius; ++dy) {
    for (int dx = -radius; dx <= radius; ++dx) {
      if (dx * dx + dy * dy <= radius * radius) {
        frame[(y + dy) * width + x + dx] = imuReadOk ? dot : 0x00f8;
      }
    }
  }
  // Submit one fully composed region. This is a rendering baseline.
  LCD_addWindow(0, top, width - 1, top + height - 1, frame);
}

static void diagnostics() {
  if (!Serial.available() || Serial.read() != 'D') return;
  uint32_t peak = 0;
  for (int i = 0; i < samples; ++i) {
    peak = std::max(peak, frameIntervals[i]);
  }
  Serial.printf("TILT_DOT imu_ack=%d imu_read=%d frames=%d peak_us=%lu\n",
                imuAck, imuReadOk, samples, static_cast<unsigned long>(peak));
}

void setup() {
  Serial.begin(115200);
  Serial.setTxTimeoutMs(8);
  pinMode(7, OUTPUT);
  digitalWrite(7, HIGH);
  Backlight_Init();
  LCD_Init();
  I2C_Init();
  Wire.setClock(400000);
  Wire.setTimeOut(5);
  Wire.beginTransmission(QMI8658_L_SLAVE_ADDRESS);
  imuAck = Wire.endTransmission() == 0;
  if (imuAck) QMI8658_Init();
  std::fill_n(frame, width * height, background);
  LCD_addWindow(0, 0, width - 1, top - 1, frame);
  LCD_addWindow(0, top + height, width - 1, LCD_HEIGHT - 1, frame);
  lastFrame = micros();
}

void loop() {
  const uint32_t now = micros();
  const uint32_t interval = now - lastFrame;
  if (interval >= framePeriodUs) {
    lastFrame = now;
    frameIntervals[nextSample] = interval;
    nextSample = (nextSample + 1) % historySize;
    if (samples < historySize) ++samples;
    imuReadOk = imuAck && readTilt();
    paint();
  }
  diagnostics();
  delay(1);
}
