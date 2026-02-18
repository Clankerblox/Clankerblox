"""Procedural Obby Generator v2 - Teleport-based sections with moving obstacles.

Each themed section is placed in a SEPARATE AREA (2000 studs apart on Z axis).
Players teleport between sections via entry/exit pads.
Each section has its own baseplate, walls, and atmosphere.

Roblox Character Physics (JumpPower=50, WalkSpeed=24 sprint, Gravity=196.2):
- Jump height: ~7.2 studs (center of mass), can clear ~11 stud blocks (legs below COM)
- Max horizontal jump at WalkSpeed=24: ~12.2 studs
- Max practical jump (edge jump, sprint): ~11 studs
- Sprint safe jump: ~9 studs comfortable
- Time in air: ~0.51 seconds
- Character height: ~5 studs (R15)

Difficulty Chart (tuned for WalkSpeed=24 sprint):
- Section 1 (lobby): 3-4 stud gaps, 10x10 platforms (baby easy)
- Section 2: 4-5.5 stud gaps, 8x8 platforms
- Section 3-4: 5-7 stud gaps, 6x6 platforms
- Section 5-6: 6-7.5 stud gaps, 5x5, moving obstacles introduced
- Section 7-8: 7-8.5 stud gaps, 4x4, more moving obstacles, smaller platforms
"""
import random
import math
import json
from typing import Optional

# ============================================================
# ROBLOX PHYSICS CONSTANTS (validated from DevForum + DCOS Wiki)
# ============================================================
MAX_JUMP_HEIGHT = 7.2       # studs - center of mass rise
MAX_JUMP_DISTANCE = 9.0     # studs - practical max horizontal jump
SAFE_JUMP_HEIGHT = 5.0      # studs - comfortable upward jump
SAFE_JUMP_DISTANCE = 7.0    # studs - comfortable horizontal gap
PLAYER_HEIGHT = 5.0         # studs (R15 avatar)
DEFAULT_WALK_SPEED = 16.0   # studs/sec
GRAVITY = 196.2             # studs/s^2

# Sprint mode constants (WalkSpeed=24)
SPRINT_WALK_SPEED = 24.0
SPRINT_MAX_JUMP_DISTANCE = 11.0   # practical max at sprint speed
SPRINT_SAFE_JUMP_DISTANCE = 9.0   # comfortable at sprint speed

# Section separation distance on Z axis
SECTION_Z_SPACING = 2000

# ============================================================
# THEME DEFINITIONS
# ============================================================
THEMES = {
    "lobby": {
        "name": "Spawn Lobby",
        "baseplate_color": [0.3, 0.7, 0.3],   # Green grass
        "baseplate_material": "Grass",
        "platform_colors": [[1, 0.85, 0], [0.3, 0.9, 0.3], [0.4, 0.8, 1]],
        "platform_material": "SmoothPlastic",
        "accent_material": "Neon",
        "accent_colors": [[1, 1, 0], [0, 1, 0.5]],
        "wall_colors": [[0.9, 0.9, 0.95]],
        "wall_material": "SmoothPlastic",
        "sky_hint": "bright day",
        "kill_color": None,  # No kill bricks in lobby
    },
    "lava_volcano": {
        "name": "Volcanic Inferno",
        "baseplate_color": [0.15, 0.08, 0.02],   # Dark volcanic rock
        "baseplate_material": "Slate",
        "platform_colors": [[0.4, 0.2, 0.1], [0.6, 0.3, 0.1], [0.3, 0.15, 0.05]],
        "platform_material": "Slate",
        "accent_material": "Neon",
        "accent_colors": [[1, 0.3, 0], [1, 0.1, 0], [1, 0.6, 0]],
        "wall_colors": [[0.2, 0.1, 0.05], [0.35, 0.15, 0.05]],
        "wall_material": "Granite",
        "sky_hint": "red sky",
        "kill_color": [1, 0.15, 0],  # Lava
    },
    "ice_crystal": {
        "name": "Frozen Peaks",
        "baseplate_color": [0.7, 0.85, 1.0],
        "baseplate_material": "Ice",
        "platform_colors": [[0.6, 0.8, 1], [0.4, 0.7, 0.95], [0.8, 0.9, 1]],
        "platform_material": "Ice",
        "accent_material": "Neon",
        "accent_colors": [[0, 0.8, 1], [0.5, 0.5, 1], [0, 1, 1]],
        "wall_colors": [[0.85, 0.92, 1], [0.7, 0.85, 0.95]],
        "wall_material": "Glass",
        "sky_hint": "snowy",
        "kill_color": [0, 0.2, 0.6],  # Freezing water
    },
    "neon_cyber": {
        "name": "Neon Cyber City",
        "baseplate_color": [0.05, 0.05, 0.1],
        "baseplate_material": "SmoothPlastic",
        "platform_colors": [[0.1, 0.1, 0.2], [0.05, 0.05, 0.15], [0.15, 0.1, 0.2]],
        "platform_material": "SmoothPlastic",
        "accent_material": "Neon",
        "accent_colors": [[1, 0, 1], [0, 1, 1], [1, 0, 0.5], [0.5, 0, 1]],
        "wall_colors": [[0.08, 0.08, 0.15]],
        "wall_material": "Metal",
        "sky_hint": "dark neon",
        "kill_color": [1, 0, 0.3],  # Electric
    },
    "candy_land": {
        "name": "Candy Kingdom",
        "baseplate_color": [1, 0.7, 0.8],
        "baseplate_material": "SmoothPlastic",
        "platform_colors": [[1, 0.4, 0.6], [0.6, 0.3, 1], [0.3, 0.9, 0.6], [1, 0.9, 0.3]],
        "platform_material": "SmoothPlastic",
        "accent_material": "Neon",
        "accent_colors": [[1, 0.3, 0.5], [0.4, 1, 0.8], [1, 1, 0.3]],
        "wall_colors": [[1, 0.8, 0.85], [0.8, 0.6, 1]],
        "wall_material": "SmoothPlastic",
        "sky_hint": "pink sunset",
        "kill_color": [0.6, 0, 0.3],  # Poison candy
    },
    "space_galaxy": {
        "name": "Galactic Odyssey",
        "baseplate_color": [0.02, 0.02, 0.08],
        "baseplate_material": "SmoothPlastic",
        "platform_colors": [[0.2, 0.1, 0.4], [0.1, 0.2, 0.5], [0.3, 0.1, 0.3]],
        "platform_material": "Metal",
        "accent_material": "Neon",
        "accent_colors": [[0.5, 0, 1], [0, 0.5, 1], [1, 0, 0.8], [0, 1, 0.5]],
        "wall_colors": [[0.05, 0.05, 0.15]],
        "wall_material": "DiamondPlate",
        "sky_hint": "dark space",
        "kill_color": [0.3, 0, 0.6],  # Void
    },
    "jungle_temple": {
        "name": "Ancient Jungle Temple",
        "baseplate_color": [0.15, 0.35, 0.1],
        "baseplate_material": "Grass",
        "platform_colors": [[0.4, 0.35, 0.2], [0.5, 0.4, 0.25], [0.3, 0.25, 0.15]],
        "platform_material": "Cobblestone",
        "accent_material": "Neon",
        "accent_colors": [[0, 1, 0.3], [0.8, 0.8, 0], [0, 0.8, 0.4]],
        "wall_colors": [[0.35, 0.3, 0.2], [0.25, 0.4, 0.15]],
        "wall_material": "Brick",
        "sky_hint": "misty jungle",
        "kill_color": [0.1, 0.5, 0],  # Poison
    },
    "rainbow_sky": {
        "name": "Rainbow Skylands",
        "baseplate_color": [0.4, 0.7, 1.0],
        "baseplate_material": "SmoothPlastic",
        "platform_colors": [[1, 0.2, 0.2], [1, 0.6, 0], [1, 1, 0], [0, 0.8, 0], [0, 0.5, 1], [0.5, 0, 1]],
        "platform_material": "SmoothPlastic",
        "accent_material": "Neon",
        "accent_colors": [[1, 1, 1], [1, 0.8, 0]],
        "wall_colors": [[0.9, 0.9, 1]],
        "wall_material": "SmoothPlastic",
        "sky_hint": "bright clouds",
        "kill_color": None,  # Fall off = death
    },
}

