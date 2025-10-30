"""
测试 item.py 中的数据映射功能
"""
import pytest
import sys
import os

# 添加父目录到路径以便导入模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from item import buffs, buff_id_map, buff_name_map


class TestBuffsData:
    """测试 buffs 基础数据"""
    
    def test_buffs_structure(self):
        """测试 buffs 数据结构"""
        assert isinstance(buffs, list)
        assert len(buffs) > 0
        
        # 验证每个 buff 的结构
        for buff in buffs:
            assert isinstance(buff, dict)
            assert "id" in buff
            assert "name" in buff
            assert "icon" in buff
            assert "stock" in buff
            assert "remain_ms" in buff
            
            # 验证数据类型
            assert isinstance(buff["id"], int)
            assert isinstance(buff["name"], str)
            assert isinstance(buff["icon"], int)
            assert isinstance(buff["stock"], int)
            assert isinstance(buff["remain_ms"], int)
    
    def test_buffs_unique_ids(self):
        """测试 buffs 中的 id 唯一性"""
        ids = [buff["id"] for buff in buffs]
        assert len(ids) == len(set(ids)), "Buff IDs should be unique"
    
    def test_buffs_unique_names(self):
        """测试 buffs 中的 name 唯一性"""
        names = [buff["name"] for buff in buffs]
        assert len(names) == len(set(names)), "Buff names should be unique"
    
    def test_buffs_content(self):
        """测试 buffs 具体内容"""
        # 验证预期的测试数据存在
        buff_names = [buff["name"] for buff in buffs]
        assert "测试buff1" in buff_names
        assert "测试buff2" in buff_names
        
        # 验证具体数据
        buff1 = next(buff for buff in buffs if buff["name"] == "测试buff1")
        assert buff1["id"] == 1
        assert buff1["icon"] == 1
        assert buff1["stock"] == 0
        assert buff1["remain_ms"] == 0
        
        buff2 = next(buff for buff in buffs if buff["name"] == "测试buff2")
        assert buff2["id"] == 2
        assert buff2["icon"] == 2
        assert buff2["stock"] == 0
        assert buff2["remain_ms"] == 100


class TestBuffIdMap:
    """测试 buff_id_map 映射"""
    
    def test_buff_id_map_structure(self):
        """测试 buff_id_map 结构"""
        assert isinstance(buff_id_map, dict)
        assert len(buff_id_map) == len(buffs)
        
        # 验证所有 buff id 都在映射中
        for buff in buffs:
            assert buff["id"] in buff_id_map
    
    def test_buff_id_map_content(self):
        """测试 buff_id_map 内容正确性"""
        for buff in buffs:
            mapped_buff = buff_id_map[buff["id"]]
            assert mapped_buff == buff
            
            # 验证映射的 buff 包含所有必需字段
            assert mapped_buff["id"] == buff["id"]
            assert mapped_buff["name"] == buff["name"]
            assert mapped_buff["icon"] == buff["icon"]
            assert mapped_buff["stock"] == buff["stock"]
            assert mapped_buff["remain_ms"] == buff["remain_ms"]
    
    def test_buff_id_map_lookup(self):
        """测试通过 id 查找 buff"""
        # 测试存在的 id
        buff1 = buff_id_map.get(1)
        assert buff1 is not None
        assert buff1["name"] == "测试buff1"
        
        buff2 = buff_id_map.get(2)
        assert buff2 is not None
        assert buff2["name"] == "测试buff2"
        
        # 测试不存在的 id
        nonexistent = buff_id_map.get(999)
        assert nonexistent is None
    
    def test_buff_id_map_keys_are_integers(self):
        """测试 buff_id_map 的键都是整数"""
        for key in buff_id_map.keys():
            assert isinstance(key, int)


class TestBuffNameMap:
    """测试 buff_name_map 映射"""
    
    def test_buff_name_map_structure(self):
        """测试 buff_name_map 结构"""
        assert isinstance(buff_name_map, dict)
        assert len(buff_name_map) == len(buffs)
        
        # 验证所有 buff name 都在映射中
        for buff in buffs:
            assert buff["name"] in buff_name_map
    
    def test_buff_name_map_content(self):
        """测试 buff_name_map 内容正确性"""
        for buff in buffs:
            mapped_buff = buff_name_map[buff["name"]]
            assert mapped_buff == buff
            
            # 验证映射的 buff 包含所有必需字段
            assert mapped_buff["id"] == buff["id"]
            assert mapped_buff["name"] == buff["name"]
            assert mapped_buff["icon"] == buff["icon"]
            assert mapped_buff["stock"] == buff["stock"]
            assert mapped_buff["remain_ms"] == buff["remain_ms"]
    
    def test_buff_name_map_lookup(self):
        """测试通过名称查找 buff"""
        # 测试存在的名称
        buff1 = buff_name_map.get("测试buff1")
        assert buff1 is not None
        assert buff1["id"] == 1
        
        buff2 = buff_name_map.get("测试buff2")
        assert buff2 is not None
        assert buff2["id"] == 2
        
        # 测试不存在的名称
        nonexistent = buff_name_map.get("不存在的buff")
        assert nonexistent is None
    
    def test_buff_name_map_keys_are_strings(self):
        """测试 buff_name_map 的键都是字符串"""
        for key in buff_name_map.keys():
            assert isinstance(key, str)
    
    def test_buff_name_map_chinese_support(self):
        """测试 buff_name_map 支持中文名称"""
        # 验证中文名称能正确映射
        chinese_names = [name for name in buff_name_map.keys() if any('\u4e00' <= char <= '\u9fff' for char in name)]
        assert len(chinese_names) > 0, "Should have Chinese buff names"
        
        for name in chinese_names:
            buff = buff_name_map[name]
            assert buff["name"] == name


