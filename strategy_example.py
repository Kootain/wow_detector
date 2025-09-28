#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
游戏策略系统使用示例

本文件展示了如何使用 strategy.py 中实现的复杂游戏行动策略系统。
包括基本使用、自定义策略、配置管理等完整示例。
"""

from strategy import (
    # 基础数据模型
    State, Action, GameState, Priority,
    
    # 条件判断系统
    HealthCondition, ManaCondition, BuffCondition, CooldownCondition,
    CombatCondition, CastingCondition, CompositeCondition,
    
    # 策略系统
    EmergencyHealingStrategy, BuffMaintenanceStrategy, DamageRotationStrategy,
    ManaManagementStrategy, PaladinHealingStrategy, MageFireStrategy,
    DungeonStrategy, RaidStrategy, PvPStrategy,
    
    # 配置和管理系统
    StrategyConfig, StrategyConfigManager, AdaptiveStrategyManager,
    
    # 决策引擎
    DecisionEngine, PriorityAction
)

def create_sample_game_state() -> State:
    """创建示例游戏状态"""
    return State(
        health_percent=75,
        mana_percent=60,
        target_health_percent=45,
        in_combat=True,
        is_casting=False,
        buffs={21562: 25000},  # 真言术：韧 剩余25秒
        debuffs={},
        cooldowns={2061: 0, 139: 5000},  # 快速治疗可用，恢复还有5秒
        global_cooldown_ms=0,
        combat_time_ms=15000,  # 战斗进行了15秒
        last_spell_id=0,
        spell_queue=[],
        player_class="PRIEST",
        player_spec="Holy",
        player_level=70,
        zone_type="dungeon",
        group_size=5,
        role="healer"
    )

def basic_usage_example():
    """基础使用示例"""
    print("=== 基础使用示例 ===")
    
    # 1. 创建游戏状态
    game_state = create_sample_game_state()
    print(f"当前状态: 血量{game_state.health_percent}%, 法力{game_state.mana_percent}%, 战斗中: {game_state.in_combat}")
    
    # 2. 创建条件判断
    low_health = HealthCondition(threshold=80)
    low_mana = ManaCondition(threshold=30)
    in_combat = CombatCondition()
    
    print(f"血量低于80%: {low_health.evaluate(game_state)}")
    print(f"法力低于30%: {low_mana.evaluate(game_state)}")
    print(f"在战斗中: {in_combat.evaluate(game_state)}")
    
    # 3. 创建复合条件
    emergency_condition = CompositeCondition(
        conditions=[low_health, in_combat],
        operator='AND'
    )
    print(f"紧急情况(低血量且在战斗): {emergency_condition.evaluate(game_state)}")
    
    # 4. 使用决策引擎
    engine = DecisionEngine()
    
    # 添加优先级动作
    engine.add_action(PriorityAction(
        action=Action(spell_id=2061, target_type="self"),  # 快速治疗
        priority=Priority.HIGH.value,
        condition=low_health
    ))
    
    engine.add_action(PriorityAction(
        action=Action(spell_id=33447, target_type="self"),  # 法力药水
        priority=Priority.MEDIUM.value,
        condition=low_mana
    ))
    
    # 获取最佳动作
    best_action = engine.get_best_action(game_state)
    if best_action:
        print(f"推荐动作: 施放法术 {best_action.spell_id}")
    else:
        print("没有合适的动作")
    
    print()

def strategy_usage_example():
    """策略使用示例"""
    print("=== 策略使用示例 ===")
    
    game_state = create_sample_game_state()
    
    # 1. 使用紧急治疗策略
    emergency_strategy = EmergencyHealingStrategy(heal_spell_id=2061)
    if emergency_strategy.can_execute(game_state):
        actions = emergency_strategy.get_actions(game_state)
        print(f"紧急治疗策略推荐: {len(actions)} 个动作")
        for action in actions:
            print(f"  - 施放法术 {action.spell_id}")
    
    # 2. 使用Buff维护策略
    buff_strategy = BuffMaintenanceStrategy(
        buff_spell_id=21562,  # 真言术：韧
        buff_duration_ms=30000
    )
    if buff_strategy.can_execute(game_state):
        actions = buff_strategy.get_actions(game_state)
        print(f"Buff维护策略推荐: {len(actions)} 个动作")
    
    # 3. 使用职业特定策略
    paladin_strategy = PaladinHealingStrategy()
    # 修改状态为圣骑士
    paladin_state = State(
        health_percent=60,
        mana_percent=80,
        target_health_percent=30,
        in_combat=True,
        is_casting=False,
        buffs={},
        debuffs={},
        cooldowns={},
        global_cooldown_ms=0,
        combat_time_ms=10000,
        last_spell_id=0,
        spell_queue=[],
        player_class="PALADIN",
        player_spec="Holy",
        player_level=70,
        zone_type="dungeon",
        group_size=5,
        role="healer"
    )
    
    if paladin_strategy.can_execute(paladin_state):
        actions = paladin_strategy.get_actions(paladin_state)
        print(f"圣骑士治疗策略推荐: {len(actions)} 个动作")
        for action in actions:
            print(f"  - 施放法术 {action.spell_id}")
    
    print()

def configuration_management_example():
    """配置管理示例"""
    print("=== 配置管理示例 ===")
    
    # 1. 创建配置管理器
    config_manager = StrategyConfigManager()
    config_manager.load_default_configs()
    
    print(f"加载了 {len(config_manager.configs)} 个默认配置")
    
    # 2. 查看配置
    for name, config in config_manager.configs.items():
        print(f"配置: {name}, 启用: {config.enabled}, 优先级: {config.priority}, 标签: {config.tags}")
    
    # 3. 根据标签筛选配置
    healing_configs = config_manager.get_configs_by_tags(['healing'])
    print(f"\n治疗相关配置: {[c.name for c in healing_configs]}")
    
    # 4. 根据职业筛选配置
    paladin_configs = config_manager.get_configs_by_class('PALADIN')
    print(f"圣骑士配置: {[c.name for c in paladin_configs]}")
    
    # 5. 创建自定义配置
    custom_config = StrategyConfig(
        name="custom_healing",
        priority=Priority.HIGH.value,
        parameters={'heal_spell_id': 2050},  # 治疗术
        tags=['healing', 'custom'],
        conditions={'health_threshold': 50},
        required_class="PRIEST"
    )
    config_manager.add_config(custom_config)
    print(f"\n添加自定义配置: {custom_config.name}")
    
    # 6. 修改配置
    config_manager.update_config('emergency_healing', priority=Priority.EMERGENCY.value)
    print("更新紧急治疗配置优先级")
    
    # 7. 导出和导入配置
    exported_configs = config_manager.export_configs()
    print(f"\n导出配置数量: {len(exported_configs)}")
    
    print()

def adaptive_manager_example():
    """自适应管理器示例"""
    print("=== 自适应管理器示例 ===")
    
    # 1. 创建自适应管理器
    manager = AdaptiveStrategyManager()
    manager.initialize()
    
    print(f"管理器状态: {manager.get_manager_status()}")
    
    # 2. 模拟游戏状态变化
    game_states = [
        # 战斗开始 - 满血满蓝
        State(
            health_percent=100, mana_percent=100, target_health_percent=100,
            in_combat=True, is_casting=False, buffs={}, debuffs={}, cooldowns={},
            global_cooldown_ms=0, combat_time_ms=1000, last_spell_id=0, spell_queue=[],
            player_class="MAGE", player_spec="Fire", player_level=70,
            zone_type="dungeon", group_size=5, role="damage"
        ),
        # 战斗中期 - 血量下降
        State(
            health_percent=60, mana_percent=80, target_health_percent=70,
            in_combat=True, is_casting=False, buffs={}, debuffs={}, cooldowns={},
            global_cooldown_ms=0, combat_time_ms=15000, last_spell_id=0, spell_queue=[],
            player_class="MAGE", player_spec="Fire", player_level=70,
            zone_type="dungeon", group_size=5, role="damage"
        ),
        # 紧急情况 - 低血量
        State(
            health_percent=25, mana_percent=40, target_health_percent=50,
            in_combat=True, is_casting=False, buffs={}, debuffs={}, cooldowns={},
            global_cooldown_ms=0, combat_time_ms=30000, last_spell_id=0, spell_queue=[],
            player_class="MAGE", player_spec="Fire", player_level=70,
            zone_type="dungeon", group_size=5, role="damage"
        )
    ]
    
    for i, state in enumerate(game_states, 1):
        print(f"\n--- 游戏状态 {i} ---")
        print(f"血量: {state.health_percent}%, 法力: {state.mana_percent}%")
        
        # 更新游戏状态
        manager.update_game_state(state)
        
        # 获取推荐动作
        next_action = manager.get_next_action(state)
        if next_action:
            print(f"推荐动作: 施放法术 {next_action.spell_id}")
        else:
            print("没有推荐动作")
        
        # 显示当前活跃策略
        active_strategies = manager.get_active_strategies()
        print(f"活跃策略: {active_strategies}")
    
    # 3. 动态调整策略
    print("\n--- 动态调整策略 ---")
    
    # 禁用某个策略
    manager.disable_strategy('mage_fire')
    print("禁用法师火系策略")
    
    # 调整策略优先级
    manager.set_strategy_priority('emergency_healing', Priority.EMERGENCY.value)
    print("提高紧急治疗优先级")
    
    # 添加自定义策略配置
    custom_config = StrategyConfig(
        name="custom_mage_strategy",
        priority=Priority.HIGH.value,
        parameters={'spell_rotation': [133, 2136, 44614]},  # 火球术、冰霜新星、火焰冲击
        tags=['damage', 'mage', 'custom'],
        required_class="MAGE"
    )
    manager.add_custom_strategy_config(custom_config)
    print("添加自定义法师策略")
    
    # 显示最终状态
    final_status = manager.get_manager_status()
    print(f"\n最终管理器状态: {final_status}")
    
    print()

def advanced_condition_example():
    """高级条件判断示例"""
    print("=== 高级条件判断示例 ===")
    
    game_state = create_sample_game_state()
    
    # 1. 复杂的复合条件
    # 紧急治疗条件：(血量<30% 或 目标血量<20%) 且 在战斗中 且 不在施法
    emergency_heal_condition = CompositeCondition(
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
    
    print(f"紧急治疗条件满足: {emergency_heal_condition.evaluate(game_state)}")
    
    # 2. 冷却时间条件
    heal_ready = CooldownCondition(spell_id=2061, max_cooldown_ms=0)
    print(f"快速治疗可用: {heal_ready.evaluate(game_state)}")
    
    # 3. Buff条件
    has_fortitude = BuffCondition(buff_id=21562, min_duration_ms=10000)
    print(f"有真言术：韧(>10秒): {has_fortitude.evaluate(game_state)}")
    
    print()

def performance_optimization_tips():
    """性能优化建议"""
    print("=== 性能优化建议 ===")
    
    tips = [
        "1. 合理设置策略优先级，避免不必要的计算",
        "2. 使用条件缓存，避免重复评估相同条件",
        "3. 限制同时活跃的策略数量",
        "4. 定期清理过期的动作和状态",
        "5. 使用配置组管理相关策略",
        "6. 根据游戏场景动态启用/禁用策略",
        "7. 监控策略执行性能，及时调整"
    ]
    
    for tip in tips:
        print(tip)
    
    print()

def main():
    """主函数 - 运行所有示例"""
    print("游戏策略系统完整使用示例")
    print("=" * 50)
    
    try:
        basic_usage_example()
        strategy_usage_example()
        configuration_management_example()
        adaptive_manager_example()
        advanced_condition_example()
        performance_optimization_tips()
        
        print("所有示例运行完成！")
        
    except Exception as e:
        print(f"运行示例时出错: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()