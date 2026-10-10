"""실행: python main.py (Python 3.10 이상)."""

from machine import coordinate, frame, machine, unit


def main() -> None:
    equipment = machine("장비 1")
    equipment.add_frame(frame("메인 프레임", coordinate(0, 0, 0)))
    process_unit = unit("이송 유닛", coordinate(100, 0, 50))
    equipment.add_unit(process_unit)

    axis = process_unit.add_motor("X축 모터")
    axis.add_motion(position=100, speed=50, acc=10, dec=10, time=2)
    actuator = process_unit.add_cylinder("클램프 실린더")
    actuator.speed.extend([20, 30])
    print(process_unit)
    equipment.power_on()
    equipment.start()
    equipment.step(1.0)
    print(equipment.get_status())

    equipment.stop()
    equipment.raise_error("테스트 오류")
    print(equipment.get_status())

    equipment.reset()
    equipment.power_off()
    print(equipment.get_status())


if __name__ == "__main__":
    main()
