
import pygame
import random
import math

class WhiteBloodCell:
    def __init__(self, screen_width, screen_height, target, wall_manager):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.target = target
        self.wall_manager = wall_manager
        self.radius = 10
        self.state = 'WALL_ATTACHED'
        self.speed = random.uniform(1.5, 2.5)
        self.velocity_x = 0
        self.velocity_y = 0
        self.color = (240, 240, 255)
        self.attached_offset = (0, 0)
        self.avoid_timer = 0
        self.detachment_radius = 200
        self.repel_cooldown_timer = 0 # New attribute

        # Attach to a random wall point
        self._attach_to_wall()

    def _attach_to_wall(self):
        side = random.choice(['left', 'right'])
        if side == 'left':
            wall_points = self.wall_manager.left_inner_points
        else:
            wall_points = self.wall_manager.right_inner_points

        if wall_points:
            # Choose a random point from the wall points that is currently on screen
            on_screen_points = [p for p in wall_points if 0 <= p[1] <= self.screen_height]
            if on_screen_points:
                chosen_point = random.choice(on_screen_points)
                self.x = chosen_point[0]
                self.y = chosen_point[1]

                # No additional x-adjustment needed, as they spawn directly on the wall line
            else:
                # Fallback if no on-screen points, start seeking
                self.state = 'SEEKING'
                self.x = random.randint(0, self.screen_width)
                self.y = random.randint(0, self.screen_height)
        else:
            # If no wall points are available at all, start seeking
            self.state = 'SEEKING'
            self.x = random.randint(0, self.screen_width)
            self.y = random.randint(0, self.screen_height)

    def update(self, world_scroll_speed):
        dx = self.target.x - self.x
        dy = self.target.y - self.y
        dist = math.hypot(dx, dy)

        # Debugging: Log update entry
        print(f"WBC Update: State={self.state}, Y={self.y:.2f}, world_scroll_speed={world_scroll_speed:.2f}, Cooldown={self.repel_cooldown_timer}")

        self._handle_state_transitions(dist, dx, dy)

        if self.state == 'SEEKING':
            self._seeking_behavior(dx, dy, dist)
        elif self.state == 'AVOIDING':
            self._avoiding_behavior(dx, dy, dist)
        elif self.state == 'ATTACHED':
            self._attached_behavior()
        elif self.state == 'WALL_ATTACHED':
            self._wall_attached_behavior(world_scroll_speed)

        self.x += self.velocity_x
        if self.state != 'ATTACHED':
            self.y += self.velocity_y + world_scroll_speed
        else:
            self.y += self.velocity_y

        if self.repel_cooldown_timer > 0:
            self.repel_cooldown_timer -= 1

    def _handle_state_transitions(self, dist, dx, dy):
        # Debugging: Log state transitions entry
        print(f"  _handle_state_transitions: Current State={self.state}, Dist={dist:.2f}, Cooldown={self.repel_cooldown_timer}")

        if self.state == 'WALL_ATTACHED' and dist < self.detachment_radius:
            print(f"  Transition: WALL_ATTACHED -> SEEKING (Detached)")
            self.state = 'SEEKING'

        elif self.state == 'SEEKING':
            # Debugging: Log SEEKING state checks
            print(f"    SEEKING checks: shield_active={self.target.shield_active}, dist={dist:.2f}, target_radius+self_radius={self.target.radius + self.radius}, cooldown={self.repel_cooldown_timer}")
            if self.target.shield_active and dist < self.target.radius + 80:
                print(f"    Transition: SEEKING -> AVOIDING (Shield Active)")
                self.state = 'AVOIDING'
                self.avoid_timer = 120
            elif not self.target.shield_active and dist < self.target.radius + self.radius and self.repel_cooldown_timer == 0:
                print(f"    Transition: SEEKING -> ATTACHED (No Shield, Close, No Cooldown)")
                self.state = 'ATTACHED'
                angle_of_approach = math.atan2(dy, dx)
                self.attached_offset = (self.target.radius * math.cos(angle_of_approach), 
                                        self.target.radius * math.sin(angle_of_approach))

        elif self.state == 'AVOIDING':
            self.avoid_timer -= 1
            if self.avoid_timer <= 0:
                print(f"  Transition: AVOIDING -> SEEKING (Avoid Timer Expired)")
                self.state = 'SEEKING'

    def _seeking_behavior(self, dx, dy, dist):
        if dist > 0:
            seek_angle = math.atan2(dy, dx) + random.uniform(-0.4, 0.4)
            self.velocity_x = self.speed * math.cos(seek_angle)
            self.velocity_y = self.speed * math.sin(seek_angle)
        else:
            self.velocity_x, self.velocity_y = 0, 0

    def _avoiding_behavior(self, dx, dy, dist):
        if dist > 0:
            flee_angle = math.atan2(dy, dx) + math.pi
            self.velocity_x = self.speed * 1.5 * math.cos(flee_angle)
            self.velocity_y = self.speed * 1.5 * math.sin(flee_angle)
        else:
            random_angle = random.uniform(0, 2 * math.pi)
            self.velocity_x = self.speed * 1.5 * math.cos(random_angle)
            self.velocity_y = self.speed * 1.5 * math.sin(random_angle)

    def _attached_behavior(self):
        self.x = self.target.x + self.attached_offset[0]
        self.y = self.target.y + self.attached_offset[1]
        self.velocity_x = self.target.vx
        self.velocity_y = self.target.vy

    def _wall_attached_behavior(self, world_scroll_speed):
        # WBCs attached to walls should scroll with the world
        self.y += world_scroll_speed
        self.velocity_x = 0
        self.velocity_y = 0 # No independent vertical movement when attached to wall

    def be_repelled(self, burst_center_x, burst_center_y, burst_force):
        # Debugging: Log be_repelled entry
        print(f"WBC be_repelled: Before: State={self.state}, Cooldown={self.repel_cooldown_timer}")
        self.state = 'SEEKING'
        self.repel_cooldown_timer = 120 # Set cooldown for 120 frames (2 seconds)
        dx = self.x - burst_center_x
        dy = self.y - burst_center_y
        dist = math.hypot(dx, dy)
        if dist > 0:
            self.velocity_x += burst_force * dx / dist
            self.velocity_y += burst_force * dy / dist
        # Debugging: Log be_repelled exit
        print(f"WBC be_repelled: After: State={self.state}, Cooldown={self.repel_cooldown_timer}, New Velocity=({self.velocity_x:.2f}, {self.velocity_y:.2f})")

    def is_offscreen(self):
        return (self.y - self.radius > self.screen_height or
                self.y + self.radius < 0 or
                self.x - self.radius > self.screen_width or
                self.x + self.radius < 0)

    def draw(self, screen):
        pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), self.radius)
        pygame.draw.circle(screen, (200, 200, 220), (int(self.x), int(self.y)), self.radius - 4)
