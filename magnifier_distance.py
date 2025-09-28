#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import threading
import time
from PIL import Image
import mss
import math
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTextEdit, QGroupBox
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject
from PyQt6.QtGui import QPixmap, QImage, QPainter, QPen, QColor, QCursor
from pynput import mouse

class MagnifierApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("屏幕放大镜 - 距离测量工具")
        self.setGeometry(100, 100, 400, 500)
        
        # 居中显示窗口
        self.center_window()
        
        # 设置窗口置顶
        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint)
        
        # 放大倍数
        self.zoom_factor = 3
        self.capture_size = 100  # 捕获区域大小
        
        # 点击状态
        self.points = []  # 存储选择的两个点
        self.selecting = False
        
        # 屏幕截图对象
        self.sct = mss.mss()
        
        # 全局鼠标监听器
        self.mouse_listener = None
        
        # 创建界面
        self.create_widgets()
        
        # 创建定时器更新放大镜
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_magnifier)
        self.timer.start(50)  # 20 FPS
    
    def center_window(self):
        """将窗口居中显示"""
        screen = QApplication.primaryScreen().geometry()
        window = self.geometry()
        x = (screen.width() - window.width()) // 2
        y = (screen.height() - window.height()) // 2
        self.move(x, y)
    
    def create_widgets(self):
        """创建界面组件"""
        # 主窗口部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QVBoxLayout(central_widget)
        
        # 放大镜显示区域
        self.magnifier_label = QLabel()
        self.magnifier_label.setFixedSize(300, 300)
        self.magnifier_label.setStyleSheet("border: 1px solid black; background-color: black;")
        self.magnifier_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.magnifier_label)
        
        # 鼠标位置显示
        self.pos_label = QLabel("鼠标位置: (0, 0)")
        self.pos_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.pos_label)
        
        # 控制按钮
        button_layout = QHBoxLayout()
        
        self.start_btn = QPushButton("开始选择点")
        self.start_btn.clicked.connect(self.start_selection)
        button_layout.addWidget(self.start_btn)
        
        self.clear_btn = QPushButton("清除点")
        self.clear_btn.clicked.connect(self.clear_points)
        button_layout.addWidget(self.clear_btn)
        
        main_layout.addLayout(button_layout)
        
        # 结果显示区域
        result_group = QGroupBox("测量结果")
        result_layout = QVBoxLayout(result_group)
        
        self.result_text = QTextEdit()
        self.result_text.setMaximumHeight(150)
        result_layout.addWidget(self.result_text)
        
        main_layout.addWidget(result_group)
    
    def start_selection(self):
        """开始选择点"""
        self.selecting = True
        self.points.clear()
        self.start_btn.setText("选择中... (左击选择点)")
        self.start_btn.setEnabled(False)
        self.result_text.clear()
        self.result_text.append("请在屏幕上左击选择第一个点...")
        
        # 启动全局鼠标监听器
        if self.mouse_listener:
            self.mouse_listener.stop()
        self.mouse_listener = mouse.Listener(on_click=self.on_global_click)
        self.mouse_listener.start()
        
    def clear_points(self):
        """清除选择的点"""
        self.points.clear()
        self.selecting = False
        self.start_btn.setText("开始选择点")
        self.start_btn.setEnabled(True)
        self.result_text.clear()
        
        # 停止全局鼠标监听器
        if self.mouse_listener:
            self.mouse_listener.stop()
            self.mouse_listener = None
    
    def on_global_click(self, x, y, button, pressed):
        """处理全局鼠标点击事件"""
        if not self.selecting or button != mouse.Button.left or not pressed:
            return
            
        self.points.append((x, y))
        
        if len(self.points) == 1:
            self.result_text.append(f"第一个点: ({x}, {y})")
            self.result_text.append("请左击选择第二个点...")
        elif len(self.points) == 2:
            self.result_text.append(f"第二个点: ({x}, {y})")
            self.result_text.append("")
            self.calculate_distance()
            self.selecting = False
            self.start_btn.setText("开始选择点")
            self.start_btn.setEnabled(True)
            
            # 停止监听器
            if self.mouse_listener:
                self.mouse_listener.stop()
                self.mouse_listener = None
    
    def calculate_distance(self):
        """计算两点间的距离"""
        if len(self.points) != 2:
            return
            
        x1, y1 = self.points[0]
        x2, y2 = self.points[1]
        
        # 计算距离
        dx = abs(x2 - x1)
        dy = abs(y2 - y1)
        euclidean_distance = math.sqrt(dx**2 + dy**2)
        
        # 显示结果
        self.result_text.append("=== 测量结果 ===")
        self.result_text.append(f"X轴距离: {dx} 像素")
        self.result_text.append(f"Y轴距离: {dy} 像素")
        self.result_text.append(f"直线距离: {euclidean_distance:.2f} 像素")
        self.result_text.append(f"方向: {self.get_direction(x1, y1, x2, y2)}")
        self.result_text.append("")
        
        # 自动滚动到底部
        cursor = self.result_text.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.result_text.setTextCursor(cursor)
    
    def get_direction(self, x1, y1, x2, y2):
        """获取两点间的方向"""
        dx = x2 - x1
        dy = y2 - y1
        
        if dx > 0 and dy > 0:
            return "右下"
        elif dx > 0 and dy < 0:
            return "右上"
        elif dx < 0 and dy > 0:
            return "左下"
        elif dx < 0 and dy < 0:
            return "左上"
        elif dx > 0:
            return "右"
        elif dx < 0:
            return "左"
        elif dy > 0:
            return "下"
        elif dy < 0:
            return "上"
        else:
            return "同一点"
    
    def update_magnifier(self):
        """更新放大镜显示"""
        try:
            # 获取鼠标位置
            cursor_pos = QCursor.pos()
            mouse_x = cursor_pos.x()
            mouse_y = cursor_pos.y()
            
            # 更新位置标签
            self.pos_label.setText(f"鼠标位置: ({mouse_x}, {mouse_y})")
            
            # 计算截图区域
            half_size = self.capture_size // 2
            left = mouse_x - half_size
            top = mouse_y - half_size
            
            # 截图
            monitor = {"top": top, "left": left, "width": self.capture_size, "height": self.capture_size}
            screenshot = self.sct.grab(monitor)
            
            # 转换为PIL图像
            img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
            
            # 放大图像
            new_size = (img.width * self.zoom_factor, img.height * self.zoom_factor)
            img_zoomed = img.resize(new_size, Image.NEAREST)
            
            # 转换为QImage
            img_data = img_zoomed.tobytes("raw", "RGB")
            qimg = QImage(img_data, img_zoomed.width, img_zoomed.height, QImage.Format.Format_RGB888)
            
            # 创建QPixmap并绘制十字准线
            pixmap = QPixmap.fromImage(qimg)
            painter = QPainter(pixmap)
            painter.setPen(QPen(QColor(255, 0, 0), 2))
            
            # 绘制十字准线
            center_x = pixmap.width() // 2
            center_y = pixmap.height() // 2
            painter.drawLine(center_x - 10, center_y, center_x + 10, center_y)
            painter.drawLine(center_x, center_y - 10, center_x, center_y + 10)
            painter.end()
            
            # 更新显示
            self.magnifier_label.setPixmap(pixmap)
            
        except Exception as e:
            print(f"更新放大镜时出错: {e}")
    
    def closeEvent(self, event):
        """关闭程序时清理资源"""
        if self.mouse_listener:
            self.mouse_listener.stop()
        event.accept()
    
    def run(self):
        """运行程序"""
        self.show()
        return QApplication.instance().exec()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MagnifierApp()
    sys.exit(window.run())