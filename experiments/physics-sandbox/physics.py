#!/usr/bin/env python3
"""
Terminal Physics Sandbox - A particle physics simulation in your terminal.

Simulates particles with mass, velocity, gravity, and elastic collisions.
Add particles by clicking their start position, dragging for velocity, and releasing.
Or use the demo scenarios to watch chaos unfold.

Controls:
  - Click and drag to launch particles
  - G: Toggle gravity
  - F: Toggle friction/damping
  - R: Reset all particles
  - D: Demo mode (random particles)
  - +/-: Adjust simulation speed
  - Q: Quit
"""

import sys
import math
import time
import random
import select
import termios
import tty
from dataclasses import dataclass
from typing import List, Tuple, Optional

# Terminal escape codes
CLEAR_SCREEN = "\033[2J"
HIDE_CURSOR = "\033[?25l"
SHOW_CURSOR = "\033[?25h"
RESET = "\033[0m"
MOVE_CURSOR = "\033[{row};{col}H"

@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    mass: float = 1.0
    radius: float = 1.0
    char: str = "●"
    life: float = float('inf')
    
    def kinetic_energy(self) -> float:
        v_squared = self.vx**2 + self.vy**2
        return 0.5 * self.mass * v_squared

def get_terminal_size() -> Tuple[int, int]:
    """Get current terminal dimensions."""
    import shutil
    size = shutil.get_terminal_size()
    return size.lines, size.columns

def set_nonblocking_input() -> int:
    """Set terminal to non-blocking input mode."""
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    tty.setraw(fd)
    return fd, old_settings

def restore_terminal(fd, old_settings):
    """Restore terminal settings."""
    termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

def parse_mouse_sequence(seq: str) -> Optional[Tuple[str, int, int]]:
    """Parse SGR (1006) mouse sequence. Returns (button, x, y) or None."""
    # SGR format: \033[<button;x;yM (press) or m (release)
    if not seq.startswith("\033["):
        return None
    
    # Strip the escape prefix
    inner = seq[2:]
    if not inner.startswith('<') or not (inner.endswith('M') or inner.endswith('m')):
        return None
    
    inner = inner[1:-1]  # Remove < and M/m
    parts = inner.split(';')
    if len(parts) != 3:
        return None
    
    try:
        button = int(parts[0])
        x = int(parts[1])
        y = int(parts[2])
        event = 'press' if seq.endswith('M') else 'release'
        # SGR mouse encoding: button = 32 + mouse_button (press), 32+64 (release)
        # Adjust for the encoding
        if event == 'press' and button >= 32:
            button = button - 32
        elif event == 'release' and button >= 96:
            button = button - 96
        return (event, button, x, y)
    except ValueError:
        return None

