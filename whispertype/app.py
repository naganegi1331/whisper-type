"""WhisperType アプリケーションエントリポイント。

処理フロー（要件 8 章）:
  起動 → システムトレイへ常駐 → ホットキー押下で音声入力開始
  → リアルタイム認識・カーソル位置へ入力 → ホットキー押下で終了
"""

from __future__ import annotations

import logging
import signal
import sys

from PySide6.QtWidgets import QApplication, QMessageBox, QSystemTrayIcon

from . import __app_name__, autostart
from .config import AppConfig
from .controller import AppController
from .gui.main_window import MainWindow
from .gui.tray import TrayIcon
from .hotkey import HotkeyManager

logger = logging.getLogger(__name__)


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s: %(message)s",
    )

    app = QApplication(sys.argv)
    app.setApplicationName(__app_name__)
    app.setQuitOnLastWindowClosed(False)  # ウィンドウを閉じても常駐を続ける

    config = AppConfig.load()

    # コントローラ（コールバックは後で GUI のシグナルへ接続する）
    controller = AppController(config)
    window = MainWindow(controller, config)
    tray = TrayIcon(
        window=window,
        on_toggle=controller.toggle,
        on_quit=lambda: _quit(app, controller, hotkey_manager),
        parent=app,
    )

    # ワーカースレッド → Qt シグナル（GUI スレッド）へのブリッジ
    controller.set_callbacks(
        on_state=window.state_changed.emit,
        on_text=window.text_changed.emit,
        on_error=window.error_occurred.emit,
    )
    window.state_changed.connect(tray.show_state)

    # グローバルホットキー（要件 4.2）
    hotkey_manager: HotkeyManager | None = None
    try:
        hotkey_manager = HotkeyManager(config.hotkey, controller.toggle)
    except Exception as exc:
        logger.exception("ホットキーを登録できませんでした")
        QMessageBox.warning(
            None,
            __app_name__,
            f"ホットキー「{config.hotkey}」を登録できませんでした:\n{exc}\n\n"
            "設定画面からホットキーを変更してください。",
        )

    def rebind_hotkey(hotkey: str) -> bool:
        nonlocal hotkey_manager
        try:
            if hotkey_manager is None:
                hotkey_manager = HotkeyManager(hotkey, controller.toggle)
            else:
                hotkey_manager.rebind(hotkey)
            return True
        except Exception as exc:
            QMessageBox.warning(
                window,
                __app_name__,
                f"ホットキー「{hotkey}」を登録できませんでした:\n{exc}",
            )
            return False

    window.on_hotkey_changed = rebind_hotkey

    # 自動起動設定を OS 側と同期（要件 4.1）
    if autostart.is_supported():
        try:
            autostart.set_enabled(config.autostart)
        except OSError:
            logger.warning("自動起動設定を反映できませんでした", exc_info=True)

    # トレイ常駐（トレイが使えない環境ではウィンドウを表示）
    if QSystemTrayIcon.isSystemTrayAvailable():
        tray.show()
        if not config.start_minimized:
            window.show()
    else:
        window.show()

    signal.signal(signal.SIGINT, lambda *_: _quit(app, controller, hotkey_manager))

    return app.exec()


def _quit(app: QApplication, controller: AppController, hotkey_manager) -> None:
    """アプリ終了（要件 4.1）。録音停止とホットキー解除を行ってから終了する。"""
    try:
        if hotkey_manager is not None:
            hotkey_manager.unbind()
        controller.shutdown()
    finally:
        app.quit()


if __name__ == "__main__":
    sys.exit(main())
