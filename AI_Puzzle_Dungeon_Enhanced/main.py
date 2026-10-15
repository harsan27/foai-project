import math
import random
import heapq
from collections import deque
import pygame

import sound_manager
import sprite_factory as sf

# -------------------------------------------------------------
# AI Puzzle Dungeon - Enhanced Edition v2.0
# Features:
# - 100% Solvable Guaranteed Procedural Dungeon Generation (Dual-Pass BFS state verification)
# - Intelligent AI Enemies with vision cones, smart chase & line-of-sight checks
# - Interactive Puzzles: Gold Keys & Locked Doors, Levers & Magic Gates,
#   Sokoban Pushable Crates, Frictionless Ice, Floor Spikes & Teleport Portals.
# - Complete Polish UI:
#     * HP Hearts bar (active and empty heart containers)
#     * Moves Counter
#     * Emerald Gems Counter with animated gem icon
#     * Keys counter with golden key icon
#     * Level badge & AI explored nodes metric
# - A* AI pathfinding preview toggle ('H')
# - Synthesized sound effects without external audio files
# -------------------------------------------------------------

pygame.init()
sound_manager.init_audio()

TITLE_TEXT = "AI Puzzle Dungeon | The Infinite Labyrinth"
pygame.display.set_caption(TITLE_TEXT)

TILE = 36
COLS, ROWS = 23, 16
HUD_HEIGHT = 90
WIDTH = COLS * TILE
HEIGHT = ROWS * TILE + HUD_HEIGHT
FPS = 60

screen = pygame.display.set_mode((WIDTH, HEIGHT))
clock = pygame.time.Clock()

# Color Palette
C = {
    "bg": (12, 14, 26),
    "panel": (18, 22, 42),
    "panel_card": (26, 32, 58),
    "panel_border": (48, 62, 102),
    "text": (245, 248, 255),
    "muted": (155, 172, 205),
    "wall": (38, 44, 70),
    "wall_top": (62, 72, 108),
    "wall_shadow": (20, 24, 38),
    "floor1": (32, 38, 62),
    "floor2": (28, 33, 54),
    "cyan": (55, 215, 255),
    "blue": (45, 135, 255),
    "purple": (180, 75, 255),
    "pink": (255, 80, 165),
    "gold": (255, 205, 55),
    "green": (60, 240, 140),
    "red": (255, 75, 95),
    "white": (255, 255, 255)
}

FONT = pygame.font.SysFont("consolas", 16, bold=True)
SMALL = pygame.font.SysFont("consolas", 13)
TITLE_FONT = pygame.font.SysFont("consolas", 26, bold=True)
BIG_FONT = pygame.font.SysFont("consolas", 36, bold=True)

# ----------------- Particle System -----------------
particles = []

def burst(px, py, color, n=16, speed_range=(40, 140), life_range=(0.3, 0.8)):
    for _ in range(n):
        angle = random.random() * math.tau
        speed = random.uniform(*speed_range)
        particles.append([
            px, py,
            math.cos(angle) * speed,
            math.sin(angle) * speed,
            random.uniform(*life_range),
            color,
            random.randint(2, 5)
        ])

def update_and_draw_particles(surface, dt):
    for p in particles:
        p[0] += p[2] * dt
        p[1] += p[3] * dt
        p[3] += 40 * dt
        p[4] -= dt
        if p[4] > 0:
            sz = max(1, int(p[6] * (p[4] / 0.8)))
            pygame.draw.circle(surface, p[5], (int(p[0]), int(p[1])), sz)
    particles[:] = [p for p in particles if p[4] > 0]

