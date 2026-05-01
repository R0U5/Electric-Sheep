#!/usr/bin/env python3
"""
Orbital Mechanics Sandbox
A terminal-based n-body gravitational simulation.

Controls:
  Click: Launch a small body from that position with orbital velocity
  +/-: Zoom in/out
  Space: Pause/unpause
  C: Clear all bodies (keep sun)
  R: Reset with sun only
  S: Spawn a random asteroid belt
  Arrow keys: Pan view
  Q: Quit
"""

import sys
import math
import curses
import random
from dataclasses import dataclass
from typing import List

@dataclass
class Body:
    x: float
    y: float
    vx: float
    vy: float
    mass: float
    radius: float
    char: str
    color: int
    trail: List[tuple] = None
    
    def __post_init__(self):
        if self.trail is None:
            self.trail = []

class OrbitalSandbox:
    G = 0.5  # Gravitational constant (tuned for terminal scale)
    SUN_MASS = 5000
    TIME_STEP = 0.1
    TRAIL_LENGTH = 50
    
    def __init__(self, stdscr):
        self.stdscr = stdscr
        curses.curs_set(0)
        self.stdscr.nodelay(1)
        self.stdscr.timeout(50)
        
        # Colors
        curses.start_color()
        curses.init_pair(1, curses.COLOR_YELLOW, curses.COLOR_BLACK)  # Sun
        curses.init_pair(2, curses.COLOR_CYAN, curses.COLOR_BLACK)    # Planet
        curses.init_pair(3, curses.COLOR_WHITE, curses.COLOR_BLACK)   # Small body
        curses.init_pair(4, curses.COLOR_RED, curses.COLOR_BLACK)     # UI
        curses.init_pair(5, curses.COLOR_GREEN, curses.COLOR_BLACK)   # Success
        
        self.height, self.width = self.stdscr.getmaxyx()
        self.center_x = self.width // 2
        self.center_y = self.height // 2
        self.zoom = 1.0
        self.pan_x = 0
        self.pan_y = 0
        self.paused = False
        
        self.reset()
    
    def reset(self):
        """Reset simulation with just the sun."""
        self.bodies = [
            Body(0, 0, 0, 0, self.SUN_MASS, 2, 'O', 1)
        ]
    
    def clear_orbiters(self):
        """Clear all bodies except the sun."""
        self.bodies = [b for b in self.bodies if b.mass >= self.SUN_MASS]
    
    def spawn_asteroid_belt(self):
        """Spawn a ring of asteroids."""
        for i in range(20):
            angle = (2 * math.pi * i) / 20
            distance = 30 + random.uniform(-5, 5)
            x = math.cos(angle) * distance
            y = math.sin(angle) * distance
            
            # Orbital velocity for circular orbit: v = sqrt(GM/r)
            v_mag = math.sqrt(self.G * self.SUN_MASS / distance)
            vx = -math.sin(angle) * v_mag
            vy = math.cos(angle) * v_mag
            
            body = Body(x, y, vx, vy, 1, 0, '.', 3)
            self.bodies.append(body)
    
    def world_to_screen(self, x, y):
        """Convert world coordinates to screen coordinates."""
        sx = int(self.center_x + (x + self.pan_x) * self.zoom)
        sy = int(self.center_y + (y + self.pan_y) * self.zoom * 0.5)  # 0.5 for wide chars
        return sx, sy
    
    def screen_to_world(self, sx, sy):
        """Convert screen coordinates to world coordinates."""
        x = (sx - self.center_x) / self.zoom - self.pan_x
        y = (sy - self.center_y) / (self.zoom * 0.5) - self.pan_y
        return x, y
    
    def launch_body(self, sx, sy):
        """Launch a small body from screen position with orbital velocity."""
        x, y = self.screen_to_world(sx, sy)
        
        # Calculate distance from sun
        r = math.sqrt(x * x + y * y)
        if r < 1:
            return  # Too close to sun
        
        # Calculate orbital velocity for a roughly circular orbit
        # v = sqrt(GM/r) for circular orbit
        v_mag = math.sqrt(self.G * self.SUN_MASS / r) * random.uniform(0.9, 1.1)
        
        # Velocity perpendicular to radius vector
        angle = math.atan2(y, x)
        vx = -math.sin(angle) * v_mag
        vy = math.cos(angle) * v_mag
        
        # Slight random perturbation for elliptical orbits
        vx += random.uniform(-0.1, 0.1)
        vy += random.uniform(-0.1, 0.1)
        
        body = Body(x, y, vx, vy, 5, 1, 'o', 2)
        self.bodies.append(body)
    
    def compute_gravity(self, b1: Body, b2: Body):
        """Compute gravitational force between two bodies."""
        dx = b2.x - b1.x
        dy = b2.y - b1.y
        dist_sq = dx * dx + dy * dy
        dist = math.sqrt(dist_sq)
        
        if dist < b1.radius + b2.radius:
            # Simple collision - bodies merge
            return None, None
        
        # F = G * m1 * m2 / r^2
        force = self.G * b1.mass * b2.mass / dist_sq
        fx = force * dx / dist
        fy = force * dy / dist
        
        return fx, fy
    
    def update_physics(self):
        """Update all bodies using n-body gravity."""
        if self.paused:
            return
        
        # Calculate forces
        forces = [(0.0, 0.0) for _ in self.bodies]
        
        for i in range(len(self.bodies)):
            for j in range(i + 1, len(self.bodies)):
                b1, b2 = self.bodies[i], self.bodies[j]
                fx, fy = self.compute_gravity(b1, b2)
                
                if fx is None:  # Collision
                    # Merge smaller into larger
                    if b1.mass >= b2.mass:
                        b1.mass += b2.mass
                        b2.mass = 0  # Mark for removal
                    else:
                        b2.mass += b1.mass
                        b1.mass = 0
                    continue
                
                forces[i] = (forces[i][0] + fx, forces[i][1] + fy)
                forces[j] = (forces[j][0] - fx, forces[j][1] - fy)
        
        # Update velocities and positions
        for i, body in enumerate(self.bodies):
            if body.mass == 0:
                continue
            
            ax = forces[i][0] / body.mass
            ay = forces[i][1] / body.mass
            
            body.vx += ax * self.TIME_STEP
            body.vy += ay * self.TIME_STEP
            
            body.x += body.vx * self.TIME_STEP
            body.y += body.vy * self.TIME_STEP
            
            # Update trail
            body.trail.append((body.x, body.y))
            if len(body.trail) > self.TRAIL_LENGTH:
                body.trail.pop(0)
        
        # Remove merged bodies
        self.bodies = [b for b in self.bodies if b.mass > 0]
    
    def draw(self):
        """Render the simulation."""
        self.stdscr.clear()
        self.height, self.width = self.stdscr.getmaxyx()
        self.center_x = self.width // 2
        self.center_y = self.height // 2
        
        # Draw trails
        for body in self.bodies:
            for i, (tx, ty) in enumerate(body.trail):
                sx, sy = self.world_to_screen(tx, ty)
                if 0 <= sx < self.width - 1 and 0 <= sy < self.height - 1:
                    alpha = int(255 * (i / len(body.trail))) if body.trail else 0
                    if body.mass >= self.SUN_MASS:
                        char = '*'
                    else:
                        char = '.'
                    try:
                        self.stdscr.addstr(sy, sx, char, curses.color_pair(body.color))
                    except:
                        pass
        
        # Draw bodies
        for body in self.bodies:
            sx, sy = self.world_to_screen(body.x, body.y)
            if 0 <= sx < self.width - 1 and 0 <= sy < self.height - 1:
                char = body.char
                if body.radius >= 2:
                    # Draw larger bodies with multiple chars
                    for dy in range(-1, 2):
                        for dx in range(-1, 2):
                            if abs(dx) + abs(dy) <= 1:
                                try:
                                    self.stdscr.addstr(sy + dy, sx + dx, char, 
                                                      curses.color_pair(body.color) | curses.A_BOLD)
                                except:
                                    pass
                else:
                    try:
                        self.stdscr.addstr(sy, sx, char, 
                                          curses.color_pair(body.color) | curses.A_BOLD)
                    except:
                        pass
        
        # Draw UI
        ui_y = 0
        self.stdscr.addstr(ui_y, 0, "═" * (self.width - 1), curses.color_pair(4))
        ui_y += 1
        self.stdscr.addstr(ui_y, 2, "🌌 ORBITAL MECHANICS SANDBOX", curses.color_pair(4) | curses.A_BOLD)
        ui_y += 1
        
        status = "PAUSED" if self.paused else "RUNNING"
        self.stdscr.addstr(ui_y, 2, f"Status: {status}  |  Bodies: {len(self.bodies)}  |  Zoom: {self.zoom:.1f}x", 
                          curses.color_pair(3))
        ui_y += 1
        
        self.stdscr.addstr(ui_y, 2, "Click: Launch  +/-: Zoom  Space: Pause  C: Clear orbiters  R: Reset  S: Asteroid belt  Arrows: Pan  Q: Quit", 
                          curses.color_pair(3))
        ui_y += 1
        self.stdscr.addstr(ui_y, 0, "═" * (self.width - 1), curses.color_pair(4))
        
        # Draw help text at bottom
        help_text = "Tip: Launch bodies from different distances to create elliptical orbits!"
        if self.width > len(help_text) + 4:
            self.stdscr.addstr(self.height - 2, 2, help_text, curses.color_pair(5))
        
        self.stdscr.refresh()
    
    def run(self):
        """Main loop."""
        # Spawn initial asteroid belt for visual interest
        self.spawn_asteroid_belt()
        
        curses.mousemask(curses.BUTTON1_CLICKED)
        
        while True:
            self.update_physics()
            self.draw()
            
            try:
                key = self.stdscr.getch()
            except:
                key = -1
            
            if key == ord('q') or key == ord('Q'):
                break
            elif key == ord(' '):
                self.paused = not self.paused
            elif key == ord('r') or key == ord('R'):
                self.reset()
            elif key == ord('c') or key == ord('C'):
                self.clear_orbiters()
            elif key == ord('s') or key == ord('S'):
                self.spawn_asteroid_belt()
            elif key == ord('+') or key == ord('='):
                self.zoom *= 1.2
            elif key == ord('-') or key == ord('_'):
                self.zoom /= 1.2
            elif key == curses.KEY_UP:
                self.pan_y += 10 / self.zoom
            elif key == curses.KEY_DOWN:
                self.pan_y -= 10 / self.zoom
            elif key == curses.KEY_LEFT:
                self.pan_x += 10 / self.zoom
            elif key == curses.KEY_RIGHT:
                self.pan_x -= 10 / self.zoom
            elif key == curses.KEY_MOUSE:
                try:
                    _, mx, my, _, _ = curses.getmouse()
                    self.launch_body(mx, my)
                except:
                    pass

def main():
    try:
        curses.wrapper(lambda stdscr: OrbitalSandbox(stdscr).run())
    except KeyboardInterrupt:
        pass
    print("Thanks for playing with gravity!")

if __name__ == "__main__":
    main()
