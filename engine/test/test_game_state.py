"""
测试 game_state.py 中的数据模型
"""
import pytest
from pydantic import ValidationError
import sys
import os

# 添加父目录到路径以便导入模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from game_state import Item, Buff, Action, BaseResource, MagaResouce, MagicResouce, CoolDown


class TestItem:
    """测试 Item 基础模型"""
    
    def test_item_creation(self):
        """测试 Item 正常创建"""
        item = Item(name="测试物品", id=123, icon=456)
        assert item.name == "测试物品"
        assert item.id == 123
        assert item.icon == 456
    
    def test_item_hash(self):
        """测试 Item 哈希功能"""
        item1 = Item(name="物品1", id=123, icon=456)
        item2 = Item(name="物品2", id=123, icon=789)  # 相同 id
        item3 = Item(name="物品3", id=124, icon=456)  # 不同 id
        
        assert hash(item1) == hash(item2)  # 相同 id 应该有相同哈希
        assert hash(item1) != hash(item3)  # 不同 id 应该有不同哈希
    
    def test_item_equality(self):
        """测试 Item 相等性比较"""
        item1 = Item(name="物品1", id=123, icon=456)
        item2 = Item(name="物品2", id=123, icon=789)  # 相同 id
        item3 = Item(name="物品3", id=124, icon=456)  # 不同 id
        
        assert item1 == item2  # 相同 id 应该相等
        assert item1 != item3  # 不同 id 应该不相等
    
    def test_item_validation_error(self):
        """测试 Item 验证错误"""
        with pytest.raises(ValidationError):
            Item(name="测试", id="invalid_id", icon=456)  # id 应该是 int
        
        with pytest.raises(ValidationError):
            Item(name=123, id=123, icon=456)  # name 应该是 str
    
    def test_item_missing_fields(self):
        """测试 Item 缺少必需字段"""
        with pytest.raises(ValidationError):
            Item(name="测试")  # 缺少 id 和 icon
        
        with pytest.raises(ValidationError):
            Item(id=123, icon=456)  # 缺少 name


class TestBuff:
    """测试 Buff 模型"""
    
    def test_buff_creation(self):
        """测试 Buff 正常创建"""
        buff = Buff(name="敏锐直觉", id=123, icon=456, remain_ms=5000, stock=2)
        assert buff.name == "敏锐直觉"
        assert buff.id == 123
        assert buff.icon == 456
        assert buff.remain_ms == 5000
        assert buff.stock == 2
    
    def test_buff_inheritance(self):
        """测试 Buff 继承 Item 的功能"""
        buff1 = Buff(name="buff1", id=123, icon=456, remain_ms=1000, stock=1)
        buff2 = Buff(name="buff2", id=123, icon=789, remain_ms=2000, stock=2)
        
        # 继承 Item 的哈希和相等性
        assert hash(buff1) == hash(buff2)
        assert buff1 == buff2
    
    def test_buff_validation(self):
        """测试 Buff 字段验证"""
        with pytest.raises(ValidationError):
            Buff(name="测试", id=123, icon=456, remain_ms="invalid", stock=1)
        
        with pytest.raises(ValidationError):
            Buff(name="测试", id=123, icon=456, remain_ms=1000, stock="invalid")
    
    def test_buff_set_operations(self):
        """测试 Buff 在集合中的操作"""
        buff1 = Buff(name="buff1", id=123, icon=456, remain_ms=1000, stock=1)
        buff2 = Buff(name="buff2", id=123, icon=789, remain_ms=2000, stock=2)
        buff3 = Buff(name="buff3", id=124, icon=456, remain_ms=1000, stock=1)
        
        buff_set = {buff1, buff2, buff3}
        assert len(buff_set) == 2  # buff1 和 buff2 有相同 id，应该只有一个


class TestAction:
    """测试 Action 模型"""
    
    def test_action_creation(self):
        """测试 Action 正常创建"""
        action = Action(
            name="火球术", 
            id=133, 
            icon=789, 
            start_ms=1000, 
            end_ms=3000, 
            type="cast"
        )
        assert action.name == "火球术"
        assert action.id == 133
        assert action.icon == 789
        assert action.start_ms == 1000
        assert action.end_ms == 3000
        assert action.type == "cast"
    
    def test_action_type_validation(self):
        """测试 Action type 字段的字面量验证"""
        # 有效的 type 值
        action1 = Action(name="技能1", id=1, icon=1, start_ms=0, end_ms=1000, type="cast")
        action2 = Action(name="技能2", id=2, icon=2, start_ms=0, end_ms=1000, type="channel")
        
        assert action1.type == "cast"
        assert action2.type == "channel"
        
        # 无效的 type 值
        with pytest.raises(ValidationError):
            Action(name="技能", id=1, icon=1, start_ms=0, end_ms=1000, type="invalid")
    
    def test_action_time_validation(self):
        """测试 Action 时间字段验证"""
        with pytest.raises(ValidationError):
            Action(name="技能", id=1, icon=1, start_ms="invalid", end_ms=1000, type="cast")


