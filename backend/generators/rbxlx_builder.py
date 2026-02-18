"""RBXLX Builder v2 - Generates complete .rbxlx Roblox place files
Uses correct Roblox XML serialization format per the rbxlx spec.

v2 changes:
- Supports part attributes (MoveAxis, MoveDistance, SpinSpeed, TeleportTo, etc.)
- Adds SurfaceGui+TextLabel for stage signs and welcome signs
- Uses hardcoded obby scripts from obby_scripts.py instead of Claude API
- Supports teleport-based section structure
- Adds CollectionService tags via an ObbySetup bootstrap script
"""
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
import re
import json
import math
import struct
import base64

from backend.config import GAMES_OUTPUT_DIR
from backend.utils.logger import log, LogLevel, EventType
from backend.utils.claude_client import ask_claude_json
from backend.generators.obby_generator import generate_obby, THEMES


# ============================================================
# LOW-LEVEL XML HELPERS (Correct RBXLX format)
# ============================================================

def _next_ref():
    """Generate unique referent IDs."""
    if not hasattr(_next_ref, "counter"):
        _next_ref.counter = 0
    _next_ref.counter += 1
    return f"RBX{_next_ref.counter:08X}"


def _rgb_to_uint8(r, g, b):
    """Convert float RGB (0-1) to packed Color3uint8 integer.
    Format: 0xFF000000 | (R<<16) | (G<<8) | B  where R,G,B are 0-255."""
    ri = max(0, min(255, int(r * 255)))
    gi = max(0, min(255, int(g * 255)))
    bi = max(0, min(255, int(b * 255)))
    return 0xFF000000 | (ri << 16) | (gi << 8) | bi


def _add_prop(props: ET.Element, tag: str, name: str, value):
    """Add a property with correct RBXLX XML format."""
    prop = ET.SubElement(props, tag)
    prop.set("name", name)

    if tag in ("string", "ProtectedString", "Content", "BinaryString"):
        prop.text = str(value) if value else ""
    elif tag == "bool":
        prop.text = str(value).lower()
    elif tag in ("int", "int64"):
        prop.text = str(int(value))
    elif tag in ("float", "double"):
        prop.text = str(float(value))
    elif tag == "token":
        prop.text = str(int(value))
    elif tag == "Color3uint8":
        # Packed uint32: 0xFF000000 | (R<<16) | (G<<8) | B
        if isinstance(value, (list, tuple)):
            prop.text = str(_rgb_to_uint8(value[0], value[1], value[2]))
        else:
            prop.text = str(int(value))
    elif tag == "Color3":
        for ch_name, ch_val in zip(["R", "G", "B"], value):
            el = ET.SubElement(prop, ch_name)
            el.text = str(float(ch_val))
    elif tag == "Vector3":
        for ch_name, ch_val in zip(["X", "Y", "Z"], value):
            el = ET.SubElement(prop, ch_name)
            el.text = str(float(ch_val))
    elif tag == "Vector2":
        for ch_name, ch_val in zip(["X", "Y"], value):
            el = ET.SubElement(prop, ch_name)
            el.text = str(float(ch_val))
    elif tag == "CoordinateFrame":
        keys = ["X", "Y", "Z", "R00", "R01", "R02", "R10", "R11", "R12", "R20", "R21", "R22"]
        defaults = [0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1]
        for i, key in enumerate(keys):
            el = ET.SubElement(prop, key)
            el.text = str(value[i] if i < len(value) else defaults[i])
    elif tag == "UDim2":
        for ch_name, ch_val in zip(["XS", "XO", "YS", "YO"], value):
            el = ET.SubElement(prop, ch_name)
            el.text = str(ch_val)
    elif tag == "Ref":
        prop.text = str(value) if value else "null"
    else:
        prop.text = str(value)
    return prop


