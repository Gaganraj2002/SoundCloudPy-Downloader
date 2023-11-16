import sys
import subprocess
import os
import json
import urllib.request
from PyQt5.QtWidgets import (
    QApplication,
    QWidget,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QFileDialog,
    QMessageBox,
    QProgressBar,
    QHBoxLayout,
)
from PyQt5.QtCore import QThread, pyqtSignal
import time


MAX_RETRY = 3
RETRY_DELAY = 5


class DownloadThread(QThread):
    progress_signal = pyqtSignal(int)
    speed_signal = pyqtSignal(float)
    size_signal = pyqtSignal(int)
    total_size_signal = pyqtSignal(int)
    emit_message_signal = pyqtSignal(str, str)

    def __init__(self, url, output_dir, parent=None):
        super(DownloadThread, self).__init__(parent)
        self.url = url
        self.output_dir = output_dir
        self.is_paused = False
        self.is_cancelled = False

    def run(self):
        try:
            self.download_audio(self.url, self.output_dir)
        except Exception as e:
            self.emit_error_signal(str(e))

    def download_audio(self, url, output_dir):
        try:
            filename = subprocess.check_output(
                ["youtube-dl", "--get-filename", url],
                encoding="utf-8",
                stderr=subprocess.DEVNULL,
            ).strip()

            subprocess.call(
                ["youtube-dl", "--write-info-json", "--skip-download", url],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

            json_files = [
                pos_json
                for pos_json in os.listdir(".")
                if pos_json.endswith(".info.json")
            ]
            if json_files:
                with open(json_files[0], "r") as fp:
                    data = json.load(fp)

                file_url = data["url"]
                title = data["fulltitle"]
                file_name = f"{title.replace('/', '_')}.mp3"
                full_path = os.path.join(output_dir, file_name)
                temp_path = os.path.join(output_dir, f"{file_name}.scpydownload")

                response = urllib.request.urlopen(file_url)
                file_size = int(response.headers["Content-Length"])

                self.total_size_signal.emit(file_size)

                start_time = time.time()
                downloaded = 0

                with open(temp_path, "wb") as file:
                    connection_speed = 0
                    while True:
                        if self.is_cancelled:
                            os.remove(temp_path)
                            break

                        data = response.read(1024)
                        if not data:
                            break

                        file.write(data)
                        downloaded += len(data)

                        elapsed_time = time.time() - start_time
                        if elapsed_time > 0:
                            connection_speed = downloaded / elapsed_time / 1024

                        progress = min(int((downloaded / file_size) * 100), 100)
                        self.progress_signal.emit(progress)
                        self.speed_signal.emit(connection_speed)
                        self.size_signal.emit(downloaded)

                        self.msleep(10)

                        while self.is_paused:
                            time.sleep(1)

                os.remove(json_files[0])

                os.rename(temp_path, full_path)

                self.emit_success_signal()
            else:
                raise Exception("Failed to locate info JSON file.")
        except subprocess.CalledProcessError as e:
            raise Exception(f"Failed to download audio. {e}")
        except (IndexError, FileNotFoundError):
            raise Exception("Failed to locate info JSON file.")
        except urllib.error.URLError as e:
            raise Exception(f"Failed to download audio. {e}")

    def toggle_pause_resume(self):
        self.is_paused = not self.is_paused

    def cancel_download(self):
        self.is_cancelled = True

    def emit_success_signal(self):
        self.emit_message_signal.emit("Download Complete", "Audio download complete.")

    def emit_error_signal(self, error_message):
        self.emit_message_signal.emit("Error", f"An error occurred: {error_message}")


class SoundCloudDownloaderApp(QWidget):
    def __init__(self):
        super(SoundCloudDownloaderApp, self).__init__()

        self.init_ui()

    def init_ui(self):
        self.url_label = QLabel("SoundCloud URL:")
        self.url_entry = QLineEdit(self)

        self.output_dir_label = QLabel("Output Directory:")
        self.output_dir_entry = QLineEdit(os.getcwd())
        self.output_dir_button = QPushButton("Browse", self)
        self.output_dir_button.clicked.connect(self.browse_output_dir)

        self.download_button = QPushButton("Download", self)
        self.download_button.clicked.connect(self.handle_download)

        self.progress_bar = QProgressBar(self)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)

        self.speed_label = QLabel("Speed: 0 KB/s")

        self.size_label = QLabel("Size: 0 MB")

        self.total_size_label = QLabel("Total Size: 0 MB")

        self.pause_resume_button = QPushButton("Pause", self)
        self.pause_resume_button.clicked.connect(self.toggle_pause_resume)

        self.cancel_button = QPushButton("Cancel", self)
        self.cancel_button.clicked.connect(self.cancel_download)

        input_layout = QVBoxLayout()
        input_layout.addWidget(self.url_label)
        input_layout.addWidget(self.url_entry)
        input_layout.addWidget(self.output_dir_label)
        input_layout.addWidget(self.output_dir_entry)
        input_layout.addWidget(self.output_dir_button)

        button_layout = QVBoxLayout()
        button_layout.addWidget(self.download_button)
        button_layout.addWidget(self.pause_resume_button)
        button_layout.addWidget(self.cancel_button)

        status_layout = QHBoxLayout()
        status_layout.addWidget(self.speed_label)
        status_layout.addWidget(self.size_label)
        status_layout.addWidget(self.total_size_label)

        main_layout = QVBoxLayout(self)
        main_layout.addLayout(input_layout)
        main_layout.addLayout(button_layout)
        main_layout.addWidget(self.progress_bar)
        main_layout.addLayout(status_layout)

        self.setWindowTitle("SoundCloudPy Downloader")
        self.show()

    def handle_download(self):
        url = self.url_entry.text()
        output_dir = self.output_dir_entry.text()

        if url and output_dir:
            self.thread = DownloadThread(url, output_dir)
            self.thread.progress_signal.connect(self.update_progress)
            self.thread.speed_signal.connect(self.update_speed)
            self.thread.size_signal.connect(self.update_size)
            self.thread.total_size_signal.connect(self.update_total_size)
            self.thread.emit_message_signal.connect(self.show_message_box)
            self.thread.start()
        else:
            QMessageBox.critical(
                self, "Error", "Please enter a URL and select an output directory."
            )

    def browse_output_dir(self):
        output_dir = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        self.output_dir_entry.setText(output_dir)

    def update_progress(self, progress):
        self.progress_bar.setValue(progress)

    def update_speed(self, speed):
        if speed > 1024:
            speed /= 1024
            speed_unit = "MB/s"
        else:
            speed_unit = "KB/s"
        self.speed_label.setText(f"Speed: {speed:.2f} {speed_unit}")

    def update_size(self, size):
        size /= 1024 * 1024
        self.size_label.setText(f"Size: {size:.2f} MB")

    def update_total_size(self, total_size):
        total_size /= 1024 * 1024
        self.total_size_label.setText(f"Total Size: {total_size:.2f} MB")

    def toggle_pause_resume(self):
        if hasattr(self, "thread"):
            self.thread.toggle_pause_resume()
            button_text = "Resume" if self.thread.is_paused else "Pause"
            self.pause_resume_button.setText(button_text)

    def cancel_download(self):
        if hasattr(self, "thread"):
            self.thread.cancel_download()
            self.thread.wait()
            self.progress_bar.setValue(0)
            self.speed_label.setText("Speed: 0 KB/s")
            self.size_label.setText("Size: 0 MB")
            self.total_size_label.setText("Total Size: 0 MB")
            self.pause_resume_button.setText("Pause")

            if self.thread.is_cancelled:
                QMessageBox.information(
                    self, "Canceled", "Download canceled. File removed."
                )

    def show_message_box(self, title, message):
        QMessageBox.information(self, title, message)


def main():
    app = QApplication(sys.argv)
    ex = SoundCloudDownloaderApp()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
