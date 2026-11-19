// Salt Lake Weather Patrol, single-plane motion test.
// Waveshare ESP32-S3-Touch-LCD-2.8 V2, using ChatMaker's prepared board libraries.
#include <Arduino.h>
#include <Display_ST7789.h>
#include <Gyro_QMI8658.h>
#include <algorithm>
#include <cmath>

// The pinned Waveshare driver exposes these functions in its implementation.
void LCD_WriteCommand(uint8_t command);
void LCD_WriteData(uint8_t data);

namespace {
constexpr int width = 160;
constexpr int height = 120;
constexpr int lcdWidth = 2 * width;
constexpr int lcdHeight = 2 * height;
constexpr int maxCells = 420;
constexpr int historyLength = 180;
constexpr int calibrationFrames = 28;
constexpr float rollLimit = 0.70f;
constexpr float gravityPerCount = 4.0f / 32768.0f;  // Vendor's QMI8658 range is ±4 g.

// Waveshare initializes ST7789 RAMCTRL to 00 E8, selecting little-endian
// RGB565. SPI writes the ESP32's native little-endian buffer directly.
constexpr uint16_t rgb(int red, int green, int blue) {
  return uint16_t(((red & 0xF8) << 8) | ((green & 0xFC) << 3) | (blue >> 3));
}
static_assert(rgb(255, 0, 0) == 0xF800 && rgb(0, 255, 0) == 0x07E0 &&
              rgb(0, 0, 255) == 0x001F);

constexpr auto white = rgb(250, 233, 189);
constexpr auto shadow = rgb(164, 139, 108);
constexpr auto orange = rgb(225, 130, 74);
constexpr auto copper = rgb(172, 83, 53);
constexpr auto deepTeal = rgb(33, 53, 55);
constexpr auto teal = rgb(73, 117, 115);
constexpr auto lightTeal = rgb(136, 183, 164);
constexpr auto lake = rgb(93, 147, 139);
constexpr auto waterLine = rgb(111, 164, 153);
constexpr auto shore = rgb(173, 191, 151);
constexpr auto cream = rgb(238, 205, 143);
constexpr auto signal = rgb(254, 177, 120);

static uint16_t pixels[width * height];
alignas(4) static uint16_t lcdPixels[lcdWidth * lcdHeight];

struct Cell {
  int8_t x, y, z;
  uint16_t color;
};
struct Projected {
  float depth;
  int16_t x, y;
  uint8_t size;
  uint16_t color;
};
static Cell cells[maxCells];
static Projected projected[maxCells];
static int cellCount;

struct AccelSample {
  float x, y, z;
};
struct FrameSample {
  uint32_t frameUs, imuUs, drawUs, lcdUs;
  int16_t rollTenths, pitchTenths;
};
static FrameSample history[historyLength];
static int sampleCount, nextSample;
static uint32_t imuErrors, previousFrame, fpsEpoch, fpsFrames;
static uint32_t frameP95Scratch[historyLength];
static int displayFps;
static int neutralSamples;
static float neutralX, neutralY;
static AccelSample lastAccel{};
static float roll, pitch, heading, distanceFlown;
static bool imuPresent, imuReadOk, calibrated;

static void span(int x0, int x1, int y, uint16_t color) {
  if (y < 0 || y >= height || x0 >= width || x1 <= 0 || x1 <= x0) return;
  uint16_t *row = pixels + y * width;
  std::fill(row + std::max(0, x0), row + std::min(width, x1), color);
}

static void rectangle(int x, int y, int w, int h, uint16_t color) {
  for (int line = std::max(0, y); line < std::min(height, y + h); ++line) {
    span(x, x + w, line, color);
  }
}

// Three-bit rows. The display uses only these words and the frame-rate digits.
struct Glyph { char letter; uint8_t rows[5]; };
constexpr Glyph glyphs[] = {
  {'0',{7,5,5,5,7}}, {'1',{2,6,2,2,7}}, {'2',{7,1,7,4,7}},
  {'3',{7,1,7,1,7}}, {'4',{5,5,7,1,1}}, {'5',{7,4,7,1,7}},
  {'6',{7,4,7,5,7}}, {'7',{7,1,2,2,2}}, {'8',{7,5,7,5,7}},
  {'9',{7,5,7,1,7}}, {'A',{2,5,7,5,5}}, {'D',{6,5,5,5,6}},
  {'E',{7,4,6,4,7}}, {'F',{7,4,6,4,4}}, {'H',{5,5,7,5,5}},
  {'I',{7,2,2,2,7}}, {'K',{5,5,6,5,5}}, {'L',{4,4,4,4,7}},
  {'M',{5,7,7,5,5}}, {'N',{5,7,7,7,5}}, {'O',{7,5,5,5,7}},
  {'P',{7,5,7,4,4}}, {'S',{7,4,7,1,7}}, {'T',{7,2,2,2,2}},
  {'U',{5,5,5,5,7}}, {'V',{5,5,5,5,2}}, {'-',{0,0,7,0,0}},
};

static void label(int x, int y, const char *text, uint16_t color) {
  for (; *text; ++text, x += 4) {
    for (const auto &glyph : glyphs) {
      if (glyph.letter != *text) continue;
      for (int row = 0; row < 5; ++row) {
        for (int column = 0; column < 3; ++column) {
          if (glyph.rows[row] & (4 >> column)) span(x + column, x + column + 1, y + row, color);
        }
      }
      break;
    }
  }
}

static void prepareGlider() {
  for (int y = -1; y <= 3; ++y) {
    for (int z = -11; z <= 12; ++z) {
      for (int x = -11; x <= 11; ++x) {
        const int side = std::abs(x);
        const int halfBody = z < -4 ? 1 : std::min(2, (12 - z) / 2);
        const bool body = y < 1 && side <= halfBody - int(y < 0 && halfBody > 1);
        const bool wing = y == 0 && z <= 5 - side / 2 && z >= -2 - side / 4;
        const bool stabilizer = y == 1 && side <= 3 && z >= -11 && z <= -8 - side / 2;
        const bool fin = y >= 1 && side == 0 && z >= -11 && z <= -5 - y * 2;
        const bool cockpit = y >= 1 && y <= 2 && side <= 2 - y && z >= 1 && z <= 7 - y;
        if (!(body || wing || stabilizer || fin || cockpit)) continue;
        uint16_t color = y < 0 ? shadow : white;
        if (wing && z == -2 - side / 4) color = shadow;
        if (wing && side >= 7) color = side >= 10 ? orange : copper;
        if (stabilizer) color = cream;
        if (fin) color = y == 3 ? orange : copper;
        if (cockpit) color = y == 2 ? lightTeal : deepTeal;
        if (cellCount < maxCells) cells[cellCount++] = {int8_t(x), int8_t(y), int8_t(z), color};
      }
    }
  }
}

static uint32_t scatter(uint32_t key) {
  key ^= key >> 16;
  key *= 0x7FEB352Du;
  key ^= key >> 15;
  return key;
}

static void landscape() {
  const int horizon = 42 + int(pitch * 15.0f);
  const int drift = int(heading * 24.0f);
  for (int y = 0; y < horizon; ++y) {
    const int light = (y * 90) / horizon;
    span(0, width, y, rgb(93 + light, 132 + light * 2 / 3, 129 + light / 5));
  }
  const int sunX = 123 - drift / 5;
  for (int y = -9; y <= 9; ++y) {
    const int half = int(sqrtf(float(81 - y * y)));
    span(sunX - half, sunX + half + 1, 20 + y, y < 3 ? cream : rgb(227, 174, 109));
  }
  for (uint32_t i = 0; i < 8; ++i) {
    const auto value = scatter(i + 40);
    const int x = int(value % 156) - drift / 4;
    span(x, x + 7 + int((value >> 8) % 19), 10 + int((value >> 16) % 21), rgb(200, 193, 150));
  }
  for (int x = 0; x < width; ++x) {
    const float position = float(x + drift);
    const int far = horizon - 6 - int(5.0f * sinf(position * 0.067f) + 2.4f * sinf(position * 0.18f));
    const int near = horizon - 2 - int(3.0f * sinf(position * 0.073f + 2.1f));
    rectangle(x, far, 1, 1 + horizon - far, rgb(137, 147, 123));
    rectangle(x, near, 1, 1 + horizon - near, rgb(105, 128, 116));
  }
  for (int y = horizon; y < height; ++y) {
    const int depth = y - horizon;
    const float world = distanceFlown + 1450.0f / float(depth + 5);
    const int coast = 91 + depth / 2 - drift + int(5.0f * sinf(world * 0.038f));
    const auto sand = rgb(210 + depth / 9, 193 - depth / 4, 151 - depth / 3);
    span(0, width, y, sand);
    span(coast - 4, width, y, shore);
    span(coast, width, y, (int(world * 0.38f) & 3) == 0 ? waterLine : lake);
  }
  // Flecks are anchored to repeated rows in world space, so they accelerate toward the viewer.
  const int startRow = int(distanceFlown / 10.0f);
  for (int row = startRow + 25; row >= startRow + 2; --row) {
    const float depth = float(row * 10) - distanceFlown;
    const float scale = 88.0f / depth;
    const int y = horizon + int(1120.0f / depth);
    if (y >= height) continue;
    for (int column = -6; column <= 6; ++column) {
      const auto grain = scatter(uint32_t(row + 1) * 7933u + uint32_t(column + 6));
      const int worldX = column * 13 + int(grain % 11) - 5;
      if (worldX > 23) continue;
      const int x = width / 2 + int(worldX * scale) - drift;
      const int length = std::max(1, int(1.8f * scale));
      span(x, x + length, y, (grain & 8) ? rgb(239, 221, 175) : rgb(170, 155, 117));
    }
  }
}

static void glider() {
  const float rollSin = -sinf(roll);
  const float rollCos = cosf(roll);
  const float pitchSin = sinf(pitch * 0.42f);
  const float pitchCos = cosf(pitch * 0.42f);
  const float yawSin = sinf(roll * 0.38f + 0.16f);
  const float yawCos = cosf(roll * 0.38f + 0.16f);
  const int centerX = width / 2 + int(roll * 22.0f);
  const int centerY = 80 + int(pitch * 13.0f);
  int count = 0;
  for (int i = 0; i < cellCount; ++i) {
    const auto &cell = cells[i];
    const float x = cell.x * rollCos - cell.y * rollSin;
    const float bankHeight = cell.x * rollSin + cell.y * rollCos;
    const float y = bankHeight * pitchCos + cell.z * pitchSin;
    const float forward = cell.z * pitchCos - bankHeight * pitchSin;
    const float side = x * yawCos + forward * yawSin;
    const float depth = 34.0f + forward * yawCos - x * yawSin;
    const float scale = 63.0f / depth;
    const int screenX = centerX + int(lroundf(side * scale));
    const int screenY = centerY - int(lroundf((y + (depth - 34.0f) * 0.37f) * scale));
    projected[count++] = {depth, int16_t(screenX), int16_t(screenY),
                           uint8_t(ceilf(scale * 1.15f)), cell.color};
  }
  std::sort(projected, projected + count,
            [](const Projected &a, const Projected &b) { return a.depth > b.depth; });
  for (int i = 0; i < count; ++i) {
    const auto &point = projected[i];
    rectangle(point.x - point.size / 2, point.y - point.size / 2, point.size, point.size, point.color);
  }
}

static void compose() {
  landscape();
  glider();
  rectangle(4, 4, 43, 11, deepTeal);
  label(7, 7, "SALT LAKE", white);
  rectangle(122, 4, 34, 11, deepTeal);
  char rate[9];
  snprintf(rate, sizeof rate, "FPS %02d", displayFps);
  label(126, 7, rate, lightTeal);
  if (!imuReadOk || !calibrated) {
    rectangle(57, 104, 46, 11, deepTeal);
    const char *state = imuReadOk ? "HOLD LEVEL" : "IMU FAIL";
    label(60, 107, state, imuReadOk ? white : signal);
  }
  for (int y = 0; y < height; ++y) {
    const auto *source = pixels + y * width;
    auto *first = lcdPixels + y * 2 * lcdWidth;
    auto *second = first + lcdWidth;
    for (int x = 0; x < width; ++x) {
      const auto color = source[x];
      first[2 * x] = first[2 * x + 1] = color;
      second[2 * x] = second[2 * x + 1] = color;
    }
  }
}

static int16_t readInt16(const uint8_t *bytes) {
  return int16_t(uint16_t(bytes[0]) | uint16_t(bytes[1]) << 8);
}

static bool readAccelerometer(AccelSample &sample) {
  Wire.beginTransmission(QMI8658_L_SLAVE_ADDRESS);
  Wire.write(QMI8658_AX_L);
  if (Wire.endTransmission(false) != 0) return false;
  constexpr uint8_t size = 6;
  if (Wire.requestFrom(uint8_t(QMI8658_L_SLAVE_ADDRESS), size) != size) return false;
  uint8_t bytes[size];
  if (Wire.readBytes(bytes, size) != size) return false;
  sample = {readInt16(bytes) * gravityPerCount, readInt16(bytes + 2) * gravityPerCount,
            readInt16(bytes + 4) * gravityPerCount};
  return true;
}

static float inputAxis(float raw) {
  const float magnitude = fabsf(raw);
  if (magnitude < 0.025f) return 0.0f;
  return std::clamp((magnitude - 0.025f) * 2.35f, 0.0f, 1.0f) * (raw < 0 ? -1.0f : 1.0f);
}

static void updateFlight(float dt) {
  float targetRoll = 0.0f;
  float targetPitch = 0.0f;
  if (imuReadOk && neutralSamples < calibrationFrames) {
    neutralX += lastAccel.x;
    neutralY += lastAccel.y;
    if (++neutralSamples == calibrationFrames) {
      neutralX /= calibrationFrames;
      neutralY /= calibrationFrames;
      calibrated = true;
    }
  } else if (imuReadOk && calibrated) {
    // With the panel in landscape, lowering its right edge reduces sensor X.
    targetRoll = inputAxis(neutralX - lastAccel.x) * rollLimit;
    targetPitch = inputAxis(neutralY - lastAccel.y) * 0.55f;
  }
  const float response = std::min(1.0f, dt * 11.5f);
  roll += (targetRoll - roll) * response;
  pitch += (targetPitch - pitch) * response;
  heading += (roll - heading) * std::min(1.0f, dt * 3.4f);
  distanceFlown += dt * 30.0f;
  if (distanceFlown > 30000.0f) distanceFlown -= 30000.0f;
}

static void printDiagnostics() {
  uint64_t totalFrame = 0, totalImu = 0, totalDraw = 0, totalLCD = 0;
  int minRoll = 0, maxRoll = 0, minPitch = 0, maxPitch = 0;
  for (int i = 0; i < sampleCount; ++i) {
    const auto &sample = history[i];
    frameP95Scratch[i] = sample.frameUs;
    totalFrame += sample.frameUs;
    totalImu += sample.imuUs;
    totalDraw += sample.drawUs;
    totalLCD += sample.lcdUs;
    minRoll = std::min(minRoll, int(sample.rollTenths));
    maxRoll = std::max(maxRoll, int(sample.rollTenths));
    minPitch = std::min(minPitch, int(sample.pitchTenths));
    maxPitch = std::max(maxPitch, int(sample.pitchTenths));
  }
  std::sort(frameP95Scratch, frameP95Scratch + sampleCount);
  const auto p95 = sampleCount ? frameP95Scratch[(sampleCount * 95 + 99) / 100 - 1] : 0;
  const auto peak = sampleCount ? frameP95Scratch[sampleCount - 1] : 0;
  const float count = std::max(1, sampleCount);
  const float fps = totalFrame ? sampleCount * 1000000.0f / float(totalFrame) : 0.0f;
  Serial.printf("SALT_S3 build=02 imu=%d calibrated=%d errors=%lu n=%d fps=%.2f frame_ms=%.2f "
                "p95_ms=%.2f peak_ms=%.2f imu_ms=%.2f draw_ms=%.2f lcd_ms=%.2f "
                "roll_deg=%.1f..%.1f pitch_deg=%.1f..%.1f acc=%.3f,%.3f,%.3f\n",
                imuReadOk, calibrated, static_cast<unsigned long>(imuErrors), sampleCount, fps,
                totalFrame / count / 1000.0f, p95 / 1000.0f, peak / 1000.0f,
                totalImu / count / 1000.0f, totalDraw / count / 1000.0f, totalLCD / count / 1000.0f,
                minRoll / 10.0f, maxRoll / 10.0f, minPitch / 10.0f, maxPitch / 10.0f,
                lastAccel.x, lastAccel.y, lastAccel.z);
}

static void serialCommand() {
  if (!Serial.available()) return;
  const int command = Serial.read();
  if (command == '?' || command == 'D') {
    printDiagnostics();
    // Exclude time spent formatting and transmitting this on-demand report.
    previousFrame = 0;
  } else if (command == 'C') {
    neutralX = neutralY = 0.0f;
    neutralSamples = 0;
    calibrated = false;
    sampleCount = nextSample = 0;
    previousFrame = 0;
  }
}
}  // namespace

