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
    QLabel, QPushButton, QTextEdit, QGroupBox, QLineEdit
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject
from PyQt6.QtGui import QPixmap, QImage, QPainter, QPen, QColor, QCursor

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
        
        # 虚拟光标位置
        cursor_pos = QCursor.pos()
        self.virtual_cursor_x = cursor_pos.x()
        self.virtual_cursor_y = cursor_pos.y()
        
        # 屏幕截图对象
        self.sct = mss.mss()
        
        # 移除鼠标监听器，改用按钮控制
        
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
        
        # 方向控制按钮
        direction_group = QGroupBox("方向控制")
        direction_layout = QVBoxLayout(direction_group)
        
        # 上按钮
        up_layout = QHBoxLayout()
        up_layout.addStretch()
        self.up_btn = QPushButton("↑")
        self.up_btn.setFixedSize(40, 40)
        self.up_btn.clicked.connect(self.move_up)
        up_layout.addWidget(self.up_btn)
        up_layout.addStretch()
        direction_layout.addLayout(up_layout)
        
        # 左右按钮
        middle_layout = QHBoxLayout()
        self.left_btn = QPushButton("←")
        self.left_btn.setFixedSize(40, 40)
        self.left_btn.clicked.connect(self.move_left)
        middle_layout.addWidget(self.left_btn)
        
        middle_layout.addStretch()
        
        self.right_btn = QPushButton("→")
        self.right_btn.setFixedSize(40, 40)
        self.right_btn.clicked.connect(self.move_right)
        middle_layout.addWidget(self.right_btn)
        direction_layout.addLayout(middle_layout)
        
        # 下按钮
        down_layout = QHBoxLayout()
        down_layout.addStretch()
        self.down_btn = QPushButton("↓")
        self.down_btn.setFixedSize(40, 40)
        self.down_btn.clicked.connect(self.move_down)
        down_layout.addWidget(self.down_btn)
        down_layout.addStretch()
        direction_layout.addLayout(down_layout)
        
        main_layout.addWidget(direction_group)
        
        # 坐标输入组
        coord_group = QGroupBox("坐标跳转")
        coord_layout = QVBoxLayout(coord_group)
        
        # 坐标输入行
        coord_input_layout = QHBoxLayout()
        coord_input_layout.addWidget(QLabel("X:"))
        self.x_input = QLineEdit()
        self.x_input.setPlaceholderText("输入X坐标")
        coord_input_layout.addWidget(self.x_input)
        
        coord_input_layout.addWidget(QLabel("Y:"))
        self.y_input = QLineEdit()
        self.y_input.setPlaceholderText("输入Y坐标")
        coord_input_layout.addWidget(self.y_input)
        
        self.jump_btn = QPushButton("跳转")
        self.jump_btn.clicked.connect(self.jump_to_coordinate)
        coord_input_layout.addWidget(self.jump_btn)
        
        coord_layout.addLayout(coord_input_layout)
        main_layout.addWidget(coord_group)
        
        # 控制按钮
        button_layout = QHBoxLayout()
        
        self.start_btn = QPushButton("开始选择点")
        self.start_btn.clicked.connect(self.start_selection)
        button_layout.addWidget(self.start_btn)
        
        self.select_point_btn = QPushButton("选择当前点")
        self.select_point_btn.clicked.connect(self.select_current_point)
        self.select_point_btn.setEnabled(False)
        button_layout.addWidget(self.select_point_btn)
        
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
    
    def move_up(self):
        """向上移动虚拟光标"""
        self.virtual_cursor_y -= 1
    
    def move_down(self):
        """向下移动虚拟光标"""
        self.virtual_cursor_y += 1
    
    def move_left(self):
        """向左移动虚拟光标"""
        self.virtual_cursor_x -= 1
    
    def move_right(self):
        """向右移动虚拟光标"""
        self.virtual_cursor_x += 1
    
    def jump_to_coordinate(self):
        """跳转到指定坐标"""
        try:
            x = int(self.x_input.text())
            y = int(self.y_input.text())
            
            # 更新虚拟光标位置
            self.virtual_cursor_x = x
            self.virtual_cursor_y = y
            
            # 清空输入框
            self.x_input.clear()
            self.y_input.clear()
            
        except ValueError:
            # 如果输入不是有效数字，忽略
            pass
    
    def start_selection(self):
        """开始选择点"""
        self.selecting = True
        self.points.clear()
        self.start_btn.setText("选择中...")
        self.start_btn.setEnabled(False)
        self.select_point_btn.setEnabled(True)
        self.result_text.clear()
        self.result_text.append("请使用方向键移动到第一个点，然后点击'选择当前点'...")
        
    def clear_points(self):
        """清除选择的点"""
        self.points = []
        self.selecting = False
        self.start_btn.setText("开始选择点")
        self.start_btn.setEnabled(True)
        self.select_point_btn.setEnabled(False)
        self.result_text.clear()
    
    def select_current_point(self):
        """选择当前虚拟光标位置的点"""
        if not self.selecting:
            return
        
        x, y = self.virtual_cursor_x, self.virtual_cursor_y
        self.points.append((x, y))
        
        if len(self.points) == 1:
            self.result_text.append(f"第一个点: ({x}, {y})")
            self.result_text.append("请移动到第二个点，然后点击'选择当前点'...")
        elif len(self.points) == 2:
            self.result_text.append(f"第二个点: ({x}, {y})")
            
            # 计算距离
            self.calculate_distance()
            
            # 重置状态
            self.selecting = False
            self.start_btn.setText("开始选择点")
            self.start_btn.setEnabled(True)
            self.select_point_btn.setEnabled(False)
    

    
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
            # 使用虚拟光标位置
            x, y = self.virtual_cursor_x, self.virtual_cursor_y
            
            # 更新位置标签
            self.pos_label.setText(f"位置: ({x}, {y})")
            
            # 计算截图区域
            half_size = self.capture_size // 2
            left = x - half_size
            top = y - half_size
            
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
        """程序关闭时的清理工作"""
        event.accept()
    
    def run(self):
        """运行程序"""
        self.show()
        return QApplication.instance().exec()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MagnifierApp()
    sys.exit(window.run())