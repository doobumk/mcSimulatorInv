"""장비 종류에 관계없이 사용하는 시뮬레이터 기본 클래스."""

import math
from enum import Enum


class EquipmentState(str, Enum):
    OFF = "off"
    IDLE = "idle"
    RUNNING = "running"
    ERROR = "error"


class Equipment:
    """전원, 운전, 오류와 가상 시간을 관리한다.

    장비별 동작은 이 클래스를 상속하고 on_step()에서 구현한다.
    step()의 시간은 실제 대기 시간이 아닌 시뮬레이션 시간이다.
    """

    def __init__(self, name: str):
        if not name.strip():
            raise ValueError("장비 이름이 필요합니다.")
        self.name = name
        self._state = EquipmentState.OFF
        self._error_message: str | None = None
        self._elapsed_seconds = 0.0

    @property
    def state(self) -> EquipmentState:
        return self._state

    def power_on(self) -> None:
        self._require_state(EquipmentState.OFF)
        self._state = EquipmentState.IDLE

    def power_off(self) -> None:
        self._state = EquipmentState.OFF
        self._error_message = None

    def start(self) -> None:
        self._require_state(EquipmentState.IDLE)
        self._state = EquipmentState.RUNNING

    def stop(self) -> None:
        self._require_state(EquipmentState.RUNNING)
        self._state = EquipmentState.IDLE

    def raise_error(self, message: str) -> None:
        if self.state == EquipmentState.OFF:
            raise RuntimeError("전원이 꺼진 장비에 오류를 발생시킬 수 없습니다.")
        if not message.strip():
            raise ValueError("오류 메시지가 필요합니다.")
        self._error_message = message
        self._state = EquipmentState.ERROR

    def reset(self) -> None:
        """오류를 해제하고 운전 누적 시간을 초기화한다. 전원은 유지한다."""
        self._error_message = None
        self._elapsed_seconds = 0.0
        if self.state != EquipmentState.OFF:
            self._state = EquipmentState.IDLE

    def step(self, seconds: float) -> None:
        """운전 중일 때만 장비 동작과 누적 시간을 진행한다."""
        if not math.isfinite(seconds) or seconds <= 0:
            raise ValueError("시간은 유한한 양수여야 합니다.")
        if self.state == EquipmentState.RUNNING:
            self.on_step(seconds)
            self._elapsed_seconds += seconds

    def on_step(self, seconds: float) -> None:
        """하위 클래스에서 시간에 따른 장비 동작을 구현하는 확장 지점."""

    def get_status(self) -> dict[str, str | float | None]:
        return {
            "name": self.name,
            "state": self.state.value,
            "elapsed_seconds": self._elapsed_seconds,
            "error_message": self._error_message,
        }

    def _require_state(self, expected: EquipmentState) -> None:
        if self.state != expected:
            raise RuntimeError(
                f"현재 상태는 {self.state.value}입니다. "
                f"{expected.value} 상태에서만 실행할 수 있습니다."
            )
