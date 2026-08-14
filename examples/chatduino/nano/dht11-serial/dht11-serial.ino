#include <DFRobot_DHT.h>

const uint8_t DHT_PIN = 4;
DFRobot_DHT dht;

void setup() {
  Serial.begin(9600);
  dht.begin(DHT_PIN, DHT11);
  Serial.println("DHT11_READY");
}

void loop() {
  float temperature = dht.getTemperature();
  float humidity = dht.getHumidity();
  Serial.print("T=");
  Serial.print(temperature);
  Serial.print(" H=");
  Serial.println(humidity);
  delay(2000);
}
