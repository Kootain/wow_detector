"""
pytest 配置文件

提供测试用的 fixtures 和配置
"""
import pytest
import sys
import os

# 添加父目录到 Python 路径，确保可以导入 engine 模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from game_state import Item, Buff, Action, BaseResource, MagaResouce, MagicResouce, CoolDown
from state_manager import Identifier, BuffState, BuffManager


@pytest.fixture
def sample_item():
    """提供示例 Item 实例"""
    return Item(name="测试物品", id=100, icon=200)


@pytest.fixture
def sample_buff():
    """提供示例 Buff 实例"""
    return Buff(
        name="测试buff",
        id=101,
        icon=201,
        remain_ms=5000,
        stock=2
    )


@pytest.fixture
def sample_buff_state():
    """提供示例 BuffState 实例"""
    return BuffState(
        name="测试buff状态",
        id=102,
        icon=202,
        remain_ms=3000,
        stock=1
    )


@pytest.fixture
def sample_action():
    """提供示例 Action 实例"""
    return Action(
        name="火球术",
        id=103,
        icon=203,
        start_ms=1000,
        end_ms=3000,
        type="cast"
    )


@pytest.fixture
def sample_cooldown():
    """提供示例 CoolDown 实例"""
    return CoolDown(
        name="冰霜新星",
        id=104,
        icon=204,
        remain_ms=8000
    )


@pytest.fixture
def sample_base_resource():
    """提供示例 BaseResource 实例"""
    return BaseResource(health=80, health_max=100)


@pytest.fixture
def sample_maga_resource():
    """提供示例 MagaResouce 实例"""
    return MagaResouce(mega=60, mega_max=100)


@pytest.fixture
def sample_magic_resource():
    """提供示例 MagicResouce 实例"""
    return MagicResouce(
        health=90,
        health_max=100,
        mega=70,
        mega_max=100,
        xx=5
    )


@pytest.fixture
def buff_manager():
    """提供空的 BuffManager 实例"""
    return BuffManager()


@pytest.fixture
def buff_manager_with_data():
    """提供包含测试数据的 BuffManager 实例"""
    manager = BuffManager()
    
    # 添加一些测试 buff
    test_buffs = {
        Buff(name="buff1", id=1, icon=1, remain_ms=1000, stock=1),
        Buff(name="buff2", id=2, icon=2, remain_ms=2000, stock=2),
        Buff(name="buff3", id=3, icon=3, remain_ms=0, stock=0)  # 已过期的 buff
    }
    
    manager.update(test_buffs)
    return manager


@pytest.fixture
def multiple_buffs():
    """提供多个 Buff 实例的集合"""
    return {
        Buff(name="敏锐直觉", id=201, icon=301, remain_ms=5000, stock=3),
        Buff(name="火焰护盾", id=202, icon=302, remain_ms=8000, stock=1),
        Buff(name="冰甲术", id=203, icon=303, remain_ms=0, stock=2),
        Buff(name="魔法护甲", id=204, icon=304, remain_ms=3000, stock=0)
    }


@pytest.fixture
def identifier_test_class():
    """提供用于测试 Identifier 的测试类"""
    class TestIdentifierClass(Identifier):
        def __init__(self, value=0):
            self.value = value
            self.field1 = 10
            self.field2 = 20
        
        @Identifier.register(str)
        def simple_method(self):
            return "simple"
        
        @property
        @Identifier.register(int, depends_on=["field1"])
        def dependent_property(self):
            return self.field1 * 2
        
        @Identifier.register(bool, depends_on=["field1", "field2"])
        def complex_method(self):
            return self.field1 > self.field2
    
    return TestIdentifierClass


# pytest 配置
def pytest_configure(config):
    """pytest 配置"""
    # 添加自定义标记
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests"
    )


def pytest_collection_modifyitems(config, items):
    """修改测试收集"""
    # 为没有标记的测试添加 unit 标记
    for item in items:
        if not any(item.iter_markers()):
            item.add_marker(pytest.mark.unit)


# 测试数据常量
TEST_BUFF_DATA = [
    {"id": 1001, "name": "测试buff_A", "icon": 1001, "stock": 1, "remain_ms": 5000},
    {"id": 1002, "name": "测试buff_B", "icon": 1002, "stock": 0, "remain_ms": 3000},
    {"id": 1003, "name": "测试buff_C", "icon": 1003, "stock": 2, "remain_ms": 0},
]


@pytest.fixture
def test_buff_data():
    """提供测试用的 buff 数据"""
    return TEST_BUFF_DATA.copy()


# 参数化测试数据
BUFF_SCENARIOS = [
    # (name, id, icon, remain_ms, stock, expected_up)
    ("有效buff_1", 1, 1, 1000, 1, True),
    ("有效buff_2", 2, 2, 0, 2, True),
    ("有效buff_3", 3, 3, 1000, 0, True),
    ("无效buff", 4, 4, 0, 0, False),
]


@pytest.fixture(params=BUFF_SCENARIOS)
def buff_scenario(request):
    """参数化的 buff 场景"""
    name, id_, icon, remain_ms, stock, expected_up = request.param
    buff = Buff(name=name, id=id_, icon=icon, remain_ms=remain_ms, stock=stock)
    return buff, expected_up