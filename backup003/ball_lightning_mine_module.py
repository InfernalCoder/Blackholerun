import pygame
import random
import math

from ball_lightning_module import BallLightning
from particle_module import SuckingParticleSystem

# --- Constants for Track Overload Explosion ---
EXPLOSION_ACTIVE_DURATION = 30
EXPLOSION_FADE_DURATION = 60
ARC_LIFESPAN = 45
NEW_ARC_INTERVAL = 5
TRACK_BUFFER = 0.2

# Main Arc Properties
ARC_COUNT = 1
ARC_ANGULAR_LENGTH_RANGE = (math.pi, math.pi * 1.8)
ARC_POINTS_RANGE = (25, 40)
ARC_JITTER_MAGNITUDE_RANGE = (8, 15)
ARC_THICKNESS_RANGE = (2, 4)

# Tendril Properties
TENDRIL_CHANCE = 0.75 # Chance for a point on the main arc to spawn a tendril
TENDRIL_LENGTH_RANGE = (10, 25)
TENDRIL_POINTS_RANGE = (5, 10)
TENDRIL_JITTER_MAGNITUDE = 5
TENDRIL_THICKNESS = 1

LIGHTNING_CORE_COLOR = (255, 255, 255, 255)
LIGHTNING_PULSE_COLOR = (125, 249, 255, 255)

def _generate_lightning_segment(start_point, angle, length, num_points, jitter_magnitude):
    """Generates a single straight segment of lightning."""
    points = [start_point]
    current_pos = list(start_point)
    segment_length = length / num_points

    for _ in range(num_points):
        current_pos[0] += math.cos(angle) * segment_length + random.uniform(-jitter_magnitude, jitter_magnitude)
        current_pos[1] += math.sin(angle) * segment_length + random.uniform(-jitter_magnitude, jitter_magnitude)
        points.append(tuple(current_pos))
    return points

def _generate_lightning_arc_points(center_x, center_y, radius, track_width, start_angle, arc_length, num_points, jitter_magnitude):
    """Generates points for a main arc and its branching tendrils."""
    main_arc_points = []
    tendrils = []
    angle_step = arc_length / num_points

    for i in range(num_points + 1):
        current_angle = start_angle + i * angle_step
        effective_track_width = track_width * (1 - TRACK_BUFFER * 2)
        half_track_width = effective_track_width / 2
        current_radius = radius + random.uniform(-half_track_width, half_track_width)

        jitter_x = random.uniform(-jitter_magnitude, jitter_magnitude)
        jitter_y = random.uniform(-jitter_magnitude, jitter_magnitude)

        x = center_x + current_radius * math.cos(current_angle) + jitter_x
        y = center_y + current_radius * math.sin(current_angle) + jitter_y
        current_point = (x, y)
        main_arc_points.append(current_point)

        if random.random() < TENDRIL_CHANCE:
            tendril_angle = current_angle + random.uniform(-math.pi / 2, math.pi / 2)
            tendril_length = random.uniform(*TENDRIL_LENGTH_RANGE)
            tendril_points_count = random.randint(*TENDRIL_POINTS_RANGE)
            tendril_points = _generate_lightning_segment(current_point, tendril_angle, tendril_length, tendril_points_count, TENDRIL_JITTER_MAGNITUDE)
            tendrils.append(tendril_points)
            
    return main_arc_points, tendrils