def _encode_attributes(attrs: dict) -> str:
    """Encode a dict of attributes to Roblox's binary AttributesSerialize format.

    Binary layout: [u32 entry_count] [entry_1] ... [entry_n]
    Each entry:    [u32 key_len] [key_bytes] [u8 type_id] [value_bytes]

    Type IDs (per rbx-dom spec):
      0x02 = String  (u32 len + bytes)
      0x03 = Bool    (u8: 0x00 or 0x01)
      0x04 = Int32   (i32 LE)
      0x06 = Float64 (f64 LE, 8 bytes) — NOTE: 0x05 is Float32
      0x11 = Vector3 (3x f32 LE, 12 bytes)

    Returns base64-encoded string, or 'AAAAAA==' for empty attrs."""
    if not attrs:
        return "AAAAAA=="  # 4 zero bytes = 0 entries

    buf = bytearray()
    # Number of attributes (4 bytes LE unsigned)
    buf += struct.pack('<I', len(attrs))

    for key, value in attrs.items():
        # Key: length-prefixed UTF-8 string
        key_bytes = key.encode('utf-8')
        buf += struct.pack('<I', len(key_bytes))
        buf += key_bytes

        # Value: type_id byte + type-specific data
        # IMPORTANT: check bool before int (bool is subclass of int in Python)
        if isinstance(value, bool):
            buf += struct.pack('<B', 0x03)  # Bool
            buf += struct.pack('<B', 1 if value else 0)
        elif isinstance(value, int):
            buf += struct.pack('<B', 0x04)  # Int32 (NOT 0x05/Float32!)
            buf += struct.pack('<i', value)  # signed 32-bit LE
        elif isinstance(value, float):
            buf += struct.pack('<B', 0x06)  # Float64/Double (NOT 0x05/Float32!)
            buf += struct.pack('<d', value)  # 8 bytes IEEE-754 double
        elif isinstance(value, str):
            buf += struct.pack('<B', 0x02)  # String
            val_bytes = value.encode('utf-8')
            buf += struct.pack('<I', len(val_bytes))
            buf += val_bytes
        elif isinstance(value, (list, tuple)) and len(value) == 3:
            buf += struct.pack('<B', 0x11)  # Vector3 (0x11, NOT 0x09!)
            buf += struct.pack('<fff', float(value[0]), float(value[1]), float(value[2]))
        else:
            # Fallback: encode as string
            buf += struct.pack('<B', 0x02)
            val_bytes = str(value).encode('utf-8')
            buf += struct.pack('<I', len(val_bytes))
            buf += val_bytes

    return base64.b64encode(bytes(buf)).decode('ascii')


def _encode_tags(tags: list) -> str:
    """Encode CollectionService tags to Roblox's binary Tags format.

    Tags are stored as UTF-8 strings joined by null byte DELIMITERS (0x00).
    NO trailing null after the last tag. This matches the rbx-dom/Rojo spec.

    Example: ["Hello", "from", "Rojo"] -> "Hello\\x00from\\x00Rojo"

    Returns base64-encoded string, or empty string for no tags."""
    if not tags:
        return ""
    # Join with null byte delimiter — NO trailing null
    result = b'\x00'.join(tag.encode('utf-8') for tag in tags)
    return base64.b64encode(result).decode('ascii')


def _create_item(class_name: str, parent: ET.Element, name: str = "") -> ET.Element:
    """Create an RBXLX Item with Properties container."""
    item = ET.SubElement(parent, "Item")
    item.set("class", class_name)
    item.set("referent", _next_ref())
    props = ET.SubElement(item, "Properties")
    if name:
        name_el = ET.SubElement(props, "string")
        name_el.set("name", "Name")
        name_el.text = name
    return item


def _get_props(item: ET.Element) -> ET.Element:
    """Get or create Properties element."""
    props = item.find("Properties")
    if props is None:
        props = ET.SubElement(item, "Properties")
    return props


# ============================================================
# PART / SPAWNLOCATION CREATION
# ============================================================

MATERIAL_MAP = {
    "SmoothPlastic": 256, "Neon": 288, "Glass": 1568, "Wood": 512,
    "Grass": 1280, "Sand": 1536, "Ice": 1264, "Marble": 784,
    "Brick": 128, "Concrete": 1040, "Metal": 1040, "Foil": 1040,
    "DiamondPlate": 1040, "Granite": 832, "Slate": 800,
    "Cobblestone": 880, "Pebble": 1296, "ForceField": 1584,
    "Plastic": 256, "WoodPlanks": 528, "CorrodedMetal": 1040,
    "Fabric": 848,
}


