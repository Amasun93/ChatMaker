const uint8_t POTENTIOMETER_PIN = A0;
const uint8_t LED_PIN = 6;

void setup() {
  pinMode(LED_PIN, OUTPUT);
  analogWrite(LED_PIN, 0);
  Serial.begin(9600);
  Serial.println("POTENTIOMETER_LED_READY");
}

void loop() {
  int rawValue = analogRead(POTENTIOMETER_PIN);
  int brightness = map(rawValue, 0, 1023, 0, 255);
  analogWrite(LED_PIN, brightness);
  Serial.println(rawValue);
  delay(50);
}
