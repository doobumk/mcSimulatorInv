"""Build a portable Windows folder and ZIP using the current Python environment."""

from pathlib import Path
import shutil
import subprocess
import sys


def main():
    root = Path(__file__).resolve().parent
    subprocess.run([sys.executable, '-m', 'PyInstaller', '--noconfirm',
                    str(root / 'BatteryLineSimulator.spec')], cwd=root, check=True)
    output = root / 'dist' / 'BatteryLineSimulator'
    (output / 'datasheets').mkdir(exist_ok=True)
    shutil.copy2(root / 'datasheets' / 'battery_line.csv', output / 'datasheets' / 'battery_line.csv')
    (output / '사용방법.txt').write_text(
        'Battery Line Simulator (Windows 64-bit)\n\n'
        '1. ZIP을 모두 압축 해제하세요.\n'
        '2. BatteryLineSimulator.exe를 더블클릭하세요. Python 설치는 필요하지 않습니다.\n'
        '3. 7셀 투입 START 버튼으로 이송을 시작하세요.\n\n'
        '설정: datasheets/battery_line.csv를 UTF-8 CSV로 수정하고 앱을 다시 실행하세요.\n'
        '배포: exe, _internal 폴더, datasheets 폴더를 함께 복사하세요.\n'
        '좌클릭: 회전 / Shift+좌클릭 또는 가운데 버튼: 이동 / 휠: 확대·축소\n',
        encoding='utf-8-sig',
    )
    archive = shutil.make_archive(str(root / 'dist' / 'BatteryLineSimulator-Windows-x64'),
                                  'zip', root_dir=root / 'dist', base_dir=output.name)
    print(f'Executable: {output / "BatteryLineSimulator.exe"}')
    print(f'ZIP: {archive}')


if __name__ == '__main__':
    main()
