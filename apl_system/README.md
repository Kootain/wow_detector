# APL系统 - Python实现

基于SimulationCraft APL (Action Priority List) 概念的Python实现，用于游戏角色的智能决策和动作优先级管理。

## 概述

APL系统是一个模块化的决策引擎，能够解析类似SimulationCraft的APL语法，并根据游戏状态执行相应的动作。系统采用了词法分析、语法分析、表达式求值和动作执行的完整流程。

## 核心特性

- **完整的APL语法支持** - 支持条件表达式、动作优先级、选项参数等
- **模块化架构** - 每个组件独立设计，易于扩展和维护
- **高性能表达式求值** - 支持缓存、短路求值和性能监控
- **灵活的动作系统** - 支持动作注册、分类和别名
- **事件驱动调度** - 支持时间推进、事件调度和轮换管理
- **丰富的游戏状态** - 支持资源、Buff、冷却时间、目标信息等

## 系统架构

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   APL文本       │───▶│   词法分析器     │───▶│   语法分析器     │
│   (APL Script)  │    │   (Lexer)       │    │   (Parser)      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                        │
                                                        ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   动作执行      │◀───│   执行引擎       │◀───│   AST节点       │
│   (Actions)     │    │   (Executor)    │    │   (AST Nodes)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   动作注册器     │    │   表达式求值器   │    │   游戏上下文     │
│ (ActionRegistry)│    │  (Evaluator)    │    │   (Context)     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │   调度器        │
                       │  (Scheduler)    │
                       └─────────────────┘
```

## 模块说明

### 核心模块

| 模块 | 文件 | 功能描述 |
|------|------|----------|
| 词法分析器 | `lexer.py` | 将APL文本转换为token流 |
| 语法分析器 | `parser.py` | 将token解析为抽象语法树 |
| AST节点 | `ast_nodes.py` | 定义表达式和动作的AST结构 |
| 表达式求值器 | `evaluator.py` | 计算表达式值，支持缓存和性能监控 |
| 动作注册系统 | `action_registry.py` | 管理动作的注册、查找和执行 |
| 执行引擎 | `executor.py` | APL的核心执行逻辑和优先级决策 |
| 游戏上下文 | `context.py` | 提供游戏状态的访问接口 |
| 调度器 | `scheduler.py` | 时间推进和事件调度管理 |

### 辅助模块

| 模块 | 文件 | 功能描述 |
|------|------|----------|
| 主入口 | `__init__.py` | 系统初始化和主要接口 |
| 使用示例 | `examples.py` | 完整的使用示例和演示代码 |
| 测试模块 | `test_apl.py` | 单元测试和集成测试 |

## APL语法

### 基本语法

```apl
# 注释
actions=动作名,if=条件表达式,选项1=值1,选项2=值2
actions+=/动作名,if=条件表达式
```

### 条件表达式

```apl
# 资源检查
mana > 50
health < 30

# Buff检查
buff.combustion.up
!buff.shield.up
buff.combustion.remains > 5

# 冷却时间检查
cooldown.fireball.ready
cooldown.fireball.remains < 1.0
!cooldown.fireball.up

# 目标信息
target.health < 25
target.distance <= 5.0

# 复合条件
mana > 50 & !cooldown.fireball.up
(health < 30) | (mana > 100)
```

### 动作选项

```apl
# 基本动作
actions=fireball

# 带条件的动作
actions=fireball,if=mana>50

# 带选项的动作
actions=fireball,if=mana>50,target=enemy,cast_time=2.5

# 动作列表追加
actions+=/frostbolt,if=mana>30
actions+=/wait,sec=1.0
```

## 快速开始

### 1. 基本使用

```python
from apl_system import APLEngine
from apl_system.context import GameContext
from apl_system.action_registry import ActionRegistry, ActionHandler, ActionCategory, ActionResult

# 创建动作处理器
class MyActionHandler(ActionHandler):
    def execute(self, context, **kwargs):
        action_name = kwargs.get('action_name')
        print(f"执行动作: {action_name}")
        return ActionResult.SUCCESS

# 创建APL引擎
engine = APLEngine()

# 注册动作
handler = MyActionHandler()
engine.registry.register_action("fireball", handler, ActionCategory.DAMAGE)
engine.registry.register_action("heal", handler, ActionCategory.HEALING)

