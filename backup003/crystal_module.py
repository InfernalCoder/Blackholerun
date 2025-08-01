import pygame
import random
import math
import os
import sys

ASSET_PATH = "assets"
CRYSTAL_TEXTURES = {
    'green': None,
    'yellow': None
}
TEXTURE_DIMENSIONS = {
    'green': (0, 0),
    'yellow': (0, 0)
}
TEXTURE_LIGHTNESS_MAPS = {
    'green': {'dark': [], 'mid': [], 'light': []},
    'yellow': {'dark': [], 'mid': [], 'light': []}
}

CRYSTAL_COLORS = {
    'red': (255, 0, 0),
    'green': (0, 255, 0),
    'blue': (0, 0, 255),
    'purple': (128, 0, 128),
    'yellow': (255, 255, 0),
    'cyan': (0, 255, 255),
    'magenta': (255, 0, 255),
    'white': (255, 255, 255)
}

ANIMATION_SEQUENCE_INDICES = [1, 2, 3, 4, 5, 6, 7, 6, 5, 4, 3, 2]

# Configuration for lightness analysis
REGION_SIZE = 10 # Size of the square region to analyze (e.g., 10x10 pixels)
DARK_THRESHOLD = 80 # Max luminance for a 'dark' region
LIGHT_THRESHOLD = 120 # Min luminance for a 'light' region

def load_crystal_texture():
    global CRYSTAL_TEXTURES, TEXTURE_DIMENSIONS, TEXTURE_LIGHTNESS_MAPS
    
    texture_files = {
        'green': 'emerald_texture.png',
        'yellow': 'yellow_crystal_texture.png'
    }

    for color, filename in texture_files.items():
        try:
            texture_path = os.path.join(ASSET_PATH, filename)
            texture = pygame.image.load(texture_path).convert_alpha()
            CRYSTAL_TEXTURES[color] = texture
            TEXTURE_DIMENSIONS[color] = texture.get_size()

            # Analyze lightness levels
            tex_width, tex_height = TEXTURE_DIMENSIONS[color]
            region_size_x = min(REGION_SIZE, tex_width)
            region_size_y = min(REGION_SIZE, tex_height)

            lightness_map = TEXTURE_LIGHTNESS_MAPS[color]
            lightness_map['dark'].clear()
            lightness_map['mid'].clear()
            lightness_map['light'].clear()

            for y in range(0, tex_height, region_size_y):
                for x in range(0, tex_width, region_size_x):
                    total_luminance = 0
                    num_pixels = 0
                    for dy in range(region_size_y):
                        for dx in range(region_size_x):
                            px = x + dx
                            py = y + dy
                            if px < tex_width and py < tex_height:
                                r, g, b, _ = texture.get_at((px, py))
                                luminance = 0.299*r + 0.587*g + 0.114*b
                                total_luminance += luminance
                                num_pixels += 1
                    
                    if num_pixels > 0:
                        avg_luminance = total_luminance / num_pixels
                        if avg_luminance < DARK_THRESHOLD:
                            lightness_map['dark'].append((x, y))
                        elif avg_luminance > LIGHT_THRESHOLD:
                            lightness_map['light'].append((x, y))
                        else:
                            lightness_map['mid'].append((x, y))

        except pygame.error as e:
            print(f"Error loading texture file '{filename}': {e}")
            # We can decide to continue without this texture or exit
            # For now, let's print the error and continue
            CRYSTAL_TEXTURES[color] = None


def generate_crystal_shape(center_x, center_y, avg_radius, num_vertices, irregularity, spikiness):
    vertices = []
    angle_step = (2 * math.pi) / num_vertices
    for i in range(num_vertices):
        angle = (i * angle_step) + random.uniform(-irregularity, irregularity) * angle_step
        radius = avg_radius * (1 + random.uniform(-spikiness, spikiness))
        x = center_x + radius * math.cos(angle)
        y = center_y + radius * math.sin(angle)
        vertices.append((x, y))
    return vertices