class TestBaseResource:
    """测试 BaseResource 模型"""
    
    def test_base_resource_creation(self):
        """测试 BaseResource 正常创建"""
        resource = BaseResource(health=100, health_max=150)
        assert resource.health == 100
        assert resource.health_max == 150
    
    def test_base_resource_validation(self):
        """测试 BaseResource 验证"""
        with pytest.raises(ValidationError):
            BaseResource(health="invalid", health_max=150)
        
        with pytest.raises(ValidationError):
            BaseResource(health=100)  # 缺少 health_max


class TestMagaResouce:
    """测试 MagaResouce 模型"""
    
    def test_maga_resource_creation(self):
        """测试 MagaResouce 正常创建"""
        resource = MagaResouce(mega=50, mega_max=100)
        assert resource.mega == 50
        assert resource.mega_max == 100
    
    def test_maga_resource_validation(self):
        """测试 MagaResouce 验证"""
        with pytest.raises(ValidationError):
            MagaResouce(mega="invalid", mega_max=100)


class TestMagicResouce:
    """测试 MagicResouce 多重继承模型"""
    
    def test_magic_resource_creation(self):
        """测试 MagicResouce 正常创建"""
        resource = MagicResouce(
            health=80,
            health_max=100,
            mega=60,
            mega_max=100,
            xx=5
        )
        assert resource.health == 80
        assert resource.health_max == 100
        assert resource.mega == 60
        assert resource.mega_max == 100
        assert resource.xx == 5
    
    def test_magic_resource_inheritance(self):
        """测试 MagicResouce 继承所有父类字段"""
        resource = MagicResouce(
            health=80, health_max=100,
            mega=60, mega_max=100,
            xx=5
        )
        
        # 应该包含 BaseResource 的字段
        assert hasattr(resource, 'health')
        assert hasattr(resource, 'health_max')
        
        # 应该包含 MagaResouce 的字段
        assert hasattr(resource, 'mega')
        assert hasattr(resource, 'mega_max')
        
        # 应该包含自己的字段
        assert hasattr(resource, 'xx')
    
    def test_magic_resource_validation(self):
        """测试 MagicResouce 所有字段验证"""
        with pytest.raises(ValidationError):
            MagicResouce(
                health="invalid", health_max=100,
                mega=60, mega_max=100,
                xx=5
            )
        
        with pytest.raises(ValidationError):
            MagicResouce(
                health=80, health_max=100,
                mega=60, mega_max=100
                # 缺少 xx 字段
            )


class TestCoolDown:
    """测试 CoolDown 模型"""
    
    def test_cooldown_creation(self):
        """测试 CoolDown 正常创建"""
        cd = CoolDown(name="火球术", id=133, icon=789, remain_ms=2000)
        assert cd.name == "火球术"
        assert cd.id == 133
        assert cd.icon == 789
        assert cd.remain_ms == 2000
    
    def test_cooldown_inheritance(self):
        """测试 CoolDown 继承 Item 功能"""
        cd1 = CoolDown(name="技能1", id=123, icon=456, remain_ms=1000)
        cd2 = CoolDown(name="技能2", id=123, icon=789, remain_ms=2000)
        
        # 继承 Item 的相等性
        assert cd1 == cd2
    
    def test_cooldown_validation(self):
        """测试 CoolDown 验证"""
        with pytest.raises(ValidationError):
            CoolDown(name="技能", id=123, icon=456, remain_ms="invalid")


class TestModelSerialization:
    """测试模型序列化功能"""
    
    def test_item_serialization(self):
        """测试 Item 序列化"""
        item = Item(name="测试物品", id=123, icon=456)
        data = item.model_dump()
        
        assert data == {
            "name": "测试物品",
            "id": 123,
            "icon": 456
        }
        
        # 测试反序列化
        new_item = Item.model_validate(data)
        assert new_item == item
    
    def test_buff_serialization(self):
        """测试 Buff 序列化"""
        buff = Buff(name="敏锐直觉", id=123, icon=456, remain_ms=5000, stock=2)
        data = buff.model_dump()
        
        expected = {
            "name": "敏锐直觉",
            "id": 123,
            "icon": 456,
            "remain_ms": 5000,
            "stock": 2
        }
        assert data == expected
        
        # 测试反序列化
        new_buff = Buff.model_validate(data)
        assert new_buff == buff
    
    def test_complex_model_serialization(self):
        """测试复杂模型序列化"""
        resource = MagicResouce(
            health=80, health_max=100,
            mega=60, mega_max=100,
            xx=5
        )
        data = resource.model_dump()
        
        expected = {
            "health": 80,
            "health_max": 100,
            "mega": 60,
            "mega_max": 100,
            "xx": 5
        }
        assert data == expected
        
        # 测试反序列化
        new_resource = MagicResouce.model_validate(data)
        assert new_resource.health == resource.health
        assert new_resource.mega == resource.mega
        assert new_resource.xx == resource.xx


if __name__ == "__main__":
    pytest.main([__file__, "-v"])