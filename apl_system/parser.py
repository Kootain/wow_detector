"""APL Parser - Converts token stream to Abstract Syntax Tree

Implements a recursive descent parser for APL syntax:
- Parses expressions with proper operator precedence
- Handles function calls, identifiers, literals
- Parses complete action lines with options
- Supports all APL operators and constructs

Grammar (simplified):
  action_line := '/' IDENTIFIER option_list
  option_list := (option (',' option)*)?
  option := IDENTIFIER '=' expression
  expression := logical_or
  logical_or := logical_and ('|' logical_and)*
  logical_and := equality ('&' equality)*
  equality := comparison (('=' | '!=' | '~' | '!~') comparison)*
  comparison := addition (('<' | '<=' | '>' | '>=') addition)*
  addition := multiplication (('+' | '-') multiplication)*
  multiplication := unary (('*' | '%' | '%%') unary)*
  unary := ('+' | '-' | '!')? primary
  primary := NUMBER | STRING | identifier | function_call | '(' expression ')'
  identifier := IDENTIFIER ('.' IDENTIFIER)*
  function_call := IDENTIFIER '(' (expression (',' expression)*)? ')'
"""

from typing import List, Optional, Dict, Any, Union
from lexer import APLLexer, Token, TokenType
from ast_nodes import (
    ExprNode, LiteralNode, IdentifierNode, UnaryNode, BinaryNode, 
    FunctionCallNode, ActionLine, ActionList
)


class ParseError(Exception):
    """Exception raised during parsing"""
    
    def __init__(self, message: str, token: Optional[Token] = None, line: int = 0, column: int = 0):
        self.message = message
        self.token = token
        self.line = line if token is None else token.line
        self.column = column if token is None else token.column
        super().__init__(f"Parse error at line {self.line}, column {self.column}: {message}")