# Theme order for a 30-stage obby (8 sections)
DEFAULT_THEME_SEQUENCE = [
    "lobby",          # Section 1: Baby-easy intro
    "candy_land",     # Section 2: Fun and colorful
    "jungle_temple",  # Section 3: Adventure feel
    "lava_volcano",   # Section 4: Getting intense
    "ice_crystal",    # Section 5: Tricky ice + moving platforms
    "neon_cyber",     # Section 6: Cool vibes + more movers
    "space_galaxy",   # Section 7: Epic + lots of movers
    "rainbow_sky",    # Section 8: Grand finale
]


# ============================================================
# SECTION DIFFICULTY CONFIGURATION
# ============================================================

def _section_difficulty_config(section_index: int) -> dict:
    """Returns difficulty parameters for a given section (0-indexed).

    All gap values assume WalkSpeed=24 (sprint mode).
    Sprint max practical jump ~11 studs, so 8.5 is still very comfortable.
    """
    configs = {
        0: {  # Lobby - baby easy
            "gap_min": 3.0, "gap_max": 4.0,
            "platform_min": 9, "platform_max": 11,
            "v_offset_max": 0.5,
            "moving_chance": 0.0,
            "spinning_chance": 0.0,
            "kill_brick_chance": 0.0,
        },
        1: {  # Section 2 - easy
            "gap_min": 4.0, "gap_max": 5.5,
            "platform_min": 7, "platform_max": 9,
            "v_offset_max": 1.0,
            "moving_chance": 0.0,
            "spinning_chance": 0.0,
            "kill_brick_chance": 0.0,
        },
        2: {  # Section 3 - easy-medium
            "gap_min": 5.0, "gap_max": 7.0,
            "platform_min": 6, "platform_max": 7,
            "v_offset_max": 2.0,
            "moving_chance": 0.05,
            "spinning_chance": 0.0,
            "kill_brick_chance": 0.1,
        },
        3: {  # Section 4 - medium
            "gap_min": 5.0, "gap_max": 7.0,
            "platform_min": 5, "platform_max": 7,
            "v_offset_max": 2.5,
            "moving_chance": 0.1,
            "spinning_chance": 0.05,
            "kill_brick_chance": 0.15,
        },
        4: {  # Section 5 - medium-hard, moving obstacles start
            "gap_min": 6.0, "gap_max": 7.5,
            "platform_min": 5, "platform_max": 6,
            "v_offset_max": 3.0,
            "moving_chance": 0.3,
            "spinning_chance": 0.1,
            "kill_brick_chance": 0.2,
        },
        5: {  # Section 6 - hard, more movers
            "gap_min": 6.0, "gap_max": 7.5,
            "platform_min": 4, "platform_max": 6,
            "v_offset_max": 3.0,
            "moving_chance": 0.4,
            "spinning_chance": 0.15,
            "kill_brick_chance": 0.25,
        },
        6: {  # Section 7 - hard+
            "gap_min": 6.5, "gap_max": 8.0,  # Capped at 8.0 (safe sprint max)
            "platform_min": 4, "platform_max": 5,
            "v_offset_max": 3.0,  # Reduced — upward jumps shorten range
            "moving_chance": 0.5,
            "spinning_chance": 0.2,
            "kill_brick_chance": 0.3,
        },
        7: {  # Section 8 - expert finale
            "gap_min": 6.5, "gap_max": 8.0,  # Capped at 8.0 (safe sprint max)
            "platform_min": 3, "platform_max": 5,
            "v_offset_max": 3.0,  # Reduced — never combine max gap + max height
            "moving_chance": 0.55,
            "spinning_chance": 0.25,
            "kill_brick_chance": 0.3,
        },
    }
    # Clamp to valid range
    idx = min(section_index, max(configs.keys()))
    return configs.get(idx, configs[7])


def _platform_gap_for_section(config: dict) -> tuple:
    """Get horizontal gap and vertical offset for a section's difficulty config.

    Returns (horizontal_gap, vertical_offset).
    """
    h_gap = random.uniform(config["gap_min"], config["gap_max"])
    v_offset = random.uniform(-0.5, config["v_offset_max"])
    return (round(h_gap, 1), round(v_offset, 1))


def _platform_size_for_section(config: dict) -> list:
    """Get platform [width, height, depth] for a section's difficulty config."""
    w = random.randint(config["platform_min"], config["platform_max"])
    d = random.randint(config["platform_min"], config["platform_max"])
    return [w, 1, d]


# ============================================================
# OBSTACLE GENERATORS (per-platform level)
# ============================================================

def generate_normal_platform(x, y, z, config, theme, stage_num) -> list:
    """Standard platform jump."""
    parts = []
    size = _platform_size_for_section(config)
    color = random.choice(theme["platform_colors"])

    part = {
        "name": f"Stage{stage_num}_Platform",
        "type": "Part",
        "position": [round(x, 1), round(y, 1), round(z, 1)],
        "size": size,
        "color": color,
        "material": theme["platform_material"],
        "anchored": True,
        "can_collide": True,
        "transparency": 0,
    }

    # Possibly make it a moving platform
    if random.random() < config["moving_chance"]:
        axis = random.choice(["x", "z"])
        part["is_moving"] = True
        part["move_axis"] = axis
        part["move_distance"] = random.uniform(4, 10)
        part["move_speed"] = random.uniform(3, 7)

    parts.append(part)
    return parts


def generate_moving_platform(x, y, z, config, theme, stage_num) -> list:
    """Platform that moves back and forth on an axis. Always moving."""
    parts = []
    size = _platform_size_for_section(config)
    # Moving platforms are slightly larger for fairness
    size[0] = max(size[0], 5)
    size[2] = max(size[2], 5)
    color = random.choice(theme["accent_colors"])
    axis = random.choice(["x", "y", "z"])

    if axis == "y":
        move_dist = random.uniform(3, 6)
        move_speed = random.uniform(2, 4)
    else:
        move_dist = random.uniform(5, 12)
        move_speed = random.uniform(3, 7)

    parts.append({
        "name": f"Stage{stage_num}_MovingPlat",
        "type": "Part",
        "position": [round(x, 1), round(y, 1), round(z, 1)],
        "size": size,
        "color": color,
        "material": theme["accent_material"],
        "anchored": True,
        "can_collide": True,
        "transparency": 0,
        "is_moving": True,
        "move_axis": axis,
        "move_distance": round(move_dist, 1),
        "move_speed": round(move_speed, 1),
    })
    return parts


