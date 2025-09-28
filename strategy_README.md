# 游戏策略系统 (Game Strategy System)

这是一个为魔兽世界等MMORPG游戏设计的复杂行动策略系统，支持基于优先级的智能决策、状态机管理、策略模式和可扩展的配置系统。

## 🎯 核心特性

- **基于优先级的决策框架** - 智能评估和选择最优动作
- **状态机模式** - 根据游戏状态动态调整策略
- **策略模式** - 支持不同职业、专精和场景的策略
- **条件判断系统** - 灵活的条件组合和评估
- **动作优先级队列** - 智能的动作排序和调度
- **可扩展配置系统** - 动态配置和策略管理
- **自适应管理** - 根据游戏状态自动调整策略组合

## 📁 文件结构

```
test/
├── strategy.py           # 核心策略系统实现
├── strategy_example.py   # 完整使用示例
└── strategy_README.md    # 本文档
```

## 🏗️ 系统架构

### 1. 基础数据模型

```python
@dataclass
class State:
    """游戏状态数据模型"""
    health_percent: int          # 血量百分比
    mana_percent: int           # 法力百分比
    target_health_percent: int  # 目标血量百分比
    in_combat: bool            # 是否在战斗中
    is_casting: bool           # 是否在施法
    buffs: Dict[int, int]      # Buff列表 {buff_id: 剩余时间ms}
    debuffs: Dict[int, int]    # Debuff列表
    cooldowns: Dict[int, int]  # 冷却时间 {spell_id: 剩余时间ms}
    # ... 更多字段

@dataclass
class Action:
    """动作数据模型"""
    spell_id: int              # 法术ID
    target_type: str           # 目标类型
    priority: int = 0          # 优先级
    delay_ms: int = 0          # 延迟执行时间
```

### 2. 条件判断系统

支持多种条件类型的组合判断：

- `HealthCondition` - 血量条件
- `ManaCondition` - 法力条件
- `BuffCondition` - Buff条件
- `CooldownCondition` - 冷却时间条件
- `CombatCondition` - 战斗状态条件
- `CastingCondition` - 施法状态条件
- `CompositeCondition` - 复合条件（支持AND/OR/NOT逻辑）

### 3. 策略系统

#### 通用策略
- `EmergencyHealingStrategy` - 紧急治疗
- `BuffMaintenanceStrategy` - Buff维护
- `DamageRotationStrategy` - 伤害循环
- `ManaManagementStrategy` - 法力管理

#### 职业特定策略
- `PaladinHealingStrategy` - 圣骑士治疗
- `MageFireStrategy` - 法师火系输出

#### 场景特定策略
- `DungeonStrategy` - 地下城策略
- `RaidStrategy` - 团队副本策略
- `PvPStrategy` - PvP策略

### 4. 配置管理系统

- `StrategyConfig` - 策略配置数据模型
- `StrategyFactory` - 策略工厂，根据配置创建策略实例
- `StrategyConfigManager` - 配置管理器
- `AdaptiveStrategyManager` - 自适应策略管理器

## 🚀 快速开始

### 基础使用

```python
from strategy import (
    State, Action, HealthCondition, DecisionEngine, PriorityAction, Priority
)

# 1. 创建游戏状态
game_state = State(
    health_percent=60,
    mana_percent=80,
    in_combat=True,
    # ... 其他字段
)

# 2. 创建条件和决策引擎
low_health = HealthCondition(threshold=70)
engine = DecisionEngine()

# 3. 添加动作
engine.add_action(PriorityAction(
    action=Action(spell_id=2061, target_type="self"),  # 快速治疗
    priority=Priority.HIGH.value,
    condition=low_health
))

# 4. 获取最佳动作
best_action = engine.get_best_action(game_state)
if best_action:
    print(f"推荐施放法术: {best_action.spell_id}")
```

### 使用自适应管理器

```python
from strategy import AdaptiveStrategyManager

# 1. 创建并初始化管理器
manager = AdaptiveStrategyManager()
manager.initialize()

# 2. 更新游戏状态
manager.update_game_state(game_state)

# 3. 获取推荐动作
next_action = manager.get_next_action(game_state)

# 4. 动态调整策略
manager.disable_strategy('mage_fire')
manager.set_strategy_priority('emergency_healing', Priority.EMERGENCY.value)
```

## 📋 配置管理

### 创建自定义策略配置

```python
from strategy import StrategyConfig, Priority

custom_config = StrategyConfig(
    name="custom_healing",
    priority=Priority.HIGH.value,
    parameters={'heal_spell_id': 2050},
    tags=['healing', 'custom'],
    conditions={'health_threshold': 50},
    required_class="PRIEST"
)

manager.add_custom_strategy_config(custom_config)
```

### 配置筛选和管理

```python
# 根据标签筛选
healing_configs = config_manager.get_configs_by_tags(['healing'])

# 根据职业筛选
paladin_configs = config_manager.get_configs_by_class('PALADIN')

# 创建配置组
config_manager.create_config_group('utility', ['mana_management', 'buff_maintenance'])

# 导出/导入配置
exported = config_manager.export_configs()
config_manager.import_configs(exported)
```

## 🎮 游戏状态管理

系统支持以下游戏状态：

- `OUT_OF_COMBAT` - 脱离战斗
- `IN_COMBAT` - 战斗中
- `EMERGENCY` - 紧急状态
- `CASTING` - 施法中
- `RESTING` - 休息中

