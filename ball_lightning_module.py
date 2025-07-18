import pygame
import random
import math
import sys

# --- Helper Function for Distance Calculation (Private to Module) ---
def _distance(p1, p2):
    """Calculates Euclidean distance between two points."""
    return math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)

# --- Helper Function for Single Lightning Segment Generation (Private to Module) ---
def _generate_single_lightning_segment_points(center_x, center_y, max_segment_length, jitter_magnitude, initial_angle):
    """
    Generates a list of (x, y) points for a single jagged lightning bolt
    using a "pixel-walk" method. Points are relative to the given center_x, center_y.
    """
    points = []
    current_angle = initial_angle

    # Start exactly at the center of the graphic's local surface
    current_x, current_y = float(center_x), float(center_y) # Use floats for internal calculation precision
    points.append((int(round(current_x)), int(round(current_y))))

    # Define a generous number of steps to allow the bolt to zig-zag and still reach the edge
    num_steps_allowed = int(max_segment_length * 2)

    for i in range(num_steps_allowed):
        step_len = 1.0 # Each "step" moves 1 pixel unit
        next_x = current_x + step_len * math.cos(current_angle)
        next_y = current_y + step_len * math.sin(current_angle)

        # Apply angular jitter to make the path less straight (introduces "zig-zag")
        # Ensure a minimum turn in a random direction
        min_turn_radians = 0.05 # A small guaranteed turn (e.g., ~2.8 degrees)
        angle_jitter_magnitude = random.uniform(min_turn_radians, 0.3)
        angle_jitter = random.choice([-1, 1]) * angle_jitter_magnitude # Force a turn left or right
        current_angle += angle_jitter

        # Clamp the position to ensure it doesn't go too far
        dist_from_center = _distance((next_x, next_y), (center_x, center_y))
        if dist_from_center > max_segment_length + jitter_magnitude:
            break # Stop if we've gone too far

        # Apply positional jitter to create more pixelated jaggedness
        next_x += random.choice([-jitter_magnitude, 0, jitter_magnitude])
        next_y += random.choice([-jitter_magnitude, 0, jitter_magnitude])

        # Update current position, rounding to nearest pixel for display
        current_x, current_y = next_x, next_y

        # Add point only if it's visually distinct from the last one
        new_rounded_point = (int(round(current_x)), int(round(current_y)))
        if new_rounded_point != points[-1]:
            points.append(new_rounded_point)

    return points


# --- Global Constants for Ball Lightning Appearance and Animation ---

# Core appearance dimensions
DEFAULT_RADIUS = 15
NUM_BOLTS = 25
JITTER_MAGNITUDE = random.uniform(0.5, 2)

# Colors (RGBA format: Red, Green, Blue, Alpha)
CORE_COLOR = (255, 255, 255, 255)
PULSE_COLOR = (125, 249, 255, 255)

# Per-bolt pulse speed range (for brightness changes)
MIN_BOLT_PULSE_SPEED = 0.03
MAX_BOLT_PULSE_SPEED = 0.1

# Animation (for shape regeneration)
ANIMATION_FRAMES = 1
ANIMATION_SPEED = 5

# Constants for Bolt Extension
BOLT_EXTENSION_CHANCE = 0.35
BOLT_EXTENSION_MULTIPLIER_RANGE = (1.5, 3.75)

# NEW: Bolt growth animation
BOLT_GROWTH_DURATION = 5 # Number of frames for a bolt to "grow" from center to full length


