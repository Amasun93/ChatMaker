// Original classroom illustrations. PCB size and mounting centres use the mechanical cards.
const StarcoreComponents = (() => {
  function box(ctx, x, y, w, h, r, color, stroke) {
    ctx.beginPath();
    ctx.roundRect(x, y, w, h, r);
    ctx.fillStyle = color;
    ctx.fill();
    if (stroke) {
      ctx.strokeStyle = stroke;
      ctx.lineWidth = .18;
      ctx.stroke();
    }
  }

  function circle(ctx, x, y, r, color) {
    ctx.beginPath();
    ctx.arc(x, y, r, 0, 2 * Math.PI);
    ctx.fillStyle = color;
    ctx.fill();
  }

  function metal(ctx, x, y, width) {
    const surface = ctx.createLinearGradient(x, y, x + width, y + width);
    surface.addColorStop(0, "#f3f5ed");
    surface.addColorStop(.4, "#b4b9b9");
    surface.addColorStop(.7, "#747e81");
    surface.addColorStop(1, "#c8cdca");
    return surface;
  }

  function silk(ctx, value, x, y, size = 1.75) {
    ctx.font = "700 " + size + "px monospace";
    ctx.textAlign = "center";
    ctx.fillStyle = "#e9d298";
    ctx.fillText(value, x, y);
  }

  function plug(ctx, x, y, count) {
    const height = count * 2.1 + 1.2;
    box(ctx, x - 1, y - height / 2, 5.1, height, .45, "#fff9e8", "#aaa08c");
    box(ctx, x + .2, y - height / 2 + .8, 3.2, height - 1.6, .3, "#c6b79c");
    for (let i = 0; i < count; i++) {
      box(ctx, x - 1.8, y + (i - (count - 1) / 2) * 2.1 - .35, 4.5, .7, .12, "#cba85d");
    }
  }

  function front(ctx, module, options) {
    const [width] = module.size_mm;
    const center = width / 2;
    switch (module.art) {
      case "button": {
        box(ctx, center - 6.7, 8.3, 13.4, 13.1, .8, metal(ctx, 8, 8, 13), "#dbe0dc");
        for (const x of [center - 5, center + 5]) {
          for (const y of [10, 19.8]) circle(ctx, x, y, .52, "#555d60");
        }
        circle(ctx, center, 15, options.pressed ? 4 : 4.35, "#1a2024");
        circle(ctx, center, options.pressed ? 15 : 14.6, 3.5, options.pressed ? "#445660" : "#344047");
        silk(ctx, "BUTTON", center, 26.5);
        break;
      }
      case "switch":
        box(ctx, 7.7, 10.1, 14.1, 10, .7, metal(ctx, 8, 10, 14));
        box(ctx, 9.3, 11.05, 10.2, 7.9, .5, "#282f35");
        box(ctx, 10.1, 11.5, 5.6, 7, .45, "#5387ae", "#75b1cd");
        for (let i = 0; i < 3; i++) box(ctx, 10.9 + i * 1.3, 12.8, .42, 4.6, .17, "#adcbd2");
        silk(ctx, "SWITCH", center, 26.5);
        break;
      case "encoder":
      case "knob": {
        const encoder = module.art === "encoder";
        circle(ctx, center, 14.9, 7.2, metal(ctx, 8, 8, 14));
        circle(ctx, center, 14.9, 5.9, encoder ? "#25292e" : "#333a40");
        for (let notch = 0; notch < 12; notch++) {
          const angle = notch * Math.PI / 6;
          circle(ctx, center + 5.2 * Math.cos(angle), 14.9 + 5.2 * Math.sin(angle), .44, "#747d80");
        }
        ctx.save();
        ctx.translate(center, 14.9);
        ctx.rotate(((options.sample ?? 2048) / 4095 - .5) * Math.PI * 1.5);
        if (!encoder) box(ctx, -.48, -5, .96, 3.5, .35, "#fac7c1");
        ctx.restore();
        silk(ctx, encoder ? "ENCODER" : "POT", center, 26.5);
        break;
      }
      case "light":
        for (let i = 0; i < 8; i++) {
          ctx.save();
          ctx.translate(center, 14.7);
          ctx.rotate(i * Math.PI / 4);
          box(ctx, -.46, -6.6, .92, 2.1, .4, "#c8a653");
          ctx.restore();
        }
        circle(ctx, center, 14.7, 3.4, "#a3aaa1");
        circle(ctx, center, 14.5, 2.8, "#f3efe0");
        circle(ctx, center - .65, 13.7, 1.3, "#fffdf1");
        silk(ctx, "LIGHT", center, 26.5);
        break;
      case "accelerometer":
        box(ctx, 10, 9.5, 9.1, 9.1, .45, "#262b31", "#687275");
        for (let i = 0; i < 4; i++) {
          box(ctx, 9.2, 10.3 + i * 2, 1.45, .55, .12, "#c2a25a");
          box(ctx, 18.6, 10.3 + i * 2, 1.45, .55, .12, "#c2a25a");
        }
        silk(ctx, "XYZ", 14.55, 15.25);
        silk(ctx, "ACCEL", center, 26.5);
        break;
      case "rgb": {
        const [r, g, b] = options.color ?? [0, 0, 0];
        if (r || g || b) {
          const halo = ctx.createRadialGradient(center, 14.6, 3, center, 14.6, 13.5);
          halo.addColorStop(0, "rgba(" + [r, g, b, .8].join(",") + ")");
          halo.addColorStop(1, "transparent");
          circle(ctx, center, 14.6, 13.5, halo);
        }
        circle(ctx, center, 14.6, 6.7, "#777c70");
        circle(ctx, center, 14.6, 5.9, r || g || b ? "rgb(" + [r, g, b].join(",") + ")" : "#d0cdc1");
        circle(ctx, center - 1.7, 12.6, 2, "#fff7e699");
        silk(ctx, "RGB", center, 26.5);
        break;
      }
      case "dht11":
        box(ctx, 8, 7, 14, 16.3, 1, "#219ecb", "#78d2e8");
        for (let x = 10; x < 21; x += 3.35) {
          for (let y = 9; y < 22; y += 3.45) box(ctx, x, y, 2.1, 1.9, .2, "#114b67");
        }
        silk(ctx, "DHT11", center, 26.5);
        break;
      case "ultrasonic":
        for (const x of [13.5, width - 13.5]) {
          circle(ctx, x, 15, 7.2, metal(ctx, x - 7, 8, 14));
          circle(ctx, x, 15, 5.6, "#353b42");
          circle(ctx, x, 15, 4.65, "#7f9095");
          for (let step = -3; step <= 3; step++) {
            box(ctx, x - 2.8, 14.9 + step, 5.6, .22, .1, "#445157");
          }
        }
        silk(ctx, "TRIG / ECHO", center, 26.1);
        break;
      case "mp3":
        box(ctx, center - 7, 7.4, 14, 11, .6, "#242a2b", "#6e6149");
        for (let i = 0; i < 8; i++) {
          const x = center - 5.5 + i * 1.6;
          box(ctx, x, 6.6, .69, 2, .12, "#c7a761");
          box(ctx, x, 17.3, .69, 2, .12, "#c7a761");
        }
        for (let i = 0; i < 5; i++) box(ctx, 18.5 + i * 3.1, 22, 2.1, 4, .32, "#cd9948");
        plug(ctx, 2, 15, 2);
        silk(ctx, "MP3", width - 13.5, 25.7);
        break;
    }
  }

  function draw(canvas, module, options = {}) {
    if (module.art === "oled") {
      StarcoreArtwork.drawOled(canvas);
      return;
    }
    const [width, depth] = module.size_mm;
    const ctx = canvas.getContext("2d");
    const margin = 1.4;
    ctx.resetTransform();
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.scale(canvas.width / (width + margin * 2), canvas.height / (depth + margin * 2));
    ctx.translate(margin, margin);
    const outline = module.art === "outline";
    box(ctx, 0, 0, width, depth, 1.5, outline ? "#e4ebeb" : "#1c2528", outline ? "#859a9c" : "#9a8560");
    box(ctx, .7, .7, width - 1.4, depth - 1.4, 1.1, outline ? "#dae4e4" : "#141b1e", outline ? "#c2d1d1" : "#655a3c");
    for (const [x, y] of module.holes_mm) {
      const holeX = width / 2 + x;
      const holeY = depth / 2 - y;
      circle(ctx, holeX, holeY, 2.65, outline ? "#9aafaf" : "#b4a068");
      circle(ctx, holeX, holeY, 2.24, outline ? "#eef4f3" : "#284bd7");
      circle(ctx, holeX, holeY, 1.36, outline ? "#fff" : "#151c78");
    }
    if (outline) {
      ctx.font = "700 2.2px monospace";
      ctx.fillStyle = "#596f70";
      ctx.textAlign = "center";
      ctx.fillText(module.code, width / 2, depth / 2 + .7);
      return;
    }
    for (const [x, y] of [[11.5, 4.3], [15, 3.9], [18.5, 4.6], [6, 12], [6.5, 17.4]]) {
      box(ctx, x - .85, y - .35, 1.7, .7, .1, "#ba984c");
      if (y < 5) box(ctx, x - .43, y - .34, .86, .68, .08, "#d1d4bd");
    }
    front(ctx, module, options);
    plug(ctx, width - 5.25, depth / 2, module.pins.length);
  }

  return { draw };
})();
