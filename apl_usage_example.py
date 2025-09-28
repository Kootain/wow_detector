#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
APL系统使用示例
展示如何使用基于SimulationCraft APL概念的Python版本策略系统
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from strategy import (
    State, Action, Buff, Cooldown, Spell,
    APLStrategy, ActionDefinition, ActionType,
    ActionRegistry
)

def create_hunter_apl():
    """创建猎人射击专精APL示例"""
    
    # 完整的猎人APL脚本
    hunter_apl = """
# 猎人射击专精APL - 基于SimulationCraft设计
# 主要循环
actions=steady_shot,if=buff.steady_focus.remains<2000
actions+=/aimed_shot,if=focus>=70&cooldown.aimed_shot.ready
actions+=/multi_shot,if=active_enemies>=3&focus>=25
actions+=/arcane_shot,if=focus.deficit<=20
actions+=/steady_shot,if=focus.deficit>=20
actions+=/call_action_list,name=cooldowns
actions+=/wait

# 冷却技能循环
actions.cooldowns=rapid_fire,if=cooldown.trueshot.remains>10000&focus>=30
actions.cooldowns+=/trueshot,if=buff.lock_and_load.up|target.time_to_die<15
actions.cooldowns+=/hunters_mark,if=!buff.hunters_mark.up&target.time_to_die>30

# 爆发循环
actions.burst=trueshot
actions.burst+=/rapid_fire
actions.burst+=/aimed_shot,if=buff.lock_and_load.up
actions.burst+=/arcane_shot,if=focus>=40
"""
    
    return APLStrategy(hunter_apl)

def simulate_combat_scenario():
    """模拟战斗场景"""
    print("=== 猎人APL战斗模拟 ===")
    
    # 创建猎人策略
    strategy = create_hunter_apl()
    
    # 模拟不同的战斗状态
    scenarios = [
        {
            "name": "开场 - 满资源状态",
            "state": State(buffs=[], cooldowns=[]),
            "focus": 100
        },
        {
            "name": "Steady Focus即将消失",
            "state": State(
                buffs=[
                    Buff(spell_id=193534, name="steady_focus", stacks=1, remaining_ms=1500, icon=1)
                ],
                cooldowns=[]
            ),
            "focus": 80
        },
        {
            "name": "瞄准射击冷却中",
            "state": State(
                buffs=[],
                cooldowns=[
                    Cooldown(spell_id=19434, name="aimed_shot", remaining_ms=5000, icon=1)
                ]
            ),
            "focus": 75
        },
        {
            "name": "多目标场景",
            "state": State(buffs=[], cooldowns=[]),
            "focus": 60,
            "active_enemies": 4
        },
        {
            "name": "低资源状态",
            "state": State(buffs=[], cooldowns=[]),
            "focus": 15
        }
    ]
    
    for scenario in scenarios:
        print(f"\n场景: {scenario['name']}")
        print(f"Focus: {scenario['focus']}")
        
        # 设置资源状态
        strategy.apl_executor.resource_manager.resources["focus"].current = scenario['focus']
        
        # 设置环境变量
        if 'active_enemies' in scenario:
            strategy.apl_executor.expression_evaluator.context_vars['active_enemies'] = scenario['active_enemies']
        
        # 获取推荐动作
        action = strategy.get_next_action(scenario['state'])
        
        if action:
            # 查找动作定义
            action_def = None
            for name, definition in strategy.apl_executor.action_registry.actions.items():
                if definition.spell_id == action.spell_id:
                    action_def = definition
                    break
            
            if action_def:
                cost_info = ""
                if action_def.resource_cost:
                    costs = [f"{res}:{cost}" for res, cost in action_def.resource_cost.items()]
                    cost_info = f" (消耗: {', '.join(costs)})"
                
                print(f"推荐动作: {action_def.name}{cost_info}")
                print(f"施法ID: {action.spell_id}")
            else:
                print(f"推荐动作: 未知动作 (施法ID: {action.spell_id})")
        else:
            print("推荐动作: 等待")

