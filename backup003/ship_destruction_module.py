import pygame
import random
import math
import numpy as np
from scipy.spatial import Delaunay

# --- Configuration ---
NUM_OUTER_FRACTURE_POINTS = 12
NUM_INNER_FRACTURE_POINTS = 15
MIN_DEBRIS_LIFETIME = 240
MAX_DEBRIS_LIFETIME = 400
MIN_DEBRIS_SPEED = 0.15
MAX_DEBRIS_SPEED = 0.6
MIN_ROTATION_SPEED = -2.0
MAX_ROTATION_SPEED = 2.0

class DebrisPiece:
    """Represents a single, cropped piece of the shattered ship."""
    def __init__(self, image, x, y, velocity, rotation_speed):
        self.original_image = image
        self.image = self.original_image.copy()
        self.x = x
        self.y = y
        self.velocity = velocity
        self.rotation_speed = rotation_speed
        self.rotation_angle = 0 # Start with no rotation
        self.lifetime = random.randint(MIN_DEBRIS_LIFETIME, MAX_DEBRIS_LIFETIME)
        self.alpha = 255

    def update(self, dt_factor=1.0):
        """Updates the position, rotation, and lifetime of the debris piece."""
        self.x += self.velocity[0] * dt_factor
        self.y += self.velocity[1] * dt_factor
        self.rotation_angle += self.rotation_speed * dt_factor
        self.lifetime -= 1 * dt_factor

        if self.lifetime <= 60 * dt_factor:
            self.alpha = max(0, int(255 * (self.lifetime / (60 * dt_factor))))

    def draw(self, surface, camera_x=0, camera_y=0):
        """Draws the rotated and faded debris piece to the screen."""
        if self.lifetime > 0:
            rotated_image = pygame.transform.rotate(self.original_image, self.rotation_angle)
            if self.alpha < 255:
                # This is needed to make sure the alpha is applied to the rotated surface
                alpha_surface = pygame.Surface(rotated_image.get_size(), pygame.SRCALPHA)
                alpha_surface.fill((255, 255, 255, self.alpha))
                rotated_image.blit(alpha_surface, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
            rect = rotated_image.get_rect(center=(self.x - camera_x, self.y - camera_y))
            surface.blit(rotated_image, rect)

def create_ship_debris(ship_image, center_x, center_y):
    """
    Generates a list of DebrisPiece objects by shattering the ship's image
    using Delaunay triangulation. Each piece is cropped and positioned to
    form the intact ship initially.
    """
    debris_list = []
    ship_width, ship_height = ship_image.get_size()
    ship_rect = ship_image.get_rect()
    max_radius = max(ship_width, ship_height) / 2

    points = []
    # 1. Generate points for triangulation
    # Add corners for better boundary
    points.extend([ship_rect.topleft, ship_rect.topright, ship_rect.bottomleft, ship_rect.bottomright])
    # Add center point
    points.append(ship_rect.center)
    # Add inner points
    for _ in range(NUM_INNER_FRACTURE_POINTS):
        points.append((random.randint(0, ship_width), random.randint(0, ship_height)))
    # Add outer points
    base_angle_step = (2 * math.pi) / NUM_OUTER_FRACTURE_POINTS
    for i in range(NUM_OUTER_FRACTURE_POINTS):
        angle = base_angle_step * i + random.uniform(-0.1, 0.1)
        distance = random.uniform(max_radius * 0.9, max_radius * 1.1)
        points.append((
            ship_rect.centerx + distance * math.cos(angle),
            ship_rect.centery + distance * math.sin(angle)
        ))

    # 2. Perform Delaunay triangulation
    try:
        tri = Delaunay(np.array(points))
    except Exception as e:
        print(f"Triangulation failed: {e}. No debris created.")
        return []

    # 3. Create a debris piece for each triangle
    for simplex in tri.simplices:
        triangle_points = [tuple(points[i]) for i in simplex]

        # Calculate bounding box for the triangle
        min_x = min(p[0] for p in triangle_points)
        max_x = max(p[0] for p in triangle_points)
        min_y = min(p[1] for p in triangle_points)
        max_y = max(p[1] for p in triangle_points)
        
        # Clamp bounding box to ship image dimensions
        min_x, max_x = max(0, min_x), min(ship_width, max_x)
        min_y, max_y = max(0, min_y), min(ship_height, max_y)

        bbox_width = max_x - min_x
        bbox_height = max_y - min_y

        if bbox_width < 1 or bbox_height < 1:
            continue

        # Create a cropped surface for just this piece
        cropped_ship_part = pygame.Surface((bbox_width, bbox_height), pygame.SRCALPHA)
        cropped_ship_part.blit(ship_image, (0, 0), area=pygame.Rect(min_x, min_y, bbox_width, bbox_height))

        # Create the mask for the cropped piece
        mask = pygame.Surface((bbox_width, bbox_height), pygame.SRCALPHA)
        # Translate triangle points to be relative to the cropped surface
        translated_points = [(p[0] - min_x, p[1] - min_y) for p in triangle_points]
        pygame.draw.polygon(mask, (255, 255, 255, 255), translated_points)

        # Apply the mask
        cropped_ship_part.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

        # Calculate initial position and velocity
        piece_center_x = min_x + bbox_width / 2
        piece_center_y = min_y + bbox_height / 2
        
        initial_pos_x = center_x - ship_width / 2 + piece_center_x
        initial_pos_y = center_y - ship_height / 2 + piece_center_y

        debris_angle = math.atan2(piece_center_y - ship_rect.centery, piece_center_x - ship_rect.centerx)
        debris_angle += random.uniform(-math.pi / 16, math.pi / 16)
        
        dist_from_center = math.hypot(piece_center_x - ship_rect.centerx, piece_center_y - ship_rect.centery)
        speed_modifier = 0.5 + (dist_from_center / max_radius)
        debris_speed = random.uniform(MIN_DEBRIS_SPEED, MAX_DEBRIS_SPEED) * speed_modifier
        
        velocity = (math.cos(debris_angle) * debris_speed, math.sin(debris_angle) * debris_speed)
        rotation_speed = random.uniform(MIN_ROTATION_SPEED, MAX_ROTATION_SPEED)

        debris_list.append(DebrisPiece(cropped_ship_part, initial_pos_x, initial_pos_y, velocity, rotation_speed))

    return debris_list


if __name__ == '__main__':
    import sys
    import os

    # --- Constants ---
    SCREEN_WIDTH = 800
    SCREEN_HEIGHT = 600
    FPS = 60
    ASSET_PATH = "assets"
    SHIP_IMAGE_NAME = "ship01_big.png"

    # --- Initialization ---
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Ship Destruction Test")
    clock = pygame.time.Clock()
    font = pygame.font.Font(None, 28)

    # --- Load Assets ---
    try:
        ship_image_path = os.path.join(ASSET_PATH, SHIP_IMAGE_NAME)
        ship_image = pygame.image.load(ship_image_path).convert_alpha()
    except pygame.error as e:
        print(f"Error loading ship image '{ship_image_path}': {e}")
        print("Please ensure you are running this script from the root project directory ('BlackHoleRun').")
        pygame.quit()
        sys.exit()

    # --- Game State ---
    debris_pieces = []
    exploding = False

    def reset_explosion():
        global debris_pieces, exploding
        debris_pieces = create_ship_debris(ship_image, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
        exploding = False
        if not debris_pieces:
            print("Failed to create debris.")
        else:
            print(f"Generated {len(debris_pieces)} debris pieces.")

    reset_explosion() # Initial setup

    # --- Main Loop ---
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                if event.key == pygame.K_SPACE:
                    if not exploding:
                        print("Exploding!")
                        exploding = True
                if event.key == pygame.K_r:
                    print("Resetting.")
                    reset_explosion()

        # --- Update ---
        if exploding:
            for piece in debris_pieces:
                piece.update()

        # --- Draw ---
        screen.fill((10, 20, 40))  # Dark blue background

        if not exploding:
            # Draw the intact ship using the un-rotated, un-moved debris pieces
            for piece in debris_pieces:
                 rect = piece.original_image.get_rect(center=(piece.x, piece.y))
                 screen.blit(piece.original_image, rect)
        else:
            # Draw the exploding pieces
            for piece in debris_pieces:
                piece.draw(screen)
        
        # --- UI Text ---
        if not exploding:
            text_surf = font.render("Press SPACE to explode", True, (255, 255, 255))
            screen.blit(text_surf, (10, 10))
        else:
            text_surf = font.render("Press 'R' to reset", True, (255, 255, 255))
            screen.blit(text_surf, (10, 10))


        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    sys.exit()