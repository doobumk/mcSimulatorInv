"""제품 모델과 시뮬레이션 시간 기반의 주기적 제품 생성 기능."""

from copy import deepcopy
from dataclasses import dataclass, field
import math

from machine import coordinate


@dataclass
class Product:
    id: int = -1
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    size: tuple[float, float, float] = field(kw_only=True)

    def __post_init__(self):
        if len(self.size) != 3 or any(not math.isfinite(v) or v <= 0 for v in self.size):
            raise ValueError("product size must contain three finite positive dimensions")


@dataclass
class Cell(Product):
    """Cell 표식 클래스. 크기는 데이터시트 또는 호출자가 제공한다."""


class product_input:
    """product는 복제용 원형. input_pos는 배치 선두 제품 중심의 절대 좌표."""

    def __init__(self, input_pos: coordinate, product: Product,
                 cycle: float = 5.0, amount: int = 7):
        self.input_pos = deepcopy(input_pos)
        self.product = deepcopy(product)
        self._elapsed = 0.0
        self.configure(cycle=cycle, amount=amount)

    def configure(self, *, cycle=None, amount=None):
        new_cycle = self.cycle if cycle is None else cycle
        new_amount = self.amount if amount is None else amount
        if not math.isfinite(new_cycle) or new_cycle <= 0:
            raise ValueError("cycle must be finite and positive (seconds)")
        if isinstance(new_amount, bool) or not isinstance(new_amount, int) or new_amount < 1:
            raise ValueError("amount must be a positive integer")
        self.cycle, self.amount = float(new_cycle), new_amount
        self.reset()

    def reset(self):
        self._elapsed = 0.0

    def events(self, seconds: float) -> list[float]:
        """이번 시간 구간 내 생성 시각을 반환한다. 첫 생성은 한 주기 후다."""
        if not math.isfinite(seconds) or seconds <= 0:
            raise ValueError("seconds must be finite and positive")
        total = self._elapsed + seconds
        count = math.floor((total + 1e-10) / self.cycle)
        offsets = [max(0.0, min(seconds, self.cycle * (i + 1) - self._elapsed))
                   for i in range(count)]
        self._elapsed = max(0.0, total - count * self.cycle)
        return offsets

    def create_batch(self, pitch: float) -> list[Product]:
        """원형을 독립 복제하고 X축 음의 방향으로 피치 간격을 둔다."""
        if not math.isfinite(pitch) or pitch <= 0:
            raise ValueError("pitch must be finite and positive")
        products = []
        for i in range(self.amount):
            item = deepcopy(self.product)
            item.id = -1
            item.x = self.input_pos.x - (self.amount - 1 - i) * pitch
            item.y, item.z = self.input_pos.y, self.input_pos.z
            products.append(item)
        return products