def create_custom_class_apl():
    """创建自定义职业APL示例"""
    print("\n=== 自定义职业APL示例 ===")
    
    # 注册自定义动作
    registry = ActionRegistry()
    
    # 法师火焰专精技能
    registry.register(ActionDefinition(
        name="fireball",
        action_type=ActionType.SPELL,
        spell_id=133,
        resource_cost={"mana": 50},
        cast_time=2.5
    ))
    
    registry.register(ActionDefinition(
        name="fire_blast",
        action_type=ActionType.SPELL,
        spell_id=108853,
        resource_cost={"mana": 30},
        cast_time=0  # 瞬发
    ))
    
    registry.register(ActionDefinition(
        name="pyroblast",
        action_type=ActionType.SPELL,
        spell_id=11366,
        resource_cost={"mana": 80},
        cast_time=4.0
    ))
    
    # 法师APL
    mage_apl = """
# 法师火焰专精APL
actions=fire_blast,if=buff.heating_up.up&!buff.hot_streak.up
actions+=/pyroblast,if=buff.hot_streak.up
actions+=/fire_blast,if=cooldown.fire_blast.charges>=2
actions+=/fireball
actions+=/wait
"""
    
    # 创建策略并替换动作注册表
    strategy = APLStrategy(mage_apl)
    strategy.apl_executor.action_registry = registry
    
    # 测试场景
    test_state = State(
        buffs=[
            Buff(spell_id=48108, name="hot_streak", stacks=1, remaining_ms=10000, icon=1)
        ],
        cooldowns=[]
    )
    
    # 设置法力值
    strategy.apl_executor.resource_manager.resources["mana"].current = 800
    
    action = strategy.get_next_action(test_state)
    if action:
        print(f"法师推荐动作: 施法ID={action.spell_id} (应该是Pyroblast)")
    
    print("\n已注册的法师技能:")
    for name, action_def in registry.actions.items():
        cost_str = f", 消耗: {action_def.resource_cost}" if action_def.resource_cost else ""
        cast_str = f", 施法时间: {action_def.cast_time}s" if action_def.cast_time else ""
        print(f"  {name} (ID: {action_def.spell_id}{cost_str}{cast_str})")

def demonstrate_expression_features():
    """演示表达式系统的高级功能"""
    print("\n=== 表达式系统高级功能演示 ===")
    
    from strategy import ExpressionParser, ExpressionEvaluator, ExpressionContext
    
    parser = ExpressionParser()
    evaluator = ExpressionEvaluator()
    
    # 创建复杂的游戏状态
    complex_state = State(
        buffs=[
            Buff(spell_id=1, name="bloodlust", stacks=1, remaining_ms=25000, icon=1),
            Buff(spell_id=2, name="power_infusion", stacks=1, remaining_ms=15000, icon=2),
            Buff(spell_id=3, name="trinket_proc", stacks=3, remaining_ms=8000, icon=3)
        ],
        cooldowns=[
            Cooldown(spell_id=4, name="big_cooldown", remaining_ms=45000, icon=4),
            Cooldown(spell_id=5, name="medium_cooldown", remaining_ms=0, icon=5)
        ]
    )
    
    context = ExpressionContext(
        game_state=complex_state,
        resources={
            "mana": 750, "mana_max": 1000, "mana_deficit": 250, "mana_pct": 75.0,
            "focus": 45, "focus_max": 100, "focus_deficit": 55, "focus_pct": 45.0
        }
    )
    
    # 设置环境变量
    evaluator.context_vars.update({
        "active_enemies": 3,
        "target_health_pct": 35.5,
        "time_to_die": 120,
        "fight_remains": 180
    })
    
    # 高级表达式示例
    advanced_expressions = [
        # 爆发时机判断
        "buff.bloodlust.up&buff.power_infusion.up&cooldown.medium_cooldown.ready",
        
        # 资源管理
        "mana.pct>60&focus.deficit<=30",
        
        # 多层buff判断
        "buff.trinket_proc.stacks>=2&buff.trinket_proc.remains>5000",
        
        # 战斗阶段判断
        "target_health_pct<35&time_to_die>30",
        
        # 复杂的冷却管理
        "cooldown.big_cooldown.remains<10000|fight_remains<60",
        
        # 多目标场景
        "active_enemies>=3&mana>200",
        
        # 数学运算
        "buff.trinket_proc.stacks*25+mana.pct>=100"
    ]
    
    print("当前状态:")
    print(f"  Buff: bloodlust({complex_state.buffs[0].remaining_ms}ms), power_infusion({complex_state.buffs[1].remaining_ms}ms), trinket_proc({complex_state.buffs[2].stacks}层)")
    print(f"  资源: mana={context.resources['mana']}/{context.resources['mana_max']}, focus={context.resources['focus']}/{context.resources['focus_max']}")
    print(f"  环境: 敌人数量={evaluator.context_vars['active_enemies']}, 目标血量={evaluator.context_vars['target_health_pct']}%")
    
    print("\n表达式计算结果:")
    for expr_str in advanced_expressions:
        try:
            ast = parser.parse(expr_str)
            result = evaluator.evaluate(ast, context)
            print(f"  {expr_str}")
            print(f"    -> {result}")
        except Exception as e:
            print(f"  {expr_str}")
            print(f"    -> 错误: {e}")

def main():
    """运行所有使用示例"""
    print("APL系统使用示例")
    print("=" * 60)
    
    try:
        # 基本APL使用
        simulate_combat_scenario()
        
        # 自定义职业APL
        create_custom_class_apl()
        
        # 高级表达式功能
        demonstrate_expression_features()
        
        print("\n" + "=" * 60)
        print("APL系统使用示例演示完成！")
        print("\n主要特性:")
        print("1. 基于SimulationCraft APL语法的Python实现")
        print("2. 灵活的表达式系统支持复杂条件判断")
        print("3. 模块化设计，易于扩展和自定义")
        print("4. 支持多种资源类型和状态管理")
        print("5. 优先级驱动的动作选择机制")
        
    except Exception as e:
        print(f"示例运行过程中发生错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()