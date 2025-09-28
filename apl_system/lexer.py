"""APL Lexer - Tokenizes APL text into tokens

Implements tokenization for SimulationCraft APL syntax including:
- Action names with slash prefix (/spell_name)
- Identifiers with dot notation (buff.name.remains)
- Numbers (integers and floats)
- Operators and punctuation
- Comments and whitespace handling
"""

import re
from enum import Enum
from typing import List, Optional, NamedTuple
from dataclasses import dataclass


class TokenType(Enum):
    """Token types for APL syntax"""
    # Literals
    NUMBER = "NUMBER"
    IDENTIFIER = "IDENTIFIER"
    STRING = "STRING"
    
    # Operators
    PLUS = "PLUS"          # +
    MINUS = "MINUS"        # -
    MULTIPLY = "MULTIPLY"  # *
    MODULO = "MODULO"      # %
    MODULOS = "MODULOS"    # %%
    
    # Comparison
    EQUAL = "EQUAL"        # =
    NOT_EQUAL = "NOT_EQUAL"  # !=
    LESS = "LESS"          # <
    LESS_EQUAL = "LESS_EQUAL"  # <=
    GREATER = "GREATER"    # >
    GREATER_EQUAL = "GREATER_EQUAL"  # >=
    MATCH = "MATCH"        # ~
    NOT_MATCH = "NOT_MATCH"  # !~
    
    # Logical
    AND = "AND"            # &
    OR = "OR"              # |
    XOR = "XOR"            # ^
    NOT = "NOT"            # !
    
    # Punctuation
    SLASH = "SLASH"        # /
    DOT = "DOT"            # .
    COMMA = "COMMA"        # ,
    COLON = "COLON"        # :
    SEMICOLON = "SEMICOLON"  # ;
    LPAREN = "LPAREN"      # (
    RPAREN = "RPAREN"      # )
    
    # Special
    ASSIGN = "ASSIGN"      # = (in actions= context)
    PLUS_ASSIGN = "PLUS_ASSIGN"  # +=
    
    # Keywords
    ACTIONS = "ACTIONS"    # actions
    IF = "IF"              # if
    INTERRUPT_IF = "INTERRUPT_IF"  # interrupt_if
    TARGET_IF = "TARGET_IF"  # target_if
    WAIT_ON_READY = "WAIT_ON_READY"  # wait_on_ready
    LINE_CD = "LINE_CD"    # line_cd
    
    # Control
    NEWLINE = "NEWLINE"
    EOF = "EOF"
    COMMENT = "COMMENT"


@dataclass
class Token:
    """Represents a single token with position information"""
    type: TokenType
    value: str
    line: int
    column: int
    filename: str = ""
    
    def __str__(self):
        return f"Token({self.type.value}, '{self.value}', {self.line}:{self.column})"
    
    def __repr__(self):
        return self.__str__()


class LexerError(Exception):
    """Lexer error with position information"""
    def __init__(self, message: str, line: int, column: int, filename: str = ""):
        self.message = message
        self.line = line
        self.column = column
        self.filename = filename
        super().__init__(f"{filename}:{line}:{column}: {message}")