def _build_part(
    parent: ET.Element,
    name: str,
    class_name: str = "Part",
    position=(0, 0, 0),
    size=(4, 1, 2),
    color=(0.64, 0.64, 0.64),
    anchored=True,
    can_collide=True,
    material="SmoothPlastic",
    transparency=0.0,
    shape=1,
    attributes: dict = None,
    tags: list = None,
) -> ET.Element:
    """Build a Part/SpawnLocation with all correct properties."""
    item = _create_item(class_name, parent, name)
    props = _get_props(item)

    _add_prop(props, "bool", "Anchored", anchored)
    _add_prop(props, "token", "BottomSurface", 4)  # Smooth
    _add_prop(props, "token", "TopSurface", 0)  # Smooth

    # CFrame (position + identity rotation)
    cframe = [position[0], position[1], position[2], 1, 0, 0, 0, 1, 0, 0, 0, 1]
    _add_prop(props, "CoordinateFrame", "CFrame", cframe)

    _add_prop(props, "bool", "CanCollide", can_collide)

    # Color as packed uint8
    _add_prop(props, "Color3uint8", "Color3uint8", color)

    _add_prop(props, "bool", "Locked", False)

    # Material
    mat_id = MATERIAL_MAP.get(material, 256) if isinstance(material, str) else int(material)
    _add_prop(props, "token", "Material", mat_id)

    _add_prop(props, "float", "Transparency", transparency)
    _add_prop(props, "token", "shape", shape)  # 1=Block, 2=Sphere, 3=Cylinder

    # Size (lowercase "size" per spec!)
    _add_prop(props, "Vector3", "size", size)

    if class_name == "SpawnLocation":
        _add_prop(props, "bool", "AllowTeamChangeOnTouch", False)
        _add_prop(props, "int", "Duration", 0)
        _add_prop(props, "bool", "Neutral", True)

    # Attributes (for moving platforms, teleport pads, etc.)
    if attributes:
        encoded = _encode_attributes(attributes)
        _add_prop(props, "BinaryString", "AttributesSerialize", encoded)

    # Tags (for CollectionService - kill bricks, checkpoints, etc.)
    if tags:
        encoded = _encode_tags(tags)
        _add_prop(props, "BinaryString", "Tags", encoded)

    return item


def _build_surface_gui(parent_item: ET.Element, text: str, text_color=(1, 1, 1),
                        bg_color=(0, 0, 0), text_size=40, face="Front") -> ET.Element:
    """Add a SurfaceGui with TextLabel to a part."""
    gui = _create_item("SurfaceGui", parent_item, "SurfaceGui")
    gp = _get_props(gui)
    face_map = {"Front": 5, "Back": 2, "Top": 1, "Bottom": 4, "Left": 3, "Right": 0}
    _add_prop(gp, "token", "Face", face_map.get(face, 5))
    _add_prop(gp, "bool", "Active", False)
    _add_prop(gp, "Vector2", "CanvasSize", [400, 200])
    _add_prop(gp, "bool", "ClipsDescendants", True)

    label = _create_item("TextLabel", gui, "Label")
    lp = _get_props(label)
    _add_prop(lp, "UDim2", "Size", [1, 0, 1, 0])
    _add_prop(lp, "UDim2", "Position", [0, 0, 0, 0])
    _add_prop(lp, "string", "Text", text)
    _add_prop(lp, "Color3", "TextColor3", text_color)
    _add_prop(lp, "Color3", "BackgroundColor3", bg_color)
    _add_prop(lp, "float", "BackgroundTransparency", 0.3)
    _add_prop(lp, "float", "TextScaled", 1)  # Use bool but value 1
    _add_prop(lp, "token", "Font", 12)  # GothamBold
    _add_prop(lp, "int", "TextSize", text_size)

    return gui


def _build_script(parent: ET.Element, name: str, script_type: str, source: str) -> ET.Element:
    """Create a Script/LocalScript/ModuleScript."""
    class_map = {
        "ServerScript": "Script",
        "Script": "Script",
        "LocalScript": "LocalScript",
        "ModuleScript": "ModuleScript",
    }
    cls = class_map.get(script_type, "Script")
    item = _create_item(cls, parent, name)
    props = _get_props(item)
    _add_prop(props, "ProtectedString", "Source", source)
    if cls == "Script":
        _add_prop(props, "token", "RunContext", 0)
    return item


# ============================================================
# WORLD GENERATION (Procedural for obbys, Claude for others)
# ============================================================