def generate_rising_falling_platform(x, y, z, config, theme, stage_num) -> list:
    """Platform that rises and falls on Y axis."""
    parts = []
    size = _platform_size_for_section(config)
    size[0] = max(size[0], 5)
    size[2] = max(size[2], 5)

    parts.append({
        "name": f"Stage{stage_num}_RisingPlat",
        "type": "Part",
        "position": [round(x, 1), round(y, 1), round(z, 1)],
        "size": size,
        "color": random.choice(theme["accent_colors"]),
        "material": theme["accent_material"],
        "anchored": True,
        "can_collide": True,
        "transparency": 0,
        "is_moving": True,
        "move_axis": "y",
        "move_distance": round(random.uniform(4, 8), 1),
        "move_speed": round(random.uniform(2, 4), 1),
    })
    return parts


def generate_spinning_obstacle(x, y, z, config, theme, stage_num) -> list:
    """A spinning beam/bar that players must dodge or time their jumps around.
    Placed ON TOP of a static platform so there's something to stand on."""
    parts = []
    plat_size = _platform_size_for_section(config)
    plat_size[0] = max(plat_size[0], 8)
    plat_size[2] = max(plat_size[2], 8)

    # Static platform base
    parts.append({
        "name": f"Stage{stage_num}_SpinBase",
        "type": "Part",
        "position": [round(x, 1), round(y, 1), round(z, 1)],
        "size": plat_size,
        "color": random.choice(theme["platform_colors"]),
        "material": theme["platform_material"],
        "anchored": True,
        "can_collide": True,
        "transparency": 0,
    })

    # Spinning bar above the platform (player must jump over it)
    bar_length = plat_size[0] + 4
    parts.append({
        "name": f"Stage{stage_num}_SpinBar",
        "type": "Part",
        "position": [round(x, 1), round(y + 3, 1), round(z, 1)],
        "size": [bar_length, 2, 2],
        "color": random.choice(theme["accent_colors"]),
        "material": "Neon",
        "anchored": True,
        "can_collide": True,
        "transparency": 0,
        "is_spinning": True,
        "spin_speed": round(random.uniform(1.5, 4.0), 1),
        "is_kill_brick": True,
    })

    return parts


def generate_pendulum_swing(x, y, z, config, theme, stage_num) -> list:
    """A pendulum obstacle that swings back and forth. Players time their run past it.
    Has a large platform to cross with the pendulum overhead."""
    parts = []
    plat_width = max(10, config["platform_max"] + 4)
    plat_depth = random.randint(16, 24)

    # Long platform to cross
    parts.append({
        "name": f"Stage{stage_num}_PendulumFloor",
        "type": "Part",
        "position": [round(x, 1), round(y, 1), round(z + plat_depth / 2, 1)],
        "size": [plat_width, 1, plat_depth],
        "color": random.choice(theme["platform_colors"]),
        "material": theme["platform_material"],
        "anchored": True,
        "can_collide": True,
        "transparency": 0,
    })

    # Pendulum arm (swings on X axis across the path)
    num_pendulums = random.randint(1, 3)
    for i in range(num_pendulums):
        pz = z + (i + 1) * (plat_depth / (num_pendulums + 1))
        parts.append({
            "name": f"Stage{stage_num}_Pendulum{i + 1}",
            "type": "Part",
            "position": [round(x, 1), round(y + 4, 1), round(pz, 1)],
            "size": [8, 3, 2],
            "color": random.choice(theme["accent_colors"]),
            "material": "Neon",
            "anchored": True,
            "can_collide": True,
            "transparency": 0,
            "is_moving": True,
            "move_axis": "x",
            "move_distance": round(random.uniform(6, 12), 1),
            "move_speed": round(random.uniform(4, 8), 1),
            "is_kill_brick": True,
        })

    return parts


def generate_thin_walkway(x, y, z, config, theme, stage_num) -> list:
    """Thin beam to walk across - tests precision."""
    parts = []
    length = random.randint(12, 25)
    width = max(2, config["platform_min"] - 4)

    parts.append({
        "name": f"Stage{stage_num}_Walkway",
        "type": "Part",
        "position": [round(x, 1), round(y, 1), round(z + length / 2, 1)],
        "size": [width, 1, length],
        "color": random.choice(theme["platform_colors"]),
        "material": theme["platform_material"],
        "anchored": True,
        "can_collide": True,
        "transparency": 0,
    })
    return parts


def generate_staircase(x, y, z, config, theme, stage_num) -> list:
    """Ascending staircase of blocks."""
    parts = []
    steps = random.randint(4, 8)
    step_height = random.uniform(2, 3.5)
    step_depth = random.uniform(5, 7)

    for i in range(steps):
        color = random.choice(theme["platform_colors"])
        if i % 2 == 0:
            color = random.choice(theme["accent_colors"])
        parts.append({
            "name": f"Stage{stage_num}_Step{i + 1}",
            "type": "Part",
            "position": [round(x, 1), round(y + i * step_height, 1), round(z + i * step_depth, 1)],
            "size": [6, 1, 5],
            "color": color,
            "material": theme["platform_material"],
            "anchored": True,
            "can_collide": True,
            "transparency": 0,
        })
    return parts


def generate_zigzag(x, y, z, config, theme, stage_num) -> list:
    """Zigzag platforms alternating left and right."""
    parts = []
    count = random.randint(4, 7)
    gap_z = random.uniform(config["gap_min"], config["gap_max"])
    gap_x = random.uniform(config["gap_min"], config["gap_max"])

    for i in range(count):
        side = 1 if i % 2 == 0 else -1
        px = x + side * gap_x / 2
        pz = z + i * gap_z
        py = y + random.uniform(0, config["v_offset_max"] * 0.5)

        part = {
            "name": f"Stage{stage_num}_Zig{i + 1}",
            "type": "Part",
            "position": [round(px, 1), round(py, 1), round(pz, 1)],
            "size": _platform_size_for_section(config),
            "color": random.choice(theme["platform_colors"] if i % 2 == 0 else theme["accent_colors"]),
            "material": theme["accent_material"] if i % 3 == 0 else theme["platform_material"],
            "anchored": True,
            "can_collide": True,
            "transparency": 0,
        }

        # Some zigzag platforms can move in later sections
        if random.random() < config["moving_chance"] * 0.5:
            part["is_moving"] = True
            part["move_axis"] = "x"
            part["move_distance"] = round(random.uniform(3, 6), 1)
            part["move_speed"] = round(random.uniform(2, 5), 1)

        parts.append(part)
    return parts


