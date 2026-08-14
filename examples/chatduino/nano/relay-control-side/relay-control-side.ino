const uint8_t RELAY_PIN = 7;
const uint8_t RELAY_ON_LEVEL = HIGH;
const uint8_t RELAY_OFF_LEVEL = LOW;

void setup() {
  pinMode(RELAY_PIN, OUTPUT);
  digitalWrite(RELAY_PIN, RELAY_OFF_LEVEL);
  Serial.begin(9600);
  Serial.println("RELAY_CONTROL_READY");
}

void loop() {
  digitalWrite(RELAY_PIN, RELAY_ON_LEVEL);
  Serial.println("RELAY_ON");
  delay(1000);

  digitalWrite(RELAY_PIN, RELAY_OFF_LEVEL);
  Serial.println("RELAY_OFF");
  delay(3000);
}