# 解析APL
apl_text = """
actions=fireball,if=mana>50
actions+=/heal,if=health<30
"""

action_list = engine.parse_apl(apl_text)

# 设置游戏状态
context = GameContext()
context.set_resource("health", 80.0)
context.set_resource("mana", 120.0)

# 执行APL
result = engine.execute_apl(action_list, context)
if result.action_taken:
    print(f"执行了动作: {result.action_taken.action_name}")
```

### 2. 高级用法

```python
from apl_system.scheduler import APLScheduler, APLRotationScheduler
from apl_system.executor import ExecutionMode

# 创建调度器
scheduler = APLScheduler()
rotation_scheduler = APLRotationScheduler(scheduler)

# 创建高性能执行器
engine = APLEngine(execution_mode=ExecutionMode.PERFORMANCE)

# 调度定期轮换
def rotation_callback(event, sched):
    result = engine.execute_apl(action_list, context)
    if result.action_taken:
        print(f"时间 {sched.current_time:.1f}s: {result.action_taken.action_name}")

scheduler.schedule_timer(1.5, rotation_callback, repeating=True)

# 运行调度器
stats = scheduler.run_for_duration(30.0)
print(f"处理了 {stats.processed_events} 个事件")
```

## 游戏状态管理

### 资源管理

```python
context = GameContext()

# 设置资源
context.set_resource("health", 100.0)
context.set_resource("mana", 200.0)
context.set_resource("energy", 100.0)

# 获取资源
health = context.get_resource("health")
mana = context.get_resource("mana")
```

### Buff管理

```python
# 设置Buff
context.set_buff("combustion", 10.0, {"damage_bonus": 50})
context.set_buff("shield", 30.0, {"damage_reduction": 20})

# 检查Buff
if context.has_buff("combustion"):
    buff_info = context.get_buff_info("combustion")
    print(f"燃烧剩余时间: {buff_info.remaining_time}秒")
```

### 冷却时间管理

```python
# 设置冷却时间
context.set_cooldown("fireball", 3.0)
context.set_cooldown("heal", 8.0)

# 检查冷却时间
if context.is_cooldown_ready("fireball"):
    print("火球术可以使用")
else:
    remaining = context.get_cooldown_remaining("fireball")
    print(f"火球术还需 {remaining:.1f} 秒")
```

### 目标信息

```python
from apl_system.context import TargetInfo

# 设置目标信息
target = TargetInfo("Boss", 75.0, 100.0, 5.0)
context.set_target_info(target)

# 获取目标信息
target = context.get_target_info()
print(f"目标 {target.name} 生命值: {target.health}%")
```

## 动作系统

### 创建动作处理器

```python
from apl_system.action_registry import ActionHandler, ActionResult

class SpellHandler(ActionHandler):
    def execute(self, context, **kwargs):
        action_name = kwargs.get('action_name')
        
        if action_name == "fireball":
            # 检查法力值
            if context.get_resource("mana") < 50:
                return ActionResult.FAILED
            
            # 消耗法力值
            context.set_resource("mana", context.get_resource("mana") - 50)
            
            # 设置冷却时间
            context.set_cooldown("fireball", 2.5)
            
            print("施放火球术！")
            return ActionResult.SUCCESS
        
        return ActionResult.FAILED
```

### 注册动作

```python
registry = ActionRegistry()
spell_handler = SpellHandler()

# 注册动作
registry.register_action(
    "fireball", spell_handler, ActionCategory.DAMAGE,
    description="火球术 - 造成火焰伤害",
    tags=["spell", "fire", "damage"]
)

# 添加别名
registry.add_alias("fb", "fireball")

# 按类别获取动作
damage_actions = registry.get_actions_by_category(ActionCategory.DAMAGE)

# 按标签获取动作
fire_spells = registry.get_actions_by_tag("fire")
```

## 性能优化

### 表达式缓存

```python
from apl_system.evaluator import ExpressionEvaluator

# 启用缓存的求值器
evaluator = ExpressionEvaluator(enable_cache=True, cache_size=1000)

# 批量求值
batch_evaluator = BatchEvaluator(evaluator)
results = batch_evaluator.evaluate_batch(expressions, context)
```

### 性能监控

```python
from apl_system.evaluator import ProfiledEvaluator

# 性能分析求值器
profiled_evaluator = ProfiledEvaluator(evaluator)

