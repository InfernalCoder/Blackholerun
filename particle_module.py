
import pygame
import random
import math

class SuckingParticle(pygame.sprite.Sprite):
    def __init__(self, position, color, size, game):
        super().__init__()
        self.game = game
        self.image = pygame.Surface([size, size])
        self.image.fill(color)
        self.image.set_colorkey(self.game.black)
        pygame.draw.circle(self.image, color, (size // 2, size // 2), size // 2)
        self.rect = self.image.get_rect(center=position)
        self.x, self.y = [float(pos) for pos in position]
        self.vx = random.uniform(-2, 2)
        self.vy = random.uniform(-2, 2)
        self.lifespan = 60
        self.sucked_in = False
        self.suck_in_timer = 30
        self.swirl_strength = random.uniform(0.5, 1.5)

    def update(self):
        if not self.sucked_in:
            self.x += self.vx
            self.y += self.vy
            self.lifespan -= 1
            if self.lifespan <= self.suck_in_timer:
                self.sucked_in = True
        else:
            dx = self.game.original_screen_width // 2 - self.x
            dy = self.game.original_screen_height // 2 - self.y
            distance = math.hypot(dx, dy)
            if distance > 0:
                attraction_speed = 4
                tangential_speed = attraction_speed * 1.9 * self.swirl_strength
                nx = dx / distance
                ny = dy / distance
                tangential_vx = -ny * tangential_speed
                tangential_vy = nx * tangential_speed
                self.x += nx * attraction_speed + tangential_vx
                self.y += ny * attraction_speed + tangential_vy
        self.rect.center = (int(round(self.x)), int(round(self.y)))

class SuckingParticleSystem:
    def __init__(self, position, color, game):
        self.game = game
        self.particles = pygame.sprite.Group()
        for _ in range(20):
            size = random.randint(2, 5)
            particle = SuckingParticle(position, color, size, self.game)
            self.particles.add(particle)

    def update(self):
        self.particles.update()
        for particle in list(self.particles):
            if math.hypot(particle.x - self.game.original_screen_width // 2, particle.y - self.game.original_screen_height // 2) < 50 * 1.2:
                self.particles.remove(particle)
            elif particle.lifespan <= 0:
                self.particles.remove(particle)

    def draw(self, screen, camera_x=0, camera_y=0):
        for particle in self.particles:
            screen.blit(particle.image, (particle.rect.x - camera_x, particle.rect.y - camera_y))

class AdvancedParticle(pygame.sprite.Sprite):
    def __init__(self, start_pos, color, max_dist, pause_duration, return_speed, deceleration_factor=0.95):
        super().__init__()
        self.start_pos = start_pos
        self.color = color
        self.max_dist = max_dist
        self.pause_duration = pause_duration
        self.return_speed = return_speed
        self.deceleration_factor = deceleration_factor

        self.pos = list(start_pos)
        self.state = "burst"
        self.pause_timer = 0

        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(2, 5)
        self.velocity = [math.cos(angle) * speed, math.sin(angle) * speed]

        self.image = pygame.Surface((4, 4), pygame.SRCALPHA)
        pygame.draw.circle(self.image, self.color, (2, 2), 2)
        self.rect = self.image.get_rect(center=self.pos)

    def update(self):
        if self.state == "burst":
            self.pos[0] += self.velocity[0]
            self.pos[1] += self.velocity[1]
            self.velocity[0] *= self.deceleration_factor
            self.velocity[1] *= self.deceleration_factor

            dist_from_start = math.hypot(self.pos[0] - self.start_pos[0], self.pos[1] - self.start_pos[1])
            if dist_from_start >= self.max_dist or math.hypot(self.velocity[0], self.velocity[1]) < 0.1:
                self.state = "pause"
        elif self.state == "pause":
            self.pause_timer += 1
            if self.pause_timer >= self.pause_duration:
                self.state = "return"
        elif self.state == "return":
            dx = self.start_pos[0] - self.pos[0]
            dy = self.start_pos[1] - self.pos[1]
            dist = math.hypot(dx, dy)
            if dist < self.return_speed:
                self.kill()
            else:
                self.pos[0] += (dx / dist) * self.return_speed
                self.pos[1] += (dy / dist) * self.return_speed

        self.rect.center = self.pos

class AdvancedParticleSystem:
    def __init__(self, position, color):
        self.particles = pygame.sprite.Group()
        self.position = position
        self.color = color
        self.is_active = True

        for _ in range(30):
            particle = AdvancedParticle(
                start_pos=self.position,
                color=self.color,
                max_dist=random.uniform(50, 100),
                pause_duration=random.randint(10, 20),
                return_speed=random.uniform(4, 6)
            )
            self.particles.add(particle)
    
    def update(self):
        self.particles.update()
        if not self.particles:
            self.is_active = False

    def draw(self, screen, camera_x=0, camera_y=0):
        for particle in self.particles:
            screen.blit(particle.image, (particle.rect.x - camera_x, particle.rect.y - camera_y))

class BoostParticleSystem(AdvancedParticleSystem):
    def __init__(self, position):
         super().__init__(position, (0, 255, 0))

class PowerUpParticleSystem(AdvancedParticleSystem):
    def __init__(self, position):
        super().__init__(position, (255, 255, 0))

class ExplosionParticleSystem(AdvancedParticleSystem):
    def __init__(self, position):
        super().__init__(position, (255, 165, 0)) # Orange color for explosion
