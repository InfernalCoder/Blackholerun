
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
            return False  # Particle is dead
        return True

    def draw(self, screen, ship_angle):
        end_x = self.x + self.current_length * math.cos(self.angle)
        end_y = self.y + self.current_length * math.sin(self.angle)
        start_x = self.x + (self.current_length - self.speed) * math.cos(self.angle)
        start_y = self.y + (self.current_length - self.speed) * math.sin(self.angle)
        
        # Adjust width and color based on length
        life_fraction = self.current_length / self.max_length
        current_width = int(self.width * (1 - life_fraction))
        if current_width < 1:
            current_width = 1
            
        # Interpolate color from yellow to red
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
        self.exhaust_port_offset = -13  # How far from the center towards the back (left of sprite)
        self.port_separation = 5       # How far from the centerline to the thrusters (up/down on sprite)

    def update(self):
        # The ship's logical angle for movement
        theta = self.ship.angle

        # The ship is drawn rotated by -90 degrees, so its visual "up" is theta - 90 degrees
        visual_angle_rad = theta - (math.pi / 2)

        # Get the direction vectors for the VISUAL orientation
        forward_dx = math.cos(visual_angle_rad)
        forward_dy = math.sin(visual_angle_rad)
        sideways_dx = -forward_dy
        sideways_dy = forward_dx

        # Emit new particles for each port
        for port_side in [-1, 1]:  # -1 for "top" port, 1 for "bottom" port on the sprite
            for _ in range(self.emission_rate):
                # Calculate the port's position by starting at ship center and moving backward and sideways
                # relative to the VISUAL orientation
                port_x = (self.ship.x - 
                          self.exhaust_port_offset * forward_dx + 
                          self.port_separation * port_side * sideways_dx)
                port_y = (self.ship.y - 
                          self.exhaust_port_offset * forward_dy + 
                          self.port_separation * port_side * sideways_dy)

                # The particle's main direction is backward from the VISUAL angle
                particle_angle = visual_angle_rad + math.pi
                particle_angle += random.uniform(-0.1, 0.1) # Add spread
                
                speed = random.uniform(0.5, 1.5)
                max_length = self.ship.base_tangential_speed * 2.5 + 5
                
                particle = FlameParticle(port_x, port_y, particle_angle, speed, max_length)
                self.particles.append(particle)

        # Update and remove dead particles
        self.particles = [p for p in self.particles if p.update()]

    def draw(self, screen):
        for particle in self.particles:
            particle.draw(screen, 0) # The particle's angle is now absolute

