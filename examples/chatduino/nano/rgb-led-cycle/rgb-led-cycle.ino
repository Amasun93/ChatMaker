const uint8_t RED_PIN = 9;
const uint8_t GREEN_PIN = 10;
const uint8_t BLUE_PIN = 11;

void setColor(uint8_t red, uint8_t green, uint8_t blue) {
  analogWrite(RED_PIN, red);
  analogWrite(GREEN_PIN, green);
  analogWrite(BLUE_PIN, blue);
}

void setup() {
  pinMode(RED_PIN, OUTPUT);
  pinMode(GREEN_PIN, OUTPUT);
  pinMode(BLUE_PIN, OUTPUT);
  setColor(0, 0, 0);
  Serial.begin(9600);
  Serial.println("RGB_LED_READY");
}

void loop() {
  setColor(96, 0, 0);
  delay(700);
  setColor(0, 96, 0);
  delay(700);
  setColor(0, 0, 96);
  delay(700);
  setColor(0, 0, 0);
  delay(700);
}
