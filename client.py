import sys
import os
import pygame
import requests

# 雲端網址已固定為你的 Render 專案
API_BASE_URL = "https://wordle1109.onrender.com"

# 顏色定義
COLOR_BG = (18, 18, 19)
COLOR_TEXT = (255, 255, 255)
COLOR_EMPTY = (58, 58, 60)
COLOR_CORRECT = (83, 141, 78)    # 綠色
COLOR_PRESENT = (181, 159, 59)  # 黃色
COLOR_ABSENT = (58, 58, 60)     # 灰色
COLOR_LINE = (60, 60, 65)

pygame.init()
WIDTH, HEIGHT = 700, 650
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Pygame Wordle + FastAPI Client")
font = pygame.font.SysFont("Arial", 36, bold=True)
small_font = pygame.font.SysFont("Arial", 16)
stats_font = pygame.font.SysFont("Arial", 14)

class WordleGame:
    def __init__(self):
        self.game_id = None
        self.grid = [["" for _ in range(5)] for _ in range(6)]
        self.colors = [[COLOR_EMPTY for _ in range(5)] for _ in range(6)]
        self.history = []
        self.row = 0
        self.col = 0
        self.game_over = False
        self.hard_mode = False
        self.stats = {"total_games": 0, "wins": 0, "win_rate": 0.0}
        self.message = "Press ENTER to submit, H for Hard Mode, R to restart"
        self.start_new_game()

    def update_stats(self):
        try:
            res = requests.get(f"{API_BASE_URL}/api/stats", timeout=10)
            if res.status_code == 200:
                data = res.json()
                total = data["total_games"]
                wins = data["wins"]
                rate = (wins / total * 100) if total > 0 else 0.0
                self.stats = {"total_games": total, "wins": wins, "win_rate": round(rate, 1)}
        except requests.exceptions.RequestException:
            pass

    def start_new_game(self):
        """向 Render 雲端伺服器請求建立新的一局"""
        try:
            res = requests.post(f"{API_BASE_URL}/api/new-game?hard_mode={str(self.hard_mode).lower()}", timeout=60)
            if res.status_code == 200:
                data = res.json()
                self.game_id = data["game_id"]
                self.grid = [["" for _ in range(5)] for _ in range(6)]
                self.colors = [[COLOR_EMPTY for _ in range(5)] for _ in range(6)]
                self.history = []
                self.row = 0
                self.col = 0
                self.game_over = False
                mode_str = "HARD" if self.hard_mode else "Normal"
                self.message = f"New game started! ({mode_str} Mode)"
                if "stats" in data:
                    total = data["stats"]["total_games"]
                    wins = data["stats"]["wins"]
                    rate = (wins / total * 100) if total > 0 else 0.0
                    self.stats = {"total_games": total, "wins": wins, "win_rate": round(rate, 1)}
                else:
                    self.update_stats()
            else:
                self.message = "Server error starting new game."
        except requests.exceptions.RequestException:
            self.message = "Cannot connect to Render server!"

    def toggle_hard_mode(self):
        self.hard_mode = not self.hard_mode
        self.start_new_game()

    def submit_guess(self):
        """將當前行單字發送至雲端 FastAPI 驗證"""
        if self.col < 5:
            self.message = "Not enough letters!"
            return

        guess_word = "".join(self.grid[self.row])
        try:
            payload = {"game_id": self.game_id, "guess": guess_word}
            res = requests.post(f"{API_BASE_URL}/api/guess", json=payload, timeout=60)
            
            if res.status_code == 200:
                data = res.json()
                feedback = data["feedback"]
                
                for i in range(5):
                    if feedback[i] == "correct":
                        self.colors[self.row][i] = COLOR_CORRECT
                    elif feedback[i] == "present":
                        self.colors[self.row][i] = COLOR_PRESENT
                    else:
                        self.colors[self.row][i] = COLOR_ABSENT

                if guess_word not in self.history:
                    self.history.append(guess_word)

                if "stats" in data:
                    total = data["stats"]["total_games"]
                    wins = data["stats"]["wins"]
                    rate = (wins / total * 100) if total > 0 else 0.0
                    self.stats = {"total_games": total, "wins": wins, "win_rate": round(rate, 1)}

                if data["is_correct"]:
                    self.message = "Congratulations! You won! Press R to restart."
                    self.game_over = True
                else:
                    self.row += 1
                    self.col = 0
                    if self.row == 6:
                        target_reveal = data.get("target_word", "")
                        if target_reveal:
                            self.message = f"Game Over! The word was {target_reveal}. Press R."
                        else:
                            self.message = "Game Over! Press R to restart."
                        self.game_over = True
                    else:
                        tries_left = data.get("tries_left", 6 - self.row)
                        self.message = f"Keep guessing! ({tries_left} tries left)"
            else:
                detail = res.json().get("detail", "Error processing guess")
                if detail == "Word not in dictionary":
                    self.message = "Not in word list!"
                elif "Hard Mode" in detail:
                    self.message = "Hard Mode: Must use revealed hint!"
                else:
                    self.message = detail
        except requests.exceptions.RequestException:
            self.message = "Network error during guess!"

    def handle_keydown(self, event):
        if event.key == pygame.K_r:
            self.start_new_game()
            return
        
        if event.key == pygame.K_h:
            self.toggle_hard_mode()
            return

        if self.game_over:
            return

        if event.key == pygame.K_BACKSPACE:
            if self.col > 0:
                self.col -= 1
                self.grid[self.row][self.col] = ""
        elif event.key == pygame.K_RETURN:
            self.submit_guess()
        elif event.unicode.isalpha() and len(event.unicode) == 1:
            if self.col < 5:
                self.grid[self.row][self.col] = event.unicode.upper()
                self.col += 1

    def draw(self, surface):
        surface.fill(COLOR_BG)
        margin_x, margin_y = 45, 50
        box_size = 55
        gap = 8

        for r in range(6):
            for c in range(5):
                x = margin_x + c * (box_size + gap)
                y = margin_y + r * (box_size + gap)
                rect = pygame.Rect(x, y, box_size, box_size)
                
                pygame.draw.rect(surface, self.colors[r][c], rect, border_radius=4)
                if self.colors[r][c] == COLOR_EMPTY:
                    pygame.draw.rect(surface, (80, 80, 80), rect, width=2, border_radius=4)

                char = self.grid[r][c]
                if char:
                    text_surface = font.render(char, True, COLOR_TEXT)
                    text_rect = text_surface.get_rect(center=rect.center)
                    surface.blit(text_surface, text_rect)

        sidebar_x = 500
        pygame.draw.line(surface, COLOR_LINE, (sidebar_x, 0), (sidebar_x, HEIGHT), 2)
        
        total = self.stats["total_games"]
        wins = self.stats["wins"]
        rate = self.stats["win_rate"]
        stats_text = f"Total: {total} | Wins: {wins} | Win Rate: {rate}%"
        stats_surface = stats_font.render(stats_text, True, COLOR_TEXT)
        surface.blit(stats_surface, (sidebar_x + 10, 20))

        history_title = small_font.render("Guessed History:", True, COLOR_TEXT)
        surface.blit(history_title, (sidebar_x + 15, 90))

        hx = sidebar_x + 15
        hy = 125
        for idx, word in enumerate(self.history):
            w_surface = small_font.render(f"{idx+1}. {word}", True, (200, 200, 200))
            surface.blit(w_surface, (hx, hy + idx * 30))

        mode_str = "HARD" if self.hard_mode else "Normal"
        mode_color = (230, 80, 80) if self.hard_mode else (80, 200, 80)
        top_mode_surface = small_font.render(f"Mode: {mode_str}", True, mode_color)
        surface.blit(top_mode_surface, (WIDTH - 120, 15))

        msg_surface = small_font.render(self.message, True, COLOR_TEXT)
        msg_rect = msg_surface.get_rect(center=(WIDTH // 2, HEIGHT - 30))
        surface.blit(msg_surface, msg_rect)

def main():
    clock = pygame.time.Clock()
    game = WordleGame()

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                game.handle_keydown(event)

        game.draw(screen)
        pygame.display.flip()
        clock.tick(30)

if __name__ == "__main__":
    main()
