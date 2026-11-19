#pragma once
#include "RallyCar.h"
#include <cstdio>
namespace Rally {
constexpr Color asphalt=rgb(53,58,74),curb=rgb(240,90,52),silt=rgb(134,98,83),
  teal=rgb(25,142,153),amber=rgb(246,160,54),basalt=rgb(89,69,81);
inline int sectorOf(int i) { i=wrapIndex(i); return i<60?0:(i<128?1:2); }
inline void background(Surface &s,const Camera &cam,int region,float time) {
  const int h=cam.horizon();
  const Color top[]={rgb(58,103,152),rgb(89,104,162),rgb(86,78,147)};
  const Color haze[]={rgb(255,195,141),rgb(255,191,139),rgb(255,167,124)};
  const Color water[]={rgb(60,131,146),rgb(157,104,91),rgb(57,121,147)};
  for(int y=0;y<H;++y) {
    const Color c=y<h?mix(top[region],haze[region],std::clamp((y-h+65)*4,0,255)):
      mix(water[region],region==1?basalt:rgb(40,85,116),std::clamp((y-h)*2,0,200));
    s.span(0,W,y,c);
  }
  const float heading=atan2f(cam.forward.x,cam.forward.z);
  const int pan=int(heading*76);
  const int sunX=22+int(106*(.5f+.5f*sinf(heading+.65f)));
  if(h>-15) {
    s.disk(sunX,h-15,11,rgb(255,220,153));s.disk(sunX,h-15,8,milk);
    for(int layer=0;layer<2;++layer) {
      const int spacing=layer?13:21;
      const int shift=pan*(layer+1)+2048;
      for(int x=0;x<W;x+=2) {
        const int n=(x+shift)/spacing, mod=(x+shift)%spacing;
        const int l=hash(n+layer*11)%13, r=hash(n+1+layer*11)%13;
        const int ridge=h-(layer?1:7)-(l*(spacing-mod)+r*mod)/spacing;
        s.box(x,ridge,2,h-ridge+1,layer?rgb(123,109,131):rgb(171,140,148));
      }
    }
    if(region==0) for(int i=0;i<18;++i) {
      int x=(i*17-pan%256+256)%256-48;
      int tall=2+int(hash(i+31)%7);
      s.box(x,h-tall,5,tall,rgb(91,107,133));
      if(i%3==0){s.line({x,h-tall},{x+6,h-tall-5},basalt);s.dot(x+6,h-tall-5,amber);}
    }
  }
  if(region!=1) for(int i=0;i<87;++i) {
    const auto seed=hash(i+56);
    const int y=h+3+int(seed%123);
    int x=(int(seed>>22)+int(time*(i%3+1))-pan)%200;
    s.span(x-16,x-14+(y-h)/11,y,mix(water[region],ivory,(i%4)*19+23));
  }
}
inline void strip(Painter &p,const Rail &a,const Rail &b,float left,float right,Color col,float y=0) {
  p.quad(a.at(left,y),a.at(right,y),b.at(right,y),b.at(left,y),col);
}
inline void road(Painter &p,const Circuit &track,int i) {
  const Rail &a=track.rails[i], &b=track.rails[wrapIndex(i+1)];
  const int sector=sectorOf(i);
  const bool alternate=(i&1)!=0;
  if(sector==2) {
    for(int side:{-1,1})
      p.quad(a.at(side*6.32f),b.at(side*6.32f),b.at(side*6.32f,-1.2f),a.at(side*6.32f,-1.2f),shadowMetal);
  } else {
    const Color ground=sector==0?rgb(125,118,114):rgb(180,116,90);
    strip(p,a,b,-17,17,mix(ground,ivory,(i%3)*7),-.12f);
  }
  strip(p,a,b,-6.32f,6.32f,alternate?ivory:curb);
  strip(p,a,b,-halfWidth,halfWidth,alternate?asphalt:rgb(57,62,77));
  for(int sign:{-1,1}) {
    const float x=sign*5.03f;
    strip(p,a,b,x-.065f,x+.065f,rgb(216,209,178));
    if((i%4)<2) {float lane=sign*1.82f;strip(p,a,b,lane-.055f,lane+.055f,alloy);}
  }
  if(i==0) {
    const Rail mid=track.sample(.50f);
    for(int tile=0;tile<12;++tile) {
      const float x=-halfWidth+tile*halfWidth/6;
      strip(p,a,mid,x,x+halfWidth/6,tile%2?tire:milk);
      strip(p,mid,b,x,x+halfWidth/6,tile%2?milk:tire);
    }
  }
  for(const auto &f:patches) {
    if(i<f.first || i>=f.end) continue;
    const float left=f.x-f.half,right=f.x+f.half;
    if(f.type==Material::Boost) {
      strip(p,a,b,left,right,teal);
      for(float sign:{-1.f,1.f}) {
        const float x=f.x+sign*f.half*.92f;
        p.quad(a.at(x),a.at(x-sign*.53f),b.at(f.x-sign*.02f),b.at(f.x+sign*.55f),mint);
      }
    } else if(f.type==Material::Gravel) {
      strip(p,a,b,left,right,i%2?rgb(151,100,71):rgb(162,112,81));
      for(int j=0;j<10;++j) {
        const auto h=hash(i*27+j);
        float x=lerp(left,right,(h%256)/256.f),z=track.spacing*((h>>12)%256)/256.f;
        p.tri(a.at(x,.05f,z),a.at(x+.28f,.17f,z+.18f),a.at(x+.45f,.05f,z),j&1?ivory:basalt);
      }
    } else {
      const float y0=rampRise(f,i),y1=rampRise(f,i+1);
      p.quad(a.at(left,y0),a.at(right,y0),b.at(right,y1),b.at(left,y1),alternate?amber:curb);
      for(float x:{left,right}) {
        p.quad(a.at(x,0),b.at(x,0),b.at(x,y1),a.at(x,y0),burnt);
        p.line(a.at(x,y0+.04f),b.at(x,y1+.04f),milk);
        p.line(a.at(x,y0+.03f),b.at(f.x,y1+.03f),ivory);
      }
      if(i+1==f.end) p.quad(b.at(left),b.at(right),b.at(right,y1),b.at(left,y1),burnt);
    }
  }
}
inline void crate(Painter &p,const Rail &r,float x,float y,float z,float w,float h,float d,Color col) {
  auto a=[&](float u,float v,float t){return r.at(x+u,y+v,z+t);};
  // The visible faces depend on the camera position, including in the bridge and jump views.
  const bool left=dot(p.cam.eye-r.at(x,y,z),r.right)<0;
  const float side=left?-w:w;
  const bool back=dot(p.cam.eye-r.at(x,y,z),r.forward)<0;
  const float end=back?-d:d;
  p.quad(a(side,0,-d),a(side,0,d),a(side,h,d),a(side,h,-d),mix(col,tire,54));
  p.quad(a(-w,0,end),a(w,0,end),a(w,h,end),a(-w,h,end),col);
  p.quad(a(-w,h,-d),a(w,h,-d),a(w,h,d),a(-w,h,d),mix(col,ivory,66));
}
inline void prop(Painter &p,const Circuit &track,int i) {
  const auto &r=track.rails[i]; const int sec=sectorOf(i), side=(i%4<2?-1:1);
  if(sec==0 && i%12==0) {
    // Dockside gantry with a counterweight, cantilever and suspended hook.
    const float x=10*side;
    crate(p,r,x,0,0,.45f,11,.62f,burnt);
    p.line(r.at(x-2*side,0,1),r.at(x,9),amber);
    p.line(r.at(x,10),r.at(x-7*side,9),curb);
    p.line(r.at(x,13),r.at(x-7*side,9),amber);
    p.line(r.at(x,13),r.at(x+3*side,10),amber);
    crate(p,r,x+2*side,9,0,1.6f,1.1f,.8f,curb);
    p.line(r.at(x-6*side,9),r.at(x-6*side,6),shadowMetal);
    p.line(r.at(x-6*side,6),r.at(x-5.6f*side,5.7f),gold);
  } else if(sec==0) {
    float x=side*(9.f+i%2);
    Color c=i%3?teal:curb;
    crate(p,r,x,0,0,1.6f,1.9f,3,c);
    if(i%4==2) crate(p,r,x,1.9f,0,1.55f,1.8f,2.95f,blue);
    for(int k=-2;k<=2;++k) p.line(r.at(x-side*1.61f,.15f,k),r.at(x-side*1.61f,1.7f,k),mix(c,tire,94));
  } else if(sec==1) {
    const float x=side*(9.f+i%5),h=2.5f+(hash(i)%8);
    Vec a=r.at(x-3,0,-3),b=r.at(x+3,0,-3),c=r.at(x+2,0,3);
    Vec aa=r.at(x-1.9f,h,-1.4f),bb=r.at(x+.85f,h,-1.6f),cc=r.at(x+.6f,h,1.1f);
    p.quad(a,c,cc,aa,rgb(174,98,79)); p.quad(b,c,cc,bb,basalt);
    p.quad(a,b,bb,aa,rgb(197,131,94)); p.tri(aa,bb,cc,rgb(237,175,119));
    p.quad(a+(aa-a)*.31f,b+(bb-b)*.31f,b+(bb-b)*.42f,a+(aa-a)*.42f,rgb(161,93,77));
    p.line(a+(aa-a)*.62f,b+(bb-b)*.60f,rgb(237,169,113));
    if(i%6==0) {
      const float sx=side*6.7f;
      p.line(r.at(sx),r.at(sx,2.7f),shadowMetal);
      p.quad(r.at(sx-1,1.5f),r.at(sx+1,1.5f),r.at(sx+1,2.7f),r.at(sx-1,2.7f),gold);
      p.line(r.at(sx-.6f*side,1.7f),r.at(sx+.4f*side,2.1f),ink);
      p.line(r.at(sx+.4f*side,2.1f),r.at(sx-.6f*side,2.5f),ink);
    }
  } else if(i%12==0) {
    for(int t:{-1,1}) {
      crate(p,r,t*6.6f,-8,0,.40f,18,.55f,teal);
      p.line(r.at(t*6.6f,10),r.at(t*6.4f,.5f,11),ivory);
      p.line(r.at(t*6.6f,10),r.at(t*6.4f,.5f,-11),gold);
      p.line(r.at(t*6.6f,7),r.at(t*6.4f,.5f,-5.5f),ivory);
    }
    p.line(r.at(-6.6f,9.2f),r.at(6.6f,9.2f),mint);
  } else {
    for(int t:{-1,1}) {
      const float x=6.26f*t;
      p.line(r.at(x),r.at(x,.9f),ivory);
      p.line(r.at(x,.85f),track.rails[wrapIndex(i+2)].at(x,.85f),teal);
    }
  }
}
inline void dust(Painter &p,const Rail &r,const Race &race) {
  const bool rough=race.rough>.2f,boost=race.boost>.02f;
  if(!rough && !boost && race.landing<=0) return;
  for(int i=0;i<20;++i) {
    const float age=fmodf(race.clock*(rough?2.2f:3.f)+i*.237f,1.f);
    const float side=(i&1)?-1:1;
    Vec a=r.at(race.x+side*(.8f+.8f*age),.18f+age*(rough?1.3f:.26f),-1.6f-age*(rough?3.9f:4.9f));
    if(boost && !rough) p.line(a,a-r.forward*.36f,age<.4f?mint:teal);
    else p.tri(a,a+r.right*(.12f+.27f*age),a+Vec{0,.28f,0},i%3?rgb(198,154,105):ivory);
  }
}
inline void drawFrame(Surface &s,const Circuit &track,const Race &r) {
  const Camera cam(track,r); Painter p{s,cam};
  const int region=r.sector();
  background(s,cam,region,r.clock);
  struct Item {float depth;int id;};
  Item deck[62],objects[65]; int n=0,objectCount=0;
  const Rail here=track.sample(r.idx);
  const float playerDepth=cam.local(here.at(r.x,r.lift)).z;
  for(int d=-7;d<52;++d) {
    const int i=wrapIndex(int(r.idx)+d);
    const Vec v=cam.local(track.rails[i].center);
    if(v.z<-9 || v.z>160 || fabsf(v.x)>v.z+29) continue;
    deck[n++]={v.z,i};
    // A roadside tower can fall between the tracking camera and the car during a jump.
    // Let those foreground props leave the shot as the camera comes alongside them.
    if(i%2==0 && v.z>playerDepth+2.f && v.z<105) objects[objectCount++]={v.z,i};
  }
  auto farFirst=[](const Item &a,const Item &b){return a.depth>b.depth;};
  std::sort(deck,deck+n,farFirst);
  for(int j=0;j<n;++j) road(p,track,deck[j].id);
  const float paceDistance=4+r.clock*29.1f/track.spacing;
  const float paceIndex=fmodf(paceDistance,float(sections));
  const Rail pace=track.sample(paceIndex);
  const float paceLane=-2.6f+1.0f*sinf(paceIndex*.11f);
  const Vec competitor=cam.local(pace.at(paceLane));
  if(competitor.z>3.5f && competitor.z<66 && fabsf(competitor.x)<competitor.z*.82f)
    objects[objectCount++]={competitor.z,-2};
  objects[objectCount++]={cam.local(here.at(r.x)).z,-1};
  std::sort(objects,objects+objectCount,farFirst);
  static CarPaint car;
  for(int j=0;j<objectCount;++j) {
    const int id=objects[j].id;
    if(id>=0) {prop(p,track,id);continue;}
    const bool player=id==-1;
    const Rail &rail=player?here:pace; const float x=player?r.x:paceLane;
    p.quad(rail.at(x-1.02f,.035f,-1.95f),rail.at(x+1.18f,.035f,-1.78f),
           rail.at(x+1.32f,.035f,1.78f),rail.at(x-.95f,.035f,2.10f),rgb(39,42,59));
    if(player && r.duration<=0) dust(p,here,r);
    float pitch=0,bodyLift=player?r.lift:0,roll=player?r.roll:0;
    if(!player) {
      for(const auto &ramp:patches) {
        if(ramp.type!=Material::Ramp || fabsf(paceLane-ramp.x)>ramp.half) continue;
        if(paceIndex>=ramp.first && paceIndex<ramp.end) {
          bodyLift=rampRise(ramp,paceIndex);pitch=.12f;
        } else if(paceIndex>=ramp.end) {
          const float t=(paceIndex-ramp.end)*track.spacing/(29.1f*1.26f);
          if(t<1) bodyLift=(1-t)*rampRise(ramp,ramp.end)+12*t*(1-t);
        }
      }
    }
    if(player) {
      if(r.duration>0) pitch=.12f*cosf(pi*r.air/r.duration);
      else if(r.material==Material::Ramp) pitch=.12f;
      if(r.landing>0) bodyLift+=.12f*sinf((.32f-r.landing)*35)*r.landing/.32f;
      if(r.rough>.2f) bodyLift+=.045f*r.rough*sinf(r.clock*78);
      roll-=.06f*r.vx/8;
    }
    car.draw(s,cam,rail,x,bodyLift,roll,player?r.vx*.024f:0,pitch,r.clock,!player);
  }
  const char *title=region==0?"01 DOCKS":(region==1?"02 QUARRY":"03 SKYBRIDGE");
  s.box(3,3,int(strlen(title))*4+6,9,ink);s.word(6,5,title,ivory);
  const bool ahead=r.laps*float(sections)+r.idx>paceDistance;
  s.box(3,13,18,9,ink);s.word(6,15,ahead?"1/2":"2/2",ahead?gold:alloy);
  // Fixed course outline and live position.
  s.box(132,2,26,28,ink);
  auto mini=[](Vec v){return xy(139+v.x*.104f,15-v.z*.102f);};
  for(int i=0;i<sections;i+=4)
    s.line(mini(track.rails[i].center),mini(track.rails[wrapIndex(i+4)].center),i<60?teal:(i<128?curb:lilac));
  P mark=mini(here.center);s.box(mark.x-1,mark.y-1,3,3,milk);
  char label[32]; snprintf(label,sizeof label,"%d",int(r.speed*3.6f+.5f));
  s.box(3,101,42,16,ink); s.word(6,104,label,milk,2); s.word(30,108,"KMH",amber);
  snprintf(label,sizeof label,"L%u %02d-%02d",(r.laps%99)+1,int(r.lapTime),int(r.lapTime*100)%100);
  s.box(110,106,47,11,ink);s.word(113,109,label,ivory);
  const char *status=r.duration>0?"BARREL ROLL":(r.landing>0?"TOUCHDOWN":(r.rough>.35f?"GRAVEL":(r.boost>0?"BOOST":"")));
  if(r.laps && r.lapTime<2.4f) {snprintf(label,sizeof label,"BEST %02d-%02d",int(r.best),int(r.best*100)%100);status=label;}
  if(*status) {const int w=int(strlen(status))*4+6;s.box(79-w/2,108,w,9,ink);s.word(82-w/2,110,status,region==1?gold:mint);}
}
} // namespace Rally
