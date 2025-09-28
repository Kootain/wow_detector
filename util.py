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


def rgb_to_bytes(flat_bytes: bytes) -> Tuple[int, bytes, bool]:
    seq_id = int.from_bytes(flat_bytes[:2], byteorder='big')
    data_len = int.from_bytes(flat_bytes[2:4], byteorder='big')
    
    checksum = crc8(flat_bytes[:data_len+4])
    given = flat_bytes[data_len+4:data_len+5]
    return seq_id, flat_bytes[4:data_len+4], bytes([checksum]) == given


def bytes_to_rgb(seq: int, data: bytes, width: int, height: int) -> np.ndarray:
    
    seq_bytes = seq.to_bytes(2, byteorder='big')
    len_bytes = len(data).to_bytes(2, byteorder='big')
    data = seq_bytes + len_bytes + data
    crc_checksum = crc8(data)
    data += bytes([crc_checksum])

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
    sample_data = b'5fUdw'
    seq = 169
    img = bytes_to_rgb(seq, sample_data, 8, 8)
    img.show()
