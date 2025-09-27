import sys
import time
import threading
from PyQt6.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout, QTextEdit, QHBoxLayout
from PyQt6.QtGui import QPainter, QColor, QPen, QPixmap
from PyQt6.QtCore import Qt, pyqtSignal
from mss import mss
from PIL import Image
import numpy as np
from util import rgb_image_to_bytes

# ----------------- 配置 -----------------
# Lua 配置映射到 Python
BLOCKS_X = 8
BLOCKS_Y = 8
PIXEL_SIZE = 1
FPS = 30
USE_CRC = True
OFFSET_X = 10
OFFSET_Y = 10  # Lua offsetY=-10, TOPLEFT 是左上角, 全屏模式正向偏移

# 监控区域相对于全屏
CONFIG = {
    "monitor_region": {
        "top": OFFSET_Y +3,
        "left": OFFSET_X +3,
        "width": (BLOCKS_X) * PIXEL_SIZE,
        "height": (BLOCKS_Y) * PIXEL_SIZE
    },
    "grid_size": BLOCKS_X,
    "cell_px": PIXEL_SIZE,
    "fps": FPS,
    "use_crc": USE_CRC
}


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
            monitor_region['left'],  # 边框向外扩展2像素
            monitor_region['top'],
            monitor_region['width'],
            monitor_region['height']
        )


# ----------------- GUI -----------------
class DecoderGUI(QWidget):
    update_signal = pyqtSignal(str, object)  # 修改信号，添加图像参数
    def __init__(self, config):
        super().__init__()
        self.setWindowTitle("WoW Matrix Decoder")
        self.setGeometry(50, 50, 600, 400)  # 增加窗口宽度以容纳图像
        # 窗口置顶且半透明，防止遮挡游戏像素块
        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setWindowOpacity(0.85)

        self.monitor_region = config['monitor_region']
        self.grid_size = config['grid_size']
        self.cell_px = config['cell_px']
        self.use_crc = config['use_crc']

        # UI 元素
        self.main_layout = QVBoxLayout()
        self.info_label = QLabel("等待数据...")
        
        # 水平布局：左侧显示监控区域图像，右侧显示文本信息
        self.content_layout = QHBoxLayout()
        
        # 监控区域图像显示
        self.image_label = QLabel("监控区域")
        self.image_label.setFixedSize(200, 200)  # 固定大小
        self.image_label.setStyleSheet("border: 1px solid gray; background-color: black;")
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setScaledContents(True)  # 自动缩放图像
        
        # 文本区域
        self.text_area = QTextEdit()
        self.text_area.setReadOnly(True)
        self.text_area.setMinimumWidth(300)
        
        # 添加到水平布局
        self.content_layout.addWidget(self.image_label)
        self.content_layout.addWidget(self.text_area)
        
        # 添加到主布局
        self.main_layout.addWidget(self.info_label)
        self.main_layout.addLayout(self.content_layout)
        
        self.setLayout(self.main_layout)
        self.update_signal.connect(self.update_display)

        # self.sct = mss()
        self.running = True

        # 启动线程
        self.thread = threading.Thread(target=self.update_loop, daemon=True)
        self.thread.start()

    def update_display(self, info, image):
        self.info_label.setText(f"监控区域: {self.monitor_region}")
        self.text_area.setText(info)
        
        # 更新监控区域图像
        if image is not None:
            # 将PIL图像转换为QPixmap
            image_rgb = image.convert('RGB')
            width, height = image_rgb.size
            # 放大图像以便更好地查看
            scale_factor = min(200 // width, 200 // height, 10)  # 最大放大10倍
            new_width = width * scale_factor
            new_height = height * scale_factor
            image_scaled = image_rgb.resize((new_width, new_height), Image.NEAREST)
            
            # 转换为QPixmap
            import io
            buffer = io.BytesIO()
            image_scaled.save(buffer, format='PNG')
            buffer.seek(0)
            pixmap = QPixmap()
            pixmap.loadFromData(buffer.getvalue())
            
            self.image_label.setPixmap(pixmap)

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
                seq, payload, ok = rgb_image_to_bytes(img)
                if seq is None:
                    info = "等待有效帧... (未检测到0xAA帧头)"
                else:
                    payload_str = f"[{len(payload)} bytes]" if payload else "[空载荷]"
                    info = f"Seq: {seq}\nPayload: {payload_str}\n校验: {'OK' if ok else '错误'}"
                    if payload and len(payload) > 0:
                        info += f"\n数据预览: {payload}"
            except Exception as e:
                info = f"解码错误: {e}"

            # 发送信号时同时传递文本信息和图像
            self.update_signal.emit(info, img)

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
