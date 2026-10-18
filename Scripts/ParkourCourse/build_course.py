"""Build the parkour course map from course_layout.json through Unreal MCP.

The UnrealEngineLab editor must run the MCP server and have register_toolset.py executed once.
Rebuilding removes only the actors this script placed (tag ParkourCourse), then saves the map.
"""
from pathlib import Path
import json
import math

from mcp_client import Client, lab

LAYOUT = Path(__file__).with_name("course_layout.json")
LEVEL_BLOCK = "/Game/Levels/LevelPrototyping/LevelBlock.LevelBlock_C"
TRAVERSABLE_BLOCK = "/Game/Levels/LevelPrototyping/LevelBlock_Traversable.LevelBlock_Traversable_C"
LEVEL_VISUALS = "/Game/Levels/LevelPrototyping/LevelVisuals.LevelVisuals_C"
CHECKPOINT = "/Script/UnrealEngineLab.ParkourCheckpoint"
PLAYER_START = "/Script/Engine.PlayerStart"
UNIT = 100.0  # LevelBlock is a 100 cm cube with its pivot on the minimum corner


def floor(piece, width, thickness):
    length = piece["x1"] - piece["x0"]
    return {"class": LEVEL_BLOCK, "location": [piece["x0"], -width / 2, piece["top"] - thickness],
            "scale": [length / UNIT, width / UNIT, thickness / UNIT]}


def ramp(piece, width, thickness):
    """A slab tilted around Y. Its top surface starts at (x0, top0) and climbs (or drops) at `pitch` degrees."""
    pitch = math.radians(piece["pitch"])
    # Rotating about the pivot moves the top-front edge (0, 0, T) to (-T sin p, T cos p); shift the pivot back.
    location = [piece["x0"] + thickness * math.sin(pitch), -width / 2, piece["top0"] - thickness * math.cos(pitch)]
    return {"class": LEVEL_BLOCK, "location": location, "rotation": [0.0, piece["pitch"], 0.0],
            "scale": [piece["length"] / UNIT, width / UNIT, thickness / UNIT]}


def cross_slope(piece, width, thickness):
    """A slab tilted around X, so the left foot is higher than the right. The centre line stays at height 0."""
    roll = math.radians(piece["roll"])
    half = width / 2
    # A positive roll tips local +Y down: local (u, v, T) lands at y = py + v cos r + T sin r, z = pz - v sin r + T cos r.
    # Put the middle of the top surface (v = half) at y = 0, z = 0.
    location = [piece["x0"], -half * math.cos(roll) - thickness * math.sin(roll), half * math.sin(roll) - thickness * math.cos(roll)]
    return {"class": LEVEL_BLOCK, "location": location, "rotation": [piece["roll"], 0.0, 0.0],
            "scale": [piece["length"] / UNIT, width / UNIT, thickness / UNIT]}


def block(piece, width):
    return {"class": TRAVERSABLE_BLOCK if piece.get("traversable") else LEVEL_BLOCK,
            "location": [piece["x0"], -width / 2, piece.get("base", 0)],
            "scale": [piece["depth"] / UNIT, width / UNIT, piece["height"] / UNIT]}


def gate(piece, width):
    return {"class": CHECKPOINT, "location": [piece["x"], 0, piece["top"]],
            "properties": {"type": {"enum": "ParkourCheckpointType", "value": piece["type"]}, "order": piece["order"],
                           "gate_extent": [40, width / 2, 200]}}


def build(client, layout):
    width, thickness = layout["width"], layout["thickness"]
    lab(client, "open_course_map", {"path": layout["map"]})
    print(lab(client, "clear_course"))
    for piece in layout["pieces"]:
        kind = piece["kind"]
        if kind == "floor":
            spec = floor(piece, width, thickness)
        elif kind == "ramp":
            spec = ramp(piece, width, thickness)
        elif kind == "cross_slope":
            spec = cross_slope(piece, width, thickness)
        elif kind == "block":
            spec = block(piece, width)
        elif kind == "gate":
            spec = gate(piece, width)
        elif kind == "player_start":
            spec = {"class": PLAYER_START, "location": [piece["x"], 0, piece["top"] + 100]}
        elif kind == "visuals":
            spec = {"class": LEVEL_VISUALS, "location": [0, 0, 0]}
        else:
            raise ValueError(kind)
        spec.update({"label": piece["label"], "folder": "ParkourCourse"})
        result = lab(client, "place_actor", spec)
        print(f"{piece['label']:<20} {[round(v) for v in result['location']]} {result.get('spline_lengths') or ''}")
    lab(client, "set_game_mode", {"class": layout["game_mode"]})
    print(lab(client, "save_course_map"))


if __name__ == "__main__":
    build(Client(), json.loads(LAYOUT.read_text(encoding="utf-8")))
