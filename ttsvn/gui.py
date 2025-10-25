"""Graphical user interface for the ViettelAI Text-to-Speech desktop application."""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from PySide6.QtCore import QThread, Qt, Signal, QUrl
from PySide6.QtGui import QAction, QCloseEvent
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtMultimediaWidgets import QVideoWidget  # Required to initialise multimedia stack on some platforms
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .api import SynthesisRequest, SynthesisResult, ViettelAITextToSpeechClient, Voice
from .config import AppConfig, AudioDefaults, ApiSettings, load_config, save_config


class SynthesisWorker(QThread):
    """Background worker that performs synthesis to avoid blocking the UI."""

    succeeded = Signal(object)
    failed = Signal(str)

    def __init__(self, client: ViettelAITextToSpeechClient, request: SynthesisRequest) -> None:
        super().__init__()
        self._client = client
        self._request = request

    def run(self) -> None:  # type: ignore[override]
        try:
            result = self._client.synthesize(self._request)
        except Exception as exc:  # pragma: no cover - runtime safeguard
            self.failed.emit(str(exc))
        else:
            self.succeeded.emit(result)


class VoiceLoader(QThread):
    """Worker that loads the available voices from ViettelAI."""

    succeeded = Signal(list)
    failed = Signal(str)

    def __init__(self, client: ViettelAITextToSpeechClient) -> None:
        super().__init__()
        self._client = client

    def run(self) -> None:  # type: ignore[override]
        try:
            voices = list(self._client.list_voices())
        except Exception as exc:  # pragma: no cover - runtime safeguard
            self.failed.emit(str(exc))
        else:
            self.succeeded.emit(voices)


class ApiSettingsDialog(QDialog):
    """Dialog allowing the user to edit API credentials and endpoints."""

    def __init__(self, parent: QWidget, api_settings: ApiSettings) -> None:
        super().__init__(parent)
        self.setWindowTitle("Cài đặt API ViettelAI")
        self._settings = ApiSettings(
            token=api_settings.token,
            synthesize_url=api_settings.synthesize_url,
            voices_url=api_settings.voices_url,
            timeout=api_settings.timeout,
        )
        self._token_edit = QLineEdit(self._settings.token)
        self._synthesize_edit = QLineEdit(self._settings.synthesize_url)
        self._voices_edit = QLineEdit(self._settings.voices_url)
        self._timeout_spin = QSpinBox()
        self._timeout_spin.setRange(5, 300)
        self._timeout_spin.setValue(self._settings.timeout)

        form = QFormLayout()
        form.addRow("Token:", self._token_edit)
        form.addRow("URL tổng hợp:", self._synthesize_edit)
        form.addRow("URL giọng nói:", self._voices_edit)
        form.addRow("Timeout (giây):", self._timeout_spin)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout()
        layout.addLayout(form)
        layout.addWidget(buttons)
        self.setLayout(layout)

    @property
    def settings(self) -> ApiSettings:
        return self._settings

    def accept(self) -> None:  # type: ignore[override]
        self._settings.token = self._token_edit.text().strip()
        self._settings.synthesize_url = self._synthesize_edit.text().strip()
        self._settings.voices_url = self._voices_edit.text().strip()
        self._settings.timeout = int(self._timeout_spin.value())
        super().accept()


