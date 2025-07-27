import pygame
import random
import math
import sys
import numpy as np
from scipy.spatial import ConvexHull
from scipy.spatial.transform import Rotation as R
import noise # Import the noise library

import os

# --- Asset Path ---
ASSET_PATH = "assets"

# --- Configuration for Asteroid Generation ---
NUM_POINTS = 500 # Increased for better 3D shape and detail

# --- Color Configuration ---
ASTEROID_COLORS = {
    "purple": (128, 0, 128),
    "red": (255, 0, 0),
    "brown": (139, 69, 19),
    "green": (0, 255, 0),
    "white": (255, 255, 255)
}

# --- Size Adjustment Configuration ---
MIN_OUTER_RADIUS = 20
MAX_OUTER_RADIUS = 150

# --- Jaggedness Configuration (Radial Jitter) ---
# This will now represent jitter in the radius of the 3D sphere points
MIN_SIZE_FOR_JITTER = 20
MAX_SIZE_FOR_JITTER = 150
BASE_JITTER = 0.1 # Adjusted for 3D
MAX_JITTER = 0.4  # Adjusted for 3D

# --- Radial Variance (Inner/Outer Gap) Configuration based on Size ---
MIN_SIZE_FOR_VARIANCE_CHANGE = 20
MAX_SIZE_FOR_VARIANCE_CHANGE = 150
MIN_RADIAL_VARIANCE = 10
MAX_RADIAL_VARIANCE = 50


# --- Function to generate the asteroid's *core 3D data* (vertices and faces) ---
def generate_asteroid_core_data(inner_radius, outer_radius, jitter_val, jaggedness_factor=1.0, shape_randomization_factor=(1.0, 1.0, 1.0), displacement_strength=0.0, indentation_scale=0.0, indentation_shape_factor=(1.0, 1.0, 1.0)):
    """
    Generates the 3D vertices and faces for a new asteroid using a convex hull.
    """
    if inner_radius >= outer_radius:
        inner_radius = outer_radius - 1
        if inner_radius < 1: inner_radius = 1

    points = []
    for i in range(NUM_POINTS):
        # Generate points on a sphere using spherical coordinates
        theta = math.acos(1 - 2 * (i + 0.5) / NUM_POINTS) # Latitude
        phi = math.pi * (1 + math.sqrt(5)) * i # Longitude

        # Add random jitter to the radius, amplified by jaggedness_factor
        # Ensure jitter_val is applied as a deviation from the base radius
        base_radius = random.uniform(inner_radius, outer_radius)
        jitter_amount = random.uniform(-jitter_val, jitter_val) * jaggedness_factor
        radius = base_radius + jitter_amount

        # Ensure radius remains positive
        if radius <= 0:
            radius = 0.1 # Small positive value to avoid issues
        
        # Convert spherical to cartesian coordinates
        x = radius * math.sin(theta) * math.cos(phi)
        y = radius * math.sin(theta) * math.sin(phi)
        z = radius * math.cos(theta)

        # Apply noise for displacement (indents or bumps)
        if displacement_strength != 0 and indentation_scale > 0:
            # Scale the coordinates for the noise function
            nx = x * indentation_scale * indentation_shape_factor[0]
            ny = y * indentation_scale * indentation_shape_factor[1]
            nz = z * indentation_scale * indentation_shape_factor[2]

            # Generate 3D Perlin noise
            displacement = noise.pnoise3(nx, ny, nz, octaves=8, persistence=0.7, lacunarity=2.5, repeatx=1024, repeaty=1024, repeatz=1024, base=0)

            # Apply displacement to the radius
            radius += displacement * displacement_strength

            # Recalculate x, y, z with the new radius
            x = radius * math.sin(theta) * math.cos(phi) * shape_randomization_factor[0]
            y = radius * math.sin(theta) * math.sin(phi) * shape_randomization_factor[1]
            z = radius * math.cos(theta) * shape_randomization_factor[2]

        points.append([x, y, z])

    points = np.array(points)
    
    # Create the convex hull from the points
    hull = ConvexHull(points)

    # The vertices of the hull are the final 3D points of our asteroid
    vertices = hull.points
    # The simplices are the triangular faces, defined by indices into the vertices array
    faces = hull.simplices

    return vertices, faces


