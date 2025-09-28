#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
APL系统测试文件
测试各个模块的功能和集成效果
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from strategy import (
    State, Action, Buff, Cooldown, Spell,
    APLStrategy, ActionDefinition, ActionType,
    ExpressionParser, ExpressionEvaluator, ExpressionContext,
    APLParser, ResourceManager, StateManager
)

def test_expression_parser():
    """测试表达式解析器"""
    print("=== 测试表达式解析器 ===")
    
    parser = ExpressionParser()
    evaluator = ExpressionEvaluator()
    
    # 创建测试状态
    test_state = State(
        buffs=[
            Buff(spell_id=1, name="steady_focus", stacks=1, remaining_ms=5000, icon=1)
        ],
        cooldowns=[
            Cooldown(spell_id=2, name="aimed_shot", remaining_ms=0, icon=2)
        ]
    )
    
    # 创建测试上下文
    context = ExpressionContext(
        game_state=test_state,
        resources={"focus": 80, "focus_max": 100, "focus_deficit": 20}
    )
    
    # 测试用例
    test_cases = [
        ("focus>=70", True),
        ("focus<50", False),
        ("buff.steady_focus.up", True),
        ("buff.steady_focus.remains>2000", True),
        ("cooldown.aimed_shot.ready", True),
        ("focus>=70&buff.steady_focus.up", True),
        ("focus<50|buff.steady_focus.up", True),
        ("!buff.nonexistent.up", True)
    ]
    
    for expr_str, expected in test_cases:
        try:
            ast = parser.parse(expr_str)
            result = evaluator.evaluate(ast, context)
            status = "✓" if result == expected else "✗"
            print(f"{status} {expr_str} = {result} (期望: {expected})")
        except Exception as e:
            print(f"✗ {expr_str} - 错误: {e}")
    
    print()

def test_apl_parser():
    """测试APL解析器"""
    print("=== 测试APL解析器 ===")
    
    apl_script = """
# 猎人射击专精APL
actions=steady_shot,if=buff.steady_focus.remains<2000
actions+=/aimed_shot,if=focus>=70&cooldown.aimed_shot.ready
actions+=/multi_shot,if=active_enemies>=3
actions+=/steady_shot,if=focus.deficit>=20
actions+=/wait

# 冷却技能列表
actions.cooldowns=rapid_fire,if=cooldown.trueshot.remains>10
actions.cooldowns+=/trueshot,if=buff.lock_and_load.up
"""
    
    parser = APLParser()
    action_lists = parser.parse_apl_script(apl_script)
    
    print(f"解析到 {len(action_lists)} 个动作列表:")
    
    for list_name, action_list in action_lists.items():
        print(f"\n列表: {list_name}")
        for i, entry in enumerate(action_list.entries):
            condition_str = f", 条件: {entry.raw_condition}" if entry.raw_condition else ""
            print(f"  {i+1}. {entry.action_name}{condition_str}")
    
    print()

def test_resource_manager():
    """测试资源管理器"""
    print("=== 测试资源管理器 ===")
    
    manager = ResourceManager()
    
    print("初始资源状态:")
    resources = manager.get_resource_dict()
    for name, value in resources.items():
        print(f"  {name}: {value}")
    
    # 测试资源消耗
    print("\n消耗30点focus:")
    success = manager.consume("focus", 30)
    print(f"消耗成功: {success}")
    
    resources = manager.get_resource_dict()
    print(f"当前focus: {resources['focus']}")
    print(f"focus缺失: {resources['focus_deficit']}")
    
    # 测试资源回复
    print("\n回复2秒:")
    manager.regenerate(2.0)
    resources = manager.get_resource_dict()
    print(f"回复后focus: {resources['focus']}")
    
    print()

def test_action_system():
    """测试动作系统"""
    print("=== 测试动作系统 ===")
    
    from strategy import ActionRegistry, ActionExecutor
    
    # 创建动作注册表
    registry = ActionRegistry()
    
    # 注册自定义动作
    registry.register(ActionDefinition(
        name="multi_shot",
        action_type=ActionType.SPELL,
        spell_id=2643,
        resource_cost={"focus": 25}
    ))
    
    print("已注册的动作:")
    for name in registry.actions.keys():
        action_def = registry.get(name)
        cost_str = f", 消耗: {action_def.resource_cost}" if action_def.resource_cost else ""
        print(f"  {name} (类型: {action_def.action_type.value}{cost_str})")
    
    # 测试动作执行
    executor = ActionExecutor(registry)
    
    # 创建测试上下文
    test_state = State()
    context = ExpressionContext(
        game_state=test_state,
        resources={"focus": 80, "focus_max": 100}
    )
    
    print("\n测试动作执行:")
    test_actions = ["steady_shot", "aimed_shot", "multi_shot", "wait"]
    
    for action_name in test_actions:
        can_execute = executor.can_execute(action_name, context)
        print(f"  {action_name}: 可执行={can_execute}")
        
        if can_execute:
            result = executor.execute(action_name, context)
            if result.success and result.action:
                print(f"    -> 执行成功: 施法ID={result.action.spell_id}")
            elif result.success:
                print(f"    -> 执行成功: {result.message}")
    
    print()

