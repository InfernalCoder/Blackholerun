import pygame
import random
import math
import numpy as np
from scipy.spatial import Delaunay

# --- Configuration ---
NUM_OUTER_FRACTURE_POINTS = 8 # Reduced for asteroids to create larger pieces
NUM_INNER_FRACTURE_POINTS = 10 # Reduced for asteroids
MIN_DEBRIS_LIFETIME = 120 # Shorter initial float time
MAX_DEBRIS_LIFETIME = 240 # Shorter initial float time
MIN_DEBRIS_SPEED = 0.5 # Faster initial burst
MAX_DEBRIS_SPEED = 1.5 # Faster initial burst
MIN_ROTATION_SPEED = -5.0 # Faster rotation
MAX_ROTATION_SPEED = 5.0 # Faster rotation

class AsteroidDebrisPiece:
    """Represents a single, cropped piece of a shattered asteroid."""
    def __init__(self, image, x, y, velocity, rotation_speed, game, animated_color=(255,255,255)):
        self.game = game
        self.original_image = image
        self.image = self.original_image.copy()
        self.x = x
        self.y = y
        self.velocity = velocity
        self.rotation_speed = rotation_speed
        self.rotation_angle = 0 # Start with no rotation
        self.lifetime = random.randint(MIN_DEBRIS_LIFETIME, MAX_DEBRIS_LIFETIME) # Initial float time
        self.alpha = 255
        self.sucked_in = False
        self.suck_in_timer = self.lifetime // 2 # Start sucking in after half initial float time
        self.swirl_strength = random.uniform(0.5, 1.5)
        self.animated_color = animated_color

    def update(self, dt_factor=1.0):
        """Updates the position, rotation, and lifetime of the debris piece."""
        if not self.sucked_in:
            self.x += self.velocity[0] * dt_factor
            self.y += self.velocity[1] * dt_factor
            self.rotation_angle += self.rotation_speed * dt_factor
            self.lifetime -= 1 * dt_factor

            if self.lifetime <= self.suck_in_timer:
                self.sucked_in = True
        else:
            # Sucking logic, similar to SuckingParticle
            dx = self.game.original_screen_width // 2 - self.x
            dy = self.game.original_screen_height // 2 - self.y
            distance = math.hypot(dx, dy)
            if distance > 0:
                attraction_speed = 4 # Adjust the speed of being pulled in
                tangential_speed = attraction_speed * 1.9 * self.swirl_strength # Adjust for swirl intensity

                # Normalize the direction towards the center
                nx = dx / distance
                ny = dy / distance

                # Calculate tangential velocity components (perpendicular to the normalized direction)
                tangential_vx = -ny * tangential_speed # Rotate direction by 90 degrees counter-clockwise
                tangential_vy = nx * tangential_speed

                # Apply the velocities
                self.x += nx * attraction_speed + tangential_vx
                self.y += ny * attraction_speed + tangential_vy

            # Reduce alpha as it gets closer to the black hole
            if distance < 100: # Start fading when close to black hole
                self.alpha = max(0, int(255 * (distance / 100)))
            
            # Remove when very close to black hole
            if distance < 50 * 1.2: # Black hole radius is 50, 1.2 is a buffer
                self.lifetime = 0 # Mark for removal

        if self.lifetime <= 0:
            self.alpha = 0 # Ensure fully transparent when dead

    def draw(self, surface, camera_x=0, camera_y=0):
        """Draws the rotated and faded debris piece to the screen."""
        if self.lifetime > 0:
            rotated_image = pygame.transform.rotate(self.original_image, self.rotation_angle)
            
            # Apply the animated color tint
            tinted_image = pygame.Surface(rotated_image.get_size(), pygame.SRCALPHA)
            tinted_image.fill(self.animated_color)
            rotated_image.blit(tinted_image, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

            if self.alpha < 255:
                # This is needed to make sure the alpha is applied to the rotated surface
                alpha_surface = pygame.Surface(rotated_image.get_size(), pygame.SRCALPHA)
                alpha_surface.fill((255, 255, 255, self.alpha)) # White mask for alpha
                rotated_image.blit(alpha_surface, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
            rect = rotated_image.get_rect(center=(self.x - camera_x, self.y - camera_y))
            surface.blit(rotated_image, rect)

def create_asteroid_debris(asteroid_image, center_x, center_y, game, animated_color=(255,255,255)):
    """
    Generates a list of AsteroidDebrisPiece objects by shattering the asteroid's image
    using Delaunay triangulation.
    """
    debris_list = []
    img_width, img_height = asteroid_image.get_size()
    img_rect = asteroid_image.get_rect()
    max_radius = max(img_width, img_height) / 2

    points = []
    # 1. Generate points for triangulation
    # Add corners for better boundary
    points.extend([img_rect.topleft, img_rect.topright, img_rect.bottomleft, img_rect.bottomright])
    # Add center point
    points.append(img_rect.center)
    # Add inner points
    for _ in range(NUM_INNER_FRACTURE_POINTS):
        points.append((random.randint(0, img_width), random.randint(0, img_height)))
    # Add outer points
    base_angle_step = (2 * math.pi) / NUM_OUTER_FRACTURE_POINTS
    for i in range(NUM_OUTER_FRACTURE_POINTS):
        angle = base_angle_step * i + random.uniform(-0.1, 0.1)
        distance = random.uniform(max_radius * 0.9, max_radius * 1.1)
        points.append((
            img_rect.centerx + distance * math.cos(angle),
            img_rect.centery + distance * math.sin(angle)
        ))

    # 2. Perform Delaunay triangulation
    try:
        tri = Delaunay(np.array(points))
    except Exception as e:
        print(f"Triangulation failed for asteroid: {e}. No debris created.")
        return []

    # 3. Create a debris piece for each triangle
    for simplex in tri.simplices:
        triangle_points = [tuple(points[i]) for i in simplex]

        # Calculate bounding box for the triangle
        min_x = min(p[0] for p in triangle_points)
        max_x = max(p[0] for p in triangle_points)
        min_y = min(p[1] for p in triangle_points)
        max_y = max(p[1] for p in triangle_points)
        
        # Clamp bounding box to image dimensions
        min_x, max_x = max(0, min_x), min(img_width, max_x)
        min_y, max_y = max(0, min_y), min(img_height, max_y)

        bbox_width = max_x - min_x
        bbox_height = max_y - min_y

        if bbox_width < 1 or bbox_height < 1:
            continue

        # Create a cropped surface for just this piece
        cropped_part = pygame.Surface((bbox_width, bbox_height), pygame.SRCALPHA)
        cropped_part.blit(asteroid_image, (0, 0), area=pygame.Rect(min_x, min_y, bbox_width, bbox_height))

        # Create the mask for the cropped piece
        mask = pygame.Surface((bbox_width, bbox_height), pygame.SRCALPHA)
        # Translate triangle points to be relative to the cropped surface
        translated_points = [(p[0] - min_x, p[1] - min_y) for p in triangle_points]
        pygame.draw.polygon(mask, (255, 255, 255, 255), translated_points) # White mask

        # Apply the mask
        cropped_part.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

        # Calculate initial position and velocity
        piece_center_x = min_x + bbox_width / 2
        piece_center_y = min_y + bbox_height / 2
        
        initial_pos_x = center_x - img_width / 2 + piece_center_x
        initial_pos_y = center_y - img_height / 2 + piece_center_y

        debris_angle = math.atan2(piece_center_y - img_rect.centery, piece_center_x - img_rect.centerx)
        debris_angle += random.uniform(-math.pi / 8, math.pi / 8) # Wider spread for asteroid debris
        
        dist_from_center = math.hypot(piece_center_x - img_rect.centery, piece_center_y - img_rect.centerx)
        speed_modifier = 0.5 + (dist_from_center / max_radius) # Pieces further from center get more speed
        debris_speed = random.uniform(MIN_DEBRIS_SPEED, MAX_DEBRIS_SPEED) * speed_modifier
        
        velocity = (math.cos(debris_angle) * debris_speed, math.sin(debris_angle) * debris_speed)
        rotation_speed = random.uniform(MIN_ROTATION_SPEED, MAX_ROTATION_SPEED)

        debris_list.append(AsteroidDebrisPiece(cropped_part, initial_pos_x, initial_pos_y, velocity, rotation_speed, game, animated_color))

    return debris_list


if __name__ == '__main__':
    # This is a standalone test block for the module
    pygame.init()

    SCREEN_WIDTH = 800
    SCREEN_HEIGHT = 600
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Asteroid Destruction Test")
    clock = pygame.time.Clock()

    # Mock Game class for testing
    class MockGame:
        def __init__(self):
            self.original_screen_width = SCREEN_WIDTH
            self.original_screen_height = SCREEN_HEIGHT

    mock_game = MockGame()

    # Create a dummy asteroid image for testing
    test_asteroid_image = pygame.Surface((100, 100), pygame.SRCALPHA)
    pygame.draw.circle(test_asteroid_image, (150, 100, 50), (50, 50), 50)

    debris_pieces = []
    exploding = False

    def reset_explosion():
        global debris_pieces, exploding
        # Pass a dummy animated_color for testing (e.g., a bright red)
        debris_pieces = create_asteroid_debris(test_asteroid_image, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2, mock_game, (255, 100, 100))
        exploding = True # Start exploding immediately for test

    reset_explosion()

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    reset_explosion()

        screen.fill((10, 10, 30)) # Dark space background

        # Draw black hole center for visual reference of sucking
        pygame.draw.circle(screen, (0,0,0), (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2), 60)

        active_debris = []
        for piece in debris_pieces:
            piece.update()
            if piece.lifetime > 0:
                piece.draw(screen)
                active_debris.append(piece)
        debris_pieces = active_debris # Remove dead pieces

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
    sys.exit()