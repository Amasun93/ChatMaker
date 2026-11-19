#pragma once
#include <ESP_I2S.h>
#include <atomic>
#include "RiftSynth.h"

namespace RiftAudio {
static I2SClass dac;
static QueueHandle_t events = nullptr;
static std::atomic<uint32_t> played{0}, errors{0};
static bool ready = false;

static void audioLoop(void *) {
  Rift::Mixer mixer;
  int16_t block[Rift::audioBlock*2];
  for (;;) {
    Rift::Cue event;
    unsigned starts=0;
    if (xQueueReceive(events,&event,mixer.active()?0:portMAX_DELAY)==pdTRUE) {
      do { mixer.trigger(event); ++starts; }
      while (xQueueReceive(events,&event,0)==pdTRUE);
    }
    mixer.fill(block,Rift::audioBlock);
    if (dac.write(block,sizeof block)==sizeof block) played+=starts;
    else ++errors;
  }
}

static void begin() {
  events = xQueueCreate(5, sizeof(Rift::Cue));
  if (!events) return;
  dac.setPins(48, 38, 47);  // Onboard PCM5101 and the board's speaker amplifier.
  if (!dac.begin(I2S_MODE_STD, Rift::sampleRate, I2S_DATA_BIT_WIDTH_16BIT, I2S_SLOT_MODE_STEREO)) return;
  ready = xTaskCreatePinnedToCore(audioLoop, "rift-audio", 4096, nullptr, 2, nullptr, 0) == pdPASS;
}

static void play(Rift::Cue event) {
  if (ready && xQueueSend(events, &event, 0) != pdTRUE) ++errors;
}
}  // namespace RiftAudio
