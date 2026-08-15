#include <WiFi.h>
#include <WebServer.h>

constexpr uint8_t LED_PIN = 23;
constexpr uint8_t SENSOR_PIN = 34;

const char *AP_SSID = "ChatMaker-ESP32";
IPAddress AP_IP(192, 168, 4, 1);
IPAddress AP_SUBNET(255, 255, 255, 0);

WebServer server(80);
bool ledOn = false;

const char INDEX_HTML[] PROGMEM = R"HTML(
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>ChatMaker ESP32</title>
  <style>
    body { font-family: system-ui, sans-serif; max-width: 34rem; margin: 3rem auto; padding: 0 1rem; }
    button { font-size: 1rem; margin-right: .5rem; padding: .7rem 1rem; }
    dl { display: grid; grid-template-columns: 8rem 1fr; gap: .5rem; }
    dt { font-weight: 700; }
  </style>
</head>
<body>
  <h1>ESP32 LED 与传感器</h1>
  <p>
    <button type="button" onclick="setLed(true)">打开 LED</button>
    <button type="button" onclick="setLed(false)">关闭 LED</button>
  </p>
  <dl>
    <dt>LED</dt><dd id="led">--</dd>
    <dt>电位器原始值</dt><dd id="sensor">--</dd>
    <dt>运行时间</dt><dd id="uptime">--</dd>
  </dl>
  <script>
    function render(state) {
      document.getElementById('led').textContent = state.led_on ? '已打开' : '已关闭';
      document.getElementById('sensor').textContent = state.sensor_raw;
      document.getElementById('uptime').textContent = state.uptime_ms + ' ms';
    }

    async function refreshState() {
      const response = await fetch('/api/state');
      render(await response.json());
    }

    async function setLed(on) {
      const response = await fetch('/api/led', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ on: on })
      });
      render(await response.json());
    }

    refreshState();
    setInterval(refreshState, 1000);
  </script>
</body>
</html>
)HTML";

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
    sendLogged("GET", "/", 200, "text/html", INDEX_HTML);
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
