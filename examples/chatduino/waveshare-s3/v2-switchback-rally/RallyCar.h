#pragma once
#include "Camera.h"
namespace Rally {
constexpr Color tire=rgb(21,22,35), rubber=rgb(43,45,53), shadowMetal=rgb(50,60,75),
                alloy=rgb(163,181,183), ivory=rgb(249,230,181), sunYellow=rgb(255,184,50),
                burnt=rgb(186,69,33), windscreen=rgb(39,111,137), glassLight=rgb(83,183,187);
struct CarPaint {
  struct Face { P points[4]; float z; Color color; int count; };
  Face faces[130]; int count=0;
  Vec origin,basisX,basisY,basisZ;
  const Camera *camera=nullptr;
  Vec world(float x,float y,float z) const {return origin+basisX*x+basisY*y+basisZ*z;}
  void face(Vec a,Vec b,Vec c,Vec d,Color color,int n=4) {
    Vec v[]={a,b,c,d};
    Face &f=faces[count]; f.z=0; f.count=n; f.color=color;
    for(int i=0;i<n;++i) {
      Vec p=camera->local(world(v[i].x,v[i].y,v[i].z));
      if(p.z<1.5f) return;
      f.points[i]=camera->project(p); f.z+=p.z;
    }
    f.z/=n; ++count;
  }
  void wheel(float side,float z,float angle) {
    const float cx=side*1.065f, cy=-.26f;
    Vec inner[8],outer[8];
    for(int i=0;i<8;++i) {
      const float a=i*pi/4;
      const float yy=cy+.405f*cosf(a), zz=z+.405f*sinf(a);
      inner[i]={cx-side*.21f,yy,zz}; outer[i]={cx+side*.14f,yy,zz};
    }
    for(int i=0;i<8;++i) {
      const int j=(i+1)&7;
      face(inner[i],outer[i],outer[j],inner[j],i==0||i==7?rubber:tire);
    }
    const float rim=cx+side*.15f;
    for(int i=0;i<4;++i) {
      const int a=i*2,b=(a+1)&7,c=(a+2)&7;
      face({rim,cy,z},outer[a],outer[b],outer[c],rubber);
    }
    const float dy=.205f*cosf(angle), dz=.205f*sinf(angle);
    face({rim+side*.015f,cy+dy,z+dz},{rim+side*.015f,cy-dz,z+dy},
         {rim+side*.015f,cy-dy,z-dz},{rim+side*.015f,cy+dz,z-dy},ivory);
  }
  void draw(Surface &s,const Camera &cam,const Rail &rail,float lane,float lift,float roll,
            float yaw,float pitch,float clock,bool rival) {
    count=0; camera=&cam;
    const Vec vertical{0,1,0};
    const Vec horizontal=rail.right*cosf(yaw)-rail.forward*sinf(yaw);
    const Vec nose=rail.forward*cosf(yaw)+rail.right*sinf(yaw);
    basisZ=nose*cosf(pitch)+vertical*sinf(pitch);
    const Vec verticalPitch=vertical*cosf(pitch)-nose*sinf(pitch);
    basisX=horizontal*cosf(roll)+verticalPitch*sinf(roll);
    basisY=verticalPitch*cosf(roll)-horizontal*sinf(roll);
    origin=rail.at(lane,.67f+lift);
    const Color paint=rival?rgb(75,181,212):sunYellow;
    const Color shade=rival?rgb(39,103,146):burnt;
    // Each station describes the coupe body at one point from the tail to the nose.
    struct Station {float z,wide,top,edge;};
    const Station body[]={{-2.05f,.98f,.29f,.06f},{-1.29f,1.12f,.37f,.16f},
                           {.94f,1.11f,.28f,.10f},{1.95f,.98f,.03f,-.14f}};
    for(int i=0;i<3;++i) {
      const auto a=body[i],b=body[i+1];
      face({-a.wide*.88f,a.top,a.z},{a.wide*.88f,a.top,a.z},
           {b.wide*.88f,b.top,b.z},{-b.wide*.88f,b.top,b.z},paint);
      for(int k:{-1,1}) {
        float t=float(k);
        face({t*a.wide*.88f,a.top,a.z},{t*a.wide,a.edge,a.z},
             {t*b.wide,b.edge,b.z},{t*b.wide*.88f,b.top,b.z},k<0?ivory:paint);
        face({t*a.wide,a.edge,a.z},{t*a.wide,-.32f,a.z},
             {t*b.wide,-.32f,b.z},{t*b.wide,b.edge,b.z},shade);
      }
    }
    face({-1,-.32f,-2.05f},{1,-.32f,-2.05f},{.99f,.26f,-2.05f},{-.99f,.26f,-2.05f},shade);
    face({-.98f,-.32f,1.95f},{.98f,-.32f,1.95f},{.98f,.02f,1.95f},{-.98f,.02f,1.95f},paint);
    face({-1,-.34f,-1.95f},{1,-.34f,-1.95f},{1,-.34f,1.88f},{-1,-.34f,1.88f},shadowMetal);
    face({-.18f,-.355f,-1.74f},{.18f,-.355f,-1.74f},{.18f,-.355f,1.4f},{-.18f,-.355f,1.4f},alloy);
    // Rear glass, sloping windshield and contrasting roof with an offset racing stripe.
    face({-.84f,.37f,-1.25f},{.84f,.37f,-1.25f},{.69f,.89f,-.68f},{-.69f,.89f,-.68f},windscreen);
    face({-.69f,.89f,-.68f},{.69f,.89f,-.68f},{.69f,.91f,.12f},{-.69f,.91f,.12f},ivory);
    face({-.69f,.91f,.12f},{.69f,.91f,.12f},{.85f,.30f,.91f},{-.85f,.30f,.91f},glassLight);
    for(int k:{-1,1}) {
      const float t=k;
      face({t*.84f,.37f,-1.24f},{t*.69f,.89f,-.68f},{t*.69f,.91f,.12f},{t*.85f,.30f,.91f},windscreen);
      face({t*.86f,.35f,-.22f},{t*.71f,.90f,-.19f},{t*.71f,.90f,-.10f},{t*.86f,.34f,-.12f},tire);
      face({t*.95f,-.01f,-2.071f},{t*.46f,-.01f,-2.071f},
           {t*.46f,.15f,-2.071f},{t*.95f,.15f,-2.071f},red);
      face({t*.95f,-.01f,1.96f},{t*.53f,-.01f,1.96f},{t*.53f,-.13f,1.96f},{t*.95f,-.13f,1.96f},milk);
      face({t*.61f,.29f,-1.86f},{t*.68f,.29f,-1.86f},{t*.68f,.64f,-1.84f},{t*.61f,.64f,-1.84f},shadowMetal);
    }
    face({-1.16f,.64f,-2.15f},{1.16f,.64f,-2.15f},{1.16f,.67f,-1.76f},{-1.16f,.67f,-1.76f},shadowMetal);
    face({-.24f,.91f,-.66f},{.01f,.91f,-.66f},{.01f,.93f,.11f},{-.24f,.93f,.11f},red);
    face({-.24f,.285f,.96f},{.01f,.285f,.96f},{.01f,.05f,1.89f},{-.24f,.05f,1.89f},red);
    face({-.24f,-.19f,-2.08f},{.24f,-.19f,-2.08f},{.24f,-.06f,-2.08f},{-.24f,-.06f,-2.08f},milk);
    for(int k:{-1,1}) {wheel(k,-1.26f,clock*19); wheel(k,1.17f,clock*19);}
    std::sort(faces,faces+count,[](const Face &a,const Face &b){return a.z>b.z;});
    for(int i=0;i<count;++i) {
      const auto &f=faces[i]; s.quad(f.points[0],f.points[1],f.points[2],f.points[3],f.color);
    }
  }
};
} // namespace Rally