void setup() {
  Serial.begin(115200);
  Serial.setTxTimeoutMs(8);
  pinMode(7, OUTPUT);
  digitalWrite(7, HIGH);
  Backlight_Init();
  LCD_Init();
  LCD_WriteCommand(0x36);
  LCD_WriteData(0x60);  // Exchange row/column and mirror X for a 320 × 240 landscape window.
  I2C_Init();
  Wire.setClock(400000);
  Wire.setTimeOut(5);
  Wire.beginTransmission(QMI8658_L_SLAVE_ADDRESS);
  imuPresent = Wire.endTransmission() == 0;
  if (imuPresent) QMI8658_Init();
  prepareGlider();
  fpsEpoch = micros();
}

void loop() {
  serialCommand();
  const uint32_t start = micros();
  const uint32_t interval = previousFrame ? start - previousFrame : 0;
  previousFrame = start;
  const float dt = interval ? std::min(0.05f, interval / 1000000.0f) : 0.02f;
  imuReadOk = imuPresent && readAccelerometer(lastAccel);
  if (!imuReadOk) ++imuErrors;
  const uint32_t afterIMU = micros();
  updateFlight(dt);
  compose();
  const uint32_t afterDraw = micros();
  // Compose the whole frame first, then send a single contiguous LCD region.
  LCD_addWindow(0, 0, lcdWidth - 1, lcdHeight - 1, lcdPixels);
  const uint32_t afterLCD = micros();
  if (interval) {
    history[nextSample] = {interval, afterIMU - start, afterDraw - afterIMU, afterLCD - afterDraw,
                           int16_t(lroundf(roll * 572.9578f)), int16_t(lroundf(pitch * 572.9578f))};
    nextSample = (nextSample + 1) % historyLength;
    if (sampleCount < historyLength) ++sampleCount;
  }
  ++fpsFrames;
  const uint32_t elapsed = afterLCD - fpsEpoch;
  if (elapsed >= 1000000) {
    displayFps = int((fpsFrames * 1000000u + elapsed / 2) / elapsed);
    fpsFrames = 0;
    fpsEpoch = afterLCD;
  }
  delay(1);
}