def generate_kill_brick_section(x, y, z, config, theme, stage_num) -> list:
    """Platform with kill bricks that must be avoided."""
    parts = []

    if theme["kill_color"] is None:
        return generate_normal_platform(x, y, z, config, theme, stage_num)

    platform_width = 14
    platform_depth = 20

    # Kill floor
    parts.append({
        "name": f"Stage{stage_num}_KillFloor",
        "type": "Part",
        "position": [round(x, 1), round(y - 0.5, 1), round(z + platform_depth / 2, 1)],
        "size": [platform_width, 0.5, platform_depth],
        "color": theme["kill_color"],
        "material": "Neon",
        "anchored": True,
        "can_collide": True,
        "transparency": 0,
        "is_kill_brick": True,
    })

    # Safe path through the kill bricks
    path_z = z + 2
    for i in range(4):
        side = random.uniform(-platform_width / 3, platform_width / 3)
        parts.append({
            "name": f"Stage{stage_num}_SafePath{i + 1}",
            "type": "Part",
            "position": [round(x + side, 1), round(y + 0.5, 1), round(path_z, 1)],
            "size": [3, 1, 4],
            "color": random.choice(theme["accent_colors"]),
            "material": "Neon",
            "anchored": True,
            "can_collide": True,
            "transparency": 0,
        })
        path_z += random.uniform(4, 6)

    return parts


def generate_pillar_jumps(x, y, z, config, theme, stage_num) -> list:
    """Tall pillars to jump between - vertical challenge."""
    parts = []
    count = random.randint(3, 6)

    for i in range(count):
        pillar_height = random.uniform(8, 20)
        px = x + random.uniform(-4, 4)
        pz = z + i * random.uniform(config["gap_min"], config["gap_max"] + 1)
        py = y + i * random.uniform(0.5, config["v_offset_max"] * 0.5)

        # Tall pillar
        parts.append({
            "name": f"Stage{stage_num}_Pillar{i + 1}",
            "type": "Part",
            "position": [round(px, 1), round(py - pillar_height / 2 + 0.5, 1), round(pz, 1)],
            "size": [5, round(pillar_height), 5],
            "color": random.choice(theme["wall_colors"]),
            "material": theme["wall_material"],
            "anchored": True,
            "can_collide": True,
            "transparency": 0,
        })

        # Landing pad on top
        parts.append({
            "name": f"Stage{stage_num}_PillarTop{i + 1}",
            "type": "Part",
            "position": [round(px, 1), round(py + 0.5, 1), round(pz, 1)],
            "size": [6, 1, 6],
            "color": random.choice(theme["accent_colors"]),
            "material": "Neon",
            "anchored": True,
            "can_collide": True,
            "transparency": 0,
        })

    return parts


def generate_disappearing_path(x, y, z, config, theme, stage_num) -> list:
    """Platforms that disappear and reappear (script-controlled).
    We place them all visible - the Lua script handles timing."""
    parts = []
    count = random.randint(5, 8)

    for i in range(count):
        pz = z + i * 6
        parts.append({
            "name": f"Stage{stage_num}_Disappear{i + 1}",
            "type": "Part",
            "position": [round(x + random.uniform(-3, 3), 1), round(y, 1), round(pz, 1)],
            "size": [5, 1, 4],
            "color": random.choice(theme["accent_colors"]),
            "material": "Neon",
            "anchored": True,
            "can_collide": True,
            "transparency": 0,
            "is_disappearing": True,
        })

    return parts


def generate_wall_jump_section(x, y, z, config, theme, stage_num) -> list:
    """Two walls with platforms alternating sides - climb up."""
    parts = []
    wall_gap = 12
    levels = random.randint(4, 7)

    wall_height = levels * 6 + 10

    # Left wall
    parts.append({
        "name": f"Stage{stage_num}_WallLeft",
        "type": "Part",
        "position": [round(x - wall_gap / 2 - 1, 1), round(y + wall_height / 2, 1), round(z + 5, 1)],
        "size": [2, round(wall_height), 12],
        "color": random.choice(theme["wall_colors"]),
        "material": theme["wall_material"],
        "anchored": True,
        "can_collide": True,
        "transparency": 0,
    })

    # Right wall
    parts.append({
        "name": f"Stage{stage_num}_WallRight",
        "type": "Part",
        "position": [round(x + wall_gap / 2 + 1, 1), round(y + wall_height / 2, 1), round(z + 5, 1)],
        "size": [2, round(wall_height), 12],
        "color": random.choice(theme["wall_colors"]),
        "material": theme["wall_material"],
        "anchored": True,
        "can_collide": True,
        "transparency": 0,
    })

    # Alternating platforms
    for i in range(levels):
        side = -1 if i % 2 == 0 else 1
        px = x + side * (wall_gap / 2 - 3)
        py = y + 1 + i * 5

        parts.append({
            "name": f"Stage{stage_num}_WallPlat{i + 1}",
            "type": "Part",
            "position": [round(px, 1), round(py, 1), round(z + 5, 1)],
            "size": [5, 1, 5],
            "color": random.choice(theme["accent_colors"]),
            "material": "Neon",
            "anchored": True,
            "can_collide": True,
            "transparency": 0,
        })

    return parts


# Map obstacle types to generators
OBSTACLE_GENERATORS = {
    "normal": generate_normal_platform,
    "moving": generate_moving_platform,
    "rising_falling": generate_rising_falling_platform,
    "spinning": generate_spinning_obstacle,
    "pendulum": generate_pendulum_swing,
    "thin_walkway": generate_thin_walkway,
    "staircase": generate_staircase,
    "zigzag": generate_zigzag,
    "kill_bricks": generate_kill_brick_section,
    "pillar_jumps": generate_pillar_jumps,
    "disappearing": generate_disappearing_path,
    "wall_jump": generate_wall_jump_section,
}

# Obstacle availability by section tier
TIER1_OBSTACLES = ["normal", "thin_walkway", "staircase"]
TIER2_OBSTACLES = ["normal", "zigzag", "staircase", "thin_walkway"]
TIER3_OBSTACLES = ["normal", "zigzag", "staircase", "kill_bricks", "thin_walkway"]
TIER4_OBSTACLES = ["zigzag", "kill_bricks", "pillar_jumps", "moving", "thin_walkway"]
TIER5_OBSTACLES = ["zigzag", "kill_bricks", "pillar_jumps", "moving", "rising_falling",
                   "spinning", "disappearing"]
TIER6_OBSTACLES = ["zigzag", "kill_bricks", "pillar_jumps", "moving", "rising_falling",
                   "spinning", "pendulum", "disappearing", "wall_jump"]

SECTION_OBSTACLE_TIERS = {
    0: TIER1_OBSTACLES,
    1: TIER2_OBSTACLES,
    2: TIER3_OBSTACLES,
    3: TIER3_OBSTACLES,
    4: TIER4_OBSTACLES,
    5: TIER5_OBSTACLES,
    6: TIER6_OBSTACLES,
    7: TIER6_OBSTACLES,
}


# ============================================================
# DECORATION & UTILITY GENERATORS
# ============================================================

def generate_checkpoint(x, y, z, stage_num, theme) -> list:
    """Checkpoint flag/pad at a stage."""
    parts = []

    # Checkpoint pad (glowing)
    parts.append({
        "name": f"Checkpoint_{stage_num}",
        "type": "Part",
        "position": [round(x, 1), round(y + 0.25, 1), round(z, 1)],
        "size": [8, 0.5, 8],
        "color": [1, 0.85, 0],  # Gold
        "material": "Neon",
        "anchored": True,
        "can_collide": True,
        "transparency": 0,
        "is_checkpoint": True,
        "stage": stage_num,
    })

    # Flag pole
    parts.append({
        "name": f"FlagPole_{stage_num}",
        "type": "Part",
        "position": [round(x + 3, 1), round(y + 5, 1), round(z, 1)],
        "size": [0.5, 10, 0.5],
        "color": [0.8, 0.8, 0.8],
        "material": "Metal",
        "anchored": True,
        "can_collide": True,
        "transparency": 0,
    })

    # Flag
    parts.append({
        "name": f"Flag_{stage_num}",
        "type": "Part",
        "position": [round(x + 5, 1), round(y + 9, 1), round(z, 1)],
        "size": [4, 2.5, 0.3],
        "color": random.choice(theme["accent_colors"]),
        "material": "Neon",
        "anchored": True,
        "can_collide": False,
        "transparency": 0,
    })

    return parts


