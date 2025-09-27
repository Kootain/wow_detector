#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
util.py - 工具函数库
包含RGB图像反解成bytes的功能和CRC8校验
"""

import numpy as np
from PIL import Image
from typing import Tuple, Optional, List

def crc8(data: bytes, poly: int = 0x07, init: int = 0x00) -> int:
    """
    CRC-8校验函数 (多项式0x07)
    
    Args:
        data: 字节数据
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

def bytes_to_rgb(seq: int, data: bytes, width: int, height: int) -> np.ndarray:
    
    # 用2字节表示seq，2字节表示数据长度（大端序），再拼接数据
    seq_bytes = seq.to_bytes(2, byteorder='big')
    len_bytes = len(data).to_bytes(2, byteorder='big')
    data = seq_bytes + len_bytes + data
    crc_checksum = crc8(data)
    data += f'\x{crc_checksum}'
    
    # 计算目标RGB矩阵所需总字节数
    total_pixels = width * height
    total_bytes_needed = total_pixels * 3
    
    # 如果数据不足，用0填充；如果超出，则截断
    if len(data) < total_bytes_needed:
        data += b'\x00' * (total_bytes_needed - len(data))
    else:
        data = data[:total_bytes_needed]
    
    # 将数据重塑为RGB三通道矩阵
    rgb_matrix = np.frombuffer(data, dtype=np.uint8).reshape(height, width, 3)
    print(rgb_matrix)
    
    # 将RGB矩阵转换为PIL图像对象
    image = Image.fromarray(rgb_matrix, mode='RGB')
    
    return image



if __name__ == "__main__":
    # 示例：将字节数据转为RGB图像并展示
    sample_data = b'SFIDu'
    seq = 8
    img = bytes_to_rgb(seq, sample_data, 8, 8)
    img.show()