def test_complete_apl_system():
    """测试完整APL系统"""
    print("=== 测试完整APL系统 ===")
    
    # 创建APL策略
    apl_script = """
# 简化的猎人APL
actions=steady_shot,if=buff.steady_focus.remains<2000
actions+=/aimed_shot,if=focus>=70
actions+=/steady_shot,if=focus.deficit>=20
actions+=/wait
"""
    
    strategy = APLStrategy(apl_script)
    
    # 测试场景1: 有steady_focus buff，focus充足
    print("场景1: 有steady_focus buff (剩余1秒)，focus=80")
    test_state1 = State(
        buffs=[
            Buff(spell_id=1, name="steady_focus", stacks=1, remaining_ms=1000, icon=1)
        ]
    )
    
    # 模拟资源状态
    strategy.apl_executor.resource_manager.resources["focus"].current = 80
    
    action1 = strategy.get_next_action(test_state1)
    if action1:
        print(f"  推荐动作: 施法ID={action1.spell_id} (应该是steady_shot: 56641)")
    else:
        print("  无推荐动作")
    
    # 测试场景2: 无buff，focus充足
    print("\n场景2: 无buff，focus=80")
    test_state2 = State(buffs=[])
    
    action2 = strategy.get_next_action(test_state2)
    if action2:
        print(f"  推荐动作: 施法ID={action2.spell_id} (应该是aimed_shot: 19434)")
    else:
        print("  无推荐动作")
    
    # 测试场景3: focus不足
    print("\n场景3: focus=10")
    strategy.apl_executor.resource_manager.resources["focus"].current = 10
    
    action3 = strategy.get_next_action(test_state2)
    if action3:
        print(f"  推荐动作: 施法ID={action3.spell_id}")
    else:
        print("  无推荐动作 (应该等待)")
    
    print()

def test_advanced_expressions():
    """测试高级表达式功能"""
    print("=== 测试高级表达式 ===")
    
    parser = ExpressionParser()
    evaluator = ExpressionEvaluator()
    
    # 创建复杂测试状态
    test_state = State(
        buffs=[
            Buff(spell_id=1, name="hunter_mark", stacks=1, remaining_ms=30000, icon=1),
            Buff(spell_id=2, name="steady_focus", stacks=2, remaining_ms=5000, icon=2)
        ],
        cooldowns=[
            Cooldown(spell_id=3, name="aimed_shot", remaining_ms=2000, icon=3),
            Cooldown(spell_id=4, name="rapid_fire", remaining_ms=0, icon=4)
        ]
    )
    
    context = ExpressionContext(
        game_state=test_state,
        resources={
            "focus": 65, "focus_max": 100, "focus_deficit": 35,
            "mana": 800, "mana_max": 1000
        }
    )
    
    # 复杂表达式测试
    complex_expressions = [
        "buff.hunter_mark.up&buff.steady_focus.stacks>=2",
        "cooldown.aimed_shot.remains>0&cooldown.rapid_fire.ready",
        "focus.deficit>=30&buff.steady_focus.remains>3000",
        "(focus>=70|buff.steady_focus.up)&!cooldown.aimed_shot.ready",
        "buff.steady_focus.stacks*10+focus>=80"
    ]
    
    for expr_str in complex_expressions:
        try:
            ast = parser.parse(expr_str)
            result = evaluator.evaluate(ast, context)
            print(f"✓ {expr_str} = {result}")
        except Exception as e:
            print(f"✗ {expr_str} - 错误: {e}")
    
    print()

def main():
    """运行所有测试"""
    print("APL系统功能测试")
    print("=" * 50)
    
    try:
        test_expression_parser()
        test_apl_parser()
        test_resource_manager()
        test_action_system()
        test_complete_apl_system()
        test_advanced_expressions()
        
        print("=" * 50)
        print("所有测试完成！")
        
    except Exception as e:
        print(f"测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()