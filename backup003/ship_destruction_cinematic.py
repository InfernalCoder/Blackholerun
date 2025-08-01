
import pygame
import random
import math
import sys
import os
from scipy.spatial import Delaunay
import numpy as np

# --- Animation Configuration ---
# State Durations (in frames)
SHAKE_1_DURATION = 15
DELAY_1_DURATION = 60
SHAKE_2_DURATION = 20
DELAY_2_DURATION = 60
SHAKE_INTENSITY = 8
FLASH_DURATION = 8
FRACTURE_DURATION = 15
EXPAND_DURATION = 80
COAST_DURATION = 90
FADEOUT_DURATION = 60

# Flash
FLASH_COLOR = (255, 255, 255)

# Explosion Core
CORE_START_COLOR = (255, 255, 200) # Bright yellow-white
CORE_END_COLOR = (255, 100, 0)   # Fiery orange
CORE_MAX_RADIUS = 80

# Debris
FRACTURE_SPEED = 0.02
DEBRIS_MIN_SPEED = 3.0
DEBRIS_MAX_SPEED = 5.0
DEBRIS_MIN_ROTATION = -5.0
DEBRIS_MAX_ROTATION = 5.0

# Sparks
SPARK_COUNT = 50
SPARK_COLOR = (255, 255, 150)
SPARK_SPEED = 5
SPARK_LIFETIME = 20

# Mini-Explosion
MINI_EXPLOSION_DURATION = 15

# Smoke Clouds
SMOKE_CLOUD_COUNT = 30
SMOKE_CLOUD_COLOR = (100, 100, 100, 150) # Dark grey, more transparent
SMOKE_CLOUD_MIN_RADIUS = 5
SMOKE_CLOUD_MAX_RADIUS = 60
SMOKE_CLOUD_LIFETIME = 120 # Frames
SMOKE_CLOUD_SPEED_MULTIPLIER = 1.0 # How fast they move outwards
SMOKE_CLOUD_JITTER = 0.5 # How much random movement each frame
MINI_EXPLOSION_MAX_RADIUS = 20
MINI_EXPLOSION_COLOR = (255, 150, 0) # Orange-yellow

# Electrical Arcs
ARC_COLOR = (150, 200, 255) # Light blue
ARC_LIFETIME = 10 # Very short
ARC_LENGTH = 50 # Max length of a segment
ARC_JITTER = 9 # How jagged the arc is
BRANCH_CHANCE = 0.2 # Chance for an arc to branch
MAX_BRANCH_DEPTH = 2 # How many levels of branching

# Twinkling Stars
NUM_TWINKLING_STARS = 200
STAR_MIN_SIZE = 0
STAR_MAX_SIZE = 2
STAR_MIN_ALPHA = 50
STAR_MAX_ALPHA = 200
STAR_ALPHA_CHANGE_SPEED = 5

# --- Helper Classes ---

class CinematicDebris:
    """A piece of the ship for the cinematic explosion."""
    def __init__(self, image, pos, velocity, rotation_speed):
        self.image = image # This image is now already rotated
        self.pos = list(pos)
        self.velocity = velocity
        self.rotation_speed = rotation_speed
        self.rotation_angle = 0 # No initial rotation needed, as image is pre-rotated

    def update(self, coasting_drag=0.995):
        self.pos[0] += self.velocity[0]
        self.pos[1] += self.velocity[1]
        self.rotation_angle += self.rotation_speed
        
        # Apply drag during the coasting phase
        self.velocity[0] *= coasting_drag
        self.velocity[1] *= coasting_drag

    def draw(self, surface):
        rotated_image = pygame.transform.rotate(self.image, self.rotation_angle) # Apply only its own tumbling rotation
        rect = rotated_image.get_rect(center=self.pos)
        surface.blit(rotated_image, rect)

