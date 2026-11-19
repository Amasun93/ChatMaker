#pragma once
#include "Pixels.h"
namespace Rally {
struct Camera {
  Vec eye,right,up,forward;
  float focal;
  Camera(const Circuit &c,const Race &r) {
    const Rail road=c.sample(r.idx);
    const Vec focus=road.at(r.x*.83f,1.0f+r.lift*.47f,r.cameraLead);
    eye=road.at(r.x*.74f+r.cameraSide,r.cameraHeight+r.lift*.25f,-r.cameraBack);
    forward=normalized(focus-eye);
    right=normalized(cross({0,1,0},forward)); up=cross(forward,right);
    focal=111.f+(r.duration>0?3.f:0.f);
  }
  Vec local(Vec p) const {
    Vec d=p-eye; return {dot(d,right),dot(d,up),dot(d,forward)};
  }
  P project(Vec v) const { return xy(W*.5f+focal*v.x/v.z,H*.5f-focal*v.y/v.z); }
  int horizon() const { return int(H*.5f+focal*forward.y/std::max(.2f,up.y)); }
};
struct Painter {
  Surface &s; const Camera &cam;
  static constexpr float nearPlane=1.8f;
  void polygon(const Vec *world,int count,Color c) {
    Vec v[4],clipped[6];
    int inside=0;
    for(int i=0;i<count;++i) { v[i]=cam.local(world[i]); if(v[i].z>=nearPlane) ++inside; }
    if(!inside) return;
    int n=0;
    for(int i=0;i<count;++i) {
      const Vec a=v[(i+count-1)%count],b=v[i];
      if((a.z>=nearPlane)!=(b.z>=nearPlane)) clipped[n++]=a+(b-a)*((nearPlane-a.z)/(b.z-a.z));
      if(b.z>=nearPlane) clipped[n++]=b;
    }
    P p[6]; for(int i=0;i<n;++i) p[i]=cam.project(clipped[i]);
    for(int i=2;i<n;++i) s.tri(p[0],p[i-1],p[i],c);
  }
  void quad(Vec a,Vec b,Vec c,Vec d,Color col) { const Vec v[]={a,b,c,d}; polygon(v,4,col); }
  void tri(Vec a,Vec b,Vec c,Color col) { const Vec v[]={a,b,c}; polygon(v,3,col); }
  void line(Vec a,Vec b,Color color) {
    Vec v=cam.local(a),w=cam.local(b);
    if(v.z<nearPlane && w.z<nearPlane) return;
    if(v.z<nearPlane) v=v+(w-v)*((nearPlane-v.z)/(w.z-v.z));
    if(w.z<nearPlane) w=w+(v-w)*((nearPlane-w.z)/(v.z-w.z));
    const P p=cam.project(v),q=cam.project(w);
    if((p.x<0 && q.x<0)||(p.y<0 && q.y<0)||(p.x>=W && q.x>=W)||(p.y>=H && q.y>=H)) return;
    s.line(p,q,color);
  }
};
} // namespace Rally
