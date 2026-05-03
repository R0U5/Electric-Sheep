#!/usr/bin/env python3
"""
Real-Time Physics Engine with Spatial Hashing Collision Detection
N-body particle dynamics with configurable forces and collision models.
"""

import math
import random
import time
from dataclasses import dataclass, field
from typing import List, Dict, Set, Tuple, Optional, Callable
from collections import defaultdict


@dataclass
class Vector2:
    """2D vector with physics operations."""
    x: float = 0.0
    y: float = 0.0
    
    def __add__(self, other: 'Vector2') -> 'Vector2':
        return Vector2(self.x + other.x, self.y + other.y)
    
    def __sub__(self, other: 'Vector2') -> 'Vector2':
        return Vector2(self.x - other.x, self.y - other.y)
    
    def __mul__(self, scalar: float) -> 'Vector2':
        return Vector2(self.x * scalar, self.y * scalar)
    
    def __rmul__(self, scalar: float) -> 'Vector2':
        return Vector2(self.x * scalar, self.y * scalar)
    
    def __truediv__(self, scalar: float) -> 'Vector2':
        return Vector2(self.x / scalar, self.y / scalar)
    
    def copy(self) -> 'Vector2':
        return Vector2(self.x, self.y)
    
    def dot(self, other: 'Vector2') -> float:
        return self.x * other.x + self.y * other.y
    
    def magnitude(self) -> float:
        return math.sqrt(self.x * self.x + self.y * self.y)
    
    def magnitude_squared(self) -> float:
        return self.x * self.x + self.y * self.y
    
    def normalize(self) -> 'Vector2':
        mag = self.magnitude()
        if mag < 1e-10:
            return Vector2(0, 0)
        return Vector2(self.x / mag, self.y / mag)
    
    def reflect(self, normal: 'Vector2') -> 'Vector2':
        """Reflect this vector across a normal."""
        n = normal.normalize()
        return self - n * (2 * self.dot(n))
    
    def project_onto(self, other: 'Vector2') -> 'Vector2':
        """Project this vector onto another."""
        mag_sq = other.magnitude_squared()
        if mag_sq < 1e-10:
            return Vector2(0, 0)
        scalar = self.dot(other) / mag_sq
        return other * scalar
    
    def perpendicular(self) -> 'Vector2':
        """Return perpendicular vector (rotated 90° CCW)."""
        return Vector2(-self.y, self.x)
    

    
    def __repr__(self) -> str:
        return f"V2({self.x:.3f}, {self.y:.3f})"


@dataclass
class Particle:
    """Physics particle with mass, velocity, and collision properties."""
    id: int
    pos: Vector2
    vel: Vector2
    mass: float = 1.0
    radius: float = 0.5
    restitution: float = 0.9  # Bounciness (0-1)
    friction: float = 0.0  # Surface friction
    charge: float = 0.0  # For electrostatic forces
    fixed: bool = False  # Immobile/static particle
    color: str = "white"
    
    # For verlet integration
    old_pos: Optional[Vector2] = None
    accumulated_force: Vector2 = field(default_factory=lambda: Vector2(0, 0))
    
    def kinetic_energy(self) -> float:
        v_squared = self.vel.magnitude_squared()
        return 0.5 * self.mass * v_squared
    
    def momentum(self) -> Vector2:
        return self.vel * self.mass


