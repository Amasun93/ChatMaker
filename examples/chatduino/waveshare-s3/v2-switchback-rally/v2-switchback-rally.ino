// Switchback Rally for Waveshare ESP32-S3-Touch-LCD-2.8 V2. Hold level at power-on.
#include <Arduino.h>
#include <Display_ST7789.h>
#include <Gyro_QMI8658.h>
#include "RaceAudio.h"
#include "RaceArt.h"

void LCD_WriteCommand(uint8_t command);
void LCD_WriteData(uint8_t data);

namespace Board {
using namespace Rally;
static Surface screen;
alignas(4) static Color output[320*240];
static Circuit track;
static Race race;
static bool imuPresent, imuOk;
static float centerX, centerY;
static int calibration;
static unsigned imuErrors;
static int pilot; // Zero is live IMU. Serial 1/2 exercise alternate routes on demand.
static uint32_t previous, previousPaint, previousLcd;
static View previousView;
struct Timing {
  uint64_t sumUs=0, paintUs=0, lcdUs=0;
  uint32_t n=0, maxUs=0, bins[65]{};
  void add(uint32_t interval,uint32_t paint,uint32_t lcd) {
    ++n; sumUs+=interval; paintUs+=paint; lcdUs+=lcd;
    maxUs=std::max(maxUs,interval);
    ++bins[std::min<uint32_t>(64,(interval+999)/1000)];
  }
  int p95() const {
    uint32_t sum=0;
    for(int i=0;i<45;++i) { sum+=bins[i]; if(uint64_t(sum)*100>=uint64_t(n)*95) return i; }
    return 64;
  }
};
static Timing stats[4];

static bool acceleration(float &x,float &y) {
  Wire.beginTransmission(QMI8658_L_SLAVE_ADDRESS); Wire.write(QMI8658_AX_L);
  if(Wire.endTransmission(false)!=0) return false;
  uint8_t data[4];
  if(Wire.requestFrom(uint8_t(QMI8658_L_SLAVE_ADDRESS),uint8_t(4))!=4 || Wire.readBytes(data,4)!=4) return false;
  x=int16_t(uint16_t(data[0]) | uint16_t(data[1])<<8)/8192.f;
  y=int16_t(uint16_t(data[2]) | uint16_t(data[3])<<8)/8192.f;
  return true;
}
static float axis(float v) {
  return copysignf(unit((fabsf(v)-.025f)*3.2f),v);
}
static Input readControls() {
  float x,y;
  imuOk=imuPresent && acceleration(x,y);
  if(!imuOk) { ++imuErrors; return {}; }
  if(calibration<32) {
    centerX+=x; centerY+=y;
    if(++calibration==32) { centerX/=32; centerY/=32; }
    return {};
  }
  return {axis(centerX-x),axis(centerY-y)};
}
static void scaleFrame() {
  for(int y=0;y<H;++y) {
    const Color *src=screen.pixels+y*W;
    Color *row=output+y*2*320;
    for(int x=0;x<W;++x) row[x*2]=row[x*2+1]=src[x];
    memcpy(row+320,row,320*sizeof(Color));
  }
}
static void resetRace(int mode) {
  race=Race{}; pilot=mode;
  for(auto &item:stats) item=Timing{};
  previous=0;
}
static void commands() {
  if(!Serial.available()) return;
  const int c=Serial.read();
  if(c=='D') {
    Serial.printf("RALLY view=%s idx=%.2f speed=%.1f x=%.2f pilot=%d laps=%u last=%.2f best=%.2f pads=%u gravel=%u jumps=%u lands=%u left=%u right=%u height=%.2f roll=%.2f imu=%d imu_errors=%u audio=%d audio_errors=%u\n",
      name(race.view()),race.idx,race.speed*3.6f,race.x,pilot,race.laps,race.lastLap,race.best,race.pads,race.gravel,
      race.jumps,race.lands,race.leftRolls,race.rightRolls,race.lift,race.roll,imuOk,imuErrors,RaceAudio::ready,unsigned(RaceAudio::errors.load()));
  } else if(c=='M') {
    for(int i=0;i<4;++i) {
      const auto &s=stats[i];
      if(s.n) Serial.printf("RALLY_TIME scene=%s n=%u fps=%.2f p95_ms=%d max_ms=%.1f paint_ms=%.2f lcd_ms=%.2f\n",
        name(View(i)),unsigned(s.n),s.n*1e6/double(s.sumUs),s.p95(),s.maxUs/1000.,
        s.paintUs/1000./s.n,s.lcdUs/1000./s.n);
    }
    Serial.println("RALLY_TIME_END");
  } else if(c=='F') {
    Serial.printf("RALLY_FRAME view=%s idx=%.2f roll=%.2f bytes=%u\n",name(race.view()),race.idx,race.roll,unsigned(sizeof(screen.pixels)));
    Serial.setTxTimeoutMs(150);
    Serial.write(reinterpret_cast<const uint8_t *>(screen.pixels),sizeof(screen.pixels));
    Serial.setTxTimeoutMs(15);
  } else if(c=='1' || c=='2' || c=='R') {
    resetRace(c=='R'?0:c-'0'); return;
  } else if(c=='C') { centerX=centerY=0; calibration=0; }
  else return;
  previous=0;  // Keep host I/O outside scene timing.
}
} // namespace Board

void setup() {
  Serial.begin(115200); Serial.setTxTimeoutMs(15);
  pinMode(7,OUTPUT); digitalWrite(7,HIGH);
  Backlight_Init(); LCD_Init(); LCD_WriteCommand(0x36); LCD_WriteData(0x60);
  I2C_Init(); Wire.setClock(400000); Wire.setTimeOut(5);
  Wire.beginTransmission(QMI8658_L_SLAVE_ADDRESS);
  Board::imuPresent=Wire.endTransmission()==0;
  if(Board::imuPresent) QMI8658_Init();
  RaceAudio::begin();
}
void loop() {
  using namespace Board;
  commands();
  const uint32_t start=micros(), interval=previous?start-previous:0;
  if(interval) stats[int(previousView)].add(interval,previousPaint,previousLcd);
  previous=start;
  Input input=readControls();
  if(pilot) input=benchInput(race,pilot);
  const uint32_t drawStart=micros();
  const Cue cue=race.step(track,interval?std::min(.06f,interval*1e-6f):.026f,input);
  RaceAudio::update(race,cue);
  previousView=race.view();
  drawFrame(screen,track,race);
  if(!imuOk || calibration<32) screen.word(54,24,imuOk?"HOLD LEVEL":"IMU OFFLINE",milk);
  scaleFrame();
  const uint32_t flush=micros();
  LCD_addWindow(0,0,319,239,output);  // Driver RAMCTRL expects little-endian RGB565.
  previousPaint=flush-drawStart; previousLcd=micros()-flush;
  delay(1);
}
