"""Excel에서 편집 가능한 단일 CSV로 장비, 제품, 투입기를 구성한다."""

import csv
from dataclasses import dataclass
import math
from pathlib import Path
import sys

from machine import coordinate, frame, unit
from product_input import Product, Cell, product_input


@dataclass
class BatteryFrame(frame):
    length: float = 4970
    width: float = 1860
    height: float = 930

    @property
    def x_start(self):
        return self.coordinate.x - self.length / 2

    @property
    def x_end(self):
        return self.coordinate.x + self.length / 2


LineUnit = unit  # 이전 import 이름의 호환 별칭
APP_DIRECTORY = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
DEFAULT_DATASHEET = APP_DIRECTORY / "datasheets" / "battery_line.csv"
COLUMNS = ("type", "name", "x", "y", "z", "length", "width", "height",
           "cvBeltLength", "cvBeltWidth", "cvBeltHeight", "cvbeltAmt",
           "product", "cycle", "amount")


def load_datasheet(path: str | Path):
    """반환: frames, units, inputs. 오류에 CSV 행 번호를 포함한다."""
    path = Path(path)
    frames, units, inputs = [], [], []
    products, pending, names = {}, [], set()
    with path.open(encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        if reader.fieldnames != list(COLUMNS):
            raise ValueError(f"{path}: header must be {','.join(COLUMNS)}")
        for row in reader:
            try:
                if None in row or any(v is None for v in row.values()):
                    raise ValueError("incorrect number of columns")
                row = {k: v.strip() for k, v in row.items()}
                kind, name = row["type"], row["name"]
                if kind not in ("frame", "conveyor", "process", "product", "product_input"):
                    raise ValueError(f"unknown type: {kind}")
                if not name or name in names:
                    raise ValueError("name must be nonempty and unique")

                def number(key, positive=False):
                    value = float(row[key])
                    if not math.isfinite(value):
                        raise ValueError(f"{key} must be finite")
                    if positive and value <= 0:
                        raise ValueError(f"{key} must be positive")
                    return value

                def integer(key):
                    value = number(key, positive=True)
                    if not value.is_integer():
                        raise ValueError(f"{key} must be a positive integer")
                    return int(value)

                position = coordinate(*(number(k) for k in ("x", "y", "z")))
                if kind == "product_input":
                    pending.append((reader.line_num, name, position, row["product"],
                                    number("cycle", True), integer("amount")))
                else:
                    dimensions = {k: number(k, True) for k in ("length", "width", "height")}
                    if kind == "product":
                        if row["product"] not in ("Cell", "Product"):
                            raise ValueError("product class must be Cell or Product")
                        cls = Cell if row["product"] == "Cell" else Product
                        products[name] = cls(x=position.x, y=position.y, z=position.z,
                                             size=tuple(dimensions.values()))
                    elif kind == "frame":
                        if dimensions["length"] <= 240 or dimensions["width"] <= 240 or dimensions["height"] <= 365:
                            raise ValueError("frame requires length/width > 240 and height > 365")
                        frames.append(BatteryFrame(name=name, coordinate=position, **dimensions))
                    else:
                        component = unit(name=name, coordinate=position, kind=kind, **dimensions)
                        if kind == "conveyor":
                            component.cvBelt = tuple(number(k, True) for k in
                                ("cvBeltLength", "cvBeltWidth", "cvBeltHeight"))
                            component.cvbeltAmt = integer("cvbeltAmt")
                            if component.cvBelt[1] * component.cvbeltAmt > component.width:
                                raise ValueError("belt widths exceed conveyor width")
                        units.append(component)
                names.add(name)
            except (ValueError, TypeError) as exc:
                raise ValueError(f"{path}:{reader.line_num}: {exc}") from exc
    if not frames:
        raise ValueError(f"{path}: at least one frame is required")
    if sum(u.kind == "conveyor" for u in units) != 1:
        raise ValueError(f"{path}: exactly one continuous conveyor is required")
    for line_number, name, position, product_name, cycle, amount in pending:
        if product_name not in products:
            raise ValueError(f"{path}:{line_number}: unknown product: {product_name}")
        source = product_input(position, products[product_name], cycle, amount)
        source.name = name
        inputs.append(source)
    if not inputs:
        raise ValueError(f"{path}: at least one product_input is required")
    return frames, units, inputs