class APLLexer:
    """APL Lexer - converts APL text into tokens"""
    
    # Keywords mapping
    KEYWORDS = {
        'actions': TokenType.ACTIONS,
        'if': TokenType.IF,
        'interrupt_if': TokenType.INTERRUPT_IF,
        'target_if': TokenType.TARGET_IF,
        'wait_on_ready': TokenType.WAIT_ON_READY,
        'line_cd': TokenType.LINE_CD,
    }
    
    # Multi-character operators (order matters - longer first)
    MULTI_CHAR_OPS = [
        ('%%', TokenType.MODULOS),
        ('+=', TokenType.PLUS_ASSIGN),
        ('!=', TokenType.NOT_EQUAL),
        ('<=', TokenType.LESS_EQUAL),
        ('>=', TokenType.GREATER_EQUAL),
        ('!~', TokenType.NOT_MATCH),
    ]
    
    # Single character operators
    SINGLE_CHAR_OPS = {
        '+': TokenType.PLUS,
        '-': TokenType.MINUS,
        '*': TokenType.MULTIPLY,
        '%': TokenType.MODULO,
        '=': TokenType.EQUAL,
        '<': TokenType.LESS,
        '>': TokenType.GREATER,
        '~': TokenType.MATCH,
        '&': TokenType.AND,
        '|': TokenType.OR,
        '^': TokenType.XOR,
        '!': TokenType.NOT,
        '/': TokenType.SLASH,
        '.': TokenType.DOT,
        ',': TokenType.COMMA,
        ':': TokenType.COLON,
        ';': TokenType.SEMICOLON,
        '(': TokenType.LPAREN,
        ')': TokenType.RPAREN,
    }
    
    def __init__(self, filename: str = ""):
        self.filename = filename
        self.text = ""
        self.pos = 0
        self.line = 1
        self.column = 1
        self.tokens = []
    
    def tokenize(self, text: str, filename: str = "") -> List[Token]:
        """Tokenize APL text and return list of tokens"""
        self.filename = filename or self.filename
        self.text = text
        self.pos = 0
        self.line = 1
        self.column = 1
        self.tokens = []
        
        while self.pos < len(self.text):
            self._skip_whitespace()
            
            if self.pos >= len(self.text):
                break
                
            # Handle comments
            if self._current_char() == '#':
                self._skip_comment()
                continue
            
            # Handle newlines
            if self._current_char() == '\n':
                self._add_token(TokenType.NEWLINE, '\n')
                self._advance()
                continue
            
            # Handle numbers
            if self._current_char().isdigit() or (self._current_char() == '.' and self._peek().isdigit()):
                self._read_number()
                continue
            
            # Handle identifiers and keywords
            if self._current_char().isalpha() or self._current_char() == '_':
                self._read_identifier()
                continue
            
            # Handle strings (quoted)
            if self._current_char() in ['"', "'"]:
                self._read_string()
                continue
            
            # Handle multi-character operators
            found_multi = False
            for op_str, token_type in self.MULTI_CHAR_OPS:
                if self._match_string(op_str):
                    self._add_token(token_type, op_str)
                    self._advance(len(op_str))
                    found_multi = True
                    break
            
            if found_multi:
                continue
            
            # Handle single character operators
            char = self._current_char()
            if char in self.SINGLE_CHAR_OPS:
                self._add_token(self.SINGLE_CHAR_OPS[char], char)
                self._advance()
                continue
            
            # Unknown character
            raise LexerError(f"Unexpected character: '{char}'", self.line, self.column, self.filename)
        
        # Add EOF token
        self._add_token(TokenType.EOF, "")
        return self.tokens
    
    def _current_char(self) -> str:
        """Get current character"""
        if self.pos >= len(self.text):
            return '\0'
        return self.text[self.pos]
    
    def _peek(self, offset: int = 1) -> str:
        """Peek at character ahead"""
        peek_pos = self.pos + offset
        if peek_pos >= len(self.text):
            return '\0'
        return self.text[peek_pos]
    
    def _advance(self, count: int = 1):
        """Advance position and update line/column"""
        for _ in range(count):
            if self.pos < len(self.text) and self.text[self.pos] == '\n':
                self.line += 1
                self.column = 1
            else:
                self.column += 1
            self.pos += 1
    
    def _match_string(self, target: str) -> bool:
        """Check if current position matches target string"""
        if self.pos + len(target) > len(self.text):
            return False
        return self.text[self.pos:self.pos + len(target)] == target
    
    def _add_token(self, token_type: TokenType, value: str):
        """Add token to list"""
        token = Token(token_type, value, self.line, self.column - len(value), self.filename)
        self.tokens.append(token)
    
    def _skip_whitespace(self):
        """Skip whitespace except newlines"""
        while (self.pos < len(self.text) and 
               self._current_char() in ' \t\r' and 
               self._current_char() != '\n'):
            self._advance()
    
    def _skip_comment(self):
        """Skip comment line starting with #"""
        start_pos = self.pos
        while self.pos < len(self.text) and self._current_char() != '\n':
            self._advance()
        
        # Optionally store comment as token for documentation
        comment_text = self.text[start_pos:self.pos]
        # self._add_token(TokenType.COMMENT, comment_text)
    
    def _read_number(self):
        """Read numeric literal (int or float)"""
        start_pos = self.pos
        start_col = self.column
        
        # Handle integer part
        while self.pos < len(self.text) and self._current_char().isdigit():
            self._advance()
        
        # Handle decimal part
        if (self.pos < len(self.text) and self._current_char() == '.' and 
            self.pos + 1 < len(self.text) and self.text[self.pos + 1].isdigit()):
            self._advance()  # consume '.'
            while self.pos < len(self.text) and self._current_char().isdigit():
                self._advance()
        
        value = self.text[start_pos:self.pos]
        token = Token(TokenType.NUMBER, value, self.line, start_col, self.filename)
        self.tokens.append(token)
    
    def _read_identifier(self):
        """Read identifier or keyword"""
        start_pos = self.pos
        start_col = self.column
        
        # First character: letter or underscore
        if not (self._current_char().isalpha() or self._current_char() == '_'):
            raise LexerError(f"Invalid identifier start: '{self._current_char()}'", 
                           self.line, self.column, self.filename)
        
        # Read identifier characters
        while (self.pos < len(self.text) and 
               (self._current_char().isalnum() or self._current_char() == '_')):
            self._advance()
        
        value = self.text[start_pos:self.pos]
        
        # Check if it's a keyword
        token_type = self.KEYWORDS.get(value, TokenType.IDENTIFIER)
        token = Token(token_type, value, self.line, start_col, self.filename)
        self.tokens.append(token)
    
    def _read_string(self):
        """Read quoted string literal"""
        start_col = self.column
        quote_char = self._current_char()
        self._advance()  # consume opening quote
        
        value = ""
        while self.pos < len(self.text) and self._current_char() != quote_char:
            if self._current_char() == '\\':
                self._advance()
                if self.pos >= len(self.text):
                    raise LexerError("Unterminated string escape", self.line, self.column, self.filename)
                
                # Handle escape sequences
                escape_char = self._current_char()
                if escape_char == 'n':
                    value += '\n'
                elif escape_char == 't':
                    value += '\t'
                elif escape_char == 'r':
                    value += '\r'
                elif escape_char == '\\':
                    value += '\\'
                elif escape_char == quote_char:
                    value += quote_char
                else:
                    value += escape_char
                self._advance()
            else:
                value += self._current_char()
                self._advance()
        
        if self.pos >= len(self.text):
            raise LexerError("Unterminated string", self.line, self.column, self.filename)
        
        self._advance()  # consume closing quote
        
        token = Token(TokenType.STRING, value, self.line, start_col, self.filename)
        self.tokens.append(token)


# Utility functions for testing
def tokenize_apl(text: str, filename: str = "") -> List[Token]:
    """Convenience function to tokenize APL text"""
    lexer = APLLexer(filename)
    return lexer.tokenize(text)


if __name__ == "__main__":
    # Simple test
    test_apl = """
    actions=arcane_orb,if=buff.arcane_power.up&mana.pct>50
    actions+=arcane_missiles,if=buff.clearcasting.up
    actions+=frostbolt
    """
    
    try:
        tokens = tokenize_apl(test_apl, "test.apl")
        for token in tokens:
            if token.type != TokenType.EOF:
                print(token)
    except LexerError as e:
        print(f"Lexer Error: {e}")