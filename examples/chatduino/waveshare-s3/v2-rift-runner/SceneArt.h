#pragma once
#include "Interceptor.h"
#include "Landscape.h"
namespace Rift {
inline Color signal(int side) { return side<0?mint:gold; }
inline void bracket(Surface &s,int x,int y,int r,Color c,int n=3) {
  for(int dx:{-1,1}) for(int dy:{-1,1}) {
    s.line({x+dx*r,y+dy*r},{x+dx*(r-n),y+dy*r},c);
    s.line({x+dx*r,y+dy*r},{x+dx*r,y+dy*(r-n)},c);
  }
}
struct GateCamera {
  float x,y,k,skew;
  P at(float u,float v,float z=0) const { return xy(x+(u+skew*v+.50f*z)*k,y+(v-.55f*z)*k); }
};
inline void gate(Surface &s,const Flight &f,GateCamera cam,int open,float breakup) {
  auto panel=[&](float x,float y,float w,float h,Color c,float z=0) {
    s.quad(cam.at(x,y,z),cam.at(x+w,y,z),cam.at(x+w,y+h,z),cam.at(x,y+h,z),c);
  };
  auto stroke=[&](float x,float y,float x2,float y2,Color c) { s.line(cam.at(x,y),cam.at(x2,y2),c); };
  panel(-62,-22,124,5,dusk,-3); panel(-62,-22,124,3,steel);
  panel(-55,-21,110,1,hull);
  for(int i=-53;i<=51;i+=8) panel(i,-19,3,2,(i&8)?orange:shadow);
  for(int side:{-1,1}) {
    const int cx=side*33, cy=int(f.nodeY(side)-56);
    const Color light=signal(side);
    const int pylon=side*59;
    panel(pylon-2,-26,5,50,deep,-3); panel(pylon-2,-25,4,49,dusk);
    panel(pylon-2,-25,2,17,steel); panel(pylon-2,-5,2,7,light);
    panel(cx-11,cy-20,22,3,deep); panel(cx-9,cy-20,12,2,light);
    const P outline[]={cam.at(cx-18,cy-10),cam.at(cx-10,cy-17),cam.at(cx+10,cy-17),
      cam.at(cx+18,cy-9),cam.at(cx+18,cy+10),cam.at(cx+10,cy+17),
      cam.at(cx-10,cy+17),cam.at(cx-18,cy+9)};
    if(side!=open || breakup<.80f) {
      const float pull=side==open?ease(breakup):0;
      for(int row=-14;row<=14;++row) {
        const int half=std::min(16,25-std::abs(row));
        const int gap=int((half+1)*pull);
        if(gap>=half) continue;
        const Color grid=(row+int(f.clock*9))%5==0?mix(ink,light,115):mix(ink,light,47);
        stroke(cx-half,cy+row,cx-gap,cy+row,grid);
        stroke(cx+gap,cy+row,cx+half,cy+row,grid);
      }
    }
    for(int i=0;i<8;++i) {
      s.line(outline[i],outline[(i+1)%8],(i%3==0)?milk:light);
    }
    for(int dir:{-1,1}) {
      panel(cx+dir*17-2,cy-9,4,18,steel);
      panel(cx+dir*17-2,cy-7,3,5,ink);
      panel(cx+dir*17-2,cy+4,3,3,orange);
    }
    if(side!=open || breakup<=0) {
      float spin=f.clock*1.9f;
      P p[4];
      for(int i=0;i<4;++i) p[i]=cam.at(cx+6*cosf(spin+i*pi/2),cy+6*sinf(spin+i*pi/2),1);
      s.quad(p[0],p[1],p[2],p[3],light); s.tri(p[0],p[1],p[2],milk);
      const P a=cam.at(cx,cy,1);
      s.box(a.x-1,a.y-1,3,3,ink);
    }
  }
  panel(-3,-21,6,14,dusk); panel(-2,-20,2,9,hull);
}
inline void explosion(Surface &s,int x,int y,float t,Color light) {
  if(t<0 || t>1.28f) return;
  const float a=unit(t/1.0f);
  if(t<.25f) {
    s.disk(x,y,int(12*(1-t/.25f))+2,milk); s.circle(x,y,int(6+75*t),light);
  }
  if(t<.54f) {
    const float heat=1-t/.54f;
    for(int i=0;i<7;++i) {
      const float theta=i*2*pi/7+.27f, spread=5+18*t;
      const int cx=x+int(cosf(theta)*spread),cy=y+int(sinf(theta)*spread*.72f);
      s.disk(cx,cy,1+int(heat*9),i%2?orange:magenta);
      s.disk(cx-1,cy-1,1+int(heat*6),gold);
    }
    s.disk(x,y,int(11*heat)+1,milk);
  }
  s.circle(x,y,int(6+38*ease(a)),mix(deep,light,int(236*(1-a))));
  for(int i=0;i<48;++i) {
    const uint32_t h=hash(i+438);
    const float angle=(h%6283)*.001f, speed=18+float((h>>12)%74);
    const float vx=cosf(angle)*speed, vy=sinf(angle)*speed*.79f;
    const float d=t*(1.3f-.32f*t);
    const P p=xy(x+vx*d,y+vy*d+17*t*t);
    const Color col=(i%4==0)?milk:(i%3==0?orange:light);
    if(i%4==0 && t>.12f) {
      const int r=std::max(1,3-int(2*t));
      s.tri({p.x-r,p.y+r},{p.x+r+1,p.y},{p.x,p.y-r},mix(steel,col,135));
    } else if(t<float(65+h%60)/100.f) {
      s.line(xy(p.x-vx*.055f,p.y-vy*.055f),p,col);
    }
  }
}
inline void streaks(Surface &s,float t,int x,int y,int count,Color tint) {
  for(int i=0;i<count;++i) {
    const uint32_t h=hash(396+i);
    const float a=(h%6283)*.001f;
    const float phase=fmodf(float((h>>13)%128)/128+t*(.68f+(i%4)*.13f),1.f);
    const float d=4+phase*phase*134, from=d*(.74f+.15f*(i%2));
    s.line(xy(x+cosf(a)*from,y+sinf(a)*from*.8f),xy(x+cosf(a)*d,y+sinf(a)*d*.8f),
           mix(deep,tint,int(80+155*phase)));
  }
}
inline void tag(Surface &s,int x,int y,const char *label,Color c) {
  const int width=int(strlen(label))*4+6;
  s.box(x,y,width,9,ink); s.box(x,y,1,9,c); s.word(x+4,y+2,label,c);
}
inline void flagship(Surface &s,float cx,float cy,float k,Color trim) {
  auto a=[&](float x,float y){return xy(cx+x*k,cy+y*k);};
  s.quad(a(-36,-2),a(22,-3),a(36,1),a(-17,5),shadow);
  s.tri(a(-36,-2),a(26,-4),a(36,1),steel);
  s.tri(a(-24,-1),a(-12,-6),a(13,-3),hull);
  s.quad(a(-15,-5),a(-10,-10),a(-4,-10),a(-3,-5),dusk);
  s.line(a(-20,2),a(25,0),trim);
  for(int i=0;i<5;++i) s.line(a(-16+i*7,0),a(-14+i*7,0),milk);
}
inline void drawFrame(Surface &s,const Flight &f) {
  const World w=biome(f);
  const auto &p=palette(w);
  const int open=f.choice[f.leg];
  const Color beam=signal(open);
  if(f.scene==Scene::Orbit) {
    const float cut=ease(f.age/1.35f);
    sky(s,w,f.clock,28*cut,77-int(35*cut),true);
    flagship(s,32-58*cut,46-15*cut,.75f,gold);
    Airframe(s,70+14*cut,69+20*cut,2.48f-1.27f*cut,1.45f*(1-cut),
             .28f+.16f*cut,-.24f+.19f*cut).draw(f.clock);
    if(f.age<2.4f) { tag(s,7,9,"01 / ORBIT",mint); s.word(8,98,"RIFT RUNNER",milk,2); }
    return;
  }
  if(f.scene==Scene::Dawn) {
    const float reveal=ease(f.age/1.1f);
    sky(s,w,f.clock,20*sinf(f.clock*.23f),68);
    const float k=.68f+reveal*.62f;
    flagship(s,90,51,k,signal(f.choice[1]));
    for(int i=0;i<4;++i) {
      const int x=14+i*41+int(4*sinf(f.clock+i));
      s.line({x-5,67+i%2*6},{x,67+i%2*6},lilac);
      s.line({x,67+i%2*6},{x+2,65+i%2*6},milk);
    }
    Airframe(s,43+9*reveal+f.x*24,85+f.y*10,1.25f+.15f*reveal,1.18f,.37f,-.19f-.55f*f.bank).draw(f.clock);
    tag(s,7,9,f.frozenWorld()?"ION FJORD / CLEAR":"EMBER CITY / CLEAR",mint);
    tag(s,7,103,"FLEET FLYBY",milk);
    return;
  }
  if(f.scene==Scene::Tunnel) {
    const float a=unit(f.age/tunnelTime);
    const int cx=80+int(open*16*(1-a)-f.x*15), cy=52+int(sinf(a*pi)*6-f.y*9);
    for(int y=0;y<H;++y) s.span(0,W,y,mix(ink,deep,50+int(42*sinf(y*.08f+a*6))));
    if(a>.55f) {
      World destination=f.leg?World::Dawn:(open<0?World::Glacier:World::Furnace);
      sky(s,destination,f.clock,f.x*17,38);
      if(!f.leg) corridor(s,f,destination,38);
      else flagship(s,93,54,.9f,beam);
      const float radius=3+147*ease((a-.55f)/.45f);
      for(int y=0;y<H;++y) {
        const float v=(y-cy)*1.32f;
        const int gap=fabsf(v)<radius?int(sqrtf(radius*radius-v*v)):0;
        const Color tunnel=mix(ink,deep,50+int(42*sinf(y*.08f+a*6)));
        s.span(0,cx-gap,y,tunnel); s.span(cx+gap,W,y,tunnel);
      }
    }
    const int fade=int(255*(1-ease((a-.73f)/.27f)));
    for(int j=9;j>=0;--j) {
      const float z=fmodf(j/10.f+a*1.3f,1.f);
      const float r=6+z*z*151;
      P points[8];
      for(int i=0;i<8;++i) {
        const float theta=i*pi/4+open*(.18f+.55f*a+.33f*z);
        points[i]=xy(cx+r*cosf(theta),cy+r*.76f*sinf(theta));
      }
      if(r<4+125*ease((a-.58f)/.42f)) continue;
      for(int i=0;i<8;++i) {
        s.line(points[i],points[(i+1)%8],mix(deep,beam,int(44+185*z)*fade/255));
        if((i+j)%3==0 && z>.32f) {
          const P outer=xy(cx+(points[i].x-cx)*1.2f,cy+(points[i].y-cy)*1.2f);
          const P next=points[(i+1)%8];
          s.tri(points[i],outer,xy(points[i].x*.63f+next.x*.37f,points[i].y*.63f+next.y*.37f),
                mix(deep,beam,int(110*z)*fade/255));
        }
      }
    }
    streaks(s,f.clock*2,cx,cy,69*fade/255,beam);
    const float size=.89f-.55f*sinf(a*pi);
    Airframe(s,80+20*f.x+9*open*(1-a),81-12*sinf(a*pi)+f.y*9,size,.12f*open,.35f,
             open*.60f*sinf(a*pi)-f.bank*.62f).draw(f.clock);
    tag(s,5,5,f.leg?"FLEET CORRIDOR":(open<0?"JUMP / ION FJORD":"JUMP / EMBER CITY"),beam);
    return;
  }
  if(f.scene==Scene::Impact) {
    const float t=(f.age-contactTime)*2.7f;
    const float recoil=t>0?std::max(0.f,1-t/.40f)*sinf(t*60):0;
    const float k=1.60f+.36f*ease(f.age/.17f)-.13f*ease(t/.70f);
    const int node=int(f.nodeY(open)-56);
    const int px=86+int(4*recoil-f.x*12), py=56+int(2*recoil-f.y*8);
    sky(s,w,f.clock,35*open,48);
    corridor(s,f,w,48);
    const GateCamera lens{px-(33*open+.25f*open*node)*k,py-node*k,k,.25f*open};
    gate(s,f,lens,t>=0?open:0,unit(t/.70f));
    if(t<0) {
      const float frac=ease(f.age/contactTime);
      for(int side:{-1,1}) {
        const P start{open<0?155:4,87+side*8};
        const P a=xy(blend(start.x,px,std::max(0.f,frac-.31f)),blend(start.y,py,std::max(0.f,frac-.31f)));
        const P b=xy(blend(start.x,px,frac),blend(start.y,py,frac));
        s.line(a,b,beam); s.line({a.x,a.y+1},{b.x,b.y+1},milk);
      }
    }
    explosion(s,px,py,t,beam);
    // The ship is still piloted in this reverse angle. Its bank carries into the exit.
    Airframe(s,36+f.x*20+open*f.age*40,91+f.y*10,.66f,open*.9f,.32f,-.7f*f.bank).draw(f.clock);
    s.box(0,0,W,9,ink); s.box(0,111,W,9,ink); s.word(5,2,t<0?"PULSE CAM":"SEAL FRACTURE",milk);
    s.word(118,113,open<0?"PORT":"STARBOARD",beam);
    return;
  }
  const int horizon=38+int(-f.y*5 + (f.jolt>0?2*sinf(f.clock*75):0));
  sky(s,w,f.clock,f.x*17,horizon); corridor(s,f,w,horizon);
  const bool breached=f.scene==Scene::Breach;
  const float k=f.gateScale();
  const GateCamera chase{80-53*f.x*(k-1),56-28*f.y*(k-1),k,0};
  gate(s,f,chase,breached?open:0,breached?1.f:0.f);
  if(f.leg && !breached) {
    const float q=f.hazard;
    const float lane=int(f.age/2.8f)%2==0?.16f:-.38f;
    const int x=80+int(lane*43), y=horizon+int(60*q*q), r=2+int(q*q*10);
    if(q>.13f) {
      s.line({x-r,y},{x,y-r/2},magenta); s.line({x,y-r/2},{x+r,y},magenta);
      s.line({x-r+1,y+1},{x+r,y+1},gold);
    }
  }
  const float turn=f.roll>0?f.rollDir*2*pi*ease(1-f.roll/.70f):0;
  if(f.roll>0) streaks(s,f.clock,80,59,17,mint);
  Airframe ship(s,80+f.x*35,93+f.y*9,1.15f,-.22f*f.bank,.47f,-.67f*f.bank+turn);
  ship.draw(f.clock);
  const int aimX=int(f.sightX()), aimY=int(f.sightY());
  if(!breached) {
    bracket(s,aimX,aimY,5,mint);
    s.dot(aimX,aimY,milk);
  } else {
    const P exit=chase.at(33*open,f.nodeY(open)-56);
    const int cx=exit.x, cy=exit.y;
    const int n=int(fmodf(f.age*12,7));
    for(int i=0;i<2;++i) {
      const int x=cx-open*(16+i*7-n);
      s.line({x-3*open,cy-3},{x,cy},milk); s.line({x,cy},{x-3*open,cy+3},milk);
    }
  }
  const char *place=!f.leg?"01 / ORBIT":(f.frozenWorld()?"02 / ION FJORD":"02 / EMBER CITY");
  tag(s,4,4,place,p.lamp);
  if(f.jolt>0) tag(s,119,4,"GRAZE",red);
  else if(f.roll>0) tag(s,119,4,"ROLL",mint);
  tag(s,4,107,breached?(open<0?"CUT LEFT":"CUT RIGHT"):(f.missFlash>0?"NEXT GATE":"SWEEP TO FIRE"),breached?beam:milk);
}
} // namespace Rift
