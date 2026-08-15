#include <WiFi.h>
#include <WebServer.h>
#include "page_html.h"

constexpr uint8_t LED_PIN = 23;
constexpr uint8_t SENSOR_PIN = 34;

const char *AP_SSID = "ChatMaker-ESP32";
IPAddress AP_IP(192, 168, 4, 1);
IPAddress AP_SUBNET(255, 255, 255, 0);

WebServer server(80);
bool ledOn = false;

String buildStateJson() {
  const int sensorRaw = analogRead(SENSOR_PIN);
  const unsigned long uptimeMs = millis();

  String json = "{\"schema_version\":\"1.0\",\"led_on\":";
  json += ledOn ? "true" : "false";
  json += ",\"sensor_raw\":";
  json += sensorRaw;
  json += ",\"uptime_ms\":";
  json += uptimeMs;
  json += "}";
  return json;
}

void sendLogged(const String &method, const String &path, int statusCode,
                const char *contentType, const String &body) {
  Serial.print(method);
  Serial.print(' ');
  Serial.print(path);
  Serial.print(' ');
  Serial.println(statusCode);
  server.send(statusCode, contentType, body);
}

void sendPageLogged() {
  Serial.print("GET");
  Serial.print(' ');
  Serial.print("/");
  Serial.print(' ');
  Serial.println(200);
  server.send_P(200, PSTR("text/html; charset=utf-8"), CHATMAKER_AP_PAGE,
                CHATMAKER_AP_PAGE_LENGTH);
}

bool parseLedState(const String &body, bool &requestedOn) {
  String compact = body;
  compact.replace(" ", "");
  compact.replace("\t", "");
  compact.replace("\r", "");
  compact.replace("\n", "");

  if (compact == "{\"on\":true}") {
    requestedOn = true;
    return true;
  }
  if (compact == "{\"on\":false}") {
    requestedOn = false;
    return true;
  }
  return false;
}

String methodName(HTTPMethod method) {
  switch (method) {
    case HTTP_GET:
      return "GET";
    case HTTP_POST:
      return "POST";
    case HTTP_PUT:
      return "PUT";
    case HTTP_DELETE:
      return "DELETE";
    default:
      return "OTHER";
  }
}

void handleLedPost() {
  bool requestedOn = false;
  if (!parseLedState(server.arg("plain"), requestedOn)) {
    sendLogged("POST", "/api/led", 400, "application/json",
               "{\"error\":\"invalid_led_state\"}");
    return;
  }

  ledOn = requestedOn;
  digitalWrite(LED_PIN, requestedOn ? HIGH : LOW);
  sendLogged("POST", "/api/led", 200, "application/json", buildStateJson());
}

void setup() {
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);

  Serial.begin(115200);

  WiFi.mode(WIFI_AP);
  WiFi.softAPConfig(AP_IP, AP_IP, AP_SUBNET);
  WiFi.softAP(AP_SSID);

  server.on("/", HTTP_GET, []() {
    sendPageLogged();
  });
  server.on("/api/state", HTTP_GET, []() {
    sendLogged("GET", "/api/state", 200, "application/json", buildStateJson());
  });
  server.on("/api/led", HTTP_POST, handleLedPost);
  server.onNotFound([]() {
    sendLogged(methodName(server.method()), server.uri(), 404, "application/json",
               "{\"error\":\"not_found\"}");
  });

  server.begin();
  Serial.print("AP ready at ");
  Serial.println(WiFi.softAPIP());
}

void loop() {
  server.handleClient();
}
