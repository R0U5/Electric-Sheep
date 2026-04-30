#!/usr/bin/env python3
"""
CHIP-8 Emulator — A clean, self-contained CHIP-8 interpreter.
Emulates the fictional 1970s console: 4K RAM, 16 registers, 64x32 display,
keyboard input, and delay/sound timers.
"""

import sys
import random
import time

# ─── Display constants ───────────────────────────────────────────────────────
SCREEN_W = 64
SCREEN_H = 32

FONT_SPRITES = [
    0xF0, 0x90, 0x90, 0x90, 0xF0,  # 0
    0x20, 0x60, 0x20, 0x20, 0x70,  # 1
    0xF0, 0x10, 0xF0, 0x80, 0xF0,  # 2
    0xF0, 0x10, 0xF0, 0x10, 0xF0,  # 3
    0x90, 0x90, 0xF0, 0x10, 0x10,  # 4
    0xF0, 0x80, 0xF0, 0x10, 0xF0,  # 5
    0xF0, 0x80, 0xF0, 0x90, 0xF0,  # 6
    0xF0, 0x10, 0x20, 0x40, 0x40,  # 7
    0xF0, 0x90, 0xF0, 0x90, 0xF0,  # 8
    0xF0, 0x90, 0xF0, 0x10, 0xF0,  # 9
    0xF0, 0x90, 0xF0, 0x90, 0x90,  # A
    0xE0, 0x80, 0xE0, 0x80, 0xE0,  # B
    0xF0, 0x80, 0x80, 0x80, 0xF0,  # C
    0xE0, 0x80, 0x80, 0x80, 0xE0,  # D
    0xF0, 0x80, 0xF0, 0x80, 0xF0,  # E
    0xF0, 0x80, 0xF0, 0x80, 0x80,  # F
]


