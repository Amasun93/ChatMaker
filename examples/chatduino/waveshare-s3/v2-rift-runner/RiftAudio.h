#pragma once
#include <ESP_I2S.h>
#include <atomic>
#include <cmath>
#include "Flight.h"

namespace RiftAudio {
constexpr uint32_t rate = 24000;
constexpr size_t block = 120;
static I2SClass dac;
static QueueHandle_t events = nullptr;
static std::atomic<uint32_t> played{0}, errors{0};
static bool ready = false;

static float advancePhase(float phase, float hz) {
  phase += hz * (6.2831853f / rate);
  return (phase < 6.2831853f) ? phase : phase - 6.2831853f;
}

static bool tone(int startHz, int endHz, int milliseconds, int volume,
                 bool wind = false, int thirdHz = 0, int fifthHz = 0) {
  int16_t stereo[block * 2];
  const uint32_t frames = rate * milliseconds / 1000;
  float phase = 0;
  float thirdPhase = 0;
  float fifthPhase = 0;
  uint32_t random = 0x92451FA3u;
  for (uint32_t offset = 0; offset < frames; offset += block) {
    const size_t count = (frames - offset < block) ? frames - offset : block;
    for (size_t i = 0; i < count; ++i) {
      const float progress = float(offset + i) / frames;
      const float frequency = startHz + (endHz - startHz) * progress;
      const float attack = (progress < 0.10f) ? progress * 10.0f : 1.0f;
      const float decay = 1.0f - progress;
      phase = advancePhase(phase, frequency);
      random = 1664525u * random + 1013904223u;
      const float noise = wind ? (float(random >> 24) - 128.0f) / 512.0f : 0.0f;
      float timbre = sinf(phase) * 0.84f + sinf(2.0f * phase) * 0.10f + noise;
      if (thirdHz > 0 && fifthHz > 0) {
        thirdPhase = advancePhase(thirdPhase, thirdHz);
        fifthPhase = advancePhase(fifthPhase, fifthHz);
        timbre = 0.42f * sinf(phase) + 0.29f * sinf(thirdPhase) + 0.23f * sinf(fifthPhase);
      }
      const auto sample = int16_t(timbre * volume * attack * decay * decay);
      stereo[2 * i] = stereo[2 * i + 1] = sample;
    }
    const size_t bytes = count * 2 * sizeof(int16_t);
    if (dac.write(stereo, bytes) != bytes) return false;
  }
  return true;
}

static void audioLoop(void *) {
  Rift::Cue cue;
  for (;;) {
    if (xQueueReceive(events, &cue, portMAX_DELAY) != pdTRUE) continue;
    bool ok = false;
    using Cue = Rift::Cue;
    switch (cue) {
      case Cue::Launch: ok = tone(170, 690, 330, 3000, true); break;
      case Cue::Lock: ok = tone(750, 980, 55, 1900); break;
      case Cue::Fire: ok = tone(1280, 140, 160, 4000, true); break;
      case Cue::Break: ok = tone(245, 46, 320, 5300, true); break;
      case Cue::Jump: ok = tone(220, 930, 290, 3600, true) && tone(880, 530, 180, 2200); break;
      case Cue::Roll: ok = tone(430, 980, 120, 2150, true); break;
      case Cue::Graze: ok = tone(180, 85, 85, 2100, true); break;
      case Cue::Arrive: ok = tone(440, 440, 160, 3100, false, 554, 659) &&
                            tone(660, 660, 400, 3400, false, 830, 990); break;
      case Cue::Silent: continue;
    }
    if (ok) ++played;
    else ++errors;
  }
}

static void begin() {
  events = xQueueCreate(5, sizeof(Rift::Cue));
  if (!events) return;
  dac.setPins(48, 38, 47);  // Onboard PCM5101 and the board's speaker amplifier.
  if (!dac.begin(I2S_MODE_STD, rate, I2S_DATA_BIT_WIDTH_16BIT, I2S_SLOT_MODE_STEREO)) return;
  ready = xTaskCreatePinnedToCore(audioLoop, "rift-audio", 4096, nullptr, 2, nullptr, 0) == pdPASS;
}

static void play(Rift::Cue event) {
  if (ready && xQueueSend(events, &event, 0) != pdTRUE) ++errors;
}
}  // namespace RiftAudio
