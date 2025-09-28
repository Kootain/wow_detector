"""AST Nodes - Abstract Syntax Tree node definitions for APL expressions

Defines the node types for representing parsed APL expressions:
- ExprNode: Base class for all expression nodes
- LiteralNode: Numeric and string literals
- IdentifierNode: Variable references with dot notation
- UnaryNode: Unary operations (+, -, !)
- BinaryNode: Binary operations (+, -, *, %, ==, !=, <, >, etc.)
- FunctionCallNode: Function calls with arguments
- ActionLine: Represents a complete APL action line
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, Union
from dataclasses import dataclass, field
from enum import Enum


class NodeType(Enum):
    """Types of AST nodes"""
    LITERAL = "LITERAL"
    IDENTIFIER = "IDENTIFIER"
    UNARY = "UNARY"
    BINARY = "BINARY"
    FUNCTION_CALL = "FUNCTION_CALL"
    ACTION_LINE = "ACTION_LINE"


class ExprNode(ABC):
    """Base class for all expression nodes"""
    
    def __init__(self, node_type: NodeType, line: int = 0, column: int = 0):
        self.node_type = node_type
        self.line = line
        self.column = column
    
    @abstractmethod
    def evaluate(self, context) -> float:
        """Evaluate this expression node in the given context"""
        pass
    
    @abstractmethod
    def __str__(self) -> str:
        """String representation for debugging"""
        pass
    
    def __repr__(self) -> str:
        return self.__str__()
    
    def get_dependencies(self) -> List[str]:
        """Get list of identifiers this expression depends on (for optimization)"""
        return []


class LiteralNode(ExprNode):
    """Represents numeric or string literals"""
    
    def __init__(self, value: Union[float, int, str], line: int = 0, column: int = 0):
        super().__init__(NodeType.LITERAL, line, column)
        self.value = value
    
    def evaluate(self, context) -> float:
        """Return the literal value as float (0.0 for empty strings)"""
        if isinstance(self.value, str):
            # String literals evaluate to 0.0 unless they represent numbers
            try:
                return float(self.value)
            except ValueError:
                return 0.0 if not self.value else 1.0  # Empty string = 0, non-empty = 1
        return float(self.value)
    
    def __str__(self) -> str:
        if isinstance(self.value, str):
            return f'"\{self.value}"'
        return str(self.value)


class IdentifierNode(ExprNode):
    """Represents variable references with dot notation (e.g., buff.arcane_power.up)"""
    
    def __init__(self, parts: List[str], line: int = 0, column: int = 0):
        super().__init__(NodeType.IDENTIFIER, line, column)
        self.parts = parts  # e.g., ["buff", "arcane_power", "up"]
    
    def evaluate(self, context) -> float:
        """Resolve identifier through context"""
        if not context:
            return 0.0
        
        try:
            return context.resolve_identifier(self.parts)
        except Exception:
            # If resolution fails, return 0.0 (SimC default behavior)
            return 0.0
    
    def get_dependencies(self) -> List[str]:
        """Return the full identifier path as dependency"""
        return [".".join(self.parts)]
    
    def __str__(self) -> str:
        return ".".join(self.parts)


class UnaryNode(ExprNode):
    """Represents unary operations (+expr, -expr, !expr)"""
    
    def __init__(self, operator: str, operand: ExprNode, line: int = 0, column: int = 0):
        super().__init__(NodeType.UNARY, line, column)
        self.operator = operator  # "+", "-", "!"
        self.operand = operand
    
    def evaluate(self, context) -> float:
        """Evaluate unary operation"""
        operand_value = self.operand.evaluate(context)
        
        if self.operator == "+":
            return operand_value
        elif self.operator == "-":
            return -operand_value
        elif self.operator == "!":
            # Logical NOT: 0 if operand != 0, 1 if operand == 0
            return 1.0 if operand_value == 0.0 else 0.0
        else:
            raise ValueError(f"Unknown unary operator: {self.operator}")
    
    def get_dependencies(self) -> List[str]:
        return self.operand.get_dependencies()
    
    def __str__(self) -> str:
        return f"({self.operator}{self.operand})"


class BinaryNode(ExprNode):
    """Represents binary operations (a + b, a == b, etc.)"""
    
    def __init__(self, operator: str, left: ExprNode, right: ExprNode, line: int = 0, column: int = 0):
        super().__init__(NodeType.BINARY, line, column)
        self.operator = operator
        self.left = left
        self.right = right
    
    def evaluate(self, context) -> float:
        """Evaluate binary operation with short-circuit for logical operators"""
        
        # Short-circuit evaluation for logical operators
        if self.operator == "&":  # AND
            left_val = self.left.evaluate(context)
            if left_val == 0.0:
                return 0.0  # Short-circuit: false & anything = false
            right_val = self.right.evaluate(context)
            return 1.0 if right_val != 0.0 else 0.0
        
        elif self.operator == "|":  # OR
            left_val = self.left.evaluate(context)
            if left_val != 0.0:
                return 1.0  # Short-circuit: true | anything = true
            right_val = self.right.evaluate(context)
            return 1.0 if right_val != 0.0 else 0.0
        
        # For other operators, evaluate both sides
        left_val = self.left.evaluate(context)
        right_val = self.right.evaluate(context)
        
        # Arithmetic operators
        if self.operator == "+":
            return left_val + right_val
        elif self.operator == "-":
            return left_val - right_val
        elif self.operator == "*":
            return left_val * right_val
        elif self.operator == "%":
            return left_val % right_val if right_val != 0 else 0.0
        elif self.operator == "%%":  # SimC's %% operator (different from %)
            return left_val % right_val if right_val != 0 else 0.0
        
        # Comparison operators (return 1.0 for true, 0.0 for false)
        elif self.operator == "=":
            return 1.0 if abs(left_val - right_val) < 1e-9 else 0.0
        elif self.operator == "!=":
            return 1.0 if abs(left_val - right_val) >= 1e-9 else 0.0
        elif self.operator == "<":
            return 1.0 if left_val < right_val else 0.0
        elif self.operator == "<=":
            return 1.0 if left_val <= right_val else 0.0
        elif self.operator == ">":
            return 1.0 if left_val > right_val else 0.0
        elif self.operator == ">=":
            return 1.0 if left_val >= right_val else 0.0
        
        # Logical operators (non-short-circuit versions)
        elif self.operator == "^":  # XOR
            return 1.0 if (left_val != 0.0) != (right_val != 0.0) else 0.0
        
        # Pattern matching operators (simplified - would need string context)
        elif self.operator == "~":  # MATCH
            # For now, treat as equality
            return 1.0 if abs(left_val - right_val) < 1e-9 else 0.0
        elif self.operator == "!~":  # NOT_MATCH
            # For now, treat as inequality
            return 1.0 if abs(left_val - right_val) >= 1e-9 else 0.0
        
        else:
            raise ValueError(f"Unknown binary operator: {self.operator}")
    
    def get_dependencies(self) -> List[str]:
        deps = self.left.get_dependencies()
        deps.extend(self.right.get_dependencies())
        return deps
    
    def __str__(self) -> str:
        return f"({self.left} {self.operator} {self.right})"


class FunctionCallNode(ExprNode):
    """Represents function calls (e.g., floor(x), min(a,b))"""
    
    def __init__(self, name: str, args: List[ExprNode], line: int = 0, column: int = 0):
        super().__init__(NodeType.FUNCTION_CALL, line, column)
        self.name = name
        self.args = args
    
    def evaluate(self, context) -> float:
        """Evaluate function call"""
        # Evaluate all arguments
        arg_values = [arg.evaluate(context) for arg in self.args]
        
        # Built-in functions
        if self.name == "floor":
            if len(arg_values) != 1:
                raise ValueError(f"floor() takes 1 argument, got {len(arg_values)}")
            import math
            return float(math.floor(arg_values[0]))
        
        elif self.name == "ceil":
            if len(arg_values) != 1:
                raise ValueError(f"ceil() takes 1 argument, got {len(arg_values)}")
            import math
            return float(math.ceil(arg_values[0]))
        
        elif self.name == "abs":
            if len(arg_values) != 1:
                raise ValueError(f"abs() takes 1 argument, got {len(arg_values)}")
            return abs(arg_values[0])
        
        elif self.name == "min":
            if len(arg_values) < 1:
                raise ValueError("min() requires at least 1 argument")
            return min(arg_values)
        
        elif self.name == "max":
            if len(arg_values) < 1:
                raise ValueError("max() requires at least 1 argument")
            return max(arg_values)
        
        elif self.name == "round":
            if len(arg_values) not in [1, 2]:
                raise ValueError(f"round() takes 1 or 2 arguments, got {len(arg_values)}")
            if len(arg_values) == 1:
                return float(round(arg_values[0]))
            else:
                return float(round(arg_values[0], int(arg_values[1])))
        
        # Custom functions through context
        elif context and hasattr(context, 'call_function'):
            return context.call_function(self.name, arg_values)
        
        else:
            raise ValueError(f"Unknown function: {self.name}")
    
    def get_dependencies(self) -> List[str]:
        deps = []
        for arg in self.args:
            deps.extend(arg.get_dependencies())
        return deps
    
    def __str__(self) -> str:
        args_str = ", ".join(str(arg) for arg in self.args)
        return f"{self.name}({args_str})"


@dataclass
class ActionLine:
    """Represents a complete APL action line with all options"""
    action_name: str
    options: Dict[str, Any] = field(default_factory=dict)
    
    # Parsed expression options
    if_expr: Optional[ExprNode] = None
    interrupt_if_expr: Optional[ExprNode] = None
    target_if_expr: Optional[ExprNode] = None
    wait_on_ready_expr: Optional[ExprNode] = None
    line_cd_expr: Optional[ExprNode] = None
    
    # Position information
    line: int = 0
    column: int = 0
    filename: str = ""
    
    # Runtime state
    action_ref: Optional[Any] = None  # Reference to actual Action object
    line_cooldown_expires: float = 0.0  # When line cooldown expires
    
    def __post_init__(self):
        """Normalize action name (replace spaces with underscores)"""
        self.action_name = self.action_name.replace(" ", "_").lower()
    
    def is_ready(self, context, current_time: float = 0.0) -> bool:
        """Check if this action line is ready to execute"""
        # Check line cooldown
        if current_time < self.line_cooldown_expires:
            return False
        
        # Check action readiness (if action_ref is bound)
        if self.action_ref and hasattr(self.action_ref, 'ready'):
            if not self.action_ref.ready(context, current_time):
                return False
        
        return True
    
    def check_conditions(self, context) -> bool:
        """Check if all condition expressions are satisfied"""
        # Check if condition
        if self.if_expr:
            if self.if_expr.evaluate(context) == 0.0:
                return False
        
        # Check interrupt_if (if applicable during execution)
        # This would be checked during action execution, not here
        
        # Check target_if (would need target selection logic)
        # This would be handled by the executor
        
        return True
    
    def get_dependencies(self) -> List[str]:
        """Get all identifiers this action line depends on"""
        deps = []
        
        if self.if_expr:
            deps.extend(self.if_expr.get_dependencies())
        if self.interrupt_if_expr:
            deps.extend(self.interrupt_if_expr.get_dependencies())
        if self.target_if_expr:
            deps.extend(self.target_if_expr.get_dependencies())
        if self.wait_on_ready_expr:
            deps.extend(self.wait_on_ready_expr.get_dependencies())
        if self.line_cd_expr:
            deps.extend(self.line_cd_expr.get_dependencies())
        
        return list(set(deps))  # Remove duplicates
    
    def __str__(self) -> str:
        parts = [f"/{self.action_name}"]
        
        for key, value in self.options.items():
            parts.append(f"{key}={value}")
        
        if self.if_expr:
            parts.append(f"if={self.if_expr}")
        if self.interrupt_if_expr:
            parts.append(f"interrupt_if={self.interrupt_if_expr}")
        if self.target_if_expr:
            parts.append(f"target_if={self.target_if_expr}")
        if self.wait_on_ready_expr:
            parts.append(f"wait_on_ready={self.wait_on_ready_expr}")
        if self.line_cd_expr:
            parts.append(f"line_cd={self.line_cd_expr}")
        
        return ",".join(parts)


@dataclass
class ActionList:
    """Represents a complete APL action list"""
    name: str = "default"
    lines: List[ActionLine] = field(default_factory=list)
    
    def add_line(self, line: ActionLine):
        """Add an action line to this list"""
        self.lines.append(line)
    
    def get_dependencies(self) -> List[str]:
        """Get all dependencies for this action list"""
        deps = []
        for line in self.lines:
            deps.extend(line.get_dependencies())
        return list(set(deps))
    
    def __str__(self) -> str:
        lines_str = "\n".join(f"  {line}" for line in self.lines)
        return f"ActionList '{self.name}':\n{lines_str}"


# Utility functions for creating nodes
def literal(value: Union[float, int, str]) -> LiteralNode:
    """Create a literal node"""
    return LiteralNode(value)


def identifier(*parts: str) -> IdentifierNode:
    """Create an identifier node"""
    return IdentifierNode(list(parts))


def unary(op: str, operand: ExprNode) -> UnaryNode:
    """Create a unary operation node"""
    return UnaryNode(op, operand)


def binary(op: str, left: ExprNode, right: ExprNode) -> BinaryNode:
    """Create a binary operation node"""
    return BinaryNode(op, left, right)


def func_call(name: str, *args: ExprNode) -> FunctionCallNode:
    """Create a function call node"""
    return FunctionCallNode(name, list(args))


if __name__ == "__main__":
    # Simple test of AST nodes
    
    # Create expression: buff.arcane_power.up & mana.pct > 50
    expr = binary("&", 
                  identifier("buff", "arcane_power", "up"),
                  binary(">", identifier("mana", "pct"), literal(50)))
    
    print(f"Expression: {expr}")
    print(f"Dependencies: {expr.get_dependencies()}")
    
    # Create action line
    action = ActionLine(
        action_name="arcane_orb",
        if_expr=expr,
        options={"name": "test_action"}
    )
    
    print(f"Action: {action}")