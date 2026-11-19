#pragma once
#include "Flight.h"
namespace Rift {
struct Note { int startHz,endHz,ms,level,third=0,fifth=0; bool noise=false; };
struct Phrase { Note first,second; };
inline Phrase phrase(Cue cue) {
  switch(cue) {
    case Cue::Launch: return {{160,610,140,2400,0,0,true},{}};
    case Cue::Fire:   return {{1310,165,100,3600,0,0,true},{}};
    case Cue::Break:  return {{225,42,255,5100,0,0,true},{}};
    case Cue::Jump:   return {{180,890,185,3100,0,0,true},{860,540,80,1900}};
    case Cue::Roll:   return {{405,960,120,2100,0,0,true},{}};
    case Cue::Graze:  return {{180,80,70,2200,0,0,true},{}};
    case Cue::Arrive: return {{440,440,140,2600,554,659},{660,660,230,2700,830,990}};
    default: return {};
  }
}
constexpr int sampleRate=24000, audioBlock=120;
struct Voice {
  Note now{}, next{};
  int sample=0, length=0;
  float phase=0, third=0, fifth=0;
  uint32_t rng=31415926;
  unsigned serial=0;
  void start(Note n) {
    now=n; sample=0; length=n.ms*(sampleRate/1000);
    phase=third=fifth=0;
  }
  static void advance(float &p,float hz) {
    p+=hz*(256.f/sampleRate);
    if(p>=256.f) p-=256.f;
  }
  int render(const int16_t *wave) {
    if(!length) return 0;
    const float t=float(sample)/length;
    advance(phase,blend(now.startHz,now.endHz,t));
    float v=wave[int(phase)]*.84f+wave[(2*int(phase))&255]*.10f;
    if(now.third) {
      advance(third,now.third); advance(fifth,now.fifth);
      v=wave[int(phase)]*.42f+wave[int(third)]*.29f+wave[int(fifth)]*.23f;
    }
    if(now.noise) {
      rng=1664525u*rng+1013904223u;
      v+=(float(rng>>24)-128)*.45f;
    }
    const float envelope=std::min(1.f,sample/100.f)*(1-t)*(1-t);
    const int result=int(v*envelope*now.level/256.f);
    if(++sample>=length) { start(next); next={}; }
    return result;
  }
};
struct Mixer {
  int16_t wave[256]{};
  Voice voices[4]{};
  unsigned counter=0;
  Mixer() { for(int i=0;i<256;++i) wave[i]=int16_t(255*sinf(2*pi*i/256)); }
  bool active() const { for(const auto &v:voices) if(v.length) return true; return false; }
  void trigger(Cue cue) {
    const auto sound=phrase(cue);
    if(!sound.first.ms) return;
    Voice *slot=&voices[0];
    for(auto &v:voices) {
      if(!v.length) { slot=&v; break; }
      if(v.serial<slot->serial) slot=&v;
    }
    slot->serial=++counter; slot->start(sound.first); slot->next=sound.second;
  }
  void fill(int16_t *stereo,int count) {
    for(int i=0;i<count;++i) {
      int value=0;
      for(auto &v:voices) value+=v.render(wave);
      stereo[2*i]=stereo[2*i+1]=int16_t(std::clamp(value,-32767,32767));
    }
  }
};
} // namespace Rift
