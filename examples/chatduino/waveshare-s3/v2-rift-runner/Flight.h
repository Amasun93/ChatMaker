#pragma once
#include <algorithm>
#include <cmath>
#include <cstdint>

namespace Rift {
constexpr float pi = 3.14159265f;
inline float unit(float n) { return std::clamp(n, 0.0f, 1.0f); }
inline float ease(float n) { n = unit(n); return n * n * (3 - 2 * n); }
inline float blend(float a, float b, float t) { return a + (b - a) * t; }

enum class Scene : uint8_t { Orbit, Approach, Impact, Breach, Tunnel, Dawn };
enum class Cue : uint8_t { Silent, Launch, Fire, Break, Jump, Roll, Graze, Arrive };
constexpr float contactTime=.085f, impactTime=.40f, tunnelTime=.78f, gateDistance=3.65f;
inline const char *name(Scene scene) {
  constexpr const char *names[] = {"orbit", "approach", "impact", "breach", "tunnel", "dawn"};
  return names[int(scene)];
}
struct Input { float x = 0, y = 0; };
struct Flight {
  Scene scene = Scene::Orbit;
  int leg = 0;                  // Orbital gate, then the gate of the selected world.
  int choice[2] = {0, 0};       // -1 is port, +1 is starboard, 0 is sealed.
  int lastRoute[2] = {0, 0};
  float age = 0, clock = 0, travel = 0;
  float x = 0, y = 0, bank = 0;
  float distance = 0, missFlash = 0;
  int armedSide = 0;
  float armAge = 0, roll = 0, cool = 0;
  int rollDir = 1;
  float hazard = 0, jolt = 0;
  unsigned shots = 0, hits = 0, passes = 0, rolls = 0, grazes = 0, dodges = 0, misses = 0, laps = 0;

  void cut(Scene next) { scene = next; age = 0; }
  float gateScale() const { return .55f / std::max(.16f,1-.222f*distance); }
  float sightX() const { return 80 + 53 * x; }
  float sightY() const { return 56 + 28 * y; }
  float nodeY(int side) const { return leg == 0 ? 56.0f : 56.0f - 15 * side; }
  bool frozenWorld() const { return choice[0] < 0; }
  bool inOpening(int side) const {
    return fabsf(x - side*.62f)<.30f && fabsf(sightY()-nodeY(side))<19;
  }
  // Test the whole reticle segment. A fast hand movement can cross a core between frames.
  bool sweptCore(Input previous,int side) const {
    const float ax=(53*previous.x-side*33)/9, ay=(56+28*previous.y-nodeY(side))/11;
    const float vx=(x-previous.x)*53/9, vy=(y-previous.y)*28/11;
    const float t=unit(-(ax*vx+ay*vy)/std::max(.00001f,vx*vx+vy*vy));
    const float dx=ax+t*vx, dy=ay+t*vy;
    return dx*dx+dy*dy<=1;
  }
  void nextGate() { distance=0; hazard=0; choice[leg]=0; cut(Scene::Approach); }
  Cue step(float dt, Input tilt) {
    clock += dt;
    age += dt;
    travel += dt * (scene == Scene::Tunnel ? 5.0f : 1.0f);
    const Input previous{x,y};
    const float follow = 1 - expf(-11.5f * dt);
    x = blend(x, tilt.x, follow);
    y = blend(y, tilt.y, follow);
    bank = blend(bank, tilt.x, 1 - expf(-4.2f * dt));
    roll = std::max(0.0f, roll - dt);
    cool = std::max(0.0f, cool - dt);
    jolt = std::max(0.0f, jolt - dt);
    missFlash = std::max(0.0f,missFlash-dt);
    if(scene==Scene::Approach || scene==Scene::Impact || scene==Scene::Breach)
      distance+=dt*(choice[leg] && inOpening(choice[leg]) ? 4.0f : 1.0f);
    Cue cue = Cue::Silent;
    if (scene != Scene::Orbit) {
      if (cool <= 0 && !armedSide && fabsf(tilt.x) > .88f) {
        armedSide = tilt.x > 0 ? 1 : -1;
        armAge = 0;
      }
      if (armedSide) {
        armAge += dt;
        if (fabsf(tilt.x) < .32f || tilt.x * armedSide < 0) {
          if (armAge < .72f) {
            roll = .70f;
            cool = 1.0f;
            rollDir = armedSide;
            ++rolls;
            cue = Cue::Roll;
          }
          armedSide = 0;
        }
      }
    } else {
      armedSide = 0;
    }

    switch (scene) {
      case Scene::Orbit:
        if (age > 1.35f || fabsf(tilt.x)+fabsf(tilt.y)>.18f) { nextGate(); return Cue::Launch; }
        break;
      case Scene::Approach: {
        if (leg == 1) {
          const int cycle = int(age / 2.8f);
          const float old = hazard;
          hazard = fmodf(age, 2.8f) / 2.8f;
          const float lane = cycle % 2 == 0 ? .16f : -.38f;
          if (old < .86f && hazard >= .86f && fabsf(x - lane) < .29f) {
            if (roll > 0) ++dodges;
            else { ++grazes; jolt = .42f; cue = Cue::Graze; }
          }
        }
        for(int side:{-1,1}) {
          if(sweptCore(previous,side)) {
            choice[leg]=side; ++shots; cut(Scene::Impact); return Cue::Fire;
          }
        }
        if(distance>=gateDistance) { ++misses; nextGate(); missFlash=.45f; }
        break;
      }
      case Scene::Impact:
        if (age - dt < contactTime && age >= contactTime) { ++hits; cue = Cue::Break; }
        if (age >= impactTime) cut(Scene::Breach);
        break;
      case Scene::Breach: {
        if(distance>=gateDistance) {
          if(inOpening(choice[leg])) { ++passes; cut(Scene::Tunnel); return Cue::Jump; }
          ++misses; nextGate(); missFlash=.45f;
        }
        break;
      }
      case Scene::Tunnel:
        if (age >= tunnelTime) {
          if (leg == 0) { ++leg; nextGate(); }
          else {
            ++laps; lastRoute[0]=choice[0]; lastRoute[1]=choice[1];
            cut(Scene::Dawn); return Cue::Arrive;
          }
        }
        break;
      case Scene::Dawn:
        if(age>1.25f || fabsf(tilt.x-previous.x)>.30f) {
          leg=0; choice[1]=0; nextGate();
        }
        break;
    }
    return cue;
  }
};
}  // namespace Rift
