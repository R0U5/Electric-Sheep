#!/usr/bin/env python3
"""
Simple ray tracer – renders a scene of spheres and a plane to a PPM image.
Usage:
  python ray_tracer.py [mode]
Modes:
  (no arg) – default scene with two spheres and a plane.
  extra    – adds a third sphere to the default scene.
  none     – renders only the background gradient (no objects).
The script prints the path of the generated image.
"""
import sys
import math

# Vector utilities
class Vec3:
    __slots__ = ('x', 'y', 'z')
    def __init__(self, x: float, y: float, z: float):
        self.x = x
        self.y = y
        self.z = z
    def __add__(self, other):
        return Vec3(self.x + other.x, self.y + other.y, self.z + other.z)
    def __sub__(self, other):
        return Vec3(self.x - other.x, self.y - other.y, self.z - other.z)
    def __mul__(self, other: float):
        return Vec3(self.x * other, self.y * other, self.z * other)
    __rmul__ = __mul__
    def __truediv__(self, other: float):
        return Vec3(self.x / other, self.y / other, self.z / other)
    def dot(self, other) -> float:
        return self.x * other.x + self.y * other.y + self.z * other.z
    def length(self) -> float:
        return math.sqrt(self.dot(self))
    def normalize(self):
        l = self.length()
        if l == 0:
            return self
        return self / l
    def __repr__(self):
        return f"Vec3({self.x}, {self.y}, {self.z})"

# Ray definition
class Ray:
    __slots__ = ('origin', 'direction')
    def __init__(self, origin: Vec3, direction: Vec3):
        self.origin = origin
        self.direction = direction.normalize()

# Primitive objects
class Sphere:
    __slots__ = ('center', 'radius', 'color')
    def __init__(self, center: Vec3, radius: float, color: Vec3):
        self.center = center
        self.radius = radius
        self.color = color
    def intersect(self, ray: Ray):
        oc = ray.origin - self.center
        a = ray.direction.dot(ray.direction)
        b = 2.0 * oc.dot(ray.direction)
        c = oc.dot(oc) - self.radius * self.radius
        discriminant = b * b - 4 * a * c
        if discriminant < 0:
            return None
        sqrt_disc = math.sqrt(discriminant)
        t1 = (-b - sqrt_disc) / (2 * a)
        t2 = (-b + sqrt_disc) / (2 * a)
        t = t1 if t1 > 1e-4 else (t2 if t2 > 1e-4 else None)
        if t is None:
            return None
        hit_point = ray.origin + ray.direction * t
        normal = (hit_point - self.center).normalize()
        return (t, hit_point, normal, self.color)

class Plane:
    __slots__ = ('point', 'normal', 'color')
    def __init__(self, point: Vec3, normal: Vec3, color: Vec3):
        self.point = point
        self.normal = normal.normalize()
        self.color = color
    def intersect(self, ray: Ray):
        denom = self.normal.dot(ray.direction)
        if abs(denom) < 1e-6:
            return None
        t = (self.point - ray.origin).dot(self.normal) / denom
        if t < 1e-4:
            return None
        hit_point = ray.origin + ray.direction * t
        return (t, hit_point, self.normal, self.color)

# Scene setup helper
def build_scene(mode: str):
    objects = []
    # Add a ground plane
    objects.append(Plane(point=Vec3(0, -1, 0), normal=Vec3(0, 1, 0), color=Vec3(0.8, 0.8, 0.8)))
    # Default spheres
    objects.append(Sphere(center=Vec3(0, 0, -5), radius=1.0, color=Vec3(1.0, 0.0, 0.0)))  # red
    objects.append(Sphere(center=Vec3(2, 0, -6), radius=1.0, color=Vec3(0.0, 1.0, 0.0)))  # green
    if mode == 'extra':
        objects.append(Sphere(center=Vec3(-2, 0, -4), radius=1.0, color=Vec3(0.0, 0.0, 1.0)))  # blue
    elif mode == 'none':
        # keep only plane (or even remove plane) – show pure background
        objects = []
    return objects

# Simple diffuse shading with a single directional light
LIGHT_DIR = Vec3(-1, -1, -1).normalize()
BACKGROUND_COLOR_TOP = Vec3(0.5, 0.7, 1.0)  # light blue
BACKGROUND_COLOR_BOTTOM = Vec3(1.0, 1.0, 1.0)  # white

def shade(hit_normal: Vec3, object_color: Vec3) -> Vec3:
    diff = max(0.0, hit_normal.dot(-LIGHT_DIR))
    # Simple ambient term
    ambient = 0.1
    return (object_color * (ambient + diff))


def render(width=200, height=200, fov=90, mode=''):
    aspect_ratio = width / height
    angle = math.tan(math.radians(fov) / 2)
    camera_origin = Vec3(0, 0, 0)

    objects = build_scene(mode)

    pixels = []
    for j in range(height):
        row = []
        y = 1 - 2 * (j + 0.5) / height  # NDC Y
        for i in range(width):
            x = (2 * (i + 0.5) / width - 1) * angle * aspect_ratio
            direction = Vec3(x, y, -1).normalize()
            ray = Ray(camera_origin, direction)
            color = None
            nearest_t = float('inf')
            hit_info = None
            for obj in objects:
                result = obj.intersect(ray)
                if result:
                    t, hp, normal, obj_color = result
                    if t < nearest_t:
                        nearest_t = t
                        hit_info = (normal, obj_color)
            if hit_info:
                normal, obj_color = hit_info
                shaded = shade(normal, obj_color)
                color = shaded
            else:
                # Background gradient based on ray y direction
                t = 0.5 * (direction.y + 1.0)
                color = BACKGROUND_COLOR_BOTTOM * (1 - t) + BACKGROUND_COLOR_TOP * t
            # Clamp and convert to 0-255
            r = int(255 * max(0, min(1, color.x)))
            g = int(255 * max(0, min(1, color.y)))
            b = int(255 * max(0, min(1, color.z)))
            row.append(f"{r} {g} {b}")
        pixels.append(' '.join(row))
    return '\n'.join(pixels)


def main():
    mode = ''
    if len(sys.argv) > 1:
        mode = sys.argv[1]
    width, height = 200, 200
    img_data = render(width, height, mode=mode)
    out_path = f"output_{mode or 'default'}.ppm"
    with open(out_path, 'w') as f:
        f.write(f"P3\n{width} {height}\n255\n")
        f.write(img_data)
        f.write('\n')
    print(f"Rendered {out_path}")

if __name__ == '__main__':
    main()
