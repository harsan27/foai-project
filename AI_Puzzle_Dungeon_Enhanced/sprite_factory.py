import math
import pygame

SPRITE_CACHE = {}

def get_surface(size):
    return pygame.Surface(size, pygame.SRCALPHA)

def render_player(frame, direction, anim_state, t, size=36):
    """
    Renders player matching the reference:
    Red hooded cloak, tunic, glowing blue eyes/face shade, sword, boots.
    """
    surf = get_surface((size, size))
    cx, cy = size // 2, size // 2 + 1
    
    # Offsets and dynamics based on state
    bob = 0
    attack_offset = (0, 0)
    swing_angle = 0
    
    if anim_state == "idle":
        bob = int(math.sin(t * 5) * 1.5)
    elif anim_state == "walk":
        bob = int(abs(math.sin(t * 10)) * 3)
    elif anim_state == "attack":
        attack_offset = (direction[0] * 5, direction[1] * 5)
        swing_angle = math.sin(t * 20) * 45
    elif anim_state == "hurt":
        bob = int(math.sin(t * 30) * 2)

    # Shadow
    pygame.draw.ellipse(surf, (10, 14, 25, 140), (cx - 10, cy + 9, 20, 8))
    
    px = cx + attack_offset[0]
    py = cy + bob + attack_offset[1]
    
    # Red Cloak Back
    pygame.draw.polygon(surf, (150, 30, 45), [
        (px - 9, py - 4), (px + 9, py - 4),
        (px + 11, py + 11), (px, py + 8), (px - 11, py + 11)
    ])
    
    # Body / Leather Tunic
    pygame.draw.rect(surf, (45, 52, 71), (px - 7, py - 3, 14, 12), border_radius=3)
    # Belt & buckle
    pygame.draw.rect(surf, (30, 20, 15), (px - 7, py + 4, 14, 3))
    pygame.draw.rect(surf, (255, 200, 60), (px - 2, py + 4, 4, 3))
    
    # Boots
    foot_bob = int(math.sin(t * 10) * 3) if anim_state == "walk" else 0
    pygame.draw.rect(surf, (60, 40, 30), (px - 6, py + 9 - foot_bob, 5, 5), border_radius=2)
    pygame.draw.rect(surf, (50, 30, 20), (px + 1, py + 9 + foot_bob, 5, 5), border_radius=2)

    # Red Hood Outer
    pygame.draw.ellipse(surf, (210, 45, 60), (px - 9, py - 14, 18, 17))
    pygame.draw.polygon(surf, (170, 35, 50), [
        (px - 9, py - 6), (px - 2, py - 17), (px - 13, py - 9)
    ]) # pointy hood tip
    
    # Hood rim & shadow
    pygame.draw.ellipse(surf, (130, 25, 38), (px - 7, py - 11, 14, 13))
    # Face skin peek
    pygame.draw.ellipse(surf, (255, 205, 160), (px - 5, py - 9, 10, 9))
    
    # Eyes based on direction
    dx, dy = direction
    ex = px - 2 + dx * 2
    ey = py - 7 + dy * 2
    eye_col = (40, 40, 60)
    pygame.draw.circle(surf, eye_col, (int(ex - 2), int(ey)), 1)
    pygame.draw.circle(surf, eye_col, (int(ex + 2), int(ey)), 1)
    
    # Golden Sword
    sx = px + 9 + dx * 4
    sy = py + dy * 4
    if anim_state == "attack":
        # Glinting slashing blade
        pygame.draw.line(surf, (255, 255, 255), (sx - 2, sy + 4), (sx + 8, sy - 8), 3)
        pygame.draw.line(surf, (100, 220, 255), (sx - 1, sy + 3), (sx + 7, sy - 7), 2)
        pygame.draw.circle(surf, (255, 215, 0), (sx - 3, sy + 5), 2)
    else:
        # Sheathed / held blade
        pygame.draw.line(surf, (210, 230, 255), (sx, sy + 2), (sx + 4, sy - 7), 2)
        pygame.draw.line(surf, (255, 200, 50), (sx - 2, sy + 4), (sx + 2, sy + 1), 2)
        
    return surf

