"""
测试 state_manager.py 中的核心功能
"""
import pytest
from pydantic import ValidationError
import sys
import os

# 添加父目录到路径以便导入模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from state_manager import Identifier, BuffState, BuffManager
from game_state import Buff
from item import buff_id_map, buff_name_map


class TestIdentifier:
    """测试 Identifier 基础功能"""
    
    def test_identifier_register_decorator(self):
        """测试 register 装饰器基本功能"""
        class TestClass(Identifier):
            @Identifier.register(str)
            def test_method(self):
                return "test"
            
            @property
            @Identifier.register(int)
            def test_property(self):
                return 42
        
        obj = TestClass()
        
        # 测试方法注册
        assert "test_method" in obj.registered_methods()
        assert "test_property" in obj.registered_methods()
        
        # 测试 valid 方法返回类型
        assert obj.valid("test_method") == str
        assert obj.valid("test_property") == int
        assert obj.valid("nonexistent") is None
    
    def test_identifier_depends_on(self):
        """测试 depends_on 依赖关系"""
        class TestClass(Identifier):
            @Identifier.register(bool, depends_on=["field1", "field2"])
            def dependent_method(self):
                return True
            
            @property
            @Identifier.register(int, depends_on=["field1"])
            def dependent_property(self):
                return self.field1 * 2
        
        obj = TestClass()
        
        # 测试依赖关系记录
        assert hasattr(TestClass, "_registered_method_depends_on")
        assert TestClass._registered_method_depends_on["dependent_method"] == ["field1", "field2"]
        assert TestClass._registered_method_depends_on["dependent_property"] == ["field1"]
        
        # 测试反向依赖关系
        assert hasattr(TestClass, "_reverse_depends_on")
        assert "dependent_method" in TestClass._reverse_depends_on["field1"]
        assert "dependent_property" in TestClass._reverse_depends_on["field1"]
        assert "dependent_method" in TestClass._reverse_depends_on["field2"]
    
    def test_identifier_property_decorator_order(self):
        """测试装饰器顺序兼容性"""
        class TestClass(Identifier):
            # @property 在前
            @property
            @Identifier.register(str)
            def prop1(self):
                return "prop1"
            
            # @Identifier.register 在前
            @Identifier.register(str)
            @property
            def prop2(self):
                return "prop2"
        
        obj = TestClass()
        
        assert "prop1" in obj.registered_methods()
        assert "prop2" in obj.registered_methods()
        assert obj.valid("prop1") == str
        assert obj.valid("prop2") == str


class TestBuffState:
    """测试 BuffState 功能"""
    
    def test_buff_state_creation(self):
        """测试 BuffState 创建"""
        buff_state = BuffState(
            name="敏锐直觉",
            id=123,
            icon=456,
            remain_ms=5000,
            stock=2
        )
        
        assert buff_state.name == "敏锐直觉"
        assert buff_state.id == 123
        assert buff_state.remain_ms == 5000
        assert buff_state.stock == 2
    
    def test_buff_state_registered_properties(self):
        """测试 BuffState 注册的属性"""
        buff_state = BuffState(
            name="测试buff",
            id=123,
            icon=456,
            remain_ms=5000,
            stock=2
        )
        
        # 测试注册的方法
        registered = buff_state.registered_methods()
        assert "up" in registered
        assert "remains" in registered
        assert "stock" in registered
        
        # 测试返回类型
        assert buff_state.valid("up") == bool
        assert buff_state.valid("remains") == int
        assert buff_state.valid("stock") == int
    
    def test_buff_state_up_property(self):
        """测试 up 属性逻辑"""
        # 有库存的情况
        buff1 = BuffState(name="buff1", id=1, icon=1, remain_ms=0, stock=2)
        assert buff1.up is True
        
        # 有剩余时间的情况
        buff2 = BuffState(name="buff2", id=2, icon=2, remain_ms=5000, stock=0)
        assert buff2.up is True
        
        # 既有库存又有剩余时间
        buff3 = BuffState(name="buff3", id=3, icon=3, remain_ms=5000, stock=2)
        assert buff3.up is True
        
        # 既没有库存也没有剩余时间
        buff4 = BuffState(name="buff4", id=4, icon=4, remain_ms=0, stock=0)
        assert buff4.up is False
    
    def test_buff_state_remains_property(self):
        """测试 remains 属性"""
        buff = BuffState(name="buff", id=1, icon=1, remain_ms=3000, stock=1)
        assert buff.remains == 3000
    
    def test_buff_state_stock_property(self):
        """测试 stock 属性"""
        buff = BuffState(name="buff", id=1, icon=1, remain_ms=1000, stock=5)
        assert buff.stock == 5
    
    def test_buff_state_update_method(self):
        """测试 BuffState 的 update 方法"""
        buff_state = BuffState(
            name="测试buff",
            id=123,
            icon=456,
            remain_ms=1000,
            stock=1
        )
        
        # 创建新的 Buff 用于更新
        new_buff = Buff(
            name="测试buff",
            id=123,
            icon=456,
            remain_ms=2000,
            stock=3
        )
        
        # 执行更新
        result = buff_state.update(new_buff)
        
        # 验证更新结果
        assert buff_state.remain_ms == 2000
        assert buff_state.stock == 3
        
        # 验证返回的变更信息
        assert "changes" in result
        assert "effects" in result
        
        # 验证变更记录
        changes = result["changes"]
        assert "remain_ms" in changes
        assert "stock" in changes
        assert changes["remain_ms"] == (1000, 2000)
        assert changes["stock"] == (1, 3)
        
        # 验证影响的属性
        effects = result["effects"]
        assert "up" in effects  # up 依赖于 stock 和 remain_ms
        assert "remains" in effects  # remains 依赖于 remain_ms
    
    def test_buff_state_update_no_changes(self):
        """测试 BuffState update 方法无变更情况"""
        buff_state = BuffState(
            name="测试buff",
            id=123,
            icon=456,
            remain_ms=1000,
            stock=1
        )
        
        # 创建相同数据的 Buff
        same_buff = Buff(
            name="测试buff",
            id=123,
            icon=456,
            remain_ms=1000,
            stock=1
        )
        
        result = buff_state.update(same_buff)
        
        # 应该没有变更
        assert result["changes"] == {}
        assert result["effects"] == []
    
    def test_buff_state_update_invalid_input(self):
        """测试 BuffState update 方法无效输入"""
        buff_state = BuffState(
            name="测试buff",
            id=123,
            icon=456,
            remain_ms=1000,
            stock=1
        )
        
        # 传入非 BaseModel 实例
        with pytest.raises(TypeError):
            buff_state.update("invalid_input")
        
        with pytest.raises(TypeError):
            buff_state.update(123)


