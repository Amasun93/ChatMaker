#include <Arduino_LED_Matrix.h>

ArduinoLEDMatrix matrix;

void setup() {
  Serial.begin(115200);
  matrix.begin();
}

void loop() {
  matrix.loadFrame(LEDMATRIX_HEART_BIG);
  Serial.println("CHATMAKER_BOARD_ID:arduino-uno-r4-wifi");
  delay(650);
  matrix.clear();
  delay(350);
}
