void setup() {
  Serial.begin(115200);
  pinMode(LED_BUILTIN, OUTPUT);
}

void loop() {
  digitalWrite(LED_BUILTIN, LOW);
  Serial.println("CHATMAKER_BOARD_ID:seeed-xiao-esp32s3");
  delay(200);
  digitalWrite(LED_BUILTIN, HIGH);
  delay(800);
}
