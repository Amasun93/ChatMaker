const uint8_t TRIG_PIN = 7;
const uint8_t ECHO_PIN = 8;
const uint8_t BUZZER_PIN = 6;
const float ALARM_DISTANCE_CM = 20.0;

float readDistanceCm() {
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);
  unsigned long duration = pulseIn(ECHO_PIN, HIGH, 30000UL);
  if (duration == 0) return -1.0;
  return duration * 0.0343 / 2.0;
}

void setup() {
  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);
  pinMode(BUZZER_PIN, OUTPUT);
  digitalWrite(BUZZER_PIN, LOW);
  Serial.begin(9600);
  Serial.println("ULTRASONIC_READY");
}

void loop() {
  float distance = readDistanceCm();
  bool alarm = distance > 0 && distance < ALARM_DISTANCE_CM;
  digitalWrite(BUZZER_PIN, alarm ? HIGH : LOW);
  Serial.println(distance);
  delay(100);
}