# 执行后获取性能报告
result = profiled_evaluator.evaluate(expression, context)
report = profiled_evaluator.get_performance_report()
print(f"求值时间: {report['total_time']:.6f}秒")
```

### 执行模式

```python
from apl_system.executor import APLExecutor, ExecutionMode

# 不同的执行模式
executor_debug = APLExecutor(evaluator, registry, ExecutionMode.DEBUG)
executor_perf = APLExecutor(evaluator, registry, ExecutionMode.PERFORMANCE)
executor_sim = APLExecutor(evaluator, registry, ExecutionMode.SIMULATION)
```

## 调度和事件

### 基本调度

```python
from apl_system.scheduler import APLScheduler, EventType

scheduler = APLScheduler()

# 调度定时器
def timer_callback(event, sched):
    print(f"定时器触发: {sched.current_time:.1f}秒")

scheduler.schedule_timer(5.0, timer_callback)

# 调度冷却完成事件
def cooldown_callback(event, sched):
    ability = event.data["ability"]
    print(f"{ability} 冷却完成")

scheduler.schedule_cooldown_event("fireball", 3.0, cooldown_callback)

# 运行调度器
scheduler.run_for_duration(10.0)
```

### 轮换调度

```python
from apl_system.scheduler import APLRotationScheduler

rotation_scheduler = APLRotationScheduler(scheduler)

# 开始轮换
rotation_scheduler.start_rotation()

# 调度动作
rotation_scheduler.schedule_action("fireball")
rotation_scheduler.schedule_action("frostbolt")

# GCD管理
if rotation_scheduler.can_cast_now():
    rotation_scheduler.schedule_action("instant_spell")
```

## 测试

运行测试套件：

```bash
python test_apl.py
```

运行示例：

```bash
python examples.py
```

## 扩展指南

### 添加新的表达式函数

```python
# 在evaluator.py中添加新函数
def evaluate_custom_function(self, func_name: str, args: List, context: APLContext):
    if func_name == "my_custom_func":
        # 自定义逻辑
        return custom_result
    return super().evaluate_function(func_name, args, context)
```

### 添加新的动作类别

```python
# 在action_registry.py中扩展ActionCategory
class ActionCategory(Enum):
    DAMAGE = "damage"
    HEALING = "healing"
    BUFF = "buff"
    DEBUFF = "debuff"
    UTILITY = "utility"
    DEFENSIVE = "defensive"
    MOVEMENT = "movement"  # 新增类别
```

### 自定义事件类型

```python
# 在scheduler.py中扩展EventType
class EventType(Enum):
    TIMER = "timer"
    COOLDOWN = "cooldown"
    BUFF_EXPIRE = "buff_expire"
    CUSTOM_EVENT = "custom_event"  # 新增事件类型
```

## 常见问题

### Q: 如何处理复杂的游戏逻辑？

A: 通过自定义ActionHandler和扩展Context来实现复杂逻辑：

```python
class ComplexGameHandler(ActionHandler):
    def execute(self, context, **kwargs):
        # 复杂的游戏逻辑
        if self.check_complex_condition(context):
            return self.perform_complex_action(context, **kwargs)
        return ActionResult.FAILED
```

### Q: 如何优化大量APL的性能？

A: 使用性能模式和缓存：

```python
# 启用所有优化
evaluator = ExpressionEvaluator(enable_cache=True, cache_size=2000)
executor = APLExecutor(evaluator, registry, ExecutionMode.PERFORMANCE)

# 预编译常用表达式
for expr in common_expressions:
    evaluator.precompile(expr)
```

### Q: 如何调试APL执行？

A: 使用调试模式和追踪：

```python
executor = APLExecutor(evaluator, registry, ExecutionMode.DEBUG)
result = executor.execute_apl(action_list, context)

# 查看执行追踪
for trace in result.execution_trace:
    print(f"动作: {trace.action_name}, 条件: {trace.condition_result}")
```

## 许可证

本项目采用MIT许可证。详见LICENSE文件。

## 贡献

欢迎提交Issue和Pull Request来改进这个项目。

## 更新日志

### v1.0.0
- 初始版本发布
- 完整的APL语法支持
- 模块化架构设计
- 性能优化和缓存机制
- 事件驱动调度系统
- 完整的测试套件