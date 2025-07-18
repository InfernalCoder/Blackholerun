import pygame
import math
import random

class FlameParticle:
    def __init__(self, x, y, angle, speed, max_length):
        self.x = x
        self.y = y
        self.angle = angle
        self.speed = speed
        self.max_length = max_length
        self.current_length = 0
        self.width = 3
        self.color = (255, 100, 0)

    def update(self):
        self.current_length += self.speed
        if self.current_length > self.max_length:
            return False
        return True

    def draw(self, screen):
        end_x = self.x + self.current_length * math.cos(self.angle)
        end_y = self.y + self.current_length * math.sin(self.angle)
        start_x = self.x + (self.current_length - self.speed) * math.cos(self.angle)
        start_y = self.y + (self.current_length - self.speed) * math.sin(self.angle)
        
        life_fraction = self.current_length / self.max_length
        current_width = int(self.width * (1 - life_fraction))
        if current_width < 1:
            current_width = 1
            
        r = 255
        g = int(255 * (1 - life_fraction))
        b = 0
        self.color = (r, g, b)

        pygame.draw.line(screen, self.color, (start_x, start_y), (end_x, end_y), current_width)

class FlameSystem:
    def __init__(self, ship):
        self.ship = ship
        self.particles = []
        self.emission_rate = 2
        self.exhaust_port_offset = 0
        self.port_separation = 5

    def update(self):
        visual_angle_rad = self.ship.angle
        
        forward_dx = math.cos(visual_angle_rad)
        forward_dy = math.sin(visual_angle_rad)
        sideways_dx = -forward_dy
        sideways_dy = forward_dx

        for port_side in [-1, 1]:
            for _ in range(self.emission_rate):
                port_x = (self.ship.x - self.exhaust_port_offset * forward_dx + 
                          self.port_separation * port_side * sideways_dx)
                port_y = (self.ship.y - self.exhaust_port_offset * forward_dy + 
                          self.port_separation * port_side * sideways_dy)

                particle_angle = visual_angle_rad + math.pi + random.uniform(-0.2, 0.2)
                
                current_speed = math.sqrt(self.ship.vx**2 + self.ship.vy**2)
                speed = random.uniform(0.5, 1.5)
                max_length = max(10, current_speed * 2.5 + 5)
                
                particle = FlameParticle(port_x, port_y, particle_angle, speed, max_length)
                self.particles.append(particle)

        self.particles = [p for p in self.particles if p.update()]

    def draw(self, screen):
        for particle in self.particles:
            particle.draw(screen)

