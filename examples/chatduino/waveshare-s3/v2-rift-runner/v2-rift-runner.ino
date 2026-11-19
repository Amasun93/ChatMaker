// Rift Runner for Waveshare ESP32-S3-Touch-LCD-2.8 V2. Hold level at power-on.
#include <Arduino.h>
#include <Display_ST7789.h>
#include <Gyro_QMI8658.h>
#include "RiftAudio.h"
#include "SceneArt.h"

void LCD_WriteCommand(uint8_t command);
void LCD_WriteData(uint8_t data);

namespace Board {
using namespace Rift;
static Surface screen;
alignas(4) static Color output[320*240];
static Flight flight;
static bool imuPresent, imuOk;
static float centerX, centerY;
static int calibration;
static unsigned imuErrors;
static int pilot; // Zero is live IMU. Serial 1/2 exercise alternate routes on demand.
static uint32_t previous, previousPaint, previousLcd;
static Scene previousScene;
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
    for(int i=0;i<65;++i) { sum+=bins[i]; if(uint64_t(sum)*100>=uint64_t(n)*95) return i; }
    return 64;
  }
};
static Timing stats[6];

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
static Input benchControls() {
  const int side=(pilot==1?-1:1)*(flight.leg?-1:1);
  if(flight.scene==Scene::Approach) {
    if(pilot==2 && !flight.misses) return {};  // Deliberately fly past one sealed gate.
    if(flight.leg && flight.age<2.60f) {
      if(flight.age>1.85f && flight.age<2.05f) return {float(side),-1};
      return {0,-1};
    }
    return {side*.62f,(flight.nodeY(side)-56)/28};
  }
  if(flight.scene==Scene::Impact || flight.scene==Scene::Breach)
    return {side*.62f,(flight.nodeY(side)-56)/28};
  return {};
}
static void scaleFrame() {
  for(int y=0;y<H;++y) {
    const Color *src=screen.pixels+y*W;
    Color *row=output+y*2*320;
    for(int x=0;x<W;++x) row[x*2]=row[x*2+1]=src[x];
    memcpy(row+320,row,320*sizeof(Color));
  }
}
static void resetFlight(int mode) {
  flight=Flight{}; pilot=mode;
  for(auto &item:stats) item=Timing{};
  previous=0;
}
static void commands() {
  if(!Serial.available()) return;
  const int c=Serial.read();
  if(c=='D') {
    Serial.printf("RIFT_RUNNER build=flow scene=%s leg=%d t=%.2f pilot=%d route=%d,%d last=%d,%d laps=%u misses=%u shots=%u hits=%u passes=%u rolls=%u grazes=%u dodges=%u imu=%d imu_errors=%u audio=%d played=%u audio_errors=%u\n",
      name(flight.scene),flight.leg,flight.age,pilot,flight.choice[0],flight.choice[1],flight.lastRoute[0],flight.lastRoute[1],flight.laps,flight.misses,flight.shots,flight.hits,
      flight.passes,flight.rolls,flight.grazes,flight.dodges,imuOk,imuErrors,RiftAudio::ready,
      unsigned(RiftAudio::played.load()),unsigned(RiftAudio::errors.load()));
  } else if(c=='M') {
    for(int i=0;i<6;++i) {
      const auto &s=stats[i];
      if(s.n) Serial.printf("RIFT_TIME scene=%s n=%u fps=%.2f p95_ms=%d max_ms=%.1f paint_ms=%.2f lcd_ms=%.2f\n",
        name(Scene(i)),unsigned(s.n),s.n*1e6/double(s.sumUs),s.p95(),s.maxUs/1000.,
        s.paintUs/1000./s.n,s.lcdUs/1000./s.n);
    }
    Serial.println("RIFT_TIME_END");
  } else if(c=='F') {
    Serial.printf("RIFT_FRAME scene=%s leg=%d age=%.3f w=%d h=%d bytes=%u\n",
      name(flight.scene),flight.leg,flight.age,W,H,unsigned(sizeof(screen.pixels)));
    Serial.setTxTimeoutMs(150);
    Serial.write(reinterpret_cast<const uint8_t *>(screen.pixels),sizeof(screen.pixels));
    Serial.setTxTimeoutMs(15);
  } else if(c=='1' || c=='2' || c=='R') {
    resetFlight(c=='R'?0:c-'0'); return;
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
  RiftAudio::begin();
}
void loop() {
  using namespace Board;
  commands();
  const uint32_t start=micros(), interval=previous?start-previous:0;
  if(interval) stats[int(previousScene)].add(interval,previousPaint,previousLcd);
  previous=start;
  Input input=readControls();
  if(pilot) input=benchControls();
  const uint32_t drawStart=micros();
  const Cue cue=flight.step(interval?std::min(.06f,interval*1e-6f):.026f,input);
  if(cue!=Cue::Silent) RiftAudio::play(cue);
  previousScene=flight.scene;
  drawFrame(screen,flight);
  if(!imuOk || calibration<32) tag(screen,4,107,imuOk?"HOLD LEVEL":"IMU OFFLINE",gold);
  scaleFrame();
  const uint32_t flush=micros();
  LCD_addWindow(0,0,319,239,output);  // Driver RAMCTRL expects little-endian RGB565.
  previousPaint=flush-drawStart; previousLcd=micros()-flush;
  delay(1);
}