def render_slime(t, size=36, hit=False):
    surf = get_surface((size, size))
    cx, cy = size // 2, size // 2 + 3
    squish = math.sin(t * 7) * 2
    
    # Shadow
    pygame.draw.ellipse(surf, (10, 15, 20, 130), (cx - 11, cy + 7, 22, 7))
    
    # Slime body (Green gelatinous dome)
    col_main = (255, 120, 120) if hit else (60, 215, 95)
    col_light = (255, 180, 180) if hit else (140, 245, 130)
    col_dark = (180, 40, 40) if hit else (35, 150, 65)
    
    w = int(22 - squish)
    h = int(18 + squish)
    rect = pygame.Rect(cx - w//2, cy - h//2, w, h)
    pygame.draw.ellipse(surf, col_dark, rect)
    pygame.draw.ellipse(surf, col_main, (rect.x + 1, rect.y + 1, rect.width - 2, rect.height - 3))
    # Highlights
    pygame.draw.ellipse(surf, col_light, (rect.x + 3, rect.y + 3, rect.width // 2, 4))
    
    # Eyes
    pygame.draw.circle(surf, (20, 40, 20), (cx - 4, cy - 2), 2)
    pygame.draw.circle(surf, (20, 40, 20), (cx + 4, cy - 2), 2)
    pygame.draw.circle(surf, (255, 255, 255), (cx - 5, cy - 3), 1)
    pygame.draw.circle(surf, (255, 255, 255), (cx + 3, cy - 3), 1)
    
    return surf

def render_skeleton(t, size=36, hit=False):
    surf = get_surface((size, size))
    cx, cy = size // 2, size // 2 + 1
    bob = int(math.sin(t * 6) * 1.5)
    
    # Shadow
    pygame.draw.ellipse(surf, (10, 12, 22, 130), (cx - 9, cy + 9, 18, 7))
    
    py = cy + bob
    col_bone = (255, 140, 140) if hit else (235, 230, 215)
    
    # Ribcage / spine
    pygame.draw.rect(surf, col_bone, (cx - 4, py - 3, 8, 9), border_radius=2)
    pygame.draw.line(surf, (30, 30, 35), (cx - 3, py), (cx + 3, py), 1)
    pygame.draw.line(surf, (30, 30, 35), (cx - 3, py + 3), (cx + 3, py + 3), 1)
    
    # Skull
    pygame.draw.circle(surf, col_bone, (cx, py - 8), 6)
    pygame.draw.rect(surf, col_bone, (cx - 3, py - 4, 6, 4))
    # Eye sockets (glowing red)
    pygame.draw.circle(surf, (220, 40, 50), (cx - 2, py - 8), 1)
    pygame.draw.circle(surf, (220, 40, 50), (cx + 2, py - 8), 1)
    
    # Bone legs
    pygame.draw.line(surf, col_bone, (cx - 3, py + 6), (cx - 4, py + 11), 2)
    pygame.draw.line(surf, col_bone, (cx + 3, py + 6), (cx + 4, py + 11), 2)
    
    # Rusted sword
    pygame.draw.line(surf, (180, 140, 110), (cx + 6, py + 4), (cx + 12, py - 6), 2)
    pygame.draw.line(surf, (100, 70, 50), (cx + 4, py + 5), (cx + 8, py + 2), 2)
    
    return surf

def render_ghost(t, size=36, hit=False):
    surf = get_surface((size, size))
    cx, cy = size // 2, size // 2
    float_y = int(math.sin(t * 4) * 3)
    
    py = cy + float_y
    # Ghostly purple ethereal glow
    col_body = (255, 140, 200) if hit else (190, 110, 255)
    col_tail = (140, 60, 220)
    
    # Ectoplasmic body
    pygame.draw.circle(surf, col_body, (cx, py - 4), 8)
    pygame.draw.polygon(surf, col_tail, [
        (cx - 8, py - 4), (cx + 8, py - 4),
        (cx + 6, py + 8 + int(math.sin(t*8)*2)),
        (cx + 1, py + 5),
        (cx - 3, py + 9 - int(math.sin(t*8)*2)),
        (cx - 6, py + 5)
    ])
    
    # Spooky glowing eyes & mouth
    pygame.draw.circle(surf, (255, 255, 255), (cx - 3, py - 4), 2)
    pygame.draw.circle(surf, (255, 255, 255), (cx + 3, py - 4), 2)
    pygame.draw.circle(surf, (20, 10, 40), (cx - 3, py - 4), 1)
    pygame.draw.circle(surf, (20, 10, 40), (cx + 3, py - 4), 1)
    pygame.draw.ellipse(surf, (20, 10, 40), (cx - 2, py, 4, 3))
    
    return surf

def render_bat(t, size=36, hit=False):
    surf = get_surface((size, size))
    cx, cy = size // 2, size // 2
    wing_flap = math.sin(t * 16) * 5
    
    col_bat = (255, 100, 100) if hit else (75, 45, 115)
    
    # Wing Left
    pygame.draw.polygon(surf, col_bat, [
        (cx - 2, cy), (cx - 12, cy - 4 - int(wing_flap)), (cx - 8, cy + 4)
    ])
    # Wing Right
    pygame.draw.polygon(surf, col_bat, [
        (cx + 2, cy), (cx + 12, cy - 4 - int(wing_flap)), (cx + 8, cy + 4)
    ])
    
    # Body
    pygame.draw.ellipse(surf, (45, 25, 75), (cx - 4, cy - 4, 8, 9))
    # Ears
    pygame.draw.polygon(surf, (60, 35, 95), [(cx - 4, cy - 3), (cx - 3, cy - 8), (cx - 1, cy - 4)])
    pygame.draw.polygon(surf, (60, 35, 95), [(cx + 4, cy - 3), (cx + 3, cy - 8), (cx + 1, cy - 4)])
    # Eyes
    pygame.draw.circle(surf, (255, 50, 70), (cx - 2, cy - 2), 1)
    pygame.draw.circle(surf, (255, 50, 70), (cx + 2, cy - 2), 1)
    
    return surf

def render_boss_chest(opened=False, size=36):
    """Render golden boss reward treasure chest."""
    surf = get_surface((size, size))
    cx, cy = size // 2, size // 2
    r = pygame.Rect(cx - 12, cy - 8, 24, 20)
    # Golden chest body
    pygame.draw.rect(surf, (180, 115, 35), r, border_radius=4)
    pygame.draw.rect(surf, (245, 185, 55), (r.x + 2, r.y + 2, r.width - 4, r.height - 4), border_radius=3)
    if opened:
        # Open lid tilted up
        pygame.draw.polygon(surf, (210, 140, 45), [
            (r.x, r.y), (r.right, r.y), (r.right - 2, r.y - 8), (r.x + 2, r.y - 8)
        ])
        # Glowing inner treasure glow
        pygame.draw.ellipse(surf, (255, 245, 180), (r.x + 4, r.y + 1, r.width - 8, 6))
    else:
        # Closed lid & bands
        pygame.draw.line(surf, (100, 60, 20), (r.x, r.y + 7), (r.right, r.y + 7), 2)
        # Gold lock
        pygame.draw.rect(surf, (255, 230, 100), (cx - 3, cy - 1, 6, 7), border_radius=2)
        pygame.draw.circle(surf, (40, 25, 10), (cx, cy + 2), 1)
    return surf

def render_push_block(size=36):
    surf = get_surface((size, size))
    r = pygame.Rect(3, 3, size - 6, size - 6)
    # Wood / stone crate with metal rivets
    pygame.draw.rect(surf, (150, 95, 45), r, border_radius=4)
    pygame.draw.rect(surf, (190, 130, 70), (r.x + 2, r.y + 2, r.width - 4, r.height - 4), border_radius=3)
    # Cross brace
    pygame.draw.line(surf, (105, 60, 25), (r.x + 3, r.y + 3), (r.right - 4, r.bottom - 4), 3)
    pygame.draw.line(surf, (105, 60, 25), (r.right - 4, r.y + 3), (r.x + 3, r.bottom - 4), 3)
    # Iron corner brackets
    for corner in [(r.x, r.y), (r.right - 6, r.y), (r.x, r.bottom - 6), (r.right - 6, r.bottom - 6)]:
        pygame.draw.rect(surf, (80, 90, 110), (*corner, 6, 6))
        pygame.draw.circle(surf, (220, 220, 240), (corner[0] + 3, corner[1] + 3), 1)
    return surf

def render_ice_tile(size=36):
    surf = get_surface((size, size))
    r = pygame.Rect(0, 0, size, size)
    pygame.draw.rect(surf, (80, 180, 230), r)
    pygame.draw.rect(surf, (170, 235, 255), (r.x + 2, r.y + 2, r.width - 4, r.height - 4))
    # Cracks / glint
    pygame.draw.line(surf, (255, 255, 255), (r.x + 4, r.y + 6), (r.x + 14, r.y + 16), 2)
    pygame.draw.line(surf, (255, 255, 255), (r.x + 14, r.y + 16), (r.x + 10, r.y + 24), 1)
    pygame.draw.line(surf, (215, 245, 255), (r.right - 8, r.bottom - 12), (r.right - 18, r.bottom - 6), 2)
    return surf

def render_lever(active=False, size=36):
    surf = get_surface((size, size))
    cx, cy = size // 2, size // 2
    # Base
    pygame.draw.rect(surf, (60, 65, 80), (cx - 8, cy + 3, 16, 7), border_radius=2)
    pygame.draw.rect(surf, (90, 95, 115), (cx - 6, cy + 4, 12, 3))
    # Stick
    if active:
        pygame.draw.line(surf, (180, 190, 205), (cx, cy + 4), (cx + 7, cy - 6), 3)
        pygame.draw.circle(surf, (70, 240, 130), (cx + 7, cy - 6), 4)
    else:
        pygame.draw.line(surf, (180, 190, 205), (cx, cy + 4), (cx - 7, cy - 6), 3)
        pygame.draw.circle(surf, (240, 70, 90), (cx - 7, cy - 6), 4)
    return surf

def render_gem(t, size=36):
    surf = get_surface((size, size))
    cx, cy = size // 2, size // 2
    float_y = int(math.sin(t * 5) * 2) if t is not None else 0
    py = cy + float_y
    # Sparkling emerald / diamond
    pts = [(cx, py - 8), (cx + 7, py - 2), (cx, py + 8), (cx - 7, py - 2)]
    pygame.draw.polygon(surf, (30, 210, 150), pts)
    pygame.draw.polygon(surf, (150, 255, 220), [(cx, py - 8), (cx + 5, py - 2), (cx, py + 3), (cx - 5, py - 2)])
    pygame.draw.circle(surf, (255, 255, 255), (cx - 2, py - 4), 2)
    return surf

def render_ui_heart(filled=True, size=24):
    """Render an attractive RPG heart icon for the HUD bar."""
    surf = get_surface((size, size))
    cx, cy = size // 2, size // 2
    if filled:
        # Glow / shadow
        pygame.draw.circle(surf, (100, 20, 35), (cx - 4, cy - 3), 6)
        pygame.draw.circle(surf, (100, 20, 35), (cx + 4, cy - 3), 6)
        pygame.draw.polygon(surf, (100, 20, 35), [(cx - 9, cy - 2), (cx + 9, cy - 2), (cx, cy + 9)])
        # Vibrant red heart
        pygame.draw.circle(surf, (255, 45, 85), (cx - 4, cy - 3), 5)
        pygame.draw.circle(surf, (255, 45, 85), (cx + 4, cy - 3), 5)
        pygame.draw.polygon(surf, (255, 45, 85), [(cx - 8, cy - 2), (cx + 8, cy - 2), (cx, cy + 8)])
        # Specular glint
        pygame.draw.circle(surf, (255, 200, 215), (cx - 4, cy - 4), 2)
    else:
        # Depleted dark heart container
        pygame.draw.circle(surf, (55, 40, 50), (cx - 4, cy - 3), 5)
        pygame.draw.circle(surf, (55, 40, 50), (cx + 4, cy - 3), 5)
        pygame.draw.polygon(surf, (55, 40, 50), [(cx - 8, cy - 2), (cx + 8, cy - 2), (cx, cy + 8)])
        pygame.draw.circle(surf, (30, 22, 30), (cx - 4, cy - 3), 4)
        pygame.draw.circle(surf, (30, 22, 30), (cx + 4, cy - 3), 4)
        pygame.draw.polygon(surf, (30, 22, 30), [(cx - 6, cy - 2), (cx + 6, cy - 2), (cx, cy + 6)])
    return surf

def render_ui_key(size=24):
    """Render a golden RPG key icon for the HUD."""
    surf = get_surface((size, size))
    cx, cy = size // 2, size // 2
    pygame.draw.circle(surf, (255, 215, 60), (cx - 4, cy - 4), 5, 2)
    pygame.draw.line(surf, (255, 215, 60), (cx, cy), (cx + 7, cy + 7), 3)
    pygame.draw.line(surf, (255, 215, 60), (cx + 4, cy + 4), (cx + 7, cy + 1), 2)
    pygame.draw.line(surf, (255, 235, 140), (cx - 4, cy - 5), (cx - 3, cy - 3), 1)
    return surf

def render_boss(t, phase=1, state="chase", hit=False, size=72):
    """
    Renders the Chaos Guardian Boss matching the visual specification:
    Huge stone & purple crystal colossus, glowing cyan/purple eyes, runic core,
    horns, spikes, and state-based color shifts (Vulnerable/Enraged).
    """
    surf = get_surface((size, size))
    cx, cy = size // 2, size // 2
    bob = int(math.sin(t * 6) * 3)

    # Shadow
    pygame.draw.ellipse(surf, (10, 10, 20, 150), (cx - 24, cy + 18, 48, 16))

    by = cy + bob
    # Color schemes based on phase / state
    if hit:
        col_stone = (255, 120, 120)
        col_crystal = (255, 200, 200)
    elif state == "stunned":
        col_stone = (70, 75, 95)
        col_crystal = (100, 230, 255) # Cyan vulnerable core
    elif phase == 2:
        col_stone = (85, 30, 45)      # Enraged fiery crimson stone
        col_crystal = (255, 60, 80)
    elif phase == 3:
        col_stone = (50, 25, 75)      # Astral void
        col_crystal = (210, 80, 255)
    else:
        col_stone = (45, 40, 65)      # Ancient rune granite
        col_crystal = (175, 70, 255)

    # Runic orbiting rings
    ring_radius = int(28 + math.sin(t * 4) * 3)
    pygame.draw.circle(surf, (*col_crystal[:3], 80), (cx, by), ring_radius, 2)
    for i in range(4):
        angle = t * 3 + i * (math.pi / 2)
        rx = cx + int(math.cos(angle) * ring_radius)
        ry = by + int(math.sin(angle) * (ring_radius * 0.6))
        pygame.draw.circle(surf, col_crystal, (rx, ry), 3)

    # Massive Shoulders & Torso
    pygame.draw.ellipse(surf, col_stone, (cx - 26, by - 12, 52, 34))
    highlight = (
        min(255, col_stone[0] + 25),
        min(255, col_stone[1] + 25),
        min(255, col_stone[2] + 35)
    )
    pygame.draw.ellipse(surf, highlight, (cx - 22, by - 9, 44, 28))

    # Crystalline Arm Claws
    claw_flap = math.sin(t * 8) * 4
    pygame.draw.polygon(surf, col_stone, [
        (cx - 24, by - 6), (cx - 32, by + 12 + int(claw_flap)), (cx - 20, by + 8)
    ])
    pygame.draw.polygon(surf, col_crystal, [
        (cx - 32, by + 12 + int(claw_flap)), (cx - 34, by + 18 + int(claw_flap)), (cx - 28, by + 14 + int(claw_flap))
    ])
    pygame.draw.polygon(surf, col_stone, [
        (cx + 24, by - 6), (cx + 32, by + 12 - int(claw_flap)), (cx + 20, by + 8)
    ])
    pygame.draw.polygon(surf, col_crystal, [
        (cx + 32, by + 12 - int(claw_flap)), (cx + 34, by + 18 - int(claw_flap)), (cx + 28, by + 14 - int(claw_flap))
    ])

    # Head & Horns
    pygame.draw.circle(surf, col_stone, (cx, by - 16), 14)
    # Spiked Horns
    pygame.draw.polygon(surf, col_crystal, [(cx - 12, by - 18), (cx - 20, by - 30), (cx - 4, by - 22)])
    pygame.draw.polygon(surf, col_crystal, [(cx + 12, by - 18), (cx + 20, by - 30), (cx + 4, by - 22)])

    # Glowing Crystal Core in chest
    pulse_size = int(8 + math.sin(t * 8) * 2)
    pygame.draw.circle(surf, col_crystal, (cx, by + 3), pulse_size)
    pygame.draw.circle(surf, (255, 255, 255), (cx, by + 3), max(2, pulse_size // 2))

    # Glowing eyes
    if state == "stunned":
        eye_col = (100, 240, 255)
    elif phase == 2:
        eye_col = (255, 50, 70)
    else:
        eye_col = (255, 230, 80)
    pygame.draw.circle(surf, eye_col, (cx - 5, by - 16), 3)
    pygame.draw.circle(surf, eye_col, (cx + 5, by - 16), 3)
    pygame.draw.circle(surf, (255, 255, 255), (cx - 5, by - 16), 1)
    pygame.draw.circle(surf, (255, 255, 255), (cx + 5, by - 16), 1)

    return surf

def render_boss_altar(color, active=False, size=36):
    """Renders elemental runic pedestals for the Chaos Guardian fight."""
    surf = get_surface((size, size))
    cx, cy = size // 2, size // 2
    # Pedestal base
    pygame.draw.polygon(surf, (45, 50, 70), [(cx - 12, cy + 12), (cx + 12, cy + 12), (cx + 8, cy - 4), (cx - 8, cy - 4)])
    pygame.draw.polygon(surf, (70, 78, 105), [(cx - 8, cy - 4), (cx + 8, cy - 4), (cx + 10, cy - 8), (cx - 10, cy - 8)])
    # Runic orb atop
    if active:
        pygame.draw.circle(surf, (255, 255, 255), (cx, cy - 10), 6)
        pygame.draw.circle(surf, color, (cx, cy - 10), 5)
        pygame.draw.circle(surf, (255, 255, 255), (cx - 1, cy - 11), 2)
    else:
        pygame.draw.circle(surf, (60, 65, 85), (cx, cy - 10), 5)
        pygame.draw.circle(surf, color, (cx, cy - 10), 3)
    return surf