class APLParser:
    """Recursive descent parser for APL syntax"""
    
    def __init__(self):
        self.tokens: List[Token] = []
        self.current = 0
        self.lexer = APLLexer()
    
    def parse(self, text: str) -> ActionList:
        """Parse APL text into an ActionList"""
        self.tokens = self.lexer.tokenize(text)
        self.current = 0
        
        action_list = ActionList()
        
        while not self._is_at_end():
            # Skip empty lines and comments
            if self._check(TokenType.NEWLINE) or self._check(TokenType.COMMENT):
                self._advance()
                continue
            
            # Parse action line
            try:
                action_line = self._parse_action_line()
                if action_line:
                    action_list.add_line(action_line)
            except ParseError as e:
                # Skip to next line on error
                print(f"Warning: {e}")
                self._skip_to_next_line()
        
        return action_list
    
    def parse_expression(self, text: str) -> ExprNode:
        """Parse a single expression (for testing/utility)"""
        self.tokens = self.lexer.tokenize(text)
        self.current = 0
        return self._parse_expression()
    
    def _parse_action_line(self) -> Optional[ActionLine]:
        """Parse a complete action line: /action_name,option1=value1,option2=value2"""
        if not self._check(TokenType.SLASH):
            raise ParseError("Expected '/' at start of action line", self._peek())
        
        self._advance()  # consume '/'
        
        # Parse action name
        if not self._check(TokenType.IDENTIFIER):
            raise ParseError("Expected action name after '/'", self._peek())
        
        action_name = self._advance().value
        
        # Parse options
        options = {}
        if_expr = None
        interrupt_if_expr = None
        target_if_expr = None
        wait_on_ready_expr = None
        line_cd_expr = None
        
        # Parse comma-separated options
        while self._check(TokenType.COMMA):
            self._advance()  # consume ','
            
            if not self._check(TokenType.IDENTIFIER):
                raise ParseError("Expected option name after ','", self._peek())
            
            option_name = self._advance().value
            
            if not self._check(TokenType.ASSIGN):
                raise ParseError(f"Expected '=' after option name '{option_name}'", self._peek())
            
            self._advance()  # consume '='
            
            # Parse option value (expression or simple value)
            if option_name in ["if", "interrupt_if", "target_if", "wait_on_ready", "line_cd"]:
                # These are expression options
                expr = self._parse_expression()
                
                if option_name == "if":
                    if_expr = expr
                elif option_name == "interrupt_if":
                    interrupt_if_expr = expr
                elif option_name == "target_if":
                    target_if_expr = expr
                elif option_name == "wait_on_ready":
                    wait_on_ready_expr = expr
                elif option_name == "line_cd":
                    line_cd_expr = expr
            else:
                # Regular option - parse as simple value
                value = self._parse_simple_value()
                options[option_name] = value
        
        # Create action line
        action_line = ActionLine(
            action_name=action_name,
            options=options,
            if_expr=if_expr,
            interrupt_if_expr=interrupt_if_expr,
            target_if_expr=target_if_expr,
            wait_on_ready_expr=wait_on_ready_expr,
            line_cd_expr=line_cd_expr,
            line=self._peek().line if not self._is_at_end() else 0
        )
        
        # Consume newline if present
        if self._check(TokenType.NEWLINE):
            self._advance()
        
        return action_line
    
    def _parse_simple_value(self) -> Union[str, float, int]:
        """Parse a simple value (string, number, or identifier)"""
        if self._check(TokenType.NUMBER):
            return self._advance().value
        elif self._check(TokenType.STRING):
            return self._advance().value
        elif self._check(TokenType.IDENTIFIER):
            return self._advance().value
        else:
            raise ParseError("Expected value (number, string, or identifier)", self._peek())
    
    def _parse_expression(self) -> ExprNode:
        """Parse expression with full operator precedence"""
        return self._parse_logical_or()
    
    def _parse_logical_or(self) -> ExprNode:
        """Parse logical OR expressions (lowest precedence)"""
        expr = self._parse_logical_and()
        
        while self._match(TokenType.OR):
            operator = self._previous().value
            right = self._parse_logical_and()
            expr = BinaryNode(operator, expr, right, expr.line, expr.column)
        
        return expr
    
    def _parse_logical_and(self) -> ExprNode:
        """Parse logical AND expressions"""
        expr = self._parse_equality()
        
        while self._match(TokenType.AND):
            operator = self._previous().value
            right = self._parse_equality()
            expr = BinaryNode(operator, expr, right, expr.line, expr.column)
        
        return expr
    
    def _parse_equality(self) -> ExprNode:
        """Parse equality/pattern matching expressions"""
        expr = self._parse_comparison()
        
        while self._match(TokenType.EQUAL, TokenType.NOT_EQUAL, TokenType.MATCH, TokenType.NOT_MATCH):
            operator = self._previous().value
            right = self._parse_comparison()
            expr = BinaryNode(operator, expr, right, expr.line, expr.column)
        
        return expr
    
    def _parse_comparison(self) -> ExprNode:
        """Parse comparison expressions"""
        expr = self._parse_addition()
        
        while self._match(TokenType.LESS, TokenType.LESS_EQUAL, TokenType.GREATER, TokenType.GREATER_EQUAL):
            operator = self._previous().value
            right = self._parse_addition()
            expr = BinaryNode(operator, expr, right, expr.line, expr.column)
        
        return expr
    
    def _parse_addition(self) -> ExprNode:
        """Parse addition and subtraction"""
        expr = self._parse_multiplication()
        
        while self._match(TokenType.PLUS, TokenType.MINUS):
            operator = self._previous().value
            right = self._parse_multiplication()
            expr = BinaryNode(operator, expr, right, expr.line, expr.column)
        
        return expr
    
    def _parse_multiplication(self) -> ExprNode:
        """Parse multiplication, modulo, and division"""
        expr = self._parse_unary()
        
        while self._match(TokenType.MULTIPLY, TokenType.MODULO, TokenType.DOUBLE_MODULO):
            operator = self._previous().value
            right = self._parse_unary()
            expr = BinaryNode(operator, expr, right, expr.line, expr.column)
        
        return expr
    
    def _parse_unary(self) -> ExprNode:
        """Parse unary expressions"""
        if self._match(TokenType.NOT, TokenType.PLUS, TokenType.MINUS):
            operator = self._previous().value
            right = self._parse_unary()
            return UnaryNode(operator, right, self._previous().line, self._previous().column)
        
        return self._parse_primary()
    
    def _parse_primary(self) -> ExprNode:
        """Parse primary expressions (literals, identifiers, function calls, parentheses)"""
        # Numbers
        if self._match(TokenType.NUMBER):
            token = self._previous()
            return LiteralNode(token.value, token.line, token.column)
        
        # Strings
        if self._match(TokenType.STRING):
            token = self._previous()
            return LiteralNode(token.value, token.line, token.column)
        
        # Identifiers and function calls
        if self._match(TokenType.IDENTIFIER):
            token = self._previous()
            
            # Check for function call
            if self._check(TokenType.LEFT_PAREN):
                return self._parse_function_call(token.value, token.line, token.column)
            
            # Parse dot notation for identifiers
            parts = [token.value]
            while self._match(TokenType.DOT):
                if not self._check(TokenType.IDENTIFIER):
                    raise ParseError("Expected identifier after '.'", self._peek())
                parts.append(self._advance().value)
            
            return IdentifierNode(parts, token.line, token.column)
        
        # Parenthesized expressions
        if self._match(TokenType.LEFT_PAREN):
            expr = self._parse_expression()
            if not self._match(TokenType.RIGHT_PAREN):
                raise ParseError("Expected ')' after expression", self._peek())
            return expr
        
        raise ParseError("Expected expression", self._peek())
    
    def _parse_function_call(self, name: str, line: int, column: int) -> FunctionCallNode:
        """Parse function call arguments"""
        self._advance()  # consume '('
        
        args = []
        
        if not self._check(TokenType.RIGHT_PAREN):
            # Parse first argument
            args.append(self._parse_expression())
            
            # Parse remaining arguments
            while self._match(TokenType.COMMA):
                args.append(self._parse_expression())
        
        if not self._match(TokenType.RIGHT_PAREN):
            raise ParseError("Expected ')' after function arguments", self._peek())
        
        return FunctionCallNode(name, args, line, column)
    
    # Utility methods
    def _match(self, *types: TokenType) -> bool:
        """Check if current token matches any of the given types"""
        for token_type in types:
            if self._check(token_type):
                self._advance()
                return True
        return False
    
    def _check(self, token_type: TokenType) -> bool:
        """Check if current token is of given type"""
        if self._is_at_end():
            return False
        return self._peek().type == token_type
    
    def _advance(self) -> Token:
        """Consume and return current token"""
        if not self._is_at_end():
            self.current += 1
        return self._previous()
    
    def _is_at_end(self) -> bool:
        """Check if we're at end of tokens"""
        return self.current >= len(self.tokens) or self._peek().type == TokenType.EOF
    
    def _peek(self) -> Token:
        """Return current token without consuming it"""
        if self.current >= len(self.tokens):
            # Return EOF token if we're past the end
            return Token(TokenType.EOF, "", "", 0, 0)
        return self.tokens[self.current]
    
    def _previous(self) -> Token:
        """Return previous token"""
        if self.current > 0:
            return self.tokens[self.current - 1]
        return Token(TokenType.EOF, "", "", 0, 0)
    
    def _skip_to_next_line(self):
        """Skip tokens until next newline (for error recovery)"""
        while not self._is_at_end() and not self._check(TokenType.NEWLINE):
            self._advance()
        if self._check(TokenType.NEWLINE):
            self._advance()