class AudioSettingsGroup(QGroupBox):
    """Group box containing audio tuning controls."""

    def __init__(self, defaults: AudioDefaults) -> None:
        super().__init__("Điều chỉnh giọng đọc")
        self.voice_box = QComboBox()
        self.format_box = QComboBox()
        self.format_box.addItems(["mp3", "wav", "ogg"])
        if defaults.format in ["mp3", "wav", "ogg"]:
            self.format_box.setCurrentText(defaults.format)
        self.sample_rate_box = QComboBox()
        for value in (16000, 22050, 24000, 44100, 48000):
            self.sample_rate_box.addItem(f"{value} Hz", value)
        index = self.sample_rate_box.findData(defaults.sample_rate)
        if index != -1:
            self.sample_rate_box.setCurrentIndex(index)

        self.speed_spin = QDoubleSpinBox()
        self.speed_spin.setRange(0.5, 2.0)
        self.speed_spin.setSingleStep(0.1)
        self.speed_spin.setValue(defaults.speed)

        self.volume_spin = QDoubleSpinBox()
        self.volume_spin.setRange(0.5, 2.0)
        self.volume_spin.setSingleStep(0.1)
        self.volume_spin.setValue(defaults.volume)

        self.pitch_spin = QDoubleSpinBox()
        self.pitch_spin.setRange(0.5, 2.0)
        self.pitch_spin.setSingleStep(0.1)
        self.pitch_spin.setValue(defaults.pitch)

        form = QFormLayout()
        form.addRow("Giọng đọc:", self.voice_box)
        form.addRow("Định dạng:", self.format_box)
        form.addRow("Tần số lấy mẫu:", self.sample_rate_box)
        form.addRow("Tốc độ:", self.speed_spin)
        form.addRow("Âm lượng:", self.volume_spin)
        form.addRow("Cao độ:", self.pitch_spin)
        self.setLayout(form)

    def populate_voices(self, voices: List[Voice], default_voice: str) -> None:
        self.voice_box.clear()
        for voice in voices:
            label = voice.name
            details = []
            if voice.language:
                details.append(voice.language)
            if voice.gender:
                details.append(voice.gender)
            if details:
                label += f" ({', '.join(details)})"
            self.voice_box.addItem(label, voice.code)
        index = self.voice_box.findData(default_voice)
        if index != -1:
            self.voice_box.setCurrentIndex(index)
        elif self.voice_box.count() > 0:
            self.voice_box.setCurrentIndex(0)

    def current_voice(self) -> str:
        return self.voice_box.currentData() or ""

    def current_format(self) -> str:
        return self.format_box.currentText()

    def current_sample_rate(self) -> int:
        return int(self.sample_rate_box.currentData())

    def current_speed(self) -> float:
        return float(self.speed_spin.value())

    def current_volume(self) -> float:
        return float(self.volume_spin.value())

    def current_pitch(self) -> float:
        return float(self.pitch_spin.value())


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self, config: AppConfig) -> None:
        super().__init__()
        self.setWindowTitle("TTSVN - ViettelAI Text to Speech")
        self.resize(960, 720)

        self._config = config
        self._client = ViettelAITextToSpeechClient(config.api)
        self._voices: List[Voice] = []
        self._current_worker: Optional[SynthesisWorker] = None
        self._current_result: Optional[SynthesisResult] = None
        self._voice_loader: Optional[VoiceLoader] = None
        self._media_player = QMediaPlayer()
        self._audio_output = QAudioOutput()
        self._media_player.setAudioOutput(self._audio_output)
        self._audio_output.setVolume(0.8)
        # Some platforms require a video surface for the multimedia stack to initialises correctly.
        self._dummy_video_widget = QVideoWidget()
        self._dummy_video_widget.hide()

        self._create_actions()
        self._create_widgets()
        self._load_initial_voices()

    # ------------------------------------------------------------------
    # UI construction helpers
    # ------------------------------------------------------------------
    def _create_actions(self) -> None:
        self._synthesize_action = QAction("Tổng hợp", self)
        self._synthesize_action.triggered.connect(self.start_synthesis)

        self._save_action = QAction("Lưu âm thanh...", self)
        self._save_action.triggered.connect(self.save_current_audio)
        self._save_action.setEnabled(False)

        self._refresh_voices_action = QAction("Làm mới danh sách giọng", self)
        self._refresh_voices_action.triggered.connect(self._load_initial_voices)

        self._api_settings_action = QAction("Cài đặt API", self)
        self._api_settings_action.triggered.connect(self.edit_api_settings)

        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("Tập tin")
        file_menu.addAction(self._synthesize_action)
        file_menu.addAction(self._save_action)

        settings_menu = menu_bar.addMenu("Cài đặt")
        settings_menu.addAction(self._refresh_voices_action)
        settings_menu.addAction(self._api_settings_action)

    def _create_widgets(self) -> None:
        central = QWidget()
        central_layout = QVBoxLayout(central)

        self._text_edit = QTextEdit()
        self._text_edit.setPlaceholderText("Nhập nội dung văn bản cần chuyển đổi...")
        central_layout.addWidget(self._text_edit)

        self._audio_group = AudioSettingsGroup(self._config.audio)
        central_layout.addWidget(self._audio_group)

        button_row = QHBoxLayout()
        self._synthesize_button = QPushButton("Tổng hợp")
        self._synthesize_button.clicked.connect(self.start_synthesis)
        button_row.addWidget(self._synthesize_button)

        self._stop_button = QPushButton("Dừng phát")
        self._stop_button.clicked.connect(self.stop_playback)
        button_row.addWidget(self._stop_button)

        self._play_button = QPushButton("Phát lại")
        self._play_button.clicked.connect(self.play_current_audio)
        self._play_button.setEnabled(False)
        button_row.addWidget(self._play_button)

        central_layout.addLayout(button_row)

        history_group = QGroupBox("Lịch sử tổng hợp")
        history_layout = QVBoxLayout(history_group)
        self._history_list = QListWidget()
        history_layout.addWidget(self._history_list)
        self._history_list.itemDoubleClicked.connect(self._handle_history_double_click)

        central_layout.addWidget(history_group)
        central_layout.addWidget(self._dummy_video_widget)

        self.setCentralWidget(central)

    # ------------------------------------------------------------------
    # Voice loading and configuration
    # ------------------------------------------------------------------
    def _load_initial_voices(self) -> None:
        self.statusBar().showMessage("Đang tải danh sách giọng...")
        if self._voice_loader and self._voice_loader.isRunning():
            return
        loader = VoiceLoader(self._client)
        loader.succeeded.connect(self._handle_voices_loaded)
        loader.failed.connect(self._handle_voices_failed)
        loader.finished.connect(lambda: self.statusBar().clearMessage())
        loader.finished.connect(self._clear_voice_loader)
        loader.start()
        self._voice_loader = loader

    def _clear_voice_loader(self) -> None:
        if self._voice_loader:
            self._voice_loader.deleteLater()
            self._voice_loader = None

    def _handle_voices_loaded(self, voices: List[Voice]) -> None:
        self._voices = voices
        self._audio_group.populate_voices(voices, self._config.audio.voice)
        if self._voices:
            default_code = self._audio_group.current_voice()
            if default_code:
                self._config.audio.voice = default_code

    def _handle_voices_failed(self, message: str) -> None:
        QMessageBox.warning(self, "Không thể tải giọng", message)

    # ------------------------------------------------------------------
    # Event handlers and actions
    # ------------------------------------------------------------------
    def start_synthesis(self) -> None:
        text = self._text_edit.toPlainText().strip()
        if not text:
            QMessageBox.information(self, "Thiếu nội dung", "Vui lòng nhập nội dung văn bản.")
            return
        voice_code = self._audio_group.current_voice()
        if not voice_code:
            QMessageBox.warning(self, "Thiếu giọng đọc", "Không có giọng nào được cấu hình. Hãy kiểm tra cài đặt API.")
            return

        request = SynthesisRequest(
            text=text,
            voice=voice_code,
            audio_format=self._audio_group.current_format(),
            sample_rate=self._audio_group.current_sample_rate(),
            speed=self._audio_group.current_speed(),
            volume=self._audio_group.current_volume(),
            pitch=self._audio_group.current_pitch(),
        )

        self._synthesize_button.setEnabled(False)
        self._synthesize_action.setEnabled(False)
        self.statusBar().showMessage("Đang tổng hợp giọng nói...")

        worker = SynthesisWorker(self._client, request)
        worker.succeeded.connect(self._handle_synthesis_success)
        worker.failed.connect(self._handle_synthesis_failure)
        worker.finished.connect(self._on_worker_finished)
        self._current_worker = worker
        worker.start()

    def _on_worker_finished(self) -> None:
        self._synthesize_button.setEnabled(True)
        self._synthesize_action.setEnabled(True)
        self.statusBar().clearMessage()
        if self._current_worker:
            self._current_worker.deleteLater()
            self._current_worker = None

    def _handle_synthesis_success(self, result: SynthesisResult) -> None:
        self._current_result = result
        self._config.audio.voice = result.request.voice
        self._config.audio.format = result.audio_format
        self._config.audio.sample_rate = result.request.sample_rate
        self._config.audio.speed = result.request.speed
        self._config.audio.volume = result.request.volume
        self._config.audio.pitch = result.request.pitch
        file_path = self._write_result_to_disk(result)
        self._save_action.setEnabled(True)
        self._play_button.setEnabled(True)
        item = QListWidgetItem(f"{datetime.now():%H:%M:%S} - {result.request.voice} - {file_path.name}")
        item.setData(Qt.UserRole, str(file_path))
        self._history_list.addItem(item)
        self._history_list.setCurrentItem(item)
        self.play_audio_file(file_path)

    def _handle_synthesis_failure(self, message: str) -> None:
        QMessageBox.critical(self, "Tổng hợp thất bại", message)

    def play_current_audio(self) -> None:
        current_item = self._history_list.currentItem()
        if not current_item:
            return
        path = current_item.data(Qt.UserRole)
        if path:
            self.play_audio_file(Path(path))

    def play_audio_file(self, path: Path) -> None:
        url = QUrl.fromLocalFile(str(path.resolve()))
        self._media_player.setSource(url)
        self._media_player.play()

    def stop_playback(self) -> None:
        self._media_player.stop()

    def save_current_audio(self) -> None:
        if not self._current_result:
            return
        suggested = self._current_result.suggested_filename
        file_path, _ = QFileDialog.getSaveFileName(self, "Lưu âm thanh", suggested, "Âm thanh (*.mp3 *.wav *.ogg)")
        if file_path:
            Path(file_path).write_bytes(self._current_result.audio_bytes)
            QMessageBox.information(self, "Đã lưu", f"Tập tin đã lưu tại {file_path}")

    def _write_result_to_disk(self, result: SynthesisResult) -> Path:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{result.request.voice}.{result.audio_format}"
        output_dir = Path(self._config.output_directory).expanduser()
        output_dir.mkdir(parents=True, exist_ok=True)
        file_path = output_dir / filename
        file_path.write_bytes(result.audio_bytes)
        return file_path

    def edit_api_settings(self) -> None:
        dialog = ApiSettingsDialog(self, self._config.api)
        if dialog.exec() == QDialog.Accepted:
            self._config.api = dialog.settings
            save_config(self._config)
            self._client = ViettelAITextToSpeechClient(self._config.api)
            self._load_initial_voices()

    def _handle_history_double_click(self, item: QListWidgetItem) -> None:
        path = item.data(Qt.UserRole)
        if not path:
            return
        file_path = Path(path)
        if not file_path.exists():
            QMessageBox.warning(self, "Tập tin không tồn tại", "Tập tin đã bị di chuyển hoặc xoá.")
            return
        self.play_audio_file(file_path)

    def closeEvent(self, event: QCloseEvent) -> None:  # type: ignore[override]
        save_config(self._config)
        event.accept()


def run() -> None:
    """Entry point launching the Qt event loop."""
    config = load_config()
    app = QApplication(sys.argv)
    window = MainWindow(config)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":  # pragma: no cover
    run()
