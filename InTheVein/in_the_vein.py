
import pygame
import sys
import os
import math
from player_module import Ship
from wbc_module import WhiteBloodCell
from background_module import VeinBackground
from wall_module import WallManager

# Initialization
pygame.init()

# Screen dimensions
WIDTH, HEIGHT = 1200, 800
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("In the Vein")

# Colors & Font
VEIN_COLOR = (20, 5, 35)
WHITE = (255, 255, 255)
UI_COLOR = (200, 200, 255)
font = pygame.font.Font(None, 36)

# Load Assets
try:
    base_path = os.path.dirname(os.path.abspath(__file__))
    ship_image_path = os.path.join(base_path, '..', 'assets', 'ship01.png')
    ship_image = pygame.image.load(ship_image_path).convert_alpha()
    ship_image = pygame.transform.rotate(ship_image, 90)
except pygame.error as e:
    print(f"Unable to load asset: {ship_image_path}")
    print(e)
    sys.exit()

# Game Manager
class GameManager:
    def __init__(self, screen_width, screen_height):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.player = Ship(WIDTH, HEIGHT, ship_image)
        self.wbc_spawn_timer = 0
        self.wbc_spawn_rate = 120 # Spawn a new WBC every 2 seconds
        self.max_wbcs = 15
        self.damage_per_wbc = 0.1 # Damage per frame for each attached WBC
        self.wall_damage = 1
        self.game_over = False
        self.background = VeinBackground(WIDTH, HEIGHT, 200)
        self.base_scroll_speed = 5 # Base speed for world scrolling
        self.current_scroll_speed = self.base_scroll_speed # Actual scroll speed, can be reduced by wall collision
        self.wall_manager = WallManager(WIDTH, HEIGHT, self.base_scroll_speed, self.player)

    def update(self):
        if self.game_over:
            self._handle_input_game_over()
            return

        self._handle_input()
        self._update_game_objects()
        self._handle_collisions_and_damage()

        if self.player.is_destroyed:
            self.game_over = True

    def _handle_input(self):
        print("Handling input...")
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_b:
                    print("B key pressed!")
                    if self.player.shield_burst():
                        self._repel_wbcs()

        keys = pygame.key.get_pressed()
        if keys[pygame.K_UP] or keys[pygame.K_w]: self.player.thrust()
        if keys[pygame.K_LEFT] or keys[pygame.K_a]: self.player.turn_left()
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]: self.player.turn_right()
        if keys[pygame.K_SPACE]: self.player.activate_shield()
        else: self.player.deactivate_shield()

    def _handle_input_game_over(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN and event.key == pygame.K_r:
                self.reset_game()

    def _update_game_objects(self):
        self.player.update()

        # Calculate world scroll speed based on player's vertical position
        world_scroll_speed = self.current_scroll_speed
        buffer_top = 200
        buffer_bottom = self.screen_height - 200

        # If player is moving up and is in the top buffer, increase scroll speed
        if self.player.y <= buffer_top and self.player.vy < 0:
            world_scroll_speed -= self.player.vy # Add player's negative velocity to scroll
        # If player is moving down and is in the bottom buffer, decrease scroll speed
        elif self.player.y >= buffer_bottom and self.player.vy > 0:
            world_scroll_speed -= self.player.vy # Subtract player's positive velocity from scroll
        
        self.background.update(world_scroll_speed)
        self.wall_manager.update(world_scroll_speed)
        
        # Update and filter WBCs
        self.wbcs = self.wall_manager.get_all_wbcs()
        for wbc in self.wbcs:
            wbc.update(world_scroll_speed)

    def _handle_collisions_and_damage(self):
        # Player-WBC collision
        attached_count = 0
        for wbc in self.wbcs:
            if wbc.state == 'ATTACHED':
                attached_count += 1
        if attached_count > 0:
            self.player.take_damage(self.damage_per_wbc * attached_count)

        # Player-wall collision
        player_rect = self.player.image.get_rect(center=(self.player.x, self.player.y))
        colliding_wall_segment = self.wall_manager.check_collision(player_rect)
        if colliding_wall_segment:
            self.player.take_damage(self.wall_damage)
            penetration_depth = self.player.handle_wall_collision(colliding_wall_segment)
            # Reduce scroll speed based on penetration depth
            # Max slowdown when penetration_depth is 32, min slowdown when 0
            slowdown_factor = penetration_depth / 32.0  # Normalize to 0-1
            self.current_scroll_speed = self.base_scroll_speed * (1 - slowdown_factor)
        else:
            self.current_scroll_speed = self.base_scroll_speed

    def _repel_wbcs(self):
        print(f"Attempting to repel WBCs. Player X: {self.player.x}, Y: {self.player.y}, Burst Radius: {self.player.shield_burst_max_radius}")
        for wbc in self.wbcs:
            dist = math.hypot(wbc.x - self.player.x, wbc.y - self.player.y)
            if dist < self.player.shield_burst_max_radius:
                print(f"Repelling WBC at X: {wbc.x}, Y: {wbc.y}, Dist: {dist}")
                wbc.be_repelled(self.player.x, self.player.y, 500)

    def draw(self, screen):
        screen.fill(VEIN_COLOR)
        self.background.draw(screen)
        self.wall_manager.draw(screen)
        self.player.draw(screen)
        for wbc in self.wbcs:
            wbc.draw(screen)
        self._draw_ui(screen)
        if self.game_over:
            self._draw_game_over(screen)

    def _draw_ui(self, screen):
        structure_text = font.render(f"Structure: {int(self.player.current_structure)}", True, UI_COLOR)
        energy_text = font.render(f"Energy: {int(self.player.current_energy)}", True, UI_COLOR)
        screen.blit(structure_text, (10, 10))
        screen.blit(energy_text, (10, 50))

    def _draw_game_over(self, screen):
        over_text = font.render("GAME OVER", True, (255, 0, 0))
        restart_text = font.render("Press 'R' to Restart", True, WHITE)
        over_rect = over_text.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 20))
        restart_rect = restart_text.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 20))
        screen.blit(over_text, over_rect)
        screen.blit(restart_text, restart_rect)

    def reset_game(self):
        self.player.reset()
        self.wbcs = []
        self.game_over = False
        self.wbc_spawn_timer = 0
        self.current_scroll_speed = self.base_scroll_speed
        self.wall_manager = WallManager(WIDTH, HEIGHT, self.base_scroll_speed, self.player)

# Main Game Loop
def main():
    clock = pygame.time.Clock()
    manager = GameManager(WIDTH, HEIGHT)

    while True:
        manager.update()
        manager.draw(screen)
        pygame.display.flip()
        clock.tick(60)

if __name__ == '__main__':
    main()
