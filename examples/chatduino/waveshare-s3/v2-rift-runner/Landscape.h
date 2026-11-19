#pragma once
#include "Pixels.h"
namespace Rift {
enum class World { Orbit, Glacier, Furnace, Dawn };
inline World biome(const Flight &f) {
  if (f.scene==Scene::Dawn) return World::Dawn;
  if (!f.leg) return World::Orbit;
  return f.frozenWorld()?World::Glacier:World::Furnace;
}
struct Scenery { Color zenith,haze,nearRock,farRock,lamp,river; };
constexpr Scenery orbitSky{rgb(14,15,45),rgb(126,74,143),rgb(39,39,69),rgb(82,75,130),rgb(255,161,81),rgb(42,51,87)};
constexpr Scenery iceSky{rgb(9,38,82),rgb(145,231,219),rgb(24,69,107),rgb(70,145,163),mint,rgb(49,150,182)};
constexpr Scenery fireSky{rgb(41,17,53),rgb(255,168,89),rgb(69,37,57),rgb(137,66,77),rgb(255,116,43),rgb(194,57,44)};
constexpr Scenery dawnSky{rgb(43,37,84),rgb(251,183,137),rgb(65,53,91),rgb(160,105,130),gold,rgb(131,92,124)};
inline const Scenery &palette(World w) {
  switch(w) { case World::Glacier: return iceSky; case World::Furnace: return fireSky;
    case World::Dawn: return dawnSky; default: return orbitSky; }
}
inline void ringArc(Surface &s,int cx,int cy,int r,bool front,Color base) {
  for(int x=-r*2;x<=r*2;++x) {
    const float q=float(x)/(r*2);
    const float depth=sqrtf(std::max(0.f,1-q*q))*(front?1.f:-1.f);
    const int y=cy+int(-.28f*x+depth*r*.24f);
    const int wide=1+int(fabsf(depth)*r*.12f);
    for(int dy=0;dy<wide;++dy) s.dot(cx+x,y+dy,dy==0?milk:(dy==wide-1?lilac:base));
  }
}
inline void planet(Surface &s,int cx,int cy,int r,float time) {
  ringArc(s,cx,cy,r,false,lilac);
  for(int y=-r;y<=r;++y) {
    const int dx=int(sqrtf(float(r*r-y*y)));
    for(int x=-dx;x<=dx;++x) {
      const float u=float(x)/r, v=float(y)/r;
      const float latitude=v+.21f*u*u-.16f*u;
      const int band=int((latitude+1.4f)*35 + 1.4f*sinf(u*5+v*6+time*.09f));
      Color c=rgb(194,123,159);
      if(latitude<-.44f) c=rgb(248,192,155);
      else if(latitude<-.15f) c=rgb(217,153,161);
      else if(latitude<.02f) c=rgb(251,180,141);
      else if(latitude>.40f) c=rgb(137,106,164);
      if((band & 7)==0) c=mix(c,milk,56);
      if(u>.23f+.23f*(1-v*v)) c=mix(c,deep,122);
      if(u>.72f-.21f*v) c=mix(c,deep,171);
      if(x==-dx && y<r*.58f) c=milk;
      s.dot(cx+x,cy+y,c);
    }
  }
  ringArc(s,cx,cy,r,true,rgb(248,178,137));
}
inline void sky(Surface &s, World w,float time,float pan,int horizon,bool close=false) {
  const auto &p=palette(w);
  for(int y=0;y<H;++y) s.span(0,W,y,y<horizon ? mix(p.zenith,p.haze,220*y/std::max(1,horizon)) :
                                mix(p.river,p.nearRock,185*(y-horizon)/std::max(1,H-horizon)));
  for(int i=0;i<60;++i) {
    const auto h=hash(i+14);
    const int x=(int(h%256)-int(pan*.20f)+256)%256-48;
    const int y=int((h>>12)%74);
    if(y>=horizon-3) continue;
    s.dot(x,y,(h%7==0)?milk:mix(p.haze,milk,85));
    if(i%17==0) { s.dot(x+1,y,lilac); s.dot(x,y-1,lilac); }
  }
  if(w==World::Orbit) {
    planet(s,int(119-pan*.20f),close?34:23,close?25:16,time);
  } else if(w==World::Glacier) {
    for(int x=0;x<W;++x) {
      const float wave=sinf(x*.042f+time*.35f)+.55f*sinf(x*.089f-time*.19f);
      const int y=int(16+wave*7);
      const int h=4+int((1+sinf(x*.13f))*3);
      for(int i=0;i<h;++i) s.dot(x,y-i,mix(p.zenith,mint,165-i*13));
    }
  } else {
    const int cx=110-int(pan*.2f), cy=horizon-19;
    s.disk(cx,cy,16,mix(p.haze,gold,145)); s.disk(cx,cy,12,milk);
    for (int y=cy+3;y<cy+14;y+=3) s.span(cx-14,cx+14,y,mix(p.haze,gold,65));
  }
  for(int layer=0;layer<2;++layer) {
    const int base=horizon-7+layer*5;
    const Color rock=mix(p.farRock,p.haze,layer==0?90:15);
    for(int x=0;x<W;x+=2) {
      const int world=x+int(pan*(.25f+.22f*layer));
      const unsigned seed=uint32_t(world+4096);
      const int cell=int(seed/11);
      const int left=int(hash(cell+layer*93)%12), right=int(hash(cell+1+layer*93)%12);
      int h=(left*(11-int(seed%11))+right*int(seed%11))/11;
      if(w==World::Furnace && (cell&3)==1) h+=5;
      s.box(x,base-h,2,horizon+2-(base-h),rock);
    }
  }
}
// Perspective slices share the same two winding banks into the distance.
inline void corridor(Surface &s,const Flight &f,World w,int horizon) {
  const auto &p=palette(w);
  const float scroll=f.travel*2.0f;
  const int row=int(scroll);
  const float frac=scroll-row;
  struct Slice { int left,right,y,topL,topR; };
  auto slice=[&](int i) {
    const int id=row+i;
    const float k=1/(.84f+(i-frac)*.40f);
    const float bend=6*sinf(id*.57f)+4*sinf(id*.27f);
    const float center=80+(bend-f.x*13)*k;
    const float half=w==World::Orbit?48.f:34.f;
    const int y=horizon+int(61*k);
    const float hl=w==World::Orbit?8.f:16.f+float(hash(id+54)%22);
    const float hr=w==World::Orbit?8.f:17.f+float(hash(id+19)%26);
    return Slice{int(center-(half+int(hash(id+41)%7))*k),int(center+(half+int(hash(id+76)%7))*k),
                 y,y-int(hl*k),y-int(hr*k)};
  };
  Slice far=slice(22);
  for(int i=21;i>=0;--i) {
    const Slice n=slice(i);
    const int id=row+i;
    const Color wall=mix(p.nearRock,p.farRock,std::min(178,i*7+int(hash(id)%39)));
    for(int side:{-1,1}) {
      const int edge=side<0?-1:W;
      const int x=side<0?n.left:n.right, fx=side<0?far.left:far.right;
      const int top=side<0?n.topL:n.topR, ft=side<0?far.topL:far.topR;
      s.quad({edge,ft},{fx,ft},{x,top},{edge,top},mix(wall,p.lamp,side<0?69:38));
      s.quad({fx,ft},{fx,far.y},{x,n.y},{x,top},side<0?wall:mix(wall,ink,50));
      s.line({fx,ft},{x,top},mix(wall,p.lamp,165));
      if(w==World::Glacier) {
        s.tri({fx,ft},{x,top},{x,(top+n.y)/2},mix(wall,mint,(id&1)?120:55));
      } else if(w==World::Furnace && (id%2==0)) {
        s.line({x,top+2},{x,n.y-1},p.lamp);
        s.line({x,n.y-1},{fx,far.y},red);
      } else if(w==World::Orbit && (id%4==0)) {
        const int ht=std::max(2,(n.y-horizon)/3);
        s.box(x-2,top-ht,4,ht,deep); s.box(x-2,top-ht,4,2,gold);
      }
      // Shore landmarks grow through perspective and leave the edge of the screen.
      const int scale=std::max(1,n.y-horizon);
      const int foot=x+side*scale/10;
      if ((id+side+1)%3==0 && scale>=6) {
        const int rise=scale*(26+int(hash(id+side+87)%24))/36;
        const int wide=std::max(2,scale/5);
        if(w==World::Glacier) {
          const P peak{foot-side*wide/2,top-rise}, base{foot,top+1};
          s.tri({foot-wide,top-1},peak,base,rgb(72,157,187));
          s.tri(base,peak,{foot+wide,top-3},rgb(140,215,210));
          s.line(peak,{foot+wide,top-3},milk);
          s.tri({foot+wide/2,top},{foot+wide,top-rise/2},{foot+2*wide,top},blue);
        } else if(w==World::Furnace) {
          const int roof=top-rise;
          s.box(foot-wide,roof,wide*2,rise,shadow);
          s.quad({foot,roof+1},{foot+wide,roof-3},{foot+wide,top-2},{foot,top+1},dusk);
          s.line({foot-wide,roof},{foot,roof+1},gold);
          for(int yy=roof+3;yy<top-1;yy+=std::max(3,scale/10)) {
            s.span(foot-wide+1,foot-1,yy,orange);
            s.dot(foot+wide/2,yy-1,gold);
          }
          s.line({foot,roof},{foot,roof-rise/5},red);
        } else if(w==World::Orbit) {
          const P base{foot,top}, elbow{foot,top-rise/2}, tip{foot-side*wide,top-rise/2-wide};
          s.line(base,elbow,steel); s.line(elbow,tip,steel);
          s.line({foot+side*2,top},tip,dusk); s.box(tip.x-1,tip.y,3,2,gold);
        }
      }
    }
    if(id%3==0) {
      const int x=(n.left+n.right)/2;
      const int len=std::max(1,(n.y-horizon)/5);
      s.span(x-len,x+len,n.y,mix(p.river,p.lamp,74));
    }
    for(int lane=1;lane<=3;++lane) {
      const int px=n.left+(n.right-n.left)*lane/4;
      const int fx=far.left+(far.right-far.left)*lane/4;
      const Color reflection=mix(p.river,p.lamp,(lane==2)?80:50);
      if(w==World::Orbit) {
        if(lane!=2 && (id&1)) s.line({fx,far.y},{px,n.y},reflection);
        if((id%3)==1) s.line({n.left,n.y},{n.right,n.y},mix(p.river,steel,48));
      } else {
        const int length=std::max(1,(n.y-horizon)/5);
        const int xx=px+int(hash(id+lane)%7)-3;
        s.span(xx-length,xx+length,n.y+lane-2,reflection);
        if(w==World::Furnace && (id+lane)%3==0)
          s.dot(xx,n.y-2-int(fmodf(f.clock*8+id,9)),gold);
      }
    }
    far=n;
  }
}
} // namespace Rift