class TestMappingConsistency:
    """测试映射一致性"""
    
    def test_id_name_mapping_consistency(self):
        """测试 id 和 name 映射的一致性"""
        # 通过 id 和 name 获取的应该是同一个 buff
        for buff in buffs:
            buff_by_id = buff_id_map[buff["id"]]
            buff_by_name = buff_name_map[buff["name"]]
            
            assert buff_by_id == buff_by_name
            assert buff_by_id is buff_by_name  # 应该是同一个对象引用
    
    def test_mapping_completeness(self):
        """测试映射完整性"""
        # buff_id_map 应该包含所有 buff
        assert len(buff_id_map) == len(buffs)
        
        # buff_name_map 应该包含所有 buff
        assert len(buff_name_map) == len(buffs)
        
        # 每个 buff 都应该能通过 id 和 name 找到
        for buff in buffs:
            assert buff["id"] in buff_id_map
            assert buff["name"] in buff_name_map
    
    def test_no_duplicate_mappings(self):
        """测试没有重复映射"""
        # 每个 id 只能映射到一个 buff
        id_values = list(buff_id_map.values())
        assert len(id_values) == len(set(id(buff) for buff in id_values))
        
        # 每个 name 只能映射到一个 buff
        name_values = list(buff_name_map.values())
        assert len(name_values) == len(set(id(buff) for buff in name_values))


class TestBuffDataIntegration:
    """测试 buff 数据与其他模块的集成"""
    
    def test_buff_data_compatible_with_pydantic(self):
        """测试 buff 数据与 Pydantic 模型兼容"""
        from game_state import Buff
        
        # 每个 buff 数据都应该能创建有效的 Buff 实例
        for buff_data in buffs:
            try:
                buff_instance = Buff(**buff_data)
                assert buff_instance.id == buff_data["id"]
                assert buff_instance.name == buff_data["name"]
                assert buff_instance.icon == buff_data["icon"]
                assert buff_instance.stock == buff_data["stock"]
                assert buff_instance.remain_ms == buff_data["remain_ms"]
            except Exception as e:
                pytest.fail(f"Failed to create Buff instance from data {buff_data}: {e}")
    
    def test_buff_data_compatible_with_buff_state(self):
        """测试 buff 数据与 BuffState 兼容"""
        from state_manager import BuffState
        
        # 每个 buff 数据都应该能创建有效的 BuffState 实例
        for buff_data in buffs:
            try:
                buff_state = BuffState(**buff_data)
                assert buff_state.id == buff_data["id"]
                assert buff_state.name == buff_data["name"]
                
                # 测试 BuffState 特有的属性
                assert hasattr(buff_state, 'up')
                assert hasattr(buff_state, 'remains')
                assert isinstance(buff_state.up, bool)
                assert isinstance(buff_state.remains, int)
            except Exception as e:
                pytest.fail(f"Failed to create BuffState instance from data {buff_data}: {e}")


class TestBuffDataEdgeCases:
    """测试 buff 数据边界情况"""
    
    def test_empty_lookup(self):
        """测试空值查找"""
        assert buff_id_map.get(None) is None
        assert buff_name_map.get(None) is None
        assert buff_name_map.get("") is None
    
    def test_case_sensitive_name_lookup(self):
        """测试名称查找的大小写敏感性"""
        # 假设有 "测试buff1"
        if "测试buff1" in buff_name_map:
            assert buff_name_map.get("测试BUFF1") is None  # 大写应该找不到
            assert buff_name_map.get("测试buff1") is not None  # 原始大小写应该能找到
    
    def test_negative_id_lookup(self):
        """测试负数 id 查找"""
        assert buff_id_map.get(-1) is None
        assert buff_id_map.get(-999) is None
    
    def test_zero_values_handling(self):
        """测试零值处理"""
        # 查找是否有 stock 或 remain_ms 为 0 的 buff
        zero_stock_buffs = [buff for buff in buffs if buff["stock"] == 0]
        zero_remain_buffs = [buff for buff in buffs if buff["remain_ms"] == 0]
        
        # 这些 buff 应该仍然能正确映射
        for buff in zero_stock_buffs + zero_remain_buffs:
            assert buff_id_map[buff["id"]] == buff
            assert buff_name_map[buff["name"]] == buff


if __name__ == "__main__":
    pytest.main([__file__, "-v"])