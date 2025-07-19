import pygame
import random
import math
import sys
import numpy as np
from scipy.spatial import ConvexHull
from scipy.spatial.transform import Rotation as R

import os

# --- Asset Path ---
ASSET_PATH = "assets"

# --- Configuration for Asteroid Generation ---
NUM_POINTS = 100 # Increased for better 3D shape

# --- Color Configuration ---
ASTEROID_COLORS = {
    "purple": (128, 0, 128),
    "blue": (0, 0, 255),
    "red": (255, 0, 0),
    "brown": (139, 69, 19),
    "green": (0, 255, 0)
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
def generate_asteroid_core_data(inner_radius, outer_radius, jitter_val):
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

        # Add random jitter to the radius
        radius = random.uniform(inner_radius, outer_radius)
        
        # Convert spherical to cartesian coordinates
        x = radius * math.sin(theta) * math.cos(phi)
        y = radius * math.sin(theta) * math.sin(phi)
        z = radius * math.cos(theta)
        
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
    def __init__(self, initial_x, initial_y, initial_z, asteroid_type=None, new_outer_radius=None):
        self.position = np.array([initial_x, initial_y, initial_z], dtype=float)

        self.outer_radius = 0
        self.inner_radius = 0
        self.jitter = 0.0

        self.color_key = ""
        
        # Store the base, unrotated vertices and faces
        self.base_vertices = np.array([])
        self.faces = np.array([])
        self.uv_coords = np.array([]) # Add UV coordinates

        # 3D Rotation attributes
        self.rotation = R.from_euler('xyz', [0, 0, 0], degrees=True) # Initial rotation
        self.rotation_speed = np.random.uniform(-1, 1, 3) # Random axis and speed

        self.recreate_asteroid(
            new_outer_radius=new_outer_radius,
            asteroid_type=asteroid_type,
            randomize_all=(new_outer_radius is None and asteroid_type is None)
        )

    def recreate_asteroid(self, new_outer_radius=None, asteroid_type=None, randomize_all=False):
        if new_outer_radius is not None:
            self.outer_radius = max(MIN_OUTER_RADIUS, min(new_outer_radius, MAX_OUTER_RADIUS))
        elif randomize_all:
            self.outer_radius = random.randint(MIN_OUTER_RADIUS, MAX_OUTER_RADIUS)

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

        # Generate the 3D data
        self.base_vertices, self.faces = generate_asteroid_core_data(
            self.inner_radius, self.outer_radius, self.jitter
        )
        self.uv_coords = generate_uv_coordinates(self.base_vertices)
        
        # Set a new random rotation and speed if fully randomizing
        if randomize_all:
            self.rotation = R.from_euler('xyz', np.random.uniform(0, 360, 3), degrees=True)
            self.rotation_speed = np.random.uniform(-1, 1, 3)

    def update(self):
        # Create a small rotation delta for this frame
        rotation_delta = R.from_rotvec(self.rotation_speed * (math.pi / 180.0)) # Convert speed to radians
        # Apply the delta to the current rotation
        self.rotation = rotation_delta * self.rotation

    def get_transformed_vertices(self):
        """Applies current rotation and position to the base vertices."""
        # Rotate the base vertices
        rotated_vertices = self.rotation.apply(self.base_vertices)
        # Translate to the asteroid's world position
        transformed_vertices = rotated_vertices + self.position
        return transformed_vertices

    def get_color(self):
        return ASTEROID_COLORS.get(self.color_key, (139, 69, 19)) # Default to brown
