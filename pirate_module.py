import pygame
import random
import math
from particle_module import ExplosionParticleSystem

# --- Pirate Configuration ---
PIRATE_RADIUS = 15
PIRATE_COLOR = (150, 150, 0) # Dark yellow/gold
PIRATE_STRUCTURE = 30 # Low health
PIRATE_SPEED = 0.003 # Orbital speed
PIRATE_ENTRY_SPEED = 7 # How fast it flies in
PIRATE_SHOOT_INTERVAL_MIN = 90 # frames
PIRATE_SHOOT_INTERVAL_MAX = 240 # frames

# --- Projectile Configuration ---
PROJECTILE_RADIUS = 5
PROJECTILE_COLOR = (255, 0, 0) # Red
PROJECTILE_SPEED = 10
PROJECTILE_LIFETIME = 120 # frames
PROJECTILE_DAMAGE = 10

class PirateProjectile:
    def __init__(self, x, y, target_x, target_y, game):
        self.game = game
        self.x = x
        self.y = y
        self.radius = PROJECTILE_RADIUS
        self.color = PROJECTILE_COLOR
        self.lifetime = PROJECTILE_LIFETIME
        self.damage = PROJECTILE_DAMAGE

        # Calculate direction towards target
        dx = target_x - x
        dy = target_y - y
        distance = math.hypot(dx, dy)
        if distance > 0:
            self.vx = (dx / distance) * PROJECTILE_SPEED
            self.vy = (dy / distance) * PROJECTILE_SPEED
        else:
            self.vx = 0
            self.vy = 0

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.lifetime -= 1

    def draw(self, game_surface):
        if self.lifetime > 0:
            pygame.draw.circle(game_surface, self.color, (int(self.x), int(self.y)), self.radius)

class Pirate:
    def __init__(self, track, game):
        self.game = game
        self.track = track
        self.target_radius = self.game.player_ship.orbital_radius_base + track * self.game.player_ship.track_width * self.game.player_ship.track_spacing_multiplier
        self.angle = random.uniform(0, 2 * math.pi) # Initial angle
        self.radius = 0 # Starts off-screen
        self.orbital_speed = PIRATE_SPEED * random.choice([-1, 1]) # Random direction

        self.x = self.game.original_screen_width // 2
        self.y = self.game.original_screen_height // 2

        self.structure = PIRATE_STRUCTURE
        self.is_destroyed = False

        self.entering_screen = True
        self.shoot_timer = random.randint(PIRATE_SHOOT_INTERVAL_MIN, PIRATE_SHOOT_INTERVAL_MAX)

        self.pirate_radius = PIRATE_RADIUS # For collision detection

        # Load pirate image
        self.image_orig = pygame.image.load("assets/ship02.png").convert_alpha()
        self.image = self.image_orig # Current image (for rotation)
        self.image_scale = 1.25 # Adjusted for larger size
        self.image_orig = pygame.transform.scale(self.image_orig, (int(self.image_orig.get_width() * self.image_scale), int(self.image_orig.get_height() * self.image_scale)))

    def update(self):
        if self.is_destroyed:
            return

        # Movement logic (fly in, then orbit)
        if self.entering_screen:
            if self.radius < self.target_radius:
                self.radius += PIRATE_ENTRY_SPEED
                if self.radius >= self.target_radius:
                    self.entering_screen = False
            else: # If it spawned beyond the target radius, move inwards
                self.radius -= PIRATE_ENTRY_SPEED
                if self.radius <= self.target_radius:
                    self.entering_screen = False
        else:
            self.angle += self.orbital_speed

        # Update position based on orbital parameters
        self.x = self.game.original_screen_width // 2 + self.radius * math.cos(self.angle)
        self.y = self.game.original_screen_height // 2 + self.radius * math.sin(self.angle)

        # Shooting logic
        self.shoot_timer -= 1
        if self.shoot_timer <= 0:
            self.shoot()
            self.shoot_timer = random.randint(PIRATE_SHOOT_INTERVAL_MIN, PIRATE_SHOOT_INTERVAL_MAX)

        # Check for destruction
        if self.structure <= 0:
            self.is_destroyed = True

    def shoot(self):
        # Create a projectile aimed at the player's current position
        projectile = PirateProjectile(self.x, self.y, self.game.player_ship.x, self.game.player_ship.y, self.game)
        self.game.pirate_projectiles.append(projectile) # Add to a list in the game class
        if self.game.pirate_laser_sound:
            self.game.pirate_laser_sound.play()

    def take_damage(self, amount):
        self.structure -= amount
        if self.structure <= 0:
            self.is_destroyed = True
            # Trigger explosion effect for pirate
            self.game.particle_effects.append(ExplosionParticleSystem((self.x, self.y), (255, 100, 0))) # Orange explosion
            # Play a sound effect (re-use mini-explosion sounds)
            if self.game.mini_explosion_sounds:
                random.choice(self.game.mini_explosion_sounds).play()

    def draw(self, game_surface):
        if not self.is_destroyed:
            # Calculate base rotation angle (what it would be if moving clockwise)
            base_rotation_angle_deg = math.degrees(-self.angle) - 90

            # Adjust rotation based on orbital direction
            if self.orbital_speed > 0: # Counter-clockwise movement
                rotation_angle_deg = base_rotation_angle_deg # Now faces the "base" direction
            else: # Clockwise movement
                rotation_angle_deg = base_rotation_angle_deg + 180 # Now faces 180 degrees opposite
            
            rotated_image = pygame.transform.rotate(self.image_orig, rotation_angle_deg)
            image_rect = rotated_image.get_rect(center=(int(self.x), int(self.y)))
            game_surface.blit(rotated_image, image_rect)
