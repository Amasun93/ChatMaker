const uint8_t TRIG_PIN = 25;
const uint8_t ECHO_PIN = 26;  // HC-SR04 ECHO must pass through a divider/level shifter.

float readDistanceCm() {
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);
  unsigned long duration = pulseIn(ECHO_PIN, HIGH, 30000UL);
  return duration == 0 ? -1.0 : duration * 0.0343 / 2.0;
}

void setup() {
  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);
  Serial.begin(115200);
}

void loop() {
  Serial.println(readDistanceCm());
  delay(100);
}