class Chip8:
    def __init__(self):
        self.ram = bytearray(4096)
        for i, sprite in enumerate(FONT_SPRITES):
            self.ram[i] = sprite

        self.V = [0] * 16
        self.I = 0
        self.pc = 0x200
        self.stack = []
        self.sp = 0
        self.display = [[0] * SCREEN_W for _ in range(SCREEN_H)]
        self.keys = [0] * 16
        self.delay_timer = 0
        self.sound_timer = 0
        self.timer_last_tick = time.time()
        self.halted = False

    def load_rom(self, data: bytes):
        for i, byte in enumerate(data):
            self.ram[0x200 + i] = byte

    def reset_keys(self):
        self.keys = [0] * 16

    def tick_timers(self):
        now = time.time()
        elapsed = now - self.timer_last_tick
        decrements = int(elapsed / (1.0 / 60.0))
        if decrements > 0:
            self.timer_last_tick += decrements * (1.0 / 60.0)
            if self.delay_timer > 0:
                self.delay_timer = max(0, self.delay_timer - decrements)
            if self.sound_timer > 0:
                self.sound_timer = max(0, self.sound_timer - decrements)

    def clear_display(self):
        self.display = [[0] * SCREEN_W for _ in range(SCREEN_H)]

    def set_pixel(self, x: int, y: int, value: int):
        x %= SCREEN_W
        y %= SCREEN_H
        old = self.display[y][x]
        self.display[y][x] ^= value
        return 1 if old == 1 and value == 1 else 0

    def draw_sprite(self, x: int, y: int, height: int):
        self.V[0xF] = 0
        for row in range(height):
            sprite_byte = self.ram[self.I + row]
            for col in range(8):
                bit = (sprite_byte >> (7 - col)) & 1
                if bit:
                    if self.set_pixel(x + col, y + row, 1):
                        self.V[0xF] = 1

    def ascii_display(self) -> str:
        lines = []
        for row in self.display:
            lines.append("".join("█" if p else " " for p in row))
        return "\n".join(lines)

    def step(self):
        if self.halted:
            time.sleep(0.01)
            return True

        self.tick_timers()

        hi = self.ram[self.pc]
        lo = self.ram[self.pc + 1]
        opcode = (hi << 8) | lo
        self.pc = (self.pc + 2) & 0xFFFF

        nnn = opcode & 0x0FFF
        nn  = opcode & 0x00FF
        n   = opcode & 0x000F
        x   = (opcode >> 8) & 0x000F
        y   = (opcode >> 4) & 0x000F

        op = opcode >> 12

        if op == 0x0:
            if nn == 0xE0:
                self.clear_display()
            elif nnn == 0x0EE:
                if self.stack:
                    self.pc = self.stack.pop()
            # 0nnn: RCA 1802 call — ignored

        elif op == 0x1:
            self.pc = nnn

        elif op == 0x2:
            self.stack.append(self.pc)
            self.pc = nnn

        elif op == 0x3:
            if self.V[x] == nn:
                self.pc = (self.pc + 2) & 0xFFFF

        elif op == 0x4:
            if self.V[x] != nn:
                self.pc = (self.pc + 2) & 0xFFFF

        elif op == 0x5:
            if self.V[x] == self.V[y]:
                self.pc = (self.pc + 2) & 0xFFFF

        elif op == 0x6:
            self.V[x] = nn

        elif op == 0x7:
            self.V[x] = (self.V[x] + nn) & 0xFF

        elif op == 0x8:
            if n == 0x0:
                self.V[x] = self.V[y]
            elif n == 0x1:
                self.V[x] |= self.V[y]
            elif n == 0x2:
                self.V[x] &= self.V[y]
            elif n == 0x3:
                self.V[x] ^= self.V[y]
            elif n == 0x4:
                total = self.V[x] + self.V[y]
                self.V[x] = total & 0xFF
                self.V[0xF] = 1 if total > 0xFF else 0
            elif n == 0x5:
                diff = self.V[x] - self.V[y]
                self.V[x] = diff & 0xFF
                self.V[0xF] = 1 if self.V[x] >= self.V[y] else 0
            elif n == 0x6:
                self.V[0xF] = self.V[y] & 1
                self.V[x] = self.V[y] >> 1
            elif n == 0x7:
                diff = self.V[y] - self.V[x]
                self.V[x] = diff & 0xFF
                self.V[0xF] = 1 if self.V[y] >= self.V[x] else 0
            elif n == 0xE:
                self.V[0xF] = (self.V[y] >> 7) & 1
                self.V[x] = (self.V[y] << 1) & 0xFF

        elif op == 0x9:
            if n == 0x0 and self.V[x] != self.V[y]:
                self.pc = (self.pc + 2) & 0xFFFF

        elif op == 0xA:
            self.I = nnn

        elif op == 0xB:
            self.pc = (nnn + self.V[0]) & 0xFFFF

        elif op == 0xC:
            self.V[x] = random.randint(0, 255) & nn

        elif op == 0xD:
            self.draw_sprite(self.V[x], self.V[y], n)

        elif op == 0xE:
            if nn == 0x9E:
                if self.keys[self.V[x]]:
                    self.pc = (self.pc + 2) & 0xFFFF
            elif nn == 0xA1:
                if not self.keys[self.V[x]]:
                    self.pc = (self.pc + 2) & 0xFFFF

        elif op == 0xF:
            if nn == 0x07:
                self.V[x] = self.delay_timer
            elif nn == 0x0A:
                key = None
                for i, k in enumerate(self.keys):
                    if k:
                        key = i
                        break
                if key is None:
                    self.pc = (self.pc - 2) & 0xFFFF
                else:
                    self.V[x] = key
                    self.keys[key] = 0  # consume key
            elif nn == 0x15:
                self.delay_timer = self.V[x]
            elif nn == 0x18:
                self.sound_timer = self.V[x]
            elif nn == 0x1E:
                self.I = (self.I + self.V[x]) & 0xFFFF
            elif nn == 0x29:
                self.I = (self.V[x] & 0xF) * 5
            elif nn == 0x33:
                vx = self.V[x]
                self.ram[self.I]     = (vx // 100) % 10
                self.ram[self.I + 1] = (vx // 10) % 10
                self.ram[self.I + 2] = vx % 10
            elif nn == 0x55:
                for i in range(x + 1):
                    self.ram[self.I + i] = self.V[i]
            elif nn == 0x65:
                for i in range(x + 1):
                    self.V[i] = self.ram[self.I + i]

        return True


# ─── Demo ROM: draws "CHIP8" letters, then animates a bouncing ball ─────────
DEMO_ROM = bytes([
    # CLS
    0x00, 0xE0,
    # Draw "C" at x=4, y=8  (sprite data at I=0x200)
    0x60, 0x04,  # V0 = 4
    0x61, 0x08,  # V1 = 8
    0xA2, 0x00,  # I = 0x200 (C sprite)
    0xD0, 0x05,  # DRW V0,V1,5
    # Draw "H" at x=14
    0x60, 0x0E,  # V0 = 14
    0xA2, 0x05,  # I = 0x205 (H sprite)
    0xD0, 0x05,  # DRW V0,V1,5
    # Draw "I" at x=24
    0x60, 0x18,  # V0 = 24
    0xA2, 0x0A,  # I = 0x20A (I sprite)
    0xD0, 0x05,  # DRW V0,V1,5
    # Draw "P" at x=34
    0x60, 0x22,  # V0 = 34
    0xA2, 0x0F,  # I = 0x20F (P sprite)
    0xD0, 0x05,  # DRW V0,V1,5
    # Draw "8" at x=44
    0x60, 0x2C,  # V0 = 44
    0xA2, 0x14,  # I = 0x214 (8 sprite)
    0xD0, 0x05,  # DRW V0,V1,5

    # Store a bouncing ball in V8-VB
    0x68, 0x20,  # V8 = 32  (ball x)
    0x69, 0x10,  # V9 = 16  (ball y)
    0x6A, 0x01,  # VA = 1   (vx)
    0x6B, 0x01,  # VB = 1   (vy)

    # bounce loop: 0x02CC
    0x80, 0x28,  # V8 += VA  (update ball x)
    0x80, 0x39,  # V9 += VB  (update ball y)

    # Bounce x at walls
    0x48, 0x00,  # V8 == 0?
    0x3A, 0x01,  # VA = 1   (set forward)
    0x48, 0x3C,  # V8 == 60?
    0x3A, 0xFF,  # VA = -1  (set backward)

    # Bounce y at top/bottom
    0x49, 0x00,  # V9 == 0?
    0x3B, 0x01,  # VB = 1
    0x49, 0x1E,  # V9 == 30?
    0x3B, 0xFF,  # VB = -1

    # Draw ball
    0xA2, 0x19,  # I = 0x219 (dot sprite)
    0xD8, 0x09,  # DRW V8, V9, 1

    # Small delay via nested calls
    0x22, 0xD0,  # CALL delay
    0x12, 0xCC,  # JP bounce_loop

    # delay sub: 0x02D0
    0x60, 0xFF,  # V0 = 255
    0x70, 0x01,  # V0 -= 1  (no carry on sub, just loop)
    0x30, 0x00,  # V0 == 0?
    0x12, 0xD4,  # JP delay-2
    0x60, 0x00,  # V0 = 0
    0x00, 0xEE,  # RET

    # Sprite data (5 bytes each):
    # 0x200: C = 0xF0,0x80,0x80,0x80,0xF0
    0xF0, 0x80, 0x80, 0x80, 0xF0,
    # 0x205: H = 0x90,0x90,0xF0,0x90,0x90
    0x90, 0x90, 0xF0, 0x90, 0x90,
    # 0x20A: I = 0xE0,0x80,0x80,0x80,0xE0
    0xE0, 0x80, 0x80, 0x80, 0xE0,
    # 0x20F: P = 0xF0,0x90,0xF0,0x80,0x80
    0xF0, 0x90, 0xF0, 0x80, 0x80,
    # 0x214: 8 = 0xF0,0x90,0xF0,0x90,0xF0
    0xF0, 0x90, 0xF0, 0x90, 0xF0,
    # 0x219: dot = 0xFF (1x8 filled)
    0xFF,
])


def run(cpu: Chip8, max_cycles: int = 200000, fps: int = 60):
    cycle_limit = max_cycles
    cycles = 0
    last_display = ""
    import os
    import select as sel

    # Key bindings: ASCII → CHIP-8 key index
    KEY_MAP = {
        '1': 0x1, '2': 0x2, '3': 0x3, '4': 0xC,
        'q': 0x4, 'w': 0x5, 'e': 0x6, 'r': 0xD,
        'a': 0x7, 's': 0x8, 'd': 0x9, 'f': 0xE,
        'z': 0xA, 'x': 0x0, 'c': 0xB, 'v': 0xF,
    }

    frame_time = 1.0 / fps
    last_frame = time.time()

    def redraw():
        nonlocal last_display
        out = cpu.ascii_display()
        if out != last_display:
            # Use ANSI clear and home
            sys.stdout.write("\x1b[2J\x1b[H")
            sys.stdout.write(out)
            regs = " ".join(f"{v:02X}" for v in cpu.V[:0xF])
            sys.stdout.write(f"\n\x1b[2KCycles: {cycles:,}  I:0x{cpu.I:03X}  V: {regs}\n")
            sys.stdout.write("Keys: 1qaz 2wse 3edc 4rfa  (CHIP-8 hex)   ESC: quit\n")
            sys.stdout.flush()
            last_display = out

    try:
        while cycles < cycle_limit:
            cycle_start = time.time()

            # Non-blocking key check
            cpu.step()
            cycles += 1

            # Read any key presses
            while sel.select([sys.stdin], [], [], 0)[0]:
                try:
                    ch = sys.stdin.read(1)
                except:
                    ch = ""
                if not ch:
                    break
                if ch == "\x1b":
                    return cycles
                if ch in KEY_MAP:
                    cpu.keys[KEY_MAP[ch]] = 1

            # Throttle to target FPS
            elapsed = time.time() - cycle_start
            if elapsed < frame_time:
                time.sleep(frame_time - elapsed)

            if cycles % 2000 == 0:
                redraw()

    except KeyboardInterrupt:
        pass

    redraw()
    return cycles


def main():
    import argparse
    parser = argparse.ArgumentParser(description="CHIP-8 Emulator")
    parser.add_argument("rom", nargs="?", help="ROM file to load")
    parser.add_argument("--demo", action="store_true", help="Run built-in demo")
    parser.add_argument("--limit", type=int, default=200000, help="Max cycles")
    args = parser.parse_args()

    cpu = Chip8()

    if args.rom:
        with open(args.rom, "rb") as f:
            rom_data = f.read()
    else:
        rom_data = DEMO_ROM

    cpu.load_rom(rom_data)
    print(f"CHIP-8 Emulator")
    print(f"ROM: {len(rom_data)} bytes  PC: 0x{cpu.pc:03X}  RAM: {4096-len(rom_data)} free")
    print("─" * 64)

    total = run(cpu, max_cycles=args.limit)
    print(f"\nExited after {total:,} cycles.")


if __name__ == "__main__":
    main()
