"""TTSVN ViettelAI text-to-speech desktop application."""
from __future__ import annotations

import platform
import sys
from importlib import import_module
from typing import Callable

__all__ = ["run"]


def _missing_pyside6_message() -> str:
    python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    architecture = platform.architecture()[0]
    return (
        "PySide6 không được cài đặt hoặc không có sẵn cho phiên bản Python hiện tại.\n"
        "• Ứng dụng yêu cầu Python 64-bit từ 3.9 trở lên.\n"
        "• Hãy kiểm tra lại phiên bản bằng lệnh `python --version` và đảm bảo đang dùng bản 64-bit.\n"
        "• Nếu đang ở Python {python_version} ({architecture}), hãy cài đặt Python 3.9+ 64-bit rồi cài lại `requirements.txt`."
    )


def _load_gui_run() -> Callable[[], None]:
    try:
        module = import_module(".gui", __name__)
    except ModuleNotFoundError as exc:  # pragma: no cover - defensive runtime guard
        if exc.name and exc.name.startswith("PySide6"):
            raise SystemExit(_missing_pyside6_message()) from exc
        raise
    return getattr(module, "run")


def run() -> None:
    """Launch the graphical application."""

    _run = _load_gui_run()
    _run()