# --- Functions to calculate dynamic properties based on size ---
def calculate_dynamic_property(outer_radius, min_size, max_size, min_value, max_value, invert=False):
    """Helper function to calculate a dynamic property based on the asteroid's size."""
    # Clamp the radius to the min/max size range
    clamped_radius = max(min_size, min(outer_radius, max_size))
    # Normalize the progress from 0.0 to 1.0
    normalized_progress = (clamped_radius - min_size) / (max_size - min_size)
    
    if invert:
        normalized_progress = 1.0 - normalized_progress
        
    # Linearly interpolate the value
    return min_value + (max_value - min_value) * normalized_progress

def get_jitter_for_size(outer_radius):
    """Calculates the radial jitter based on outer_radius."""
    return calculate_dynamic_property(outer_radius, MIN_SIZE_FOR_JITTER, MAX_SIZE_FOR_JITTER, BASE_JITTER, MAX_JITTER)

def get_radial_variance_for_size(outer_radius):
    """Calculates the difference between outer_radius and inner_radius."""
    return int(round(calculate_dynamic_property(outer_radius, MIN_SIZE_FOR_VARIANCE_CHANGE, MAX_SIZE_FOR_VARIANCE_CHANGE, MIN_RADIAL_VARIANCE, MAX_RADIAL_VARIANCE)))

def generate_uv_coordinates(vertices):
    """Generates spherical UV coordinates for a set of vertices."""
    uvs = []
    for vertex in vertices:
        x, y, z = vertex
        # Normalize the vertex to get a point on the unit sphere
        length = np.linalg.norm(vertex)
        if length == 0: # Avoid division by zero
            uvs.append((0.5, 0.5))
            continue
        unit_vertex = vertex / length
        
        # Spherical coordinates to UV mapping
        # atan2(z, x) gives the angle in the xz-plane (longitude)
        # acos(y) gives the angle from the y-axis (latitude)
        u = (np.arctan2(unit_vertex[2], unit_vertex[0]) / (2 * np.pi)) + 0.5
        v = (np.arcsin(unit_vertex[1]) / np.pi) + 0.5
        uvs.append((u, v))
    return np.array(uvs)