class PhysicsSandbox:
    def __init__(self):
        self.rows, self.cols = get_terminal_size()
        self.particles: List[Particle] = []
        self.gravity_active = True
        self.friction_active = True
        self.speed_multiplier = 1.0
        self.simulation_step = 0.05  # seconds per physics tick
        
        # Mouse interaction state
        self.drag_start: Optional[Tuple[float, float]] = None
        self.drag_current: Optional[Tuple[float, float]] = None
        
        # Physics constants
        self.gravity = 0.15
        self.friction = 0.999
        self.bounce_damping = 0.9
        self.max_velocity = 20.0
        
        # Stats
        self.total_energy = 0.0
        self.particles_created = 0
        self.collisions = 0
        
    def add_particle(self, x: float, y: float, vx: float, vy: float, 
                     mass: Optional[float] = None, size: str = "medium"):
        """Add a new particle to the simulation."""
        size_chars = {
            "small": ("·", 0.8),
            "medium": ("●", 1.2),
            "large": ("█", 2.0)
        }
        char, radius = size_chars.get(size, size_chars["medium"])
        
        mass = mass or (radius ** 3)  # Mass scales with volume
        
        particle = Particle(
            x=x, y=y, vx=vx, vy=vy,
            mass=mass, radius=radius, char=char
        )
        self.particles.append(particle)
        self.particles_created += 1
        
    def resolve_collision(self, p1: Particle, p2: Particle):
        """Elastic collision resolution with momentum conservation."""
        dx = p2.x - p1.x
        dy = p2.y - p1.y
        distance = math.sqrt(dx**2 + dy**2)
        
        if distance == 0:
            return  # Overlapping exactly
        
        # Normalize collision vector
        nx = dx / distance
        ny = dy / distance
        
        # Relative velocity
        dvx = p2.vx - p1.vx
        dvy = p2.vy - p1.vy
        vel_along_normal = dvx * nx + dvy * ny
        
        # Don't resolve if velocities are separating
        if vel_along_normal > 0:
            return
        
        # Elastic collision impulse
        e = 0.9  # Coefficient of restitution
        impulse_scalar = -(1 + e) * vel_along_normal
        impulse_scalar /= (1/p1.mass + 1/p2.mass)
        
        impulse_x = impulse_scalar * nx
        impulse_y = impulse_scalar * ny
        
        p1.vx -= impulse_x / p1.mass
        p1.vy -= impulse_y / p1.mass
        p2.vx += impulse_x / p2.mass
        p2.vy += impulse_y / p2.mass
        
        # Separate overlapping particles
        overlap = (p1.radius + p2.radius) - distance
        if overlap > 0:
            separate_x = nx * overlap * 0.52  # Slightly more than half
            separate_y = ny * overlap * 0.52
            p1.x -= separate_x
            p1.y -= separate_y
            p2.x += separate_x
            p2.y += separate_y
            
        self.collisions += 1
        
    def update_physics(self):
        """Update all particles for one timestep."""
        dt = self.simulation_step * self.speed_multiplier
        
        for p in self.particles:
            # Apply forces
            if self.gravity_active:
                p.vy += self.gravity * dt
            
            # Apply velocity limits
            speed = math.sqrt(p.vx**2 + p.vy**2)
            if speed > self.max_velocity:
                scale = self.max_velocity / speed
                p.vx *= scale
                p.vy *= scale
            
            # Update position
            p.x += p.vx * dt
            p.y += p.vy * dt
            
            # Wall collisions
            margin = p.radius
            if p.x < margin:
                p.x = margin
                p.vx = -p.vx * self.bounce_damping
            elif p.x > self.cols - margin:
                p.x = self.cols - margin
                p.vx = -p.vx * self.bounce_damping
                
            if p.y < margin:
                p.y = margin
                p.vy = -p.vy * self.bounce_damping
            elif p.y > self.rows - margin:
                p.y = self.rows - margin
                p.vy = -p.vy * self.bounce_damping
                
                # Ground friction
                if self.friction_active and abs(p.vy) < self.gravity * 2:
                    p.vx *= 0.96
            
            # Air resistance
            if self.friction_active:
                p.vx *= self.friction
                p.vy *= self.friction
                
        # Particle-particle collisions
        for i in range(len(self.particles)):
            for j in range(i + 1, len(self.particles)):
                p1, p2 = self.particles[i], self.particles[j]
                dx = p2.x - p1.x
                dy = p2.y - p1.y
                distance = math.sqrt(dx**2 + dy**2)
                
                if distance < (p1.radius + p2.radius):
                    self.resolve_collision(p1, p2)
                    
        # Remove off-screen or unstable particles
        self.particles = [p for p in self.particles if 
                         0 <= p.x <= self.cols and 0 <= p.y <= self.rows]
        
        # Calculate total energy
        self.total_energy = sum(p.kinetic_energy() for p in self.particles)
        
    def render(self, buffer: List[List[str]]):
        """Render particles to the buffer."""
        rows = self.rows - 2  # Reserve bottom for status
        cols = self.cols
        
        # Clear buffer
        for r in range(rows):
            for c in range(cols):
                buffer[r][c] = " "
        
        # Draw drag line if dragging
        if self.drag_start and self.drag_current:
            x1, y1 = self.drag_start
            x2, y2 = self.drag_current
            self._draw_line(buffer, int(x1), int(y1), int(x2), int(y2), "░")
        
        # Draw particles
        for p in self.particles:
            px, py = int(p.x), int(p.y)
            if 0 <= py < rows and 0 <= px < cols:
                buffer[py][px] = p.char
                
        # Draw velocity vectors for large particles
        for p in self.particles:
            if p.mass > 1.5:
                px, py = int(p.x), int(p.y)
                vx_end = px + int(p.vx * 2)
                vy_end = py + int(p.vy)
                if 0 <= py < rows and 0 <= px < cols:
                    self._draw_line(buffer, px, py, vx_end, vy_end, "·")
    
    def _draw_line(self, buffer: List[List[str]], x1: int, y1: int, x2: int, y2: int, char: str):
        """Bresenham's line algorithm."""
        rows = len(buffer)
        cols = len(buffer[0]) if rows else 0
        
        dx = abs(x2 - x1)
        dy = abs(y2 - y1)
        sx = 1 if x1 < x2 else -1
        sy = 1 if y1 < y2 else -1
        err = dx - dy
        
        x, y = x1, y1
        max_iter = max(dx, dy) * 2 + 10
        
        for _ in range(max_iter):
            if 0 <= y < rows and 0 <= x < cols:
                buffer[y][x] = char
            if x == x2 and y == y2:
                break
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x += sx
            if e2 < dx:
                err += dx
                y += sy
    
    def render_status(self) -> str:
        """Build status bar string."""
        status_parts = [
            f"Particles: {len(self.particles)}",
            f"Energy: {self.total_energy:.1f}",
            f"Gravity: {'ON' if self.gravity_active else 'OFF'}",
            f"Friction: {'ON' if self.friction_active else 'OFF'}",
            f"Speed: {self.speed_multiplier:.1f}x",
            f"[G]rav [F]rict [R]eset [D]emo +/- Spd [Q]uit"
        ]
        return " | ".join(status_parts)[:self.cols-1]
    
    def create_demo_scenario(self):
        """Set up a fun demo with multiple particles."""
        mid_x, mid_y = self.cols // 2, (self.rows - 2) // 2
        
        # Central heavy mass
        self.add_particle(mid_x, mid_y, 0, 0, mass=5.0, size="large")
        
        # Orbiting particles
        for i in range(6):
            angle = i * math.pi / 3
            radius = 8
            vx = 2.5 * math.cos(angle + math.pi/2)
            vy = 2.5 * math.sin(angle + math.pi/2)
            self.add_particle(
                mid_x + radius * math.cos(angle),
                mid_y + radius * math.sin(angle),
                vx, vy,
                mass=0.8, size="medium"
            )
        
        # Random scatter
        for _ in range(10):
            x = random.randint(5, self.cols - 5)
            y = random.randint(5, self.rows - 10)
            vx = random.uniform(-3, 3)
            vy = random.uniform(-3, 3)
            size = random.choice(["small", "medium"])
            mass = 0.5 if size == "small" else 1.0
            self.add_particle(x, y, vx, vy, mass=mass, size=size)