class BallLightningMine:
    def __init__(self, track, game):
        self.game = game
        self.track = track
        self.target_radius = self.game.player_ship.orbital_radius_base + track * self.game.player_ship.track_width * self.game.player_ship.track_spacing_multiplier
        self.angle = random.uniform(0, 2 * math.pi)
        self.radius = 0
        self.speed = random.uniform(2, 5)

        self.x = self.game.original_screen_width // 2
        self.y = self.game.original_screen_height // 2

        self.state = "traveling"
        self.charge_timer = 0
        self.charge_duration = 300
        self.explosion_timer = 0
        self.explosion_duration = EXPLOSION_ACTIVE_DURATION + EXPLOSION_FADE_DURATION

        self.ball_lightning_graphic = BallLightning(5, (100, 200, 255, 255), (255, 255, 255, 255), 3)
        self.mine_radius = 15

        self.lightning_arcs = []
        self.new_arc_timer = 0
        
        self.thunder_sounds = [pygame.mixer.Sound("assets/thunder01.mp3"), pygame.mixer.Sound("assets/thunder02.mp3")]
        for sound in self.thunder_sounds:
            sound.set_volume(0.4)
        self.explosion_sound_delay = 500  # half a second in milliseconds
        self.explosion_sound_timer = -1

    def update(self):
        if self.state == "traveling":
            self.radius += self.speed
            if self.radius >= self.target_radius:
                self.radius = self.target_radius
                self.state = "charging"
        
        elif self.state == "charging":
            self.charge_timer += 1
            scale_factor = 1 + (self.charge_timer / self.charge_duration) * 5
            self.ball_lightning_graphic.radius = int(5 * scale_factor)
            base_alpha = 100
            charge_alpha = int(base_alpha + (255 - base_alpha) * (self.charge_timer / self.charge_duration))
            self.ball_lightning_graphic.pulse_color = (255, 255, 255, charge_alpha)
            self.ball_lightning_graphic.core_color = (100, 200, 255, charge_alpha)

            if self.charge_timer >= self.charge_duration:
                self.state = "exploding"
                self.explosion_timer = 0
                self.explosion_sound_timer = pygame.time.get_ticks()

                # --- Trigger Explosion Effects First ---
                self._generate_new_lightning_arcs() # Generate the visual arcs immediately

                # --- Then, Handle Damage and Obstacle Clearing ---
                if self.game.player_ship.track == self.track and not self.game.player_ship.shield_active:
                    self.game.player_ship.take_damage(75)
                    self.game.particle_effects.append(SuckingParticleSystem((self.game.player_ship.x, self.game.player_ship.y), self.game.red, self.game))
                
                # Destroy other obstacles on the same track
                for obstacle in self.game.obstacles[:]:
                    if obstacle is not self and obstacle.track == self.track:
                        if hasattr(obstacle, 'exploded'):
                            obstacle.exploded = True
                        else:
                            if obstacle in self.game.obstacles:
                                self.game.obstacles.remove(obstacle)

        elif self.state == "exploding":
            if self.explosion_sound_timer != -1 and pygame.time.get_ticks() - self.explosion_sound_timer > self.explosion_sound_delay:
                random.choice(self.thunder_sounds).play()
                self.explosion_sound_timer = -1
            self.explosion_timer += 1
            self.new_arc_timer += 1

            for arc_data in self.lightning_arcs:
                arc_data['lifespan'] -= 1
            self.lightning_arcs = [arc for arc in self.lightning_arcs if arc['lifespan'] > 0]

            if self.explosion_timer < EXPLOSION_ACTIVE_DURATION and self.new_arc_timer >= NEW_ARC_INTERVAL:
                self.new_arc_timer = 0
                self._generate_new_lightning_arcs()

            if self.explosion_timer >= self.explosion_duration:
                self.state = "done"

        self.ball_lightning_graphic.update()
        self.x = self.game.original_screen_width // 2 + self.radius * math.cos(self.angle)
        self.y = self.game.original_screen_height // 2 + self.radius * math.sin(self.angle)
        self.ball_lightning_graphic.set_position(self.x, self.y)

    def _generate_new_lightning_arcs(self):
        track_center_radius = self.game.player_ship.orbital_radius_base + self.track * self.game.player_ship.track_width * self.game.player_ship.track_spacing_multiplier
        
        for _ in range(ARC_COUNT):
            arc_length = random.uniform(*ARC_ANGULAR_LENGTH_RANGE)
            main_arc_points, tendrils = _generate_lightning_arc_points(
                self.game.original_screen_width // 2, self.game.original_screen_height // 2, track_center_radius,
                self.game.player_ship.track_width, random.uniform(0, 2 * math.pi),
                arc_length, random.randint(*ARC_POINTS_RANGE), random.uniform(*ARC_JITTER_MAGNITUDE_RANGE)
            )
            self.lightning_arcs.append({
                'points': main_arc_points,
                'tendrils': tendrils,
                'lifespan': ARC_LIFESPAN,
                'max_lifespan': ARC_LIFESPAN,
                'thickness': random.randint(*ARC_THICKNESS_RANGE)
            })

    def draw(self, game_surface):
        if self.state == "traveling" or self.state == "charging":
            lightning_image = self.ball_lightning_graphic.get_current_image()
            image_rect = lightning_image.get_rect(center=(int(self.x), int(self.y)))
            game_surface.blit(lightning_image, image_rect)
        
        elif self.state == "exploding":
            for arc_data in self.lightning_arcs:
                progress = arc_data['lifespan'] / arc_data['max_lifespan']
                alpha = 255 * (1 - (1 - progress)**2)

                pulse_factor = (math.sin(self.explosion_timer * 0.5 + arc_data['lifespan']) + 1) / 2
                r = LIGHTNING_CORE_COLOR[0] + (LIGHTNING_PULSE_COLOR[0] - LIGHTNING_CORE_COLOR[0]) * pulse_factor
                g = LIGHTNING_CORE_COLOR[1] + (LIGHTNING_PULSE_COLOR[1] - LIGHTNING_CORE_COLOR[1]) * pulse_factor
                b = LIGHTNING_CORE_COLOR[2] + (LIGHTNING_PULSE_COLOR[2] - LIGHTNING_CORE_COLOR[2]) * pulse_factor
                core_color = (r, g, b, alpha)

                if len(arc_data['points']) > 1:
                    pygame.draw.lines(game_surface, core_color, False, arc_data['points'], arc_data['thickness'])
                
                for tendril in arc_data['tendrils']:
                    if len(tendril) > 1:
                        pygame.draw.lines(game_surface, core_color, False, tendril, TENDRIL_THICKNESS)

