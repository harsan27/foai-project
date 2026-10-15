import math
import struct
import pygame

pygame.mixer.init(frequency=44100, size=-16, channels=1, buffer=512)

def generate_wave(frequency_func, duration, volume=0.3):
    sample_rate = 44100
    total_samples = int(sample_rate * duration)
    raw = bytearray()
    for i in range(total_samples):
        t = i / sample_rate
        freq = frequency_func(t)
        # Soft envelope (attack/decay)
        env = min(1.0, t * 40) * max(0.0, 1.0 - (t / duration) ** 1.5)
        # Waveform combination (sine + slight harmonics)
        val = math.sin(math.tau * freq * t) * 0.7 + math.sin(math.tau * freq * 2 * t) * 0.2
        sample = int(val * env * volume * 32767)
        sample = max(-32768, min(32767, sample))
        raw.extend(struct.pack("<h", sample))
    return pygame.mixer.Sound(buffer=bytes(raw))

SOUNDS = {}

def init_audio():
    try:
        SOUNDS["step"] = generate_wave(lambda t: 160 - t * 40, 0.07, 0.15)
        SOUNDS["key"] = generate_wave(lambda t: 880 + t * 440, 0.22, 0.25)
        SOUNDS["door"] = generate_wave(lambda t: 220 + 80 * math.sin(t * 30), 0.25, 0.25)
        SOUNDS["switch"] = generate_wave(lambda t: 520 if t < 0.08 else 780, 0.18, 0.25)
        SOUNDS["teleport"] = generate_wave(lambda t: 300 + 700 * (t / 0.3) ** 2, 0.3, 0.3)
        SOUNDS["gem"] = generate_wave(lambda t: 1200 + t * 600, 0.15, 0.2)
        SOUNDS["hit"] = generate_wave(lambda t: max(60, 240 - t * 800), 0.18, 0.35)
        SOUNDS["sword"] = generate_wave(lambda t: 400 + 400 * (1.0 - t / 0.15), 0.15, 0.3)
        SOUNDS["enemy_die"] = generate_wave(lambda t: 300 - t * 400, 0.25, 0.3)
        SOUNDS["win"] = generate_wave(lambda t: 523 if t < 0.1 else (659 if t < 0.2 else (783 if t < 0.3 else 1046)), 0.55, 0.35)
        SOUNDS["ice"] = generate_wave(lambda t: 900 + 200 * math.sin(t * 50), 0.16, 0.2)
        SOUNDS["box"] = generate_wave(lambda t: 110 + random_vib(t), 0.12, 0.25)
        SOUNDS["heal"] = generate_wave(lambda t: 587 if t < 0.08 else (740 if t < 0.16 else 880), 0.28, 0.3)
        SOUNDS["boss_roar"] = generate_wave(lambda t: 130 + 50 * math.sin(t * 40) - t * 40, 0.45, 0.4)
        SOUNDS["boss_slam"] = generate_wave(lambda t: max(50, 180 - t * 500), 0.35, 0.45)
    except Exception as e:
        print("Audio init notice:", e)

def random_vib(t):
    return 15 * math.sin(t * 120)

def play_sfx(name):
    snd = SOUNDS.get(name)
    if snd:
        try:
            snd.play()
        except:
            pass
