"""
Windows 시스템 트레이 (notification spec)

pystray + Pillow 필요.
notification spec 구현 시 확장.
"""
import logging
import threading
import webbrowser

logger = logging.getLogger(__name__)

_tray_instance = None


class TrayApp:
    def __init__(self):
        self._icon = None

    def start(self) -> None:
        """백그라운드 스레드에서 트레이 시작"""
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self) -> None:
        try:
            import pystray
            from PIL import Image, ImageDraw

            img = Image.new("RGB", (64, 64), color=(102, 126, 234))
            draw = ImageDraw.Draw(img)
            draw.ellipse([16, 16, 48, 48], fill=(255, 255, 255))

            menu = pystray.Menu(
                pystray.MenuItem("StockVision 열기", self._open_browser),
                pystray.MenuItem("종료", self._quit),
            )
            self._icon = pystray.Icon("StockVision", img, "StockVision", menu)
            self._icon.run()
        except ImportError:
            logger.warning("pystray/Pillow 미설치 — 트레이 비활성화")
        except Exception as e:
            logger.error(f"트레이 오류: {e}")

    def notify(self, title: str, message: str) -> None:
        if self._icon:
            try:
                self._icon.notify(title=title, message=message)
            except Exception:
                pass
        logger.info(f"[알림] {title}: {message}")

    def _open_browser(self) -> None:
        webbrowser.open("http://localhost:5173")

    def _quit(self) -> None:
        if self._icon:
            self._icon.stop()
        import sys
        sys.exit(0)


def get_tray() -> TrayApp:
    global _tray_instance
    if _tray_instance is None:
        _tray_instance = TrayApp()
    return _tray_instance
