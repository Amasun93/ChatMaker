#pragma once
#include "Pixels.h"

namespace Rift {
struct V { float x,y,z; };
struct Facet { V a,b,c; Color color; };
constexpr Color hull = rgb(210,225,227), pearl = rgb(255,241,211), steel = rgb(121,139,159),
  dusk = rgb(63,71,105), shadow = rgb(39,40,67), orange = rgb(253,111,44),
  canopy = rgb(26,91,121), glass = rgb(98,230,226);
struct Airframe {
  struct Projected { P a,b,c; float depth; Color color; };
  Projected faces[72];
  int count=0;
  Surface &s;
  float sx,sy,size,cs,sn,cb,sb,ce,se;
  Airframe(Surface &screen,float x,float y,float scale,float yaw,float elevation,float bank):
    s(screen),sx(x),sy(y),size(scale),cs(cosf(yaw)),sn(sinf(yaw)),
    cb(cosf(bank)),sb(sinf(bank)),ce(cosf(elevation)),se(sinf(elevation)) {}
  P point(V v,float &d) const {
    const float xx=v.x*cb-v.y*sb, yy=v.y*cb+v.x*sb;
    const float horizontal=xx*cs+v.z*sn, z=v.z*cs-xx*sn;
    d=z*ce-yy*se;
    const float k=size*75/(75+d*.60f);
    return xy(sx+horizontal*k,sy-(yy*ce+z*se)*k);
  }
  void face(V a,V b,V c,Color color) {
    float da,db,dc;
    Projected &p=faces[count++];
    p.a=point(a,da); p.b=point(b,db); p.c=point(c,dc);
    p.depth=(da+db+dc)/3; p.color=color;
  }
  void quad(V a,V b,V c,V d,Color color) { face(a,b,c,color); face(a,c,d,color); }
  void draw(float time) {
    const V nose{0,.3f,20}, tail{0,0,-10}, keel{0,-2,-4}, spine{0,3.2f,-4};
    for(int side:{-1,1}) {
      const float u=float(side);
      const V root{u*2,0,7}, leading{u*15,-.4f,-7}, tip{u*16,-.4f,-12},
              trailing{u*3,-.4f,-8}, shoulder{u*3,0,-5};
      face(root,leading,trailing,side<0?steel:hull);
      face(leading,tip,trailing,side<0?dusk:steel);
      face({u*12,-.12f,-5},{u*15,-.12f,-7},{u*16,-.12f,-12},orange);
      face(root,trailing,shoulder,shadow);
      face(nose,root,spine,side<0?hull:pearl);
      face(nose,root,keel,dusk);
      face(root,spine,shoulder,steel);
      face(spine,shoulder,tail,side<0?dusk:hull);
      face(keel,shoulder,tail,shadow);
      // Raised smoked-glass cockpit, a red dorsal flash and twin engine nacelles.
      face({0,1.7f,11},{u*1.7f,2,3},{0,4,1},side<0?canopy:glass);
      face({0,4,1},{u*1.7f,2,3},spine,side<0?deep:canopy);
      const V a{u*5,1,1}, b{u*7.8f,.3f,-9}, c{u*4,.1f,-10}, crest{u*5.7f,2.5f,-6};
      face(a,b,crest,steel); face(a,c,crest,pearl);
      face(b,c,crest,dusk);
      face({u*6,1,-5},{u*8,6.5f,-10},{u*6,1,-10},side<0?orange:red);
      const V l{u*4.4f,-.3f,-10.1f}, r{u*7.1f,-.3f,-10.1f}, mid{u*5.8f,1.1f,-10.8f};
      const float jet=5.7f+1.9f*sinf(time*29+side);
      const V flare{u*5.8f,-.55f,-10.3f-jet};
      face(l,r,flare,magenta);
      face(l,mid,flare,orange);
      face({u*5,-.1f,-10.7f},{u*6.7f,-.1f,-10.7f},{u*5.8f,-.2f,-13.8f},milk);
    }
    face({0,3.3f,-2},{-.65f,2.5f,-7},{.65f,2.5f,-7},orange);
    std::sort(faces,faces+count,[](const Projected &a,const Projected &b){return a.depth>b.depth;});
    for(int i=0;i<count;++i) { const auto &f=faces[i]; s.tri(f.a,f.b,f.c,f.color); }
  }
};
} // namespace Rift