if __name__ == "__main__":
    # Test the parser
    parser = APLParser()
    
    # Test expression parsing
    print("Testing expression parsing:")
    
    test_expressions = [
        "buff.arcane_power.up",
        "mana.pct > 50",
        "buff.arcane_power.up & mana.pct > 50",
        "floor(mana.pct / 10) * 2",
        "min(mana.pct, energy.pct)",
        "!buff.exhaustion.up | cooldown.sprint.ready"
    ]
    
    for expr_text in test_expressions:
        try:
            expr = parser.parse_expression(expr_text)
            print(f"  '{expr_text}' -> {expr}")
            print(f"    Dependencies: {expr.get_dependencies()}")
        except Exception as e:
            print(f"  '{expr_text}' -> ERROR: {e}")
    
    print("\nTesting action line parsing:")
    
    test_apl = """
# Hunter APL example
/auto_shot
/arcane_shot,if=focus>40
/steady_shot,if=focus<20
/multi_shot,if=target.adds>2&focus>60
/hunter_mark,target_if=!debuff.hunter_mark.up,if=target.time_to_die>10
"""
    
    try:
        action_list = parser.parse(test_apl)
        print(f"Parsed {len(action_list.lines)} action lines:")
        for i, line in enumerate(action_list.lines):
            print(f"  {i+1}: {line}")
            deps = line.get_dependencies()
            if deps:
                print(f"      Dependencies: {deps}")
    except Exception as e:
        print(f"Parse error: {e}")
