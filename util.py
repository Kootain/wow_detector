#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
util.py - 工具函数库
包含RGB图像反解成bytes的功能和CRC8校验
"""

import numpy as np
from PIL import Image
from typing import Tuple, Optional, List

def crc8(data: List[int], poly: int = 0x07, init: int = 0x00) -> int:
    """
    CRC-8校验函数 (多项式0x07)
    
    Args:
        data: 字节数据列表
        poly: CRC多项式 (默认0x07)
        init: 初始值 (默认0x00)
    
    Returns:
        CRC-8校验值
    """
    crc = init
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x80:
                crc = (crc << 1) ^ poly
            else:
                crc <<= 1
            crc &= 0xFF
    return crc

def xor_checksum(data: List[int]) -> int:
    """
    XOR校验函数
    
    Args:
        data: 字节数据列表
    
    Returns:
        XOR校验值
    """
    checksum = 0
    for byte in data:
        checksum ^= byte
    return checksum

def rgb_to_bytes(rgb_matrix: np.ndarray, use_crc: bool = True) -> Tuple[Optional[List[int]], bool, str]:
    """
    将RGB图像矩阵反解成bytes数组
    
    Args:
        rgb_matrix: RGB矩阵 [height, width, 3]
        use_crc: 是否使用CRC8校验 (默认True)
    
    Returns:
        tuple: (bytes数组, 校验是否通过, 状态信息)
    """
    try:
        height, width, channels = rgb_matrix.shape
        if channels != 3:
            return None, False, f"错误: 期望3通道RGB图像，实际{channels}通道"
        
        # 提取所有字节数据
        raw_bytes = []
        for row in range(height):
            for col in range(width):
                r, g, b = rgb_matrix[row, col]
                raw_bytes.extend([int(r), int(g), int(b)])
        
        # 检查最小长度 (至少需要: 长度字节 + 校验和)
        if len(raw_bytes) < 2:
            return None, False, "错误: 数据长度不足"
        
        # 读取长度字节
        data_length = raw_bytes[0]
        
        # 检查是否有足够的数据
        required_length = 1 + data_length + 1  # 长度字节 + 数据 + 校验和
        if len(raw_bytes) < required_length:
            return None, False, f"错误: 数据不足，需要{required_length}字节，实际{len(raw_bytes)}字节"
        
        # 提取数据和校验和
        payload = raw_bytes[1:1+data_length]
        received_checksum = raw_bytes[1+data_length]
        
        # 验证校验和
        frame_data = raw_bytes[0:1+data_length]  # 长度字节 + 数据
        if use_crc:
            calculated_checksum = crc8(frame_data)
        else:
            calculated_checksum = xor_checksum(frame_data)
        
        checksum_ok = (calculated_checksum == received_checksum)
        
        status = f"长度: {data_length}, 校验: {'✅通过' if checksum_ok else '❌失败'} (计算值: 0x{calculated_checksum:02X}, 接收值: 0x{received_checksum:02X})"
        
        return payload, checksum_ok, status
        
    except Exception as e:
        return None, False, f"解析错误: {str(e)}"

def rgb_image_to_bytes(image: Image.Image, use_crc: bool = True) -> Tuple[Optional[List[int]], bool, str]:
    """
    将PIL图像转换为bytes数组
    
    Args:
        image: PIL图像对象
        use_crc: 是否使用CRC8校验
    
    Returns:
        tuple: (bytes数组, 校验是否通过, 状态信息)
    """
    # 转换为numpy数组
    rgb_array = np.array(image.convert("RGB"))
    return rgb_to_bytes(rgb_array, use_crc)

def create_test_rgb_matrix(bytes_data: List[int], width: int, height: int, use_crc: bool = True) -> np.ndarray:
    """
    创建测试用的RGB矩阵 (模拟Lua的输出)
    
    Args:
        bytes_data: 原始字节数据
        width: 图像宽度(块数)
        height: 图像高度(块数)
        use_crc: 是否使用CRC8校验
    
    Returns:
        RGB矩阵 [height, width, 3]
    """
    # 构建帧数据: [长度][...bytes][校验和]
    frame = [len(bytes_data)] + bytes_data
    
    # 计算校验和
    if use_crc:
        checksum = crc8(frame)
    else:
        checksum = xor_checksum(frame)
    frame.append(checksum)
    
    # 计算总容量并填充
    total_blocks = width * height
    total_capacity = total_blocks * 3
    
    full_data = frame + [0] * (total_capacity - len(frame))
    full_data = full_data[:total_capacity]  # 确保不超出容量
    
    # 转换为RGB矩阵
    rgb_matrix = np.zeros((height, width, 3), dtype=np.uint8)
    
    for row in range(height):
        for col in range(width):
            block_index = row * width + col
            byte_offset = block_index * 3
            
            if byte_offset + 2 < len(full_data):
                rgb_matrix[row, col] = [
                    full_data[byte_offset],
                    full_data[byte_offset + 1], 
                    full_data[byte_offset + 2]
                ]
    
    return rgb_matrix

def test_rgb_to_bytes():
    """
    测试RGB转bytes功能
    """
    print("\n=== 测试 RGB转bytes 功能 ===")
    
    # 测试用例1: 简单数据
    test_data = [1, 2, 3, 4, 5]
    print(f"\n测试数据: {test_data}")
    
    # 创建RGB矩阵
    rgb_matrix = create_test_rgb_matrix(test_data, 4, 4, use_crc=True)
    print(f"RGB矩阵形状: {rgb_matrix.shape}")
    
    # 反解
    decoded_bytes, checksum_ok, status = rgb_to_bytes(rgb_matrix, use_crc=True)
    print(f"状态: {status}")
    
    if decoded_bytes is not None:
        print(f"解码结果: {decoded_bytes}")
        print(f"数据正确性: {'✅正确' if decoded_bytes == test_data else '❌错误'}")
    
    # 测试用例2: 较长数据
    long_data = list(range(20))
    print(f"\n长数据测试: {long_data}")
    
    rgb_matrix2 = create_test_rgb_matrix(long_data, 8, 8, use_crc=True)
    decoded_bytes2, checksum_ok2, status2 = rgb_to_bytes(rgb_matrix2, use_crc=True)
    
    print(f"状态: {status2}")
    if decoded_bytes2 is not None:
        print(f"解码长度: {len(decoded_bytes2)}")
        print(f"前10个字节: {decoded_bytes2[:10]}")
        print(f"数据正确性: {'✅正确' if decoded_bytes2 == long_data else '❌错误'}")
    
    # 测试用例3: 校验和错误
    print("\n校验和错误测试:")
    corrupted_matrix = rgb_matrix.copy()
    corrupted_matrix[0, 0, 0] = 255  # 破坏第一个字节
    
    decoded_bytes3, checksum_ok3, status3 = rgb_to_bytes(corrupted_matrix, use_crc=True)
    print(f"状态: {status3}")
    print(f"校验结果: {'✅通过' if checksum_ok3 else '❌失败 (符合预期)'}")

if __name__ == "__main__":
    test_rgb_to_bytes()