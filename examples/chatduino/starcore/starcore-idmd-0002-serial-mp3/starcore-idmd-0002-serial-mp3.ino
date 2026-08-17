#include <MPython.h>
#include <DFRobot_SerialMp3.h>

// 可调参数：音量范围 0-100，曲目编号范围 1-255。
const int MP3_VOLUME = 30;
const int TRACK_NUMBER = 1;

DFRobot_SerialMp3 serialMp3;

void setup() {
  Serial.begin(115200);
  serialMp3.begin(&Serial1, P15, P16);
  serialMp3.volume(MP3_VOLUME);
  Serial.println("STARCORE_MP3_READY");
  serialMp3.playList(TRACK_NUMBER);  // 只发送一次，避免反复重播。
  Serial.print("PLAY_TRACK=");
  Serial.println(TRACK_NUMBER);
}

void loop() {
  // 播放由模块继续执行；不要在 loop 中重复发送播放命令。
}