# --- Asteroid3D Class ---
class Asteroid3D:
    def __init__(self, initial_x, initial_y, initial_z, asteroid_type=None, new_outer_radius=None, jaggedness_factor=None, shape_randomization_factor=None, displacement_strength=None, indentation_scale=None, indentation_shape_factor=None, randomize_all=False, is_satellite=False, orbit_distance=0, orbit_speed=0, orbit_parent_position=None, texture_id=None, satellite_size_range=(5, 20), nested_satellite_proportion=0.05):
        self.position = np.array([initial_x, initial_y, initial_z], dtype=float)

        self.outer_radius = 0
        self.inner_radius = 0
        self.jitter = 0.0
        self.jaggedness_factor = 1.0 # New attribute
        self.shape_randomization_factor = (1.0, 1.0, 1.0) # New attribute for non-spherical shapes
        self.displacement_strength = 0.0 # New attribute for displacement depth/height
        self.indentation_scale = 0.0 # New attribute for indentation size/frequency
        self.indentation_shape_factor = (1.0, 1.0, 1.0) # New attribute for indentation ovalness

        self.color_key = ""
        
        # Store the base, unrotated vertices and faces
        self.base_vertices = np.array([])
        self.faces = np.array([])
        self.uv_coords = np.array([]) # Add UV coordinates

        # 3D Rotation attributes
        self.rotation = R.from_euler('xyz', [0, 0, 0], degrees=True) # Initial rotation
        self.rotation_speed = np.random.uniform(-1, 1, 3) # Random axis and speed

        self.satellites = [] # List to hold satellite objects

        # Orbital attributes for satellites
        self.is_satellite = is_satellite
        self.orbit_distance = orbit_distance
        self.orbit_angle = random.uniform(0, 2 * math.pi) # Initial random angle
        self.orbit_speed = orbit_speed
        self.orbit_parent_position = orbit_parent_position if orbit_parent_position is not None else np.array([0.0, 0.0, 0.0])

        self.texture_id = texture_id # Store the texture ID
        self.satellite_size_range = satellite_size_range # Store the satellite size range
        self.nested_satellite_proportion = nested_satellite_proportion # Store nested satellite proportion

        self.recreate_asteroid(
            new_outer_radius=new_outer_radius,
            asteroid_type=asteroid_type,
            randomize_all=randomize_all or (new_outer_radius is None and asteroid_type is None),
            satellite_size_range=satellite_size_range
        )

    def recreate_asteroid(self, new_outer_radius=None, asteroid_type=None, randomize_all=False, jaggedness_factor=None, shape_randomization_factor=None, displacement_strength=None, indentation_scale=None, indentation_shape_factor=None, satellite_size_range=None, nested_satellite_proportion=None):
        if new_outer_radius is not None:
            self.outer_radius = new_outer_radius # Prioritize explicit radius
        elif randomize_all:
            self.outer_radius = random.randint(MIN_OUTER_RADIUS, MAX_OUTER_RADIUS)
        # Ensure outer_radius is within bounds after setting
        self.outer_radius = max(MIN_OUTER_RADIUS, min(self.outer_radius, MAX_OUTER_RADIUS))

        if jaggedness_factor is not None:
            self.jaggedness_factor = jaggedness_factor
        elif randomize_all:
            # Randomly assign a jaggedness factor
            self.jaggedness_factor = random.choice([1.0, 1.0, 1.0, 1.5, 2.0]) # More likely to be less jagged

        if shape_randomization_factor is not None:
            self.shape_randomization_factor = shape_randomization_factor
        elif randomize_all:
            # Randomize shape factors for x, y, z to make it more oval
            self.shape_randomization_factor = (
                random.uniform(0.7, 1.3),
                random.uniform(0.7, 1.3),
                random.uniform(0.7, 1.3)
            )

        if displacement_strength is not None:
            self.displacement_strength = displacement_strength
        elif randomize_all:
            self.displacement_strength = random.uniform(-10.0, 10.0) # Random displacement depth/height (can be negative for indents, positive for bumps)

        if indentation_scale is not None:
            self.indentation_scale = indentation_scale
        elif randomize_all:
            self.indentation_scale = random.uniform(0.05, 0.3) # Adjusted range for new noise parameters

        if indentation_shape_factor is not None:
            self.indentation_shape_factor = indentation_shape_factor
        elif randomize_all:
            self.indentation_shape_factor = (
                random.uniform(0.5, 1.5),
                random.uniform(0.5, 1.5),
                random.uniform(0.5, 1.5)
            )

        self.radial_variance = get_radial_variance_for_size(self.outer_radius)
        self.inner_radius = self.outer_radius - self.radial_variance
        if self.inner_radius < 10: self.inner_radius = 10
        self.jitter = get_jitter_for_size(self.outer_radius)

        if asteroid_type is not None:
            self.color_key = asteroid_type
        elif randomize_all:
            self.color_key = random.choice(list(ASTEROID_COLORS.keys()))

        if self.color_key not in ASTEROID_COLORS:
            self.color_key = 'brown'

        # Generate the 3D data, passing all relevant factors
        self.base_vertices, self.faces = generate_asteroid_core_data(
            self.inner_radius, self.outer_radius, self.jitter, self.jaggedness_factor,
            self.shape_randomization_factor, self.displacement_strength,
            self.indentation_scale, self.indentation_shape_factor
        )
        self.uv_coords = generate_uv_coordinates(self.base_vertices)
        
        # Set a new random rotation and speed if fully randomizing
        if randomize_all:
            self.rotation = R.from_euler('xyz', np.random.uniform(0, 360, 3), degrees=True)
            self.rotation_speed = np.random.uniform(-1, 1, 3) # Random X, Y, Z rotation

        # Generate satellites (only if not a satellite itself)
        if not self.is_satellite:
            self.satellites = []
            num_satellites = random.randint(0, 3) # 0 to 3 satellites
            for _ in range(num_satellites):
                satellite_outer_radius = random.uniform(self.satellite_size_range[0], self.satellite_size_range[1])

                # Calculate satellite_size_range for nested satellites based on current satellite's outer_radius
                nested_satellite_proportion = self.nested_satellite_proportion # Use the stored proportion
                nested_min_satellite_size = satellite_outer_radius * nested_satellite_proportion * 0.8
                nested_max_satellite_size = satellite_outer_radius * nested_satellite_proportion * 1.2
                nested_satellite_size_range = (nested_min_satellite_size, nested_max_satellite_size) # Smaller size for satellites
                orbit_distance = self.outer_radius + random.uniform(20, 80) # Orbit slightly outside asteroid
                orbit_speed = random.uniform(0.05, 0.05) # Very slow initial orbital speed
                orbit_acceleration = random.uniform(0.001, 0.005) # Continuous acceleration
                satellite_color_key = random.choice(list(ASTEROID_COLORS.keys()))

                self.satellites.append(Asteroid3D(
                    0, 0, 0, # Initial position will be relative to parent
                    new_outer_radius=satellite_outer_radius,
                    asteroid_type=satellite_color_key,
                    randomize_all=True, # Randomize satellite's own shape
                    is_satellite=True,
                    orbit_distance=random.uniform(self.outer_radius + 10, self.outer_radius + 60), # Orbit slightly outside asteroid
                    orbit_speed=random.uniform(0.1, 0.5), # Significantly faster orbital speed for testing
                    orbit_parent_position=self.position, # Pass parent's position
                    texture_id=self.texture_id, # Pass the texture ID to the satellite
                    satellite_size_range=nested_satellite_size_range, # Pass the dynamically calculated range
                    nested_satellite_proportion=self.nested_satellite_proportion # Pass the proportion to nested satellites
                ))

    def update(self, delta_time, parent_world_position=None):
        # Update self-rotation
        rotation_delta = R.from_rotvec(self.rotation_speed * (math.pi / 180.0)) # Convert speed to radians
        self.rotation = rotation_delta * self.rotation

        # Update satellite orbital mechanics if this is a satellite
        if self.is_satellite:
            self.orbit_angle += self.orbit_speed * delta_time

            # Calculate position relative to parent's world position
            x = self.orbit_distance * math.cos(self.orbit_angle)
            y = self.orbit_distance * math.sin(self.orbit_angle)
            z = 0.0 # Satellites orbit in the XY plane for now

            # Apply parent's world position to get satellite's world position
            self.position = parent_world_position + np.array([x, y, z]) # Use parent_world_position

        # Update nested satellites
        for satellite in self.satellites:
            # Pass current asteroid's world position as parent for its satellites
            satellite.update(delta_time, self.position)

    def get_transformed_vertices(self):
        """Applies current rotation and position to the base vertices."""
        # Rotate the base vertices
        rotated_vertices = self.rotation.apply(self.base_vertices)
        # Translate to the asteroid's world position
        transformed_vertices = rotated_vertices + self.position
        return transformed_vertices

    def get_color(self):
        return ASTEROID_COLORS.get(self.color_key, (139, 69, 19)) # Default to brown

    def get_collision_radius(self):
        # Return the largest semi-axis of the ellipsoid for bounding sphere collision
        return self.outer_radius * max(self.shape_randomization_factor)

    def get_world_position(self):
        return self.position



