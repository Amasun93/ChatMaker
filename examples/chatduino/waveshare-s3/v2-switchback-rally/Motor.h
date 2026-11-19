#pragma once
#include "Circuit.h"
namespace Rally {
constexpr int sampleRate=24000, blockSamples=120;
struct Motor {
  float wave[256]{}, crank=0,tone=0,hz=110;
  float startHz=0,endHz=0,amount=0,noiseMix=0;
  int remaining=0,length=0;
  uint32_t rng=987654;
  Motor() { for(int i=0;i<256;++i) wave[i]=sinf(i*(2*pi/256)); }
  void trigger(Cue cue) {
    int ms=0; tone=0; noiseMix=0;
    switch(cue) {
      case Cue::Boost: startHz=230;endHz=1080;ms=260;amount=2600;break;
      case Cue::Gravel: startHz=125;endHz=60;ms=200;amount=2000;noiseMix=.85f;break;
      case Cue::Jump: startHz=370;endHz=900;ms=205;amount=2200;break;
      case Cue::Land: startHz=145;endHz=39;ms=160;amount=3900;noiseMix=.28f;break;
      case Cue::Lap: startHz=680;endHz=1020;ms=310;amount=2100;break;
      default: return;
    }
    length=remaining=ms*(sampleRate/1000);
  }
  void fill(int16_t *out,int count,float speed,bool airborne,float gravel) {
    const float gear=fmodf(std::max(speed-16.f,0.f),9.5f);
    const float rpm=airborne?150.f:55.f+gear*7.5f+speed;
    for(int i=0;i<count;++i) {
      hz+=(rpm-hz)*.0009f; crank+=hz*(256.f/sampleRate);
      if(crank>=256) crank-=256;
      rng=rng*1664525u+1013904223u;
      float noise=float(int(rng>>24)-128)/128;
      const int p=int(crank);
      float sample=(wave[p]+.35f*wave[(p*2)&255]+.20f*wave[(p*4)&255])*(airborne?430:710)
                    +noise*(100+gravel*570);
      if(remaining) {
        const float t=1-float(remaining)/length;
        tone+=lerp(startHz,endHz,t)*(256.f/sampleRate);
        if(tone>=256) tone-=256;
        sample+=amount*std::min(1.f,(length-remaining)/70.f)*(1-t)*(1-t)*
                (wave[int(tone)]*(1-noiseMix)+noiseMix*noise);
        --remaining;
      }
      out[2*i]=out[2*i+1]=int16_t(sample);
    }
  }
};
} // namespace Rally