class Crystal:
    def __init__(self, initial_x, initial_y, base_avg_radius=30):
        self.x = initial_x
        self.y = initial_y
        self.base_avg_radius = base_avg_radius # Overall size control

        self.color_key = 'green'
        self.base_color = CRYSTAL_COLORS[self.color_key]

        self.rotation_angle = random.uniform(0, 360)
        self.rotation_speed = random.uniform(-1.0, 1.0)
        self.animation_duration = random.randint(8, 15)
        self.animation_timer_counter = 0
        self.current_animation_frame_index = 0

        self.rear_vertices = []
        self.mid_vertices = []
        self.front_vertices = []
        self.overall_min_x = float('inf')
        self.overall_max_x = float('-inf')
        self.overall_min_y = float('inf')
        self.overall_max_y = float('-inf')

        self._generate_all_sections()

        # Randomly select a texture patch (now based on overall size)
        tex_width, tex_height = TEXTURE_DIMENSIONS.get(self.color_key, (0, 0))
        overall_width = self.overall_max_x - self.overall_min_x
        overall_height = self.overall_max_y - self.overall_min_y
        
        # Ensure patch size is at least the size of the crystal
        # Clamp patch_w and patch_h to not exceed texture dimensions
        self.patch_w = max(1, min(tex_width, int(overall_width)))
        self.patch_h = max(1, min(tex_height, int(overall_height)))

        self.texture_animation_duration = 4 # Frames until texture changes
        self.texture_animation_timer_counter = 0

        # Store patch coordinates for each section
        self.rear_patch_coords = (0, 0)
        self.mid_patch_coords = (0, 0)
        self.front_patch_coords = (0, 0)

        self._select_texture_patches_for_sections()

    def _generate_section_shape(self, avg_radius, num_vertices, irregularity, spikiness, thickness_strength, major_axis_multiplier, minor_axis_multiplier):
        shape_points = []
        angle_step = (2 * math.pi) / num_vertices
        
        # Define semi-axes for the oval
        semi_major_axis = avg_radius * major_axis_multiplier
        semi_minor_axis = avg_radius * minor_axis_multiplier

        # Rotation angle for the oval (45 degrees)
        oval_rotation_rad = math.radians(45)

        for i in range(num_vertices):
            # Base angle for the ellipse
            base_angle = (i * angle_step)
            
            # Apply irregularity to the angle
            angle = base_angle + random.uniform(-irregularity, irregularity) * angle_step

            # Calculate point on unrotated ellipse
            x_unrotated = semi_major_axis * math.cos(angle)
            y_unrotated = semi_minor_axis * math.sin(angle)

            # Apply spikiness and thickness modulation to the distance from the center
            # The thickness modulation is based on the angle relative to the oval's major axis
            angle_from_major_axis = abs(math.fmod(angle - oval_rotation_rad, math.pi))
            thickness_modulation = 1 - (thickness_strength * math.sin(angle_from_major_axis))

            scale_factor = (1 + random.uniform(-spikiness, spikiness)) * thickness_modulation
            x_perturbed = x_unrotated * scale_factor
            y_perturbed = y_unrotated * scale_factor

            # Rotate the perturbed point by 45 degrees
            x_rotated = x_perturbed * math.cos(oval_rotation_rad) - y_perturbed * math.sin(oval_rotation_rad)
            y_rotated = x_perturbed * math.sin(oval_rotation_rad) + y_perturbed * math.cos(oval_rotation_rad)

            shape_points.append((x_rotated, y_rotated))

        return shape_points

    def _generate_all_sections(self):
        oval_rotation_rad = math.radians(45)

        # Define offsets for each section to create depth
        rear_y_offset = -1  # Rearmost section is slightly behind
        mid_y_offset = 0     # Middle section is at the center
        front_y_offset = 1  # Frontmost section is slightly in front

        # Generate raw vertices for each section, centered at (0,0)
        rear_raw_vertices = self._generate_section_shape(
            self.base_avg_radius * 0.9, 8, 0.01, 0.01, 0.2, 1.0, 0.4 # Adjusted major axis for rear
        )
        self.rear_lightness_preference = 'dark'

        mid_raw_vertices = self._generate_section_shape(
            self.base_avg_radius * 0.6, 20, 0.05, 0.1, 0.2, 1.0, 0.6 # Adjusted major axis for mid
        )
        self.mid_lightness_preference = 'mid'

        front_raw_vertices = self._generate_section_shape(
            self.base_avg_radius * 0.6, 20, 0.05, 0.1, 0.2, 2.0, 0.3
        )
        self.front_lightness_preference = 'light'

        # Create lists of vertices with offsets applied
        rear_offset_vertices = [(p[0], p[1] + rear_y_offset) for p in rear_raw_vertices]
        mid_offset_vertices = [(p[0], p[1] + mid_y_offset) for p in mid_raw_vertices]
        front_offset_vertices = [(p[0], p[1] + front_y_offset) for p in front_raw_vertices]

        # Calculate overall bounding box for all offset sections
        all_points = rear_offset_vertices + mid_offset_vertices + front_offset_vertices
        self.overall_min_x = min(p[0] for p in all_points)
        self.overall_max_x = max(p[0] for p in all_points)
        self.overall_min_y = min(p[1] for p in all_points)
        self.overall_max_y = max(p[1] for p in all_points)

        # Calculate the center offset for the entire composite crystal
        center_offset_x = (self.overall_min_x + self.overall_max_x) / 2
        center_offset_y = (self.overall_min_y + self.overall_max_y) / 2

        # Translate all sections so the overall center is at (0,0) relative to the crystal's local origin
        self.rear_vertices = [(p[0] - center_offset_x, p[1] - center_offset_y) for p in rear_offset_vertices]
        self.mid_vertices = [(p[0] - center_offset_x, p[1] - center_offset_y) for p in mid_offset_vertices]
        self.front_vertices = [(p[0] - center_offset_x, p[1] - center_offset_y) for p in front_offset_vertices]

        # Calculate overall bounding box for all sections
        all_points = self.rear_vertices + self.mid_vertices + self.front_vertices
        self.overall_min_x = min(p[0] for p in all_points)
        self.overall_max_x = max(p[0] for p in all_points)
        self.overall_min_y = min(p[1] for p in all_points)
        self.overall_max_y = max(p[1] for p in all_points)

        # Translate all sections so the overall center is at (0,0) relative to the crystal's local origin
        center_offset_x = (self.overall_min_x + self.overall_max_x) / 2
        center_offset_y = (self.overall_min_y + self.overall_max_y) / 2

        self.rear_vertices = [(p[0] - center_offset_x, p[1] - center_offset_y) for p in self.rear_vertices]
        self.mid_vertices = [(p[0] - center_offset_x, p[1] - center_offset_y) for p in self.mid_vertices]
        self.front_vertices = [(p[0] - center_offset_x, p[1] - center_offset_y) for p in self.front_vertices]

    def _select_texture_patches_for_sections(self):
        tex_width, tex_height = TEXTURE_DIMENSIONS.get(self.color_key, (0, 0))
        lightness_map = TEXTURE_LIGHTNESS_MAPS.get(self.color_key)

        if not lightness_map:
            # Fallback if the lightness map for this color doesn't exist
            self.rear_patch_coords = (0, 0)
            self.mid_patch_coords = (0, 0)
            self.front_patch_coords = (0, 0)
            return

        # Helper to select a valid patch coordinate
        def get_valid_patch_coords(lightness_pref):
            # Try preferred category first
            preferred_regions = lightness_map.get(lightness_pref, [])

            if preferred_regions:
                available_regions = preferred_regions
            else:
                # Fallback to all available regions if preferred is empty
                all_regions = lightness_map['dark'] + lightness_map['mid'] + lightness_map['light']
                if all_regions:
                    available_regions = all_regions
                else:
                    # Absolute fallback if texture has no analyzable regions
                    return (0, 0)
            
            candidate_patch_x, candidate_patch_y = random.choice(available_regions)

            patch_x = min(candidate_patch_x, tex_width - self.patch_w)
            patch_y = min(candidate_patch_y, tex_height - self.patch_h)
            patch_x = max(0, patch_x)
            patch_y = max(0, patch_y)
            return patch_x, patch_y

        self.rear_patch_coords = get_valid_patch_coords(self.rear_lightness_preference)
        self.mid_patch_coords = get_valid_patch_coords(self.mid_lightness_preference)
        self.front_patch_coords = get_valid_patch_coords(self.front_lightness_preference)


    def update(self):
        self.animation_timer_counter += 1
        if self.animation_timer_counter >= self.animation_duration:
            self.animation_timer_counter = 0
            self.current_animation_frame_index = (self.current_animation_frame_index + 1) % len(ANIMATION_SEQUENCE_INDICES)
        self.rotation_angle = (self.rotation_angle + self.rotation_speed) % 360

        self.texture_animation_timer_counter += 1
        if self.texture_animation_timer_counter >= self.texture_animation_duration:
            self.texture_animation_timer_counter = 0
            self._select_texture_patches_for_sections()

    def get_current_image(self):
        # Determine the size of the surface needed to contain the crystal
        # Add a small buffer for rotation and visual effects
        overall_width = self.overall_max_x - self.overall_min_x
        overall_height = self.overall_max_y - self.overall_min_y
        surface_size = int(max(overall_width, overall_height) * 1.2) # 20% buffer
        
        crystal_surface = pygame.Surface((surface_size, surface_size), pygame.SRCALPHA)
        
        # Calculate translation to center the overall crystal on its surface
        translate_x = surface_size / 2
        translate_y = surface_size / 2

        # Draw each section
        sections = [
            (self.rear_vertices, 0.2, self.rear_lightness_preference),  # Darker for rear
            (self.mid_vertices, 0.5, self.mid_lightness_preference),   # Mid brightness
            (self.front_vertices, 1.0, self.front_lightness_preference)  # Lighter for front
        ]

        for i, (vertices, base_brightness, lightness_pref) in enumerate(sections):
            section_surface = pygame.Surface((surface_size, surface_size), pygame.SRCALPHA)
            
            brightness_factor = ANIMATION_SEQUENCE_INDICES[self.current_animation_frame_index] / 7.0
            animated_color = tuple(min(255, int(c * (base_brightness + brightness_factor * 0.2))) for c in self.base_color)
            
            section_surface.fill(animated_color)

            texture_to_use = CRYSTAL_TEXTURES.get(self.color_key)
            if texture_to_use:
                # Use the pre-selected patch coordinates for this section
                if i == 0: # Rear section
                    patch_x, patch_y = self.rear_patch_coords
                elif i == 1: # Mid section
                    patch_x, patch_y = self.mid_patch_coords
                else: # Front section
                    patch_x, patch_y = self.front_patch_coords

                texture_rect = pygame.Rect(patch_x, patch_y, self.patch_w, self.patch_h)
                texture_patch_original = texture_to_use.subsurface(texture_rect)
                scaled_texture = pygame.transform.scale(texture_patch_original, (surface_size, surface_size))
                section_surface.blit(scaled_texture, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

            mask_surface = pygame.Surface((surface_size, surface_size), pygame.SRCALPHA)
            
            # Translate the vertices to be centered on the new section surface
            translated_vertices = [(p[0] + translate_x, p[1] + translate_y) for p in vertices]

            # Draw black outline (slightly larger)
            outline_thickness = 3 # Adjust as needed
            # Create slightly expanded vertices for the outline
            expanded_vertices = []
            for i in range(len(translated_vertices)):
                p1 = translated_vertices[i]
                p2 = translated_vertices[(i + 1) % len(translated_vertices)]
                # Calculate normal vector for edge
                edge_vec = pygame.math.Vector2(p2[0] - p1[0], p2[1] - p1[1])
                normal_vec = pygame.math.Vector2(-edge_vec.y, edge_vec.x).normalize() * outline_thickness
                expanded_vertices.append((p1[0] + normal_vec.x, p1[1] + normal_vec.y))

            pygame.draw.polygon(mask_surface, (0, 0, 0, 255), expanded_vertices) # Black outline

            pygame.draw.polygon(mask_surface, (255, 255, 255, 255), translated_vertices)
            section_surface.blit(mask_surface, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
            
            crystal_surface.blit(section_surface, (0,0)) # Blit section onto main crystal surface
        
        rotated_surface = pygame.transform.rotate(crystal_surface, self.rotation_angle)
        return rotated_surface

if __name__ == '__main__':
    pygame.init()
    screen_width = 800
    screen_height = 600
    screen = pygame.display.set_mode((screen_width, screen_height))
    pygame.display.set_caption("Crystal Test")
    clock = pygame.time.Clock()
    
    load_crystal_texture()

    crystal = Crystal(screen_width // 2, screen_height // 2, base_avg_radius=50)

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                running = False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                crystal = Crystal(screen_width // 2, screen_height // 2, base_avg_radius=random.randint(20, 60))

        screen.fill((10, 10, 20))
        
        crystal.update() # Disable update for static view
        current_image = crystal.get_current_image()
        rect = current_image.get_rect(center=(crystal.x, crystal.y))
        screen.blit(current_image, rect)

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
