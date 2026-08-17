#include <DFRobot_SSD1306_I2C.h>

const uint8_t LIGHT_PIN = A0;
const uint8_t BUTTON_PIN = 2;
const unsigned long REFRESH_MS = 250;

DFRobot_SSD1306_I2C oled;
uint8_t page = 0;
bool lastButton = HIGH;
unsigned long lastButtonChange = 0;
unsigned long lastRefresh = 0;
int minimumLight = 1023;
int maximumLight = 0;

void drawDashboard(int lightValue) {
  char valueLine[22];
  char rangeLine[22];
  oled.fillScreen(0);

  if (page == 0) {
    oled.setCursorLine(1);
    oled.printLine("Light Dashboard");
    snprintf(valueLine, sizeof(valueLine), "Current: %d", lightValue);
    oled.setCursorLine(2);
    oled.printLine(valueLine);
    oled.setCursorLine(3);
    oled.printLine(lightValue >= 600 ? "Level: HIGH" : "Level: LOW");
    oled.setCursorLine(4);
    oled.printLine("Press for range");
  } else {
    oled.setCursorLine(1);
    oled.printLine("Observed Range");
    snprintf(valueLine, sizeof(valueLine), "Minimum: %d", minimumLight);
    snprintf(rangeLine, sizeof(rangeLine), "Maximum: %d", maximumLight);
    oled.setCursorLine(2);
    oled.printLine(valueLine);
    oled.setCursorLine(3);
    oled.printLine(rangeLine);
    oled.setCursorLine(4);
    oled.printLine("Press for live");
  }
}

void setup() {
  pinMode(BUTTON_PIN, INPUT_PULLUP);
  Serial.begin(9600);
  oled.begin(0x3c);
  oled.fillScreen(0);
  oled.setCursorLine(1);
  oled.printLine("Starting...");
  Serial.println("UNO_OLED_DASHBOARD_READY");
}

void loop() {
  unsigned long now = millis();
  bool button = digitalRead(BUTTON_PIN);
  if (button != lastButton && now - lastButtonChange >= 40) {
    lastButton = button;
    lastButtonChange = now;
    if (button == LOW) {
      page = (page + 1) % 2;
      lastRefresh = 0;
    }
  }

  if (now - lastRefresh >= REFRESH_MS) {
    lastRefresh = now;
    int lightValue = analogRead(LIGHT_PIN);
    minimumLight = min(minimumLight, lightValue);
    maximumLight = max(maximumLight, lightValue);
    drawDashboard(lightValue);
    Serial.print("LIGHT=");
    Serial.print(lightValue);
    Serial.print(" PAGE=");
    Serial.println(page);
  }
}
