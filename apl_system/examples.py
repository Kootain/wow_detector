#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
APL系统使用示例

展示如何使用APL系统的各个组件来创建和执行复杂的游戏策略。
包含完整的示例代码，从基础用法到高级功能。
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from lexer import APLLexer
from parser import APLParser
from ast_nodes import *
from context import GameContext, ResourceInfo, BuffInfo, CooldownInfo, TargetInfo
from evaluator import ExpressionEvaluator
from action_registry import ActionRegistry, ActionHandler, ActionCategory, ActionResult
from executor import APLExecutor, ExecutionMode
from scheduler import APLScheduler, APLRotationScheduler, EventType


class FireMageActionHandler(ActionHandler):
    """火法师动作处理器示例"""
    
    def execute(self, context, **kwargs) -> ActionResult:
        action_name = kwargs.get('action_name', 'unknown')
        
        if action_name == "fireball":
            # 检查法力值
            if context.get_resource("mana") < 50:
                return ActionResult.FAILED
            
            # 消耗法力值
            context.set_resource("mana", context.get_resource("mana") - 50)
            
            # 设置冷却时间
            context.set_cooldown("fireball", 2.5)
            
            print(f"施放火球术！剩余法力: {context.get_resource('mana')}")
            return ActionResult.SUCCESS
            
        elif action_name == "frostbolt":
            if context.get_resource("mana") < 40:
                return ActionResult.FAILED
                
            context.set_resource("mana", context.get_resource("mana") - 40)
            context.set_cooldown("frostbolt", 2.0)
            
            print(f"施放冰箭术！剩余法力: {context.get_resource('mana')}")
            return ActionResult.SUCCESS
            
        elif action_name == "arcane_missiles":
            if context.get_resource("mana") < 60:
                return ActionResult.FAILED
                
            context.set_resource("mana", context.get_resource("mana") - 60)
            context.set_cooldown("arcane_missiles", 3.0)
            
            print(f"施放奥术飞弹！剩余法力: {context.get_resource('mana')}")
            return ActionResult.SUCCESS
            
        elif action_name == "combustion":
            if context.get_cooldown_remaining("combustion") > 0:
                return ActionResult.FAILED
                
            context.set_cooldown("combustion", 120.0)
            context.set_buff("combustion", 10.0, {"damage_bonus": 50})
            
            print("使用燃烧！伤害提升50%")
            return ActionResult.SUCCESS
            
        return ActionResult.FAILED


def example_basic_usage():
    """基础使用示例"""
    print("=== APL系统基础使用示例 ===")
    
    # 1. 词法分析
    apl_text = """
    # 火法师基础轮换
    actions.precombat=flask,food
    actions=combustion,if=!buff.combustion.up
    actions+=/fireball,if=mana>50&!cooldown.fireball.up
    actions+=/frostbolt,if=mana>40
    """
    
    lexer = APLLexer()
    tokens = lexer.tokenize(apl_text)
    print(f"词法分析完成，共{len(tokens)}个token")
    
    # 2. 语法分析
    parser = APLParser()
    action_list = parser.parse(apl_text)
    print(f"语法分析完成，共{len(action_list.actions)}个动作")
    
    # 3. 创建游戏上下文
    context = GameContext()
    context.set_resource("health", 100.0)
    context.set_resource("mana", 200.0)
    context.set_target_info(TargetInfo("Boss", 100.0, 100.0, 5.0))
    
    # 4. 创建表达式求值器
    evaluator = ExpressionEvaluator()
    
    # 5. 注册动作
    registry = ActionRegistry()
    fire_mage_handler = FireMageActionHandler()
    
    registry.register_action(
        "fireball", fire_mage_handler, ActionCategory.DAMAGE,
        description="火球术 - 造成火焰伤害",
        tags=["spell", "fire", "damage"]
    )
    
    registry.register_action(
        "frostbolt", fire_mage_handler, ActionCategory.DAMAGE,
        description="冰箭术 - 造成冰霜伤害并减速",
        tags=["spell", "frost", "damage"]
    )
    
    registry.register_action(
        "combustion", fire_mage_handler, ActionCategory.BUFF,
        description="燃烧 - 提升火焰伤害",
        tags=["spell", "fire", "buff"]
    )
    
    # 6. 创建执行器
    executor = APLExecutor(evaluator, registry)
    
    # 7. 执行APL
    print("\n开始执行APL...")
    for i in range(5):
        print(f"\n--- 第{i+1}轮 ---")
        result = executor.execute_apl(action_list, context)
        
        if result.action_taken:
            print(f"执行动作: {result.action_taken.action_name}")
        else:
            print("没有可执行的动作")
            
        # 模拟时间推进
        context.advance_time(1.0)
        
        # 恢复一些法力值
        current_mana = context.get_resource("mana")
        context.set_resource("mana", min(200.0, current_mana + 20.0))


