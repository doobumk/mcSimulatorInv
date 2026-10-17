"""Windowed executable entry point with visible startup errors."""

import sys
import traceback


if __name__ == "__main__":
    try:
        from battery_line_3d import main
        main()
    except Exception:
        if '--smoke-test-report' in sys.argv:
            import json
            from pathlib import Path

            report = Path(sys.argv[sys.argv.index('--smoke-test-report') + 1])
            report.write_text(json.dumps({'ok': False, 'error': traceback.format_exc()},
                                        ensure_ascii=False, indent=2), encoding='utf-8')
            sys.exit(1)
        from PySide6.QtWidgets import QApplication, QMessageBox

        app = QApplication.instance() or QApplication(sys.argv)
        dialog = QMessageBox()
        dialog.setWindowTitle("Battery Line Simulator - 실행 오류")
        dialog.setIcon(QMessageBox.Icon.Critical)
        dialog.setText("시뮬레이터를 시작하지 못했습니다. 데이터시트와 프로그램 파일을 확인하세요.")
        dialog.setDetailedText(traceback.format_exc())
        dialog.exec()
        sys.exit(1)
