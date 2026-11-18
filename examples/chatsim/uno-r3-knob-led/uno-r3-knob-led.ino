constexpr int knobPin = A0;
constexpr int ledPin = 3;

void setup() {
    pinMode(ledPin, OUTPUT);
}

void loop() {
    const unsigned long sample = analogRead(knobPin);
    analogWrite(ledPin, (sample * 255 + 511) / 1023);
}
