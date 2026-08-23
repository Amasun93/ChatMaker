#include <Arduino.h>
#include <Wire.h>

static bool addressPresent(uint8_t address) {
  Wire.beginTransmission(address);
  return Wire.endTransmission() == 0;
}

static int readRegister(uint8_t address, uint8_t reg) {
  Wire.beginTransmission(address);
  Wire.write(reg);
  if (Wire.endTransmission(false) != 0) return -1;
  if (Wire.requestFrom(address, static_cast<uint8_t>(1)) != 1) return -1;
  return Wire.read();
}

static void addDevice(String &json, bool &first, const char *name) {
  if (!first) json += ',';
  json += '"';
  json += name;
  json += '"';
  first = false;
}

void setup() {
  Serial.begin(115200);
  Wire.begin(23, 22);
  Wire.setClock(100000);
  delay(800);

  String devices = "[";
  bool first = true;

  // QMI8658C WHO_AM_I register 0x00 returns 0x05 in the reviewed Mind+ library.
  if (addressPresent(0x6B) && readRegister(0x6B, 0x00) == 0x05) {
    addDevice(devices, first, "qmi8658c");
  }
  // These addresses are reported as address clues only; no unreviewed chip name is invented.
  if (addressPresent(0x26)) addDevice(devices, first, "i2c-0x26");
  if (addressPresent(0x30)) addDevice(devices, first, "i2c-0x30");
  if (addressPresent(0x3C)) addDevice(devices, first, "oled-0x3c");
  devices += "]";

  Serial.print("CHATMAKER_PROBE:");
  Serial.print("{\"schema_version\":\"1.0\",\"chip_family\":\"esp32\",\"probe_devices\":");
  Serial.print(devices);
  Serial.println("}");
}

void loop() {
  delay(1000);
}
