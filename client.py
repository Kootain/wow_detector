import sys
import time
import threading
from PyQt6.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout, QTextEdit
from PyQt6.QtGui import QPainter, QColor, QPen
from PyQt6.QtCore import Qt, pyqtSignal, QRect
from mss import mss
from PIL import Image
import numpy as np

# ----------------- 配置 -----------------
# Lua 配置映射到 Python
BLOCKS_X = 8
BLOCKS_Y = 8
PIXEL_SIZE = 4
FPS = 30
USE_CRC = True
OFFSET_X = 10
OFFSET_Y = 10  # Lua offsetY=-10, TOPLEFT 是左上角, 全屏模式正向偏移

# 监控区域相对于全屏
CONFIG = {
    "monitor_region": {
        "top": OFFSET_Y,
        "left": OFFSET_X,
        "width": BLOCKS_X * PIXEL_SIZE,
        "height": BLOCKS_Y * PIXEL_SIZE
    },
    "grid_size": BLOCKS_X,
    "cell_px": PIXEL_SIZE,
    "fps": FPS,
    "use_crc": USE_CRC
}

# ----------------- CRC8 -----------------
def crc8(data, poly=0x07, init=0x00):
    crc = init
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x80:
                crc = ((crc << 1) ^ poly) & 0xFF
            else:
                crc = (crc << 1) & 0xFF
    return crc

# ----------------- 解码函数 -----------------
def decode_matrix(img, grid_size, cell_px, use_crc=False):
    arr = np.array(img.convert("RGB"))
    data_bytes = []
    for row in range(grid_size):
        for col in range(grid_size):
            y = row * cell_px + cell_px // 2
            x = col * cell_px + cell_px // 2
            r, g, b = arr[y, x]
            data_bytes.extend([r, g, b])

    data_bytes = bytearray(data_bytes)
    seq = data_bytes[0]
    length = data_bytes[1]
    payload = data_bytes[2:2+length]
    checksum = data_bytes[2+length]

    # 校验
    if use_crc:
        calc = crc8([seq, length] + list(payload))
    else:
        calc = 0
        for v in [seq, length] + list(payload):
            calc ^= v
    ok = (calc == checksum)
    return seq, payload, ok

# ----------------- 监控区域边框窗口 -----------------
class MonitorOverlay(QWidget):
    def __init__(self, monitor_region):
        super().__init__()
        self.monitor_region = monitor_region
        
        # 设置窗口属性：置顶、透明背景、无边框
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint | 
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        
        # 设置窗口位置和大小为监控区域
        self.setGeometry(
            monitor_region['left'] - 2,  # 边框向外扩展2像素
            monitor_region['top'] - 2,
            monitor_region['width'] + 4,
            monitor_region['height'] + 4
        )
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 设置边框样式：红色，2像素宽
        pen = QPen(QColor(255, 0, 0, 200))  # 红色，半透明
        pen.setWidth(2)
        painter.setPen(pen)
        
        # 绘制边框矩形
        rect = QRect(1, 1, self.width() - 2, self.height() - 2)
        painter.drawRect(rect)
        
        painter.end()

# ----------------- GUI -----------------
class DecoderGUI(QWidget):
    update_signal = pyqtSignal(str)  # 定义信号
    def __init__(self, config):
        super().__init__()
        self.setWindowTitle("WoW Matrix Decoder")
        self.setGeometry(50, 50, 400, 300)
        # 窗口置顶且半透明，防止遮挡游戏像素块
        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setWindowOpacity(0.85)

        self.monitor_region = config['monitor_region']
        self.grid_size = config['grid_size']
        self.cell_px = config['cell_px']
        self.use_crc = config['use_crc']

        # UI 元素
        self.layout = QVBoxLayout()
        self.info_label = QLabel("等待数据...")
        self.text_area = QTextEdit()
        self.text_area.setReadOnly(True)
        self.layout.addWidget(self.info_label)
        self.layout.addWidget(self.text_area)
        self.setLayout(self.layout)
        self.update_signal.connect(self.update_text)

        # self.sct = mss()
        self.running = True

        # 启动线程
        self.thread = threading.Thread(target=self.update_loop, daemon=True)
        self.thread.start()

    def update_text(self, info):
            self.info_label.setText(f"监控区域: {self.monitor_region}")
            self.text_area.setText(info)

    def paintEvent(self, event):
        # GUI 窗口本身半透明，无需绘制矩形框到游戏上
        pass

    def update_loop(self):
        sct = mss()
        while self.running:
            # 截屏游戏矩阵区域
            sct_img = sct.grab(self.monitor_region)
            img = Image.frombytes("RGB", sct_img.size, sct_img.rgb)
            
            # 解码
            try:
                seq, payload, ok = decode_matrix(img, self.grid_size, self.cell_px, self.use_crc)
                info = f"Seq: {seq}\nPayload: {payload}\n校验: {'OK' if ok else '错误'}"
            except Exception as e:
                info = f"解码错误: {e}"

            self.update_signal.emit(info)

            time.sleep(1 / CONFIG['fps'])

    def closeEvent(self, event):
        self.running = False
        # 关闭边框窗口
        if hasattr(self, 'overlay'):
            self.overlay.close()
        event.accept()

# ----------------- 启动 -----------------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # 创建主GUI窗口
    gui = DecoderGUI(CONFIG)
    gui.show()
    
    # 创建监控区域边框窗口
    overlay = MonitorOverlay(CONFIG['monitor_region'])
    overlay.show()
    
    # 将overlay引用传递给gui，以便关闭时清理
    gui.overlay = overlay
    
    sys.exit(app.exec())