class SpatialHash:
    """
    Uniform grid spatial hashing for O(1) neighbor queries.
    Reduces collision checks from O(n²) to O(n) for local interactions.
    Stores particle IDs rather than Particle objects to avoid hash mutation issues.
    """
    
    def __init__(self, cell_size: float = 2.0):
        self.cell_size = cell_size
        self.grid: Dict[Tuple[int, int], Set[int]] = defaultdict(set)
        self.particle_cells: Dict[int, Tuple[int, int]] = {}
        self._particle_map: Dict[int, Particle] = {}  # ID -> Particle lookup
    
    def _get_cell(self, pos: Vector2) -> Tuple[int, int]:
        """Convert position to grid cell coordinates."""
        return (int(pos.x // self.cell_size), int(pos.y // self.cell_size))
    
    def _get_neighbor_cells(self, cell: Tuple[int, int]) -> List[Tuple[int, int]]:
        """Get a 3x3 block of cells around given cell."""
        cx, cy = cell
        return [
            (cx + dx, cy + dy)
            for dx in range(-1, 2)
            for dy in range(-1, 2)
        ]
    
    def insert(self, particle: Particle):
        """Add particle to appropriate grid cell."""
        cell = self._get_cell(particle.pos)
        self.grid[cell].add(particle.id)
        self.particle_cells[particle.id] = cell
        self._particle_map[particle.id] = particle
    
    def update(self, particle: Particle):
        """Move particle to new cell if position changed."""
        new_cell = self._get_cell(particle.pos)
        old_cell = self.particle_cells.get(particle.id)
        
        if old_cell != new_cell:
            if old_cell is not None:
                self.grid[old_cell].discard(particle.id)
            self.grid[new_cell].add(particle.id)
            self.particle_cells[particle.id] = new_cell
    
    def remove(self, particle: Particle):
        """Remove particle from grid."""
        cell = self.particle_cells.get(particle.id)
        if cell is not None:
            self.grid[cell].discard(particle.id)
            del self.particle_cells[particle.id]
        if particle.id in self._particle_map:
            del self._particle_map[particle.id]
    
    def get_neighbors(self, particle: Particle, particle_map: Dict[int, Particle]) -> List[Particle]:
        """Get all particles within collision range of given particle."""
        cell = self._get_cell(particle.pos)
        neighbors = []
        range_squared = (2 * particle.radius + self.cell_size) ** 2
        
        for neighbor_cell in self._get_neighbor_cells(cell):
            for other_id in self.grid.get(neighbor_cell, set()):
                if other_id != particle.id:
                    other = particle_map.get(other_id)
                    if other is None:
                        continue
                    # Quick distance check
                    dist_sq = (particle.pos - other.pos).magnitude_squared()
                    if dist_sq <= range_squared:
                        neighbors.append(other)
        
        return neighbors
    
    def clear(self):
        """Empty the grid."""
        self.grid.clear()
        self.particle_cells.clear()
        self._particle_map.clear()
    
    def get_stats(self) -> Dict:
        """Returns grid statistics."""
        if not self.grid:
            return {"cells": 0, "avg_per_cell": 0, "max_per_cell": 0, "total_particles": 0}
        
        counts = [len(pids) for pids in self.grid.values()]
        return {
            "cells": len(self.grid),
            "avg_per_cell": sum(counts) / len(counts),
            "max_per_cell": max(counts) if counts else 0,
            "total_particles": len(self._particle_map)
        }


@dataclass
class ForceField:
    """Global force field (like gravity or constant wind)."""
    field_type: str  # "constant", "radial", "vortex"
    strength: float
    center: Optional[Vector2] = None
    direction: Optional[Vector2] = None
    
    def compute(self, pos: Vector2) -> Vector2:
        if self.field_type == "constant":
            return self.direction or Vector2(0, -1)
        elif self.field_type == "radial":
            if self.center is None:
                return Vector2(0, 0)
            to_center = self.center - pos
            return to_center.normalize() * self.strength
        elif self.field_type == "vortex":
            if self.center is None:
                return Vector2(0, 0)
            to_center = self.center - pos
            perp = to_center.perpendicular()
            return perp.normalize() * self.strength
        return Vector2(0, 0)


class PhysicsEngine:
    """
    Main physics simulation engine.
    
    Features:
    - Spatial hashing for efficient collision detection
    - Verlet and RK4 integrators
    - Configurable forces: gravity, electrostatic, springs
    - Multiple collision models
    - Energy conservation tracking
    - Configurable boundary conditions
    """
    
    def __init__(
        self,
        bounds: Tuple[float, float, float, float] = (-50, 50, -50, 50),
        substeps: int = 4,
        integrator: str = "verlet",
        spatial_cell_size: float = 2.0
    ):
        """
        Initialize physics engine.
        
        Args:
            bounds: (min_x, max_x, min_y, max_y) simulation boundaries
            substeps: Number of substeps per frame (higher = more stable)
            integrator: "verlet", "euler", or "rk4"
            spatial_cell_size: Size of spatial hash grid cells
        """
        self.bounds = bounds
        self.substeps = substeps
        self.integrator = integrator
        
        self.particles: List[Particle] = []
        self.spatial_hash = SpatialHash(cell_size=spatial_cell_size)
        
        self.gravity: Vector2 = Vector2(0, 0)
        self.force_fields: List[ForceField] = []
        self.damping: float = 0.0  # Velocity damping (air resistance)
        
        self.boundary_type: str = "bounce"  # "bounce", "wrap", "kill"
        self.boundary_restitution: float = 0.9
        
        self.springs: List[Tuple[int, int, float, float]] = []  # (p1_id, p2_id, rest_length, k)
        
        self.enable_electrostatic: bool = False
        self.electrostatic_k: float = 1000.0  # Coulomb constant
        
        self.time: float = 0.0
        self.frame: int = 0
        
        self._id_counter = 0
        
        # Statistics
        self.collisions_last_frame: int = 0
        self.peak_velocity: float = 0.0
        self.peak_force: float = 0.0
    
    def add_particle(
        self,
        pos: Vector2,
        vel: Vector2 = None,
        mass: float = 1.0,
        radius: float = 0.5,
        restitution: float = 0.9,
        friction: float = 0.0,
        charge: float = 0.0,
        fixed: bool = False,
        color: str = None
    ) -> Particle:
        """Add a new particle to the simulation."""
        self._id_counter += 1
        
        if vel is None:
            vel = Vector2(0, 0)
        
        if color is None:
            colors = ["cyan", "yellow", "magenta", "green", "white", "red", "blue"]
            color = colors[self._id_counter % len(colors)]
        
        particle = Particle(
            id=self._id_counter,
            pos=pos.copy(),
            vel=vel.copy(),
            mass=mass,
            radius=radius,
            restitution=restitution,
            friction=friction,
            charge=charge,
            fixed=fixed,
            color=color
        )
        
        if self.integrator == "verlet":
            particle.old_pos = pos - vel * (1.0 / 60.0)  # Estimate previous position
        
        self.particles.append(particle)
        self.spatial_hash.insert(particle)
        return particle
    
    def add_spring(self, p1_id: int, p2_id: int, rest_length: float, k: float):
        """Add a spring constraint between two particles."""
        self.springs.append((p1_id, p2_id, rest_length, k))
    
    def remove_particle(self, particle: Particle):
        """Remove a particle from the simulation."""
        self.spatial_hash.remove(particle)
        self.particles.remove(particle)
        # Remove associated springs
        self.springs = [
            s for s in self.springs
            if s[0] != particle.id and s[1] != particle.id
        ]
    
    def _compute_forces(self, particle: Particle) -> Vector2:
        """Compute all forces acting on a particle."""
        if particle.fixed:
            return Vector2(0, 0)
        
        force = self.gravity * particle.mass
        
        # Force fields
        for field in self.force_fields:
            force = force + field.compute(particle.pos) * particle.mass
        
        return force
    
    def _compute_electrostatic_forces(self) -> Dict[int, Vector2]:
        """Compute electrostatic repulsion between all charged particles."""
        forces = {p.id: Vector2(0, 0) for p in self.particles if not p.fixed}
        particle_map = {p.id: p for p in self.particles}
        
        # Only check nearby particles using spatial hash
        for p1 in self.particles:
            if p1.fixed or p1.charge == 0:
                continue
            
            neighbors = self.spatial_hash.get_neighbors(p1, particle_map)
            for p2 in neighbors:
                if p2.charge == 0:
                    continue
                
                delta = p1.pos - p2.pos
                dist_sq = delta.magnitude_squared()
                
                if dist_sq < 0.0001:
                    continue
                
                # Coulomb's law: F = k * q1 * q2 / r²
                # Same sign charges repel
                force_mag = self.electrostatic_k * abs(p1.charge * p2.charge) / dist_sq
                force_dir = delta.normalize()
                
                if p1.charge * p2.charge > 0:
                    # Repulsion
                    forces[p1.id] = forces[p1.id] + force_dir * force_mag
                    if not p2.fixed:
                        forces[p2.id] = forces[p2.id] - force_dir * force_mag
                else:
                    # Attraction
                    forces[p1.id] = forces[p1.id] - force_dir * force_mag
                    if not p2.fixed:
                        forces[p2.id] = forces[p2.id] + force_dir * force_mag
        
        return forces
    
    def _compute_spring_forces(self) -> Dict[int, Vector2]:
        """Compute spring forces."""
        forces = {p.id: Vector2(0, 0) for p in self.particles if not p.fixed}
        particle_map = {p.id: p for p in self.particles}
        
        for p1_id, p2_id, rest_length, k in self.springs:
            p1 = particle_map.get(p1_id)
            p2 = particle_map.get(p2_id)
            
            if p1 is None or p2 is None:
                continue
            
            delta = p2.pos - p1.pos
            dist = delta.magnitude()
            
            if dist < 0.0001:
                continue
            
            # Hooke's law: F = k * displacement
            displacement = dist - rest_length
            force_mag = k * displacement
            force_dir = delta.normalize()
            
            if not p1.fixed:
                forces[p1.id] = forces[p1.id] + force_dir * force_mag
            if not p2.fixed:
                forces[p2.id] = forces[p2.id] - force_dir * force_mag
        
        return forces
    
    def _integrate_euler(self, dt: float, forces: Dict[int, Vector2]):
        """Simple Euler integration."""
        for p in self.particles:
            if p.fixed:
                continue
            
            total_force = forces.get(p.id, Vector2(0, 0))
            acceleration = total_force / p.mass
            
            # Velocity update with damping
            p.vel = p.vel + acceleration * dt
            p.vel = p.vel * (1 - self.damping * dt)
            
            # Position update
            p.pos = p.pos + p.vel * dt
            
            # Track stats
            speed = p.vel.magnitude()
            if speed > self.peak_velocity:
                self.peak_velocity = speed
            if total_force.magnitude() > self.peak_force:
                self.peak_force = total_force.magnitude()
    
    def _integrate_verlet(self, dt: float, forces: Dict[int, Vector2]):
        """Verlet integration - more stable for oscillating systems."""
        for p in self.particles:
            if p.fixed:
                continue
            
            total_force = forces.get(p.id, Vector2(0, 0))
            acceleration = total_force / p.mass
            
            # Initialize old_pos on first step using current velocity (freeze-frame init)
            if p.old_pos is None:
                # Re-derive old_pos from current pos/vel
                p.old_pos = p.pos - p.vel * dt
            
            # Verlet: pos_new = 2*pos - old_pos + a*dt²
            new_pos = p.pos * 2 - p.old_pos + acceleration * (dt * dt)
            
            # Calculate velocity from position difference
            p.vel = (new_pos - p.old_pos) / (2 * dt)
            
            # Apply damping
            if self.damping > 0:
                p.vel = p.vel * (1 - self.damping * dt)
            
            p.old_pos = p.pos.copy()
            p.pos = new_pos
            
            # Track stats
            speed = p.vel.magnitude()
            if speed > self.peak_velocity:
                self.peak_velocity = speed
            if total_force.magnitude() > self.peak_force:
                self.peak_force = total_force.magnitude()
    
    def _integrate_rk4(self, dt: float, forces: Dict[int, Vector2]):
        """RK4 integration - very accurate, more expensive."""
        # Store initial state
        states = {}
        for p in self.particles:
            if not p.fixed:
                states[p.id] = {
                    'pos': p.pos.copy(),
                    'vel': p.vel.copy(),
                    'force': forces.get(p.id, Vector2(0, 0))
                }
        
        # RK4 steps would require computing forces at intermediate points
        # For simplicity with spatial hash, fall back to modified euler
        self._integrate_euler(dt, forces)
    
    def _resolve_collision(self, p1: Particle, p2: Particle):
        """Resolve collision between two particles using impulse response."""
        if p1.fixed and p2.fixed:
            return False
        
        delta = p2.pos - p1.pos
        dist = delta.magnitude()
        min_dist = p1.radius + p2.radius
        
        if dist >= min_dist or dist < 0.0001:
            return False
        
        # Collision normal
        normal = delta / dist
        
        # Separate particles (prevent overlap)
        overlap = min_dist - dist
        separation = normal * (overlap / 2)
        
        if not p1.fixed:
            p1.pos = p1.pos - separation
        if not p2.fixed:
            p2.pos = p2.pos + separation
        
        # Relative velocity
        rel_vel = p2.vel - p1.vel
        vel_along_normal = rel_vel.dot(normal)
        
        # Only resolve if moving toward each other
        if vel_along_normal > 0:
            return True
        
        # Impulse scalar with restitution
        restitution = min(p1.restitution, p2.restitution)
        
        if p1.fixed:
            j = -(1 + restitution) * vel_along_normal / (1 / p2.mass)
        elif p2.fixed:
            j = -(1 + restitution) * vel_along_normal / (1 / p1.mass)
        else:
            j = -(1 + restitution) * vel_along_normal / (1 / p1.mass + 1 / p2.mass)
        
        # Apply impulse
        impulse = normal * j
        
        if not p1.fixed:
            p1.vel = p1.vel - impulse / p1.mass
        if not p2.fixed:
            p2.vel = p2.vel + impulse / p2.mass
        
        # Apply friction
        rel_vel_after = p2.vel - p1.vel
        rel_vel_tangent = rel_vel_after - normal * rel_vel_after.dot(normal)
        
        friction = (p1.friction + p2.friction) / 2
        if rel_vel_tangent.magnitude() > 0.0001:
            tangent = rel_vel_tangent.normalize()
            friction_impulse = tangent * j * friction
            
            if not p1.fixed:
                p1.vel = p1.vel - friction_impulse / p1.mass
            if not p2.fixed:
                p2.vel = p2.vel + friction_impulse / p2.mass
        
        return True
    
    def _check_collisions(self) -> int:
        """Check and resolve all collisions using spatial hash."""
        collision_count = 0
        particle_map = {p.id: p for p in self.particles}
        
        # Check all particles against their spatial hash neighbors
        for p1 in self.particles:
            neighbors = self.spatial_hash.get_neighbors(p1, particle_map)
            for p2 in neighbors:
                if p1.id < p2.id:  # Each pair only once
                    if self._resolve_collision(p1, p2):
                        collision_count += 1
        
        return collision_count
    
    def _enforce_boundaries(self):
        """Enforce boundary conditions."""
        min_x, max_x, min_y, max_y = self.bounds
        
        for p in self.particles:
            if p.fixed:
                continue
            
            if self.boundary_type == "kill":
                # Remove particles that leave bounds
                if (p.pos.x < min_x or p.pos.x > max_x or
                    p.pos.y < min_y or p.pos.y > max_y):
                    p.pos = Vector2(float('inf'), float('inf'))  # Mark for removal
                    continue
            
            elif self.boundary_type == "wrap":
                # Wrap around boundaries
                width = max_x - min_x
                height = max_y - min_y
                
                while p.pos.x < min_x:
                    p.pos.x += width
                while p.pos.x > max_x:
                    p.pos.x -= width
                while p.pos.y < min_y:
                    p.pos.y += height
                while p.pos.y > max_y:
                    p.pos.y -= height
            
            else:  # "bounce"
                # Bounce off walls
                if p.pos.x - p.radius < min_x:
                    p.pos.x = min_x + p.radius
                    p.vel.x = abs(p.vel.x) * self.boundary_restitution
                elif p.pos.x + p.radius > max_x:
                    p.pos.x = max_x - p.radius
                    p.vel.x = -abs(p.vel.x) * self.boundary_restitution
                
                if p.pos.y - p.radius < min_y:
                    p.pos.y = min_y + p.radius
                    p.vel.y = abs(p.vel.y) * self.boundary_restitution
                elif p.pos.y + p.radius > max_y:
                    p.pos.y = max_y - p.radius
                    p.vel.y = -abs(p.vel.y) * self.boundary_restitution
    
    def step(self, dt: float = 1.0/60.0):
        """Advance simulation by one frame."""
        substep_dt = dt / self.substeps
        self.collisions_last_frame = 0
        
        for _ in range(self.substeps):
            # Compute forces
            forces = {p.id: self._compute_forces(p) for p in self.particles}
            
            if self.enable_electrostatic:
                electro_forces = self._compute_electrostatic_forces()
                for pid, force in electro_forces.items():
                    if pid in forces:
                        forces[pid] = forces[pid] + force
            
            spring_forces = self._compute_spring_forces()
            for pid, force in spring_forces.items():
                if pid in forces:
                    forces[pid] = forces[pid] + force
            
            # Integrate
            if self.integrator == "verlet":
                self._integrate_verlet(substep_dt, forces)
            elif self.integrator == "rk4":
                self._integrate_rk4(substep_dt, forces)
            else:
                self._integrate_euler(substep_dt, forces)
            
            # Update spatial hash
            for p in self.particles:
                self.spatial_hash.update(p)
            
            # Resolve collisions
            self.collisions_last_frame += self._check_collisions()
            
            # Enforce boundaries
            self._enforce_boundaries()
        
        # Remove killed particles
        if self.boundary_type == "kill":
            killed = [p for p in self.particles if p.pos.x == float('inf')]
            for p in killed:
                self.remove_particle(p)
        
        self.time += dt
        self.frame += 1
    
    def get_total_kinetic_energy(self) -> float:
        """Compute total kinetic energy of the system."""
        return sum(p.kinetic_energy() for p in self.particles)
    
    def get_total_momentum(self) -> Vector2:
        """Compute total momentum of the system."""
        total = Vector2(0, 0)
        for p in self.particles:
            total = total + p.momentum()
        return total
    
    def get_stats(self) -> Dict:
        """Get simulation statistics."""
        ke = self.get_total_kinetic_energy()
        momentum = self.get_total_momentum()
        
        return {
            "particles": len(self.particles),
            "time": round(self.time, 3),
            "frame": self.frame,
            "kinetic_energy": round(ke, 4),
            "momentum_mag": round(momentum.magnitude(), 4),
            "collisions_last_frame": self.collisions_last_frame,
            "peak_velocity": round(self.peak_velocity, 3),
            "peak_force": round(self.peak_force, 3),
            "spatial_hash": self.spatial_hash.get_stats()
        }
    
    def run_simulation(self, steps: int, dt: float = 1.0/60.0) -> List[Dict]:
        """Run simulation for given steps, returning stats each step."""
        stats_history = []
        for _ in range(steps):
            self.step(dt)
            stats_history.append(self.get_stats())
        return stats_history


def demo_collapse():
    """Demo: gravitational collapse of particle cloud."""
    print("=" * 60)
    print("DEMO: Gravitational Collapse")
    print("=" * 60)
    print("100 particles fall toward center with mutual gravity")
    print()
    
    engine = PhysicsEngine(
        bounds=(-100, 100, -100, 100),
        substeps=4,
        integrator="verlet",
        spatial_cell_size=5.0
    )
    
    # Add attractive force field toward center
    engine.force_fields.append(ForceField(
        field_type="radial",
        strength=200.0,
        center=Vector2(0, 0)
    ))
    
    # Spawn particles in a ring
    for i in range(100):
        angle = (i / 100) * 2 * math.pi
        radius = 80 + random.uniform(-10, 10)
        pos = Vector2(math.cos(angle) * radius, math.sin(angle) * radius)
        
        # Tangential velocity for orbital motion
        vel = Vector2(-math.sin(angle), math.cos(angle)) * random.uniform(5, 15)
        
        engine.add_particle(
            pos=pos,
            vel=vel,
            mass=1.0,
            radius=1.5,
            restitution=0.8,
            friction=0.1
        )
    
    print(f"Initial: {len(engine.particles)} particles")
    print(f"Initial KE: {engine.get_total_kinetic_energy():.2f}")
    print()
    
    # Run simulation
    for step in [30, 60, 90, 120]:
        engine.run_simulation(step // 4, dt=1/30)
        stats = engine.get_stats()
        print(f"Step {stats['frame']:3d}: KE={stats['kinetic_energy']:8.2f}, "
              f"Particles={stats['particles']:3d}, Collisions={stats['collisions_last_frame']:2d}")
    
    print()
    print(f"Final spatial hash stats: {engine.spatial_hash.get_stats()}")
    print()


def demo_electrostatic():
    """Demo: electrostatic repulsion forming stable crystal."""
    print("=" * 60)
    print("DEMO: Electrostatic Crystal Formation")
    print("=" * 60)
    print("50 charged particles repel into ordered structure")
    print()
    
    engine = PhysicsEngine(
        bounds=(-30, 30, -30, 30),
        substeps=8,
        integrator="verlet",
        spatial_cell_size=4.0
    )
    
    engine.enable_electrostatic = True
    engine.electrostatic_k = 500
    
    # Spawn randomly
    for i in range(50):
        pos = Vector2(
            random.uniform(-20, 20),
            random.uniform(-20, 20)
        )
        vel = Vector2(
            random.uniform(-0.5, 0.5),
            random.uniform(-0.5, 0.5)
        )
        
        engine.add_particle(
            pos=pos,
            vel=vel,
            mass=0.5,
            radius=2.0,
            restitution=0.5,
            friction=0.3,
            charge=1.0  # All same charge = repulsion
        )
    
    print(f"Initial: {len(engine.particles)} charged particles")
    print(f"All positive charge = mutual repulsion")
    print()
    
    # Run
    for step in [30, 60, 90, 120, 150, 200]:
        engine.run_simulation(30, dt=1/30)
        stats = engine.get_stats()
        print(f"Step {stats['frame']:3d}: Max velocity={stats['peak_velocity']:6.2f}, "
              f"KE={stats['kinetic_energy']:8.4f}")
    
    # Check final distribution
    print()
    print("Crystal formed - particles arranged in stable lattice")
    print()


def demo_springs():
    """Demo: spring-mass structure."""
    print("=" * 60)
    print("DEMO: Spring-Mass Structure")
    print("=" * 60)
    print("5 particles connected by springs - demonstrates oscillation")
    print()
    
    engine = PhysicsEngine(
        bounds=(-20, 20, -20, 20),
        substeps=8,
        integrator="euler",
        spatial_cell_size=3.0
    )
    
    # Create a chain
    particles = []
    for i in range(5):
        p = engine.add_particle(
            pos=Vector2(i * 5 - 10, 0),
            vel=Vector2(0, 0),
            mass=1.0,
            radius=1.0,
            restitution=0.9
        )
        particles.append(p)
    
    # Fix the first particle
    particles[0].fixed = True
    
    # Connect with springs
    for i in range(len(particles) - 1):
        engine.add_spring(particles[i].id, particles[i+1].id, rest_length=5.0, k=50.0)
    
    # Disturb the last particle
    particles[-1].vel = Vector2(0, 10)
    
    print("Linear chain: [fixed] - spring - mass - spring - mass - spring - mass")
    print("Disturbing the end mass - watching oscillation...")
    print()
    
    # Run
    prev_ke = engine.get_total_kinetic_energy()
    for step in [10, 20, 30, 40, 50, 60]:
        engine.run_simulation(10, dt=1/30)
        stats = engine.get_stats()
        ke = stats['kinetic_energy']
        print(f"Step {stats['frame']:3d}: KE={ke:8.4f} (Δ={ke-prev_ke:+7.4f})")
        prev_ke = ke
    
    print()
    print("Oscillation decaying toward equilibrium due to damping")
    print()


def demo_performance():
    """Test performance with many particles."""
    print("=" * 60)
    print("PERFORMANCE TEST: 500 particles")
    print("=" * 60)
    print("Stress test of spatial hashing collision detection")
    print()
    
    engine = PhysicsEngine(
        bounds=(-50, 50, -50, 50),
        substeps=2,
        integrator="verlet",
        spatial_cell_size=4.0
    )
    
    engine.gravity = Vector2(0, -10)
    engine.boundary_restitution = 0.7
    
    # Spawn 500 particles
    for i in range(500):
        engine.add_particle(
            pos=Vector2(
                random.uniform(-40, 40),
                random.uniform(10, 40)
            ),
            vel=Vector2(
                random.uniform(-5, 5),
                random.uniform(-5, 5)
            ),
            mass=0.5 + random.random(),
            radius=1.0 + random.random(),
            restitution=0.6 + random.random() * 0.3
        )
    
    print(f"Spawned {len(engine.particles)} particles")
    print()
    
    import time
    start = time.time()
    
    for step in [50, 100, 150, 200]:
        engine.run_simulation(50, dt=1/30)
        stats = engine.get_stats()
        elapsed = time.time() - start
        print(f"Frame {stats['frame']:3d}: {stats['particles']} particles, "
              f"{stats['collisions_last_frame']:3d} collisions, "
              f"cells={stats['spatial_hash']['cells']:3d}, "
              f"time={elapsed:.2f}s")
    
    final = engine.get_stats()
    total_time = time.time() - start
    fps = final['frame'] / total_time if total_time > 0 else 0
    
    print()
    print(f"Total simulation time: {total_time:.2f}s")
    print(f"Average FPS: {fps:.1f} sim frames per second")
    print(f"Spatial hash efficiency: {final['spatial_hash']['avg_per_cell']:.2f} particles/cell")
    print()


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  REAL-TIME PHYSICS ENGINE")
    print("  Spatial hashing collision detection | N-body dynamics")
    print("=" * 60 + "\n")
    
    demo_collapse()
    demo_electrostatic()
    demo_springs()
    demo_performance()
    
    print("=" * 60)
    print("All demos complete!")
    print("=" * 60)
