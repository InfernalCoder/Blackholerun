
import pygame
import random
import math
from wbc_module import WhiteBloodCell # Import WBC

class WallManager:
    def __init__(self, screen_width, screen_height, scroll_speed, player):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.scroll_speed = scroll_speed
        self.player = player
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.scroll_speed = scroll_speed
        self.segment_spacing = 20  # Vertical spacing between points defining the wall
        self.color = (50, 20, 80)
        self.inner_vein_color = (70, 30, 100, 102) # A slightly lighter shade for the vein interior with 40% alpha
        self.wall_thickness = 30  # Visual thickness of the wall

        self.min_gap = 300
        self.max_gap = 600
        self.initial_gap = 400
        self.gap_amplitude = 100  # How much the gap widens/narrows
        self.gap_frequency = 0.01 # How fast the gap changes
        self.tick_counter = 0     # For sine wave calculation

        self.jitter_amount = 20   # Max pixels for jitter

        # Store points as (x, y) tuples for inner and outer edges
        self.left_inner_points = []
        self.right_inner_points = []
        self.attached_wbcs = [] # New list to store WBCs attached to walls

        # Initialize walls to cover screen plus buffer
        self._initialize_walls()

    def _initialize_walls(self):
        # Start from slightly below screen to ensure full coverage
        current_y = self.screen_height + self.segment_spacing * 2 # Start below screen
        while current_y >= -self.segment_spacing * 2: # Go above screen
            self._add_new_segment_points(current_y)
            current_y -= self.segment_spacing

    def _add_new_segment_points(self, y):
        # Dynamic gap calculation
        dynamic_gap = self.initial_gap + self.gap_amplitude * math.sin(self.tick_counter * self.gap_frequency)
        dynamic_gap = max(self.min_gap, min(self.max_gap, dynamic_gap)) # Ensure within min/max

        center_x = self.screen_width / 2
        
        # Calculate base x positions for left and right walls
        base_left_x = center_x - dynamic_gap / 2
        base_right_x = center_x + dynamic_gap / 2

        # Apply jitter to the base x positions
        jitter_left = random.uniform(-self.jitter_amount, self.jitter_amount)
        jitter_right = random.uniform(-self.jitter_amount, self.jitter_amount)

        left_x = base_left_x + jitter_left
        right_x = base_right_x + jitter_right

        # Add points to the beginning of the lists (top of the screen)
        self.left_inner_points.insert(0, [left_x, y])
        self.right_inner_points.insert(0, [right_x, y])

        # Randomly spawn WBCs on walls
        # Randomly spawn WBCs on walls
        if random.random() < 0.2: # 20% chance to spawn a WBC
            side = random.choice(['left', 'right'])
            if side == 'left':
                wbc_x = left_x - self.wall_thickness / 2
            else:
                wbc_x = right_x + self.wall_thickness / 2

            new_wbc = WhiteBloodCell(self.screen_width, self.screen_height, self.player, self)
            new_wbc.x = wbc_x
            new_wbc.y = y
            new_wbc.state = 'WALL_ATTACHED'
            self.attached_wbcs.append(new_wbc)

    def update(self, world_scroll_speed):
        self.tick_counter += 1 # Increment tick counter for sine wave

        # Scroll all existing points
        for i in range(len(self.left_inner_points)):
            self.left_inner_points[i][1] += world_scroll_speed
            self.right_inner_points[i][1] += world_scroll_speed

        # Update attached WBCs
        for wbc in self.attached_wbcs:
            wbc.y += world_scroll_speed

        # Remove points that have scrolled off-screen (bottom)
        # Keep points that are still on screen or just off the top
        self.left_inner_points = [p for p in self.left_inner_points if p[1] < self.screen_height + self.segment_spacing]
        self.right_inner_points = [p for p in self.right_inner_points if p[1] < self.screen_height + self.segment_spacing]

        # Remove WBCs that are off-screen or have detached
        self.attached_wbcs = [wbc for wbc in self.attached_wbcs if not wbc.is_offscreen() and wbc.state == 'WALL_ATTACHED']

        # Add new points at the top if needed
        # Check if the topmost point is visible or just off-screen
        while not self.left_inner_points or self.left_inner_points[0][1] > -self.segment_spacing:
            self._add_new_segment_points(self.left_inner_points[0][1] - self.segment_spacing if self.left_inner_points else self.screen_height)

    def draw(self, screen):
        # Draw the inner vein area first
        if len(self.left_inner_points) > 1 and len(self.right_inner_points) > 1:
            # Create a temporary surface for transparent drawing
            temp_surface = pygame.Surface((self.screen_width, self.screen_height), pygame.SRCALPHA)
            
            # Combine inner points to form the vein polygon
            vein_polygon_points = [(p[0], p[1]) for p in self.left_inner_points] + \
                                  [(p[0], p[1]) for p in reversed(self.right_inner_points)]
            pygame.draw.polygon(temp_surface, self.inner_vein_color, vein_polygon_points)
            
            # Blit the temporary surface onto the main screen
            screen.blit(temp_surface, (0, 0))

        # Draw left wall
        if len(self.left_inner_points) > 1:
            # Create polygon points for the left wall
            # Inner edge points
            poly_points_left = [(p[0], p[1]) for p in self.left_inner_points]
            # Outer edge points (reversed to connect correctly)
            poly_points_left_outer = [(p[0] - self.wall_thickness, p[1]) for p in reversed(self.left_inner_points)]
            
            pygame.draw.polygon(screen, self.color, poly_points_left + poly_points_left_outer)

        # Draw right wall
        if len(self.right_inner_points) > 1:
            # Create polygon points for the right wall
            # Inner edge points
            poly_points_right = [(p[0], p[1]) for p in self.right_inner_points]
            # Outer edge points (reversed to connect correctly)
            poly_points_right_outer = [(p[0] + self.wall_thickness, p[1]) for p in reversed(self.right_inner_points)]
            
            pygame.draw.polygon(screen, self.color, poly_points_right + poly_points_right_outer)

        # Draw attached WBCs
        for wbc in self.attached_wbcs:
            wbc.draw(screen)

    def check_collision(self, player_rect):
        player_y = player_rect.centery
        player_left = player_rect.left
        player_right = player_rect.right
        player_radius = player_rect.width / 2 # Assuming player_rect is square, use half width as radius

        # Debugging player rect info
        print(f"Player Rect: x={player_rect.x}, y={player_rect.y}, width={player_rect.width}, height={player_rect.height}")
        print(f"Player: Y={player_y}, Left={player_left}, Right={player_right}, Radius={player_radius}")

        # Find the two wall points that bracket the player's y-position
        # Assuming points are sorted by y (from top to bottom)
        for i in range(len(self.left_inner_points) - 1):
            p1_left = self.left_inner_points[i]
            p2_left = self.left_inner_points[i+1]
            p1_right = self.right_inner_points[i]
            p2_right = self.right_inner_points[i+1]

            # Debugging segment points
            # print(f"  Segment {i}: p1_left={p1_left}, p2_left={p2_left}, p1_right={p1_right}, p2_right={p2_right}")

            # Check if player_y is between p1.y and p2.y
            if (p1_left[1] <= player_y <= p2_left[1]):
                # Interpolate left_x and right_x at player's y-level
                # alpha is the interpolation factor (0 at p2.y, 1 at p1.y)
                alpha = (player_y - p2_left[1]) / (p1_left[1] - p2_left[1])
                
                interpolated_left_inner_x = p2_left[0] + alpha * (p1_left[0] - p2_left[0])
                interpolated_right_inner_x = p2_right[0] + alpha * (p1_right[0] - p2_right[0])

                # Calculate outer wall boundaries
                interpolated_left_outer_x = interpolated_left_inner_x - self.wall_thickness
                interpolated_right_outer_x = interpolated_right_inner_x + self.wall_thickness

                # Debugging interpolated values
                print(f"  Interpolated: LeftInner={interpolated_left_inner_x:.2f}, RightInner={interpolated_right_inner_x:.2f}")
                print(f"  Interpolated: LeftOuter={interpolated_left_outer_x:.2f}, RightOuter={interpolated_right_outer_x:.2f}")

                # Check for collision with the actual wall (considering its thickness)
                # Collision with left wall
                collision_left = player_rect.right > interpolated_left_outer_x and player_rect.left < interpolated_left_inner_x
                # Collision with right wall
                collision_right = player_rect.left < interpolated_right_outer_x and player_rect.right > interpolated_right_inner_x

                print(f"  Collision Check: Left={collision_left}, Right={collision_right}")

                if collision_left:
                    # Return a rect representing the left wall at the collision point
                    print(f"  Collision detected with LEFT wall. Returning Rect: x={interpolated_left_outer_x}, y={player_y - player_radius}, width={self.wall_thickness}, height={player_rect.height}")
                    return pygame.Rect(interpolated_left_outer_x, player_y - player_radius, self.wall_thickness, player_rect.height)
                
                if collision_right:
                    # Return a rect representing the right wall at the collision point
                    print(f"  Collision detected with RIGHT wall. Returning Rect: x={interpolated_right_inner_x}, y={player_y - player_radius}, width={self.wall_thickness}, height={player_rect.height}")
                    return pygame.Rect(interpolated_right_inner_x, player_y - player_radius, self.wall_thickness, player_rect.height)
        return None

    def get_all_wbcs(self):
        # Return attached WBCs and any that have detached and are seeking
        seeking_wbcs = [wbc for wbc in self.attached_wbcs if wbc.state != 'WALL_ATTACHED']
        return self.attached_wbcs + seeking_wbcs