def example_advanced_apl():
    """高级APL示例"""
    print("\n\n=== 高级APL示例 ===")
    
    # 复杂的火法师APL
    advanced_apl = """
    # 战前准备
    actions.precombat=flask
    actions.precombat+=/food
    actions.precombat+=/arcane_intellect
    
    # 主要轮换
    actions=combustion,if=!buff.combustion.up&cooldown.combustion.ready&target.health>50
    actions+=/fireball,if=buff.combustion.up&mana>50
    actions+=/arcane_missiles,if=buff.arcane_power.up&mana>60
    actions+=/frostbolt,if=target.health<25&mana>40
    actions+=/fireball,if=mana>50&!cooldown.fireball.up
    actions+=/frostbolt,if=mana>40
    
    # 应急处理
    actions.emergency=health_potion,if=health<30
    actions.emergency+=/mana_potion,if=mana<50
    """
    
    # 解析APL
    parser = APLParser()
    action_list = parser.parse(advanced_apl)
    
    # 设置更复杂的游戏状态
    context = GameContext()
    context.set_resource("health", 80.0)
    context.set_resource("mana", 150.0)
    context.set_target_info(TargetInfo("Elite Boss", 75.0, 100.0, 8.0))
    
    # 添加一些Buff
    context.set_buff("arcane_intellect", 3600.0, {"intellect": 50})
    
    # 创建执行器
    evaluator = ExpressionEvaluator()
    registry = ActionRegistry()
    fire_mage_handler = FireMageActionHandler()
    
    # 注册更多动作
    actions_to_register = [
        ("fireball", "火球术", ["spell", "fire", "damage"]),
        ("frostbolt", "冰箭术", ["spell", "frost", "damage"]),
        ("arcane_missiles", "奥术飞弹", ["spell", "arcane", "damage"]),
        ("combustion", "燃烧", ["spell", "fire", "buff"]),
    ]
    
    for action_name, description, tags in actions_to_register:
        registry.register_action(
            action_name, fire_mage_handler, ActionCategory.DAMAGE,
            description=description, tags=tags
        )
    
    executor = APLExecutor(evaluator, registry, ExecutionMode.PERFORMANCE)
    
    print("执行高级APL轮换...")
    
    # 模拟战斗
    for round_num in range(10):
        print(f"\n--- 战斗轮次 {round_num + 1} ---")
        print(f"生命值: {context.get_resource('health'):.1f}, 法力值: {context.get_resource('mana'):.1f}")
        print(f"目标生命值: {context.get_target_info().health:.1f}%")
        
        # 执行APL
        result = executor.execute_apl(action_list, context)
        
        if result.action_taken:
            print(f"→ 执行: {result.action_taken.action_name}")
        else:
            print("→ 等待中...")
        
        # 模拟战斗进展
        context.advance_time(1.5)
        
        # 目标掉血
        target = context.get_target_info()
        if target:
            new_health = max(0, target.health - 5.0)
            context.set_target_info(TargetInfo(target.name, new_health, target.max_health, target.distance))
        
        # 法力值恢复
        current_mana = context.get_resource("mana")
        context.set_resource("mana", min(200.0, current_mana + 15.0))
        
        # 检查战斗结束
        if context.get_target_info().health <= 0:
            print("\n目标已击败！")
            break
    
    # 显示执行统计
    stats = executor.get_stats()
    print(f"\n执行统计:")
    print(f"总评估次数: {stats.total_evaluations}")
    print(f"成功执行: {stats.successful_actions}")
    print(f"失败次数: {stats.failed_actions}")
    print(f"平均评估时间: {stats.average_evaluation_time:.6f}秒")