# --- Standalone Test Block ---
if __name__ == "__main__":
    pygame.init()

    SCREEN_WIDTH = 1000
    SCREEN_HEIGHT = 800
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Ball Lightning Mine Test")

    clock = pygame.time.Clock()
    FPS = 60

    class MockPlayerShip:
        def __init__(self, screen_width, screen_height):
            self.orbital_radius_base = 150
            self.track_width = 60
            self.track_spacing_multiplier = 2.5
            self.track = 1
            self.shield_active = False
            self.x = screen_width // 2
            self.y = screen_height // 2
            self.current_structure = 200
        def take_damage(self, amount):
            self.current_structure -= amount
            print(f"MockPlayerShip: Took {amount} damage. Current structure: {self.current_structure}")

    class MockGame:
        def __init__(self, screen_width, screen_height):
            self.screen_width = screen_width
            self.screen_height = screen_height
            self.player_ship = MockPlayerShip(screen_width, screen_height)
            self.red = (255, 0, 0)
            self.black = (0, 0, 0)
            self.particle_effects = []
            self.obstacles = []
            self.SuckingParticleSystem = SuckingParticleSystem

    mock_game = MockGame(SCREEN_WIDTH, SCREEN_HEIGHT)
    test_mine = BallLightningMine(track=1, game=mock_game)

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    if test_mine.state == "done":
                        test_mine = BallLightningMine(track=1, game=mock_game)
                    elif test_mine.state == "charging":
                        test_mine.charge_timer = test_mine.charge_duration
                    elif test_mine.state == "traveling":
                        test_mine.radius = test_mine.target_radius

        test_mine.update()

        screen.fill((40, 0, 60))

        track_center_radius = mock_game.player_ship.orbital_radius_base + test_mine.track * mock_game.player_ship.track_width * mock_game.player_ship.track_spacing_multiplier
        pygame.draw.circle(screen, (20, 0, 30), (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2), track_center_radius + mock_game.player_ship.track_width // 2, 1)
        pygame.draw.circle(screen, (20, 0, 30), (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2), track_center_radius - mock_game.player_ship.track_width // 2, 1)

        test_mine.draw(screen)

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