def main():
    # Setup terminal
    print(HIDE_CURSOR, end="")
    print(CLEAR_SCREEN, end="")
    
    # Enable mouse tracking (SGR protocol)
    print("\033[?1006h", end="")  # SGR
    print("\033[?1000h", end="")  # Mouse
    
    # Enable alternative screen buffer
    print("\033[?1049h", end="")
    
    try:
        fd, old_settings = set_nonblocking_input()
        
        sandbox = PhysicsSandbox()
        rows, cols = sandbox.rows, sandbox.cols
        
        # Pre-allocate render buffer
        buffer = [[" " for _ in range(cols)] for _ in range(rows - 2)]
        
        last_frame = time.time()
        frame_delay = 1/30  # Target 30 FPS
        
        print(f"{MOVE_CURSOR.format(row=rows//2, col=cols//2-10)}Welcome to Physics Sandbox!")
        print(f"{MOVE_CURSOR.format(row=rows//2+1, col=cols//2-15)}Click and drag to launch particles")
        print(f"{MOVE_CURSOR.format(row=rows//2+2, col=cols//2-10)}Press D for demo mode...")
        
        time.sleep(1.5)
        
        while True:
            # Check for input
            if select.select([sys.stdin], [], [], 0) == ([sys.stdin], [], []):
                key = sys.stdin.read(1)
                
                if key == '\x03':  # Ctrl+C
                    break
                elif key == 'q' or key == 'Q':
                    break
                elif key == 'g' or key == 'G':
                    sandbox.gravity_active = not sandbox.gravity_active
                elif key == 'f' or key == 'F':
                    sandbox.friction_active = not sandbox.friction_active
                elif key == 'r' or key == 'R':
                    sandbox.particles.clear()
                    sandbox.collisions = 0
                elif key == 'd' or key == 'D':
                    sandbox.particles.clear()
                    sandbox.create_demo_scenario()
                elif key == '+' or key == '=':
                    sandbox.speed_multiplier = min(3.0, sandbox.speed_multiplier + 0.25)
                elif key == '-' or key == '_':
                    sandbox.speed_multiplier = max(0.25, sandbox.speed_multiplier - 0.25)
                elif key == '\033':
                    # Escape sequence - check for mouse
                    seq = key + sys.stdin.read(100)
                    mouse = parse_mouse_sequence(seq)
                    if mouse:
                        event, button, x, y = mouse
                        
                        if event == 'press' and y < rows - 2:
                            sandbox.drag_start = (x, y)
                            sandbox.drag_current = (x, y)
                        elif event == 'release' and sandbox.drag_start and y < rows - 2:
                            # Launch particle with velocity based on drag
                            x1, y1 = sandbox.drag_start
                            dx = x1 - x  # Reverse: pull back to shoot forward
                            dy = y1 - y
                            vx = dx * 0.15  # Scale factor
                            vy = dy * 0.15
                            
                            sandbox.add_particle(x1, y1, vx, vy, size="medium")
                            sandbox.drag_start = None
                            sandbox.drag_current = None
                        
            # Check for mouse drag updates (simplified - real implementation would track motion)
                    
            # Update physics (may step multiple times per frame)
            sandbox.rows, sandbox.cols = get_terminal_size()
            sandbox.update_physics()
            
            # Throttle rendering
            now = time.time()
            if now - last_frame >= frame_delay:
                # Resize buffer if needed
                rows, cols = sandbox.rows, sandbox.cols
                if len(buffer) != rows - 2 or (buffer and len(buffer[0]) != cols):
                    buffer = [[" " for _ in range(cols)] for _ in range(rows - 2)]
                
                sandbox.render(buffer)
                
                # Draw buffer to screen
                output = ""
                for row_idx, row in enumerate(buffer):
                    output += MOVE_CURSOR.format(row=row_idx + 1, col=1) + "".join(row)
                
                # Draw status bar
                status = sandbox.render_status()
                output += MOVE_CURSOR.format(row=rows, col=1) + status.ljust(cols)
                
                print(output, end="", flush=True)
                last_frame = now
            else:
                time.sleep(0.001)
                
    except KeyboardInterrupt:
        pass
    finally:
        # Cleanup
        print(SHOW_CURSOR, end="")
        print("\033[?1006l", end="")  # Disable SGR mouse
        print("\033[?1000l", end="")  # Disable mouse
        print("\033[?1049l", end="")  # Restore normal screen
        
        try:
            restore_terminal(fd, old_settings)
        except:
            pass

if __name__ == "__main__":
    main()
