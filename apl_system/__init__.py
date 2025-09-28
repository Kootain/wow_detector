"""APL (Action Priority List) System

A Python implementation of SimulationCraft's APL system for game action prioritization.

This module provides:
- APL syntax parsing and evaluation
- Expression evaluation engine
- Action priority decision making
- Flexible state context system

Usage:
    from apl_system import APLEngine, APLParser
    
    # Parse APL text
    parser = APLParser()
    action_list = parser.parse(apl_text)
    
    # Create engine and execute
    engine = APLEngine(action_list, context)
    action = engine.get_next_action()
"""

from .lexer import APLLexer
from .parser import APLParser
from .ast_nodes import *
from .evaluator import ExpressionEvaluator
from .context import EvalContext
from .action_registry import ActionRegistry, Action
from .executor import APLExecutor
from .scheduler import APLScheduler

__version__ = "1.0.0"
__author__ = "APL System Team"

__all__ = [
    'APLLexer',
    'APLParser', 
    'ExpressionEvaluator',
    'EvalContext',
    'ActionRegistry',
    'Action',
    'APLExecutor',
    'APLScheduler',
    # AST nodes
    'ExprNode',
    'LiteralNode',
    'IdentifierNode', 
    'UnaryNode',
    'BinaryNode',
    'FunctionCallNode',
    'ActionLine'
]

# Main engine class for convenience
class APLEngine:
    """Main APL Engine - combines all components for easy usage"""
    
    def __init__(self, apl_text: str = None, context: EvalContext = None):
        self.lexer = APLLexer()
        self.parser = APLParser()
        self.evaluator = ExpressionEvaluator()
        self.registry = ActionRegistry()
        self.executor = APLExecutor(self.evaluator, self.registry)
        self.scheduler = APLScheduler()
        
        self.action_list = None
        self.context = context
        
        if apl_text:
            self.load_apl(apl_text)
    
    def load_apl(self, apl_text: str):
        """Parse and load APL text"""
        tokens = self.lexer.tokenize(apl_text)
        self.action_list = self.parser.parse(tokens)
        return self.action_list
    
    def set_context(self, context: EvalContext):
        """Set evaluation context"""
        self.context = context
    
    def get_next_action(self):
        """Get next action to execute based on APL priority"""
        if not self.action_list or not self.context:
            return None
        return self.executor.execute_cycle(self.action_list, self.context)
    
    def register_action(self, name: str, action: 'Action'):
        """Register a new action"""
        self.registry.register(name, action)