#pragma once
#include <algorithm>
#include <cmath>
#include <cstdint>
namespace Rally {
constexpr float pi=3.14159265f;
inline float unit(float x) { return std::clamp(x,0.f,1.f); }
inline float ease(float x) { x=unit(x); return x*x*(3-2*x); }
inline float lerp(float a,float b,float t) { return a+(b-a)*t; }
struct Vec { float x,y,z; };
inline Vec operator+(Vec a,Vec b) { return {a.x+b.x,a.y+b.y,a.z+b.z}; }
inline Vec operator-(Vec a,Vec b) { return {a.x-b.x,a.y-b.y,a.z-b.z}; }
inline Vec operator*(Vec a,float n) { return {a.x*n,a.y*n,a.z*n}; }
inline float dot(Vec a,Vec b) { return a.x*b.x+a.y*b.y+a.z*b.z; }
inline Vec cross(Vec a,Vec b) { return {a.y*b.z-a.z*b.y,a.z*b.x-a.x*b.z,a.x*b.y-a.y*b.x}; }
inline Vec normalized(Vec v) { return v*(1/std::max(.001f,sqrtf(dot(v,v)))); }
struct Rail {
  Vec center,forward,right;
  Vec at(float x,float y=0,float z=0) const {return center+right*x+Vec{0,y,0}+forward*z;}
};
enum class Material : uint8_t { Asphalt,Boost,Gravel,Ramp };
constexpr int sections=192;
constexpr float halfWidth=5.6f;
struct Patch { int first,end; float x,half; Material type; };
constexpr Patch patches[]={
  {6,11,0,2.4f,Material::Boost}, {15,21,2.8f,2.0f,Material::Gravel},
  {25,29,0,3.25f,Material::Ramp}, {45,51,-2.6f,2.15f,Material::Boost},
  {66,74,0,2.35f,Material::Gravel}, {84,89,2.5f,2.05f,Material::Boost},
  {97,101,-2.6f,2.25f,Material::Ramp}, {111,116,2.7f,1.9f,Material::Gravel},
  {132,139,0,2.4f,Material::Boost}, {149,154,0,4.8f,Material::Ramp},
  {173,178,-2.3f,2.2f,Material::Gravel}, {182,187,2.1f,2.55f,Material::Boost}
};
inline int wrapIndex(int i) { i%=sections; return i<0?i+sections:i; }
inline const Patch *patchAt(float index,float x) {
  for(const auto &p:patches) if(index>=p.first && index<p.end && fabsf(x-p.x)<=p.half) return &p;
  return nullptr;
}
inline float rampRise(const Patch &p,float idx) {
  return (p.first==149?2.45f:1.45f)*unit((idx-p.first)/(p.end-p.first));
}
struct Circuit {
  Rail rails[sections];
  float length=0,spacing=0;
  static Vec spline(float t) {
    // Closed control polygon in metres. The height of each sector is part of the course.
    static constexpr Vec nodes[]={{0,3,0},{4,4,60},{38,5,102},{92,7,117},{138,16,97},
      {152,20,50},{130,17,25},{94,11,38},{73,9,15},{91,10,-42},{84,10,-83},
      {37,12,-111},{-15,12,-104},{-52,8,-83},{-58,4,-44},{-27,3,-25}};
    int s=int(t)%16; float u=t-int(t);
    Vec a=nodes[(s+15)%16], b=nodes[s], c=nodes[(s+1)%16], d=nodes[(s+2)%16];
    return (b*2+(c-a)*u+(a*2-b*5+c*4-d)*(u*u)+(b*3-a-c*3+d)*(u*u*u))*.5f;
  }
  Circuit() {
    float arc[sections+1]{};
    Vec last=spline(0);
    for(int i=1;i<=sections;++i) {
      const Vec p=spline(i*16.f/sections),diff=p-last;
      arc[i]=arc[i-1]+sqrtf(dot(diff,diff)); last=p;
    }
    length=arc[sections]; spacing=length/sections;
    int j=0;
    for(int i=0;i<sections;++i) {
      const float dist=i*spacing;
      while(j<sections-1 && arc[j+1]<dist) ++j;
      rails[i].center=spline((j+(dist-arc[j])/(arc[j+1]-arc[j]))*16.f/sections);
    }
    for(int i=0;i<sections;++i) {
      Vec d=rails[wrapIndex(i+1)].center-rails[wrapIndex(i-1)].center; d.y=0;
      rails[i].forward=normalized(d);
      rails[i].right={rails[i].forward.z,0,-rails[i].forward.x};
    }
  }
  Rail sample(float idx) const {
    const int n=int(floorf(idx)); const float t=idx-n;
    const auto &a=rails[wrapIndex(n)], &b=rails[wrapIndex(n+1)];
    const Vec f=normalized(a.forward+(b.forward-a.forward)*t);
    return {a.center+(b.center-a.center)*t,f,{f.z,0,-f.x}};
  }
};
enum class View : uint8_t { Chase, Overhead, Bridge, Air };
enum class Cue : uint8_t { Silent, Boost, Gravel, Jump, Land, Lap };
inline const char *name(View v) {
  constexpr const char *names[]={"chase","overhead","bridge","air"};
  return names[int(v)];
}
struct Input { float steer=0,throttle=0; };
struct Race {
  float idx=0,x=0,vx=0,speed=26,clock=0,lapTime=0,best=0,lastLap=0;
  float air=0,duration=0,lift=0,roll=0,spin=1,launchHeight=0,spinOffset=0;
  float boost=0,landing=0,steer=0,rough=0,engine=0;
  float cameraSide=0,cameraHeight=3.25f,cameraBack=8.6f,cameraLead=3.6f;
  unsigned laps=0,pads=0,gravel=0,jumps=0,lands=0,leftRolls=0,rightRolls=0;
  Material material=Material::Asphalt;
  int sector() const { return idx<60?0:(idx<128?1:2); }
  View view() const { return duration>0?View::Air:View(sector()); }
  Cue step(const Circuit &track,float dt,Input input) {
    clock+=dt; lapTime+=dt;
    landing=std::max(0.f,landing-dt);
    boost=std::max(0.f,boost-dt);
    steer=lerp(steer,input.steer,1-expf(-dt*11));
    const auto &rail=track.rails[int(idx)];
    const float turn=dot(rail.right,track.rails[wrapIndex(int(idx)+2)].forward);
    float desired=steer*6.9f-turn*(speed/30)*2.0f;
    if(duration>0) desired=x+input.steer*.70f;
    vx=lerp(vx,std::clamp((desired-x)*6.f,-15.f,15.f),1-expf(-dt*9));
    x=std::clamp(x+vx*dt,-7.f,7.f);
    const auto *p=patchAt(idx,x);
    const Material surface=duration>0?Material::Asphalt:
      (fabsf(x)>halfWidth?Material::Gravel:(p?p->type:Material::Asphalt));
    Cue cue=Cue::Silent;
    if(surface!=material) {
      if(surface==Material::Boost) {++pads; boost=1.35f; speed=std::max(speed,38.f); cue=Cue::Boost;}
      if(surface==Material::Gravel) {++gravel; speed*=.81f; cue=Cue::Gravel;}
    }
    material=surface;
    rough=lerp(rough,float(surface==Material::Gravel),1-expf(-dt*12));
    const float target=surface==Material::Gravel?18.f:(boost>0?46.f:30.5f+input.throttle*5);
    speed=lerp(speed,target,1-expf(-dt*(surface==Material::Gravel?5.f:1.8f)));
    const float old=idx;
    idx+=speed*dt/track.spacing;
    if(idx>=sections) {
      idx-=sections; ++laps; lastLap=lapTime;
      if(!best || lastLap<best) best=lastLap;
      lapTime=0; cue=Cue::Lap;
    }
    if(duration>0) {
      air+=dt;
      const float phase=unit(air/duration);
      if(phase<.18f && fabsf(input.steer)>.22f) spin=input.steer<0?-1.f:1.f;
      // Tilt changes rotation timing; the wheels always complete the turn before touchdown.
      spinOffset=lerp(spinOffset,input.steer*spin*.14f,1-expf(-dt*7));
      const float progress=ease(unit((phase-.10f)/.80f+spinOffset*sinf(phase*pi)));
      roll=spin*2*pi*progress;
      lift=(1-phase)*launchHeight+4*phase*(1-phase)*(duration*2.7f);
      if(phase>=1) {
        ++lands; if(spin<0) ++leftRolls; else ++rightRolls;
        lift=roll=duration=0; landing=.32f; cue=Cue::Land;
      }
    } else {
      lift=0;
      if(p && p->type==Material::Ramp) {
        lift=rampRise(*p,idx);
        if(old<p->end && idx>=p->end) {
          launchHeight=lift; air=0; duration=.97f+speed*.011f+(p->first==149?.20f:0);
          spin=fabsf(input.steer)>.18f?(input.steer<0?-1:1):(p->x<0?-1:1);
          spinOffset=0; ++jumps; cue=Cue::Jump;
        }
      }
    }
    const auto mode=view();
    const float side=mode==View::Air?-8.0f:(mode==View::Bridge?-5.5f:(mode==View::Overhead?1.8f:0));
    const float high=mode==View::Air?3.9f:(mode==View::Bridge?4.6f:(mode==View::Overhead?15.8f:3.25f));
    const float back=mode==View::Air?6.1f:(mode==View::Bridge?8.1f:(mode==View::Overhead?9.6f:8.6f));
    const float follow=1-expf(-dt*(mode==View::Air?6.f:4.3f));
    cameraSide=lerp(cameraSide,side,follow); cameraHeight=lerp(cameraHeight,high,follow);
    cameraBack=lerp(cameraBack,back,follow);
    cameraLead=lerp(cameraLead,mode==View::Overhead?4.2f:(mode==View::Air?1.0f:3.6f),follow);
    engine=lerp(engine,speed,1-expf(-dt*9));
    return cue;
  }
};
// Reproducible route for stand-alone bench measurements. Live input is the default.
inline Input benchInput(const Race &r,int mode) {
  if(r.duration>0) return {mode==1?-.65f:.65f,0};
  if(mode==2) return {.70f,0};
  float lane=0;
  for(const auto &p:patches)
    if(r.idx>=p.first-3 && r.idx<p.end) {lane=p.x/6.9f; break;}
  return {lane,0};
}
} // namespace Rally
