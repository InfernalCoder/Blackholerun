import pygame
import random
import math
import sys

import os

# --- Asset Path ---
ASSET_PATH = "assets"

# --- Configuration for Asteroid Generation ---
NUM_POINTS = 25

# --- Smoothing Configuration ---
SMOOTHING_FACTOR_Q1 = 0.25
SMOOTHING_FACTOR_Q2 = 0.75

# --- Texture Configuration ---
# Global storage for the single, clear asteroid texture
CLEAR_ASTEROID_TEXTURE = None
# Global storage for texture dimensions
TEXTURE_DIMENSIONS = (0, 0)

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

# --- Jaggedness Configuration based on Size (POINT_ANGLE_JITTER) ---
MIN_SIZE_FOR_JITTER = 20
MAX_SIZE_FOR_JITTER = 150
BASE_JITTER = 0.05
MAX_JITTER = 0.20

# --- Smoothing Iteration Configuration based on Size ---
MIN_SIZE_FOR_SMOOTHING_CHANGE = 20
MAX_SIZE_FOR_SMOOTHING_CHANGE = 150 # Corrected typo: '0' to 'O'
MAX_SMOOTHING_ITERATIONS = 4
MIN_SMOOTHING_ITERATIONS = 1

# --- Radial Variance (Inner/Outer Gap) Configuration based on Size ---
MIN_SIZE_FOR_VARIANCE_CHANGE = 20
MAX_SIZE_FOR_VARIANCE_CHANGE = 150
MIN_RADIAL_VARIANCE = 10
MAX_RADIAL_VARIANCE = 50

# --- Animation Configuration ---
ANIMATION_SEQUENCE_INDICES = [0, 1, 2, 3, 4, 5, 6, 7, 6, 5, 4, 3, 2]


# --- Helper function for smoothing polygon points ---
def smooth_polygon(points, iterations, factor_q1=SMOOTHING_FACTOR_Q1, factor_q2=SMOOTHING_FACTOR_Q2):
    """
    Applies a smoothing process to a list of polygon points using a method similar to Chaikin's algorithm.
    """
    current_points = list(points)
    for _ in range(iterations):
        next_points = []
        num_current_points = len(current_points)
        for i in range(num_current_points):
            p1 = current_points[i]
            p2 = current_points[(i + 1) % num_current_points]
            q1_x = p1[0] + factor_q1 * (p2[0] - p1[0])
            q1_y = p1[1] + factor_q1 * (p2[1] - p1[1])
            q2_x = p1[0] + factor_q2 * (p2[0] - p1[0])
            q2_y = p1[1] + factor_q2 * (p2[1] - p1[1])
            next_points.append((q1_x, q1_y))
            next_points.append((q2_x, q2_y))
        current_points = next_points
    return [(int(x), int(y)) for x, y in current_points]


# --- Function to generate the asteroid's *core data* (shape and initial texture patch) ---
def generate_asteroid_core_data(inner_radius, outer_radius, point_angle_jitter_val, smoothing_iterations_val, texture_frame_width, texture_frame_height):
    """
    Generates the smoothed polygon points, surface size, and random texture patch coordinates
    for a new asteroid.
    """
    if inner_radius >= outer_radius:
        inner_radius = outer_radius - 1
        if inner_radius < 1: inner_radius = 1

    # Add padding around the asteroid for rotation and visual effects
    surface_size = outer_radius * 2 + 10

    jagged_points = []
    base_angle_step = (2 * math.pi) / NUM_POINTS
    current_angle = 0.0

    for _ in range(NUM_POINTS):
        jitter_angle = (random.random() * 2 - 1) * base_angle_step * point_angle_jitter_val
        current_angle += base_angle_step + jitter_angle
        if current_angle > 2 * math.pi: current_angle -= 2.0 * math.pi
        distance = random.uniform(inner_radius, outer_radius)
        x = surface_size // 2 + distance * math.cos(current_angle)
        y = surface_size // 2 + distance * math.sin(current_angle)
        jagged_points.append((x, y))

    if len(jagged_points) > 2:
        smoothed_points = smooth_polygon(jagged_points, smoothing_iterations_val)
    else:
        smoothed_points = [(int(p[0]), int(p[1])) for p in jagged_points]

    max_patch_x = max(0, texture_frame_width - surface_size)
    max_patch_y = max(0, texture_frame_height - surface_size)
    patch_x = random.randint(0, max_patch_x) if max_patch_x > 0 else 0
    patch_y = random.randint(0, max_patch_y) if max_patch_y > 0 else 0

    return smoothed_points, surface_size, patch_x, patch_y

