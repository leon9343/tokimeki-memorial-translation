import sys
import numpy as np
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QLabel,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
    QPushButton,
    QLineEdit,
    QAction,
    QFileDialog,
    QMessageBox,
)
from PyQt5.QtGui import QPixmap, QImage, QKeySequence
from PyQt5.QtCore import Qt, QPoint
import math
import os


class TokimekiEditor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.scale = 1.0  
        self.scroll_offset = 0  
        self.width = None
        self.height = None
        self.hex_value = None  
        self.image_data = None  
        self.original_data = None  
        self.image_array = None  
        self.undo_stack = []  
        self.initUI()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.paint_pixel(event)

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton:
            self.paint_pixel(event)

    def paint_pixel(self, event):
        if not self.label.pixmap():
            return

        local_pos = self.label.mapFromParent(event.pos())
        label_x = local_pos.x()
        label_y = local_pos.y()

        if label_x < 0 or label_y < 0:
            return

        x_scale = 1 / self.scale
        y_scale = 1 / self.scale

        x_center = int(label_x * x_scale)
        y_center = int(label_y * y_scale + self.scroll_offset)

        brush_radius = self.get_brush_radius()

        if self.image_data is not None:
            self.undo_stack.append(self.image_data.copy())
            if len(self.undo_stack) > 20:
                self.undo_stack.pop(0)

        for dy in range(-brush_radius, brush_radius + 1):
            for dx in range(-brush_radius, brush_radius + 1):
                distance = math.sqrt(dx**2 + dy**2)
                if distance <= brush_radius:
                    x = x_center + dx
                    y = y_center + dy

                    if 0 <= x < self.width and 0 <= y < self.height:
                        if self.hex_value and len(self.hex_value) == 4:
                            try:
                                pixel_data = int(self.hex_value, 16)
                                b = (pixel_data & 0x1F) << 3
                                g = ((pixel_data >> 5) & 0x1F) << 3
                                r = ((pixel_data >> 10) & 0x1F) << 3

                                self.image_array[y, x] = [r, g, b]

                                byte_index = (y * self.width + x) * 2
                                if byte_index + 1 < len(self.image_data):
                                    self.image_data[byte_index: byte_index + 2] = pixel_data.to_bytes(
                                        2, byteorder="little"
                                    )
                            except ValueError:
                                self.status_bar.showMessage(
                                    "Invalid hex value.", 5000)
                        else:
                            self.status_bar.showMessage(
                                "Set a valid 4-character hex value.", 5000)

        self.update_image_display()

    def get_brush_radius(self):
        try:
            radius_text = self.brush_input.text().strip()
            radius = int(radius_text)
            if radius < 0:
                raise ValueError
            return min(radius, 50)
        except ValueError:
            return 0  

    def initUI(self):
        self.setWindowTitle("Tokimeki Memorial Graphics Editor")
        self.central_widget = QWidget(self)
        self.layout = QVBoxLayout(self.central_widget)
        self.setCentralWidget(self.central_widget)

        file_panel = QHBoxLayout()
        self.layout.addLayout(file_panel)

        file_panel.addWidget(QLabel("File:"))
        self.file_input = QLineEdit(self)
        file_panel.addWidget(self.file_input)

        open_button = QPushButton("Open", self)
        open_button.clicked.connect(self.open_file)
        file_panel.addWidget(open_button)

        save_panel = QHBoxLayout()
        self.layout.addLayout(save_panel)

        save_panel.addWidget(QLabel("Save As:"))
        self.save_input = QLineEdit(self)
        save_panel.addWidget(self.save_input)

        save_button = QPushButton("Save As", self)
        save_button.clicked.connect(self.save_file)
        save_panel.addWidget(save_button)

        control_panel = QHBoxLayout()
        self.layout.addLayout(control_panel)

        control_panel.addWidget(QLabel("Width:"))
        self.width_input = QLineEdit(self)
        control_panel.addWidget(self.width_input)

        control_panel.addWidget(QLabel("Height:"))
        self.height_input = QLineEdit(self)
        control_panel.addWidget(self.height_input)

        set_button = QPushButton("Set Dimensions", self)
        set_button.clicked.connect(self.apply_custom_dimensions)
        control_panel.addWidget(set_button)

        control_panel.addWidget(QLabel("Hex:"))
        self.hex_input = QLineEdit(self)
        self.hex_input.setMaxLength(4)
        self.hex_input.setPlaceholderText("e.g., 7FFF")
        control_panel.addWidget(self.hex_input)
        self.hex_input.textChanged.connect(self.on_hex_changed)

        control_panel.addWidget(QLabel("Brush Radius:"))
        self.brush_input = QLineEdit(self)
        self.brush_input.setPlaceholderText("0")
        self.brush_input.setFixedWidth(50)
        control_panel.addWidget(self.brush_input)

        self.brush_input.setText("0")

        control_panel.addWidget(QLabel("Target File:"))
        self.inject_file_input = QLineEdit(self)
        control_panel.addWidget(self.inject_file_input)

        inject_browse_button = QPushButton("Browse", self)
        inject_browse_button.clicked.connect(self.browse_inject_file)
        control_panel.addWidget(inject_browse_button)

        control_panel.addWidget(QLabel("Offset:"))
        self.inject_offset_input = QLineEdit(self)
        self.inject_offset_input.setPlaceholderText("0x00000000 or 0")
        control_panel.addWidget(self.inject_offset_input)

        inject_button = QPushButton("Inject", self)
        inject_button.clicked.connect(self.inject_data)
        control_panel.addWidget(inject_button)

        self.label = QLabel(self)
        self.label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.layout.addWidget(self.label)

        self.label.wheelEvent = self.handle_wheel_event

        self.status_bar = self.statusBar()

        self.init_shortcuts()

    def init_shortcuts(self):
        open_action = QAction(self)
        open_action.setShortcut(QKeySequence("Ctrl+O"))
        open_action.triggered.connect(self.open_file)
        self.addAction(open_action)

        save_action = QAction(self)
        save_action.setShortcut(QKeySequence("Ctrl+S"))
        save_action.triggered.connect(self.save_file)
        self.addAction(save_action)

        undo_action = QAction(self)
        undo_action.setShortcut(QKeySequence("Ctrl+Z"))
        undo_action.triggered.connect(self.undo)
        self.addAction(undo_action)

    def on_hex_changed(self, text):
        text = text.strip()
        if len(text) == 4:
            try:
                int(text, 16)
                self.hex_value = text
                self.status_bar.showMessage("Hex value updated.", 2000)
            except ValueError:
                self.hex_value = None
                self.status_bar.showMessage("Invalid hex value.", 3000)
        else:
            if len(text) > 0:
                self.hex_value = None
                self.status_bar.showMessage(
                    "Hex value must be 4 characters.", 3000)
            else:
                self.hex_value = None
                self.status_bar.showMessage("Hex value cleared.", 2000)

    def browse_inject_file(self):
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Target File", "", "All Files (*)", options=options
        )
        if file_path:
            self.inject_file_input.setText(file_path)

    def inject_data(self):
        target_file = self.inject_file_input.text().strip()
        offset_text = self.inject_offset_input.text().strip()

        if not target_file:
            self.status_bar.showMessage("Please specify a target file.", 5000)
            return

        if not self.image_data:
            self.status_bar.showMessage("No image data to inject.", 5000)
            return

        try:
            if offset_text.startswith("0x") or offset_text.startswith("0X"):
                offset = int(offset_text, 16)
            else:
                offset = int(offset_text, 10)
            if offset < 0:
                raise ValueError("Offset cannot be negative.")
        except ValueError as ve:
            self.status_bar.showMessage(f"Invalid offset: {ve}", 5000)
            return

        try:
            with open(target_file, "r+b") as f:
                f.seek(0, os.SEEK_END)
                file_size = f.tell()
                if offset > file_size:
                    self.status_bar.showMessage(
                        "Offset exceeds file size.", 5000)
                    return
                f.seek(offset)
                if offset + len(self.image_data) > file_size:
                    f.seek(0, os.SEEK_END)
                f.write(self.image_data)
            self.status_bar.showMessage(
                f"Injected image data into {
                    target_file} at offset {offset:#010x}.", 5000
            )
        except Exception as e:
            self.status_bar.showMessage(f"Error injecting data: {e}", 7000)

    def apply_custom_dimensions(self):
        try:
            width = int(self.width_input.text())
            height = int(self.height_input.text())
            if width <= 0 or height <= 0:
                raise ValueError
            self.width = width
            self.height = height
            self.scroll_offset = 0
            self.update_image_display()
            self.status_bar.showMessage(
                f"Dimensions set to {width}x{height}.", 5000)
        except ValueError:
            self.status_bar.showMessage("Invalid dimensions entered.", 5000)

    def update_image_display(self):
        if self.width is None or self.height is None:
            total_pixels = len(self.image_data) // 2
            side_length = int(math.sqrt(total_pixels))
            self.width = side_length
            self.height = (total_pixels + self.width - 1) // self.width

        total_pixels = self.width * self.height
        decoded_pixels = self.decode_15bpp_bgr(self.image_data, total_pixels)

        self.image_array = decoded_pixels.reshape((self.height, self.width, 3))

        # Calculate visible_height based on the label's height and current scale
        label_height = self.label.height()
        if label_height == 0:
            # Prevent division by zero; assume full image is visible if label height is not set yet
            visible_height = self.height
        else:
            visible_height = int(label_height / self.scale)

        # Ensure visible_height does not exceed image boundaries
        visible_height = min(visible_height, self.height - self.scroll_offset)

        visible_image = self.image_array[
            self.scroll_offset: self.scroll_offset + visible_height, :, :
        ]

        qimage = QImage(
            visible_image.data,
            self.width,
            visible_image.shape[0],
            3 * self.width,
            QImage.Format_RGB888,
        )
        pixmap = QPixmap.fromImage(qimage)

        scaled_pixmap = pixmap.scaled(
            self.scale * pixmap.size(), Qt.KeepAspectRatio, Qt.FastTransformation
        )
        self.label.setPixmap(scaled_pixmap)
        self.label.adjustSize()

    def decode_15bpp_bgr(self, data, total_pixels):
        pixels = []
        for i in range(0, min(len(data), total_pixels * 2), 2):
            if i + 1 >= len(data):
                break
            pixel_data = int.from_bytes(data[i: i + 2], byteorder="little")
            b = (pixel_data & 0x1F) << 3
            g = ((pixel_data >> 5) & 0x1F) << 3
            r = ((pixel_data >> 10) & 0x1F) << 3
            pixels.append((r, g, b))

        if len(pixels) < total_pixels:
            pixels.extend([(0, 0, 0)] * (total_pixels - len(pixels)))

        return np.array(pixels, dtype=np.uint8)

    def handle_wheel_event(self, event):
        if event.modifiers() == Qt.ControlModifier:
            if event.angleDelta().y() > 0:
                self.scale *= 1.1
            else:
                self.scale /= 1.1
            self.scale = max(0.1, min(self.scale, 10.0))
        else:
            scroll_amount = 10
            if event.angleDelta().y() > 0:
                self.scroll_offset = max(0, self.scroll_offset - scroll_amount)
            else:
                max_offset = max(
                    0, self.image_array.shape[0] -
                    int(self.label.height() / self.scale)
                )
                self.scroll_offset = min(
                    max_offset, self.scroll_offset + scroll_amount)

        self.update_image_display()

    def undo(self):
        if not self.undo_stack:
            self.status_bar.showMessage("Nothing to undo.", 3000)
            return

        self.image_data = self.undo_stack.pop()

        total_pixels = self.width * self.height
        decoded_pixels = self.decode_15bpp_bgr(self.image_data, total_pixels)
        self.image_array = decoded_pixels.reshape((self.height, self.width, 3))

        self.update_image_display()
        self.status_bar.showMessage("Undo successful.", 3000)

    def open_file(self):
        file_path = self.file_input.text().strip()
        if not file_path:
            options = QFileDialog.Options()
            file_path, _ = QFileDialog.getOpenFileName(
                self, "Open NBN File", "", "NBN Files (*.nbn);;All Files (*)", options=options
            )
            if not file_path:
                return  

        if os.path.isfile(file_path):
            self.load_nbn_file(file_path)
            self.scroll_offset = 0
            self.update_image_display()
            self.status_bar.showMessage(f"Loaded file: {file_path}", 5000)
        else:
            self.status_bar.showMessage(
                "File not found, using the current image.", 5000)

    def save_file(self):
        save_path = self.save_input.text().strip()
        if not save_path:
            options = QFileDialog.Options()
            save_path, _ = QFileDialog.getSaveFileName(
                self, "Save As", "", "NBN Files (*.nbn);;All Files (*)", options=options
            )
            if not save_path:
                return  

        if save_path:
            try:
                if len(self.image_data) == len(self.original_data):
                    with open(save_path, "wb") as file:
                        file.write(self.image_data)
                    self.status_bar.showMessage(
                        f"File saved as {save_path}", 5000)
                else:
                    self.status_bar.showMessage(
                        "Warning: Data length mismatch. Check the image processing steps.", 7000
                    )
            except Exception as e:
                self.status_bar.showMessage(f"Error saving file: {e}", 7000)
        else:
            self.status_bar.showMessage(
                "Please specify a valid save file path.", 5000)

    def load_nbn_file(self, file_path):
        try:
            with open(file_path, "rb") as file:
                binary_data = file.read()
            self.original_data = binary_data
            self.image_data = bytearray(binary_data)
            # Clear undo stack since we have a new image
            self.undo_stack.clear()
        except Exception as e:
            self.status_bar.showMessage(f"Error loading file: {e}", 7000)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    editor = TokimekiEditor()
    editor.show()
    sys.exit(app.exec_())
