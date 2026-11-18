// Original teaching art registered to the v4.2.2 front view from the Starcore lesson.
const StarcoreArtwork = (() => {
  const board = { width: 820, height: 560 };
  // Coordinates below use the front render's origin. The exterior canvas excludes its margins.
  const boardOrigin = { x: 45, y: 20 };
  const buttonA = { x: 317, y: 297 };
  const pins = [
    ["RX", "R", 3], ["TX", "T", 1], ["37", "IO37", 37], ["38", "IO38", 38],
    ["P", "P23", 27], ["Y", "P24", 14], ["T", "P25", 12], ["H", "P26", 13],
    ["O", "P27", 15], ["N", "P28", 4], ["P0", "P0", 33], ["P1", "P1", 32],
    ["P2", "P2", 35], ["P3", "P3", 34], ["P4", "P4", 39], ["P5", "P5", 0],
    ["P6", "P6", 16], ["P7", "P7", 17], ["P8", "P8", 26], ["P9", "P9", 25],
    ["P10", "P10", 36], ["P11", "P11", 2], ["P13", "P13", 18], ["P14", "P14", 19],
    ["P15", "P15", 21], ["P16", "P16", 5],
  ].map(([mark, label, gpio], index) => ({ mark, label, gpio, x: 165 + index * 22.84 }));

  const sockets = [
    { id: "3v3", x: 846, y: 140 }, { id: "gnd", x: 846, y: 163 },
    { id: "scl", x: 846, y: 186 }, { id: "sda", x: 846, y: 209 },
  ];

  function rect(ctx, x, y, w, h, radius, fill, outline) {
    ctx.beginPath();
    ctx.roundRect(x, y, w, h, radius);
    ctx.fillStyle = fill;
    ctx.fill();
    if (outline) {
      ctx.strokeStyle = outline;
      ctx.lineWidth = 1.2;
      ctx.stroke();
    }
  }

  function disc(ctx, x, y, radius, fill) {
    ctx.beginPath();
    ctx.arc(x, y, radius, 0, Math.PI * 2);
    ctx.fillStyle = fill;
    ctx.fill();
  }

  function text(ctx, value, x, y, size, color = "#eaddaa", align = "center") {
    ctx.font = "700 " + size + "px 'Microsoft YaHei', 'PingFang SC', monospace";
    ctx.fillStyle = color;
    ctx.textAlign = align;
    ctx.textBaseline = "middle";
    ctx.fillText(value, x, y);
  }

  function vertical(ctx, top, bottom, colors) {
    const gradient = ctx.createLinearGradient(0, top, 0, bottom);
    colors.forEach((color, i) => gradient.addColorStop(i / (colors.length - 1), color));
    return gradient;
  }

  function horizontal(ctx, left, right, colors) {
    const gradient = ctx.createLinearGradient(left, 0, right, 0);
    colors.forEach((color, i) => gradient.addColorStop(i / (colors.length - 1), color));
    return gradient;
  }

  function silkStar(ctx, x, y, radius) {
    ctx.beginPath();
    for (let vertex = 0; vertex < 10; vertex++) {
      const angle = -Math.PI / 2 + vertex * Math.PI / 5;
      const r = radius * (vertex % 2 ? .49 : 1);
      const px = x + r * Math.cos(angle);
      const py = y + r * Math.sin(angle);
      if (vertex === 0) ctx.moveTo(px, py);
      else ctx.lineTo(px, py);
    }
    ctx.closePath();
    ctx.fillStyle = "#dcca83";
    ctx.fill();
  }

  function locator(ctx, x, y, radius) {
    disc(ctx, x, y, radius + 3, "#ecebe0");
    disc(ctx, x, y, radius + 1, "#111312");
    disc(ctx, x, y, radius - 4, vertical(ctx, y - radius, y + radius, ["#edcf79", "#967330", "#c9a34c"]));
    disc(ctx, x + 1, y + 2, radius - 7, "#151b2a");
    const blue = ctx.createRadialGradient(x - 9, y - 11, 2, x, y, radius - 5);
    blue.addColorStop(0, "#5b78ec");
    blue.addColorStop(.55, "#344fc2");
    blue.addColorStop(1, "#1c286f");
    disc(ctx, x, y, radius - 8, blue);
    disc(ctx, x + 1, y + 1, radius * .36, vertical(ctx, y - 11, y + 12, ["#131b30", "#546374", "#a7b4c2"]));
  }

  function smd(ctx, x, y, w, h, fill) {
    rect(ctx, x - 3, y, w + 6, h, 1, "#b49b57");
    rect(ctx, x, y, w, h, 1, fill, "#070909");
    rect(ctx, x - 2, y + 1, 3, h - 2, 1, "#c7b89a");
    rect(ctx, x + w - 1, y + 1, 3, h - 2, 1, "#d2c5a7");
  }

  function chip(ctx, x, y, w, h, name) {
    for (let i = 2; i < w - 2; i += 7) {
      rect(ctx, x + i, y - 5, 3, h + 10, .5, "#b0a17b");
    }
    rect(ctx, x + 2, y + 3, w, h, 2, "#090b0a");
    rect(ctx, x, y, w, h, 2, vertical(ctx, y, y + h, ["#333735", "#242624", "#171a18"]), "#88877b");
    rect(ctx, x + 2, y + 2, w - 4, 2, .6, "#464842");
    disc(ctx, x + 5, y + 6, 1.8, "#88887a");
    if (name) text(ctx, name, x + w / 2, y + h / 2, 7, "#b0a898");
  }

  function headerHousing(ctx, x, y, width, height, contacts) {
    rect(ctx, x + 2, y + 4, width, height, 3, "#080b0a");
    rect(ctx, x, y, width, height, 3, vertical(ctx, y, y + height, ["#f5ecd0", "#dccea8", "#a79972"]), "#9a8f70");
    rect(ctx, x + 6, y + 5, width - 12, height * .51, 2, "#6c6651");
    rect(ctx, x + 9, y + 7, width - 18, height * .37, 1, "#373a34");
    for (let i = 0; i < contacts; i++) {
      const leadX = x + (i + .5) * width / contacts;
      rect(ctx, leadX - 3, y + height * .62, 6, height * .57, 1,
        horizontal(ctx, leadX - 3, leadX + 3, ["#aa904f", "#f4d989", "#9b844a"]));
    }
    rect(ctx, x + 3, y + height * .62, 5, height * .38, 1, "#f3e9cb");
    rect(ctx, x + width - 8, y + height * .62, 5, height * .38, 1, "#eadbb3");
  }

  function tread(ctx, x, y, width) {
    rect(ctx, x - width / 2, y - 4, width, 8, 3,
      horizontal(ctx, x - width / 2, x + width / 2, ["#826632", "#d0ad5b", "#dec78a", "#927647"]));
  }

  function socketBank(ctx, top, supply) {
    const ys = [top, top + 23, top + 46, top + 69];
    rect(ctx, 706, top - 12, 94, 95, 2, "#211e14", "#e9dcb4");
    for (const [index, name] of [supply, "GND", "SCL", "SDA"].entries()) {
      const y = ys[index];
      rect(ctx, 669, y - 8, 33, 17, 6, "#101210", "#b7a261");
      text(ctx, name, 685, y + 1, 11, "#f1d990");
      for (const x of [718, 741, 764, 787]) {
        disc(ctx, x, y + 3, 6.5, "#b59249");
        disc(ctx, x, y + 3, 4.2, "#e7c775");
      }
      const pin = vertical(ctx, y - 5, y + 5, ["#6d592e", "#e7cd87", "#f1d897", "#ab8d4e"]);
      rect(ctx, 714, y - 4, 139, 8, 2, pin, "#c3ab70");
    }
    rect(ctx, 776, top - 15, 26, 100, 2, horizontal(ctx, 776, 802, ["#3b3b36", "#282a26", "#4a4941"]), "#747064");
    for (const y of ys) rect(ctx, 778, y - 6, 22, 12, 2, "#30312c");
    ctx.save();
    ctx.translate(653, top + 36);
    ctx.rotate(-Math.PI / 2);
    rect(ctx, -45, -6, 90, 12, 5, "#121513", "#c4b997");
    text(ctx, supply === "3V3" ? "3V3 I²C" : "D5V I²C", 0, 0, 8, "#e9dfc5");
    ctx.restore();
  }

  function drawBoard(canvas) {
    const ctx = canvas.getContext("2d");
    ctx.scale(canvas.width / board.width, canvas.height / board.height);
    ctx.translate(-boardOrigin.x, -boardOrigin.y);
    const outline = new Path2D(
      "M95 23H302l8 8h265l8-8h61l7 8h79l8-8h68q49 0 49 49v373q0 45-48 45h-13q-10 0-10 13v65" +
      "q0 6-6 6H601q-6 0-6-6v-61q0-10-9-10t-9 10v61q0 6-6 6h-89q-6 0-6-6v-54q0-16-14-16" +
      "h-19q-14 0-14 16v54q0 6-6 6H244q-6 0-6-6v-47q0-14-9-14t-9 14v47q0 6-6 6h-88q-6 0-6-6" +
      "v-64q0-14-14-14H94q-45 0-45-45V71q0-48 46-48z"
    );
    ctx.fillStyle = vertical(ctx, 23, 574, ["#212522", "#151817", "#181b18", "#101412"]);
    ctx.fill(outline);
    ctx.strokeStyle = "#343a33";
    ctx.lineWidth = 2;
    ctx.stroke(outline);
    for (const [x, width] of [[120, 101], [239, 190], [478, 102], [596, 188]]) {
      for (let column = x + 4; column < x + width - 4; column += 8) {
        tread(ctx, column, 557, 5.8);
      }
    }
    for (const [x, y] of [[91, 66], [814, 66], [91, 448], [814, 448]]) locator(ctx, x, y, 35);
    rect(ctx, 162, 26, 89, 68, 4, "#0c100e");
    rect(ctx, 166, 20, 80, 68, 4, vertical(ctx, 20, 88, ["#fafcfb", "#d2d7d5", "#8d9690"]), "#9da6a1");
    rect(ctx, 173, 22, 66, 6, 2, "#a6afac", "#edf2ef");
    rect(ctx, 172, 34, 3, 42, 1, "#d7dcd9");
    rect(ctx, 238, 35, 3, 42, 1, "#adb6b1");
    for (let x = 174; x <= 237; x += 5) rect(ctx, x, 87, 2.4, 7, 1, "#d4b46a");
    rect(ctx, 176, 100, 65, 17, 8, "#111613", "#d5cfb1");
    text(ctx, "USB TYPE-C", 208, 108, 10, "#f1ead0");
    for (const [index, x] of [320, 410, 499].entries()) {
      headerHousing(ctx, x, 30, 72, 61, 2);
      if (index === 2) text(ctx, "VIN", x + 36, 111, 10);
    }
    headerHousing(ctx, 658, 30, 70, 41, 4);
    rect(ctx, 653, 94, 32, 24, 7, "#0f1411", "#dfd8be");
    text(ctx, "CAN", 669, 100, 8);
    text(ctx, "BUS", 669, 111, 8);
    rect(ctx, 49, 109, 71, 108, 2, vertical(ctx, 109, 217, ["#d8d6bf", "#afae97", "#cdccbc"]), "#a79b76");
    rect(ctx, 65, 143, 18, 48, 1, "#d7c495");
    rect(ctx, 67, 151, 14, 31, 1, "#e7ded1");
    rect(ctx, 64, 141, 19, 7, 1, "#d6ae4f");
    rect(ctx, 64, 186, 19, 7, 1, "#d6ae4f");
    rect(ctx, 52, 242, 34, 65, 2, "#b5af99", "#b1ac99");
    rect(ctx, 55, 245, 28, 59, 2, vertical(ctx, 245, 304, ["#2e4269", "#1c2f56", "#121d35"]), "#8190ab");
    for (const [x,y] of [[131,105], [842,106], [790,118], [818,133], [71,382],
      [107,392], [824,350], [826,390], [749,351], [710,339], [59,329]]) silkStar(ctx, x, y, 6.4);
    for (const x of [98, 122, 145, 760, 783, 805]) {
      disc(ctx, x, 373, 7, "#cdb377");
      disc(ctx, x, 373, 3.2, "#222a26");
    }

    chip(ctx, 182, 177, 47, 48, "ESP32");
    chip(ctx, 251, 164, 35, 45);
    chip(ctx, 319, 166, 39, 34);
    chip(ctx, 437, 210, 34, 32);
    chip(ctx, 539, 209, 45, 37);
    chip(ctx, 605, 98, 31, 25);
    chip(ctx, 586, 284, 44, 35);
    chip(ctx, 114, 284, 25, 27);
    rect(ctx, 482, 201, 50, 53, 4, "#797f74", "#d4d5c2");
    disc(ctx, 506, 228, 23, vertical(ctx, 205, 250, ["#f3f4ec", "#a5aea8", "#d4ddd5"]));
    disc(ctx, 506, 228, 19, "#dce4db");
    disc(ctx, 506, 228, 1.8, "#b4bcb4");
    const capacitors = [[377, 143], [377, 192], [410, 190], [566, 136],
      [377, 276], [411, 278], [444, 278], [484, 278], [526, 276], [549, 279]];
    capacitors.forEach(([x, y], index) => {
      const green = index === 5;
      rect(ctx, x - 1, y - 4, 25, 40, 2, "#a89050");
      rect(ctx, x, y, 23, 32, 2, vertical(ctx, y, y + 32, green
        ? ["#a9bf81", "#487557", "#709456"] : ["#ebc68e", "#bf9058", "#dba66d"]), "#e2c392");
      rect(ctx, x + 1, y + 5, 21, 3, 1, green ? "#bbcea0" : "#f2d3a4");
    });
    for (const [index, x] of [449, 471, 494].entries()) {
      rect(ctx, x - 6, 132, 12, 43, 6, "#191b16", "#d6cfb1");
      rect(ctx, x - 3, 138, 6, 23, 2, ["#61a86a", "#cc643e", "#587dd1"][index]);
      text(ctx, ["3V3", "5V", "VIN"][index], x, 169, 6);
    }
    for (const [x, y, count] of [[145, 120, 12], [139, 139, 9], [250, 119, 9],
      [302, 216, 5], [442, 128, 8], [539, 271, 9], [593, 138, 8],
      [109, 242, 7], [378, 241, 7], [172, 343, 24]]) {
      for (let i = 0; i < count; i++) {
        smd(ctx, x + i * 11, y + (i % 3 === 2 ? 3 : 0), 4, 5, ["#655a42", "#282c28", "#9d8f69"][i % 3]);
      }
    }
    rect(ctx, 165, 245, 77, 102, 2, "#101410", "#ede2b1");
    text(ctx, "星核板", 203, 263, 19, "#faeed1");
    text(ctx, "V4.2.2", 203, 287, 13);
    text(ctx, "斯坦星球", 203, 308, 11);
    text(ctx, "IDEALAB", 203, 330, 12);

    for (const [name, x] of [["A", 317], ["B", 352]]) {
      for (const dx of [-12, 8]) {
        rect(ctx, x + dx, 275, 5, 12, 1, "#c7ae69");
        rect(ctx, x + dx, 308, 5, 10, 1, "#c7ae69");
      }
      rect(ctx, x - 14, 280, 28, 35, 3, vertical(ctx, 280, 315, ["#efeee2", "#b5b6ab", "#919684"]), "#656c5f");
      rect(ctx, x - 11, 284, 22, 25, 2, "#aeb5a7", "#e1e0d4");
      disc(ctx, x, 297, 9, "#252923");
      disc(ctx, x, 296, 7, vertical(ctx, 289, 304, ["#5b6059", "#343932", "#282e29"]));
      text(ctx, name, x, 268, 13, "#fff3cb");
    }
    socketBank(ctx, 140, "3V3");
    socketBank(ctx, 252, "D5V");

    rect(ctx, 136, 393, 631, 87, 4, "#e8e5cf");
    rect(ctx, 148, 397, 602, 80, 2, "#242219");
    rect(ctx, 150, 378, 597, 18, 2, "#e9e5ce");
    for (const {mark, x} of pins) {
      disc(ctx, x, 369, 6.1, "#bba15e");
      disc(ctx, x - 1, 368, 3.7, "#e2c980");
      text(ctx, mark, x, 388, mark.length > 2 ? 11 : 13, "#292b22");
      for (const y of [407, 432, 457]) {
        disc(ctx, x, y, 6.3, "#c2a45d");
        disc(ctx, x, y, 3.3, "#7d693d");
      }
      const metal = horizontal(ctx, x - 4, x + 4, ["#856936", "#f2d98a", "#c7aa64", "#795c34"]);
      rect(ctx, x - 3.4, 413, 6.8, 56, 2, metal);
      rect(ctx, x + 2.6, 417, 1.7, 53, 1, "#e5ca80");
      rect(ctx, x - 3.4, 489, 6.8, 54, 1, metal);
    }
    for (const [mark, y] of [["S", 406], ["V", 432], ["G", 458]]) {
      text(ctx, mark, 756, y, 13, "#262921");
      text(ctx, mark, 143, y, 11, "#30352e");
    }
    rect(ctx, 138, 468, 620, 25, 2, vertical(ctx, 468, 493, ["#4c4c45", "#343632", "#262825"]), "#5e6155");
    for (const { x } of pins) rect(ctx, x - 9, 470, 1.3, 20, .6, "#242824");
  }

  function drawOled(canvas) {
    const ctx = canvas.getContext("2d");
    ctx.scale(canvas.width / 550, canvas.height / 301);
    rect(ctx, 2, 3, 546, 294, 39, vertical(ctx, 3, 297, ["#262925", "#141715", "#111412"]), "#414638");
    for (const [x, y] of [[50, 51], [500, 51], [50, 250], [500, 250]]) locator(ctx, x, y, 31);
    rect(ctx, 94, 33, 362, 235, 5, "#3d4541", "#59635e");
    rect(ctx, 96, 38, 358, 226, 2, vertical(ctx, 38, 264, ["#b5bcb6", "#737b73", "#8e968a"]), "#7c857d");
    rect(ctx, 116, 63, 318, 163, 4, "#121f20", "#0a1616");
    for (const [x, y, r] of [[109, 22, 7], [438, 22, 7], [26, 106, 6], [61, 126, 7], [73, 170, 7],
      [51, 205, 11], [499, 154, 7], [134, 281, 7], [430, 281, 7]]) silkStar(ctx, x, y, r);
    for (const y of [130, 150, 170, 190]) disc(ctx, 23, y, 5, "#c4a655");
    rect(ctx, 480, 111, 49, 31, 1, "#171b16", "#c7ab60");
    rect(ctx, 498, 142, 13, 6, 0, "#d3b971");
    rect(ctx, 491, 148, 26, 2, 0, "#d3b971");
    rect(ctx, 491, 167, 35, 26, 3, "#d2b469");
    disc(ctx, 500, 177, 3, "#212419");
    disc(ctx, 517, 177, 3, "#212419");
    text(ctx, "ideaLab   斯坦星球", 275, 20, 17, "#e2c989");
    text(ctx, "1.3 inch OLED 显示屏", 275, 282, 17);
  }

  return { board, boardOrigin, buttonA, pins, sockets, drawBoard, drawOled };
})();
