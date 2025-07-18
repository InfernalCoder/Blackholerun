import pygame
import math
import random
import sys
import json

from asteroid_module import Asteroid, load_asteroid_textures, MIN_OUTER_RADIUS, MAX_OUTER_RADIUS, ASTEROID_COLORS
from ball_lightning_module import BallLightning
from player_module import Ship
from game_state_module import GameStateManager
from particle_module import SuckingParticleSystem, BoostParticleSystem, PowerUpParticleSystem, ExplosionParticleSystem
from ball_lightning_mine_module import BallLightningMine
from ship_destruction_module import create_ship_debris
from crystal_module import Crystal, load_crystal_texture

import os

# --- Asset Path ---
ASSET_PATH = "assets"

# --- Helper functions (can be outside the class) ---
def check_collision(obj1_radius, obj1_x, obj1_y, obj2_radius, obj2_x, obj2_y):
    distance_squared = (obj1_x - obj2_x)**2 + (obj1_y - obj2_y)**2
    radii_sum_squared = (obj1_radius + obj2_radius)**2
    return distance_squared < radii_sum_squared

def save_final_score(player_name, final_score):
    score_entry = {
        'name': player_name,
        'score': int(final_score),
        'timestamp': pygame.time.get_ticks()
    }
    high_scores = []
    try:
        with open(os.path.join(ASSET_PATH, 'highscores.json'), 'r') as f:
            high_scores = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        high_scores = []
    high_scores.append(score_entry)
    high_scores.sort(key=lambda x: x['score'], reverse=True)
    try:
        with open(os.path.join(ASSET_PATH, 'highscores.json'), 'w') as f:
            json.dump(high_scores, f, indent=4)
        print("Score saved successfully!")
    except IOError as e:
        print(f"Error saving scores: {e}")

def load_high_scores():
    try:
        with open(os.path.join(ASSET_PATH, 'highscores.json'), 'r') as f:
            scores = json.load(f)
            print(f"Loaded high scores: {scores}")
            return scores
    except (FileNotFoundError, json.JSONDecodeError):
        print("No highscores.json found or file is empty/corrupt. Returning empty list.")
        return []
    except IOError as e:
        print(f"Error loading scores: {e}")
        return []

