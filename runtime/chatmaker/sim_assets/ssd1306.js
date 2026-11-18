// SSD1306 RAM addressing and basic display commands for the UNO's I2C preview.
const ssd1306ArgumentCounts = {
  0x20: 1, 0x21: 2, 0x22: 2, 0x81: 1, 0x8d: 1, 0xa8: 1, 0xd3: 1,
  0xd5: 1, 0xd9: 1, 0xda: 1, 0xdb: 1,
};

class ChatSimSSD1306 {
  constructor(canvas) {
    this.context = canvas.getContext("2d");
    this.image = this.context.createImageData(128, 64);
    this.ram = new Uint8Array(128 * 8);
    this.reset();
  }

  reset() {
    this.ram.fill(0);
    this.on = this.inverse = this.allOn = false;
    this.column = this.page = 0;
    this.columnStart = this.pageStart = 0;
    this.columnEnd = 127;
    this.pageEnd = 7;
    this.addressMode = 2;
    this.control = null;
    this.command = null;
    this.arguments = [];
    this.dirty = true;
    this.redraw();
  }

  connect(twi) {
    twi.eventHandler = {
      start: () => twi.completeStart(),
      stop: () => twi.completeStop(),
      connectToSlave: (address, write) => {
        this.control = null;
        twi.completeConnect(address === 0x3c && write);
      },
      writeByte: (byte) => {
        this.receive(byte);
        twi.completeWrite(true);
      },
      readByte: () => twi.completeRead(0xff),
    };
  }

  receive(byte) {
    if (this.control === null) {
      this.control = byte;
      return;
    }
    if (this.control & 0x40) this.writePixelColumn(byte);
    else this.receiveCommand(byte);
    if (this.control & 0x80) this.control = null;
  }

  receiveCommand(byte) {
    if (this.command !== null) {
      this.arguments.push(byte);
      if (this.arguments.length === ssd1306ArgumentCounts[this.command]) {
        this.applyCommand(this.command, this.arguments);
        this.command = null;
        this.arguments = [];
      }
    } else if (ssd1306ArgumentCounts[byte]) {
      this.command = byte;
    } else {
      this.applyCommand(byte, []);
    }
  }

  applyCommand(command, [first, second]) {
    switch (command) {
      case 0x20: this.addressMode = first & 3; break;
      case 0x21:
        this.column = this.columnStart = first & 127;
        this.columnEnd = second & 127;
        break;
      case 0x22:
        this.page = this.pageStart = first & 7;
        this.pageEnd = second & 7;
        break;
      case 0xae: case 0xaf: this.on = command === 0xaf; this.dirty = true; break;
      case 0xa6: case 0xa7: this.inverse = command === 0xa7; this.dirty = true; break;
      case 0xa4: case 0xa5: this.allOn = command === 0xa5; this.dirty = true; break;
      default:
        if (command < 0x10) this.column = (this.column & 0x70) | command;
        else if (command < 0x18) this.column = (this.column & 0x0f) | ((command & 7) << 4);
        else if (command >= 0xb0 && command <= 0xb7) this.page = command & 7;
    }
  }

  writePixelColumn(byte) {
    this.ram[this.page * 128 + this.column] = byte;
    this.dirty = true;
    if (this.addressMode === 0) {
      if (++this.column > this.columnEnd) {
        this.column = this.columnStart;
        if (++this.page > this.pageEnd) this.page = this.pageStart;
      }
    } else if (this.addressMode === 1) {
      if (++this.page > this.pageEnd) {
        this.page = this.pageStart;
        if (++this.column > this.columnEnd) this.column = this.columnStart;
      }
    } else {
      this.column = (this.column + 1) & 127;
    }
  }

  redraw() {
    if (!this.dirty) return;
    const { data } = this.image;
    for (let y = 0; y < 64; y++) {
      const row = (y >> 3) * 128;
      const mask = 1 << (y & 7);
      for (let x = 0; x < 128; x++) {
        const lit = this.on && (this.allOn || (Boolean(this.ram[row + x] & mask) !== this.inverse));
        const index = (y * 128 + x) * 4;
        data[index] = lit ? 183 : 6;
        data[index + 1] = lit ? 246 : 18;
        data[index + 2] = lit ? 255 : 29;
        data[index + 3] = 255;
      }
    }
    this.context.putImageData(this.image, 0, 0);
    this.dirty = false;
  }
}
