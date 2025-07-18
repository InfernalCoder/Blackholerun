
import pygame
import random

class BackgroundParticle:
    def __init__(self, screen_width, screen_height):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.x = random.randint(0, screen_width)
        self.y = random.randint(0, screen_height)
        self.speed = random.uniform(0.5, 2.5)
        self.radius = random.randint(1, 3)
        self.color = (random.randint(50, 100), random.randint(10, 30), random.randint(80, 140))

    def update(self, world_scroll_speed):
        self.y += self.speed + world_scroll_speed
        if self.y > self.screen_height:
            self.y = 0
            self.x = random.randint(0, self.screen_width)

    def draw(self, screen):
        pygame.draw.circle(screen, self.color, (self.x, int(self.y)), self.radius)

class VeinBackground:
    def __init__(self, screen_width, screen_height, num_particles):
        self.particles = [BackgroundParticle(screen_width, screen_height) for _ in range(num_particles)]

    def update(self, world_scroll_speed):
        for particle in self.particles:
            particle.update(world_scroll_speed)

    def draw(self, screen):
        for particle in self.particles:
            particle.draw(screen)
