
import pygame
import sys

class GameStateManager:
    def __init__(self, initial_state, game):
        self.current_state = initial_state
        self.game = game

    def get_state(self):
        return self.current_state

    def set_state(self, new_state):
        print(f"Transitioning from {self.current_state} to {new_state}")
        self.current_state = new_state
        self.game.manage_music() # Manage music on every state change
        if new_state == "HIGH_SCORES":
            self.game.on_enter_high_scores_state()

    def handle_events(self, events):
        # Generic events that can happen in any state
        for event in events:
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            
            # State-specific event handling delegated to the main game class
            if self.current_state == "SPLASH":
                self.game.handle_splash_screen_events(event)
            elif self.current_state == "MENU":
                self.game.handle_menu_events(event)
            elif self.current_state == "GAME":
                self.game.handle_game_events(event)
            elif self.current_state == "PAUSED":
                self.game.handle_pause_menu_events(event)
            elif self.current_state in ["GAME_OVER", "ESCAPED", "ESCAPING", "ELECTROCUTED", "ESCAPED_INPUT_NAME", "DESTRUCTION"]:
                self.game.handle_end_screen_events(event)
            elif self.current_state == "HIGH_SCORES":
                self.game.handle_high_scores_events(event)

    def update(self):
        if self.current_state == "GAME":
            self.game.run_game_update()
        elif self.current_state == "ESCAPING":
            self.game.run_escaping_update()
        elif self.current_state == "ELECTROCUTED":
            self.game.run_electrocuted_update()

    def draw(self, screen):
        if self.current_state == "SPLASH":
            self.game.run_splash_screen_draw(screen)
        elif self.current_state == "MENU":
            self.game.run_menu_draw(screen)
        elif self.current_state == "GAME":
            self.game.run_game_draw(screen)
        elif self.current_state == "PAUSED":
            self.game.run_pause_menu_draw(screen)
        elif self.current_state == "GAME_OVER":
            self.game.run_game_over_draw(screen)
        elif self.current_state == "ESCAPED":
            self.game.run_escaped_draw(screen)
        elif self.current_state == "ESCAPED_INPUT_NAME":
            self.game.run_escaped_input_name_draw(screen)
        elif self.current_state == "ESCAPING":
            self.game.run_game_draw(screen) # Draw game elements during escaping animation
        elif self.current_state == "ELECTROCUTED":
            self.game.run_electrocuted_draw(screen)
        elif self.current_state == "HIGH_SCORES":
            self.game.run_high_scores_draw(screen)
