import os
import sys
from pathlib import Path

# Give Windows a stable AppUserModelID so the taskbar uses Jazzify's icon
# instead of the Python interpreter icon when launched with `py app.py`.
if sys.platform == "win32":
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("Jazzify.App")
    except Exception:
        pass

os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Basic")

from PySide6.QtCore import QUrl
from PySide6.QtGui import QGuiApplication, QIcon, QSurfaceFormat
from PySide6.QtQuick import QQuickWindow
from PySide6.QtQml import QQmlApplicationEngine

from core.database import Database
from core.library import Library
from core.player import Player
from core.settings import Settings

ROOT = Path(__file__).resolve().parent


def main() -> int:
    # QQuickWindow must know that an alpha buffer is required BEFORE any
    # QML Window is created. Setting the default alpha buffer after the QML
    # window exists is too late on some Windows/Qt configurations and causes
    # the opaque/white overlay and swapchain warnings.
    surface = QSurfaceFormat()
    surface.setAlphaBufferSize(8)
    QSurfaceFormat.setDefaultFormat(surface)
    QQuickWindow.setDefaultAlphaBuffer(True)

    app = QGuiApplication(sys.argv)
    app.setApplicationName("Jazzify")
    app.setApplicationDisplayName("Jazzify")
    app.setOrganizationName("Jazzify")
    app.setWindowIcon(QIcon(str(ROOT / "images" / "jazzify-icon.svg")))

    settings = Settings(ROOT / "data" / "settings.json")
    database = Database(ROOT / "data" / "music.db")
    library = Library(database, settings, ROOT / "cache" / "artwork")
    player = Player()

    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("library", library)
    engine.rootContext().setContextProperty("player", player)
    engine.rootContext().setContextProperty("settings", settings)

    qml = ROOT / "qml" / "Main.qml"
    engine.load(QUrl.fromLocalFile(str(qml)))
    roots = engine.rootObjects()
    if not roots:
        database.close()
        return 1

    window = roots[0]

    try:
        window.show()
        app.processEvents()
        hwnd = int(window.winId())
        player.initialize_media_controls(hwnd)
    except Exception as exc:
        print(f"[Jazzify] Could not initialize Windows media controls: {exc}")
        try:
            window.show()
        except Exception:
            pass

    library.start()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
