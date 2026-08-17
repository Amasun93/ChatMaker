#include <MPython.h>
#include <DFRobot_DHT.h>

// 可调参数：P0 是课堂默认数据脚；每次总线读取至少间隔 2500ms。
const int DHT_PIN = P0;
const unsigned long READ_INTERVAL_MS = 2500;

DFRobot_DHT dht;
unsigned long lastReadMs = 0;
bool readTemperatureNext = true;

void setup() {
  Serial.begin(115200);
  dht.begin(DHT_PIN, DHT11);
  Serial.println("STARCORE_DHT11_READY");
}

void loop() {
  unsigned long now = millis();
  if (now - lastReadMs < READ_INTERVAL_MS) return;
  lastReadMs = now;

  if (readTemperatureNext) {
    float temperature = dht.getTemperature();
    Serial.print(temperature == 0 ? "TEMP_CHECK=" : "TEMP_C=");
    Serial.println(temperature);
  } else {
    float humidity = dht.getHumidity();
    Serial.print(humidity == 0 ? "HUMIDITY_CHECK=" : "HUMIDITY_RH=");
    Serial.println(humidity);
  }
  readTemperatureNext = !readTemperatureNext;
}
