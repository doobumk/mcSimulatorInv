"""Battery transfer simulation API. Coordinates and dimensions are in mm (Z up)."""

from dataclasses import dataclass
import math

from equipment import EquipmentState
from machine import machine
from line_datasheet import DEFAULT_DATASHEET, load_datasheet


@dataclass
class Cell:
    id: int
    x: float


class BatteryLine(machine):
    CELL_SIZE = (123, 600, 17.8)
    def __init__(self, datasheet=DEFAULT_DATASHEET):
        super().__init__("Battery Cell Transfer Line")
        self.frames, self.units = load_datasheet(datasheet)
        self.conveyor = next(component for component in self.units if component.kind == "conveyor")
        self.cells: list[Cell] = []
        self.speed = 300.0
        self.pitch = 180.0
        self._next_id = 0
        self.power_on()

    @property
    def LINE_START(self):
        return self.conveyor.coordinate.x - self.conveyor.length / 2

    @property
    def LINE_END(self):
        return self.conveyor.coordinate.x + self.conveyor.length / 2

    @property
    def BELT_TOP(self):
        return self.conveyor.coordinate.z + self.conveyor.height / 2

    def configure(self, *, speed=None, pitch=None):
        new_speed = self.speed if speed is None else float(speed)
        new_pitch = self.pitch if pitch is None else float(pitch)
        if not math.isfinite(new_speed) or not 0 <= new_speed <= 3000:
            raise ValueError("Speed must be between 0 and 3000 mm/s")
        if not math.isfinite(new_pitch) or not 123 <= new_pitch <= 1000:
            raise ValueError("Pitch must be between 123 and 1000 mm")
        self.speed, self.pitch = new_speed, new_pitch

    def inject_batch(self):
        if self.state not in (EquipmentState.IDLE, EquipmentState.RUNNING):
            raise RuntimeError("Power on and clear errors before feeding")
        # Keep successive batches separated even when START is clicked rapidly.
        end = min(self.LINE_START, min((c.x for c in self.cells), default=self.LINE_START + self.pitch) - self.pitch)
        for i in range(7):
            self.cells.append(Cell(self._next_id, end - (6 - i) * self.pitch))
            self._next_id += 1
        if self.state == EquipmentState.IDLE:
            self.start()

    def pause(self):
        if self.state == EquipmentState.RUNNING:
            self.stop()

    def clear(self):
        self.cells.clear()
        self.pause()

    def on_step(self, seconds):
        for cell in self.cells:
            cell.x += self.speed * seconds
        self.cells[:] = [c for c in self.cells if c.x <= self.LINE_END + self.CELL_SIZE[0]]

    def get_status(self):
        return {**super().get_status(), "cell_count": len(self.cells),
                "speed_mm_s": self.speed, "pitch_mm": self.pitch}