def generate_stage_sign(x, y, z, stage_num, theme_name) -> list:
    """Stage number display sign."""
    parts = []

    # Sign board
    parts.append({
        "name": f"StageSign_{stage_num}",
        "type": "Part",
        "position": [round(x - 5, 1), round(y + 4, 1), round(z, 1)],
        "size": [0.5, 4, 6],
        "color": [0.1, 0.1, 0.15],
        "material": "SmoothPlastic",
        "anchored": True,
        "can_collide": True,
        "transparency": 0,
        "is_stage_sign": True,
        "stage": stage_num,
        "theme_name": theme_name,
    })

    # Neon outline
    parts.append({
        "name": f"SignGlow_{stage_num}",
        "type": "Part",
        "position": [round(x - 5.3, 1), round(y + 4, 1), round(z, 1)],
        "size": [0.2, 4.5, 6.5],
        "color": [1, 1, 0],
        "material": "Neon",
        "anchored": True,
        "can_collide": False,
        "transparency": 0.2,
    })

    return parts


def _generate_section_baseplate(cx, cy, cz, theme, section_index, section_name) -> list:
    """Generate the ground floor for a section.

    CRITICAL FIX v4.1: The baseplate itself is now a KILL BRICK for sections 1+.
    This prevents players from falling to the ground and walking around obstacles.
    Section 0 (lobby) keeps a walkable baseplate since it's the tutorial area.
    A secondary kill floor is placed deeper as a safety net.
    """
    parts = []
    baseplate_size_x = 120
    baseplate_size_z = 200

    is_lobby = section_index == 0
    kill_color = theme.get("kill_color") or [1, 0, 0]  # Default red if no theme kill color

    if is_lobby:
        # Lobby: walkable baseplate (tutorial area)
        parts.append({
            "name": f"Section{section_index}_Baseplate",
            "type": "Part",
            "position": [round(cx, 1), round(cy - 1, 1), round(cz + baseplate_size_z / 2, 1)],
            "size": [baseplate_size_x, 2, baseplate_size_z],
            "color": theme["baseplate_color"],
            "material": theme["baseplate_material"],
            "anchored": True,
            "can_collide": True,
            "transparency": 0,
            "is_baseplate": True,
            "section_index": section_index,
        })
    else:
        # Non-lobby: baseplate IS a kill brick — falling = death
        # Visual floor (thin, slightly transparent, shows the theme color)
        parts.append({
            "name": f"Section{section_index}_KillFloor_Main",
            "type": "Part",
            "position": [round(cx, 1), round(cy - 1, 1), round(cz + baseplate_size_z / 2, 1)],
            "size": [baseplate_size_x, 2, baseplate_size_z],
            "color": kill_color,
            "material": "Neon",
            "anchored": True,
            "can_collide": True,
            "transparency": 0.15,
            "is_kill_brick": True,
            "is_baseplate": True,
            "section_index": section_index,
        })

    # Safety net kill floor DEEP below (catches any edge cases)
    parts.append({
        "name": f"Section{section_index}_KillFloor_Deep",
        "type": "Part",
        "position": [round(cx, 1), round(cy - 50, 1), round(cz + baseplate_size_z / 2, 1)],
        "size": [baseplate_size_x + 60, 2, baseplate_size_z + 60],
        "color": kill_color,
        "material": "Neon",
        "anchored": True,
        "can_collide": True,
        "transparency": 0,
        "is_kill_brick": True,
        "section_index": section_index,
    })

    return parts


def _generate_section_walls(cx, cy, cz, theme, section_index) -> list:
    """Generate boundary walls for a section.

    Walls extend from below the ground up to 50 studs high.
    This ensures players CANNOT escape the section boundaries.
    """
    parts = []
    wall_height = 50  # Tall enough that no jump can clear it
    baseplate_size_x = 120
    baseplate_size_z = 200
    wall_transparency = 0.6 if theme["wall_material"] == "Glass" else 0.3

    wall_color = random.choice(theme["wall_colors"])

    wall_base = {
        "anchored": True,
        "can_collide": True,
        "transparency": wall_transparency,
        "is_wall": True,
        "section_index": section_index,
    }

    # Left wall
    parts.append({
        **wall_base,
        "name": f"Section{section_index}_WallLeft",
        "type": "Part",
        "position": [round(cx - baseplate_size_x / 2 - 1, 1), round(cy + wall_height / 2 - 10, 1),
                      round(cz + baseplate_size_z / 2, 1)],
        "size": [2, wall_height, baseplate_size_z + 4],
        "color": wall_color,
        "material": theme["wall_material"],
    })

    # Right wall
    parts.append({
        **wall_base,
        "name": f"Section{section_index}_WallRight",
        "type": "Part",
        "position": [round(cx + baseplate_size_x / 2 + 1, 1), round(cy + wall_height / 2 - 10, 1),
                      round(cz + baseplate_size_z / 2, 1)],
        "size": [2, wall_height, baseplate_size_z + 4],
        "color": wall_color,
        "material": theme["wall_material"],
    })

    # Back wall (behind entry)
    parts.append({
        **wall_base,
        "name": f"Section{section_index}_WallBack",
        "type": "Part",
        "position": [round(cx, 1), round(cy + wall_height / 2 - 10, 1), round(cz - 1, 1)],
        "size": [baseplate_size_x + 4, wall_height, 2],
        "color": wall_color,
        "material": theme["wall_material"],
    })

    # Front wall (past exit)
    parts.append({
        **wall_base,
        "name": f"Section{section_index}_WallFront",
        "type": "Part",
        "position": [round(cx, 1), round(cy + wall_height / 2 - 10, 1), round(cz + baseplate_size_z + 1, 1)],
        "size": [baseplate_size_x + 4, wall_height, 2],
        "color": wall_color,
        "material": theme["wall_material"],
    })

    return parts


def _generate_entry_teleport_pad(x, y, z, section_index) -> list:
    """Generate the entry teleport pad where players arrive in a section."""
    parts = []

    # Entry pad (large, glowing)
    parts.append({
        "name": f"Section{section_index}_EntryPad",
        "type": "Part",
        "position": [round(x, 1), round(y + 0.25, 1), round(z, 1)],
        "size": [12, 0.5, 12],
        "color": [0, 1, 0.5],  # Green glow
        "material": "Neon",
        "anchored": True,
        "can_collide": True,
        "transparency": 0,
        "is_section_entry": True,
        "section_index": section_index,
    })

    # Entry ring effect
    parts.append({
        "name": f"Section{section_index}_EntryRing",
        "type": "Part",
        "position": [round(x, 1), round(y + 3, 1), round(z, 1)],
        "size": [14, 0.5, 14],
        "color": [0, 1, 0.5],
        "material": "Neon",
        "anchored": True,
        "can_collide": False,
        "transparency": 0.5,
    })

    return parts