# --- Function to apply a texture to a given asteroid shape ---
def apply_texture_to_shape(smoothed_points, surface_size, texture_surface, patch_x, patch_y, base_color):
    """
    Creates a colored asteroid surface by layering a color, the clear texture, and a shape mask.
    """
    asteroid_surface = pygame.Surface((surface_size, surface_size), pygame.SRCALPHA)
    asteroid_surface.fill(base_color) # Start with the base color

    # Blit the clear texture on top of the color
    patch_w = surface_size
    patch_h = surface_size
    texture_rect = pygame.Rect(patch_x, patch_y, patch_w, patch_h)
    texture_patch_original = texture_surface.subsurface(texture_rect)
    texture_patch_scaled = pygame.transform.scale(texture_patch_original, (surface_size, surface_size))
    asteroid_surface.blit(texture_patch_scaled, (0, 0))

    # Apply the shape mask
    mask_surface = pygame.Surface((surface_size, surface_size), pygame.SRCALPHA)
    pygame.draw.polygon(mask_surface, (255, 255, 255, 255), smoothed_points)
    asteroid_surface.blit(mask_surface, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

    return asteroid_surface


# --- Functions to calculate dynamic properties based on size ---
def calculate_dynamic_property(outer_radius, min_size, max_size, min_value, max_value, invert=False):
    """Helper function to calculate a dynamic property based on the asteroid's size."""
    clamped_radius = max(min_size, min(outer_radius, max_size))
    normalized_progress = (clamped_radius - min_size) / (max_size - min_size)
    
    if invert:
        normalized_progress = 1.0 - normalized_progress
        
    return min_value + (max_value - min_value) * normalized_progress

def get_jitter_for_size(outer_radius):
    """Calculates POINT_ANGLE_JITTER based on outer_radius."""
    return calculate_dynamic_property(outer_radius, MIN_SIZE_FOR_JITTER, MAX_SIZE_FOR_JITTER, BASE_JITTER, MAX_JITTER)

def get_smoothing_iterations_for_size(outer_radius):
    """Calculates smoothing iterations based on outer_radius."""
    return int(round(calculate_dynamic_property(outer_radius, MIN_SIZE_FOR_SMOOTHING_CHANGE, MAX_SIZE_FOR_SMOOTHING_CHANGE, MIN_SMOOTHING_ITERATIONS, MAX_SMOOTHING_ITERATIONS, invert=True)))

def get_radial_variance_for_size(outer_radius):
    """Calculates the difference between outer_radius and inner_radius."""
    return int(round(calculate_dynamic_property(outer_radius, MIN_SIZE_FOR_VARIANCE_CHANGE, MAX_SIZE_FOR_VARIANCE_CHANGE, MIN_RADIAL_VARIANCE, MAX_RADIAL_VARIANCE)))


# --- Function for Loading Textures (remains mostly global as it populates shared resources) ---
def load_asteroid_textures():
    """
    Loads the single clear asteroid texture and stores its dimensions.
    """
    global CLEAR_ASTEROID_TEXTURE, TEXTURE_DIMENSIONS

    try:
        frame_path = os.path.join(ASSET_PATH, 'clear_asteroid_texture.png')
        CLEAR_ASTEROID_TEXTURE = pygame.image.load(frame_path).convert_alpha()
        TEXTURE_DIMENSIONS = CLEAR_ASTEROID_TEXTURE.get_size()
    except pygame.error as e:
        print(f"Error loading texture file '{frame_path}': {e}")
        pygame.quit()
        sys.exit(1)

    max_asteroid_surface_dimension = MAX_OUTER_RADIUS * 2 + 10
    w, h = TEXTURE_DIMENSIONS
    if w < max_asteroid_surface_dimension or h < max_asteroid_surface_dimension:
        print("\n" + "="*80)
        print(f"WARNING: The 'clear_asteroid_texture.png' may be too small for effective random sampling, especially for large asteroids.")
        print(f"Loaded texture frame size: {w}x{h}. ")
        print(f"Max asteroid visual size (surface_size): {max_asteroid_surface_dimension}x{max_asteroid_surface_dimension}")
        print(f"For optimal random texture variation, 'clear_asteroid_texture.png' should be larger than the max asteroid size.")
        print("="*80 + "\n")



# --- Asteroid Class ---
class Asteroid:
    def __init__(self, initial_x, initial_y, asteroid_type=None, new_outer_radius=None):
        self.x = initial_x
        self.y = initial_y

        self.outer_radius = 0
        self.inner_radius = 0
        self.jitter = 0.0
        self.smoothing_iterations = 0

        self.color_key = ""
        self.animation_duration = 0
        self.animation_timer_counter = 0
        self.current_animation_frame_index = 0

        self.smoothed_points = []
        self.surface_size = 0
        self.patch_x = 0
        self.patch_y = 0

        self.rotation_angle = 0.0
        self.rotation_speed = 0.0

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
        self.smoothing_iterations = get_smoothing_iterations_for_size(self.outer_radius)

        if asteroid_type is not None:
            self.color_key = asteroid_type
        elif randomize_all:
            self.color_key = random.choice(list(ASTEROID_COLORS.keys()))

        if self.color_key not in ASTEROID_COLORS:
            self.color_key = 'brown'

        self.animation_duration = random.randint(6, 12)
        self.rotation_angle = random.uniform(0, 360)
        self.rotation_speed = random.uniform(-1.5, 1.5)

        tex_width, tex_height = TEXTURE_DIMENSIONS

        self.smoothed_points, self.surface_size, self.patch_x, self.patch_y = \
            generate_asteroid_core_data(
                self.inner_radius, self.outer_radius, self.jitter, self.smoothing_iterations,
                tex_width, tex_height
            )

        if randomize_all or new_outer_radius is not None or asteroid_type is not None:
             self.animation_timer_counter = random.randint(0, self.animation_duration - 1)
             self.current_animation_frame_index = random.randint(0, len(ANIMATION_SEQUENCE_INDICES) - 1)

    def update(self):
        self.animation_timer_counter += 1
        if self.animation_timer_counter >= self.animation_duration:
            self.animation_timer_counter = 0
            self.current_animation_frame_index = (self.current_animation_frame_index + 1) % len(ANIMATION_SEQUENCE_INDICES)

        self.rotation_angle += self.rotation_speed
        if self.rotation_angle >= 360:
            self.rotation_angle -= 360
        elif self.rotation_angle < 0:
            self.rotation_angle += 360

    def get_current_image(self):
        if CLEAR_ASTEROID_TEXTURE is None:
            return pygame.Surface((self.surface_size, self.surface_size), pygame.SRCALPHA)

        base_color = ASTEROID_COLORS.get(self.color_key, (255, 255, 255))
        brightness_factor = ANIMATION_SEQUENCE_INDICES[self.current_animation_frame_index] / 7.0
        animated_color = tuple(min(255, int(c * (0.5 + brightness_factor * 0.5))) for c in base_color)

        original_asteroid_surface = apply_texture_to_shape(
            self.smoothed_points, self.surface_size, CLEAR_ASTEROID_TEXTURE, self.patch_x, self.patch_y, animated_color
        )

        rotated_asteroid_surface = pygame.transform.rotate(original_asteroid_surface, self.rotation_angle)

        return rotated_asteroid_surface