class Game:
    def __init__(self):
        pygame.init()
        pygame.mixer.init()

        self.original_screen_width = 1000
        self.original_screen_height = 800
        self.screen = pygame.display.set_mode((self.original_screen_width, self.original_screen_height), pygame.RESIZABLE)
        self.game_surface = pygame.Surface((self.original_screen_width, self.original_screen_height))
        self.screen_width = self.original_screen_width # Current screen width
        self.screen_height = self.original_screen_height # Current screen height
        self.aspect_ratio = self.original_screen_width / self.original_screen_height
        self.scale_factor = 1.0
        self.offset_x = 0
        self.offset_y = 0

        # Initial resize calculation based on actual window size
        current_w, current_h = self.screen.get_size()
        current_aspect_ratio = current_w / current_h
        if current_aspect_ratio > self.aspect_ratio: # Wider than original
            self.scale_factor = current_h / self.original_screen_height
            self.offset_x = (current_w - int(self.original_screen_width * self.scale_factor)) // 2
            self.offset_y = 0
        else: # Taller than original or same aspect ratio
            self.scale_factor = current_w / self.original_screen_width
            self.offset_y = (current_h - int(self.original_screen_height * self.scale_factor)) // 2
            self.offset_x = 0

        # Camera and Slow-motion
        self.slow_motion_factor = 1.0
        self.zoom_level = 1.0
        self.zoom_target = (0, 0)

        pygame.display.set_caption("Black Hole Run")

        self.clock = pygame.time.Clock()
        self.fps = 120

        self.load_assets()
        self.initialize_game_objects()
        self.initialize_ui_elements()
        
        self.state_manager = GameStateManager("SPLASH", self)

    def load_assets(self):
        load_asteroid_textures()
        load_crystal_texture()
        print("Asteroid textures loaded.")
        self.ship_image_orig = pygame.image.load(os.path.join(ASSET_PATH, 'ship01.png')).convert_alpha()
        self.ship_debris_image = pygame.image.load(os.path.join(ASSET_PATH, 'ship01_big.png')).convert_alpha()
        self.background_image = pygame.image.load(os.path.join(ASSET_PATH, 'Nebula.png')).convert()
        self.background_image = pygame.transform.scale(self.background_image, (self.original_screen_width, self.original_screen_height))
        self.second_background_image = pygame.image.load(os.path.join(ASSET_PATH, 'testrun.png')).convert_alpha()
        self.second_background_image = pygame.transform.scale(self.second_background_image, (self.original_screen_width // 8, self.original_screen_height // 8))
        self.second_bg_x = random.randint(0, self.screen_width - self.second_background_image.get_width())
        self.second_bg_y = random.randint(0, self.screen_height - self.second_background_image.get_height())
        self.splash_background_image = pygame.image.load(os.path.join(ASSET_PATH, 'BHRTitleScreen.png')).convert()
        self.splash_background_image = pygame.transform.scale(self.splash_background_image, (self.original_screen_width, self.original_screen_height))
        self.asteroid_splash_image = pygame.image.load(os.path.join(ASSET_PATH, 'AsteroidSplash.png')).convert_alpha()
        width = self.asteroid_splash_image.get_width()
        height = self.asteroid_splash_image.get_height()
        new_width = int(width * 0.8)
        new_height = int(height * 0.8)
        self.asteroid_splash_image = pygame.transform.scale(self.asteroid_splash_image, (new_width, new_height))
        self.game_over_background_image = pygame.image.load(os.path.join(ASSET_PATH, 'ballLightningSplash.png')).convert_alpha()
        width = self.game_over_background_image.get_width()
        height = self.game_over_background_image.get_height()
        new_width = int(width * 0.8)
        new_height = int(height * 0.8)
        self.game_over_background_image = pygame.transform.scale(self.game_over_background_image, (new_width, new_height))
        self.escaped_splash_image = pygame.image.load(os.path.join(ASSET_PATH, 'escaped_splash.png')).convert()
        self.escaped_splash_image = pygame.transform.scale(self.escaped_splash_image, (self.original_screen_width, self.original_screen_height))
        print("Escaped splash image loaded.")
        try:
            pygame.mixer.music.load(os.path.join(ASSET_PATH, "stellar_thrills.mp3"))
            pygame.mixer.music.play(-1)
            pygame.mixer.music.set_volume(0.5)
        except pygame.error as e:
            print(f"Error loading or playing music: {e}")

    def initialize_game_objects(self):
        self.player_ship = Ship(self.screen_width, self.screen_height, self.ship_image_orig)
        self.following_charge = FollowingCharge()
        
        # Create three layers of stars for parallax effect
        num_stars_per_layer = 1000 // 3
        self.stars = []
        # Layer 1: Fastest (original speed)
        self.stars.extend([Star(self.original_screen_width, self.original_screen_height, 1.0) for _ in range(num_stars_per_layer)])
        # Layer 2: Slower
        self.stars.extend([Star(self.original_screen_width, self.original_screen_height, 0.5) for _ in range(num_stars_per_layer)])
        # Layer 3: Very Slowest
        self.stars.extend([Star(self.original_screen_width, self.original_screen_height, 0.2) for _ in range(1000 - 2 * num_stars_per_layer)]) # Ensure total is 1000

        self.speed_boosts = []
        self.power_ups = []
        self.obstacles = []
        self.particle_effects = []
        self.ship_debris = []
        self.reset_game_variables()

    def initialize_ui_elements(self):
        # Font path
        font_path = os.path.join(ASSET_PATH, 'font', 'Bladerounded-Regular.ttf')

        # Fonts
        self.title_font = pygame.font.Font(font_path, 60)
        self.start_font = pygame.font.Font(font_path, 58)
        self.menu_item_font = pygame.font.Font(font_path, 30)
        self.game_over_font_large = pygame.font.Font(font_path, 80)
        self.game_over_font_small = pygame.font.Font(font_path, 28)
        self.escaped_font_large = pygame.font.Font(font_path, 60)
        self.escaped_font_small = pygame.font.Font(font_path, 28)
        self.escaped_font = pygame.font.Font(font_path, 38)
        self.timer_font = pygame.font.Font(font_path, 24)
        self.dilation_font = pygame.font.Font(font_path, 24)
        self.how_to_play_font = pygame.font.Font(font_path, 20)

        # Colors
        self.light_green = (144, 238, 144)
        self.dark_green = (0, 100, 0)
        self.white = (255, 255, 255)
        self.red = (255, 0, 0)
        self.black = (0, 0, 0)
        self.dark_purple = (30, 0, 60)
        self.track_color = (50, 50, 50)
        self.speed_boost_color = (0, 255, 0)

        # UI Text Renderings
        self.title_text_render = self.title_font.render("BLACK HOLE RUN COMMENCING!", True, self.light_green)
        self.title_rect = self.title_text_render.get_rect(center=(self.original_screen_width // 2, self.original_screen_height // 7))
        self.start_text = self.start_font.render("press any key to start", True, self.light_green)
        self.start_rect = self.start_text.get_rect(center=(self.original_screen_width // 2, self.original_screen_height // 4.5))
        self.score_text = self.start_font.render("press h for High Scores", True, self.light_green)
        self.score_rect = self.score_text.get_rect(center=(self.original_screen_width // 2, self.original_screen_height // 3.5))
        self.destroyed_text = self.game_over_font_large.render("YOU WERE DESTROYED", True, self.red)
        self.destroyed_rect = self.destroyed_text.get_rect(center=(self.original_screen_width // 2, self.original_screen_height // 3))
        self.restart_text = self.game_over_font_small.render("Press 'ENTER' to try again", True, self.light_green)
        self.restart_rect = self.restart_text.get_rect(center=(self.original_screen_width // 2, self.original_screen_height // 2))
        self.quit_text = self.game_over_font_small.render("Press 'Q' to quit", True, self.light_green)
        self.quit_rect = self.quit_text.get_rect(center=(self.original_screen_width // 2, self.original_screen_height * 2 / 3))
        self.escaped_message_text = self.escaped_font_large.render("YOU ESCAPED THE BLACK HOLE!", True, self.light_green)
        self.escaped_rect = self.escaped_message_text.get_rect(center=(self.original_screen_width // 2, self.original_screen_height // 4))
        self.restart_text_escaped = self.escaped_font_small.render("Press 'ENTER' to try again", True, self.light_green)
        self.restart_rect_escaped = self.restart_text_escaped.get_rect(center=(self.original_screen_width // 2, self.original_screen_height // 1.4))
        self.quit_text_escaped = self.escaped_font_small.render("Press 'Q' to quit", True, self.light_green)
        self.quit_rect_escaped = self.quit_text_escaped.get_rect(center=(self.original_screen_width // 2, self.original_screen_height // 1.2))
        self.color_cycle = 0
        self.asteroid_rotation_angle = 0
        self.glow_alpha = 0
        self.glow_direction = 1
        self.glow_speed = 4
        self.max_glow_alpha = 100

        self.menu_asteroid = Asteroid(0, 0, asteroid_type='brown', new_outer_radius=20)
        self.menu_ball_lightning = BallLightning(radius=15, initial_color=(125, 249, 255, 255), pulse_color=(255, 255, 255, 255))
        self.menu_speed_boost_crystal = Crystal(0, 0, base_avg_radius=15)
        self.menu_crystal_large = Crystal(self.original_screen_width // 2, self.original_screen_height // 2, base_avg_radius=250)

        # Jitter effect variables
        self.jitter_timer = random.uniform(0.5, 1.5) * self.fps
        self.jitter_active = False
        self.jitter_sequence = []
        self.jitter_flash_duration = 2 # Duration of each flash in frames
        self.jitter_flash_timer = 0
        self.current_jitter_surface = None

    def reset_game_variables(self):
        pygame.time.set_timer(pygame.USEREVENT + 1, 0) # Disable any lingering game over timers
        self.player_ship.reset()
        self.survival_timer_start_time = pygame.time.get_ticks()
        self.survival_timer = 60 * self.fps
        self.speed_boosts.clear()
        self.power_ups.clear()
        self.obstacles.clear()
        self.particle_effects.clear()
        self.ship_debris.clear()
        self.following_charge.deactivate()
        self.charge_spawn_timer = 0
        self.dilation_score = 0
        self.num_boosts_collected = 0
        self.score_saved_for_current_game = False
        self.player_name_input = ""
        self.name_input_active = False
        self.name_input_cursor_visible = True
        self.name_input_cursor_timer = 0
        self.name_input_max_length = 8
        self.mine_spawn_timer = 0 # Initialize mine spawn timer
        self.mine_spawn_interval = 10 * self.fps # 10 seconds * FPS
        self.escape_rotations_completed = 0
        self.target_rotations = 2 # Number of rotations before accelerating off-screen
        self.initial_escape_angle = 0 # To track full rotations
        self.initial_escape_orbital_radius = 0.0
        self.initial_escape_tangential_speed = 0.0
        self.total_angle_rotated_in_escape = 0.0
        self.electrocuted_timer = 0
        self.electrocuted_duration = 90 # Duration of the electrocution effect in frames

    def on_enter_high_scores_state(self):
        self.current_high_scores = load_high_scores()

    def handle_menu_events(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.state_manager.set_state("SPLASH")

    def handle_splash_screen_events(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_n:
                self.state_manager.set_state("GAME")
                self.reset_game_variables()
            elif event.key == pygame.K_p:
                self.state_manager.set_state("MENU")
            elif event.key == pygame.K_h:
                self.state_manager.set_state("HIGH_SCORES")
            elif event.key == pygame.K_q:
                pygame.quit()
                sys.exit()

    def handle_game_events(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RIGHT:
                self.player_ship.move('right')
            elif event.key == pygame.K_LEFT:
                self.player_ship.move('left')
            elif event.key == pygame.K_SPACE:
                self.player_ship.activate_shield()
        elif event.type == pygame.KEYUP:
            if event.key == pygame.K_SPACE:
                self.player_ship.deactivate_shield()
        elif event.type == pygame.USEREVENT + 1:
            self.state_manager.set_state("GAME_OVER")
            pygame.time.set_timer(pygame.USEREVENT + 1, 0) # Disable the timer

    def handle_end_screen_events(self, event):
        if self.state_manager.get_state() == "ESCAPED_INPUT_NAME":
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    if len(self.player_name_input) > 0:
                        self.save_score_if_needed()
                        self.state_manager.set_state("SPLASH")
                elif event.key == pygame.K_BACKSPACE:
                    self.player_name_input = self.player_name_input[:-1]
                elif event.key == pygame.K_ESCAPE:
                    self.state_manager.set_state("SPLASH")
                else:
                    if len(self.player_name_input) < self.name_input_max_length:
                        self.player_name_input += event.unicode.upper()
        else:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    self.state_manager.set_state("SPLASH")
                elif event.key == pygame.K_q:
                    pygame.quit()
                    sys.exit()

    def run_escaping_update(self):
        # Phase 1: Spinning
        if self.escape_rotations_completed < self.target_rotations:
            # Gradually increase orbital radius during spin
            self.player_ship.orbital_radius += 0.1 # Smaller increment per frame

            # Gradually accelerate during spin
            self.player_ship.base_tangential_speed = min(self.player_ship.max_tangential_speed, self.player_ship.base_tangential_speed + 0.01)
            current_tangential_speed = self.player_ship.base_tangential_speed

            # Update angle
            current_angular_speed = current_tangential_speed / self.player_ship.orbital_radius
            self.player_ship.angle += current_angular_speed
            self.total_angle_rotated_in_escape += current_angular_speed

            # Check for full rotations
            if self.total_angle_rotated_in_escape >= (self.escape_rotations_completed + 1) * 2 * math.pi:
                self.escape_rotations_completed += 1
                print(f"Rotations completed: {self.escape_rotations_completed}")

        # Phase 2: Accelerating off-screen
        else:
            self.player_ship.orbital_radius += 5  # Make it move outwards faster
            self.player_ship.base_tangential_speed += 0.2 # Make it speed up faster

            current_angular_speed = self.player_ship.base_tangential_speed / self.player_ship.orbital_radius
            self.player_ship.angle += current_angular_speed

        # Update ship's x, y based on the new orbital_radius and angle
        self.player_ship.x = self.original_screen_width // 2 + self.player_ship.orbital_radius * math.cos(self.player_ship.angle)
        self.player_ship.y = self.original_screen_height // 2 + self.player_ship.orbital_radius * math.sin(self.player_ship.angle)

        # Update the ship's internal speed attribute (used by stars)
        self.player_ship.speed = current_angular_speed

        # Update stars based on the ship's new speed
        for star in self.stars:
            star.update(self.player_ship.speed)

        # Create an accurate bounding box for the drawn ship
        ship_visual_size = max(self.player_ship.image_orig.get_width(), self.player_ship.image_orig.get_height()) * self.player_ship.display_scale
        ship_rect = pygame.Rect(0, 0, ship_visual_size, ship_visual_size)
        ship_rect.center = (self.player_ship.x, self.player_ship.y)

        # Check if the ship is completely off-screen
        if not self.screen.get_rect().colliderect(ship_rect):
            self.state_manager.set_state("ESCAPED")

    def run_electrocuted_update(self):
        self.electrocuted_timer += 1

        # Shrink the ship and move it towards the black hole
        shrink_factor = 1 - (self.electrocuted_timer / self.electrocuted_duration)
        if shrink_factor < 0: shrink_factor = 0

        self.player_ship.display_scale = 1.7 * shrink_factor

        # Move ship towards black hole center
        dx = (self.original_screen_width // 2) - self.player_ship.x
        dy = (self.original_screen_height // 2) - self.player_ship.y
        distance = math.hypot(dx, dy)
        if distance > 0:
            move_speed = 5 # Adjust how fast it gets sucked in
            self.player_ship.x += (dx / distance) * move_speed
            self.player_ship.y += (dy / distance) * move_speed

        # Generate electrocution particles
        if self.electrocuted_timer % 5 == 0: # Emit particles every few frames
            self.particle_effects.append(SuckingParticleSystem((self.player_ship.x, self.player_ship.y), (125, 249, 255), self)) # Blue/white electricity

        # Transition to GAME_OVER after duration
        if self.electrocuted_timer >= self.electrocuted_duration:
            self.state_manager.set_state("GAME_OVER")

    def handle_high_scores_events(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.state_manager.set_state("SPLASH")

    def run_destruction_update(self):
        # Update debris
        for piece in self.ship_debris[:]:
            piece.update(self.slow_motion_factor)
            if piece.lifetime <= 0:
                self.ship_debris.remove(piece)

        # Update zoom and slow-motion
        self.zoom_level += (3.0 - self.zoom_level) * 0.05 # Smoothly zoom to 3x
        self.slow_motion_factor += (1.0 - self.slow_motion_factor) * 0.05 # Smoothly return to normal speed

        # Transition to GAME_OVER when animation is done
        if not self.ship_debris:
            self.state_manager.set_state("GAME_OVER")

    def run_destruction_draw(self, game_surface):
        # Create a zoomed surface
        zoomed_width = self.original_screen_width / self.zoom_level
        zoomed_height = self.original_screen_height / self.zoom_level
        zoomed_surface = pygame.Surface((zoomed_width, zoomed_height), pygame.SRCALPHA)
        
        # Calculate the camera offset to center the zoom target
        camera_x = self.zoom_target[0] - zoomed_width / 2
        camera_y = self.zoom_target[1] - zoomed_height / 2

        # Draw the game elements onto the zoomed surface, offsetting by the camera position
        zoomed_surface.blit(self.background_image, (-camera_x, -camera_y))
        for star in self.stars:
            star.draw(zoomed_surface, camera_x, camera_y)
        self.draw_tracks(zoomed_surface, camera_x, camera_y)
        self.draw_black_hole(zoomed_surface, camera_x, camera_y)
        for piece in self.ship_debris:
            piece.draw(zoomed_surface, camera_x, camera_y)
        for effect in self.particle_effects:
            effect.draw(zoomed_surface, camera_x, camera_y)

        # Scale the zoomed surface to the screen and draw it
        scaled_zoomed_surface = pygame.transform.scale(zoomed_surface, (self.original_screen_width, self.original_screen_height))
        game_surface.blit(scaled_zoomed_surface, (0,0))


    def run_electrocuted_draw(self, game_surface):
        game_surface.fill(self.dark_purple) # Clear game_surface
        for star in self.stars:
            star.draw(game_surface)
        self.draw_tracks(game_surface)
        self.draw_black_hole(game_surface)
        self.player_ship.draw(game_surface) # Draw the shrinking ship
        for effect in self.particle_effects:
            effect.draw(game_surface)

    def run_game_update(self):
        # Only update the ship and handle interactions if it's not destroyed
        if not self.player_ship.is_destroyed:
            self.player_ship.update()
            self.handle_dilation()
            self.handle_spawning()
            self.handle_collisions()
            self.survival_timer -= 1
        
        # These should continue to update for ambiance
        for star in self.stars:
            star.update(self.player_ship.speed)
        for boost in self.speed_boosts:
            boost.update()
        for power_up in self.power_ups:
            power_up.update()
        for obstacle in self.obstacles:
            obstacle.update()
        # Remove inactive mines
        self.obstacles = [o for o in self.obstacles if not (isinstance(o, BallLightningMine) and o.state == "done")]
        self.following_charge.update(self.player_ship.x, self.player_ship.y, self.player_ship.orbital_radius, self.player_ship.speed)
        for effect in self.particle_effects:
            effect.update()

        # Update ship debris after it's created
        if self.player_ship.is_destroyed:
            for piece in self.ship_debris[:]:
                piece.update()
                if piece.lifetime <= 0:
                    self.ship_debris.remove(piece)
        
        # Check for destruction condition
        if self.player_ship.current_structure <= 0 and not self.player_ship.is_destroyed:
            self.player_ship.is_destroyed = True
            self.ship_debris = create_ship_debris(self.ship_debris_image, self.player_ship.x, self.player_ship.y)
            self.state_manager.set_state("DESTRUCTION")
            self.zoom_target = (self.player_ship.x, self.player_ship.y)
            self.slow_motion_factor = 0.1 # Start slow-motion
            self.particle_effects.append(ExplosionParticleSystem((self.player_ship.x, self.player_ship.y)))
            pygame.time.set_timer(pygame.USEREVENT + 1, 5000) # 5-second timer

        if self.survival_timer <= 0:
            self.state_manager.set_state("ESCAPING")

    def handle_dilation(self):
        track_dilation_rate = [1, 0.20, 0.10][self.player_ship.track]
        speed_effect = (self.player_ship.base_tangential_speed / self.player_ship.max_tangential_speed)
        speed_influence = [30.0, 10.0, -50.5][self.player_ship.track]
        dilation_modifier = 1.0 + (speed_effect * speed_influence)
        self.dilation_score += track_dilation_rate * dilation_modifier

    def handle_spawning(self):
        # Force BallLightningMine spawn every 10 seconds for testing
        self.mine_spawn_timer += 1
        if self.mine_spawn_timer >= self.mine_spawn_interval:
            self.obstacles.append(BallLightningMine(random.randint(0, 2), self))
            print("  - FORCED Spawning BallLightningMine")
            self.mine_spawn_timer = 0 # Reset timer

        # Original spawning logic (can be commented out or adjusted as needed)
        if not self.speed_boosts and random.random() < 0.01:
            self.speed_boosts.append(SpeedBoost(random.randint(0, 2), self))
        if not self.power_ups and random.random() < 0.002:
            self.power_ups.append(PowerUp(random.randint(0, 2), self))
        if len(self.obstacles) < 5 and random.random() < 0.008: # Overall obstacle spawn chance
            spawn_type_roll = random.random()
            if spawn_type_roll < 0.2: # 20% chance for ExplodingObstacle (relative to 0.008)
                self.obstacles.append(ExplodingObstacle(random.randint(0, 2), self))
            elif spawn_type_roll < 0.2 + 0.02: # 2% chance for BallLightningMine (relative to 0.008)
                # This will now be overridden by the forced spawn for testing
                pass
            else: # Remaining chance for regular Obstacle
                self.obstacles.append(Obstacle(random.randint(0, 2), self))
        self.charge_spawn_timer += 1
        if not self.following_charge.active and self.charge_spawn_timer >= 300:
            self.following_charge.activate()

    def handle_collisions(self):
        # Ship with Speed Boosts
        for boost in self.speed_boosts[:]:
            boost_x = self.original_screen_width // 2 + boost.radius * math.cos(boost.angle)
            boost_y = self.original_screen_height // 2 + boost.radius * math.sin(boost.angle)
            if boost.track == self.player_ship.track and check_collision(self.player_ship.radius, self.player_ship.x, self.player_ship.y, boost.crystal_graphic.base_avg_radius, boost_x, boost_y):
                if self.player_ship.collect_boost():
                    self.num_boosts_collected += 1
                self.speed_boosts.remove(boost)
                self.particle_effects.append(BoostParticleSystem((boost_x, boost_y)))

        # Ship with Power Ups
        for power_up in self.power_ups[:]:
            power_up_x = self.original_screen_width // 2 + power_up.radius * math.cos(power_up.angle)
            power_up_y = self.original_screen_height // 2 + power_up.radius * math.sin(power_up.angle)
            if power_up.track == self.player_ship.track and check_collision(self.player_ship.radius, self.player_ship.x, self.player_ship.y, power_up.powerup_radius, power_up_x, power_up_y):
                self.player_ship.collect_energy(30)
                self.power_ups.remove(power_up)
                self.particle_effects.append(PowerUpParticleSystem((power_up_x, power_up_y)))

        # Ship with Obstacles
        for obstacle in self.obstacles[:]:
            if isinstance(obstacle, BallLightningMine):
                # The mine's explosion logic is self-contained in its own update() method.
                # The main loop will remove it once its state is "done".
                pass
            else:
                obstacle_x = self.original_screen_width // 2 + obstacle.radius * math.cos(obstacle.angle)
                obstacle_y = self.original_screen_height // 2 + obstacle.radius * math.sin(obstacle.angle)
                if obstacle.track == self.player_ship.track and check_collision(self.player_ship.radius, self.player_ship.x, self.player_ship.y, obstacle.obstacle_radius, obstacle_x, obstacle_y):
                    # Get color from the asteroid that was hit and create particles at its location
                    obstacle_color = ASTEROID_COLORS.get(obstacle.asteroid.color_key, self.red)
                    effect_position = (obstacle_x, obstacle_y)

                    if self.player_ship.shield_active:
                        self.player_ship.deactivate_shield()
                        self.obstacles.remove(obstacle)
                        self.particle_effects.append(SuckingParticleSystem(effect_position, obstacle_color, self))
                    else:
                        damage = 10 if isinstance(obstacle, ExplodingObstacle) else 5
                        self.player_ship.take_damage(damage)
                        self.obstacles.remove(obstacle)
                        self.particle_effects.append(SuckingParticleSystem(effect_position, obstacle_color, self))

        # Ship with Following Charge
        if self.following_charge.active:
            if check_collision(self.player_ship.radius, self.player_ship.x, self.player_ship.y, self.following_charge.radius, self.following_charge.position[0], self.following_charge.position[1]):
                if self.player_ship.shield_active:
                    self.following_charge.deactivate()
                    self.charge_spawn_timer = 0
                    self.player_ship.deactivate_shield()
                else:
                    self.state_manager.set_state("ELECTROCUTED")

    def run_menu_draw(self, game_surface):
        game_surface.blit(self.background_image, (0, 0))
        for star in self.stars:
            star.update(0.01)  # Slow constant rotation
            star.draw(game_surface)
        self.asteroid_rotation_angle += 0.05  # Slow rotation speed
        rotated_asteroid = pygame.transform.rotate(self.asteroid_splash_image, self.asteroid_rotation_angle)
        asteroid_rect = rotated_asteroid.get_rect(center=(self.original_screen_width // 2, self.original_screen_height // 2))
        game_surface.blit(rotated_asteroid, asteroid_rect)

        # Draw semi-transparent black box for menu content
        box_width = int(self.original_screen_width * 0.8)
        box_height = int(self.original_screen_height * 0.8) + 60
        box_x = (self.original_screen_width - box_width) // 2
        box_y = self.original_screen_height // 10 # Adjust as needed
        
        alpha_surface = pygame.Surface((box_width, box_height), pygame.SRCALPHA)
        alpha_surface.fill((0, 0, 0, 100)) # Black with 100 alpha (out of 255)
        game_surface.blit(alpha_surface, (box_x, box_y))

        menu_item_y = self.original_screen_height // 9
        item_spacing = 60
        icon_size = 40
        text_offset_x = icon_size + 20
        menu_y_offset = 20
        shadow_color = (0, 0, 0)  # Black shadow
        icon_center_x = self.original_screen_width // 4

        # Speed Boost
        row_center_y = menu_item_y + menu_y_offset
        self.menu_speed_boost_crystal.update()
        boost_icon = self.menu_speed_boost_crystal.get_current_image()
        boost_icon_rect = boost_icon.get_rect(center=(icon_center_x, row_center_y))
        boost_text = self.how_to_play_font.render("Speed Boost: Increases ship speed.", True, self.white)
        boost_text_rect = boost_text.get_rect(midleft=(icon_center_x + text_offset_x, row_center_y))
        shadow_boost_text = self.how_to_play_font.render("Speed Boost: Increases ship speed.", True, shadow_color)
        shadow_boost_text_rect = shadow_boost_text.get_rect(midleft=(boost_text_rect.left + 2, boost_text_rect.centery + 2))
        game_surface.blit(boost_icon, boost_icon_rect)
        game_surface.blit(shadow_boost_text, shadow_boost_text_rect)
        game_surface.blit(boost_text, boost_text_rect)
        menu_item_y += item_spacing

        # Power-Up (Energy)
        row_center_y = menu_item_y + menu_y_offset
        power_up_icon = pygame.Surface((icon_size, icon_size), pygame.SRCALPHA)
        pygame.draw.circle(power_up_icon, (255, 255, 0), (icon_size // 2, icon_size // 2), 10)
        power_up_icon_rect = power_up_icon.get_rect(center=(icon_center_x, row_center_y))
        power_up_text = self.how_to_play_font.render("Energy: Replenishes energy for shields.", True, self.white)
        power_up_text_rect = power_up_text.get_rect(midleft=(icon_center_x + text_offset_x, row_center_y))
        shadow_power_up_text = self.how_to_play_font.render("Energy: Replenishes energy for shields.", True, shadow_color)
        shadow_power_up_text_rect = shadow_power_up_text.get_rect(midleft=(power_up_text_rect.left + 2, power_up_text_rect.centery + 2))
        game_surface.blit(power_up_icon, power_up_icon_rect)
        game_surface.blit(shadow_power_up_text, shadow_power_up_text_rect)
        game_surface.blit(power_up_text, power_up_text_rect)
        menu_item_y += item_spacing

        # Obstacle
        row_center_y = menu_item_y + menu_y_offset
        self.menu_asteroid.update()
        asteroid_icon = self.menu_asteroid.get_current_image()
        asteroid_icon_rect = asteroid_icon.get_rect(center=(icon_center_x, row_center_y))
        obstacle_text = self.how_to_play_font.render("Obstacle: Avoid! Reduces hull integrity.", True, self.white)
        obstacle_text_rect = obstacle_text.get_rect(midleft=(icon_center_x + text_offset_x, row_center_y))
        shadow_obstacle_text = self.how_to_play_font.render("Obstacle: Avoid! Reduces hull integrity.", True, shadow_color)
        shadow_obstacle_text_rect = shadow_obstacle_text.get_rect(midleft=(obstacle_text_rect.left + 2, obstacle_text_rect.centery + 2))
        game_surface.blit(asteroid_icon, asteroid_icon_rect)
        game_surface.blit(shadow_obstacle_text, shadow_obstacle_text_rect)
        game_surface.blit(obstacle_text, obstacle_text_rect)
        menu_item_y += item_spacing

        # Following Charge
        row_center_y = menu_item_y + menu_y_offset
        self.menu_ball_lightning.update()
        charge_icon = self.menu_ball_lightning.get_current_image()
        charge_icon_rect = charge_icon.get_rect(center=(icon_center_x, row_center_y))
        charge_text = self.how_to_play_font.render("Electrical Charge: Chases ship and destroys it.", True, self.white)
        charge_text_rect = charge_text.get_rect(midleft=(icon_center_x + text_offset_x, row_center_y))
        shadow_charge_text = self.how_to_play_font.render("Electrical Charge: Chases ship and destroys it.", True, shadow_color)
        shadow_charge_text_rect = shadow_charge_text.get_rect(midleft=(charge_text_rect.left + 2, charge_text_rect.centery + 2))
        game_surface.blit(charge_icon, charge_icon_rect)
        game_surface.blit(shadow_charge_text, shadow_charge_text_rect)
        game_surface.blit(charge_text, charge_text_rect)
        menu_item_y += item_spacing

        instructions_rect = pygame.Rect(self.original_screen_width // 4, menu_item_y + 40, self.original_screen_width // 2, 100)
        instructions_text = (
        "You are trapped in a black hole!\n"
        "- Steer your ship through the orbital tracks using the LEFT and RIGHT arrow keys.\n"
        "- Collect green Speed Boosts to increase your speed and slightly reduce time dilation.\n"
        "- Gather yellow Energy power-ups to charge your shield. You can activated the shield with SPACE.\n"
        "- Avoid the red Obstacles! The blue Electrical Charge will actively pursue you.\n"
        "- Stay on the outer ring as much as possible to avoid time dilation!\n"
        "- Survive!"
        )
        self.draw_paragraph(game_surface, instructions_text, self.how_to_play_font, self.white, instructions_rect, shadow_color=shadow_color)

    def run_splash_screen_draw(self, game_surface):

        game_surface.blit(self.splash_background_image, (0, 0))

        """shadow_color = (0, 70, 0) # Darker green for shadow

        # New Game
        new_game_text = self.start_font.render("New Game (N)", True, self.light_green)
        new_game_rect = new_game_text.get_rect(center=(self.original_screen_width // 2, self.original_screen_height // 2 - 100))
        shadow_new_game_text = self.start_font.render("New Game (N)", True, shadow_color)
        game_surface.blit(shadow_new_game_text, (new_game_rect.x + 3, new_game_rect.y + 3))
        game_surface.blit(new_game_text, new_game_rect)

        # How to Play
        how_to_play_text = self.start_font.render("How to Play (P)", True, self.light_green)
        how_to_play_rect = how_to_play_text.get_rect(center=(self.original_screen_width // 2, self.original_screen_height // 2 - 30))
        shadow_how_to_play_text = self.start_font.render("How to Play (P)", True, shadow_color)
        game_surface.blit(shadow_how_to_play_text, (how_to_play_rect.x + 3, how_to_play_rect.y + 3))
        game_surface.blit(how_to_play_text, how_to_play_rect)

        # High Scores
        high_scores_text = self.start_font.render("High Scores (H)", True, self.light_green)
        high_scores_rect = high_scores_text.get_rect(center=(self.original_screen_width // 2, self.original_screen_height // 2 + 40))
        shadow_high_scores_text = self.start_font.render("High Scores (H)", True, shadow_color)
        game_surface.blit(shadow_high_scores_text, (high_scores_rect.x + 3, high_scores_rect.y + 3))
        game_surface.blit(high_scores_text, high_scores_rect)

        # Quit Game
        quit_text = self.start_font.render("Quit Game (Q)", True, self.light_green)
        quit_rect = quit_text.get_rect(center=(self.original_screen_width // 2, self.original_screen_height // 2 + 110))
        shadow_quit_text = self.start_font.render("Quit Game (Q)", True, shadow_color)
        game_surface.blit(shadow_quit_text, (quit_rect.x + 3, quit_rect.y + 3))
        game_surface.blit(quit_text, quit_rect) """

    def run_game_draw(self, game_surface):

        game_surface.blit(self.background_image, (0, 0))
        # game_surface.blit(self.second_background_image, (self.second_bg_x, self.second_bg_y)) # Temporarily disabled
        for star in self.stars:
            star.draw(game_surface)
        self.draw_tracks(game_surface)
        self.draw_black_hole(game_surface)
        if not self.player_ship.is_destroyed:
            self.player_ship.draw(game_surface)
        else:
            for piece in self.ship_debris:
                piece.draw(game_surface)
        for boost in self.speed_boosts:
            boost.draw(game_surface)
        for power_up in self.power_ups:
            power_up.draw(game_surface)
        for obstacle in self.obstacles:
            obstacle.draw(game_surface)
        self.following_charge.draw(game_surface)
        for effect in self.particle_effects:
            effect.draw(game_surface)
        self.draw_game_ui(game_surface)

    def draw_game_ui(self, game_surface):
        total_milliseconds = self.survival_timer * 1000 // self.fps
        minutes = total_milliseconds // 60000
        seconds = (total_milliseconds % 60000) // 1000
        milliseconds = (total_milliseconds % 1000) // 10
        timer_text_surface = self.timer_font.render(f"Time: {minutes:02}:{seconds:02}:{milliseconds:02}", True, self.light_green)
        game_surface.blit(timer_text_surface, (40, 40))
        dilation_text_surface = self.dilation_font.render(f"Dilation: {int(self.dilation_score)}", True, self.light_green)
        game_surface.blit(dilation_text_surface, (40, 70))
        energy_text_surface = self.timer_font.render(f"Energy: {int(self.player_ship.current_energy)}", True, self.light_green)
        game_surface.blit(energy_text_surface, (40, 100))
        structure_text_surface = self.timer_font.render(f"Hull Integrity: {int(self.player_ship.current_structure)}", True, self.light_green)
        game_surface.blit(structure_text_surface, (40, 130))

    def run_game_over_draw(self, game_surface):
        game_surface.blit(self.background_image, (0, 0))
        for star in self.stars:
            star.update(0.01)  # Slow constant rotation for the background
            star.draw(game_surface)

        # --- Jitter Effect Logic ---
        self.jitter_timer -= 1
        if self.jitter_timer <= 0 and not self.jitter_active:
            self.jitter_active = True
            self.jitter_sequence = []
            num_flashes = random.randint(6, 12)
            for _ in range(num_flashes):
                scale = random.uniform(0.95, 1.05)
                angle = random.uniform(-5, 5)
                self.jitter_sequence.append((scale, angle))
            self.jitter_flash_timer = self.jitter_flash_duration

        # --- Drawing Logic ---
        img_to_draw = self.game_over_background_image
        if self.jitter_active:
            self.jitter_flash_timer -= 1
            if self.current_jitter_surface is None:
                # Get the next jitter effect from the sequence
                if self.jitter_sequence:
                    scale, angle = self.jitter_sequence.pop(0)
                    # Use rotozoom for combined rotation and scaling
                    self.current_jitter_surface = pygame.transform.rotozoom(self.game_over_background_image, angle, scale)
                else:
                    # Sequence is over
                    self.jitter_active = False
                    self.jitter_timer = random.randint(1, 2) * self.fps
                    self.current_jitter_surface = None

            if self.current_jitter_surface:
                img_to_draw = self.current_jitter_surface

            if self.jitter_flash_timer <= 0:
                # Reset for the next flash in the sequence
                self.current_jitter_surface = None
                self.jitter_flash_timer = self.jitter_flash_duration

        # Center and draw the appropriate image
        img_rect = img_to_draw.get_rect(center=(self.original_screen_width // 2, self.original_screen_height // 2))
        game_surface.blit(img_to_draw, img_rect.topleft)


        # --- Text with Shadows ---
        shadow_color = (0, 0, 0)

        # Destroyed Text
        shadow_destroyed_text = self.game_over_font_large.render("YOU WERE DESTROYED", True, shadow_color)
        game_surface.blit(shadow_destroyed_text, (self.destroyed_rect.x + 3, self.destroyed_rect.y + 3))
        game_surface.blit(self.destroyed_text, self.destroyed_rect)

        # Restart Text
        shadow_restart_text = self.game_over_font_small.render("Press 'ENTER' to try again", True, shadow_color)
        game_surface.blit(shadow_restart_text, (self.restart_rect.x + 3, self.restart_rect.y + 3))
        game_surface.blit(self.restart_text, self.restart_rect)

        # Quit Text
        shadow_quit_text = self.game_over_font_small.render("Press 'Q' to quit", True, shadow_color)
        game_surface.blit(shadow_quit_text, (self.quit_rect.x + 3, self.quit_rect.y + 3))
        game_surface.blit(self.quit_text, self.quit_rect)

    """def run_game_over_draw(self, game_surface):
        game_surface.fill(self.black)
        for star in self.stars:
            star.update(0.01) # Slow constant rotation for the background
            star.draw(game_surface)

        # Center and draw the main image
        img_rect = self.game_over_background_image.get_rect(center=(self.original_screen_width // 2, self.original_screen_height // 2))
        game_surface.blit(self.game_over_background_image, img_rect.topleft)

        # --- Text with Shadows ---
        shadow_color = (0, 0, 0)

        # Destroyed Text
        shadow_destroyed_text = self.game_over_font_large.render("YOU WERE DESTROYED", True, shadow_color)
        game_surface.blit(shadow_destroyed_text, (self.destroyed_rect.x + 3, self.destroyed_rect.y + 3))
        game_surface.blit(self.destroyed_text, self.destroyed_rect)

        # Restart Text
        shadow_restart_text = self.game_over_font_small.render("Press 'ENTER' to try again", True, shadow_color)
        game_surface.blit(shadow_restart_text, (self.restart_rect.x + 3, self.restart_rect.y + 3))
        game_surface.blit(self.restart_text, self.restart_rect)

        # Quit Text
        shadow_quit_text = self.game_over_font_small.render("Press 'Q' to quit", True, shadow_color)
        game_surface.blit(shadow_quit_text, (self.quit_rect.x + 3, self.quit_rect.y + 3))
        game_surface.blit(self.quit_text, self.quit_rect)"""

    def run_escaped_draw(self, game_surface):
        # Calculate final score
        if self.dilation_score > 0:
            processed_dilation = 1
        else:
            processed_dilation = abs(self.dilation_score)
        final_score = processed_dilation * self.num_boosts_collected * 100

        # Determine the high score threshold dynamically
        current_high_scores = load_high_scores()
        if len(current_high_scores) < 10:  # If fewer than 10 scores, any score is a high score
            dynamic_threshold = 0
        else:
            # Get the 10th score (lowest in top 10) and set threshold to 1 above it
            dynamic_threshold = current_high_scores[9]['score'] + 1

        print(f"Final Score: {final_score}, Dynamic Threshold: {dynamic_threshold}")

        # Check if score qualifies for high score entry
        if final_score >= dynamic_threshold:
            self.state_manager.set_state("ESCAPED_INPUT_NAME")
            return # Exit to let the new state handle drawing

        # If not qualifying, just display score and options
        self.save_score_if_needed() # Save score even if not high score, but without name
        game_surface.blit(self.escaped_splash_image, (0, 0))
        # Text with Shadows
        shadow_color = (0, 0, 0) # Black shadow

        # Escaped Message Text
        shadow_escaped_message_text = self.escaped_font_large.render("YOU ESCAPED THE BLACK HOLE!", True, shadow_color)
        game_surface.blit(shadow_escaped_message_text, (self.escaped_rect.x + 3, self.escaped_rect.y + 3))
        game_surface.blit(self.escaped_message_text, self.escaped_rect)

        # Final Score Label
        final_score_label_text = self.escaped_font.render("Final Score:", True, self.light_green)
        final_score_label_rect = final_score_label_text.get_rect(center=(self.original_screen_width // 2 - 100, self.original_screen_height // 2))
        shadow_final_score_label_text = self.escaped_font.render("Final Score:", True, shadow_color)
        game_surface.blit(shadow_final_score_label_text, (final_score_label_rect.x + 3, final_score_label_rect.y + 3))
        game_surface.blit(final_score_label_text, final_score_label_rect)

        # Final Score Value
        final_score_value_text = self.escaped_font.render(f"{int(final_score):,}", True, self.light_green)
        final_score_value_rect = final_score_value_text.get_rect(midleft=(self.original_screen_width // 2 + 40, self.original_screen_height // 2))
        shadow_final_score_value_text = self.escaped_font.render(f"{int(final_score):,}", True, shadow_color)
        game_surface.blit(shadow_final_score_value_text, (final_score_value_rect.x + 3, final_score_value_rect.y + 3))
        game_surface.blit(final_score_value_text, final_score_value_rect)

        # Restart Text
        shadow_restart_text_escaped = self.escaped_font_small.render("Press 'ENTER' to try again", True, shadow_color)
        game_surface.blit(shadow_restart_text_escaped, (self.restart_rect_escaped.x + 3, self.restart_rect_escaped.y + 3))
        game_surface.blit(self.restart_text_escaped, self.restart_rect_escaped)

        # Quit Text
        shadow_quit_text_escaped = self.escaped_font_small.render("Press 'Q' to quit", True, shadow_color)
        game_surface.blit(shadow_quit_text_escaped, (self.quit_rect_escaped.x + 3, self.quit_rect_escaped.y + 3))
        game_surface.blit(self.quit_text_escaped, self.quit_rect_escaped)

    def run_escaped_input_name_draw(self, game_surface):
        game_surface.blit(self.escaped_splash_image, (0, 0))
        # Text with Shadows
        shadow_color = (0, 0, 0) # Black shadow

        # Escaped Message Text
        shadow_escaped_message_text = self.escaped_font_large.render("YOU ESCAPED THE BLACK HOLE!", True, shadow_color)
        game_surface.blit(shadow_escaped_message_text, (self.escaped_rect.x + 3, self.escaped_rect.y + 3))
        game_surface.blit(self.escaped_message_text, self.escaped_rect)

        final_score = (abs(self.dilation_score) if self.dilation_score < 0 else 1) * self.num_boosts_collected * 100

        # Final Score Label
        final_score_label_text = self.escaped_font.render("Final Score:", True, self.light_green)
        final_score_label_rect = final_score_label_text.get_rect(center=(self.original_screen_width // 2 - 100, self.original_screen_height // 2 - 50))
        shadow_final_score_label_text = self.escaped_font.render("Final Score:", True, shadow_color)
        game_surface.blit(shadow_final_score_label_text, (final_score_label_rect.x + 3, final_score_label_rect.y + 3))
        game_surface.blit(final_score_label_text, final_score_label_rect)

        # Final Score Value
        final_score_value_text = self.escaped_font.render(f"{int(final_score):,}", True, self.light_green)
        final_score_value_rect = final_score_value_text.get_rect(midleft=(self.original_screen_width // 2 + 40, self.original_screen_height // 2 - 50))
        shadow_final_score_value_text = self.escaped_font.render(f"{int(final_score):,}", True, shadow_color)
        game_surface.blit(shadow_final_score_value_text, (final_score_value_rect.x + 3, final_score_value_rect.y + 3))
        game_surface.blit(final_score_value_text, final_score_value_rect)

        # Prompt Text
        prompt_text = self.escaped_font_small.render("Enter your name (up to 8 letters):", True, self.white)
        prompt_rect = prompt_text.get_rect(center=(self.original_screen_width // 2, self.original_screen_height // 2 + 50))
        shadow_prompt_text = self.escaped_font_small.render("Enter your name (up to 8 letters):", True, shadow_color)
        game_surface.blit(shadow_prompt_text, (prompt_rect.x + 3, prompt_rect.y + 3))
        game_surface.blit(prompt_text, prompt_rect)

        # Blinking cursor
        self.name_input_cursor_timer += 1
        if self.name_input_cursor_timer % 30 == 0:
            self.name_input_cursor_visible = not self.name_input_cursor_visible

        display_name = self.player_name_input
        if self.name_input_active and self.name_input_cursor_visible:
            display_name += "_"

        # Name Text
        name_text = self.escaped_font.render(display_name, True, self.light_green)
        name_rect = name_text.get_rect(center=(self.original_screen_width // 2, self.original_screen_height // 2 + 100))
        shadow_name_text = self.escaped_font.render(display_name, True, shadow_color)
        game_surface.blit(shadow_name_text, (name_rect.x + 3, name_rect.y + 3))
        game_surface.blit(name_text, name_rect)

        # Instructions Text
        instructions_text = self.escaped_font_small.render("Press ENTER to save, ESC to skip", True, self.white)
        instructions_rect = instructions_text.get_rect(center=(self.original_screen_width // 2, self.original_screen_height // 2 + 150))
        shadow_instructions_text = self.escaped_font_small.render("Press ENTER to save, ESC to skip", True, shadow_color)
        game_surface.blit(shadow_instructions_text, (instructions_rect.x + 3, instructions_rect.y + 3))
        game_surface.blit(instructions_text, instructions_rect)

    def run_high_scores_draw(self, game_surface):
        game_surface.blit(self.background_image, (0, 0))
        for star in self.stars:
            star.update(0.01)  # Slow constant rotation
            star.draw(game_surface)

        # Draw the large crystal in the background
        self.menu_crystal_large.update()
        crystal_image = self.menu_crystal_large.get_current_image()
        crystal_rect = crystal_image.get_rect(center=(self.original_screen_width // 2, self.original_screen_height // 2))
        game_surface.blit(crystal_image, crystal_rect)

        # Draw semi-transparent black box
        box_width = int(self.original_screen_width * 0.6)
        box_height = int(self.original_screen_height * 0.7)
        box_x = (self.original_screen_width - box_width) // 2
        box_y = self.original_screen_height // 8 - 50 # Start slightly above title, moved up by 30 pixels
        
        alpha_surface = pygame.Surface((box_width, box_height), pygame.SRCALPHA)
        alpha_surface.fill((0, 0, 0, 100)) # Black with 100 alpha (out of 255)
        game_surface.blit(alpha_surface, (box_x, box_y))

        high_scores = self.current_high_scores

        title_text = self.title_font.render("HIGH SCORES", True, self.light_green)
        title_rect = title_text.get_rect(center=(self.original_screen_width // 2, self.original_screen_height // 8))
        game_surface.blit(title_text, title_rect)

        y_offset = self.original_screen_height // 4
        if not high_scores:
            no_scores_text = self.menu_item_font.render("No scores yet. Play a game to set one!", True, self.white)
            no_scores_rect = no_scores_text.get_rect(center=(self.original_screen_width // 2, y_offset + 50))
            game_surface.blit(no_scores_text, no_scores_rect)
        else:
            header_name_text = self.escaped_font.render("NAME", True, self.white)
            header_score_text = self.escaped_font.render("SCORE", True, self.white)

            # Calculate positions to center them over their respective columns
            # The score list is centered at original_screen_width // 2
            # The name list is to the left of it, with 15 characters padding
            name_x_pos = (self.original_screen_width // 2) - (header_name_text.get_width() // 2) - (self.menu_item_font.size(" ")[0] * 10) # 10 spaces for padding
            score_x_pos = (self.original_screen_width // 2) + (header_score_text.get_width() // 2) + (self.menu_item_font.size(" ")[0] * 10) # 10 spaces for padding

            game_surface.blit(header_name_text, (name_x_pos, y_offset - 20))
            game_surface.blit(header_score_text, (score_x_pos - header_score_text.get_width(), y_offset - 20)) # Adjust score_x_pos to blit from left
            y_offset += 40

            for i, entry in enumerate(high_scores[:10]): # Display top 10 scores
                player_name = entry.get('name', '---') # Safely get name, default to '---' if not present
                score_line = f"{player_name:<15} {entry['score']:,}"
                score_text = self.menu_item_font.render(score_line, True, self.white)
                score_rect = score_text.get_rect(center=(self.original_screen_width // 2, y_offset + i * 35))
                shadow_score_text = self.menu_item_font.render(score_line, True, (0,0,0)) # Black shadow
                game_surface.blit(shadow_score_text, (score_rect.x + 3, score_rect.y + 3))
                game_surface.blit(score_text, score_rect)
        
        return_text = self.start_font.render("Press ESC to return to Menu", True, self.light_green)
        return_rect = return_text.get_rect(center=(self.original_screen_width // 2, self.original_screen_height * 0.9))
        game_surface.blit(return_text, return_rect)

    def save_score_if_needed(self):
        if not self.score_saved_for_current_game:
            time_survived_ms = pygame.time.get_ticks() - self.survival_timer_start_time
            if self.dilation_score > 0:
                processed_dilation = 1
            else:
                processed_dilation = abs(self.dilation_score)
            final_score = processed_dilation * self.num_boosts_collected * 100
            save_final_score(self.player_name_input, final_score)
            self.score_saved_for_current_game = True

    def draw_paragraph(self, surface, text, font, color, rect, shadow_color=None):
        """Draws a paragraph of text onto a given surface within a specified rectangle."""
        words = text.split('\n')
        lines = []
        for line in words:
            words_in_line = line.split(' ')
            current_line = []
            line_width = 0
            for word in words_in_line:
                word_surface = font.render(word, True, color)
                word_width = word_surface.get_width()
                if line_width + word_width < rect.width:
                    current_line.append(word)
                    line_width += word_width + font.size(" ")[0]
                else:
                    lines.append(" ".join(current_line))
                    current_line = [word]
                    line_width = word_width + font.size(" ")[0]
            lines.append(" ".join(current_line))

        y_offset = rect.top
        line_spacing = 5
        for line in lines:
            if shadow_color:
                shadow_surface = font.render(line, True, shadow_color)
                surface.blit(shadow_surface, (rect.left + 2, y_offset + 2))
            line_surface = font.render(line, True, color)
            surface.blit(line_surface, (rect.left, y_offset))
            y_offset += line_surface.get_height() + line_spacing
            
    def draw_tracks(self, game_surface, camera_x=0, camera_y=0):
        for i in range(3):
            center_radius = self.player_ship.orbital_radius_base + i * self.player_ship.track_width * self.player_ship.track_spacing_multiplier
            inner_radius = center_radius - self.player_ship.track_width // 2
            outer_radius = center_radius + self.player_ship.track_width // 2
            pygame.draw.circle(game_surface, self.track_color, (self.original_screen_width // 2 - camera_x, self.original_screen_height // 2 - camera_y), int(inner_radius), 1)
            pygame.draw.circle(game_surface, self.track_color, (self.original_screen_width // 2 - camera_x, self.original_screen_height // 2 - camera_y), int(outer_radius), 1)

    def draw_black_hole(self, game_surface, camera_x=0, camera_y=0):
        pygame.draw.circle(game_surface, self.black, (self.original_screen_width // 2 - camera_x, self.original_screen_height // 2 - camera_y), 50)

    def run(self):
        while True:
            events = pygame.event.get()
            for event in events:
                if event.type == pygame.VIDEORESIZE:
                    self.screen_width, self.screen_height = event.size
                    self.screen = pygame.display.set_mode((self.screen_width, self.screen_height), pygame.RESIZABLE)
                    current_aspect_ratio = self.screen_width / self.screen_height
                    if current_aspect_ratio > self.aspect_ratio:
                        self.scale_factor = self.screen_height / self.original_screen_height
                        self.offset_x = (self.screen_width - int(self.original_screen_width * self.scale_factor)) // 2
                        self.offset_y = 0
                    else:
                        self.scale_factor = self.screen_width / self.original_screen_width
                        self.offset_y = (self.screen_height - int(self.original_screen_height * self.scale_factor)) // 2
                        self.offset_x = 0
                self.state_manager.handle_events([event]) # Pass individual event to state manager
            
            if self.state_manager.get_state() == "DESTRUCTION":
                self.run_destruction_update()
            else:
                self.state_manager.update()

            if self.state_manager.get_state() == "DESTRUCTION":
                self.run_destruction_draw(self.game_surface)
            else:
                self.state_manager.draw(self.game_surface)

            # Scale the game_surface to the current screen size and blit it
            scaled_surface = pygame.transform.scale(self.game_surface, (int(self.original_screen_width * self.scale_factor), int(self.original_screen_height * self.scale_factor)))
            self.screen.blit(scaled_surface, (self.offset_x, self.offset_y))

            pygame.display.flip()
            self.clock.tick(self.fps)

# --- Entity Classes (Need to be adapted to take the game object) ---
class SpeedBoost:
    def __init__(self, track, game):
        self.game = game
        self.track = track
        self.radius = self.game.player_ship.orbital_radius_base + track * self.game.player_ship.track_width * self.game.player_ship.track_spacing_multiplier
        self.angle = random.uniform(0, 2 * math.pi)
        self.lifetime = random.randint(240, 360)
        self.crystal_graphic = Crystal(0, 0, base_avg_radius=15) # Initialize Crystal graphic

    def draw(self, game_surface, camera_x=0, camera_y=0):
        x = self.game.original_screen_width // 2 + self.radius * math.cos(self.angle) - camera_x
        y = self.game.original_screen_height // 2 + self.radius * math.sin(self.angle) - camera_y
        
        crystal_image = self.crystal_graphic.get_current_image()
        crystal_rect = crystal_image.get_rect(center=(int(round(x)), int(round(y))))
        game_surface.blit(crystal_image, crystal_rect)

    def update(self):
        self.lifetime -= 1
        self.crystal_graphic.update() # Update the crystal graphic

class PowerUp:
    def __init__(self, track, game):
        self.game = game
        self.track = track
        self.radius = self.game.player_ship.orbital_radius_base + track * self.game.player_ship.track_width * self.game.player_ship.track_spacing_multiplier
        self.angle = random.uniform(0, 2 * math.pi)
        self.lifetime = random.randint(180, 300)
        self.crystal_graphic = Crystal(0, 0, base_avg_radius=15)
        self.crystal_graphic.color_key = 'yellow'
        self.crystal_graphic.base_color = CRYSTAL_COLORS[self.crystal_graphic.color_key]
        self.powerup_radius = self.crystal_graphic.base_avg_radius

    def draw(self, game_surface, camera_x=0, camera_y=0):
        x = self.game.original_screen_width // 2 + self.radius * math.cos(self.angle) - camera_x
        y = self.game.original_screen_height // 2 + self.radius * math.sin(self.angle) - camera_y
        
        crystal_image = self.crystal_graphic.get_current_image()
        crystal_rect = crystal_image.get_rect(center=(int(round(x)), int(round(y))))
        game_surface.blit(crystal_image, crystal_rect)

    def update(self):
        self.lifetime -= 1
        self.crystal_graphic.update()

class Obstacle:
    def __init__(self, track, game):
        self.game = game
        self.track = track
        self.target_radius = self.game.player_ship.orbital_radius_base + track * self.game.player_ship.track_width * self.game.player_ship.track_spacing_multiplier
        self.angle = random.uniform(0, 2 * math.pi)
        self.entering_screen = True
        self.entry_speed = random.uniform(5, 10)
        self.orbital_speed = random.uniform(0.001, 0.002) * random.choice([-1, 1])

        if random.random() < 0.5:
            self.radius = random.uniform(0, self.game.player_ship.orbital_radius_base - 50)
        else:
            self.radius = random.uniform(self.target_radius + 100, self.game.screen_width * 0.75)

        initial_asteroid_size = 20
        available_asteroid_types = list(ASTEROID_COLORS.keys())
        if not available_asteroid_types:
            random_asteroid_type = 'brown'
        else:
            random_asteroid_type = random.choice(available_asteroid_types)
            if random_asteroid_type == 'red':
                random_asteroid_type = 'brown'

        self.asteroid = Asteroid(0, 0, asteroid_type=random_asteroid_type, new_outer_radius=initial_asteroid_size)
        self.obstacle_radius = self.asteroid.outer_radius

    def draw(self, game_surface, camera_x=0, camera_y=0):
        x = self.game.original_screen_width // 2 + self.radius * math.cos(self.angle) - camera_x
        y = self.game.original_screen_height // 2 + self.radius * math.sin(self.angle) - camera_y
        self.asteroid.x = x
        self.asteroid.y = y
        asteroid_image = self.asteroid.get_current_image()
        image_rect = asteroid_image.get_rect(center=(int(round(x)), int(round(y))))
        game_surface.blit(asteroid_image, image_rect)

    def update(self):
        if self.entering_screen:
            if self.radius < self.target_radius:
                self.radius += self.entry_speed
                if self.radius >= self.target_radius:
                    self.entering_screen = False
            else:
                self.radius -= self.entry_speed
                if self.radius <= self.target_radius:
                    self.entering_screen = False
        else:
            self.angle += self.orbital_speed
            if self.angle > 2 * math.pi:
                self.angle -= 2 * math.pi
            elif self.angle < 0:
                self.angle += 2 * math.pi
        self.asteroid.update()
        self.asteroid.x = self.game.screen_width // 2 + self.radius * math.cos(self.angle)
        self.asteroid.y = self.game.screen_height // 2 + self.radius * math.sin(self.angle)

class ExplodingObstacle(Obstacle):
    def __init__(self, track, game):
        super().__init__(track, game)
        custom_asteroid_size = 25
        custom_asteroid_type = 'red'
        self.asteroid.recreate_asteroid(
            new_outer_radius=custom_asteroid_size,
            asteroid_type=custom_asteroid_type,
            randomize_all=False
        )
        self.obstacle_radius = self.asteroid.outer_radius
        self.color_bright = (255, 100, 100)
        self.color_dark = self.game.red
        self.glow_speed = 0.05
        self.glow_value = 0
        self.glow_direction = 1
        self.explosion_radius = 180
        self.explosion_duration = 30
        self.exploded = False
        self.explosion_timer = 0
        self.explosion_color = (255, 165, 0)
        self.x = self.calculate_x()
        self.y = self.calculate_y()

    def calculate_x(self):
        return self.game.original_screen_width // 2 + self.radius * math.cos(self.angle)

    def calculate_y(self):
        return self.game.original_screen_height // 2 + self.radius * math.sin(self.angle)

    def update_position(self):
        self.x = self.calculate_x()
        self.y = self.calculate_y()
        self.asteroid.x = self.x
        self.asteroid.y = self.y

    def update_color(self):
        self.glow_value += self.glow_speed * self.glow_direction
        if self.glow_value >= 1:
            self.glow_value = 1
            self.glow_direction = -1
        elif self.glow_value <= 0:
            self.glow_value = 0
            self.glow_direction = 1
        r = int(self.color_bright[0] + (self.color_dark[0] - self.color_bright[0]) * self.glow_value)
        g = int(self.color_bright[1] + (self.color_dark[1] - self.color_bright[1]) * self.glow_value)
        b = int(self.color_bright[2] + (self.color_dark[2] - self.color_bright[2]) * self.glow_value)
        self.color = (r, g, b)

    def draw(self, game_surface, camera_x=0, camera_y=0):
        if self.exploded:
            current_radius = int(round(self.explosion_radius * (self.explosion_timer / self.explosion_duration)))
            pygame.draw.circle(game_surface, self.explosion_color, (int(round(self.x - camera_x)), int(round(self.y - camera_y))), current_radius)
        else:
            super().draw(game_surface, camera_x, camera_y)

    def update(self):
        if not self.exploded:
            super().update()
            self.update_color()
            self.update_position()
        else:
            self.explosion_timer += 1
            if self.explosion_timer >= self.explosion_duration:
                if self in self.game.obstacles:
                    self.game.obstacles.remove(self)

class FollowingCharge:
    def __init__(self):
        self.color = (125, 249, 255)
        self.pulse_color = (255, 255, 255)
        self.radius = 15
        self.initial_position = [500, 400]
        self.position = list(self.initial_position)
        self.base_speed_multiplier = 0.6
        self.speed_increase_rate = 0.0005
        self.current_speed_multiplier = self.base_speed_multiplier
        self.active = False
        self.initial_spawn_speed_multiplier = 0.3
        self.ball_lightning_graphic = BallLightning(
            radius=self.radius,
            initial_color=self.color + (255,),
            pulse_color=self.pulse_color + (255,),
        )

    def activate(self):
        self.active = True
        self.current_speed_multiplier = self.initial_spawn_speed_multiplier
        self.position = list(self.initial_position)

    def deactivate(self):
        self.active = False
        self.position = list(self.initial_position)
        self.current_speed_multiplier = self.base_speed_multiplier

    def update(self, ship_x, ship_y, orbital_radius, ship_angular_speed):
        if self.active:
            player_tangential_speed = ship_angular_speed * orbital_radius
            charge_speed = player_tangential_speed * self.current_speed_multiplier
            self.current_speed_multiplier += self.speed_increase_rate
            dx = ship_x - self.position[0]
            dy = ship_y - self.position[1]
            distance = math.hypot(dx, dy)
            if distance > 0:
                self.position[0] += (dx / distance) * charge_speed
                self.position[1] += (dy / distance) * charge_speed
        self.ball_lightning_graphic.update()

    def draw(self, game_surface, camera_x=0, camera_y=0):
        if self.active:
            self.ball_lightning_graphic.set_position(int(self.position[0]), int(self.position[1]))
            lightning_image = self.ball_lightning_graphic.get_current_image()
            image_rect = lightning_image.get_rect(center=(int(self.position[0] - camera_x), int(self.position[1] - camera_y)))
            game_surface.blit(lightning_image, image_rect)

class Star:
    def __init__(self, screen_width, screen_height, speed_multiplier):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.speed_multiplier = speed_multiplier # New attribute for parallax effect
        self.radius = random.uniform(0, max(self.screen_width, self.screen_height) / 2)
        self.angle = random.uniform(0, 2 * math.pi)
        self.size = random.randint(1, 3)
        self.color = (255, 255, 255)
        self.alpha = random.randint(50, 255)
        self.alpha_change = random.choice([-5, 5])
        self.surface = pygame.Surface((self.size, self.size), pygame.SRCALPHA)
        self.surface.fill(self.color)
        self.surface.set_alpha(self.alpha)

    def update(self, ship_speed):
        angular_speed = -ship_speed * 0.5 * self.speed_multiplier # Apply speed multiplier
        self.angle += angular_speed
        if self.angle > 2 * math.pi:
            self.angle -= 2 * math.pi
        elif self.angle < 0:
            self.angle += 2 * math.pi
        self.alpha += self.alpha_change
        if self.alpha <= 50 or self.alpha >= 255:
            self.alpha_change *= -1
        self.surface.set_alpha(self.alpha)

    def draw(self, game_surface, camera_x=0, camera_y=0):
        x = self.screen_width // 2 + self.radius * math.cos(self.angle) - camera_x
        y = self.screen_height // 2 + self.radius * math.sin(self.angle) - camera_y
        game_surface.blit(self.surface, (int(x - self.size // 2), int(y - self.size // 2)))

if __name__ == "__main__":
    game = Game()
    game.run()