def _generate_exit_teleport_pad(x, y, z, section_index, next_section_index,
                                 next_entry_pos) -> list:
    """Generate the exit teleport pad that sends players to the next section."""
    parts = []

    # Exit pad (large, glowing different color)
    parts.append({
        "name": f"Section{section_index}_ExitPad",
        "type": "Part",
        "position": [round(x, 1), round(y + 0.25, 1), round(z, 1)],
        "size": [12, 0.5, 12],
        "color": [1, 0.5, 0],  # Orange glow
        "material": "Neon",
        "anchored": True,
        "can_collide": True,
        "transparency": 0,
        "is_teleport": True,
        "teleport_to": [round(next_entry_pos[0], 1), round(next_entry_pos[1] + 3, 1),
                         round(next_entry_pos[2], 1)],
        "is_section_exit": True,
        "section_index": section_index,
        "next_section_index": next_section_index,
    })

    # Exit ring effect
    parts.append({
        "name": f"Section{section_index}_ExitRing",
        "type": "Part",
        "position": [round(x, 1), round(y + 3, 1), round(z, 1)],
        "size": [14, 0.5, 14],
        "color": [1, 0.5, 0],
        "material": "Neon",
        "anchored": True,
        "can_collide": False,
        "transparency": 0.5,
    })

    # "NEXT SECTION" sign above exit
    parts.append({
        "name": f"Section{section_index}_ExitSign",
        "type": "Part",
        "position": [round(x, 1), round(y + 8, 1), round(z, 1)],
        "size": [12, 3, 0.5],
        "color": [0.1, 0.1, 0.15],
        "material": "SmoothPlastic",
        "anchored": True,
        "can_collide": False,
        "transparency": 0,
        "is_stage_sign": True,
        "stage": -1,
        "theme_name": f"Next: Section {next_section_index + 1}",
    })

    return parts


def _generate_victory_exit_pad(x, y, z, section_index) -> list:
    """Generate the final victory pad for the last section (no teleport)."""
    parts = []

    parts.append({
        "name": f"Section{section_index}_VictoryPad",
        "type": "Part",
        "position": [round(x, 1), round(y + 0.25, 1), round(z, 1)],
        "size": [20, 0.5, 20],
        "color": [1, 0.85, 0],
        "material": "Neon",
        "anchored": True,
        "can_collide": True,
        "transparency": 0,
        "is_victory": True,
    })

    # Victory arch pillars
    for side in [-1, 1]:
        parts.append({
            "name": f"VictoryPillar_{'L' if side < 0 else 'R'}",
            "type": "Part",
            "position": [round(x + side * 12, 1), round(y + 12, 1), round(z, 1)],
            "size": [3, 24, 3],
            "color": [1, 0.85, 0],
            "material": "Neon",
            "anchored": True,
            "can_collide": True,
            "transparency": 0,
        })

    # Victory arch top
    parts.append({
        "name": "VictoryArch",
        "type": "Part",
        "position": [round(x, 1), round(y + 24, 1), round(z, 1)],
        "size": [30, 3, 3],
        "color": [1, 0.85, 0],
        "material": "Neon",
        "anchored": True,
        "can_collide": True,
        "transparency": 0,
    })

    # Trophy
    parts.append({
        "name": "Trophy",
        "type": "Part",
        "position": [round(x, 1), round(y + 5, 1), round(z, 1)],
        "size": [4, 4, 4],
        "color": [1, 0.85, 0],
        "material": "Neon",
        "anchored": True,
        "can_collide": False,
        "transparency": 0,
        "shape": 2,  # Sphere
        "is_trophy": True,
    })

    # Celebration sparkle orbs
    for i in range(12):
        angle = (i / 12) * math.pi * 2
        ox = x + math.cos(angle) * 15
        oz = z + math.sin(angle) * 15
        oy = y + 10 + math.sin(angle * 3) * 5

        parts.append({
            "name": f"CelebOrb_{i}",
            "type": "Part",
            "position": [round(ox, 1), round(oy, 1), round(oz, 1)],
            "size": [2, 2, 2],
            "color": random.choice([[1, 0, 0], [1, 0.5, 0], [1, 1, 0],
                                     [0, 1, 0], [0, 0.5, 1], [0.5, 0, 1]]),
            "material": "Neon",
            "anchored": True,
            "can_collide": False,
            "transparency": 0.3,
            "shape": 2,
        })

    return parts


def _generate_section_decorations(cx, cy, cz, theme, section_index) -> list:
    """Background decorations for a themed section area."""
    parts = []
    baseplate_size_z = 200

    # Side decoration columns/structures
    for i in range(random.randint(3, 6)):
        side = random.choice([-1, 1])
        dz = cz + random.uniform(20, baseplate_size_z - 20)
        wall_height = random.uniform(8, 25)

        parts.append({
            "name": f"Section{section_index}_Deco_Wall_{i}",
            "type": "Part",
            "position": [round(cx + side * random.uniform(30, 50), 1),
                          round(cy + wall_height / 2, 1), round(dz, 1)],
            "size": [random.uniform(2, 5), round(wall_height), random.uniform(3, 10)],
            "color": random.choice(theme["wall_colors"]),
            "material": theme["wall_material"],
            "anchored": True,
            "can_collide": True,
            "transparency": random.uniform(0, 0.3),
        })

    # Floating accent orbs/cubes
    for i in range(random.randint(4, 10)):
        dz = cz + random.uniform(10, baseplate_size_z - 10)
        parts.append({
            "name": f"Section{section_index}_Deco_Float_{i}",
            "type": "Part",
            "position": [
                round(cx + random.uniform(-40, 40), 1),
                round(cy + random.uniform(15, 40), 1),
                round(dz, 1)
            ],
            "size": [random.uniform(2, 6)] * 3,
            "color": random.choice(theme["accent_colors"]),
            "material": "Neon",
            "anchored": True,
            "can_collide": False,
            "transparency": random.uniform(0.2, 0.6),
            "shape": 2,  # Sphere
        })

    # Section name arch at the entry
    arch_height = 18
    arch_width = 20
    entry_z = cz + 5

    # Left pillar
    parts.append({
        "name": f"Section{section_index}_Arch_Left",
        "type": "Part",
        "position": [round(cx - arch_width / 2, 1), round(cy + arch_height / 2, 1),
                      round(entry_z, 1)],
        "size": [3, arch_height, 3],
        "color": random.choice(theme["accent_colors"]),
        "material": "Neon",
        "anchored": True,
        "can_collide": True,
        "transparency": 0,
    })

    # Right pillar
    parts.append({
        "name": f"Section{section_index}_Arch_Right",
        "type": "Part",
        "position": [round(cx + arch_width / 2, 1), round(cy + arch_height / 2, 1),
                      round(entry_z, 1)],
        "size": [3, arch_height, 3],
        "color": random.choice(theme["accent_colors"]),
        "material": "Neon",
        "anchored": True,
        "can_collide": True,
        "transparency": 0,
    })

    # Top beam
    parts.append({
        "name": f"Section{section_index}_Arch_Top",
        "type": "Part",
        "position": [round(cx, 1), round(cy + arch_height + 1, 1), round(entry_z, 1)],
        "size": [arch_width + 6, 3, 3],
        "color": random.choice(theme["accent_colors"]),
        "material": "Neon",
        "anchored": True,
        "can_collide": True,
        "transparency": 0,
    })

    return parts