# --- Main BallLightning Class ---
class BallLightning:
    def __init__(self, radius=DEFAULT_RADIUS,
                 initial_color=CORE_COLOR, pulse_color=PULSE_COLOR,
                 animation_speed=ANIMATION_SPEED):

        self.radius = radius
        self.core_color = initial_color
        self.pulse_color = pulse_color
        self.animation_speed = animation_speed

        self.current_frame_count = 0
        self.patterns = []
        self.current_pattern_index = 0

        self.x = 0
        self.y = 0

        self._generate_all_patterns()

    def _generate_all_patterns(self):
        """
        Generates distinct lightning patterns for all bolts at once.
        Each pattern stores data for each individual bolt, including its pulse state and NEW growth state.
        With ANIMATION_FRAMES=1, this effectively generates one new random pattern.
        """
        self.patterns = []

        base_angle_step = (2 * math.pi) / NUM_BOLTS

        for _ in range(ANIMATION_FRAMES):
            frame_bolts_data = []
            for i in range(NUM_BOLTS):
                angle = base_angle_step * i + random.uniform(-0.2, 0.2)

                current_max_segment_length = self.radius
                if random.random() < BOLT_EXTENSION_CHANCE:
                    extension_multiplier = random.uniform(BOLT_EXTENSION_MULTIPLIER_RANGE[0], BOLT_EXTENSION_MULTIPLIER_RANGE[1])
                    current_max_segment_length = self.radius * extension_multiplier

                bolt_points = _generate_single_lightning_segment_points(
                    center_x=self.radius,
                    center_y=self.radius,
                    max_segment_length=current_max_segment_length,
                    jitter_magnitude=JITTER_MAGNITUDE,
                    initial_angle=angle
                )

                bolt_data = {
                    'points': bolt_points,
                    'pulse_value': random.uniform(0.0, 1.0),
                    'pulse_direction': random.choice([-1, 1]),
                    'pulse_speed': random.uniform(MIN_BOLT_PULSE_SPEED, MAX_BOLT_PULSE_SPEED),
                    'growth_progress': 0.0 # NEW: Initialize growth progress for newly generated bolts
                }
                frame_bolts_data.append(bolt_data)
            self.patterns.append(frame_bolts_data)

    def update(self):
        """
        Advances the internal animation state of the ball lightning graphic.
        Shapes are regenerated for all bolts based on animation_speed.
        Each bolt's pulse value and NEW growth progress are updated independently.
        """
        self.current_frame_count += 1
        if self.current_frame_count >= self.animation_speed:
            self.current_frame_count = 0
            self._generate_all_patterns() # Regenerates points for ALL bolts and new initial pulse states (with growth_progress = 0)
            self.current_pattern_index = 0

        current_pattern_bolts = self.patterns[self.current_pattern_index]
        for bolt_data in current_pattern_bolts:
            # Update pulse value (brightness)
            bolt_data['pulse_value'] += bolt_data['pulse_speed'] * bolt_data['pulse_direction']
            if bolt_data['pulse_value'] >= 1.0:
                bolt_data['pulse_value'] = 1.0
                bolt_data['pulse_direction'] = -1
            elif bolt_data['pulse_value'] <= 0.0:
                bolt_data['pulse_value'] = 0.0
                bolt_data['pulse_direction'] = 1

            # NEW: Update growth progress
            if bolt_data['growth_progress'] < 1.0:
                bolt_data['growth_progress'] += (1.0 / BOLT_GROWTH_DURATION)
                if bolt_data['growth_progress'] > 1.0: # Clamp to 1.0 to prevent overshooting
                    bolt_data['growth_progress'] = 1.0

    def get_current_image(self):
        """
        Returns a pygame.Surface representing the ball lightning's current visual state,
        with each bolt colored according to its individual pulse phase and NEW growth state.
        """
        max_visual_radius = self.radius * BOLT_EXTENSION_MULTIPLIER_RANGE[1] + JITTER_MAGNITUDE
        surface_dim = int(max_visual_radius * 2) + 4
        lightning_surface = pygame.Surface((surface_dim, surface_dim), pygame.SRCALPHA)
        drawing_center = (surface_dim // 2, surface_dim // 2)

        current_pattern_bolts = self.patterns[self.current_pattern_index]
        for bolt_data in current_pattern_bolts:
            bolt_points = bolt_data['points']
            bolt_pulse_value = bolt_data['pulse_value']
            bolt_growth_progress = bolt_data['growth_progress'] # NEW: Get growth progress

            current_lightning_color = (
                int(self.core_color[0] + (self.pulse_color[0] - self.core_color[0]) * bolt_pulse_value),
                int(self.core_color[1] + (self.pulse_color[1] - self.core_color[1]) * bolt_pulse_value),
                int(self.core_color[2] + (self.pulse_color[2] - self.core_color[2]) * bolt_pulse_value),
                self.core_color[3]
            )

            if len(bolt_points) > 1:
                # NEW: Calculate how many points to draw based on growth progress
                # Ensure at least 2 points are drawn to form a line, even at very low progress
                num_points_to_draw = max(2, int(len(bolt_points) * bolt_growth_progress))
                points_for_drawing = bolt_points[:num_points_to_draw] # Take only the growing segment of points

                offset_x = drawing_center[0] - self.radius
                offset_y = drawing_center[1] - self.radius
                offset_points = [(p[0] + offset_x, p[1] + offset_y) for p in points_for_drawing]
                if len(offset_points) > 1: # Ensure there are at least two points to draw a line
                    pygame.draw.lines(lightning_surface, current_lightning_color, False, offset_points, 1)

        pygame.draw.circle(lightning_surface, self.core_color, drawing_center, 2)

        return lightning_surface

    def set_position(self, x, y):
        """Sets the current screen position of the ball lightning graphic."""
        self.x = x
        self.y = y

# --- Standalone Test Block ---
if __name__ == "__main__":
    pygame.init()

    SCREEN_WIDTH = 400
    SCREEN_HEIGHT = 400
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Ball Lightning Animation Test (With Growth Effect)")

    clock = pygame.time.Clock()
    FPS = 60

    test_lightning = BallLightning(
        radius=DEFAULT_RADIUS,
        initial_color=(125, 249, 255, 255),
        pulse_color=(255, 255, 255, 255),
        animation_speed=5 # Shapes regenerate every 5 frames for all bolts
    )

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        test_lightning.update()
        test_lightning.set_position(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)

        screen.fill((0, 0, 0))

        lightning_image = test_lightning.get_current_image()
        image_rect = lightning_image.get_rect(center=(test_lightning.x, test_lightning.y))
        screen.blit(lightning_image, image_rect)

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    sys.exit()