class Ship:
    def __init__(self, screen_width, screen_height, ship_image):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.image_orig = ship_image
        self.image = self.image_orig
        self.radius = 12
        self.x = screen_width // 2
        self.y = screen_height // 2
        self.angle = -math.pi / 2 # Pointing up
        self.vx = 0
        self.vy = 0
        self.acceleration = 0.2
        self.turn_speed = 0.1
        self.max_speed = 5
        self.drag = 0.99

        self.initial_structure = 200
        self.current_structure = self.initial_structure
        self.max_energy = 100
        self.current_energy = self.max_energy

        self.shield_active = False
        self.shield_drain_rate = 0.5
        self.shield_color = (0, 150, 255)
        self.shield_thickness = 2

        self.shield_burst_active = False
        self.shield_burst_cost = 50
        self.shield_burst_radius = 20
        self.shield_burst_max_radius = 200
        self.shield_burst_duration = 40
        self.shield_burst_timer = 0
        self.shield_burst_color = (255, 255, 0)

        self.is_destroyed = False
        self.flame_system = FlameSystem(self)

    def thrust(self):
        self.vx += self.acceleration * math.cos(self.angle)
        self.vy += self.acceleration * math.sin(self.angle)

    def turn_left(self):
        self.angle = max(-math.pi, self.angle - self.turn_speed)

    def turn_right(self):
        self.angle = min(0, self.angle + self.turn_speed)

    def activate_shield(self):
        if self.current_energy > 0:
            self.shield_active = True

    def deactivate_shield(self):
        self.shield_active = False

    def shield_burst(self):
        if self.current_energy >= self.shield_burst_cost and not self.shield_burst_active:
            self.current_energy -= self.shield_burst_cost
            self.shield_burst_active = True
            self.shield_burst_timer = 0
            self.shield_burst_radius = 20
            print(f"Shield Burst Activated! Cost: {self.shield_burst_cost}, Current Energy: {self.current_energy}")
            return True
        print(f"Shield Burst Failed: Not enough energy ({self.current_energy}/{self.shield_burst_cost}) or already active ({self.shield_burst_active})")
        return False

    def take_damage(self, amount):
        self.current_structure -= amount
        if self.current_structure <= 0:
            self.is_destroyed = True
        print(f"Hit! Structure: {self.current_structure}")

    def handle_wall_collision(self, wall_rect):
        # Reduce speed upon collision
        self.vx *= 0.5
        self.vy *= 0.5

        penetration_limit = 32
        player_rect = self.image.get_rect(center=(self.x, self.y))
        penetration_depth = 0
        bounce_factor = -0.5 # Negative to reverse direction, magnitude for bounce strength

        # Determine which side the collision occurred on and resolve
        if player_rect.centerx < wall_rect.centerx: # Collided with left wall
            # Calculate penetration depth
            current_penetration = player_rect.right - wall_rect.left
            if current_penetration > 0:
                penetration_depth = min(current_penetration, penetration_limit)
                self.x = wall_rect.right + penetration_depth - self.radius # Push out to limit
                self.vx *= bounce_factor # Apply bounce
        else: # Collided with right wall
            # Calculate penetration depth
            current_penetration = wall_rect.right - player_rect.left
            if current_penetration > 0:
                penetration_depth = min(current_penetration, penetration_limit)
                self.x = wall_rect.left - penetration_depth + self.radius # Push out to limit
                self.vx *= bounce_factor # Apply bounce
        return penetration_depth

    def update(self):
        # Apply drag
        self.vx *= self.drag
        self.vy *= self.drag

        # Cap speed
        speed = math.sqrt(self.vx**2 + self.vy**2)
        if speed > self.max_speed:
            self.vx = (self.vx / speed) * self.max_speed
            self.vy = (self.vy / speed) * self.max_speed

        # Update position
        self.x += self.vx

        # Horizontal screen wrapping
        if self.x < 0: self.x = self.screen_width
        if self.x > self.screen_width: self.x = 0

        # Vertical clamping with buffer zone
        buffer_top = 200
        buffer_bottom = self.screen_height - 200

        if self.y < buffer_top:
            self.y = buffer_top
            self.vy = 0  # Stop vertical movement
        elif self.y > buffer_bottom:
            self.y = buffer_bottom
            self.vy = 0  # Stop vertical movement

        self._update_shield()
        self._update_shield_burst()
        
        self.flame_system.update()

    def _update_shield(self):
        if self.shield_active:
            self.current_energy -= self.shield_drain_rate
            if self.current_energy <= 0:
                self.current_energy = 0
                self.shield_active = False
                print("Shield failed! Energy depleted.")

    def _update_shield_burst(self):
        if self.shield_burst_active:
            self.shield_burst_timer += 1
            self.shield_burst_radius = 20 + (self.shield_burst_max_radius - 20) * (self.shield_burst_timer / self.shield_burst_duration)
            if self.shield_burst_timer >= self.shield_burst_duration:
                self.shield_burst_active = False

    def draw(self, screen):
        self.flame_system.draw(screen)
        
        rotation_angle_deg = math.degrees(self.angle) + 90
        rotated_image = pygame.transform.rotate(self.image_orig, -rotation_angle_deg)
        image_rect = rotated_image.get_rect(center=(self.x, self.y))
        screen.blit(rotated_image, image_rect.topleft)

        if self.shield_active:
            pygame.draw.circle(screen, self.shield_color, (int(self.x), int(self.y)), self.radius + 5, self.shield_thickness)

        if self.shield_burst_active:
            alpha = 255 * (1 - (self.shield_burst_timer / self.shield_burst_duration))
            color = (*self.shield_burst_color, alpha)
            s = pygame.Surface((self.shield_burst_radius * 2, self.shield_burst_radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(s, color, (self.shield_burst_radius, self.shield_burst_radius), self.shield_burst_radius, 2)
            screen.blit(s, (self.x - self.shield_burst_radius, self.y - self.shield_burst_radius))

    def reset(self):
        self.x = self.screen_width // 2
        self.y = self.screen_height // 2
        self.vx = 0
        self.vy = 0
        self.angle = -math.pi / 2
        self.current_structure = self.initial_structure
        self.current_energy = self.max_energy
        self.shield_active = False
        self.shield_burst_active = False
        self.is_destroyed = False