class Ship:
    def __init__(self, screen_width, screen_height, ship_image, debug_mode=False):
        # Screen dimensions
        self.screen_width = screen_width
        self.screen_height = screen_height

        # Core Attributes
        self.image_orig = ship_image
        self.image = self.image_orig
        self.display_scale = 1.7
        self.radius = 12
        self.angle = 0
        self.track = 1  # Start on the middle track (0, 1, 2)

        # Position (calculated in update)
        self.x = 0
        self.y = 0
        self.orbital_radius = 0

        # Movement & Speed
        self.base_tangential_speed = 3.0
        self.max_tangential_speed = 10.0
        self.speed = 0

        # Health & Energy
        self.initial_structure = 200
        self.current_structure = self.initial_structure
        self.max_energy = 100
        self.current_energy = self.max_energy

        # Shield Attributes
        self.shield_active = False
        self.shield_drain_rate = 0.5  # Energy drained per frame
        self.shield_color = (255, 0, 0)
        self.shield_thickness = 3

        # Shield Overload Attributes (Can be kept for a potential future "desperation" mechanic)
        self.shield_overload_active = False
        self.shield_overload_cost = 10

        # Hit Effect Attributes
        self.hit_effect_active = False
        self.hit_effect_timer = 0
        self.hit_effect_duration = 30
        self.hit_scale_factor = 1.7
        self.original_radius = self.radius

        # Track layout properties from the main game
        self.track_width = 40
        self.track_spacing_multiplier = 2.5
        self.orbital_radius_base = 150
        self.is_destroyed = False
        
        self.flame_system = FlameSystem(self)
        self.debug_mode = debug_mode

    def move(self, direction):
        """Moves the ship left or right between tracks."""
        if self.debug_mode: return
        if direction == 'left':
            self.track = min(2, self.track + 1)
        elif direction == 'right':
            self.track = max(0, self.track - 1)

    def activate_shield(self):
        """Activates the shield if there is enough energy."""
        if self.current_energy > 0:
            self.shield_active = True

    def deactivate_shield(self):
        """Deactivates the shield."""
        self.shield_active = False

    def take_damage(self, amount):
        """Reduces the ship's structure and triggers the hit effect."""
        if self.debug_mode: return
        self.current_structure -= amount
        self.base_tangential_speed = max(1.0, self.base_tangential_speed - 0.5)
        self.hit_effect_active = True
        self.hit_effect_timer = 0 # Reset timer
        self.radius = int(self.original_radius * self.hit_scale_factor)
        print(f"Hit! Structure: {self.current_structure}, Shield Active: {self.shield_active}")

    def collect_energy(self, amount):
        """Recharges the ship's energy."""
        self.current_energy = min(self.max_energy, self.current_energy + amount)
        print(f"Energy Recharged! Current Energy: {self.current_energy}")

    def collect_boost(self):
        """Increases the ship's speed."""
        if self.debug_mode: return
        self.base_tangential_speed = min(self.max_tangential_speed, self.base_tangential_speed + 1.0)
        return True # Return a flag for the main game to handle dilation reduction

    def update(self):
        """Updates all per-frame logic for the ship."""
        if self.debug_mode:
            self.x = self.screen_width // 2
            self.y = self.screen_height // 2
            # self.angle += 0.01 # Slow rotation disabled for static view
            self.flame_system.update()
            return
            
        # Update shield state and drain energy
        self._update_shield()
        # Update hit effect timer
        self._update_hit_effect()

        # Update position and angle
        self.orbital_radius = self.orbital_radius_base + self.track * self.track_width * self.track_spacing_multiplier
        self.speed = self.base_tangential_speed / self.orbital_radius
        self.angle += self.speed
        if self.angle > 2 * math.pi:
            self.angle -= 2 * math.pi
        elif self.angle < 0:
            self.angle += 2 * math.pi

        self.x = self.screen_width // 2 + self.orbital_radius * math.cos(self.angle)
        self.y = self.screen_height // 2 + self.orbital_radius * math.sin(self.angle)
        
        self.flame_system.update()

    def _update_shield(self):
        if self.shield_active:
            self.current_energy -= self.shield_drain_rate
            if self.current_energy <= 0:
                self.current_energy = 0
                self.shield_active = False
                print("Shield failed! Energy depleted.")

    def _update_hit_effect(self):
        if self.hit_effect_active:
            self.hit_effect_timer += 1
            if self.hit_effect_timer >= self.hit_effect_duration:
                self.hit_effect_active = False
                self.radius = self.original_radius

    def draw(self, screen):
        """Draws the ship and its shield to the screen."""
        self.flame_system.draw(screen)
        
        # Draw ship
        scaled_image = pygame.transform.scale(self.image_orig, (int(self.image.get_width() * self.display_scale), int(self.image.get_height() * self.display_scale)))
        
        rotation_angle_deg = math.degrees(-self.angle)
        if not self.debug_mode:
            rotation_angle_deg -= 90 # Adjust for in-game orientation

        rotated_image = pygame.transform.rotate(scaled_image, rotation_angle_deg)
        image_rect = rotated_image.get_rect(center=(self.x, self.y))
        screen.blit(rotated_image, image_rect.topleft)

        # Draw shield
        if self.shield_active:
            shield_radius = self.radius * 2
            pygame.draw.circle(screen, self.shield_color, (int(round(self.x)), int(round(self.y))), int(round(shield_radius)), self.shield_thickness)

    def reset(self):
        """Resets the ship to its initial state for a new game."""
        self.current_structure = self.initial_structure
        self.current_energy = self.max_energy
        self.angle = 0
        self.track = 1
        self.base_tangential_speed = 3.0
        self.shield_active = False
        self.shield_overload_active = False
        self.hit_effect_active = False
        self.shield_timer = 0
        self.shield_overload_timer = 0
        self.hit_effect_timer = 0
        self.radius = self.original_radius
        self.display_scale = 1.7 # Reset display scale to default
        self.is_destroyed = False
