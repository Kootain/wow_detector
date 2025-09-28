#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
APL系统测试模块

包含对APL系统各个组件的单元测试和集成测试。
确保系统的正确性和稳定性。
"""

import unittest
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from lexer import APLLexer, TokenType, LexerError
from parser import APLParser, ParseError
from ast_nodes import *
from context import GameContext, ResourceInfo, BuffInfo, CooldownInfo, TargetInfo
from evaluator import ExpressionEvaluator
from action_registry import ActionRegistry, ActionHandler, ActionCategory, ActionResult
from executor import APLExecutor, ExecutionMode
from scheduler import APLScheduler, EventType, EventPriority


class TestActionHandler(ActionHandler):
    """测试用动作处理器"""
    
    def __init__(self):
        self.executed_actions = []
    
    def execute(self, context, **kwargs) -> ActionResult:
        action_name = kwargs.get('action_name', 'test_action')
        self.executed_actions.append(action_name)
        return ActionResult.SUCCESS


class TestLexer(unittest.TestCase):
    """词法器测试"""
    
    def setUp(self):
        self.lexer = APLLexer()
    
    def test_basic_tokens(self):
        """测试基本token识别"""
        text = "actions=fireball,if=mana>50"
        tokens = self.lexer.tokenize(text)
        
        expected_types = [
            TokenType.IDENTIFIER,  # actions
            TokenType.ASSIGN,      # =
            TokenType.IDENTIFIER,  # fireball
            TokenType.COMMA,       # ,
            TokenType.IDENTIFIER,  # if
            TokenType.ASSIGN,      # =
            TokenType.IDENTIFIER,  # mana
            TokenType.GT,          # >
            TokenType.NUMBER,      # 50
            TokenType.EOF
        ]
        
        actual_types = [token.type for token in tokens]
        self.assertEqual(actual_types, expected_types)
    
    def test_numbers(self):
        """测试数字识别"""
        text = "123 45.67 0.5 100"
        tokens = self.lexer.tokenize(text)
        
        numbers = [token for token in tokens if token.type == TokenType.NUMBER]
        self.assertEqual(len(numbers), 4)
        self.assertEqual(numbers[0].value, 123)
        self.assertEqual(numbers[1].value, 45.67)
        self.assertEqual(numbers[2].value, 0.5)
        self.assertEqual(numbers[3].value, 100)
    
    def test_strings(self):
        """测试字符串识别"""
        text = '"hello world" "test"'
        tokens = self.lexer.tokenize(text)
        
        strings = [token for token in tokens if token.type == TokenType.STRING]
        self.assertEqual(len(strings), 2)
        self.assertEqual(strings[0].value, "hello world")
        self.assertEqual(strings[1].value, "test")
    
    def test_comments(self):
        """测试注释处理"""
        text = """
        # 这是注释
        actions=fireball  # 行末注释
        """
        tokens = self.lexer.tokenize(text)
        
        # 注释应该被忽略
        non_eof_tokens = [token for token in tokens if token.type != TokenType.EOF]
        self.assertEqual(len(non_eof_tokens), 3)  # actions, =, fireball
    
    def test_operators(self):
        """测试操作符识别"""
        text = "+ - * / % == != < <= > >= & | !"
        tokens = self.lexer.tokenize(text)
        
        expected_types = [
            TokenType.PLUS, TokenType.MINUS, TokenType.MULTIPLY, TokenType.DIVIDE, TokenType.MODULO,
            TokenType.EQ, TokenType.NE, TokenType.LT, TokenType.LE, TokenType.GT, TokenType.GE,
            TokenType.AND, TokenType.OR, TokenType.NOT, TokenType.EOF
        ]
        
        actual_types = [token.type for token in tokens]
        self.assertEqual(actual_types, expected_types)


class TestParser(unittest.TestCase):
    """解析器测试"""
    
    def setUp(self):
        self.parser = APLParser()
    
    def test_simple_action(self):
        """测试简单动作解析"""
        text = "actions=fireball"
        action_list = self.parser.parse(text)
        
        self.assertEqual(len(action_list.actions), 1)
        action = action_list.actions[0]
        self.assertEqual(action.action_name, "fireball")
        self.assertIsNone(action.condition)
    
    def test_action_with_condition(self):
        """测试带条件的动作解析"""
        text = "actions=fireball,if=mana>50"
        action_list = self.parser.parse(text)
        
        self.assertEqual(len(action_list.actions), 1)
        action = action_list.actions[0]
        self.assertEqual(action.action_name, "fireball")
        self.assertIsNotNone(action.condition)
    
    def test_multiple_actions(self):
        """测试多个动作解析"""
        text = """
        actions=fireball,if=mana>50
        actions+=/frostbolt,if=mana>30
        actions+=/wait
        """
        action_list = self.parser.parse(text)
        
        self.assertEqual(len(action_list.actions), 3)
        self.assertEqual(action_list.actions[0].action_name, "fireball")
        self.assertEqual(action_list.actions[1].action_name, "frostbolt")
        self.assertEqual(action_list.actions[2].action_name, "wait")
    
    def test_expression_parsing(self):
        """测试表达式解析"""
        expressions = [
            "mana > 50",
            "health < 30 & mana > 100",
            "!buff.combustion.up",
            "(health > 50) | (mana < 20)",
            "cooldown.fireball.remains <= 1.0"
        ]
        
        for expr_text in expressions:
            tokens = APLLexer().tokenize(expr_text)
            expr = self.parser.parse_expression(tokens)
            self.assertIsNotNone(expr)
    
    def test_invalid_syntax(self):
        """测试无效语法处理"""
        invalid_texts = [
            "actions=",  # 缺少动作名
            "actions=fireball,if=",  # 缺少条件
            "actions=fireball,if=mana>",  # 不完整的表达式
        ]
        
        for text in invalid_texts:
            with self.assertRaises(ParseError):
                self.parser.parse(text)


class TestContext(unittest.TestCase):
    """上下文测试"""
    
    def setUp(self):
        self.context = GameContext()
    
    def test_resource_management(self):
        """测试资源管理"""
        # 设置资源
        self.context.set_resource("health", 100.0)
        self.context.set_resource("mana", 200.0)
        
        # 获取资源
        self.assertEqual(self.context.get_resource("health"), 100.0)
        self.assertEqual(self.context.get_resource("mana"), 200.0)
        self.assertEqual(self.context.get_resource("nonexistent"), 0.0)
    
    def test_buff_management(self):
        """测试Buff管理"""
        # 设置Buff
        self.context.set_buff("combustion", 10.0, {"damage_bonus": 50})
        
        # 检查Buff
        self.assertTrue(self.context.has_buff("combustion"))
        self.assertFalse(self.context.has_buff("nonexistent"))
        
        buff_info = self.context.get_buff_info("combustion")
        self.assertIsNotNone(buff_info)
        self.assertEqual(buff_info.remaining_time, 10.0)
        self.assertEqual(buff_info.data["damage_bonus"], 50)
        
        # 时间推进
        self.context.advance_time(5.0)
        buff_info = self.context.get_buff_info("combustion")
        self.assertEqual(buff_info.remaining_time, 5.0)
        
        # Buff过期
        self.context.advance_time(6.0)
        self.assertFalse(self.context.has_buff("combustion"))
    
    def test_cooldown_management(self):
        """测试冷却时间管理"""
        # 设置冷却
        self.context.set_cooldown("fireball", 3.0)
        
        # 检查冷却
        self.assertEqual(self.context.get_cooldown_remaining("fireball"), 3.0)
        self.assertFalse(self.context.is_cooldown_ready("fireball"))
        
        # 时间推进
        self.context.advance_time(2.0)
        self.assertEqual(self.context.get_cooldown_remaining("fireball"), 1.0)
        
        # 冷却完成
        self.context.advance_time(2.0)
        self.assertEqual(self.context.get_cooldown_remaining("fireball"), 0.0)
        self.assertTrue(self.context.is_cooldown_ready("fireball"))
    
    def test_target_info(self):
        """测试目标信息"""
        target = TargetInfo("Boss", 75.0, 100.0, 5.0)
        self.context.set_target_info(target)
        
        retrieved_target = self.context.get_target_info()
        self.assertEqual(retrieved_target.name, "Boss")
        self.assertEqual(retrieved_target.health, 75.0)
        self.assertEqual(retrieved_target.max_health, 100.0)
        self.assertEqual(retrieved_target.distance, 5.0)


class TestEvaluator(unittest.TestCase):
    """表达式求值器测试"""
    
    def setUp(self):
        self.evaluator = ExpressionEvaluator()
        self.context = GameContext()
        self.context.set_resource("health", 80.0)
        self.context.set_resource("mana", 120.0)
        self.context.set_buff("combustion", 5.0)
        self.context.set_cooldown("fireball", 2.0)
        self.context.set_target_info(TargetInfo("Enemy", 60.0, 100.0, 3.0))
    
    def test_literal_evaluation(self):
        """测试字面量求值"""
        # 数字
        result = self.evaluator.evaluate(create_literal(42), self.context)
        self.assertEqual(result, 42)
        
        # 字符串
        result = self.evaluator.evaluate(create_literal("test"), self.context)
        self.assertEqual(result, "test")
        
        # 布尔值
        result = self.evaluator.evaluate(create_literal(True), self.context)
        self.assertEqual(result, True)
    
    def test_identifier_evaluation(self):
        """测试标识符求值"""
        # 资源
        result = self.evaluator.evaluate(create_identifier("health"), self.context)
        self.assertEqual(result, 80.0)
        
        result = self.evaluator.evaluate(create_identifier("mana"), self.context)
        self.assertEqual(result, 120.0)
    
    def test_binary_operations(self):
        """测试二元运算"""
        # 算术运算
        expr = create_binary(create_literal(10), "+", create_literal(5))
        result = self.evaluator.evaluate(expr, self.context)
        self.assertEqual(result, 15)
        
        # 比较运算
        expr = create_binary(create_identifier("health"), ">", create_literal(50))
        result = self.evaluator.evaluate(expr, self.context)
        self.assertEqual(result, True)
        
        # 逻辑运算
        expr = create_binary(
            create_binary(create_identifier("health"), ">", create_literal(50)),
            "&",
            create_binary(create_identifier("mana"), ">", create_literal(100))
        )
        result = self.evaluator.evaluate(expr, self.context)
        self.assertEqual(result, True)
    
    def test_function_calls(self):
        """测试函数调用"""
        # buff.combustion.up
        expr = create_function_call("buff.combustion.up", [])
        result = self.evaluator.evaluate(expr, self.context)
        self.assertEqual(result, True)
        
        # cooldown.fireball.remains
        expr = create_function_call("cooldown.fireball.remains", [])
        result = self.evaluator.evaluate(expr, self.context)
        self.assertEqual(result, 2.0)
        
        # target.health
        expr = create_function_call("target.health", [])
        result = self.evaluator.evaluate(expr, self.context)
        self.assertEqual(result, 60.0)


class TestActionRegistry(unittest.TestCase):
    """动作注册系统测试"""
    
    def setUp(self):
        self.registry = ActionRegistry()
        self.handler = TestActionHandler()
    
    def test_action_registration(self):
        """测试动作注册"""
        # 注册动作
        self.registry.register_action(
            "fireball", self.handler, ActionCategory.DAMAGE,
            description="火球术", tags=["spell", "fire"]
        )
        
        # 检查注册
        self.assertTrue(self.registry.has_action("fireball"))
        self.assertFalse(self.registry.has_action("nonexistent"))
        
        # 获取动作
        action = self.registry.get_action("fireball")
        self.assertIsNotNone(action)
        self.assertEqual(action.name, "fireball")
        self.assertEqual(action.category, ActionCategory.DAMAGE)
    
    def test_action_execution(self):
        """测试动作执行"""
        self.registry.register_action("test_action", self.handler, ActionCategory.UTILITY)
        
        context = GameContext()
        result = self.registry.execute_action("test_action", context)
        
        self.assertEqual(result, ActionResult.SUCCESS)
        self.assertIn("test_action", self.handler.executed_actions)
    
    def test_action_filtering(self):
        """测试动作筛选"""
        # 注册多个动作
        actions_data = [
            ("fireball", ActionCategory.DAMAGE, ["spell", "fire"]),
            ("heal", ActionCategory.HEALING, ["spell", "holy"]),
            ("shield", ActionCategory.DEFENSIVE, ["spell", "protection"]),
            ("buff", ActionCategory.BUFF, ["spell", "enhancement"])
        ]
        
        for name, category, tags in actions_data:
            self.registry.register_action(name, self.handler, category, tags=tags)
        
        # 按类别筛选
        damage_actions = self.registry.get_actions_by_category(ActionCategory.DAMAGE)
        self.assertEqual(len(damage_actions), 1)
        self.assertEqual(damage_actions[0].name, "fireball")
        
        # 按标签筛选
        spell_actions = self.registry.get_actions_by_tag("spell")
        self.assertEqual(len(spell_actions), 4)
        
        fire_actions = self.registry.get_actions_by_tag("fire")
        self.assertEqual(len(fire_actions), 1)
        self.assertEqual(fire_actions[0].name, "fireball")


class TestExecutor(unittest.TestCase):
    """执行器测试"""
    
    def setUp(self):
        self.evaluator = ExpressionEvaluator()
        self.registry = ActionRegistry()
        self.handler = TestActionHandler()
        self.executor = APLExecutor(self.evaluator, self.registry)
        
        # 注册测试动作
        self.registry.register_action("action1", self.handler, ActionCategory.DAMAGE)
        self.registry.register_action("action2", self.handler, ActionCategory.DAMAGE)
    
    def test_simple_execution(self):
        """测试简单执行"""
        # 创建简单的APL
        action_line = ActionLine("action1", None, {})
        action_list = ActionList([action_line])
        
        context = GameContext()
        result = self.executor.execute_apl(action_list, context)
        
        self.assertIsNotNone(result.action_taken)
        self.assertEqual(result.action_taken.action_name, "action1")
        self.assertIn("action1", self.handler.executed_actions)
    
    def test_conditional_execution(self):
        """测试条件执行"""
        # 创建带条件的APL
        condition = create_binary(create_identifier("mana"), ">", create_literal(50))
        action_line = ActionLine("action1", condition, {})
        action_list = ActionList([action_line])
        
        context = GameContext()
        
        # 条件不满足
        context.set_resource("mana", 30.0)
        result = self.executor.execute_apl(action_list, context)
        self.assertIsNone(result.action_taken)
        
        # 条件满足
        context.set_resource("mana", 80.0)
        result = self.executor.execute_apl(action_list, context)
        self.assertIsNotNone(result.action_taken)
        self.assertEqual(result.action_taken.action_name, "action1")
    
    def test_priority_execution(self):
        """测试优先级执行"""
        # 创建多个动作的APL
        condition1 = create_binary(create_identifier("mana"), ">", create_literal(100))  # 不满足
        condition2 = create_binary(create_identifier("mana"), ">", create_literal(50))   # 满足
        
        action_list = ActionList([
            ActionLine("action1", condition1, {}),
            ActionLine("action2", condition2, {})
        ])
        
        context = GameContext()
        context.set_resource("mana", 80.0)
        
        result = self.executor.execute_apl(action_list, context)
        
        # 应该执行第二个动作（第一个条件不满足）
        self.assertIsNotNone(result.action_taken)
        self.assertEqual(result.action_taken.action_name, "action2")


class TestScheduler(unittest.TestCase):
    """调度器测试"""
    
    def setUp(self):
        self.scheduler = APLScheduler()
    
    def test_event_scheduling(self):
        """测试事件调度"""
        executed_events = []
        
        def test_callback(event, scheduler):
            executed_events.append(event.event_id)
        
        # 调度事件
        event_id1 = self.scheduler.schedule_timer(1.0, test_callback)
        event_id2 = self.scheduler.schedule_timer(2.0, test_callback)
        
        # 检查待处理事件
        pending = self.scheduler.get_pending_events()
        self.assertEqual(len(pending), 2)
        
        # 推进时间并处理事件
        self.scheduler.advance_time(1.5)
        processed = self.scheduler.process_events()
        
        self.assertEqual(processed, 1)
        self.assertEqual(len(executed_events), 1)
        self.assertEqual(executed_events[0], event_id1)
        
        # 继续推进时间
        self.scheduler.advance_time(1.0)
        processed = self.scheduler.process_events()
        
        self.assertEqual(processed, 1)
        self.assertEqual(len(executed_events), 2)
        self.assertEqual(executed_events[1], event_id2)
    
    def test_repeating_events(self):
        """测试重复事件"""
        executed_count = [0]
        
        def repeat_callback(event, scheduler):
            executed_count[0] += 1
        
        # 调度重复事件
        self.scheduler.schedule_timer(1.0, repeat_callback, repeating=True)
        
        # 运行一段时间
        self.scheduler.run_for_duration(3.5, 0.1)
        
        # 应该执行3次（1.0s, 2.0s, 3.0s）
        self.assertEqual(executed_count[0], 3)
    
    def test_event_cancellation(self):
        """测试事件取消"""
        executed = [False]
        
        def test_callback(event, scheduler):
            executed[0] = True
        
        # 调度并取消事件
        event_id = self.scheduler.schedule_timer(1.0, test_callback)
        success = self.scheduler.cancel_event(event_id)
        
        self.assertTrue(success)
        
        # 运行调度器
        self.scheduler.run_for_duration(2.0, 0.1)
        
        # 事件不应该被执行
        self.assertFalse(executed[0])


class TestIntegration(unittest.TestCase):
    """集成测试"""
    
    def test_full_apl_execution(self):
        """测试完整APL执行流程"""
        # 创建完整的APL系统
        lexer = APLLexer()
        parser = APLParser()
        evaluator = ExpressionEvaluator()
        registry = ActionRegistry()
        handler = TestActionHandler()
        executor = APLExecutor(evaluator, registry)
        
        # 注册动作
        registry.register_action("fireball", handler, ActionCategory.DAMAGE)
        registry.register_action("frostbolt", handler, ActionCategory.DAMAGE)
        
        # 解析APL
        apl_text = """
        actions=fireball,if=mana>50
        actions+=/frostbolt,if=mana>30
        """
        
        action_list = parser.parse(apl_text)
        
        # 创建上下文
        context = GameContext()
        context.set_resource("mana", 80.0)
        
        # 执行APL
        result = executor.execute_apl(action_list, context)
        
        # 验证结果
        self.assertIsNotNone(result.action_taken)
        self.assertEqual(result.action_taken.action_name, "fireball")
        self.assertIn("fireball", handler.executed_actions)
        
        # 测试法力值不足的情况
        handler.executed_actions.clear()
        context.set_resource("mana", 40.0)
        
        result = executor.execute_apl(action_list, context)
        
        self.assertIsNotNone(result.action_taken)
        self.assertEqual(result.action_taken.action_name, "frostbolt")
        self.assertIn("frostbolt", handler.executed_actions)


def run_all_tests():
    """运行所有测试"""
    # 创建测试套件
    test_classes = [
        TestLexer,
        TestParser,
        TestContext,
        TestEvaluator,
        TestActionRegistry,
        TestExecutor,
        TestScheduler,
        TestIntegration
    ]
    
    suite = unittest.TestSuite()
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    print("APL系统测试")
    print("=" * 50)
    
    success = run_all_tests()
    
    if success:
        print("\n所有测试通过！")
    else:
        print("\n部分测试失败！")
        sys.exit(1)