class ExplosionCore:
    """The central expanding fireball of the explosion."""
    def __init__(self, pos):
        self.pos = pos
        self.radius = 0
        self.alpha = 255
        self.color = CORE_START_COLOR

    def update(self, progress): # Progress is 0.0 to 1.0
        self.radius = CORE_MAX_RADIUS * math.sin(progress * math.pi) # Smooth expansion and contraction
        self.alpha = max(0, min(255, 255 * (1 - progress)))
        
        # Interpolate color from start to end
        r = CORE_START_COLOR[0] + (CORE_END_COLOR[0] - CORE_START_COLOR[0]) * progress
        g = CORE_START_COLOR[1] + (CORE_END_COLOR[1] - CORE_START_COLOR[1]) * progress
        b = CORE_START_COLOR[2] + (CORE_END_COLOR[2] - CORE_START_COLOR[2]) * progress
        self.color = (r, g, b)

    def draw(self, surface):
        if self.alpha > 0:
            temp_surface = pygame.Surface((self.radius * 2, self.radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(temp_surface, (*self.color, int(self.alpha)), (self.radius, self.radius), self.radius)
            surface.blit(temp_surface, (self.pos[0] - self.radius, self.pos[1] - self.radius), special_flags=pygame.BLEND_RGBA_ADD)

class MiniExplosion:
    """A small, short-lived explosion for localized damage effects."""
    def __init__(self, pos):
        self.pos = pos
        self.radius = 0
        self.alpha = 255
        self.timer = 0

    def update(self):
        self.timer += 1
        progress = self.timer / MINI_EXPLOSION_DURATION
        if progress >= 1.0:
            self.alpha = 0 # Mark for removal
            return

        self.radius = MINI_EXPLOSION_MAX_RADIUS * math.sin(progress * math.pi)
        self.alpha = max(0, min(255, 255 * (1 - progress)))

    def draw(self, surface):
        if self.alpha > 0:
            temp_surface = pygame.Surface((self.radius * 2, self.radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(temp_surface, (*MINI_EXPLOSION_COLOR, int(self.alpha)), (self.radius, self.radius), self.radius)
            surface.blit(temp_surface, (self.pos[0] - self.radius, self.pos[1] - self.radius), special_flags=pygame.BLEND_RGBA_ADD)

class SmokeCloud:
    """An expanding and fading smoke/dust cloud."""
    def __init__(self, pos, initial_direction):
        self.pos = list(pos)
        self.direction = initial_direction # Normalized vector
        self.radius = SMOKE_CLOUD_MIN_RADIUS
        self.alpha = 255
        self.lifetime = SMOKE_CLOUD_LIFETIME
        self.current_lifetime = 0

    def update(self):
        self.current_lifetime += 1
        if self.current_lifetime > self.lifetime:
            self.alpha = 0 # Mark for removal
            return

        progress = self.current_lifetime / self.lifetime
        
        # Expand radius
        self.radius = SMOKE_CLOUD_MIN_RADIUS + (SMOKE_CLOUD_MAX_RADIUS - SMOKE_CLOUD_MIN_RADIUS) * progress

        # Fade out
        self.alpha = max(0, min(255, 255 * (1 - progress)))

        # Move outwards with jitter
        self.pos[0] += self.direction[0] * SMOKE_CLOUD_SPEED_MULTIPLIER + random.uniform(-SMOKE_CLOUD_JITTER, SMOKE_CLOUD_JITTER)
        self.pos[1] += self.direction[1] * SMOKE_CLOUD_SPEED_MULTIPLIER + random.uniform(-SMOKE_CLOUD_JITTER, SMOKE_CLOUD_JITTER)

    def draw(self, surface):
        if self.alpha > 0:
            temp_surface = pygame.Surface((self.radius * 2, self.radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(temp_surface, (SMOKE_CLOUD_COLOR[0], SMOKE_CLOUD_COLOR[1], SMOKE_CLOUD_COLOR[2], int(self.alpha)), (self.radius, self.radius), self.radius)
            surface.blit(temp_surface, (self.pos[0] - self.radius, self.pos[1] - self.radius), special_flags=pygame.BLEND_RGBA_ADD)

class ElectricalArc:
    """A short-lived electrical arc/line effect."""
    def __init__(self, start_pos, end_pos, current_jitter=ARC_JITTER, current_length=ARC_LENGTH, depth=0):
        self.points = []
        self.start_pos = start_pos
        self.end_pos = end_pos
        self.lifetime = ARC_LIFETIME
        self.alpha = 255
        self.current_jitter = current_jitter
        self.current_length = current_length
        self.depth = depth
        self.child_arcs = []
        self._generate_arc_points()

    def _generate_arc_points(self):
        # Simple jagged line generation
        num_segments = 5 # Number of segments in the arc
        current_pos = list(self.start_pos)
        self.points.append(tuple(current_pos))

        dx_segment = (self.end_pos[0] - self.start_pos[0]) / num_segments
        dy_segment = (self.end_pos[1] - self.start_pos[1]) / num_segments

        for i in range(num_segments):
            current_pos[0] += dx_segment + random.uniform(-self.current_jitter, self.current_jitter)
            current_pos[1] += dy_segment + random.uniform(-self.current_jitter, self.current_jitter)
            self.points.append(tuple(current_pos))

            # Branching logic
            if self.depth < MAX_BRANCH_DEPTH and random.random() < BRANCH_CHANCE:
                branch_start = tuple(current_pos)
                branch_angle = random.uniform(0, 2 * math.pi) # Random direction for branch
                branch_end_x = branch_start[0] + math.cos(branch_angle) * (self.current_length * 0.5)
                branch_end_y = branch_start[1] + math.sin(branch_angle) * (self.current_length * 0.5)
                self.child_arcs.append(ElectricalArc(
                    branch_start, (branch_end_x, branch_end_y),
                    self.current_jitter * 0.7, self.current_length * 0.5, self.depth + 1
                ))
        
        # Ensure the arc ends at the desired end_pos, or close to it
        self.points[-1] = self.end_pos

    def update(self):
        self.lifetime -= 1
        self.alpha = max(0, min(255, 255 * (self.lifetime / ARC_LIFETIME)))

        for arc in self.child_arcs:
            arc.update()

    def draw(self, surface):
        if self.alpha > 0 and len(self.points) > 1:
            pygame.draw.lines(surface, (*ARC_COLOR, int(self.alpha)), False, self.points, 1)
        
        for arc in self.child_arcs:
            arc.draw(surface)

class Spark:
    """A small, fast particle emitted from the explosion."""
    def __init__(self, pos):
        self.pos = list(pos)
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(SPARK_SPEED * 0.5, SPARK_SPEED)
        self.velocity = [math.cos(angle) * speed, math.sin(angle) * speed]
        self.lifetime = SPARK_LIFETIME
        self.alpha = 255

    def update(self):
        self.pos[0] += self.velocity[0]
        self.pos[1] += self.velocity[1]
        self.lifetime -= 1
        self.alpha = max(0, min(255, 255 * (self.lifetime / SPARK_LIFETIME)))

    def draw(self, surface):
        if self.lifetime > 0:
            pygame.draw.circle(surface, (*SPARK_COLOR, int(self.alpha)), self.pos, 1)

class TwinklingStar:
    """A small, twinkling star in the background."""
    def __init__(self, screen_width, screen_height):
        self.pos = (random.randint(0, screen_width), random.randint(0, screen_height))
        self.size = random.randint(STAR_MIN_SIZE, STAR_MAX_SIZE)
        self.alpha = random.randint(STAR_MIN_ALPHA, STAR_MAX_ALPHA)
        self.alpha_change = random.choice([-1, 1]) * STAR_ALPHA_CHANGE_SPEED

    def update(self):
        self.alpha += self.alpha_change
        if self.alpha <= STAR_MIN_ALPHA or self.alpha >= STAR_MAX_ALPHA:
            self.alpha_change *= -1 # Reverse twinkling direction

    def draw(self, surface):
        pygame.draw.circle(surface, (255, 255, 255, int(self.alpha)), self.pos, self.size)

class ShipDestructionCinematic:
    """Manages the entire ship destruction animation sequence."""
    def __init__(self, position, ship_image, main_explosion_sound, mini_explosion_sounds, screen_width, screen_height, background_image):
        self.position = list(position)
        self.ship_image = ship_image
        self.state = "SHAKE_1"
        self.state_timer = 0
        self.is_finished = False

        self.ship_drift_velocity = pygame.math.Vector2(random.uniform(-1.0, 1.0), random.uniform(-1.0, 1.0))
        self.ship_angular_velocity = random.uniform(-0.5, 0.5)
        self.ship_current_rotation_angle = 0

        self.debris = None
        self.explosion_core = None
        self.sparks = []
        self.mini_explosions = []
        self.electrical_arcs = []
        self.smoke_clouds = [] # New list for smoke clouds
        self.main_explosion_sound = main_explosion_sound # Removed trailing comma
        self.mini_explosion_sounds = mini_explosion_sounds
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.background_image = background_image # Store the background image
        self.shake_1_sounds_played = 0
        self.shake_2_sounds_played = 0

        self.twinkling_stars = []
        for _ in range(NUM_TWINKLING_STARS):
            self.twinkling_stars.append(TwinklingStar(screen_width, screen_height))

    def update(self):
        if self.is_finished:
            return

        self.state_timer += 1
        print(f"State: {self.state}, Timer: {self.state_timer}") # Debug print

        # Update mini-explosions (always active once spawned)
        for mini_exp in self.mini_explosions[:]:
            mini_exp.update()
            if mini_exp.alpha <= 0: # Mini-explosion is done
                self.mini_explosions.remove(mini_exp)

        # Update electrical arcs (always active once spawned)
        for arc in self.electrical_arcs[:]:
            arc.update()
            if arc.alpha <= 0: # Arc is done
                self.electrical_arcs.remove(arc)

        # Update smoke clouds (always active once spawned)
        for cloud in self.smoke_clouds[:]:
            cloud.update()
            if cloud.alpha <= 0: # Cloud is done
                self.smoke_clouds.remove(cloud)

        # Update twinkling stars
        for star in self.twinkling_stars:
            star.update()

        # Spawn electrical arcs continuously
        if self.state_timer % 3 == 0: # Spawn every 3 frames
            num_arcs = random.randint(1, 2)
            for _ in range(num_arcs):
                start_offset_x = random.uniform(-self.ship_image.get_width() / 3, self.ship_image.get_width() / 3)
                start_offset_y = random.uniform(-self.ship_image.get_height() / 3, self.ship_image.get_height() / 3)
                end_offset_x = start_offset_x + random.uniform(-ARC_LENGTH, ARC_LENGTH)
                end_offset_y = start_offset_y + random.uniform(-ARC_LENGTH, ARC_LENGTH)
                start_pos = (self.position[0] + start_offset_x, self.position[1] + start_offset_y)
                end_pos = (self.position[0] + end_offset_x, self.position[1] + end_offset_y)
                self.electrical_arcs.append(ElectricalArc(start_pos, end_pos, ARC_JITTER, ARC_LENGTH, 0))

        # --- State Machine Logic ---
        if self.state == "SHAKE_1":
            self.position[0] += self.ship_drift_velocity.x
            self.position[1] += self.ship_drift_velocity.y
            self.ship_current_rotation_angle += self.ship_angular_velocity

            # Spawn mini-explosions during shake
            if self.state_timer == 5 or self.state_timer == 15: # Play at specific times for distinct sounds
                if self.shake_1_sounds_played < 2:
                    num_mini_explosions = random.randint(2, 4)
                    for _ in range(num_mini_explosions):
                        # Spawn within ship's approximate bounds
                        offset_x = random.uniform(-self.ship_image.get_width() / 4, self.ship_image.get_width() / 4)
                        offset_y = random.uniform(-self.ship_image.get_height() / 4, self.ship_image.get_height() / 4)
                        self.mini_explosions.append(MiniExplosion((self.position[0] + offset_x, self.position[1] + offset_y)))
                    if self.mini_explosion_sounds: # Play sound for mini-explosion
                        random.choice(self.mini_explosion_sounds).play()
                        self.shake_1_sounds_played += 1
            
            # Spawn electrical arcs during shake
            if self.state_timer % 3 == 0: # Spawn every 3 frames
                num_arcs = random.randint(1, 2)
                for _ in range(num_arcs):
                    start_offset_x = random.uniform(-self.ship_image.get_width() / 3, self.ship_image.get_width() / 3)
                    start_offset_y = random.uniform(-self.ship_image.get_height() / 3, self.ship_image.get_height() / 3)
                    end_offset_x = start_offset_x + random.uniform(-ARC_LENGTH, ARC_LENGTH)
                    end_offset_y = start_offset_y + random.uniform(-ARC_LENGTH, ARC_LENGTH)
                    start_pos = (self.position[0] + start_offset_x, self.position[1] + start_offset_y)
                    end_pos = (self.position[0] + end_offset_x, self.position[1] + end_offset_y)
                    self.electrical_arcs.append(ElectricalArc(start_pos, end_pos, ARC_JITTER, ARC_LENGTH, 0))

            if self.state_timer >= SHAKE_1_DURATION:
                self.state = "DELAY_1"
                self.state_timer = 0
                print("Transition to DELAY_1") # Debug print

        elif self.state == "DELAY_1":
            self.position[0] += self.ship_drift_velocity.x
            self.position[1] += self.ship_drift_velocity.y
            self.ship_current_rotation_angle += self.ship_angular_velocity

            if self.state_timer >= DELAY_1_DURATION:
                self.state = "SHAKE_2"
                self.state_timer = 0
                print("Transition to SHAKE_2") # Debug print

        elif self.state == "SHAKE_2":
            self.position[0] += self.ship_drift_velocity.x
            self.position[1] += self.ship_drift_velocity.y
            self.ship_current_rotation_angle += self.ship_angular_velocity

            # Spawn mini-explosions during shake
            if self.state_timer == 5 or self.state_timer == 15: # Play at specific times for distinct sounds
                if self.shake_2_sounds_played < 2:
                    num_mini_explosions = random.randint(2, 4)
                    for _ in range(num_mini_explosions):
                        offset_x = random.uniform(-self.ship_image.get_width() / 4, self.ship_image.get_width() / 4)
                        offset_y = random.uniform(-self.ship_image.get_height() / 4, self.ship_image.get_height() / 4)
                        self.mini_explosions.append(MiniExplosion((self.position[0] + offset_x, self.position[1] + offset_y)))
                    if self.mini_explosion_sounds: # Play sound for mini-explosion
                        random.choice(self.mini_explosion_sounds).play()
                        self.shake_2_sounds_played += 1

            # Spawn electrical arcs during shake
            if self.state_timer % 3 == 0: # Spawn every 3 frames
                num_arcs = random.randint(1, 2)
                for _ in range(num_arcs):
                    start_offset_x = random.uniform(-self.ship_image.get_width() / 3, self.ship_image.get_width() / 3)
                    start_offset_y = random.uniform(-self.ship_image.get_height() / 3, self.ship_image.get_height() / 3)
                    end_offset_x = start_offset_x + random.uniform(-ARC_LENGTH, ARC_LENGTH)
                    end_offset_y = start_offset_y + random.uniform(-ARC_LENGTH, ARC_LENGTH)
                    start_pos = (self.position[0] + start_offset_x, self.position[1] + start_offset_y)
                    end_pos = (self.position[0] + end_offset_x, self.position[1] + end_offset_y)
                    self.electrical_arcs.append(ElectricalArc(start_pos, end_pos, ARC_JITTER, ARC_LENGTH, 0))

            if self.state_timer >= SHAKE_2_DURATION:
                self.state = "DELAY_2"
                self.state_timer = 0
                print("Transition to DELAY_2") # Debug print

        elif self.state == "DELAY_2":
            self.position[0] += self.ship_drift_velocity.x
            self.position[1] += self.ship_drift_velocity.y
            self.ship_current_rotation_angle += self.ship_angular_velocity

            if self.state_timer >= DELAY_2_DURATION:
                self.state = "INITIAL_FLASH"
                self.state_timer = 0
                print("Transition to INITIAL_FLASH") # Debug print

        elif self.state == "INITIAL_FLASH":
            if self.state_timer >= FLASH_DURATION:
                self.state = "FRACTURING"
                self.state_timer = 0
                print("Transition to FRACTURING") # Debug print
                # Create debris at current ship position and rotation
                self.debris = _create_cinematic_debris(self.ship_image, self.position, self.ship_current_rotation_angle)
                self.explosion_core = ExplosionCore(self.position)
                # Play main explosion sound
                if self.main_explosion_sound:
                    self.main_explosion_sound.play()

        elif self.state == "FRACTURING":
            for piece in self.debris:
                piece.pos[0] += piece.velocity[0] * FRACTURE_SPEED
                piece.pos[1] += piece.velocity[1] * FRACTURE_SPEED
            if self.state_timer >= FRACTURE_DURATION:
                self.state = "EXPANDING_CORE"
                self.state_timer = 0
                print("Transition to EXPANDING_CORE") # Debug print
                # Create sparks on expansion
                for _ in range(SPARK_COUNT):
                    self.sparks.append(Spark(self.position))
                # Create smoke clouds on expansion
                for _ in range(SMOKE_CLOUD_COUNT):
                    angle = random.uniform(0, 2 * math.pi)
                    direction = (math.cos(angle), math.sin(angle))
                    self.smoke_clouds.append(SmokeCloud(self.position, direction))

        elif self.state == "EXPANDING_CORE":
            progress = self.state_timer / EXPAND_DURATION
            self.explosion_core.update(progress)
            for spark in self.sparks:
                spark.update()
            # Push debris with the shockwave
            for piece in self.debris:
                piece.update(coasting_drag=1.0) # No drag yet
            if self.state_timer >= EXPAND_DURATION:
                self.state = "COASTING"
                self.state_timer = 0
                print("Transition to COASTING") # Debug print

        elif self.state == "COASTING":
            all_debris_off_screen = True
            screen_rect = pygame.Rect(0, 0, self.screen_width, self.screen_height)
            for piece in self.debris:
                piece.update() # Default update with drag
                if screen_rect.colliderect(piece.image.get_rect(center=piece.pos)):
                    all_debris_off_screen = False
            
            for spark in self.sparks:
                spark.update()
            # The mini-explosions are updated globally now

            if all_debris_off_screen:
                self.is_finished = True # End the animation
                print("Animation Finished") # Debug print

    def draw(self, surface):
        if self.is_finished:
            return

        # --- State-based Drawing ---
        surface.blit(self.background_image, (0, 0)) # Draw the background first
        # Draw twinkling stars in the background
        for star in self.twinkling_stars:
            star.draw(surface)

        if self.state in ["SHAKE_1", "DELAY_1", "SHAKE_2", "DELAY_2", "INITIAL_FLASH"]:
            # Draw the intact ship at its current position and rotation
            rotated_ship_image = pygame.transform.rotate(self.ship_image, self.ship_current_rotation_angle)
            rect = rotated_ship_image.get_rect(center=self.position)
            surface.blit(rotated_ship_image, rect)
            # Draw mini-explosions on top of the ship
            for mini_exp in self.mini_explosions:
                mini_exp.draw(surface)
            # Draw electrical arcs on top of everything else in these states
            for arc in self.electrical_arcs:
                arc.draw(surface)

        elif self.state == "INITIAL_FLASH":
            alpha = 255 * (1 - self.state_timer / FLASH_DURATION)
            flash_surface = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
            flash_surface.fill(FLASH_COLOR) # Fill with RGB, then set alpha
            flash_surface.set_alpha(int(max(0, min(255, alpha)))) # Apply alpha separately
            surface.blit(flash_surface, (0, 0))

        elif self.state == "FRACTURING":
            if self.debris:
                for piece in self.debris:
                    piece.draw(surface)

        elif self.state in ["EXPANDING_CORE", "COASTING"]:
            if self.explosion_core:
                self.explosion_core.draw(surface)
            if self.debris:
                for piece in self.debris:
                    piece.draw(surface)
            for spark in self.sparks:
                spark.draw(surface)
            for mini_exp in self.mini_explosions:
                mini_exp.draw(surface)
            for cloud in self.smoke_clouds:
                cloud.draw(surface)

    def is_done(self):
        return self.is_finished

# --- Helper for Debris Creation (adapted from ship_destruction_module) ---
def _create_cinematic_debris(ship_image, center_pos, ship_rotation_angle):
    debris_list = []

    # 1. Create a rotated version of the ship image
    rotated_ship_image = pygame.transform.rotate(ship_image, ship_rotation_angle)
    rotated_ship_rect = rotated_ship_image.get_rect(center=(ship_image.get_width() / 2, ship_image.get_height() / 2))

    # Create a temporary surface to draw the rotated ship onto, ensuring it's centered
    temp_surface_size = max(rotated_ship_image.get_width(), rotated_ship_image.get_height())
    temp_surface = pygame.Surface((temp_surface_size, temp_surface_size), pygame.SRCALPHA)
    temp_surface.blit(rotated_ship_image, rotated_ship_image.get_rect().topleft)

    img_width, img_height = temp_surface.get_size()
    img_rect = temp_surface.get_rect()
    max_radius = max(img_width, img_height) / 2

    points = []
    # Generate points for triangulation relative to the temp_surface
    points.extend([img_rect.topleft, img_rect.topright, img_rect.bottomleft, img_rect.bottomright])
    points.append(img_rect.center)
    for _ in range(15): # Inner points
        points.append((random.randint(0, img_width), random.randint(0, img_height)))
    for i in range(12): # Outer points
        angle = (2 * math.pi / 12) * i
        distance = random.uniform(max_radius * 0.9, max_radius * 1.1)
        points.append((img_rect.centerx + distance * math.cos(angle), img_rect.centery + distance * math.sin(angle)))

    try:
        tri = Delaunay(np.array(points))
    except Exception:
        return [] # Failed to create debris

    for simplex in tri.simplices:
        triangle_points = [tuple(points[i]) for i in simplex]
        min_x = min(p[0] for p in triangle_points)
        max_x = max(p[0] for p in triangle_points)
        min_y = min(p[1] for p in triangle_points)
        max_y = max(p[1] for p in triangle_points)
        
        min_x, max_x = max(0, min_x), min(img_width, max_x)
        min_y, max_y = max(0, min_y), min(img_height, max_y)

        bbox_width = max_x - min_x
        bbox_height = max_y - min_y

        if bbox_width < 1 or bbox_height < 1: continue

        # Crop from the rotated_ship_image (or temp_surface)
        cropped_part = pygame.Surface((bbox_width, bbox_height), pygame.SRCALPHA)
        cropped_part.blit(temp_surface, (0, 0), area=pygame.Rect(min_x, min_y, bbox_width, bbox_height))

        mask = pygame.Surface((bbox_width, bbox_height), pygame.SRCALPHA)
        translated_points = [(p[0] - min_x, p[1] - min_y) for p in triangle_points]
        pygame.draw.polygon(mask, (255, 255, 255, 255), translated_points)
        cropped_part.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

        # Calculate initial position relative to the center of the *original* ship image
        # This is the key: we want the debris to appear at the ship's world position
        piece_center_x_relative_to_temp_surface = min_x + bbox_width / 2
        piece_center_y_relative_to_temp_surface = min_y + bbox_height / 2

        # The initial_pos is simply the piece's center on the temp_surface, offset by the ship's world position
        initial_pos = (center_pos[0] + (piece_center_x_relative_to_temp_surface - img_width / 2),
                       center_pos[1] + (piece_center_y_relative_to_temp_surface - img_height / 2))

        # Calculate debris angle relative to the piece's position on the *rotated* ship
        debris_angle_relative = math.atan2(piece_center_y_relative_to_temp_surface - img_rect.centery, piece_center_x_relative_to_temp_surface - img_rect.centerx)
        
        # The debris burst direction is relative to the piece's position on the rotated ship
        debris_speed = random.uniform(DEBRIS_MIN_SPEED, DEBRIS_MAX_SPEED)
        velocity = [math.cos(debris_angle_relative) * debris_speed, math.sin(debris_angle_relative) * debris_speed]
        rotation_speed = random.uniform(DEBRIS_MIN_ROTATION, DEBRIS_MAX_ROTATION)

        debris_list.append(CinematicDebris(cropped_part, initial_pos, velocity, rotation_speed))

    return debris_list

# --- Standalone Test Environment ---
if __name__ == '__main__':
    pygame.init()

    SCREEN_WIDTH = 1000
    SCREEN_HEIGHT = 800
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Ship Destruction Cinematic Test")
    clock = pygame.time.Clock()
    font = pygame.font.Font(None, 28)

    ASSET_PATH = "assets"
    SHIP_IMAGE_NAME = "ship01_bigger.png"

    try:
        pygame.mixer.init()
        ship_image_path = os.path.join(ASSET_PATH, SHIP_IMAGE_NAME)
        ship_image = pygame.image.load(ship_image_path).convert_alpha()
        full_background_image = pygame.image.load(os.path.join(ASSET_PATH, 'Nebula.png')).convert()
        
        # Create a random 250x200 slice and scale it up to fill the screen
        bg_width, bg_height = full_background_image.get_size()
        slice_width = SCREEN_WIDTH // 4
        slice_height = SCREEN_HEIGHT // 4

        if bg_width > slice_width and bg_height > slice_height:
            max_x = bg_width - slice_width
            max_y = bg_height - slice_height
            crop_x = random.randint(0, max_x)
            crop_y = random.randint(0, max_y)
            # Take the smaller slice
            small_slice = full_background_image.subsurface(pygame.Rect(crop_x, crop_y, slice_width, slice_height))
            # Scale it up to fill the screen
            background_slice = pygame.transform.scale(small_slice, (SCREEN_WIDTH, SCREEN_HEIGHT))
        else:
            # Fallback if the original image is too small
            background_slice = pygame.transform.scale(full_background_image, (SCREEN_WIDTH, SCREEN_HEIGHT))

        # Load explosion sounds
        main_explosion_sound = pygame.mixer.Sound(os.path.join(ASSET_PATH, "explosion01.mp3"))
        main_explosion_sound.set_volume(0.8) # Main explosion is louder

        mini_explosion_sounds = [
            pygame.mixer.Sound(os.path.join(ASSET_PATH, "explosion02.mp3")),
            pygame.mixer.Sound(os.path.join(ASSET_PATH, "explosion03.mp3")),
            pygame.mixer.Sound(os.path.join(ASSET_PATH, "explosion04.mp3"))
        ]
        for sound in mini_explosion_sounds:
            sound.set_volume(0.2) # Mini explosions are quieter

    except pygame.error as e:
        print(f"Error loading image or sound: {e}")
        pygame.quit()
        sys.exit()

    animation = None

    def start_animation():
        global animation
        animation_start_pos = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
        animation = ShipDestructionCinematic(animation_start_pos, ship_image, main_explosion_sound, mini_explosion_sounds)

    start_animation()

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    start_animation()

        screen.blit(background_slice, (0, 0))

        if animation:
            animation.update()

            # Handle screen shake
            shake_offset = [0, 0]
            if animation.state in ["SHAKE_1", "SHAKE_2", "INITIAL_FLASH"]:
                shake_offset[0] = random.randint(-SHAKE_INTENSITY, SHAKE_INTENSITY)
                shake_offset[1] = random.randint(-SHAKE_INTENSITY, SHAKE_INTENSITY)
            
            # Create a temporary surface to draw the animation on
            animation_surface = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
            animation.draw(animation_surface)
            screen.blit(animation_surface, shake_offset)

            if animation.is_done():
                text_surf = font.render("Animation finished. Press SPACE to restart.", True, (255, 255, 255))
                screen.blit(text_surf, (10, 10))

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
    sys.exit()
