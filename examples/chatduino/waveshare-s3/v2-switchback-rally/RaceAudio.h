#pragma once
#include <ESP_I2S.h>
#include <atomic>
#include "Motor.h"
namespace RaceAudio {
using namespace Rally;
static I2SClass dac;
static QueueHandle_t cues;
static std::atomic<unsigned> controls{0},errors{0};
static bool ready=false;
static void worker(void *) {
  Motor motor;
  int16_t buffer[blockSamples*2];
  for(;;) {
    Cue cue;
    while(xQueueReceive(cues,&cue,0)==pdTRUE) motor.trigger(cue);
    const unsigned state=controls.load();
    motor.fill(buffer,blockSamples,(state&1023)*.1f,(state&1024)!=0,((state>>11)&255)/255.f);
    if(dac.write(buffer,sizeof buffer)!=sizeof buffer) { ++errors; vTaskDelay(1); }
  }
}
static void begin() {
  cues=xQueueCreate(6,sizeof(Cue));
  dac.setPins(48,38,47);
  if(cues && dac.begin(I2S_MODE_STD,sampleRate,I2S_DATA_BIT_WIDTH_16BIT,I2S_SLOT_MODE_STEREO))
    ready=xTaskCreatePinnedToCore(worker,"rally-audio",4096,nullptr,2,nullptr,0)==pdPASS;
}
static void update(const Race &race,Cue cue) {
  controls.store(unsigned(race.engine*10) | (race.duration>0?1024u:0u) | (unsigned(race.rough*255)<<11));
  if(ready && cue!=Cue::Silent && xQueueSend(cues,&cue,0)!=pdTRUE) ++errors;
}
} // namespace RaceAudio