# ============================================================
# MAIN OBBY GENERATOR
# ============================================================

def generate_obby(
    num_stages: int = 30,
    theme_sequence: Optional[list] = None,
    game_name: str = "Epic Obby",
    agent_theme_data: Optional[dict] = None,
) -> dict:
    """Generate a complete obby level with teleport-based themed sections.

    Each section is placed 2000 studs apart on the Z axis. Players teleport
    between sections via entry/exit pads. Each section has its own baseplate,
    walls, decorations, and 4-8 stages.

    Args:
        num_stages: Total number of stages (distributed across sections)
        theme_sequence: List of theme keys (defaults to DEFAULT_THEME_SEQUENCE)
        game_name: Display name for the game
        agent_theme_data: Optional theme data from ThemeDesignerAgent.
            If provided, overrides colors/materials per section. Format:
            {
                "sections": [
                    {"index": 0, "name": "...", "platform_color": [r,g,b], ...},
                    ...
                ]
            }

    Returns a dict with:
    - parts: list of all parts
    - stages: list of stage metadata
    - sections: list of section metadata
    - themes_used: list of themes in order
    - total_stages, total_parts
    - game_name
    """
    if theme_sequence is None:
        theme_sequence = DEFAULT_THEME_SEQUENCE

    # If agents provided custom theme data, override THEMES entries
    if agent_theme_data and "sections" in agent_theme_data:
        for sec_data in agent_theme_data["sections"]:
            sec_idx = sec_data.get("index", -1)
            if 0 <= sec_idx < len(theme_sequence):
                theme_key = theme_sequence[sec_idx]
                if theme_key in THEMES:
                    theme = THEMES[theme_key]
                    # Override with agent data (if provided)
                    if "platform_color" in sec_data:
                        theme["platform_colors"] = [sec_data["platform_color"]]
                    if "platform_material" in sec_data:
                        theme["platform_material"] = sec_data["platform_material"]
                    if "accent_color" in sec_data:
                        theme["accent_colors"] = [sec_data["accent_color"]]
                    if "wall_color" in sec_data:
                        theme["wall_colors"] = [sec_data["wall_color"]]
                    if "wall_material" in sec_data:
                        theme["wall_material"] = sec_data["wall_material"]
                    if "floor_color" in sec_data:
                        theme["baseplate_color"] = sec_data["floor_color"]
                    if "floor_material" in sec_data:
                        theme["baseplate_material"] = sec_data["floor_material"]
                    if "kill_brick_color" in sec_data:
                        theme["kill_color"] = sec_data["kill_brick_color"]
                    if "name" in sec_data:
                        theme["name"] = sec_data["name"]

    all_parts = []
    stages = []
    sections = []

    num_sections = len(theme_sequence)

    # Distribute stages across sections (4-8 stages per section, filling evenly)
    base_stages_per_section = max(2, num_stages // num_sections)
    leftover = num_stages - base_stages_per_section * num_sections
    section_stage_counts = []
    for i in range(num_sections):
        count = base_stages_per_section
        if leftover > 0:
            count += 1
            leftover -= 1
        # Clamp to 2-8 range
        count = max(2, min(8, count))
        section_stage_counts.append(count)

    # Adjust if total doesn't match (trim or add to last sections)
    total_assigned = sum(section_stage_counts)
    while total_assigned < num_stages and section_stage_counts[-1] < 10:
        section_stage_counts[-1] += 1
        total_assigned += 1
    while total_assigned > num_stages and section_stage_counts[-1] > 2:
        section_stage_counts[-1] -= 1
        total_assigned -= 1

    # Pre-compute section entry positions (needed for teleport targets)
    section_entry_positions = []
    for sec_idx in range(num_sections):
        section_base_z = sec_idx * SECTION_Z_SPACING
        # Entry pad is at the start of each section area
        entry_x = 0
        entry_y = 5  # 5 studs above ground
        entry_z = section_base_z + 10
        section_entry_positions.append([entry_x, entry_y, entry_z])

    # ---- BUILD EACH SECTION ----
    global_stage_num = 0

    for sec_idx in range(num_sections):
        theme_key = theme_sequence[sec_idx]
        theme = THEMES[theme_key]
        config = _section_difficulty_config(sec_idx)

        section_base_z = sec_idx * SECTION_Z_SPACING
        section_center_x = 0
        section_ground_y = 0

        entry_pos = section_entry_positions[sec_idx]
        stages_in_section = section_stage_counts[sec_idx] if sec_idx < len(section_stage_counts) else 4

        section_start_stage = global_stage_num + 1

        # ---- Section baseplate ----
        bp_parts = _generate_section_baseplate(
            section_center_x, section_ground_y, section_base_z,
            theme, sec_idx, theme["name"]
        )
        all_parts.extend(bp_parts)

        # ---- Section walls ----
        wall_parts = _generate_section_walls(
            section_center_x, section_ground_y, section_base_z,
            theme, sec_idx
        )
        all_parts.extend(wall_parts)

        # ---- Section decorations ----
        deco_parts = _generate_section_decorations(
            section_center_x, section_ground_y, section_base_z,
            theme, sec_idx
        )
        all_parts.extend(deco_parts)

        # ---- Entry teleport pad ----
        entry_tp_parts = _generate_entry_teleport_pad(
            entry_pos[0], entry_pos[1], entry_pos[2], sec_idx
        )
        all_parts.extend(entry_tp_parts)

        # ---- Spawn location (only in first section / lobby) ----
        if sec_idx == 0:
            all_parts.append({
                "name": "SpawnPlatform",
                "type": "SpawnLocation",
                "position": [round(entry_pos[0], 1), round(entry_pos[1] + 0.5, 1),
                              round(entry_pos[2], 1)],
                "size": [12, 1, 12],
                "color": [1, 0.85, 0],
                "material": "Neon",
                "anchored": True,
                "can_collide": True,
                "transparency": 0,
            })

            # Welcome sign
            all_parts.append({
                "name": "WelcomeSign",
                "type": "Part",
                "position": [round(entry_pos[0], 1), round(entry_pos[1] + 8, 1),
                              round(entry_pos[2] - 8, 1)],
                "size": [30, 8, 1],
                "color": [0.1, 0.1, 0.15],
                "material": "SmoothPlastic",
                "anchored": True,
                "can_collide": True,
                "transparency": 0,
                "is_welcome_sign": True,
                "game_name": game_name,
            })

            # Welcome sign glow
            all_parts.append({
                "name": "WelcomeSignGlow",
                "type": "Part",
                "position": [round(entry_pos[0], 1), round(entry_pos[1] + 8, 1),
                              round(entry_pos[2] - 8.3, 1)],
                "size": [31, 9, 0.5],
                "color": [1, 0, 0.8],
                "material": "Neon",
                "anchored": True,
                "can_collide": False,
                "transparency": 0.3,
            })

            # Lobby decorative pillars
            for lx, lz in [(-15, -5), (15, -5), (-15, 25), (15, 25)]:
                all_parts.append({
                    "name": "LobbyPillar",
                    "type": "Part",
                    "position": [lx, section_ground_y + 7, section_base_z + lz],
                    "size": [3, 14, 3],
                    "color": [1, 0.85, 0],
                    "material": "Neon",
                    "anchored": True,
                    "can_collide": True,
                    "transparency": 0,
                })

        # ---- Generate stages within this section ----
        # Cursor starts after the entry pad, moving along Z within the section
        cursor_x = entry_pos[0]
        cursor_y = entry_pos[1]
        cursor_z = entry_pos[2] + 15  # Start a bit ahead of entry pad

        available_obstacles = SECTION_OBSTACLE_TIERS.get(sec_idx, TIER6_OBSTACLES)

        for local_stage in range(stages_in_section):
            global_stage_num += 1
            stage_num = global_stage_num

            # Choose obstacle type
            obstacle_type = random.choice(available_obstacles)

            # Generate obstacle
            generator = OBSTACLE_GENERATORS[obstacle_type]
            obstacle_parts = generator(cursor_x, cursor_y, cursor_z, config, theme, stage_num)

            # Tag all obstacle parts with section_index and stage for validation
            for p in obstacle_parts:
                p["section_index"] = sec_idx
                if "stage" not in p:
                    p["stage"] = stage_num

            all_parts.extend(obstacle_parts)

            # Add checkpoint every 3 stages or at first stage of each section
            if stage_num % 3 == 0 or local_stage == 0:
                last_platform = obstacle_parts[-1] if obstacle_parts else None
                if last_platform:
                    cp_pos = last_platform["position"]
                    cp_y = cp_pos[1] + last_platform["size"][1] / 2 + 0.25
                    cp_parts = generate_checkpoint(cp_pos[0], cp_y, cp_pos[2], stage_num, theme)
                    all_parts.extend(cp_parts)

            # Add stage sign
            sign_parts = generate_stage_sign(cursor_x, cursor_y, cursor_z - 2,
                                              stage_num, theme["name"])
            all_parts.extend(sign_parts)

            # Store stage metadata
            stages.append({
                "stage": stage_num,
                "section_index": sec_idx,
                "theme": theme_key,
                "theme_name": theme["name"],
                "obstacle_type": obstacle_type,
                "position": [round(cursor_x, 1), round(cursor_y, 1), round(cursor_z, 1)],
            })

            # ---- Advance cursor to next stage ----
            # Remember the end of the current obstacle for bridge placement
            last_obstacle_part = obstacle_parts[-1] if obstacle_parts else None
            prev_end_pos = None
            if last_obstacle_part:
                lp = last_obstacle_part["position"]
                ls = last_obstacle_part["size"]
                prev_end_pos = [lp[0], lp[1], lp[2] + ls[2] / 2]

            h_gap, v_offset = _platform_gap_for_section(config)

            # Slight lateral movement for visual variety
            cursor_x += random.uniform(-4, 4)
            cursor_x = max(-30, min(30, cursor_x))

            cursor_y = max(section_ground_y + 3, cursor_y + v_offset)

            # Z advance depends on obstacle type (longer obstacles need more space)
            if obstacle_type in ("thin_walkway", "kill_bricks", "zigzag",
                                  "wall_jump", "pendulum"):
                cursor_z += random.uniform(30, 45)
            elif obstacle_type in ("staircase", "pillar_jumps", "disappearing"):
                cursor_z += random.uniform(20, 35)
            else:
                cursor_z += h_gap + random.uniform(8, 15)

            # ---- BRIDGE PLATFORM: connect end of this stage to start of next ----
            # Ensures no gap between stages exceeds 6 studs (well under 8 stud max).
            # Uses conservative 5-stud spacing so even walk-speed jumps work.
            if prev_end_pos and local_stage < stages_in_section - 1:
                bridge_start_z = prev_end_pos[2] + 1
                bridge_end_z = cursor_z - 1
                bridge_gap = bridge_end_z - bridge_start_z

                MAX_BRIDGE_SPAN = 5.0  # Conservative — must be jumpable without sprint

                if bridge_gap > MAX_BRIDGE_SPAN:
                    num_bridges = max(1, math.ceil(bridge_gap / MAX_BRIDGE_SPAN) - 1)
                    bridge_spacing = bridge_gap / (num_bridges + 1)
                    bridge_y = prev_end_pos[1]
                    # Gentle Y transition — never more than 2 studs per bridge step
                    total_dy = cursor_y - bridge_y
                    max_step = 2.0
                    bridge_y_step = max(-max_step, min(max_step, total_dy / (num_bridges + 1)))

                    plat_color = random.choice(theme["platform_colors"])
                    for bi in range(num_bridges):
                        bz = bridge_start_z + bridge_spacing * (bi + 1)
                        by = bridge_y + bridge_y_step * (bi + 1)
                        bx = prev_end_pos[0] + random.uniform(-2, 2)
                        bx = max(-30, min(30, bx))

                        bridge_size = random.uniform(
                            max(4, config["platform_min"]),
                            config["platform_max"]
                        )

                        all_parts.append({
                            "name": f"Stage{stage_num}_Bridge{bi}",
                            "type": "Part",
                            "position": [round(bx, 1), round(by, 1), round(bz, 1)],
                            "size": [round(bridge_size, 1), 1, round(bridge_size, 1)],
                            "color": plat_color,
                            "material": theme["platform_material"],
                            "anchored": True,
                            "can_collide": True,
                            "transparency": 0,
                            "section_index": sec_idx,
                            "stage": stage_num,
                        })

        section_end_stage = global_stage_num

        # ---- Exit teleport pad (or victory pad for last section) ----
        exit_x = cursor_x
        exit_y = cursor_y
        exit_z = cursor_z + 10

        if sec_idx < num_sections - 1:
            # Regular exit: teleports to next section's entry
            next_entry = section_entry_positions[sec_idx + 1]
            exit_parts = _generate_exit_teleport_pad(
                exit_x, exit_y, exit_z,
                sec_idx, sec_idx + 1, next_entry
            )
            all_parts.extend(exit_parts)
        else:
            # Last section: victory pad
            victory_parts = _generate_victory_exit_pad(exit_x, exit_y, exit_z, sec_idx)
            all_parts.extend(victory_parts)

        # Store section metadata
        sections.append({
            "section_index": sec_idx,
            "theme": theme_key,
            "theme_name": theme["name"],
            "start_pos": [round(section_center_x, 1), round(section_ground_y, 1),
                           round(section_base_z, 1)],
            "entry_pos": [round(entry_pos[0], 1), round(entry_pos[1], 1),
                           round(entry_pos[2], 1)],
            "exit_pos": [round(exit_x, 1), round(exit_y, 1), round(exit_z, 1)],
            "stage_range": [section_start_stage, section_end_stage],
            "stages_count": stages_in_section,
            "teleport_to_pos": (
                [round(section_entry_positions[sec_idx + 1][0], 1),
                 round(section_entry_positions[sec_idx + 1][1] + 3, 1),
                 round(section_entry_positions[sec_idx + 1][2], 1)]
                if sec_idx < num_sections - 1 else None
            ),
            "sky_hint": theme["sky_hint"],
        })

    # Build themes_used list (ordered, deduplicated)
    themes_used = list(dict.fromkeys([s["theme"] for s in stages]))

    return {
        "parts": all_parts,
        "stages": stages,
        "sections": sections,
        "themes_used": themes_used,
        "total_stages": global_stage_num,
        "total_parts": len(all_parts),
        "total_sections": num_sections,
        "game_name": game_name,
    }
