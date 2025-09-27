def crc8(data: bytes, poly: int = 0x07) -> int:
    """
    计算CRC8校验值
    :param data: 待校验的字节数据
    :param poly: 生成多项式，默认0x07 (x^8 + x^2 + x + 1)
    :return: 8位CRC校验值
    """
    crc = 0x00  # 初始值
    for byte in data:
        crc ^= byte  # 异或输入字节
        for _ in range(8):  # 处理每个位
            if crc & 0x80:  # 最高位为1
                crc = (crc << 1) ^ poly
            else:  # 最高位为0
                crc <<= 1
            crc &= 0xFF  # 保持为8位
    return crc

if __name__ == '__main__':
    data = b'123456789'*50
    crc = crc8(data)
    print(f'CRC8({data}) = {crc:02X}')