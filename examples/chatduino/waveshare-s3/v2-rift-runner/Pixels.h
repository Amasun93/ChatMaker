#pragma once
#include "Flight.h"
#include <cstring>
#include <cstdlib>
namespace Rift {
using Color = uint16_t;
constexpr Color rgb(int r, int g, int b) {
  return uint16_t((r & 248) << 8 | (g & 252) << 3 | b >> 3);
}
constexpr Color ink = rgb(12,13,34), milk = rgb(255,239,209), gold = rgb(255,176,56),
  red = rgb(255,76,62), magenta = rgb(239,57,130), lilac = rgb(174,153,240),
  mint = rgb(69,248,224), blue = rgb(53,139,205), deep = rgb(36,48,87);
inline Color mix(Color a, Color b, int t) {
  t = std::clamp(t,0,256);
  const int r = ((a >> 11) * (256-t) + (b >> 11) * t) >> 8;
  const int g = (((a >> 5) & 63) * (256-t) + ((b >> 5) & 63) * t) >> 8;
  const int v = ((a & 31) * (256-t) + (b & 31) * t) >> 8;
  return Color((r << 11) | (g << 5) | v);
}
inline uint32_t hash(int n) {
  uint32_t v = uint32_t(n) * 747796405u + 2891336453u;
  v = ((v >> ((v >> 28) + 4)) ^ v) * 277803737u;
  return (v >> 22) ^ v;
}
struct P { int x, y; };
inline P xy(float x, float y) { return {int(lroundf(x)),int(lroundf(y))}; }
constexpr int W = 160, H = 120;
struct Surface {
  Color pixels[W*H];
  void dot(int x,int y,Color c) {
    if (unsigned(x)<W && unsigned(y)<H) pixels[y*W+x]=c;
  }
  void span(int x,int end,int y,Color c) {
    if (unsigned(y)>=H) return;
    x=std::max(0,x); end=std::min(W,end);
    if (x<end) std::fill(pixels+y*W+x,pixels+y*W+end,c);
  }
  void box(int x,int y,int w,int h,Color c) {
    for (int i=std::max(0,y);i<std::min(H,y+h);++i) span(x,x+w,i,c);
  }
  void line(P a,P b,Color c) {
    const int dx=std::abs(b.x-a.x), dy=-std::abs(b.y-a.y);
    const int sx=a.x<b.x?1:-1, sy=a.y<b.y?1:-1;
    int err=dx+dy;
    for (;;) {
      dot(a.x,a.y,c);
      if (a.x==b.x && a.y==b.y) return;
      const int twice=2*err;
      if (twice>=dy) { err+=dy; a.x+=sx; }
      if (twice<=dx) { err+=dx; a.y+=sy; }
    }
  }
  void tri(P a,P b,P c,Color col) {
    if (a.y>b.y) std::swap(a,b);
    if (b.y>c.y) std::swap(b,c);
    if (a.y>b.y) std::swap(a,b);
    if (c.y<0 || a.y>=H || a.y==c.y) return;
    const int first=std::max(0,a.y), last=std::min(H-1,c.y);
    const int longStep=(c.x-a.x)*256/(c.y-a.y);
    int across=a.x*256+longStep*(first-a.y);
    const int upper=(b.x-a.x)*256/std::max(1,b.y-a.y);
    const int lower=(c.x-b.x)*256/std::max(1,c.y-b.y);
    for (int y=first;y<=last;++y,across+=longStep) {
      const int other=y<b.y ? a.x*256+upper*(y-a.y) : b.x*256+lower*(y-b.y);
      span(std::min(across,other)>>8,(std::max(across,other)>>8)+1,y,col);
    }
  }
  void quad(P a,P b,P c,P d,Color color) { tri(a,b,c,color); tri(a,c,d,color); }
  void disk(int x,int y,int r,Color c) {
    for(int dy=-r;dy<=r;++dy) {
      const int dx=int(sqrtf(float(r*r-dy*dy)));
      span(x-dx,x+dx+1,y+dy,c);
    }
  }
  void circle(int x,int y,int r,Color c) {
    int dx=r,dy=0,d=1-r;
    while (dx>=dy) {
      dot(x+dx,y+dy,c); dot(x+dy,y+dx,c); dot(x-dy,y+dx,c); dot(x-dx,y+dy,c);
      dot(x-dx,y-dy,c); dot(x-dy,y-dx,c); dot(x+dy,y-dx,c); dot(x+dx,y-dy,c);
      ++dy;
      if(d<0) d+=2*dy+1;
      else { --dx; d+=2*(dy-dx)+1; }
    }
  }
  void word(int x,int y,const char *s,Color c,int scale=1) {
    static constexpr char alphabet[]="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789- /";
    static constexpr uint16_t font[]={
      0x2bed,0x6bae,0x3923,0x6b6e,0x79a7,0x79a4,0x396b,0x5bed,0x7497,0x124a,
      0x5bad,0x4927,0x5fed,0x5ffd,0x2b6a,0x6ba4,0x2b7b,0x6bad,0x38ce,0x7492,
      0x5b6f,0x5b6a,0x5bfd,0x5aad,0x5a92,0x72a7,0x7b6f,0x3497,0x73e7,0x73cf,
      0x5bc9,0x79cf,0x79ef,0x7249,0x7bef,0x7bcf,0x01c0,0,0x12a4
    };
    for(;*s;++s,x+=4*scale) {
      const char *p=std::strchr(alphabet,*s);
      if (!p) continue;
      uint16_t bits=font[p-alphabet];
      for(int j=0;j<5;++j) for(int i=0;i<3;++i)
        if(bits & (1u<<(14-3*j-i))) box(x+i*scale,y+j*scale,scale,scale,c);
    }
  }
};
} // namespace Rift
