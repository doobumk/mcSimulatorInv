# 생산 시설 장비 시뮬레이터

## 데이터시트에서 프레임과 유닛 생성

`BatteryLine`은 `machine`을 상속합니다. 기존 `FRAME_SIZES` 튜플 대신
`frame`을 상속한 `BatteryFrame` 객체를 `line.frames`에 보관합니다.
`unit`을 상속한 `LineUnit` 객체는 `line.units`에 보관합니다.
클래스와 CSV 로더는 `line_datasheet.py`에 있습니다.

기본 설정 파일은 `datasheets/battery_line.csv`이며, 시작할 때 읽습니다.
Excel 또는 텍스트 편집기로 수정하고 **UTF-8 CSV**로 저장한 뒤 앱을 다시 실행하세요.
코드에서 치수나 프레임 개수를 수정할 필요가 없습니다.

```powershell
.\.venv\Scripts\python.exe battery_line_3d.py --datasheet datasheets/battery_line.csv
```

```python
from battery_line import BatteryLine

line = BatteryLine("datasheets/battery_line.csv")
print(line.frames[0].name, line.frames[0].length)
print(line.units[0].coordinate)
```

CSV 열 순서는 `type,name,x,y,z,length,width,height`입니다. 모든 수치는 mm입니다.

| 열 | 의미 |
| --- | --- |
| type | `frame`: 프레임, `conveyor`: 트윈 벨트, `process`: 일반 공정 유닛 |
| name | 구성 요소의 고유 이름 |
| x, y, z | 프레임은 바닥 기준 XY 중심 좌표, 유닛은 형상 중심 좌표 |
| length, width, height | X 길이, Y 폭, Z 높이. 프레임 높이는 바닥 기준에서 데크 상면까지 |

예를 들어 다음 행을 추가하면 공정 유닛 객체와 화면의 박스를 생성합니다.

```csv
process,Inspection,2000,650,1100,500,400,300
```

프레임은 1개 이상, `conveyor`는 1개여야 합니다. 공정 유닛은 여러 개 추가할 수
있습니다. 현재 이송 모델은 X축을 따라 이동하는 단일 연속 경로입니다.
컨베이어 폭은 벨트 두 줄의 바깥쪽 전체 폭이며 각 벨트 폭은 30 mm입니다.
이송 시작·끝과 셀 높이/Y 위치는 컨베이어 데이터에서 계산됩니다.
프레임 배치와 컨베이어 배치는 각각 절대 좌표이므로 크기 변경 시 관련 행의
좌표도 함께 조정해야 합니다. 자동 배치 및 공정 유닛의 개별 동작은 포함하지 않습니다.
잘못된 열, 중복 이름, 유효하지 않은 숫자는 로딩 오류로 표시됩니다.

## 배터리 셀 3D 이송 라인

첨부 HTML의 Three.js 장면을 Python의 PyVista/VTK 및 Qt API로 구현했습니다.
Python 3.10 이상에서 다음 명령으로 별도 데스크톱 화면을 실행합니다.

```powershell
python -m pip install -r requirements-3d.txt
python battery_line_3d.py
```

`battery_line_3d.py`는 3개 프레임, 데크, 레벨링 풋, 2줄 벨트와 눕힌 셀을
mm 단위로 생성합니다. 속도, 배치 피치, 7셀 투입 START, STOP, 초기화,
Top/Front/ISO 시점 전환을 제공합니다. 좌클릭은 회전, Shift+좌클릭 또는
가운데 버튼은 이동, 휠은 확대/축소입니다. 원본과 마우스 조작 방식 및
렌더링 재질/조명 표현은 다릅니다. 바닥과 풋은 Z축 기준으로 배치했습니다.

START는 7셀을 추가하고 이송을 재개합니다. STOP은 셀을 유지한 채 정지합니다.
초기 화면은 셀이 없는 정지 상태입니다. 피치는 셀 폭인 123 mm 이상이며,
연속 투입 시 앞 배치와 겹치지 않도록 다음 배치를 뒤로 배치합니다.

`battery_line.py`의 API는 화면 라이브러리 없이도 사용할 수 있습니다.

```python
from battery_line import BatteryLine

line = BatteryLine()
line.configure(speed=300, pitch=180)
line.inject_batch()
line.step(1.0)  # 가상 시간 1초만큼 300 mm 이동
line.pause()
print(line.get_status())
print([(cell.id, cell.x) for cell in line.cells])
```

모델 테스트: `python -m unittest test_battery_line -v`.
이 구현은 로컬 Python API 및 데스크톱 화면이며 HTTP 서버는 포함하지 않습니다.

Python 3.10 이상을 사용합니다. `python main.py`로 기본 동작 예제를 실행합니다.

## 공통 기능

`Equipment`는 장비 이름, 상태, 운전 누적 시간, 오류 메시지를 관리합니다.

| 기능 | 메서드 | 상태 변화 |
| --- | --- | --- |
| 전원 켜기 | `power_on()` | OFF → IDLE |
| 운전 시작 | `start()` | IDLE → RUNNING |
| 운전 정지 | `stop()` | RUNNING → IDLE |
| 오류 발생 | `raise_error(message)` | IDLE/RUNNING/ERROR → ERROR |
| 초기화 | `reset()` | 전원이 켜져 있으면 IDLE, 꺼져 있으면 OFF 유지 |
| 전원 끄기 | `power_off()` | 모든 상태 → OFF, 오류 해제 |
| 시간 진행 | `step(seconds)` | RUNNING 상태에서만 장비 동작과 운전 시간 진행 |
| 상태 조회 | `get_status()` | 상태 스냅샷 반환 |

초기화는 운전 누적 시간과 오류를 지웁니다. 전원을 끄는 동작은 운전 누적 시간을 보존합니다.
허용하지 않는 상태에서 제어 명령을 실행하면 `RuntimeError`가 발생합니다.

## 장비별 확장

장비 종류가 정해지면 `Equipment`를 상속하고 `on_step(seconds)`에
생산량, 온도, 이동 거리 등의 변화를 구현합니다. 필요한 설정값과 측정값은
하위 클래스에서 관리하고 `get_status()`를 확장해 반환합니다.

`step()`은 실제로 기다리지 않습니다. 호출자가 전달한 가상 시간만큼 진행하므로
나중에 시설 시뮬레이터가 각 장비에 같은 시간 간격을 전달할 수 있습니다.
하위 클래스의 `on_step()` 역시 실제 대기 없이 동작하도록 구현합니다.

현재 기본 클래스는 장비 수명주기만 구현합니다. 생산 공정, 장비 간 자재 전달,
통신 프로토콜과 화면은 구체적인 요구사항이 정해질 때 별도 계층으로 추가합니다.