class TestBuffManager:
    """测试 BuffManager 功能"""
    
    def test_buff_manager_creation(self):
        """测试 BuffManager 创建"""
        manager = BuffManager()
        assert isinstance(manager.buffs, set)
        assert len(manager.buffs) == 0
    
    def test_buff_manager_id_parsing(self):
        """测试 BuffManager _id 方法"""
        manager = BuffManager()
        
        # 测试 id: 前缀
        assert manager._id("id:123") == 123
        assert isinstance(manager._id("id:123"), int)
        
        # 测试普通字符串
        assert manager._id("测试buff") == "测试buff"
        assert isinstance(manager._id("测试buff"), str)
    
    def test_buff_manager_update_add_buffs(self):
        """测试 BuffManager 添加 buff"""
        manager = BuffManager()
        
        # 添加新的 buff
        new_buffs = {
            Buff(name="buff1", id=1, icon=1, remain_ms=1000, stock=1),
            Buff(name="buff2", id=2, icon=2, remain_ms=2000, stock=2)
        }
        
        result = manager.update(new_buffs)
        
        # 验证返回结果结构
        assert "effects" in result
        assert "changes" in result
        assert isinstance(result["effects"], set)
        assert isinstance(result["changes"], dict)
        
        # 验证 buff 被添加到管理器中
        assert len(manager.buffs) == 2
        
        # 验证可以通过 ID 和名称访问 buff
        assert manager.__getattr__("id:1").name == "buff1"
        assert manager.__getattr__("buff2").id == 2

    def test_buff_manager_update_remove_buffs(self):
        """测试 BuffManager 移除 buff"""
        manager = BuffManager()
        
        # 先添加一些 buff
        initial_buffs = {
            Buff(name="buff1", id=1, icon=1, remain_ms=1000, stock=1),
            Buff(name="buff2", id=2, icon=2, remain_ms=2000, stock=2),
            Buff(name="buff3", id=3, icon=3, remain_ms=3000, stock=3)
        }
        manager.update(initial_buffs)
        assert len(manager.buffs) == 3
        
        # 移除一个 buff（只保留两个）
        remaining_buffs = {
            Buff(name="buff1", id=1, icon=1, remain_ms=1000, stock=1),
            Buff(name="buff3", id=3, icon=3, remain_ms=3000, stock=3)
        }
        
        result = manager.update(remaining_buffs)
        
        # 验证返回结果结构
        assert "effects" in result
        assert "changes" in result
        
        # 验证 buff 被移除
        assert len(manager.buffs) == 2
        
        # 验证移除的 buff 无法访问
        with pytest.raises(AttributeError):
            manager.__getattr__("id:2")

    def test_buff_manager_update_modify_buffs(self):
        """测试 BuffManager 修改 buff"""
        manager = BuffManager()
        
        # 先添加一个 buff
        initial_buffs = {
            Buff(name="buff1", id=1, icon=1, remain_ms=1000, stock=1)
        }
        manager.update(initial_buffs)
        
        # 修改 buff 的属性
        modified_buffs = {
            Buff(name="buff1", id=1, icon=1, remain_ms=2000, stock=3)
        }
        
        result = manager.update(modified_buffs)
        
        # 验证返回结果结构
        assert "effects" in result
        assert "changes" in result
        
        # 验证 buff 数量不变
        assert len(manager.buffs) == 1
        
        # 验证 buff 属性被更新
        buff = manager.__getattr__("id:1")
        assert buff.remain_ms == 2000
        assert buff.stock == 3
    
    def test_buff_manager_valid_method(self):
        """测试 BuffManager valid 方法"""
        manager = BuffManager()
        
        # 测试 id 格式
        result = manager.valid("id:1")
        assert result == (True, BuffState)  # buff_id_map 中有 id=1
        
        result = manager.valid("id:999")
        assert result == (False, BuffState)  # buff_id_map 中没有 id=999
        
        # 测试名称格式
        result = manager.valid("测试buff1")
        assert result == (True, BuffState)  # buff_name_map 中有这个名称
        
        result = manager.valid("不存在的buff")
        assert result == (False, BuffState)  # buff_name_map 中没有这个名称
    
    def test_buff_manager_getattr_by_id(self):
        """测试 BuffManager 通过 id 获取 buff"""
        manager = BuffManager()
        
        # 添加 buff
        buffs = {
            Buff(name="buff1", id=123, icon=1, remain_ms=1000, stock=1),
            Buff(name="buff2", id=456, icon=2, remain_ms=2000, stock=2)
        }
        manager.update(buffs)
        
        # 通过 id 获取
        buff = getattr(manager, "id:123")
        assert buff.id == 123
        assert buff.name == "buff1"
        
        # 获取不存在的 id
        with pytest.raises(AttributeError):
            getattr(manager, "id:999")
    
    def test_buff_manager_getattr_by_name(self):
        """测试 BuffManager 通过名称获取 buff"""
        manager = BuffManager()
        
        # 添加 buff
        buffs = {
            Buff(name="敏锐直觉", id=123, icon=1, remain_ms=1000, stock=1),
            Buff(name="火焰护盾", id=456, icon=2, remain_ms=2000, stock=2)
        }
        manager.update(buffs)
        
        # 通过名称获取
        buff = getattr(manager, "敏锐直觉")
        assert buff.name == "敏锐直觉"
        assert buff.id == 123
        
        # 获取不存在的名称
        with pytest.raises(AttributeError):
            getattr(manager, "不存在的buff")
    
    def test_buff_manager_complex_scenario(self):
        """测试 BuffManager 复杂场景"""
        manager = BuffManager()
        
        # 第一次更新：添加三个 buff
        buffs1 = {
            Buff(name="buff1", id=1, icon=1, remain_ms=1000, stock=1),
            Buff(name="buff2", id=2, icon=2, remain_ms=2000, stock=2),
            Buff(name="buff3", id=3, icon=3, remain_ms=3000, stock=3)
        }
        result1 = manager.update(buffs1)
        assert "effects" in result1
        assert len(manager.buffs) == 3
        
        # 第二次更新：移除一个，修改一个，添加一个
        buffs2 = {
            Buff(name="buff1", id=1, icon=1, remain_ms=1500, stock=2),  # 修改
            Buff(name="buff3", id=3, icon=3, remain_ms=3000, stock=3),  # 保持不变
            Buff(name="buff4", id=4, icon=4, remain_ms=4000, stock=4)   # 新增
        }
        result2 = manager.update(buffs2)
        assert "effects" in result2
        assert len(manager.buffs) == 3
        
        # 验证最终状态
        assert manager.__getattr__("id:1").remain_ms == 1500
        assert manager.__getattr__("id:1").stock == 2
        assert manager.__getattr__("id:3").remain_ms == 3000
        assert manager.__getattr__("id:4").remain_ms == 4000
        
        # 验证 buff2 被移除
        with pytest.raises(AttributeError):
            manager.__getattr__("id:2")


class TestIdentifierAutoUpdate:
    """测试 Identifier 自动添加的 update 方法"""
    
    def test_auto_update_method_added(self):
        """测试自动添加 update 方法"""
        class TestModel(Identifier):
            def __init__(self, value):
                self.value = value
        
        obj = TestModel(10)
        
        # 应该自动有 update 方法
        assert hasattr(obj, 'update')
        assert callable(obj.update)
    
    def test_auto_update_method_not_override_existing(self):
        """测试不会覆盖已存在的 update 方法"""
        class TestModel(Identifier):
            def __init__(self, value):
                self.value = value
            
            def update(self, new_value):
                return "custom_update"
        
        obj = TestModel(10)
        
        # 应该使用自定义的 update 方法
        result = obj.update("test")
        assert result == "custom_update"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])