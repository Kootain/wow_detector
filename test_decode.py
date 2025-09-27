#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试脚本：验证decode_matrix函数是否能正确解析visual_transmit.lua生成的数据格式
"""

import numpy as np
from PIL import Image
from client import decode_matrix, crc8

def simulate_lua_frame(payload_bytes, sequence=1, use_crc=True):
    """
    模拟visual_transmit.lua的SendBytes方法生成的数据格式
    格式: [0xAA, sequence, length, ...payload_bytes, checksum]
    """
    frame_data = [0xAA, sequence, len(payload_bytes)] + list(payload_bytes)
    
    if use_crc:
        checksum = crc8(frame_data)
    else:
        checksum = 0
        for v in frame_data:
            checksum ^= v
    
    frame_data.append(checksum)
    return frame_data

def create_test_image(frame_data, grid_size=8, cell_px=4):
    """
    创建测试图像，将帧数据编码为RGB像素
    """
    # 计算总的字节容量
    total_blocks = grid_size * grid_size
    total_byte_capacity = total_blocks * 3
    
    # 创建完整的字节数组，不足的部分用0填充
    full_bytes = [0] * total_byte_capacity
    for i, byte_val in enumerate(frame_data):
        if i < total_byte_capacity:
            full_bytes[i] = byte_val
    
    # 创建图像
    img_size = grid_size * cell_px
    img_array = np.zeros((img_size, img_size, 3), dtype=np.uint8)
    
    for block_idx in range(total_blocks):
        r_byte = full_bytes[block_idx * 3]
        g_byte = full_bytes[block_idx * 3 + 1] 
        b_byte = full_bytes[block_idx * 3 + 2]
        
        row = block_idx // grid_size
        col = block_idx % grid_size
        
        # 填充整个块区域
        y_start = row * cell_px
        y_end = y_start + cell_px
        x_start = col * cell_px
        x_end = x_start + cell_px
        
        img_array[y_start:y_end, x_start:x_end, 0] = r_byte
        img_array[y_start:y_end, x_start:x_end, 1] = g_byte
        img_array[y_start:y_end, x_start:x_end, 2] = b_byte
    
    return Image.fromarray(img_array)

def test_decode():
    """
    测试decode_matrix函数
    """
    print("=== 测试decode_matrix函数 ===")
    
    # 测试用例1: 简单的载荷数据
    test_payload = [0x01, 0x04, 0xFF, 0x00, 0x80, 0x7F]  # 模拟一些状态数据
    print(f"\n测试用例1: 载荷数据 = {test_payload}")
    
    # 生成帧数据
    frame_data = simulate_lua_frame(test_payload, sequence=42, use_crc=True)
    print(f"生成的帧数据: {frame_data}")
    
    # 创建测试图像
    test_img = create_test_image(frame_data)
    
    # 解码测试
    seq, payload, ok = decode_matrix(test_img, grid_size=8, cell_px=4, use_crc=True)
    
    print(f"解码结果:")
    print(f"  序列号: {seq}")
    print(f"  载荷: {list(payload) if payload else None}")
    print(f"  校验通过: {ok}")
    
    # 验证结果
    if seq == 42 and list(payload) == test_payload and ok:
        print("✅ 测试用例1 通过!")
    else:
        print("❌ 测试用例1 失败!")
        print(f"  期望序列号: 42, 实际: {seq}")
        print(f"  期望载荷: {test_payload}, 实际: {list(payload) if payload else None}")
        print(f"  期望校验通过: True, 实际: {ok}")
    
    # 测试用例2: 空载荷
    print(f"\n测试用例2: 空载荷")
    empty_payload = []
    frame_data2 = simulate_lua_frame(empty_payload, sequence=1, use_crc=True)
    test_img2 = create_test_image(frame_data2)
    
    seq2, payload2, ok2 = decode_matrix(test_img2, grid_size=8, cell_px=4, use_crc=True)
    print(f"解码结果: 序列号={seq2}, 载荷长度={len(payload2) if payload2 else 0}, 校验={ok2}")
    
    if seq2 == 1 and len(payload2) == 0 and ok2:
        print("✅ 测试用例2 通过!")
    else:
        print("❌ 测试用例2 失败!")
    
    # 测试用例3: 错误的帧头
    print(f"\n测试用例3: 错误的帧头")
    bad_frame = [0xBB, 1, 2, 0x01, 0x02, 0x00]  # 错误的帧头标记
    test_img3 = create_test_image(bad_frame)
    
    seq3, payload3, ok3 = decode_matrix(test_img3, grid_size=8, cell_px=4, use_crc=True)
    print(f"解码结果: 序列号={seq3}, 载荷={payload3}, 校验={ok3}")
    
    if seq3 is None and payload3 is None and ok3 == False:
        print("✅ 测试用例3 通过! (正确拒绝了错误的帧头)")
    else:
        print("❌ 测试用例3 失败!")

if __name__ == "__main__":
    test_decode()