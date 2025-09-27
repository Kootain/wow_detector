-- util.lua - 工具函数库
-- 包含bytes转RGB图像的功能和CRC8校验

local util = {}

-- CRC-8校验函数 (多项式0x07)
function util.crc8(data)
    local crc = 0
    for i = 1, #data do
        crc = crc ~ data[i]  -- XOR操作
        for j = 1, 8 do
            if (crc & 0x80) ~= 0 then
                crc = ((crc << 1) ~ 0x07) & 0xFF
            else
                crc = (crc << 1) & 0xFF
            end
        end
    end
    return crc
end

-- XOR校验函数
function util.xor_checksum(data)
    local checksum = 0
    for i = 1, #data do
        checksum = checksum ~ data[i]  -- XOR操作
    end
    return checksum
end

-- 限制数值范围
function util.clamp(value, min, max)
    if value < min then return min end
    if value > max then return max end
    return value
end

-- 将bytes数组转换为RGB图像数据
-- @param bytes: 字节数组 (0-255的整数)
-- @param width: 图像宽度(像素块数)
-- @param height: 图像高度(像素块数)
-- @param use_crc: 是否使用CRC8校验 (默认true)
-- @return: RGB数据矩阵 [row][col] = {r, g, b}
function util.bytes_to_rgb(bytes, width, height, use_crc)
    if use_crc == nil then use_crc = true end
    
    -- 构建帧数据: [长度][...bytes][校验和]
    local frame = {}
    frame[1] = #bytes  -- 长度字节
    
    -- 添加原始数据
    for i = 1, #bytes do
        frame[#frame + 1] = bytes[i]
    end
    
    -- 计算并添加校验和
    local checksum
    if use_crc then
        checksum = util.crc8(frame)
    else
        checksum = util.xor_checksum(frame)
    end
    frame[#frame + 1] = checksum
    
    -- 计算总容量
    local total_blocks = width * height
    local total_capacity = total_blocks * 3  -- 每个块3个字节(RGB)
    
    -- 创建完整的字节数组，不足部分填充0
    local full_data = {}
    for i = 1, total_capacity do
        if i <= #frame then
            full_data[i] = util.clamp(frame[i], 0, 255)
        else
            full_data[i] = 0
        end
    end
    
    -- 转换为RGB矩阵
    local rgb_matrix = {}
    for row = 1, height do
        rgb_matrix[row] = {}
        for col = 1, width do
            local block_index = (row - 1) * width + col
            local byte_offset = (block_index - 1) * 3
            
            local r = full_data[byte_offset + 1] or 0
            local g = full_data[byte_offset + 2] or 0
            local b = full_data[byte_offset + 3] or 0
            
            rgb_matrix[row][col] = {r, g, b}
        end
    end
    
    return rgb_matrix, #frame  -- 返回RGB矩阵和实际帧长度
end

-- 打印RGB矩阵 (调试用)
function util.print_rgb_matrix(matrix, title)
    if title then
        print("=== " .. title .. " ===")
    end
    
    for row = 1, #matrix do
        local line = ""
        for col = 1, #matrix[row] do
            local rgb = matrix[row][col]
            line = line .. string.format("(%d,%d,%d) ", rgb[1], rgb[2], rgb[3])
        end
        print("Row " .. row .. ": " .. line)
    end
end

-- 测试函数
function util.test_bytes_to_rgb()
    print("\n=== 测试 bytes_to_rgb 函数 ===")
    
    -- 测试用例1: 简单数据
    local test_bytes = {1, 2, 3, 4, 5}
    local matrix, frame_len = util.bytes_to_rgb(test_bytes, 4, 4, true)
    
    print("测试数据: {1, 2, 3, 4, 5}")
    print("帧长度: " .. frame_len)
    util.print_rgb_matrix(matrix, "RGB矩阵")
    
    -- 测试用例2: 较长数据
    local long_bytes = {}
    for i = 1, 20 do
        long_bytes[i] = (i - 1) % 256
    end
    
    local matrix2, frame_len2 = util.bytes_to_rgb(long_bytes, 8, 8, true)
    print("\n长数据测试 (20字节)")
    print("帧长度: " .. frame_len2)
    
    -- 只打印前几行
    for row = 1, math.min(3, #matrix2) do
        local line = ""
        for col = 1, math.min(4, #matrix2[row]) do
            local rgb = matrix2[row][col]
            line = line .. string.format("(%d,%d,%d) ", rgb[1], rgb[2], rgb[3])
        end
        print("Row " .. row .. ": " .. line .. "...")
    end
end

return util