async def generate_world_parts(plan: dict) -> dict:
    """Generate world geometry. Uses procedural generation for obbys,
    falls back to Claude for other game types."""
    game_id = plan.get("game_id", "unknown")
    game_type = plan.get("game_type", "obby")
    game_name = plan.get("name", "Unknown")

    await log(f"Generating world geometry ({game_type})...", LogLevel.STEP, EventType.GAME_BUILD, game_id=game_id)

    if game_type == "obby":
        await log("Using procedural obby generator v2 (teleport sections + moving obstacles)",
                  LogLevel.INFO, EventType.GAME_BUILD, game_id=game_id)
        obby_data = generate_obby(
            num_stages=30,
            game_name=game_name,
            agent_theme_data=plan.get("agent_theme_data"),
        )
        part_count = obby_data["total_parts"]
        num_sections = obby_data.get("total_sections", len(obby_data.get("sections", [])))
        await log(
            f"Generated {part_count} parts across {obby_data['total_stages']} stages, "
            f"{num_sections} sections, {len(obby_data['themes_used'])} themes",
            LogLevel.SUCCESS, EventType.GAME_BUILD, game_id=game_id
        )
        return obby_data
    else:
        await log("Using Claude for world generation", LogLevel.INFO, EventType.GAME_BUILD, game_id=game_id)
        world_design = plan.get("world_design", {})
        gameplay = plan.get("gameplay", {})
        parts = await ask_claude_json(
            prompt=f"""Generate 3D world geometry for this Roblox {game_type} game: {game_name}.
World design: {json.dumps(world_design, indent=2)}
Gameplay: {json.dumps(gameplay, indent=2)}
Return JSON with "parts" array. Each part needs: name, type, position [x,y,z], size [w,h,d], color [r,g,b] floats 0-1, anchored, can_collide, material, transparency.""",
            system="You are a Roblox world builder. Use bright colors, proper Roblox physics. Ground=Y0.",
            max_tokens=4096,
            temperature=0.6
        )
        part_count = len(parts.get("parts", []))
        await log(f"Generated {part_count} world parts", LogLevel.SUCCESS, EventType.GAME_BUILD, game_id=game_id)
        return parts


def _get_part_attributes(part_info: dict) -> dict:
    """Extract Roblox attributes from part metadata."""
    attrs = {}

    # Moving platform attributes
    if part_info.get("is_moving"):
        attrs["MoveAxis"] = str(part_info.get("move_axis", "x"))
        attrs["MoveDistance"] = float(part_info.get("move_distance", 10))
        attrs["MoveSpeed"] = float(part_info.get("move_speed", 4))

    # Spinning obstacle attributes
    if part_info.get("is_spinning"):
        attrs["SpinSpeed"] = float(part_info.get("spin_speed", 2))
        attrs["SpinAxis"] = str(part_info.get("spin_axis", "y"))

    # Teleport attributes
    if part_info.get("is_teleport") and part_info.get("teleport_to"):
        tp = part_info["teleport_to"]
        attrs["TeleportTo"] = tp  # Vector3

    # Checkpoint attributes
    if part_info.get("is_checkpoint"):
        attrs["Stage"] = int(part_info.get("stage", 1))

    # Stage sign attributes
    if part_info.get("is_stage_sign"):
        attrs["Stage"] = int(part_info.get("stage", 1))
        attrs["ThemeName"] = str(part_info.get("theme_name", ""))

    # Kill brick flag
    if part_info.get("is_kill_brick"):
        attrs["IsKillBrick"] = True

    # Disappearing flag
    if part_info.get("is_disappearing"):
        attrs["IsDisappearing"] = True

    return attrs


def _get_part_tags(part_info: dict) -> list:
    """Get CollectionService tags for a part."""
    tags = []
    if part_info.get("is_kill_brick"):
        tags.append("KillBrick")
    if part_info.get("is_checkpoint"):
        tags.append("Checkpoint")
    if part_info.get("is_teleport") or part_info.get("is_section_exit"):
        tags.append("TeleportPad")
    if part_info.get("is_section_entry"):
        tags.append("SectionEntry")
    if part_info.get("is_moving"):
        tags.append("MovingPlatform")
    if part_info.get("is_spinning"):
        tags.append("SpinningObstacle")
    if part_info.get("is_disappearing"):
        tags.append("DisappearingPlatform")
    if part_info.get("is_victory"):
        tags.append("VictoryPad")
    return tags


# ============================================================
# MAIN BUILD FUNCTION
# ============================================================

