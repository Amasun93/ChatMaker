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
enum class Cue : uint8_t { Silent, Launch, Lock, Fire, Break, Jump, Roll, Graze, Arrive };
inline const char *name(Scene scene) {
  constexpr const char *names[] = {"orbit", "approach", "impact", "breach", "tunnel", "dawn"};
  return names[int(scene)];
}
struct Input { float x = 0, y = 0; };
struct Flight {
  Scene scene = Scene::Orbit;
  int leg = 0;                  // Orbital gate, then the gate of the selected world.
  int choice[2] = {0, 0};       // -1 is port, +1 is starboard, 0 is sealed.
  float age = 0, clock = 0, travel = 0;
  float x = 0, y = 0, bank = 0;
  float lock = 0, crossing = 0;
  int tracking = 0, armedSide = 0;
  float armAge = 0, roll = 0, cool = 0;
  int rollDir = 1;
  float hazard = 0, jolt = 0;
  bool centered = false;
  unsigned shots = 0, hits = 0, passes = 0, rolls = 0, grazes = 0, dodges = 0;

  void cut(Scene next) { scene = next; age = 0; }
  float gateScale() const { return 0.32f + 0.68f * ease(age / 2.45f); }
  float sightX() const { return 80 + 53 * x; }
  float sightY() const { return 56 + 28 * y; }
  float nodeY(int side) const { return leg == 0 ? 56.0f : 56.0f - 7 * side; }
  bool frozenWorld() const { return choice[0] < 0; }
  Cue step(float dt, Input tilt) {
    clock += dt;
    age += dt;
    travel += dt * (scene == Scene::Tunnel ? 5.0f : 1.0f);
    const float follow = 1 - expf(-7.5f * dt);
    x = blend(x, tilt.x, follow);
    y = blend(y, tilt.y, follow);
    bank = blend(bank, tilt.x, 1 - expf(-4.2f * dt));
    roll = std::max(0.0f, roll - dt);
    cool = std::max(0.0f, cool - dt);
    jolt = std::max(0.0f, jolt - dt);
    Cue cue = Cue::Silent;
    if (scene == Scene::Approach || scene == Scene::Breach) {
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
        if (age > 3.15f) { cut(Scene::Approach); return Cue::Launch; }
        break;
      case Scene::Approach: {
        if (leg == 1) {
          const int cycle = int(age / 2.8f);
          const float old = hazard;
          hazard = fmodf(age, 2.8f) / 2.8f;
          const float lane = cycle % 2 == 0 ? .16f : -.38f;
          if (old < .86f && hazard >= .86f && fabsf(x - lane) < .29f) {
            if (roll > 0) ++dodges;
            else { ++grazes; lock = 0; jolt = .42f; cue = Cue::Graze; }
          }
        }
        if (age < 1.4f) break;
        const float scale = gateScale();
        const int side = x < 0 ? -1 : 1;
        const float dx = (sightX() - (80 + side * 33 * scale)) / 11.0f;
        const float dy = (sightY() - (56 + (nodeY(side) - 56) * scale)) / 15.0f;
        if (dx * dx + dy * dy <= 1 && roll <= 0) {
          if (tracking != side) { lock = 0; tracking = side; cue = Cue::Lock; }
          lock += dt;
          if (lock >= .59f) {
            choice[leg] = side; ++shots; cut(Scene::Impact); return Cue::Fire;
          }
        } else { tracking = 0; lock = 0; }
        break;
      }
      case Scene::Impact:
        if (age - dt < .38f && age >= .38f) { ++hits; cue = Cue::Break; }
        if (age > 1.65f) { crossing = 0; cut(Scene::Breach); }
        break;
      case Scene::Breach: {
        const int open = choice[leg];
        if (age > .35f && fabsf(x - open * .62f) < .26f &&
            fabsf(sightY() - nodeY(open)) < 19.0f) {
          crossing += dt;
          if (crossing > .40f) { ++passes; cut(Scene::Tunnel); return Cue::Jump; }
        } else crossing = 0;
        break;
      }
      case Scene::Tunnel:
        if (age > 1.65f) {
          lock = 0; tracking = 0; hazard = 0;
          if (leg == 0) { ++leg; cut(Scene::Approach); }
          else { centered = false; cut(Scene::Dawn); return Cue::Arrive; }
        }
        break;
      case Scene::Dawn:
        if (age > 2.8f) {
          if (fabsf(tilt.x) < .18f) centered = true;
          if (centered && fabsf(tilt.x) > .65f) *this = Flight{};
        }
        break;
    }
    return cue;
  }
};
}  // namespace Rift
