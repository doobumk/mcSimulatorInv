"""CSV configuration for line frames and units. All dimensions are in mm."""

import csv
from dataclasses import dataclass
import math
from pathlib import Path

from machine import coordinate, frame, unit


@dataclass
class BatteryFrame(frame):
    """Frame coordinate is its XY center at floor level; height is deck top."""

    length: float = 4970
    width: float = 1860
    height: float = 930

    @property
    def x_start(self):
        return self.coordinate.x - self.length / 2

    @property
    def x_end(self):
        return self.coordinate.x + self.length / 2


@dataclass
class LineUnit(unit):
    """Unit coordinate is its geometry center; kind is conveyor or process."""

    kind: str = "process"
    length: float = 100
    width: float = 100
    height: float = 100


DEFAULT_DATASHEET = Path(__file__).resolve().parent / "datasheets" / "battery_line.csv"
COLUMNS = ("type", "name", "x", "y", "z", "length", "width", "height")


def load_datasheet(path: str | Path):
    """Build objects atomically. Report invalid data with file and row number."""
    path = Path(path)
    frames: list[BatteryFrame] = []
    units: list[LineUnit] = []
    names = set()
    with path.open(encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        if reader.fieldnames != list(COLUMNS):
            raise ValueError(f"{path}: header must be {','.join(COLUMNS)}")
        for row in reader:
            try:
                if None in row or any(value is None for value in row.values()):
                    raise ValueError("incorrect number of columns")
                kind, name = row["type"].strip(), row["name"].strip()
                if kind not in ("frame", "conveyor", "process"):
                    raise ValueError(f"unknown type: {kind}")
                if not name or name in names:
                    raise ValueError("name must be nonempty and unique")
                values = {key: float(row[key]) for key in COLUMNS[2:]}
                if not all(math.isfinite(value) for value in values.values()):
                    raise ValueError("all numbers must be finite")
                if any(values[key] <= 0 for key in ("length", "width", "height")):
                    raise ValueError("dimensions must be positive")
                if kind == "frame" and (values["length"] <= 240 or values["width"] <= 240 or values["height"] <= 365):
                    raise ValueError("frame requires length/width > 240 and height > 365")
                if kind == "conveyor" and values["width"] < 60:
                    raise ValueError("conveyor width must be at least 60 (two 30 mm belts)")
                position = coordinate(*(values[key] for key in ("x", "y", "z")))
                dimensions = {key: values[key] for key in ("length", "width", "height")}
                if kind == "frame":
                    frames.append(BatteryFrame(name=name, coordinate=position, **dimensions))
                else:
                    units.append(LineUnit(name=name, coordinate=position, kind=kind, **dimensions))
                names.add(name)
            except (ValueError, TypeError) as exc:
                raise ValueError(f"{path}:{reader.line_num}: {exc}") from exc
    if not frames:
        raise ValueError(f"{path}: at least one frame is required")
    if sum(component.kind == "conveyor" for component in units) != 1:
        raise ValueError(f"{path}: exactly one continuous conveyor is required")
    return frames, units