async def build_rbxlx(plan: dict, scripts: dict[str, str] = None) -> Path:
    """Build a complete .rbxlx file from a game plan.

    For obby games, scripts come from obby_scripts.py (hardcoded).
    For other types, scripts dict is passed from lua_generator.

    Args:
        plan: Game plan dict
        scripts: Optional dict of {name: code_string}. If None for obbys, uses hardcoded scripts.
    """
    game_id = plan.get("game_id", "unknown")
    game_name = plan.get("name", "ClankerbloxGame")
    game_type = plan.get("game_type", "obby")
    safe_name = re.sub(r'[^\w\s-]', '', game_name).strip().replace(' ', '_')

    await log(f"Building .rbxlx file for: {game_name}", LogLevel.STEP, EventType.GAME_BUILD, game_id=game_id)

    # Reset ref counter
    _next_ref.counter = 0

    # ---- Root ----
    root = ET.Element("roblox")
    root.set("xmlns:xmime", "http://www.w3.org/2005/05/xmlmime")
    root.set("xmlns:xsi", "http://www.w3.org/2001/XMLSchema-instance")
    root.set("xsi:noNamespaceSchemaLocation", "http://www.roblox.com/roblox.xsd")
    root.set("version", "4")

    # ---- Workspace ----
    workspace = _create_item("Workspace", root, "Workspace")
    wp = _get_props(workspace)
    _add_prop(wp, "bool", "FilteringEnabled", True)

    # Camera
    cam = _create_item("Camera", workspace, "Camera")
    cp = _get_props(cam)
    _add_prop(cp, "CoordinateFrame", "CFrame", [0, 20, 30, 1, 0, 0, 0, 1, 0, 0, 0, 1])
    _add_prop(cp, "float", "FieldOfView", 70)

    # ---- Generate World Parts ----
    world_data = await generate_world_parts(plan)
    parts_data = world_data.get("parts", [])

    for part_info in parts_data:
        part_type = part_info.get("type", "Part")
        class_name = "SpawnLocation" if part_type == "SpawnLocation" else "Part"

        pos = part_info.get("position", [0, 0, 0])
        size = part_info.get("size", [4, 1, 4])
        color = part_info.get("color", [0.5, 0.5, 0.5])
        material = part_info.get("material", "SmoothPlastic")
        transparency = part_info.get("transparency", 0)
        anchored = part_info.get("anchored", True)
        can_collide = part_info.get("can_collide", True)
        shape = part_info.get("shape", 1)

        # Get attributes and tags
        attrs = _get_part_attributes(part_info)
        tags = _get_part_tags(part_info)

        part_el = _build_part(
            workspace,
            name=part_info.get("name", "Part"),
            class_name=class_name,
            position=pos,
            size=size,
            color=color,
            anchored=anchored,
            can_collide=can_collide,
            material=material,
            transparency=transparency,
            shape=shape,
            attributes=attrs if attrs else None,
            tags=tags if tags else None,
        )

        # Add SurfaceGui for signs
        if part_info.get("is_stage_sign"):
            stage = part_info.get("stage", "?")
            theme_name = part_info.get("theme_name", "")
            _build_surface_gui(
                part_el,
                text=f"Stage {stage}\n{theme_name}",
                text_color=[1, 1, 0],
                bg_color=[0.05, 0.05, 0.1],
                text_size=48,
                face="Front"
            )
            # Also add to back face
            _build_surface_gui(
                part_el,
                text=f"Stage {stage}\n{theme_name}",
                text_color=[1, 1, 0],
                bg_color=[0.05, 0.05, 0.1],
                text_size=48,
                face="Back"
            )

        elif part_info.get("is_welcome_sign"):
            gname = part_info.get("game_name", game_name)
            _build_surface_gui(
                part_el,
                text=f"{gname}\nCan you beat all stages?",
                text_color=[1, 1, 1],
                bg_color=[0.05, 0, 0.1],
                text_size=56,
                face="Front"
            )

        elif part_info.get("is_section_entry"):
            sec_idx = part_info.get("section_index", 0)
            _build_surface_gui(
                part_el,
                text=f"Section {sec_idx + 1}\nGood Luck!",
                text_color=[0, 1, 0.5],
                bg_color=[0, 0, 0],
                text_size=40,
                face="Front"
            )

    # ---- Lighting ----
    lighting = _create_item("Lighting", root, "Lighting")
    lp = _get_props(lighting)
    _add_prop(lp, "float", "Brightness", 2)
    _add_prop(lp, "float", "EnvironmentDiffuseScale", 1)
    _add_prop(lp, "float", "EnvironmentSpecularScale", 1)
    _add_prop(lp, "Color3", "Ambient", [0.5, 0.5, 0.5])
    _add_prop(lp, "Color3", "OutdoorAmbient", [0.5, 0.5, 0.5])
    _add_prop(lp, "string", "TimeOfDay", "14:00:00")
    _add_prop(lp, "float", "GeographicLatitude", 41.7)

    # Atmosphere
    atm = _create_item("Atmosphere", lighting, "Atmosphere")
    atmp = _get_props(atm)
    _add_prop(atmp, "float", "Density", 0.3)
    _add_prop(atmp, "float", "Offset", 0.25)
    _add_prop(atmp, "Color3", "Color", [0.85, 0.9, 1.0])
    _add_prop(atmp, "Color3", "Decay", [0.9, 0.95, 1.0])

    # Bloom for glow effects
    bloom = _create_item("BloomEffect", lighting, "Bloom")
    bp = _get_props(bloom)
    _add_prop(bp, "float", "Intensity", 0.5)
    _add_prop(bp, "float", "Size", 24)
    _add_prop(bp, "float", "Threshold", 0.8)

    # ColorCorrection for vibrant look
    cc = _create_item("ColorCorrectionEffect", lighting, "ColorCorrection")
    ccp = _get_props(cc)
    _add_prop(ccp, "float", "Brightness", 0.05)
    _add_prop(ccp, "float", "Contrast", 0.1)
    _add_prop(ccp, "float", "Saturation", 0.25)

    # SunRays
    sr = _create_item("SunRaysEffect", lighting, "SunRays")
    srp = _get_props(sr)
    _add_prop(srp, "float", "Intensity", 0.15)
    _add_prop(srp, "float", "Spread", 0.8)

    # ---- ServerScriptService ----
    sss = _create_item("ServerScriptService", root, "ServerScriptService")

    # ---- ReplicatedStorage ----
    rs = _create_item("ReplicatedStorage", root, "ReplicatedStorage")

    # Remote events - these are created by GameManager script at runtime,
    # but we also pre-create them for robustness
    remotes_folder = _create_item("Folder", rs, "Remotes")
    for rname in ["StageUpdated", "PlayerDied", "SectionChanged",
                   "TeleportEffect", "CheckpointReached", "VictoryReached",
                   "UpdateStats", "PurchaseItem", "NotifyPlayer"]:
        _create_item("RemoteEvent", remotes_folder, rname)

    # Remote functions
    funcs_folder = _create_item("Folder", rs, "RemoteFunctions")
    for fname in ["GetPlayerData", "GetShopItems", "GetLeaderboard"]:
        _create_item("RemoteFunction", funcs_folder, fname)

    # ---- StarterPlayer ----
    starter_player = _create_item("StarterPlayer", root, "StarterPlayer")

    # Set WalkSpeed default to 16 (sprint will boost to 24)
    sp_props = _get_props(starter_player)
    _add_prop(sp_props, "float", "CharacterWalkSpeed", 16)
    _add_prop(sp_props, "float", "CharacterJumpPower", 50)

    starter_scripts = _create_item("StarterPlayerScripts", starter_player, "StarterPlayerScripts")
    starter_character = _create_item("StarterCharacterScripts", starter_player, "StarterCharacterScripts")

    # ---- StarterGui ----
    starter_gui = _create_item("StarterGui", root, "StarterGui")
    sgp = _get_props(starter_gui)
    _add_prop(sgp, "bool", "ResetOnSpawn", False)

    # ---- SoundService ----
    _create_item("SoundService", root, "SoundService")

    # ---- Teams ----
    _create_item("Teams", root, "Teams")

    # ---- Add Scripts ----
    location_map = {
        "ServerScriptService": sss,
        "ReplicatedStorage": rs,
        "StarterPlayerScripts": starter_scripts,
        "StarterCharacterScripts": starter_character,
        "StarterGui": starter_gui,
        "Workspace": workspace,
    }

    if game_type == "obby":
        # Use hardcoded obby scripts
        from backend.generators.obby_scripts import get_obby_scripts

        # Build section data for scripts
        sections_data = []
        for sec in world_data.get("sections", []):
            sr = sec.get("stage_range", [1, 5])
            sections_data.append({
                "name": sec.get("theme_name", "Unknown"),
                "theme": sec.get("theme", "lobby"),
                "start_stage": sr[0] if isinstance(sr, list) else 1,
                "end_stage": sr[1] if isinstance(sr, list) else 5,
            })

        stages_data = world_data.get("stages", [])
        script_bundle = get_obby_scripts(game_name, sections_data, stages_data)

        scripts_written = {}
        for script_name, script_info in script_bundle.items():
            code = script_info["code"]
            script_type = script_info["type"]
            location = script_info["location"]
            parent_el = location_map.get(location, sss)

            _build_script(parent_el, script_name, script_type, code)
            scripts_written[script_name] = code

        await log(
            f"Added {len(scripts_written)} hardcoded obby scripts",
            LogLevel.INFO, EventType.GAME_BUILD, game_id=game_id,
            data={"scripts": list(scripts_written.keys())}
        )

    elif scripts:
        # Use provided scripts (from Claude or other generator)
        scripts_written = scripts
        script_locations = {}
        for s in plan.get("scripts_needed", []):
            script_locations[s["name"]] = s.get("location", "ServerScriptService")

        core_locations = {
            "GameManager": "ServerScriptService",
            "DataManager": "ServerScriptService",
            "ClientUI": "StarterPlayerScripts",
            "ShopManager": "ServerScriptService",
        }
        script_locations.update(core_locations)

        for script_name, script_code in scripts.items():
            loc = script_locations.get(script_name, "ServerScriptService")
            parent_el = location_map.get(loc, sss)

            script_type = "Script"
            for s in plan.get("scripts_needed", []):
                if s["name"] == script_name:
                    script_type = s.get("type", "ServerScript")
                    break

            name_lower = script_name.lower()
            if any(kw in name_lower for kw in ["gui", "hud", "client", "local", "ui", "sprint"]):
                script_type = "LocalScript"
                if loc == "ServerScriptService":
                    parent_el = starter_scripts
            elif "module" in name_lower or script_name == "DataManager":
                script_type = "ModuleScript"

            _build_script(parent_el, script_name, script_type, script_code)
    else:
        scripts_written = {}

    # ---- Write File ----
    output_dir = GAMES_OUTPUT_DIR / safe_name
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"{safe_name}.rbxlx"

    xml_str = ET.tostring(root, encoding='unicode', xml_declaration=False)
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('<?xml version="1.0" encoding="utf-8"?>\n')
        f.write(xml_str)

    # Save metadata
    meta_file = output_dir / "game_info.json"
    meta = {
        "game_id": game_id,
        "name": game_name,
        "game_type": game_type,
        "roblox_title": plan.get("roblox_title", game_name),
        "roblox_description": plan.get("roblox_description", ""),
        "tagline": plan.get("tagline", ""),
        "keywords": plan.get("seo_keywords", []),
        "thumbnail_description": plan.get("thumbnail_description", ""),
        "monetization": plan.get("monetization", {}),
        "scripts": list(scripts_written.keys()) if isinstance(scripts_written, dict) else [],
        "parts_count": len(parts_data),
        "created_at": datetime.now().isoformat(),
        "rbxlx_file": str(output_file),
        "stages": world_data.get("stages", []),
        "sections": world_data.get("sections", []),
        "themes_used": world_data.get("themes_used", []),
        "total_stages": world_data.get("total_stages", 0),
        "total_sections": world_data.get("total_sections", 0),
    }
    with open(meta_file, 'w') as f:
        json.dump(meta, f, indent=2)

    # Save individual scripts
    scripts_dir = output_dir / "scripts"
    scripts_dir.mkdir(exist_ok=True)
    if isinstance(scripts_written, dict):
        for sname, scode in scripts_written.items():
            with open(scripts_dir / f"{sname}.lua", 'w', encoding='utf-8') as f:
                f.write(scode)

    file_size_kb = output_file.stat().st_size // 1024
    await log(
        f"Built .rbxlx file: {output_file} ({file_size_kb} KB, {len(parts_data)} parts, "
        f"{len(scripts_written) if isinstance(scripts_written, dict) else 0} scripts)",
        LogLevel.SUCCESS, EventType.GAME_BUILD, game_id=game_id,
        data={"file": str(output_file), "size_kb": file_size_kb}
    )

    return output_file