def example_scheduler_integration():
    """调度器集成示例"""
    print("\n\n=== 调度器集成示例 ===")
    
    # 创建调度器
    scheduler = APLScheduler()
    rotation_scheduler = APLRotationScheduler(scheduler)
    
    # 创建游戏上下文
    context = GameContext()
    context.set_resource("health", 100.0)
    context.set_resource("mana", 200.0)
    
    # 创建APL执行器
    evaluator = ExpressionEvaluator()
    registry = ActionRegistry()
    fire_mage_handler = FireMageActionHandler()
    
    registry.register_action("fireball", fire_mage_handler, ActionCategory.DAMAGE)
    registry.register_action("frostbolt", fire_mage_handler, ActionCategory.DAMAGE)
    
    executor = APLExecutor(evaluator, registry)
    
    # 简单的APL
    simple_apl = """
    actions=fireball,if=mana>50
    actions+=/frostbolt,if=mana>40
    """
    
    parser = APLParser()
    action_list = parser.parse(simple_apl)
    
    # 定义轮换回调
    def rotation_callback(event, sched):
        result = executor.execute_apl(action_list, context)
        if result.action_taken:
            print(f"时间 {sched.current_time:.1f}s: 执行 {result.action_taken.action_name}")
        
        # 恢复法力值
        current_mana = context.get_resource("mana")
        context.set_resource("mana", min(200.0, current_mana + 10.0))
    
    # 调度定期轮换检查
    scheduler.schedule_timer(1.5, rotation_callback, repeating=True)
    
    # 调度法力值恢复事件
    def mana_regen(event, sched):
        current_mana = context.get_resource("mana")
        context.set_resource("mana", min(200.0, current_mana + 5.0))
    
    scheduler.schedule_timer(0.5, mana_regen, repeating=True)
    
    print("开始调度器驱动的APL轮换...")
    
    # 运行调度器
    stats = scheduler.run_for_duration(15.0, 0.1)
    
    print(f"\n调度器统计:")
    print(f"处理事件: {stats.processed_events}")
    print(f"模拟时间: {stats.simulation_time:.1f}秒")


def example_expression_evaluation():
    """表达式求值示例"""
    print("\n\n=== 表达式求值示例 ===")
    
    # 创建上下文
    context = GameContext()
    context.set_resource("health", 75.0)
    context.set_resource("mana", 120.0)
    context.set_buff("combustion", 8.0, {"damage_bonus": 50})
    context.set_cooldown("fireball", 1.5)
    context.set_target_info(TargetInfo("Boss", 60.0, 100.0, 3.0))
    
    evaluator = ExpressionEvaluator()
    
    # 测试各种表达式
    test_expressions = [
        "mana > 50",
        "health < 80",
        "buff.combustion.up",
        "!cooldown.fireball.up",
        "target.health < 25",
        "mana > 50 & !cooldown.fireball.up",
        "buff.combustion.up | target.health < 30",
        "(mana > 100) & (health > 50) & buff.combustion.up",
        "target.distance <= 5.0",
        "cooldown.fireball.remains < 1.0"
    ]
    
    print("当前状态:")
    print(f"生命值: {context.get_resource('health')}")
    print(f"法力值: {context.get_resource('mana')}")
    print(f"燃烧Buff: {'是' if context.has_buff('combustion') else '否'}")
    print(f"火球术冷却: {context.get_cooldown_remaining('fireball'):.1f}秒")
    print(f"目标生命值: {context.get_target_info().health}%")
    print(f"目标距离: {context.get_target_info().distance}码")
    
    print("\n表达式求值结果:")
    for expr_text in test_expressions:
        try:
            # 解析表达式
            lexer = APLLexer()
            tokens = lexer.tokenize(expr_text)
            
            parser = APLParser()
            expr = parser.parse_expression(tokens)
            
            # 求值
            result = evaluator.evaluate(expr, context)
            print(f"{expr_text:35} → {result}")
            
        except Exception as e:
            print(f"{expr_text:35} → 错误: {e}")


def main():
    """主函数 - 运行所有示例"""
    print("APL系统完整示例")
    print("=" * 50)
    
    try:
        # 运行各个示例
        example_basic_usage()
        example_advanced_apl()
        example_scheduler_integration()
        example_expression_evaluation()
        
        print("\n\n=== 所有示例执行完成 ===")
        print("APL系统功能演示成功！")
        
    except Exception as e:
        print(f"示例执行出错: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()