状态转换规则：

```python
# 自动状态转换
state_machine = GameStateMachine(GameState.OUT_OF_COMBAT)
state_machine.add_transition(StateTransition(
    from_state=GameState.OUT_OF_COMBAT,
    to_state=GameState.IN_COMBAT,
    condition=CombatCondition()
))
```

## 🔧 高级功能

### 复合条件判断

```python
# 复杂条件组合
emergency_condition = CompositeCondition(
    conditions=[
        CompositeCondition(
            conditions=[
                HealthCondition(threshold=30),
                HealthCondition(threshold=20, target=True)
            ],
            operator='OR'
        ),
        CombatCondition(),
        CompositeCondition(
            conditions=[CastingCondition()],
            operator='NOT'
        )
    ],
    operator='AND'
)
```

### 动作队列和调度

```python
# 智能动作管理
action_manager = SmartActionManager()
action_manager.add_action(action, priority=Priority.HIGH.value)
action_manager.schedule_delayed_action(action, delay_ms=2000)
action_manager.add_recurring_action(action, interval_ms=30000)

# 获取下一个动作
next_action = action_manager.get_next_action(game_state)
```

### 策略性能监控

```python
# 获取管理器状态
status = manager.get_manager_status()
print(f"当前游戏状态: {status['current_game_state']}")
print(f"活跃策略: {status['active_strategies']}")
print(f"动作管理器状态: {status['action_manager_status']}")
```

## 📊 优先级系统

系统使用以下优先级等级：

```python
class Priority(Enum):
    EMERGENCY = 1000    # 紧急情况（如生命危险）
    HIGH = 800         # 高优先级（如重要治疗、打断）
    MEDIUM = 500       # 中等优先级（如常规输出、Buff维护）
    LOW = 200          # 低优先级（如非关键技能）
    IDLE = 50          # 空闲时执行（如休息时的准备工作）
```

## 🎯 最佳实践

### 1. 策略设计原则

- **单一职责** - 每个策略专注于特定的游戏场景
- **优先级明确** - 合理设置策略和动作的优先级
- **条件精确** - 使用精确的条件判断避免误触发
- **性能优化** - 避免复杂的条件判断和重复计算

### 2. 配置管理建议

- **分组管理** - 使用配置组管理相关策略
- **标签系统** - 合理使用标签进行策略分类
- **动态调整** - 根据游戏情况动态启用/禁用策略
- **版本控制** - 导出配置进行版本管理

### 3. 性能优化

- **条件缓存** - 缓存重复的条件判断结果
- **策略限制** - 限制同时活跃的策略数量
- **定期清理** - 清理过期的动作和状态数据
- **监控调优** - 监控策略执行性能并及时调整

### 4. 调试和测试

- **日志记录** - 记录策略执行和决策过程
- **状态监控** - 实时监控游戏状态和策略状态
- **单元测试** - 为关键组件编写单元测试
- **集成测试** - 测试完整的策略执行流程

## 🔍 故障排除

### 常见问题

1. **策略不执行**
   - 检查策略是否启用
   - 验证条件判断是否正确
   - 确认优先级设置

2. **动作冲突**
   - 检查全局冷却时间
   - 验证动作优先级
   - 确认条件互斥性

3. **性能问题**
   - 减少复杂条件判断
   - 限制活跃策略数量
   - 优化状态更新频率

### 调试工具

```python
# 获取详细状态信息
status = manager.get_manager_status()
print(f"管理器状态: {status}")

# 检查策略执行条件
for strategy in manager.current_strategies:
    can_execute = strategy.can_execute(game_state)
    print(f"策略 {strategy.__class__.__name__}: {can_execute}")

# 监控动作队列
queue_status = action_manager.get_status()
print(f"动作队列状态: {queue_status}")
```

## 📚 扩展开发

### 创建自定义策略

```python
from strategy import BaseStrategy, Priority

class CustomStrategy(BaseStrategy):
    def __init__(self, priority: int = Priority.MEDIUM.value):
        super().__init__(priority)
        # 初始化自定义参数
    
    def can_execute(self, state: State) -> bool:
        # 实现执行条件判断
        return True
    
    def get_actions(self, state: State) -> List[Action]:
        # 实现动作生成逻辑
        return []
```

### 创建自定义条件

```python
from strategy import BaseCondition

class CustomCondition(BaseCondition):
    def __init__(self, threshold: float):
        self.threshold = threshold
    
    def evaluate(self, state: State) -> bool:
        # 实现条件评估逻辑
        return True
```

### 注册自定义策略构建器

```python
def build_custom_strategy(config: StrategyConfig) -> CustomStrategy:
    return CustomStrategy(config.priority)

factory = StrategyFactory()
factory.register_strategy_builder('custom_strategy', build_custom_strategy)
```

## 📄 许可证

本项目采用 MIT 许可证。详见 LICENSE 文件。

## 🤝 贡献

欢迎提交 Issue 和 Pull Request 来改进这个项目。

## 📞 支持

如有问题或建议，请通过以下方式联系：

- 提交 GitHub Issue
- 发送邮件至项目维护者
- 参与项目讨论区

---

**注意**: 本系统仅供学习和研究使用，请遵守游戏服务条款和相关法律法规。