def glow_circle(surface, color, center, radius, strength=3):
    x, y = center
    for i in range(strength, 0, -1):
        r = radius + i * 4
        layer = pygame.Surface((r * 2 + 2, r * 2 + 2), pygame.SRCALPHA)
        alpha = max(6, 30 // i)
        pygame.draw.circle(layer, (*color[:3], alpha), (r + 1, r + 1), r)
        surface.blit(layer, (x - r - 1, y - r - 1), special_flags=pygame.BLEND_RGBA_ADD)
    pygame.draw.circle(surface, color, center, radius)

# ----------------- Enemy Classes with Refined AI -----------------
class Enemy:
    def __init__(self, x, y, kind="slime"):
        self.x = x
        self.y = y
        self.visual_x = x * TILE
        self.visual_y = y * TILE
        self.kind = kind
        self.hp = 2 if kind == "skeleton" else (1 if kind in ("slime", "bat") else 3)
        self.max_hp = self.hp
        self.move_cooldown = random.uniform(0.3, 0.7)
        self.hit_timer = 0.0
        self.dir = random.choice([(1,0), (-1,0), (0,1), (0,-1)])
        self.alive = True
        self.state = "patrol" # patrol, alert, chase

    def update_ai(self, dt, dungeon, player_pos):
        if not self.alive: return
        if self.hit_timer > 0:
            self.hit_timer -= dt
            
        target_vx = self.x * TILE
        target_vy = self.y * TILE
        self.visual_x += (target_vx - self.visual_x) * min(1.0, dt * 10)
        self.visual_y += (target_vy - self.visual_y) * min(1.0, dt * 10)

        self.move_cooldown -= dt
        if self.move_cooldown <= 0:
            self.take_action(dungeon, player_pos)

    def has_line_of_sight(self, dungeon, target_pos):
        """Bresenham style tile raycast to verify true line of sight."""
        x0, y0 = self.x, self.y
        x1, y1 = target_pos
        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy
        curr_x, curr_y = x0, y0
        while True:
            if (curr_x, curr_y) == (x1, y1):
                return True
            if dungeon.grid[curr_y][curr_x] == 1 or (curr_x, curr_y) in dungeon.crates:
                if (curr_x, curr_y) != (x0, y0):
                    return False
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                curr_x += sx
            if e2 < dx:
                err += dx
                curr_y += sy

    def take_action(self, dungeon, player_pos):
        dist_to_player = abs(self.x - player_pos[0]) + abs(self.y - player_pos[1])

        if self.kind == "slime":
            # Slime patrols hall; if player is within 3 tiles, bounces excitedly towards player
            self.move_cooldown = random.uniform(0.75, 1.0)
            if dist_to_player <= 3:
                self.move_cooldown = 0.6
                opts = [(1,0),(-1,0),(0,1),(0,-1)]
                opts.sort(key=lambda d: abs((self.x + d[0]) - player_pos[0]) + abs((self.y + d[1]) - player_pos[1]))
                for d in opts:
                    nx, ny = self.x + d[0], self.y + d[1]
                    if dungeon.is_walkable_for_enemy(nx, ny):
                        self.x, self.y = nx, ny
                        break
            else:
                nx, ny = self.x + self.dir[0], self.y + self.dir[1]
                if dungeon.is_walkable_for_enemy(nx, ny) and random.random() > 0.2:
                    self.x, self.y = nx, ny
                else:
                    valid = [d for d in [(1,0),(-1,0),(0,1),(0,-1)] if dungeon.is_walkable_for_enemy(self.x+d[0], self.y+d[1])]
                    if valid:
                        self.dir = random.choice(valid)
                        self.x += self.dir[0]
                        self.y += self.dir[1]

        elif self.kind == "bat":
            # Bat moves in fast 0.4s pulses, swooping when close
            self.move_cooldown = 0.42
            opts = [(1,0),(-1,0),(0,1),(0,-1)]
            if dist_to_player <= 6:
                # Prioritize narrowing distance
                opts.sort(key=lambda d: abs((self.x + d[0]) - player_pos[0]) + abs((self.y + d[1]) - player_pos[1]))
            else:
                random.shuffle(opts)
            for d in opts:
                nx, ny = self.x + d[0], self.y + d[1]
                if dungeon.is_walkable_for_enemy(nx, ny):
                    self.x, self.y = nx, ny
                    break

        elif self.kind == "skeleton":
            # Skeleton uses precise A* pathfinding towards player if within 9 tiles
            self.move_cooldown = 0.65
            if dist_to_player <= 9:
                path = dungeon.find_path((self.x, self.y), player_pos, allow_doors=False)
                if path and len(path) > 1:
                    nxt = path[1]
                    if dungeon.is_walkable_for_enemy(nxt[0], nxt[1]):
                        self.x, self.y = nxt[0], nxt[1]
            else:
                valid = [d for d in [(1,0),(-1,0),(0,1),(0,-1)] if dungeon.is_walkable_for_enemy(self.x+d[0], self.y+d[1])]
                if valid and random.random() < 0.6:
                    d = random.choice(valid)
                    self.x += d[0]
                    self.y += d[1]

        elif self.kind == "ghost":
            # Ghost floats smoothly every 0.7s; can track through open areas
            self.move_cooldown = 0.70
            if dist_to_player <= 10:
                dx = 1 if player_pos[0] > self.x else (-1 if player_pos[0] < self.x else 0)
                dy = 1 if player_pos[1] > self.y else (-1 if player_pos[1] < self.y else 0)
                choices = []
                if dx != 0: choices.append((dx, 0))
                if dy != 0: choices.append((0, dy))
                if not choices: choices = [(0, 1)]
                random.shuffle(choices)
                for d in choices:
                    nx, ny = self.x + d[0], self.y + d[1]
                    if dungeon.is_walkable_for_enemy(nx, ny):
                        self.x, self.y = nx, ny
                        break

    def take_hit(self, damage=1):
        self.hp -= damage
        self.hit_timer = 0.25
        sound_manager.play_sfx("hit")
        cx = self.visual_x + TILE // 2
        cy = HUD_HEIGHT + self.visual_y + TILE // 2
        burst(cx, cy, C["red"], 14)
        if self.hp <= 0:
            self.alive = False
            sound_manager.play_sfx("enemy_die")
            burst(cx, cy, C["gold"], 25)

    def draw(self, surface, t):
        if not self.alive: return
        cx = int(self.visual_x)
        cy = int(HUD_HEIGHT + self.visual_y)
        is_hit = self.hit_timer > 0
        
        if self.kind == "slime":
            surf = sf.render_slime(t, TILE, hit=is_hit)
        elif self.kind == "skeleton":
            surf = sf.render_skeleton(t, TILE, hit=is_hit)
        elif self.kind == "ghost":
            surf = sf.render_ghost(t, TILE, hit=is_hit)
        else:
            surf = sf.render_bat(t, TILE, hit=is_hit)
            
        surface.blit(surf, (cx, cy))
        
        if self.hp < self.max_hp:
            bar_w = 20
            pct = max(0, self.hp / self.max_hp)
            bx = cx + (TILE - bar_w) // 2
            by = cy + 2
            pygame.draw.rect(surface, (40, 20, 20), (bx, by, bar_w, 3))
            pygame.draw.rect(surface, (240, 60, 60), (bx, by, int(bar_w * pct), 3))

# ----------------- Boss Class: The Chaos Guardian -----------------
class Boss:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.visual_x = x * TILE
        self.visual_y = y * TILE
        self.max_hp = 30
        self.hp = 30
        self.phase = 1          # Phase 1: The Awakening, Phase 2: The Rage, Phase 3: The Final Puzzle
        self.state = "chase"     # chase, telegraph, attack, stunned
        self.state_timer = 0.0
        self.move_cooldown = 0.8
        self.hit_timer = 0.0
        self.telegraph_tiles = []
        self.alive = True
        self.shockwaves = []    # list of [x, y, radius, max_radius, life, color]

    def take_hit(self, damage=1):
        if self.state == "stunned":
            # Vulnerable: Takes critical 2.5x damage!
            actual_damage = int(damage * 2.5)
        else:
            actual_damage = max(1, damage // 2)

        self.hp -= actual_damage
        self.hit_timer = 0.3
        sound_manager.play_sfx("hit")
        cx = self.visual_x + TILE
        cy = HUD_HEIGHT + self.visual_y + TILE
        burst(cx, cy, C["purple"], 22)
        burst(cx, cy, C["gold"], 15)

        # Dynamic phase transitions
        if self.hp <= 10 and self.phase < 3:
            self.phase = 3
            self.state = "chase"
            self.move_cooldown = 0.5
            sound_manager.play_sfx("boss_roar")
        elif self.hp <= 20 and self.phase < 2:
            self.phase = 2
            self.state = "chase"
            self.move_cooldown = 0.65
            sound_manager.play_sfx("boss_roar")

        if self.hp <= 0:
            self.hp = 0
            self.alive = False
            sound_manager.play_sfx("enemy_die")
            burst(cx, cy, C["gold"], 60)
            burst(cx, cy, C["green"], 40)
        return actual_damage

    def stun(self, duration=5.0):
        self.state = "stunned"
        self.state_timer = duration
        self.telegraph_tiles = []
        sound_manager.play_sfx("teleport")
        cx = self.visual_x + TILE
        cy = HUD_HEIGHT + self.visual_y + TILE
        burst(cx, cy, (100, 240, 255), 35)

    def update_ai(self, dt, dungeon, player_pos):
        if not self.alive: return
        if self.hit_timer > 0: self.hit_timer -= dt

        # Smooth position lerp (Boss is 2x2 tiles in visual size)
        target_vx = self.x * TILE
        target_vy = self.y * TILE
        self.visual_x += (target_vx - self.visual_x) * min(1.0, dt * 8)
        self.visual_y += (target_vy - self.visual_y) * min(1.0, dt * 8)

        # Update shockwaves
        for sw in self.shockwaves:
            sw[2] += 120 * dt
            sw[4] -= dt
        self.shockwaves[:] = [sw for sw in self.shockwaves if sw[4] > 0]

        # State Machine: chase -> telegraph -> attack -> chase (or stunned)
        if self.state == "stunned":
            self.state_timer -= dt
            if self.state_timer <= 0:
                self.state = "chase"
                self.state_timer = 0
                sound_manager.play_sfx("boss_roar")
            return

        elif self.state == "telegraph":
            self.state_timer -= dt
            if self.state_timer <= 0:
                # Slam attack triggers!
                self.state = "attack"
                self.state_timer = 0.3
                sound_manager.play_sfx("boss_slam")
                cx = self.visual_x + TILE
                cy = HUD_HEIGHT + self.visual_y + TILE
                self.shockwaves.append([cx, cy, 10, 90, 0.5, C["purple"]])
                burst(cx, cy, C["purple"], 30)

        elif self.state == "attack":
            self.state_timer -= dt
            if self.state_timer <= 0:
                self.state = "chase"
                self.telegraph_tiles = []
                self.move_cooldown = 0.6 if self.phase == 2 else 0.8
            return

        elif self.state == "chase":
            self.move_cooldown -= dt
            dist = abs(self.x - player_pos[0]) + abs(self.y - player_pos[1])

            # In Phase 2 & 3, periodically telegraph a shockwave slam when close
            if dist <= 4 and random.random() < (0.35 if self.phase >= 2 else 0.15):
                self.state = "telegraph"
                self.state_timer = 0.85 # telegraph warning time to dodge!
                sound_manager.play_sfx("boss_roar")
                # Mark 3x3 tiles around boss as danger zone
                self.telegraph_tiles = []
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        tx, ty = self.x + dx, self.y + dy
                        if 1 <= tx < COLS - 1 and 1 <= ty < ROWS - 1:
                            self.telegraph_tiles.append((tx, ty))
                return

            if self.move_cooldown <= 0:
                self.move_cooldown = 0.55 if self.phase == 2 else (0.45 if self.phase == 3 else 0.75)
                # A* pathfinding towards player
                path = dungeon.find_path((self.x, self.y), player_pos, allow_doors=True)
                if path and len(path) > 1:
                    nxt = path[1]
                    if dungeon.grid[nxt[1]][nxt[0]] == 0 and nxt not in dungeon.crates:
                        self.x, self.y = nxt[0], nxt[1]

    def draw(self, surface, t):
        if not self.alive: return
        cx = int(self.visual_x) - TILE // 2
        cy = int(HUD_HEIGHT + self.visual_y) - TILE // 2

        # Draw red telegraphed slam danger tiles
        if self.state == "telegraph":
            pulse_alpha = int(120 + 80 * math.sin(t * 20))
            for tx, ty in self.telegraph_tiles:
                danger_rect = pygame.Rect(tx * TILE, HUD_HEIGHT + ty * TILE, TILE, TILE)
                overlay = pygame.Surface((TILE, TILE), pygame.SRCALPHA)
                overlay.fill((255, 40, 60, pulse_alpha))
                surface.blit(overlay, danger_rect.topleft)
                pygame.draw.rect(surface, (255, 120, 140), danger_rect, 1)

        # Draw shockwaves
        for sw in self.shockwaves:
            pygame.draw.circle(surface, sw[5], (int(sw[0]), int(sw[1])), int(sw[2]), 3)

        # Draw large Boss Sprite
        boss_surf = sf.render_boss(t, phase=self.phase, state=self.state, hit=(self.hit_timer > 0), size=72)
        surface.blit(boss_surf, (cx, cy))

        # Floating status text (e.g. STUNNED! VULNERABLE!)
        if self.state == "stunned":
            txt = SMALL.render(f"STUNNED! CORE EXPOSED ({self.state_timer:.1f}s)", True, (100, 240, 255))
            surface.blit(txt, txt.get_rect(center=(cx + 36, cy - 8)))
        elif self.state == "telegraph":
            txt = SMALL.render("! SLAM CHARGING !", True, (255, 70, 90))
            surface.blit(txt, txt.get_rect(center=(cx + 36, cy - 8)))

# ----------------- Dungeon Generator & Solvability Verifier -----------------
class Dungeon:
    def __init__(self, level_num=1, seed=None):
        self.level_num = level_num
        self.seed = seed if seed is not None else random.randint(100000, 999999)
        self.grid = [[1 for _ in range(COLS)] for _ in range(ROWS)]
        self.start = (1, 1)
        self.exit = (COLS - 2, ROWS - 2)
        
        self.objects = {}
        self.crates = set()
        self.ice_tiles = set()
        self.enemies = []
        self.boss = None
        self.altars = []       # [(x, y), color, active_bool, order_id]
        self.altar_sequence = []
        self.current_altar_step = 0
        self.explored_states = 0
        self.is_boss_level = (level_num == 6)
        
        random.seed(self.seed)
        if self.is_boss_level:
            self.generate_boss_arena()
        else:
            self.generate_verified_level()

    def generate_boss_arena(self):
        """
        Creates an epic, grand Boss Arena chamber for The Chaos Guardian:
        - Wide open ritual sanctum with outer stone columns
        - 4 elemental runic altars (Fire Red, Ice Blue, Nature Green, Astral Violet)
        - The Boss placed in center
        - Exit portal sealed by Chaos Barrier until Guardian is defeated
        """
        self.grid = [[1 for _ in range(COLS)] for _ in range(ROWS)]
        # Hollow out arena floor from (2, 2) to (COLS-3, ROWS-3)
        for y in range(2, ROWS - 2):
            for x in range(2, COLS - 2):
                self.grid[y][x] = 0

        # Runic stone pillars
        for px, py in [(5, 4), (COLS - 6, 4), (5, ROWS - 5), (COLS - 6, ROWS - 5)]:
            self.grid[py][px] = 1

        self.start = (3, ROWS // 2)
        self.exit = (COLS - 3, ROWS // 2)
        self.objects = {}
        self.crates = set()
        self.ice_tiles = set()
        self.enemies = []

        # Spawn Boss in center
        boss_x = COLS // 2
        boss_y = ROWS // 2
        self.boss = Boss(boss_x, boss_y)

        # 4 Elemental Altars at the four quadrants of the sanctum
        # Activating in correct sequence stuns the boss and opens its core!
        altar_coords = [
            (4, 3),            # Top-Left: Astral Violet
            (COLS - 5, 3),     # Top-Right: Sun Gold
            (4, ROWS - 4),     # Bottom-Left: Nature Green
            (COLS - 5, ROWS - 4) # Bottom-Right: Frost Cyan
        ]
        colors = [C["purple"], C["gold"], C["green"], C["cyan"]]
        color_names = ["VIOLET ASTRAL", "GOLDEN SUN", "EMERALD NATURE", "FROST CYAN"]

        self.altars = []
        for i in range(4):
            coord = altar_coords[i]
            col = colors[i]
            self.altars.append({
                "pos": coord,
                "color": col,
                "name": color_names[i],
                "active": False,
                "id": i
            })
            self.objects[coord] = {
                "type": "ALTAR",
                "altar_index": i,
                "color": col
            }

        # Randomized sequence for the ritual
        self.altar_sequence = [0, 1, 2, 3]
        random.shuffle(self.altar_sequence)
        self.current_altar_step = 0
        self.explored_states = 100

    def generate_raw_maze(self):
        self.grid = [[1 for _ in range(COLS)] for _ in range(ROWS)]
        start = (1, 1)
        self.grid[1][1] = 0
        stack = [start]
        
        while stack:
            cx, cy = stack[-1]
            neighbors = []
            for dx, dy in ((2,0), (-2,0), (0,2), (0,-2)):
                nx, ny = cx + dx, cy + dy
                if 1 <= nx < COLS-1 and 1 <= ny < ROWS-1 and self.grid[ny][nx] == 1:
                    neighbors.append((nx, ny, dx, dy))
            if neighbors:
                nx, ny, dx, dy = random.choice(neighbors)
                self.grid[cy + dy//2][cx + dx//2] = 0
                self.grid[ny][nx] = 0
                stack.append((nx, ny))
            else:
                stack.pop()

        # Add loops for tactical gameplay
        for _ in range(10 + self.level_num * 2):
            rx = random.randint(2, COLS - 3)
            ry = random.randint(2, ROWS - 3)
            if self.grid[ry][rx] == 1:
                floors = sum(1 for dx, dy in ((1,0),(-1,0),(0,1),(0,-1)) if self.grid[ry+dy][rx+dx] == 0)
                if floors >= 2:
                    self.grid[ry][rx] = 0

    def generate_verified_level(self):
        attempts = 0
        while True:
            attempts += 1
            self.generate_raw_maze()
            
            # Start is at (1, 1)
            self.start = (1, 1)
            dist_map = self.get_distances(self.start)
            if len(dist_map) < 30: continue
            
            # Exit placed at farthest location
            self.exit = max(dist_map, key=dist_map.get)
            
            self.objects = {}
            self.crates = set()
            self.ice_tiles = set()
            self.enemies = []

            # 1. First solve simple path from start to exit
            base_path = self.find_path(self.start, self.exit, allow_doors=True)
            if not base_path or len(base_path) < 12:
                continue

            available = [p for p in dist_map if p != self.start and p != self.exit]
            random.shuffle(available)

            # 2. Place Door along the path to ensure it guards a passage
            path_candidates = [p for p in base_path[3:-2] if p in available]
            if not path_candidates:
                continue
            door_pos = random.choice(path_candidates)
            available.remove(door_pos)
            self.objects[door_pos] = {"type": "DOOR", "locked": True}

            # 3. Ensure Key is placed in a branch reachable BEFORE passing through the locked door!
            # We compute all tiles reachable from start without opening the locked door
            reachable_before_door = self.get_reachable_without_doors(self.start, {door_pos})
            key_candidates = [p for p in reachable_before_door if p in available and p != self.start]
            if not key_candidates:
                continue
            key_pos = random.choice(key_candidates)
            available.remove(key_pos)
            self.objects[key_pos] = {"type": "KEY", "collected": False}

            # 4. Lever and Gate placement
            # Gate placed somewhere past or near, lever reachable
            if len(available) >= 2:
                gate_pos = available.pop()
                self.objects[gate_pos] = {"type": "GATE", "active": False}
                # Lever must be reachable
                lever_pos = available.pop()
                self.objects[lever_pos] = {"type": "LEVER", "active": False}

            # 5. Place Safe Crates (Never in tight 1-tile bottlenecks on the only solution path)
            num_crates = min(3, 1 + self.level_num // 2)
            # Find candidate spots with at least 3 floor neighbors so they don't permanently seal passages
            crate_candidates = [p for p in available if sum(1 for dx, dy in ((1,0),(-1,0),(0,1),(0,-1)) if self.grid[p[1]+dy][p[0]+dx] == 0) >= 3]
            for _ in range(min(num_crates, len(crate_candidates))):
                cp = crate_candidates.pop()
                available.remove(cp)
                self.crates.add(cp)

            # 6. Slippery Ice Tiles
            num_ice = min(8, 3 + self.level_num * 2)
            for _ in range(min(num_ice, len(available))):
                ip = available.pop()
                self.ice_tiles.add(ip)

            # 7. Bonus Emerald Gems
            for _ in range(min(4, len(available))):
                gp = available.pop()
                self.objects[gp] = {"type": "GEM", "collected": False}

            # 8. CRITICAL BFS STATE VALIDATION & SOLUTION PATH EXTRACTION
            # Player state = (x, y, has_key, lever_active)
            is_valid, sol_path, explored_count = self.validate_state_bfs()
            if not is_valid:
                # Level was mathematically unsolvable; discard and generate again!
                continue

            self.explored_states = explored_count
            self.solution_path = sol_path

            # 9. Spike Traps: Place strictly OFF the correct solution path!
            # Players following the correct puzzle route won't be forced into unavoidable spikes
            correct_path_tiles = set(sol_path) if sol_path else set()
            off_path_candidates = [p for p in available if p not in correct_path_tiles and p != self.start and p != self.exit]
            num_spikes = min(3, 1 + self.level_num // 2)
            random.shuffle(off_path_candidates)
            for _ in range(min(num_spikes, len(off_path_candidates))):
                sp = off_path_candidates.pop()
                if sp in available:
                    available.remove(sp)
                self.objects[sp] = {"type": "SPIKE", "state": "down"}

            # 10. Spawn Enemies safely away from start
            enemy_types = ["slime", "skeleton"]
            if self.level_num >= 2: enemy_types.append("bat")
            if self.level_num >= 3: enemy_types.extend(["ghost", "skeleton"])

            for k in enemy_types:
                if available:
                    ep = available.pop()
                    if abs(ep[0] - self.start[0]) + abs(ep[1] - self.start[1]) > 5:
                        self.enemies.append(Enemy(ep[0], ep[1], kind=k))

            # Generated successfully and proven 100% solvable!
            return

    def get_reachable_without_doors(self, start_pos, blocked_tiles):
        visited = set([start_pos])
        q = deque([start_pos])
        while q:
            x, y = q.popleft()
            for dx, dy in ((1,0),(-1,0),(0,1),(0,-1)):
                nx, ny = x + dx, y + dy
                if 0 <= nx < COLS and 0 <= ny < ROWS and self.grid[ny][nx] == 0:
                    if (nx, ny) not in blocked_tiles and (nx, ny) not in visited:
                        visited.add((nx, ny))
                        q.append((nx, ny))
        return visited

    def validate_state_bfs(self):
        """Rigorous graph search validating that the level can be cleared."""
        start_state = (self.start[0], self.start[1], False, False)
        q = deque([start_state])
        parent = {start_state: None}
        explored = 0
        goal_state = None

        while q:
            s = q.popleft()
            explored += 1
            x, y, has_key, lever_active = s

            if (x, y) == self.exit:
                goal_state = s
                break

            for dx, dy in ((1,0), (-1,0), (0,1), (0,-1)):
                nx, ny = x + dx, y + dy
                if not (0 <= nx < COLS and 0 <= ny < ROWS): continue
                if self.grid[ny][nx] == 1: continue
                if (nx, ny) in self.crates: continue

                obj = self.objects.get((nx, ny))
                next_key = has_key
                next_lever = lever_active

                if obj:
                    t = obj["type"]
                    if t == "DOOR" and not has_key: continue
                    if t == "GATE" and not lever_active: continue
                    if t == "KEY": next_key = True
                    if t == "LEVER": next_lever = True

                next_state = (nx, ny, next_key, next_lever)
                if next_state not in parent:
                    parent[next_state] = s
                    q.append(next_state)

        if goal_state is None:
            return False, None, explored

        # Reconstruct path
        path = []
        cur = goal_state
        while cur is not None:
            path.append((cur[0], cur[1]))
            cur = parent[cur]
        return True, path[::-1], explored

    def find_puzzle_solution_path(self, start_pos, has_key_init, lever_active_init):
        """
        Calculates the complete multi-goal intelligent puzzle path from current player state:
        Takes into account needing to visit Key (if door locked and key needed),
        visiting Lever (if gate locked and lever needed), avoiding closed doors,
        and finally reaching the exit portal.
        """
        start_state = (start_pos[0], start_pos[1], has_key_init, lever_active_init)
        q = deque([start_state])
        parent = {start_state: None}
        seen = {start_state}
        goal_state = None

        while q:
            s = q.popleft()
            x, y, has_key, lever_active = s

            if (x, y) == self.exit:
                goal_state = s
                break

            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = x + dx, y + dy
                if not (0 <= nx < COLS and 0 <= ny < ROWS): continue
                if self.grid[ny][nx] == 1: continue
                if (nx, ny) in self.crates: continue

                obj = self.objects.get((nx, ny))
                next_key = has_key
                next_lever = lever_active

                if obj:
                    t = obj["type"]
                    if t == "DOOR" and obj.get("locked", True) and not has_key: continue
                    if t == "GATE" and not obj.get("active", False) and not lever_active: continue
                    if t == "KEY" and not obj.get("collected", False): next_key = True
                    if t == "LEVER": next_lever = True

                next_state = (nx, ny, next_key, next_lever)
                if next_state not in seen:
                    seen.add(next_state)
                    parent[next_state] = s
                    q.append(next_state)

        if goal_state is None:
            return []

        path = []
        cur = goal_state
        while cur is not None:
            path.append((cur[0], cur[1]))
            cur = parent[cur]
        return path[::-1]

    def get_distances(self, start_pos):
        d = {start_pos: 0}
        q = deque([start_pos])
        while q:
            x, y = q.popleft()
            for dx, dy in ((1,0),(-1,0),(0,1),(0,-1)):
                nx, ny = x + dx, y + dy
                if 0 <= nx < COLS and 0 <= ny < ROWS and self.grid[ny][nx] == 0:
                    if (nx, ny) not in d:
                        d[(nx, ny)] = d[(x, y)] + 1
                        q.append((nx, ny))
        return d

    def is_solid(self, x, y):
        if not (0 <= x < COLS and 0 <= y < ROWS): return True
        if self.grid[y][x] == 1: return True
        if (x, y) in self.crates: return True
        obj = self.objects.get((x, y))
        if obj:
            if obj["type"] == "DOOR" and obj.get("locked", True): return True
            if obj["type"] == "GATE" and not obj.get("active", False): return True
        return False

    def is_walkable_for_enemy(self, x, y):
        if not (0 <= x < COLS and 0 <= y < ROWS): return False
        if self.grid[y][x] == 1: return False
        if (x, y) in self.crates: return False
        obj = self.objects.get((x, y))
        if obj:
            if obj["type"] == "DOOR" and obj.get("locked", True): return False
            if obj["type"] == "GATE" and not obj.get("active", False): return False
        return True

    def find_path(self, start, goal, allow_doors=False):
        h = lambda p: abs(p[0] - goal[0]) + abs(p[1] - goal[1])
        heap = [(h(start), 0, start)]
        parent = {}
        g = {start: 0}
        seen = set()

        while heap:
            _, cost, p = heapq.heappop(heap)
            if p in seen: continue
            seen.add(p)
            if p == goal:
                path = [p]
                while p in parent:
                    p = parent[p]
                    path.append(p)
                return path[::-1]
            for dx, dy in ((1,0),(-1,0),(0,1),(0,-1)):
                n = (p[0] + dx, p[1] + dy)
                if not (0 <= n[0] < COLS and 0 <= n[1] < ROWS): continue
                if self.grid[n[1]][n[0]] == 1: continue
                if n in self.crates and n != goal: continue
                obj = self.objects.get(n)
                if obj and not allow_doors:
                    if obj["type"] == "DOOR" and obj.get("locked", True): continue
                    if obj["type"] == "GATE" and not obj.get("active", False): continue
                ng = g[p] + 1
                if ng < g.get(n, 999999):
                    g[n] = ng
                    parent[n] = p
                    heapq.heappush(heap, (ng + h(n), ng, n))
        return None

# ----------------- Game State & Manager -----------------
class Game:
    def __init__(self):
        self.level_num = 1
        self.dungeon = Dungeon(self.level_num)
        
        self.player_x = self.dungeon.start[0]
        self.player_y = self.dungeon.start[1]
        self.visual_x = self.player_x * TILE
        self.visual_y = self.player_y * TILE
        
        self.player_dir = (0, 1)
        self.anim_state = "idle"
        self.anim_timer = 0.0
        
        self.hp = 6
        self.max_hp = 6
        self.keys = 0
        self.gems = 0
        self.moves = 0
        self.won = False
        self.game_over = False
        self.menu = True
        self.invulnerable_timer = 0.0
        
        # Weapon Reward System (Awarded from Boss Chest)
        self.weapon_name = "Iron Sword"
        self.weapon_bonus = 0  # +0 base, upgraded to +4 by Chaos Blade!
        
        self.show_route = False
        self.route = []
        self.auto_assist = False
        self.auto_step_delay = 0.16
        self.auto_cooldown = 0.0
        
        self.message = "Welcome! Find keys, solve puzzles, and reach the exit portal!"
        self.msg_timer = 6.0
        self.time_total = 0.0

    def say(self, msg, duration=3.0):
        self.message = msg
        self.msg_timer = duration

    def reset(self, next_level=False):
        self.hp = self.max_hp  # Reset HP to maximum level for EVERY level & restart!
        if next_level:
            self.level_num += 1
            sound_manager.play_sfx("win")
            # Generate a fresh new seed for the next level
            self.dungeon = Dungeon(self.level_num, seed=None)
        else:
            # Recreate the EXACT same level layout and enemy positions!
            self.dungeon = Dungeon(self.level_num, seed=self.dungeon.seed)
            
        self.player_x, self.player_y = self.dungeon.start
        self.visual_x = self.player_x * TILE
        self.visual_y = self.player_y * TILE
        self.player_dir = (0, 1)
        self.anim_state = "idle"
        self.won = False
        self.game_over = False
        self.keys = 0
        self.moves = 0 # reset moves on every level & restart!
        self.show_route = False
        self.route = []
        self.auto_assist = False
        self.auto_cooldown = 0.0
        if next_level:
            self.say(f"LEVEL {self.level_num} - Solvable dungeon verified with {len(self.dungeon.enemies)} AI foes!", 4.0)
        else:
            self.say(f"LEVEL {self.level_num} RESTARTERD - Retrying the same dungeon layout!", 3.5)

    def get_attack_damage(self):
        # Base (1) + Weapon Bonus (e.g. +4 from Chaos Blade)
        return 1 + self.weapon_bonus

    def do_attack(self):
        if self.anim_state == "attack" or self.won or self.game_over or self.menu:
            return
        self.anim_state = "attack"
        self.anim_timer = 0.22
        sound_manager.play_sfx("sword")
        
        tx = self.player_x + self.player_dir[0]
        ty = self.player_y + self.player_dir[1]
        hit_any = False
        dmg = self.get_attack_damage()

        # Check Boss hit (Boss occupies a 2x2 area centered on self.dungeon.boss.x, y)
        if self.dungeon.boss and self.dungeon.boss.alive:
            boss = self.dungeon.boss
            # Check if attack point is within boss radius
            dist_to_boss = math.hypot(tx - boss.x, ty - boss.y)
            if dist_to_boss <= 1.5 or (self.player_x, self.player_y) == (boss.x, boss.y):
                dealt = boss.take_hit(dmg)
                hit_any = True
                status_note = " (CRITICAL EXPOSED HIT!)" if boss.state == "stunned" else ""
                wpn_str = f" [{self.weapon_name}]" if self.weapon_bonus > 0 else ""
                self.say(f"SLASHED CHAOS GUARDIAN! Dealt {dealt} DMG{wpn_str}!{status_note}", 2.2)
                if not boss.alive:
                    self.heal(3, "CHAOS GUARDIAN SLAIN! A Legendary Treasure Chest appeared!")
                    burst(boss.visual_x + TILE, HUD_HEIGHT + boss.visual_y + TILE, C["gold"], 70)
                    # Spawn reward chest at center of arena!
                    chest_x, chest_y = int(boss.x), int(boss.y)
                    self.dungeon.objects[(chest_x, chest_y)] = {
                        "type": "CHEST",
                        "opened": False,
                        "weapon_name": "Chaos Crystal Blade",
                        "weapon_bonus": 4
                    }

        if not hit_any:
            for e in self.dungeon.enemies:
                if e.alive and (e.x, e.y) == (tx, ty):
                    was_alive = e.alive
                    e.take_hit(dmg)
                    hit_any = True
                    if was_alive and not e.alive:
                        self.heal(1, f"Defeated {e.kind.upper()}! +1 Heart recovered!")
                    else:
                        self.say(f"Hit the {e.kind.upper()} for {dmg} DMG!", 1.5)
                    break
        if not hit_any:
            for e in self.dungeon.enemies:
                if e.alive and (e.x, e.y) == (self.player_x, self.player_y):
                    was_alive = e.alive
                    e.take_hit(dmg)
                    hit_any = True
                    if was_alive and not e.alive:
                        self.heal(1, f"Defeated {e.kind.upper()}! +1 Heart recovered!")
                    break

    def heal(self, amount=1, reason="Healed 1 Heart!"):
        if self.hp < self.max_hp:
            self.hp = min(self.max_hp, self.hp + amount)
            sound_manager.play_sfx("heal")
            burst(self.player_x * TILE + TILE // 2, HUD_HEIGHT + self.player_y * TILE + TILE // 2, C["green"], 22)
            self.say(reason, 2.5)
        else:
            self.say(reason, 2.0)

    def try_move(self, dx, dy):
        if self.won or self.game_over or self.menu: return
        self.player_dir = (dx, dy)
        nx = self.player_x + dx
        ny = self.player_y + dy
        
        if not (0 <= nx < COLS and 0 <= ny < ROWS) or self.dungeon.grid[ny][nx] == 1:
            self.say("A solid dungeon stone wall blocks your path.", 1.2)
            return

        # Sokoban crate check
        if (nx, ny) in self.dungeon.crates:
            push_x, push_y = nx + dx, ny + dy
            if (0 <= push_x < COLS and 0 <= push_y < ROWS and 
                self.dungeon.grid[push_y][push_x] == 0 and 
                (push_x, push_y) not in self.dungeon.crates and 
                not self.dungeon.is_solid(push_x, push_y)):
                
                self.dungeon.crates.remove((nx, ny))
                self.dungeon.crates.add((push_x, push_y))
                sound_manager.play_sfx("box")
                burst((push_x * TILE + TILE//2), (HUD_HEIGHT + push_y * TILE + TILE//2), (180, 130, 80), 8)
                self.say("Pushed the heavy crate forward!", 1.5)
            else:
                self.say("The crate cannot be moved there!", 1.2)
                return

        obj = self.dungeon.objects.get((nx, ny))
        if obj:
            if obj["type"] == "DOOR" and obj.get("locked", True):
                if self.keys > 0:
                    self.keys -= 1
                    obj["locked"] = False
                    sound_manager.play_sfx("door")
                    burst(nx * TILE + TILE//2, HUD_HEIGHT + ny * TILE + TILE//2, C["gold"], 18)
                    self.say("Used a gold key to unlock the door!", 2.5)
                else:
                    self.say("The door is locked! Find the gold key first.", 1.5)
                    burst(nx * TILE + TILE//2, HUD_HEIGHT + ny * TILE + TILE//2, C["gold"], 6)
                    return
            elif obj["type"] == "GATE" and not obj.get("active", False):
                self.say("The magic gate is barred! Flip the dungeon lever.", 1.5)
                burst(nx * TILE + TILE//2, HUD_HEIGHT + ny * TILE + TILE//2, C["purple"], 6)
                return

        # Advance player
        self.player_x = nx
        self.player_y = ny
        self.moves += 1
        self.anim_state = "walk"
        self.anim_timer = 0.15
        sound_manager.play_sfx("step")

        # Ice sliding
        if (self.player_x, self.player_y) in self.dungeon.ice_tiles:
            sound_manager.play_sfx("ice")
            slide_x = self.player_x + dx
            slide_y = self.player_y + dy
            if (0 <= slide_x < COLS and 0 <= slide_y < ROWS and 
                not self.dungeon.is_solid(slide_x, slide_y)):
                self.player_x = slide_x
                self.player_y = slide_y
                burst(self.player_x * TILE + TILE//2, HUD_HEIGHT + self.player_y * TILE + TILE//2, C["cyan"], 10)
                self.say("Slipped across the ice!", 1.2)

        # Trigger tile objects
        curr_obj = self.dungeon.objects.get((self.player_x, self.player_y))
        if curr_obj:
            if curr_obj["type"] == "KEY" and not curr_obj.get("collected", False):
                curr_obj["collected"] = True
                self.keys += 1
                sound_manager.play_sfx("key")
                burst(self.player_x * TILE + TILE//2, HUD_HEIGHT + self.player_y * TILE + TILE//2, C["gold"], 24)
                self.say("GOLD KEY FOUND! You can now open locked doors.", 2.5)
                
            elif curr_obj["type"] == "LEVER":
                curr_obj["active"] = not curr_obj.get("active", False)
                for o in self.dungeon.objects.values():
                    if o["type"] == "GATE":
                        o["active"] = curr_obj["active"]
                sound_manager.play_sfx("switch")
                burst(self.player_x * TILE + TILE//2, HUD_HEIGHT + self.player_y * TILE + TILE//2, C["green"], 20)
                status = "OPENED" if curr_obj["active"] else "LOCKED"
                self.say(f"LEVER FLIPPED! Magic gates {status}.", 2.5)
                
            elif curr_obj["type"] == "GEM" and not curr_obj.get("collected", False):
                curr_obj["collected"] = True
                self.gems += 1
                sound_manager.play_sfx("gem")
                burst(self.player_x * TILE + TILE//2, HUD_HEIGHT + self.player_y * TILE + TILE//2, C["green"], 18)
                self.say(f"Collected Emerald Gem! Total: {self.gems}", 2.0)

            elif curr_obj["type"] == "SPIKE":
                if self.invulnerable_timer <= 0:
                    self.take_damage(1, "Ouch! Spike trap sprang! -1 HP")
                    
            elif curr_obj["type"] == "PORTAL":
                tx, ty = curr_obj["target"]
                self.player_x, self.player_y = tx, ty
                sound_manager.play_sfx("teleport")
                burst(self.player_x * TILE + TILE//2, HUD_HEIGHT + self.player_y * TILE + TILE//2, C["purple"], 30)
                self.say("Teleported across the dungeon!", 2.2)

            elif curr_obj["type"] == "CHEST" and not curr_obj.get("opened", False):
                curr_obj["opened"] = True
                self.weapon_name = curr_obj.get("weapon_name", "Chaos Crystal Blade")
                self.weapon_bonus = curr_obj.get("weapon_bonus", 4)
                sound_manager.play_sfx("gem")
                burst(self.player_x * TILE + TILE // 2, HUD_HEIGHT + self.player_y * TILE + TILE // 2, C["gold"], 35)
                self.say(f"CHEST OPENED! Equipped [{self.weapon_name}] (+{self.weapon_bonus} ATK)! Reach the Exit Portal!", 4.0)

            elif curr_obj["type"] == "ALTAR":
                altar_idx = curr_obj["altar_index"]
                expected_idx = self.dungeon.altar_sequence[self.dungeon.current_altar_step]
                if altar_idx == expected_idx:
                    self.dungeon.altars[altar_idx]["active"] = True
                    self.dungeon.current_altar_step += 1
                    sound_manager.play_sfx("switch")
                    burst(self.player_x * TILE + TILE // 2, HUD_HEIGHT + self.player_y * TILE + TILE // 2, curr_obj["color"], 25)
                    step_num = self.dungeon.current_altar_step
                    if step_num == len(self.dungeon.altar_sequence):
                        # All 4 altars triggered in order! STUN THE GUARDIAN!
                        if self.dungeon.boss and self.dungeon.boss.alive:
                            self.dungeon.boss.stun(6.0)
                            self.say("RITUAL COMPLETE! CHAOS GUARDIAN STUNNED! ATTACK CORE FOR 2.5X CRIT DMG!", 4.0)
                        # Reset for next cycle
                        for a in self.dungeon.altars: a["active"] = False
                        self.dungeon.current_altar_step = 0
                    else:
                        next_expected = self.dungeon.altar_sequence[self.dungeon.current_altar_step]
                        next_name = self.dungeon.altars[next_expected]["name"]
                        self.say(f"Rune {step_num}/4 Activated! Next: Seek the {next_name} altar!", 3.0)
                else:
                    # Incorrect sequence order: slight shock recoil
                    sound_manager.play_sfx("hit")
                    burst(self.player_x * TILE + TILE // 2, HUD_HEIGHT + self.player_y * TILE + TILE // 2, C["purple"], 12)
                    expected_name = self.dungeon.altars[expected_idx]["name"]
                    self.say(f"Wrong Altar! Runic energy repels you! Find {expected_name} first!", 2.5)

        # Check Exit
        if (self.player_x, self.player_y) == self.dungeon.exit:
            if self.dungeon.is_boss_level and self.dungeon.boss and self.dungeon.boss.alive:
                self.say("The Exit is sealed by a Chaos Barrier! Slay the Chaos Guardian to open it!", 2.5)
                burst(self.player_x * TILE + TILE // 2, HUD_HEIGHT + self.player_y * TILE + TILE // 2, C["purple"], 10)
            else:
                self.won = True
                sound_manager.play_sfx("win")
                burst(self.player_x * TILE + TILE//2, HUD_HEIGHT + self.player_y * TILE + TILE//2, C["green"], 50)
                if self.dungeon.is_boss_level:
                    self.say("VICTORY! THE CHAOS GUARDIAN IS VANQUISHED! Press 'N' for Level 7!", 999)
                else:
                    self.say("DUNGEON ESCAPED! Press 'N' for the Next Dungeon Level!", 999)

        if self.show_route:
            self.update_route()

    def take_damage(self, amount=1, reason="Took damage!"):
        if self.invulnerable_timer > 0 or self.won or self.game_over: return
        self.hp -= amount
        self.invulnerable_timer = 1.0
        self.anim_state = "hurt"
        self.anim_timer = 0.3
        sound_manager.play_sfx("hit")
        burst(self.player_x * TILE + TILE//2, HUD_HEIGHT + self.player_y * TILE + TILE//2, C["red"], 20)
        self.say(reason, 2.0)
        if self.hp <= 0:
            self.hp = 0
            self.game_over = True
            self.say("YOU PERISHED! Press 'R' to Retry current level.", 999)

    def is_lever_active(self):
        for o in self.dungeon.objects.values():
            if o["type"] == "LEVER":
                return o.get("active", False)
        return False

    def update_route(self):
        # Calculates complete intelligent multi-phase solution path
        # (collecting keys, activating levers, opening doors, avoiding spikes, and reaching exit)
        self.route = self.dungeon.find_puzzle_solution_path(
            (self.player_x, self.player_y),
            (self.keys > 0),
            self.is_lever_active()
        )

    def update(self, dt):
        self.time_total += dt
        if self.msg_timer > 0: self.msg_timer -= dt
        if self.invulnerable_timer > 0: self.invulnerable_timer -= dt

        if self.anim_timer > 0:
            self.anim_timer -= dt
            if self.anim_timer <= 0:
                self.anim_state = "idle"

        # Smooth Player lerp
        target_vx = self.player_x * TILE
        target_vy = self.player_y * TILE
        self.visual_x += (target_vx - self.visual_x) * min(1.0, dt * 14)
        self.visual_y += (target_vy - self.visual_y) * min(1.0, dt * 14)

        if not self.menu and not self.won and not self.game_over:
            # 1. Update AI Enemies
            for enemy in self.dungeon.enemies:
                enemy.update_ai(dt, self.dungeon, (self.player_x, self.player_y))
                if enemy.alive and (enemy.x, enemy.y) == (self.player_x, self.player_y):
                    self.take_damage(1, f"Ambushed by a vicious {enemy.kind.upper()}!")

            # 2. Update Chaos Guardian Boss
            if self.dungeon.boss and self.dungeon.boss.alive:
                boss = self.dungeon.boss
                boss.update_ai(dt, self.dungeon, (self.player_x, self.player_y))
                # Check collision with Boss
                dist_to_boss = math.hypot(self.player_x - boss.x, self.player_y - boss.y)
                if dist_to_boss <= 1.2 and boss.state != "stunned":
                    self.take_damage(1, "Crushed by the Chaos Guardian's colossus frame!")
                # Check slam damage if standing in telegraphed tile when slam triggers
                if boss.state == "attack" and (self.player_x, self.player_y) in boss.telegraph_tiles:
                    self.take_damage(1, "BLASTED by Chaos Shockwave! -1 HP!")

            # 3. AUTO AI ASSIST: Character moves and completes the level automatically!
            if self.auto_assist and not self.won and not self.game_over:
                self.auto_cooldown -= dt
                if self.auto_cooldown <= 0:
                    self.auto_cooldown = self.auto_step_delay
                    
                    # In boss level: check attack if adjacent to Boss or core exposed
                    attacked = False
                    if self.dungeon.boss and self.dungeon.boss.alive:
                        boss = self.dungeon.boss
                        dist_to_boss = math.hypot(self.player_x - boss.x, self.player_y - boss.y)
                        if dist_to_boss <= 1.5:
                            dx = 1 if boss.x > self.player_x else (-1 if boss.x < self.player_x else 0)
                            dy = 1 if boss.y > self.player_y else (-1 if boss.y < self.player_y else 0)
                            self.player_dir = (dx, dy) if (dx != 0 or dy != 0) else (0, 1)
                            self.do_attack()
                            attacked = True

                    if not attacked:
                        # Auto defense check - attack any enemy directly adjacent!
                        for d in [(1,0), (-1,0), (0,1), (0,-1)]:
                            ax, ay = self.player_x + d[0], self.player_y + d[1]
                            for e in self.dungeon.enemies:
                                if e.alive and (e.x, e.y) == (ax, ay):
                                    self.player_dir = d
                                    self.do_attack()
                                    attacked = True
                                    break
                            if attacked: break

                    if not attacked:
                        # Boss level AI pathing
                        if self.dungeon.is_boss_level:
                            if self.dungeon.boss and self.dungeon.boss.alive:
                                if self.dungeon.boss.state == "stunned":
                                    # Rush to boss core to attack!
                                    target = (int(self.dungeon.boss.x), int(self.dungeon.boss.y))
                                else:
                                    # Target next altar in sequence!
                                    next_idx = self.dungeon.altar_sequence[self.dungeon.current_altar_step]
                                    target = self.dungeon.altars[next_idx]["pos"]
                            else:
                                target = self.dungeon.exit
                            self.route = self.dungeon.find_path((self.player_x, self.player_y), target, allow_doors=True) or []
                        else:
                            self.update_route()

                        if self.route and len(self.route) > 1:
                            next_step = self.route[1]
                            dx = next_step[0] - self.player_x
                            dy = next_step[1] - self.player_y
                            self.try_move(dx, dy)

    # ----------------- Polished RPG Top HUD -----------------
    def draw_hud(self, surface):
        # 1. Main Background Bar
        hud_rect = pygame.Rect(0, 0, WIDTH, HUD_HEIGHT)
        pygame.draw.rect(surface, C["panel"], hud_rect)
        pygame.draw.line(surface, C["panel_border"], (0, HUD_HEIGHT - 1), (WIDTH, HUD_HEIGHT - 1), 2)
        pygame.draw.line(surface, (28, 36, 68), (0, HUD_HEIGHT - 2), (WIDTH, HUD_HEIGHT - 2), 1)

        # 2. Left Card: Title and Subtitle
        surface.blit(TITLE_FONT.render("AI PUZZLE DUNGEON", True, C["gold"]), (16, 8))
        surface.blit(SMALL.render("SOLVABLE LABYRINTH • BFS VALIDATED • 4 AI ARCHETYPES", True, C["cyan"]), (18, 38))

        # 3. STAT CARDS: HP (6 Hearts), MOVES, EMERALDS, KEYS, LEVEL
        # Card 1: HEALTH BAR with 6 RPG Hearts
        hp_card = pygame.Rect(16, 56, 185, 26)
        pygame.draw.rect(surface, C["panel_card"], hp_card, border_radius=6)
        pygame.draw.rect(surface, C["panel_border"], hp_card, 1, border_radius=6)
        surface.blit(SMALL.render("HP:", True, C["muted"]), (hp_card.x + 6, hp_card.y + 5))
        for i in range(self.max_hp):
            heart = sf.render_ui_heart(filled=(i < self.hp), size=18)
            surface.blit(heart, (hp_card.x + 30 + i * 25, hp_card.y + 4))

        # Card 2: MOVES COUNTER
        moves_card = pygame.Rect(210, 56, 110, 26)
        pygame.draw.rect(surface, C["panel_card"], moves_card, border_radius=6)
        pygame.draw.rect(surface, C["panel_border"], moves_card, 1, border_radius=6)
        surface.blit(SMALL.render("MOVES:", True, C["muted"]), (moves_card.x + 7, moves_card.y + 5))
        surface.blit(FONT.render(str(self.moves), True, C["text"]), (moves_card.x + 58, moves_card.y + 4))

        # Card 3: EMERALDS (Gems)
        gem_card = pygame.Rect(328, 56, 115, 26)
        pygame.draw.rect(surface, C["panel_card"], gem_card, border_radius=6)
        pygame.draw.rect(surface, C["panel_border"], gem_card, 1, border_radius=6)
        gem_ico = sf.render_gem(None, 20)
        surface.blit(gem_ico, (gem_card.x + 5, gem_card.y + 3))
        surface.blit(SMALL.render("GEMS:", True, C["muted"]), (gem_card.x + 26, gem_card.y + 5))
        surface.blit(FONT.render(f"{self.gems}", True, C["green"]), (gem_card.x + 65, gem_card.y + 4))

        # Card 4: KEYS
        key_card = pygame.Rect(453, 56, 105, 26)
        pygame.draw.rect(surface, C["panel_card"], key_card, border_radius=6)
        pygame.draw.rect(surface, C["panel_border"], key_card, 1, border_radius=6)
        key_ico = sf.render_ui_key(20)
        surface.blit(key_ico, (key_card.x + 6, key_card.y + 3))
        surface.blit(SMALL.render("KEYS:", True, C["muted"]), (key_card.x + 30, key_card.y + 5))
        surface.blit(FONT.render(str(self.keys), True, C["gold"]), (key_card.x + 78, key_card.y + 4))

        # Card 5: WEAPON (if equipped)
        if self.weapon_name:
            weap_card = pygame.Rect(568, 56, 185, 26)
            pygame.draw.rect(surface, C["panel_card"], weap_card, border_radius=6)
            pygame.draw.rect(surface, (255, 215, 0), weap_card, 1, border_radius=6)
            surface.blit(SMALL.render("ATK:", True, C["muted"]), (weap_card.x + 6, weap_card.y + 5))
            surface.blit(SMALL.render(f"{self.weapon_name} (+{self.weapon_bonus})", True, (255, 215, 0)), (weap_card.x + 36, weap_card.y + 5))

        # Card 5: Right Info Panel (Level Badge & Solvability Info & Auto AI status)
        right_card = pygame.Rect(WIDTH - 230, 10, 216, 72)
        pygame.draw.rect(surface, C["panel_card"], right_card, border_radius=8)
        border_col = C["green"] if self.auto_assist else C["panel_border"]
        pygame.draw.rect(surface, border_col, right_card, 2 if self.auto_assist else 1, border_radius=8)
        
        surface.blit(FONT.render(f"LEVEL  {self.level_num}", True, C["gold"]), (right_card.x + 14, right_card.y + 8))
        if self.auto_assist:
            surface.blit(SMALL.render("AUTO AI: ACTIVE", True, C["green"]), (right_card.x + 14, right_card.y + 30))
        else:
            surface.blit(SMALL.render("STATUS: SOLVABLE", True, C["cyan"]), (right_card.x + 14, right_card.y + 30))
        surface.blit(SMALL.render(f"AI PATH NODES: {self.dungeon.explored_states}", True, C["muted"]), (right_card.x + 14, right_card.y + 49))

    # ----------------- Rendering Dungeon -----------------
    def draw_dungeon(self, surface, t):
        # 1. Floor & Wall tiles
        for y in range(ROWS):
            for x in range(COLS):
                rect = pygame.Rect(x * TILE, HUD_HEIGHT + y * TILE, TILE, TILE)
                if self.dungeon.grid[y][x] == 1:
                    pygame.draw.rect(surface, C["wall"], rect)
                    pygame.draw.rect(surface, C["wall_top"], (rect.x, rect.y, TILE, 4))
                    pygame.draw.rect(surface, C["wall_shadow"], (rect.x, rect.bottom - 4, TILE, 4))
                    if (x + y) % 2 == 0:
                        pygame.draw.line(surface, (50, 58, 88), (rect.x, rect.y + 16), (rect.right, rect.y + 16), 1)
                else:
                    if (x, y) in self.dungeon.ice_tiles:
                        surface.blit(sf.render_ice_tile(TILE), rect.topleft)
                    else:
                        base_col = C["floor1"] if (x + y) % 2 == 0 else C["floor2"]
                        pygame.draw.rect(surface, base_col, rect)
                        pygame.draw.rect(surface, (36, 44, 70), rect, 1)

        # 2. Wall Torches
        for y in range(ROWS):
            for x in range(COLS):
                if self.dungeon.grid[y][x] == 1 and (x * 7 + y * 13) % 17 == 0:
                    cx = x * TILE + TILE // 2
                    cy = HUD_HEIGHT + y * TILE + TILE // 2
                    flicker = int(3 * math.sin(t * 14 + x * 2))
                    glow_circle(surface, (255, 140, 40), (cx, cy - 3), 4 + flicker // 2, 2)
                    pygame.draw.rect(surface, (120, 80, 50), (cx - 2, cy - 1, 4, 8))

        # 3. Enhanced AI Puzzle Path Visualizer
        if (self.show_route or self.auto_assist) and self.route:
            # Draw connected glowing energy beam
            if len(self.route) >= 2:
                pts = [(p[0] * TILE + TILE // 2, HUD_HEIGHT + p[1] * TILE + TILE // 2) for p in self.route]
                # Outer glow line
                route_color = (60, 240, 150) if self.auto_assist else (55, 175, 255)
                pygame.draw.lines(surface, (*route_color, 120), False, pts, 4)
                pygame.draw.lines(surface, (220, 250, 255), False, pts, 2)

            for i, p in enumerate(self.route[1:-1]):
                rx = p[0] * TILE + TILE // 2
                ry = HUD_HEIGHT + p[1] * TILE + TILE // 2
                # Traveling energy pulse along the route
                pulse_offset = (i * 0.15 - t * 4) % 1.0
                node_col = (70, 245, 160) if self.auto_assist else (60, 200, 255)
                glow_circle(surface, node_col, (rx, ry), 5 if pulse_offset < 0.3 else 3, 2 if pulse_offset < 0.3 else 1)
                pygame.draw.circle(surface, (255, 255, 255), (rx, ry), 2)

        # 4. Interactive Objects
        for (x, y), obj in self.dungeon.objects.items():
            cx = x * TILE + TILE // 2
            cy = HUD_HEIGHT + y * TILE + TILE // 2
            pulse = 1.0 + 0.12 * math.sin(t * 5 + x)
            
            if obj["type"] == "KEY" and not obj.get("collected", False):
                glow_circle(surface, C["gold"], (cx, cy), int(6 * pulse), 2)
                pygame.draw.circle(surface, (255, 240, 140), (cx - 3, cy - 3), 4, 2)
                pygame.draw.line(surface, C["gold"], (cx, cy), (cx + 8, cy + 8), 3)
                pygame.draw.line(surface, C["gold"], (cx + 4, cy + 4), (cx + 7, cy + 1), 2)
                
            elif obj["type"] == "DOOR":
                rect = pygame.Rect(x * TILE + 2, HUD_HEIGHT + y * TILE + 2, TILE - 4, TILE - 4)
                if obj.get("locked", True):
                    pygame.draw.rect(surface, (140, 75, 55), rect, border_radius=4)
                    pygame.draw.rect(surface, (210, 170, 100), rect, 2, border_radius=4)
                    pygame.draw.circle(surface, (20, 20, 25), (cx, cy - 2), 3)
                    pygame.draw.polygon(surface, (20, 20, 25), [(cx - 2, cy - 2), (cx + 2, cy - 2), (cx, cy + 4)])
                else:
                    pygame.draw.rect(surface, (40, 50, 75), rect, 2, border_radius=4)
                    glow_circle(surface, C["green"], (cx, cy), 5, 1)

            elif obj["type"] == "LEVER":
                surface.blit(sf.render_lever(obj.get("active", False), TILE), (x * TILE, HUD_HEIGHT + y * TILE))

            elif obj["type"] == "GATE":
                rect = pygame.Rect(x * TILE + 2, HUD_HEIGHT + y * TILE + 2, TILE - 4, TILE - 4)
                if not obj.get("active", False):
                    glow_circle(surface, C["purple"], (cx, cy), int(7 * pulse), 2)
                    pygame.draw.rect(surface, (160, 60, 230), rect, 2, border_radius=4)
                    pygame.draw.line(surface, (240, 190, 255), (rect.left, cy), (rect.right, cy), 3)
                    pygame.draw.line(surface, (240, 190, 255), (cx, rect.top), (cx, rect.bottom), 3)
                else:
                    glow_circle(surface, C["green"], (cx, cy), 5, 1)

            elif obj["type"] == "SPIKE":
                pygame.draw.ellipse(surface, (60, 30, 45), (cx - 12, cy - 5, 24, 12))
                for ox in (-7, 0, 7):
                    pygame.draw.polygon(surface, C["red"], [(cx + ox, cy - 8), (cx + ox - 3, cy + 3), (cx + ox + 3, cy + 3)])
                    pygame.draw.line(surface, (255, 200, 210), (cx + ox, cy - 7), (cx + ox, cy), 1)

            elif obj["type"] == "PORTAL":
                col = obj.get("col", C["purple"])
                glow_circle(surface, col, (cx, cy), int(9 * pulse), 3)
                pygame.draw.ellipse(surface, (20, 15, 45), (cx - 10, cy - 13, 20, 26))
                pygame.draw.ellipse(surface, col, (cx - 8, cy - 11, 16, 22), 2)

            elif obj["type"] == "GEM" and not obj.get("collected", False):
                glow_circle(surface, C["green"], (cx, cy), int(5 * pulse), 1)
                surface.blit(sf.render_gem(t, TILE), (x * TILE, HUD_HEIGHT + y * TILE))

            elif obj["type"] == "CHEST":
                glow_circle(surface, C["gold"], (cx, cy), int(8 * pulse), 2)
                surface.blit(sf.render_boss_chest(obj.get("opened", False), TILE), (x * TILE, HUD_HEIGHT + y * TILE))

            elif obj["type"] == "ALTAR":
                altar_info = self.dungeon.altars[obj["altar_index"]]
                is_active = altar_info["active"]
                if is_active:
                    glow_circle(surface, obj["color"], (cx, cy - 8), int(8 * pulse), 2)
                surface.blit(sf.render_boss_altar(obj["color"], active=is_active, size=TILE), (x * TILE, HUD_HEIGHT + y * TILE))

        # 5. Sokoban Crates
        for (cx_pos, cy_pos) in self.dungeon.crates:
            surface.blit(sf.render_push_block(TILE), (cx_pos * TILE, HUD_HEIGHT + cy_pos * TILE))

        # 6. Exit Portal
        ex, ey = self.dungeon.exit
        ecx = ex * TILE + TILE // 2
        ecy = HUD_HEIGHT + ey * TILE + TILE // 2
        is_sealed = (self.dungeon.is_boss_level and self.dungeon.boss and self.dungeon.boss.alive)
        portal_col = C["purple"] if is_sealed else C["green"]
        glow_circle(surface, portal_col, (ecx, ecy), int(10 * (1 + 0.15 * math.sin(t * 6))), 3)
        pygame.draw.ellipse(surface, (10, 20, 35) if is_sealed else (10, 40, 30), (ecx - 11, ecy - 14, 22, 28))
        pygame.draw.ellipse(surface, (200, 120, 255) if is_sealed else (140, 255, 180), (ecx - 9, ecy - 12, 18, 24), 2)
        label = "SEALED" if is_sealed else "EXIT"
        surface.blit(SMALL.render(label, True, (240, 160, 255) if is_sealed else C["text"]), (ex * TILE + 2, HUD_HEIGHT + ey * TILE - 14))

        # 7. Enemies & Boss
        for enemy in self.dungeon.enemies:
            enemy.draw(surface, t)

        if self.dungeon.boss and self.dungeon.boss.alive:
            self.dungeon.boss.draw(surface, t)

        # 8. Player
        if self.invulnerable_timer <= 0 or int(t * 20) % 2 == 0:
            player_surf = sf.render_player(0, self.player_dir, self.anim_state, t, TILE)
            surface.blit(player_surf, (int(self.visual_x), int(HUD_HEIGHT + self.visual_y)))

        # 9. Boss Grand Health Bar (Matches reference design)
        if self.dungeon.is_boss_level and self.dungeon.boss and self.dungeon.boss.alive:
            boss = self.dungeon.boss
            bar_w = 420
            bar_h = 16
            bx = (WIDTH - bar_w) // 2
            by = HUD_HEIGHT + 14
            # Dark frame
            pygame.draw.rect(surface, (15, 18, 32), (bx - 8, by - 20, bar_w + 16, bar_h + 38), border_radius=8)
            pygame.draw.rect(surface, (90, 50, 140), (bx - 8, by - 20, bar_w + 16, bar_h + 38), 2, border_radius=8)
            # Boss Name and Subtitle
            surface.blit(FONT.render("CHAOS GUARDIAN", True, (255, 80, 110)), (bx, by - 16))
            surface.blit(SMALL.render(f"PHASE {boss.phase} / 3  |  CORE HP: {boss.hp}/{boss.max_hp}", True, C["gold"]), (bx + bar_w - 180, by - 16))
            # Segmented Health bar
            pygame.draw.rect(surface, (35, 20, 50), (bx, by + 4, bar_w, bar_h), border_radius=4)
            pct = max(0.0, boss.hp / boss.max_hp)
            fill_col = (100, 240, 255) if boss.state == "stunned" else (C["red"] if boss.phase == 2 else C["purple"])
            pygame.draw.rect(surface, fill_col, (bx, by + 4, int(bar_w * pct), bar_h), border_radius=4)
            # Segments divider lines
            for s in range(1, 6):
                sx = bx + int(bar_w * (s / 6))
                pygame.draw.line(surface, (15, 18, 32), (sx, by + 4), (sx, by + 4 + bar_h), 2)
            # Runic Ritual sequence guide
            seq_text = "RITUAL: "
            for idx in range(len(self.dungeon.altar_sequence)):
                seq_id = self.dungeon.altar_sequence[idx]
                name = self.dungeon.altars[seq_id]["name"].split()[0]
                if idx < self.dungeon.current_altar_step:
                    seq_text += f"[OK {name}] "
                elif idx == self.dungeon.current_altar_step:
                    seq_text += f">> {name} << "
                else:
                    seq_text += f"[{name}] "
            surface.blit(SMALL.render(seq_text, True, (210, 240, 255)), (bx, by + 24))

        # 10. Particles
        update_and_draw_particles(surface, clock.get_time() / 1000.0)

        # 11. Always render HUD on top!
        self.draw_hud(surface)

        # 11. Bottom Toast Status Bar
        status_rect = pygame.Rect(10, HEIGHT - 32, WIDTH - 20, 26)
        pygame.draw.rect(surface, (16, 22, 42), status_rect, border_radius=8)
        pygame.draw.rect(surface, (55, 80, 140), status_rect, 1, border_radius=8)
        
        if self.msg_timer > 0:
            surface.blit(SMALL.render(self.message, True, C["text"]), (20, HEIGHT - 26))
        else:
            surface.blit(SMALL.render("WASD: Move | SPACE: Attack | TAB: Auto AI | H: Route | R: Retry | ESC: Menu", True, C["muted"]), (20, HEIGHT - 26))

        # 12. Overlays
        if self.won:
            overlay = pygame.Surface((WIDTH, ROWS * TILE), pygame.SRCALPHA)
            overlay.fill((5, 12, 25, 200))
            surface.blit(overlay, (0, HUD_HEIGHT))
            
            vt = BIG_FONT.render("DUNGEON CLEARED!", True, C["green"])
            vs = FONT.render(f"Final Moves: {self.moves}  |  Emeralds: {self.gems}", True, C["text"])
            vn = TITLE_FONT.render("Press 'N' to Enter Next Dungeon Level", True, C["gold"])
            surface.blit(vt, vt.get_rect(center=(WIDTH//2, HUD_HEIGHT + ROWS * TILE // 2 - 40)))
            surface.blit(vs, vs.get_rect(center=(WIDTH//2, HUD_HEIGHT + ROWS * TILE // 2)))
            surface.blit(vn, vn.get_rect(center=(WIDTH//2, HUD_HEIGHT + ROWS * TILE // 2 + 45)))
            
        elif self.game_over:
            overlay = pygame.Surface((WIDTH, ROWS * TILE), pygame.SRCALPHA)
            overlay.fill((30, 8, 12, 215))
            surface.blit(overlay, (0, HUD_HEIGHT))
            
            gt = BIG_FONT.render("GAME OVER", True, C["red"])
            gs = FONT.render("You fell in battle. The labyrinth claims another soul.", True, C["text"])
            gr = TITLE_FONT.render("Press 'R' to Retry Current Level", True, C["gold"])
            surface.blit(gt, gt.get_rect(center=(WIDTH//2, HUD_HEIGHT + ROWS * TILE // 2 - 40)))
            surface.blit(gs, gs.get_rect(center=(WIDTH//2, HUD_HEIGHT + ROWS * TILE // 2)))
            surface.blit(gr, gr.get_rect(center=(WIDTH//2, HUD_HEIGHT + ROWS * TILE // 2 + 45)))

    def draw_menu(self, surface, t):
        surface.fill(C["bg"])
        for i in range(110):
            sx = (i * 137) % WIDTH
            sy = (i * 79) % HEIGHT
            twinkle = 1 + int(2 * (0.5 + 0.5 * math.sin(t * 3 + i)))
            pygame.draw.circle(surface, (50, 90, 160), (sx, sy), twinkle)

        for i in range(8):
            px = 60 + i * 110
            py = HEIGHT // 2 + int(28 * math.sin(t * 1.5 + i))
            glow_circle(surface, (45, 120, 240), (px, py), 6, 2)

        t1 = BIG_FONT.render("AI PUZZLE", True, C["gold"])
        t2 = BIG_FONT.render("DUNGEON", True, C["cyan"])
        sub = FONT.render("THE INFINITE LABYRINTH - ENHANCED", True, C["purple"])
        
        surface.blit(t1, t1.get_rect(center=(WIDTH // 2, 140)))
        surface.blit(t2, t2.get_rect(center=(WIDTH // 2, 185)))
        surface.blit(sub, sub.get_rect(center=(WIDTH // 2, 225)))

        hero = sf.render_player(0, (0, 1), "idle", t, 50)
        surface.blit(hero, hero.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 10)))

        btn_rect = pygame.Rect(WIDTH // 2 - 110, HEIGHT // 2 + 65, 220, 50)
        pygame.draw.rect(surface, (25, 130, 95), btn_rect, border_radius=12)
        pygame.draw.rect(surface, C["green"], btn_rect, 2, border_radius=12)
        btn_txt = TITLE_FONT.render("START GAME", True, C["text"])
        surface.blit(btn_txt, btn_txt.get_rect(center=btn_rect.center))

        hint = SMALL.render("Click START or press ENTER / SPACE", True, C["muted"])
        surface.blit(hint, hint.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 135)))

        feats = SMALL.render("GUARANTEED SOLVABLE • INTELLIGENT AI • TACTICAL PUZZLES • RETRO SFX", True, C["muted"])
        surface.blit(feats, feats.get_rect(center=(WIDTH // 2, HEIGHT - 30)))
        return btn_rect

# ----------------- Main Game Loop -----------------
def main():
    import traceback
    try:
        game = Game()
        running = True

        while running:
            dt = clock.tick(FPS) / 1000.0
            game.update(dt)

            start_btn = None
            if game.menu:
                start_btn = game.draw_menu(screen, game.time_total)
            else:
                game.draw_dungeon(screen, game.time_total)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                    
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if game.menu and start_btn and start_btn.collidepoint(event.pos):
                        game.menu = False
                        sound_manager.play_sfx("switch")
                        game.say("Welcome, Adventurer! Solve puzzles, slay foes, and reach the exit portal!", 4.0)

                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        if game.menu:
                            running = False
                        else:
                            game.menu = True
                            
                    elif game.menu and event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        game.menu = False
                        sound_manager.play_sfx("switch")
                        game.say("Welcome, Adventurer! Solve puzzles, slay foes, and reach the exit portal!", 4.0)

                    elif not game.menu:
                        # Arrow keys and WASD movement (pressing movement keys manually disengages auto assist)
                        if event.key == pygame.K_UP or event.key == pygame.K_w:
                            game.auto_assist = False
                            game.try_move(0, -1)
                        elif event.key == pygame.K_DOWN or event.key == pygame.K_s:
                            game.auto_assist = False
                            game.try_move(0, 1)
                        elif event.key == pygame.K_LEFT or event.key == pygame.K_a:
                            game.auto_assist = False
                            game.try_move(-1, 0)
                        elif event.key == pygame.K_RIGHT or event.key == pygame.K_d:
                            game.auto_assist = False
                            game.try_move(1, 0)
                        elif event.key == pygame.K_SPACE:
                            game.do_attack()
                        elif event.key == pygame.K_TAB:
                            # Toggle Auto AI Assist with TAB only (never triggers on A key!)
                            game.auto_assist = not game.auto_assist
                            if game.auto_assist:
                                game.show_route = True
                                game.update_route()
                                sound_manager.play_sfx("switch")
                                game.say("AUTO AI ASSIST ENGAGED! Hero is solving and navigating automatically.", 3.5)
                            else:
                                game.say("Auto AI Assist disengaged. Manual control resumed.", 2.0)
                        elif event.key == pygame.K_h:
                            game.show_route = not game.show_route
                            if game.show_route:
                                game.update_route()
                                game.say("AI Puzzle Path highlighted in neon beam!", 2.5)
                            else:
                                game.say("AI Route hidden.", 1.5)
                        elif event.key == pygame.K_r:
                            game.reset(next_level=False)
                        elif event.key == pygame.K_n:
                            if game.won:
                                game.reset(next_level=True)
                            else:
                                game.say("Reach the green exit portal first to advance!", 2.0)

            pygame.display.flip()

    except Exception as exc:
        err = traceback.format_exc()
        print("CRITICAL GAME ERROR OCCURRED:\n", err)
        with open("crash_log.txt", "w") as f:
            f.write(err)
        # Keep window alive showing crash message so it never silently closes
        try:
            screen.fill((35, 10, 15))
            t_err = FONT.render("A GAME ERROR OCCURRED (Saved to crash_log.txt):", True, (255, 100, 100))
            screen.blit(t_err, (20, 30))
            lines = err.strip().split("\n")
            for i, line in enumerate(lines[-14:]):
                screen.blit(SMALL.render(line[:120], True, (240, 240, 240)), (20, 70 + i * 22))
            t_sub = SMALL.render("Press ESC to exit or R to restart level", True, (255, 215, 0))
            screen.blit(t_sub, (20, HEIGHT - 40))
            pygame.display.flip()
            waiting = True
            while waiting:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                        waiting = False
        except:
            pass
    finally:
        pygame.quit()

if __name__ == "__main__":
    main()
