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

  function locator(ctx, x, y, radius) {
    disc(ctx, x, y, radius + 3, "#e6dfc6");
    disc(ctx, x, y, radius + 1, "#171811");
    disc(ctx, x, y, radius - 3, "#b59342");
    disc(ctx, x, y, radius - 8, "#2a53d3");
    disc(ctx, x, y, radius - 10, "#2142b0");
    disc(ctx, x, y, radius * .38, "#101d31");
    disc(ctx, x - radius * .06, y - radius * .04, radius * .27, "#78899f");
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
    rect(ctx, x, y, w, h, 2, vertical(ctx, y, y + h, ["#353633", "#1c211f", "#2b2d28"]), "#69695b");
    disc(ctx, x + 5, y + 6, 1.8, "#88887a");
    if (name) text(ctx, name, x + w / 2, y + h / 2, 7, "#b0a898");
  }

  function socketBank(ctx, top, supply) {
    const ys = [top, top + 23, top + 46, top + 69];
    rect(ctx, 707, top - 12, 147, 95, 4, "#261f13", "#c2a457");
    for (const [index, name] of [supply, "GND", "SCL", "SDA"].entries()) {
      const y = ys[index];
      rect(ctx, 669, y - 8, 33, 17, 5, "#10120f", "#b7a261");
      text(ctx, name, 685, y + 1, 9);
      const pin = vertical(ctx, y - 5, y + 5, ["#fff1b6", "#dfbf73", "#93703f"]);
      rect(ctx, 713, y - 4, 136, 8, 2, pin, "#dec37c");
      for (const x of [719, 742, 765, 788]) disc(ctx, x, y + 3, 5.5, "#eed296");
    }
    rect(ctx, 779, top - 13, 22, 96, 2, "#2b2a25", "#4c4b42");
    text(ctx, supply === "3V3" ? "3V3  I²C" : "5V  I²C", 646, top - 5, 11, "#fbefcf");
  }

  function drawBoard(canvas) {
    const ctx = canvas.getContext("2d");
    ctx.scale(canvas.width / board.width, canvas.height / board.height);
    ctx.translate(-boardOrigin.x, -boardOrigin.y);
    rect(ctx, 49, 23, 806, 466, 46, vertical(ctx, 23, 489, ["#1a1e1c", "#0d1211", "#191c18"]), "#2e352c");
    for (const [x, width] of [[120, 101], [239, 190], [478, 102], [596, 188]]) {
      rect(ctx, x, 465, width, 109, 3, "#101813", "#2d332a");
      for (let column = x + 4; column < x + width - 4; column += 8) {
        rect(ctx, column, 551, 5.8, 10, .9, "#c6aa58");
      }
    }
    for (const [x, y] of [[91, 66], [814, 66], [91, 448], [814, 448]]) locator(ctx, x, y, 35);
    rect(ctx, 166, 20, 80, 68, 3, vertical(ctx, 20, 88, ["#f0f3f3", "#c9d2d3", "#9aa6a6"]), "#7f8989");
    rect(ctx, 172, 20, 67, 8, 2, "#7c8888", "#c9d2d0");
    text(ctx, "USB TYPE-C", 206, 108, 12, "#f1e5bc");
    for (const [index, x] of [320, 410, 499].entries()) {
      rect(ctx, x, 30, 73, 61, 3, vertical(ctx, 30, 91, ["#f2e0a0", "#ceb970", "#91814a"]), "#b9a469");
      rect(ctx, x + 11, 34, 51, 29, 6, "#675c38", "#cbb779");
      for (const dx of [22, 49]) rect(ctx, x + dx, 62, 9, 37, 1, "#dbc687");
      if (index === 2) text(ctx, "VIN", x + 36, 111, 10);
    }
    rect(ctx, 658, 29, 69, 51, 3, vertical(ctx, 29, 80, ["#f4f3ea", "#b9bbb1"]), "#767c74");
    rect(ctx, 667, 30, 51, 20, 2, "#777b72");
    text(ctx, "CAN BUS", 693, 105, 10);
    rect(ctx, 51, 109, 69, 108, 3, "#c0ba91", "#d6c897");
    rect(ctx, 64, 138, 24, 59, 3, "#afa051");
    rect(ctx, 53, 247, 31, 57, 3, "#183252", "#8c99a3");
    [808, 793, 768, 110, 61].forEach((x, i) => disc(ctx, x, 351 + i % 2 * 20, 6, "#bb9f4f"));

    chip(ctx, 182, 177, 47, 48, "ESP32");
    chip(ctx, 251, 164, 35, 45);
    chip(ctx, 319, 166, 39, 34);
    chip(ctx, 437, 210, 34, 32);
    chip(ctx, 539, 209, 45, 37);
    chip(ctx, 605, 98, 31, 25);
    chip(ctx, 586, 284, 44, 35);
    chip(ctx, 114, 284, 25, 27);
    disc(ctx, 506, 228, 25, "#a3a8a4");
    disc(ctx, 506, 228, 20, "#30322c");
    disc(ctx, 506, 228, 3, "#141a18");
    const topCards = [[377, 143], [377, 192], [410, 190], [566, 136],
      [377, 276], [411, 278], [444, 278], [484, 278], [526, 276], [549, 279]];
    topCards.forEach(([x,y], i) => rect(ctx, x, y, 23, 32, 2, i === 5 ? "#598458" : "#bf935c", "#f6cf85"));
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
      rect(ctx, x - 14, 280, 28, 35, 3, vertical(ctx, 280, 315, ["#f4e6cd", "#9c9f96"]), "#555d55");
      rect(ctx, x - 9, 286, 18, 24, 3, "#a6a89d", "#e0ddce");
      disc(ctx, x, 297, 8, "#2b2e2b");
      text(ctx, name, x, 271, 11, "#fff0bf");
    }
    socketBank(ctx, 140, "3V3");
    socketBank(ctx, 252, "D5V");
    rect(ctx, 137, 391, 624, 100, 4, "#211e16", "#b8ae8f");
    for (const {mark, x} of pins) {
      disc(ctx, x, 372, 6.4, "#cab16a");
      text(ctx, mark, x, 387, mark.length > 2 ? 10 : 12, "#f3e9c1");
      for (const y of [407, 432, 457]) {
        disc(ctx, x, y, 6.9, "#c29d4a");
        disc(ctx, x, y, 4, "#342d1d");
      }
      rect(ctx, x - 3, 414, 6, 56, 2, vertical(ctx, 414, 470, ["#f7de90", "#a9854b", "#ebc76c"]));
    }
    for (const [mark, y] of [["S", 407], ["V", 432], ["G", 457]]) text(ctx, mark, 770, y, 12);
    rect(ctx, 142, 468, 616, 24, 2, vertical(ctx, 468, 492, ["#46423a", "#292822"]), "#575248");
    for (const { x } of pins) rect(ctx, x - 3, 493, 6, 51, 1, "#d0b77d");
  }

  function drawOled(canvas) {
    const ctx = canvas.getContext("2d");
    ctx.scale(canvas.width / 550, canvas.height / 301);
    rect(ctx, 2, 3, 546, 294, 39, vertical(ctx, 3, 297, ["#222521", "#101613", "#1d2119"]), "#35372e");
    for (const [x, y] of [[50, 51], [500, 51], [50, 250], [500, 250]]) locator(ctx, x, y, 31);
    rect(ctx, 96, 42, 358, 208, 5, vertical(ctx, 42, 250, ["#acb7b3", "#697675", "#859290"]), "#616c69");
    rect(ctx, 116, 63, 318, 163, 4, "#121f20", "#0a1616");
    text(ctx, "IDMD-0021", 275, 22, 16, "#e4d29d");
    text(ctx, "1.3 inch OLED 显示屏", 275, 271, 17);
  }

  return { board, boardOrigin, buttonA, pins, sockets, drawBoard, drawOled };
})();
