"""Battery transfer simulation API. Coordinates and dimensions are in mm (Z up)."""

import math

from equipment import EquipmentState
from machine import machine
from product_input import Product, Cell
from line_datasheet import DEFAULT_DATASHEET, load_datasheet


class BatteryLine(machine):
    def __init__(self, datasheet=DEFAULT_DATASHEET, inputs=None):
        super().__init__("Battery Cell Transfer Line")
        self.frames, self.units, configured_inputs = load_datasheet(datasheet)
        self.conveyors = [item for item in self.units if item.kind == "conveyor"]
        self.conveyor = self.conveyors[0]
        self.products: list[Product] = []
        self.inputs = list(inputs) if inputs is not None else configured_inputs
        self._feeding = False
        self.speed = 300.0
        self.pitch = max(180.0, self.minimum_pitch)
        self._next_id = 0
        self.power_on()

    @property
    def minimum_pitch(self):
        return max((source.product.size[0] for source in self.inputs), default=1.0)

    @property
    def LINE_START(self):
        return self.conveyor.x_start

    @property
    def LINE_END(self):
        return self.conveyor.x_end

    @property
    def BELT_TOP(self):
        return self.conveyor.belt_top

    @property
    def cells(self):
        """기존 API 호환용 제품 목록 별칭."""
        return self.products

    def start_input(self):
        if self.state == EquipmentState.IDLE:
            self.start()
        elif self.state != EquipmentState.RUNNING:
            raise RuntimeError("Power on and clear errors before feeding")
        self._feeding = True

    def _emit(self, source):
        for item in source.create_batch(self.pitch):
            item.id = self._next_id
            self._next_id += 1
            self.products.append(item)

    def configure(self, *, speed=None, pitch=None):
        new_speed = self.speed if speed is None else float(speed)
        new_pitch = self.pitch if pitch is None else float(pitch)
        if not math.isfinite(new_speed) or not 0 <= new_speed <= 3000:
            raise ValueError("Speed must be between 0 and 3000 mm/s")
        if not math.isfinite(new_pitch) or not self.minimum_pitch <= new_pitch <= max(1000, self.minimum_pitch):
            raise ValueError(f"Pitch must be between {self.minimum_pitch:g} and {max(1000, self.minimum_pitch):g} mm")
        self.speed, self.pitch = new_speed, new_pitch

    def inject_batch(self):
        if self.state not in (EquipmentState.IDLE, EquipmentState.RUNNING):
            raise RuntimeError("Power on and clear errors before feeding")
        for source in self.inputs:
            self._emit(source)
        if self.state == EquipmentState.IDLE:
            self.start()

    def pause(self):
        if self.state == EquipmentState.RUNNING:
            self.stop()

    def clear(self):
        self.cells.clear()
        self.pause()
        self._feeding = False
        for source in self.inputs:
            source.reset()

    def reset(self):
        super().reset()
        self._feeding = False
        for source in self.inputs:
            source.reset()

    def power_off(self):
        super().power_off()
        self._feeding = False
        for source in self.inputs:
            source.reset()

    def _move(self, seconds):
        for item in self.products:
            item.x += self.speed * seconds
        self.products[:] = [p for p in self.products if p.x <= self.LINE_END + p.size[0]]

    def on_step(self, seconds):
        events = []
        if self._feeding:
            for index, source in enumerate(self.inputs):
                events.extend((round(offset, 10), index) for offset in source.events(seconds))
        previous = 0.0
        for offset, index in sorted(events):
            offset = min(seconds, offset)
            self._move(offset - previous)
            self._emit(self.inputs[index])
            previous = offset
        self._move(seconds - previous)

    def get_status(self):
        return {**super().get_status(), "cell_count": len(self.cells),
                "speed_mm_s": self.speed, "pitch_mm": self.pitch}
