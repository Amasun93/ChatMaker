const uint8_t LIGHT_PIN = A0;
const uint8_t LED_PIN = 6;
const int DARK_THRESHOLD = 450;

void setup() {
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);
  Serial.begin(9600);
  Serial.println("LIGHT_LED_READY");
}

void loop() {
  int lightValue = analogRead(LIGHT_PIN);
  bool isDark = lightValue < DARK_THRESHOLD;
  digitalWrite(LED_PIN, isDark ? HIGH : LOW);
  Serial.println(lightValue);
  delay(100);
}
