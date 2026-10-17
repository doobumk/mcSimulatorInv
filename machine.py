"""생산 장비의 구성 모델. 좌표와 구동 설정을 보관한다."""

from dataclasses import dataclass, field

from equipment import Equipment


@dataclass
class coordinate:
    """3차원 좌표. 단위와 기준점은 사용하는 시설에서 정한다."""

    x: float = 0.0
    y: float = 0.0
    z: float = 0.0


@dataclass
class frame:
    name: str
    coordinate: coordinate = field(default_factory=coordinate)


@dataclass
class motor:
    """각 리스트의 같은 인덱스는 하나의 구동 설정을 나타낸다."""

    name: str
    position: list[float] = field(default_factory=list)
    speed: list[float] = field(default_factory=list)
    acc: list[float] = field(default_factory=list)
    dec: list[float] = field(default_factory=list)
    time: list[float] = field(default_factory=list)

    def add_motion(
        self, position: float, speed: float, acc: float, dec: float, time: float
    ) -> None:
        """구동 설정 한 행을 다섯 리스트에 함께 추가한다."""
        self.position.append(position)
        self.speed.append(speed)
        self.acc.append(acc)
        self.dec.append(dec)
        self.time.append(time)


@dataclass
class cylinder:
    name: str
    speed: list[float] = field(default_factory=list)


class part:
    """Unit에서 사용하는 구동 부품의 생성 담당 클래스."""

    @staticmethod
    def create_motor(name: str) -> motor:
        return motor(name=name)

    @staticmethod
    def create_cylinder(name: str) -> cylinder:
        return cylinder(name=name)


@dataclass
class unit:
    """개별 공정의 좌표와 구동 부품을 보관한다."""

    name: str
    coordinate: coordinate = field(default_factory=coordinate)
    motors: list[motor] = field(default_factory=list)
    cylinders: list[cylinder] = field(default_factory=list)
    kind: str = "process"
    length: float = 0.0
    width: float = 0.0
    height: float = 0.0
    cvBelt: tuple[float, float, float] | None = None
    cvbeltAmt: int = 0

    @property
    def x_start(self):
        return self.coordinate.x - (self.cvBelt[0] if self.cvBelt else self.length) / 2

    @property
    def x_end(self):
        return self.coordinate.x + (self.cvBelt[0] if self.cvBelt else self.length) / 2

    @property
    def belt_top(self):
        return self.coordinate.z + (self.cvBelt[2] if self.cvBelt else self.height) / 2

    @property
    def belt_centers_y(self):
        """전체 폭 안에 벨트를 균등 배치한다. 한 줄이면 중앙 배치."""
        if self.cvBelt is None or self.cvbeltAmt == 0:
            return []
        if self.cvbeltAmt == 1:
            return [self.coordinate.y]
        span = self.width - self.cvBelt[1]
        return [self.coordinate.y - span / 2 + i * span / (self.cvbeltAmt - 1)
                for i in range(self.cvbeltAmt)]

    def add_motor(self, name: str) -> motor:
        component = part.create_motor(name)
        self.motors.append(component)
        return component

    def add_cylinder(self, name: str) -> cylinder:
        component = part.create_cylinder(name)
        self.cylinders.append(component)
        return component


class machine(Equipment):
    """공통 장비 제어 기능과 Frame/Unit 구성을 갖는 생산 장비."""

    def __init__(self, name: str):
        super().__init__(name)
        self.frames: list[frame] = []
        self.units: list[unit] = []

    def add_frame(self, component: frame) -> None:
        self.frames.append(component)

    def add_unit(self, component: unit) -> None:
        self.units.append(component)
