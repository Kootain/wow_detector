# Redesigned chain-resolution APL prototype (Python)
# Focus: implement chained identifier resolution where:
# - Top-level module (e.g., 'buff') is only responsible for locating the named entity (e.g., 'xxx')
# - It returns a Handle (opaque) that represents that entity
# - Attribute resolvers (separate registry) are responsible for handling attribute names (e.g., 'stack', 'remains', 'up')
# - Attribute resolvers can return numeric values or another Handle, enabling arbitrary chaining
#
# This demo integrates a small expression parser, module registry, attribute resolver registry,
# static validation that checks prefixes and attribute availability for known handle types,
# and a simple evaluator demonstrating chain resolution.
#
# Run the bottom demo to see behavior for expressions like: buff.steady_focus.stack > 0

import re, math
from typing import List, Tuple, Dict, Optional, Any, Union

# ---------- Tokenizer (compact) ----------
TOKEN_SPEC = [
    ('NUMBER',   r'\d+(\.\d+)?'),
    ('IDENT',    r'[A-Za-z_][A-Za-z0-9_]*'),
    ('DOT',      r'\.'),
    ('LPAREN',   r'\('),
    ('RPAREN',   r'\)'),
    ('COMMA',    r','),
    ('PLUS',     r'\+'),
    ('MINUS',    r'-'),
    ('STAR',     r'\*'),
    ('EQ',       r'==|='),
    ('NE',       r'!='),
    ('LE',       r'<='),
    ('GE',       r'>='),
    ('LT',       r'<'),
    ('GT',       r'>'),
    ('AMP',      r'&'),
    ('PIPE',     r'\|'),
    ('CARET',    r'\^'),
    ('BANG',     r'!'),
    ('WS',       r'[ \t]+'),
    ('NEWLINE',  r'\n'),
    ('MISMATCH', r'.'),
]
MASTER_RE = re.compile('|'.join('(?P<%s>%s)' % pair for pair in TOKEN_SPEC))

def lex(text: str):
    tokens = []
    line, col = 1, 1
    pos = 0
    while pos < len(text):
        m = MASTER_RE.match(text, pos)
        if not m:
            raise SyntaxError(f"Unexpected char at {line}:{col}")
        kind = m.lastgroup
        val = m.group()
        if kind == 'NEWLINE':
            line += 1; col = 1; pos = m.end(); continue
        if kind == 'WS':
            pos = m.end(); col += len(val); continue
        if kind == 'MISMATCH':
            raise SyntaxError(f"Unexpected {val!r} at {line}:{col}")
        tokens.append((kind, val, line, col))
        pos = m.end(); col += len(val)
    tokens.append(('EOF','',line, col))
    return tokens

# ---------- Minimal expression parser (supports identifiers with dots) ----------
class ParseError(Exception): pass

class Expr:
    def eval(self, ctx): raise NotImplementedError()
    def walk_idents(self): return []

class Literal(Expr):
    def __init__(self, v): self.v = float(v)
    def eval(self, ctx): return self.v
    def __repr__(self): return f"Lit({self.v})"

class Ident(Expr):
    def __init__(self, parts: List[str]): self.parts = parts
    def eval(self, ctx): return ctx.resolve_identifier(self.parts)
    def walk_idents(self): return [self.parts]
    def __repr__(self): return "Ident(" + ".".join(self.parts) + ")"

class Binary(Expr):
    def __init__(self, op, a, b): self.op=op; self.a=a; self.b=b
    def eval(self, ctx):
        la = self.a.eval(ctx)
        # short-circuit for & and |
        if self.op in ('&','and'):
            if la == 0.0: return 0.0
            lb = self.b.eval(ctx); return 1.0 if (la!=0.0 and lb!=0.0) else 0.0
        if self.op in ('|','or'):
            if la != 0.0: return 1.0
            lb = self.b.eval(ctx); return 1.0 if (lb!=0.0) else 0.0
        lb = self.b.eval(ctx)
        if self.op == '+': return la + lb
        if self.op == '-': return la - lb
        if self.op == '*': return la * lb
        if self.op in ('=','=='): return 1.0 if la == lb else 0.0
        if self.op == '!=': return 1.0 if la != lb else 0.0
        if self.op == '<': return 1.0 if la < lb else 0.0
        if self.op == '<=': return 1.0 if la <= lb else 0.0
        if self.op == '>': return 1.0 if la > lb else 0.0
        if self.op == '>=': return 1.0 if la >= lb else 0.0
        raise RuntimeError("Unknown op " + self.op)
    def walk_idents(self): return self.a.walk_idents() + self.b.walk_idents()
    def __repr__(self): return f"({self.a} {self.op} {self.b})"

class Parser:
    def __init__(self, tokens):
        self.toks = tokens; self.pos = 0
    def peek(self): return self.toks[self.pos][0]
    def next(self): t=self.toks[self.pos]; self.pos+=1; return t
    def expect(self, k):
        t=self.next()
        if t[0]!=k: raise ParseError(f"Expected {k} got {t}")
        return t
    def parse_ident(self):
        parts = []
        tok = self.next()
        if tok[0] != 'IDENT': raise ParseError("ident expected")
        parts.append(tok[1])
        while self.peek() == 'DOT':
            self.next(); p = self.expect('IDENT')[1]; parts.append(p)
        return Ident(parts)
    def parse_primary(self):
        if self.peek() == 'NUMBER':
            v = self.next()[1]; return Literal(v)
        if self.peek() == 'IDENT':
            return self.parse_ident()
        if self.peek() == 'LPAREN':
            self.next(); e = self.parse_expr(); self.expect('RPAREN'); return e
        raise ParseError("primary")
    def parse_mul(self):
        n = self.parse_primary()
        while self.peek() in ('STAR',):
            op = self.next()[1]; r = self.parse_primary(); n = Binary(op, n, r)
        return n
    def parse_add(self):
        n = self.parse_mul()
        while self.peek() in ('PLUS','MINUS'):
            tok = self.next()[0]; op = '+' if tok=='PLUS' else '-'; r = self.parse_mul(); n = Binary(op, n, r)
        return n
    def parse_cmp(self):
        n = self.parse_add()
        while self.peek() in ('EQ','NE','LT','GT','LE','GE'):
            t = self.next()[0]
            opmap = {'EQ':'=','NE':'!=','LT':'<','GT':'>','LE':'<=','GE':'>='}
            op = opmap[t]; r = self.parse_add(); n = Binary(op, n, r)
        return n
    def parse_and(self):
        n = self.parse_cmp()
        while self.peek() in ('AMP',) or (self.peek()=='IDENT' and self.toks[self.pos][1].lower()=='and'):
            if self.peek()=='AMP': self.next(); r = self.parse_cmp(); n = Binary('&', n, r)
            else: self.next(); r=self.parse_cmp(); n=Binary('and', n, r)
        return n
    def parse_or(self):
        n = self.parse_and()
        while self.peek() in ('PIPE',) or (self.peek()=='IDENT' and self.toks[self.pos][1].lower()=='or'):
            if self.peek()=='PIPE': self.next(); r=self.parse_and(); n = Binary('|', n, r)
            else: self.next(); r=self.parse_and(); n = Binary('or', n, r)
        return n
    def parse_expr(self):
        return self.parse_or()

# ---------- Chain resolution types ----------
class Handle:
    def __init__(self, htype: str, name: str, data: Any=None):
        self.htype = htype    # e.g., 'buff'
        self.name = name
        self.data = data or {}
    def __repr__(self):
        return f"<Handle {self.htype}:{self.name} data={self.data}>"
    
class ModuleBase:
    """Top-level module: only responsible for locating a named entity after the prefix.
       Must implement: supported_prefixes(), get_handle(name, ctx) -> Handle, handle_type() or handle_type_for(name)
    """
    def supported_prefixes(self) -> List[str]:
        return []
    def get_handle(self, name: str, ctx) -> Optional[Handle]:
        raise NotImplementedError()
    def handle_type_for(self, name: str) -> Optional[str]:
        # return a stable handle type string for static validation (e.g., 'buff_instance')
        return None

class ModuleRegistry:
    def __init__(self):
        self._by_prefix: Dict[str, ModuleBase] = {}
    def register(self, m: ModuleBase):
        for p in m.supported_prefixes():
            self._by_prefix[p] = m
    def unregister(self, m: ModuleBase):
        for p in list(self._by_prefix.keys()):
            if self._by_prefix[p] is m:
                del self._by_prefix[p]
    def get(self, prefix: str) -> Optional[ModuleBase]:
        return self._by_prefix.get(prefix)
    def list_prefixes(self):
        return list(self._by_prefix.keys())

# Attribute resolver:
class AttrResolverBase:
    """Resolve attributes given a handle and a list of parts starting at the attribute.
       Must implement can_resolve(handle_type, attr_name) and resolve(handle, parts, ctx)
       resolve returns a tuple (result, consumed):
         - if result is float -> numeric value; consumed is number of tokens consumed (>=1)
         - if result is Handle -> another handle object; consumed indicates tokens consumed
    """
    def can_resolve(self, handle_type: str, attr_name: str) -> bool:
        return False
    def resolve(self, handle: Handle, parts: List[str], ctx) -> Tuple[Union[float, Handle], int]:
        raise NotImplementedError()

class AttrRegistry:
    def __init__(self):
        self.resolvers: List[AttrResolverBase] = []
    def register(self, r: AttrResolverBase): self.resolvers.append(r)
    def find(self, handle_type: str, attr_name: str) -> Optional[AttrResolverBase]:
        for r in self.resolvers:
            try:
                if r.can_resolve(handle_type, attr_name):
                    return r
            except Exception:
                continue
        return None
    def find_any(self, attr_name: str) -> Optional[AttrResolverBase]:
        for r in self.resolvers:
            try:
                if r.can_resolve('*', attr_name):
                    return r
            except Exception:
                continue
        return None

# ---------- Example modules & attribute resolvers ----------
class BuffModule(ModuleBase):
    def supported_prefixes(self): return ['buff','debuff']  # both return the same handle type
    def handle_type_for(self, name): return 'buff_inst'
    def get_handle(self, name, ctx):
        # find in player buffs or target_debuffs depending on prefix? 
        # For demo, just search both places
        b = ctx.state.get('buffs', {}).get(name)
        if b is not None:
            return Handle('buff_inst', name, b)
        db = ctx.state.get('target_debuffs', {}).get(name)
        if db is not None:
            return Handle('buff_inst', name, db)
        # not found -> return handle with empty data (we prefer returning a handle to allow attribute resolvers to return defaults)
        return Handle('buff_inst', name, {})

class BuffAttrResolver(AttrResolverBase):
    def can_resolve(self, handle_type, attr_name):
        return handle_type == 'buff_inst' and attr_name in ('remains','stack','stacks','up')
    def resolve(self, handle: Handle, parts: List[str], ctx):
        # parts[0] is attr_name
        if len(parts)==0:
            # no attr, default to 'up' semantic
            up = 1.0 if handle.data.get('remains',0.0)>0.0 else 0.0
            return (up, 0)
        a = parts[0]
        if a in ('remains',):
            return (float(handle.data.get('remains',0.0)), 1)
        if a in ('stack','stacks'):
            return (float(handle.data.get('stacks',0)), 1)
        if a == 'up':
            return (1.0 if handle.data.get('remains',0.0)>0.0 else 0.0, 1)
        return (0.0, 1)

# Example: attribute resolver that returns a nested handle: e.g., handle.someattr.subattr
# (for demo, not used)
class ExampleNestedAttrResolver(AttrResolverBase):
    def can_resolve(self, handle_type, attr_name):
        return handle_type == 'buff_inst' and attr_name == 'owner'
    def resolve(self, handle: Handle, parts: List[str], ctx):
        # return a new handle representing the owner (player)
        owner = ctx.state.get('buff_owners', {}).get(handle.name, 'player')
        return (Handle('entity', owner, {'id': owner}), 1)

# ---------- EvalContext with chain resolution ----------
class EvalContext:
    def __init__(self, state: Dict[str,Any], module_registry: ModuleRegistry, attr_registry: AttrRegistry):
        self.state = state
        self.modules = module_registry
        self.attrs = attr_registry
    def resolve_identifier(self, parts: List[str]) -> float:
        # parts example: ['buff','steady_focus','stack']
        if not parts: return 0.0
        prefix = parts[0]
        module = self.modules.get(prefix)
        if module is None:
            # unknown prefix -> 0
            return 0.0
        if len(parts) < 2:
            # prefix alone (e.g., "buff") -> not meaningful -> 0
            return 0.0
        name = parts[1]
        handle = module.get_handle(name, self)
        # now consume parts starting at index 2
        idx = 2
        while idx < len(parts):
            attr = parts[idx]
            # find resolver by handle_type & attr first
            resolver = self.attrs.find(handle.htype, attr)
            if resolver is None:
                resolver = self.attrs.find_any(attr)
            if resolver is None:
                # unknown attribute for this handle -> return 0
                return 0.0
            result, consumed = resolver.resolve(handle, parts[idx:], self)
            if isinstance(result, Handle):
                handle = result
                idx += max(1, consumed)
                continue
            else:
                # numeric result
                return float(result)
        # if we consumed all parts and didn't get a numeric value, try default attribute resolution (e.g., buff -> up)
        # attempt to resolve default attribute using 'up'
        default_resolver = self.attrs.find(handle.htype, 'up') or self.attrs.find_any('up')
        if default_resolver:
            val, _ = default_resolver.resolve(handle, ['up'], self)
            return float(val)
        return 0.0

# ---------- Static validation for identifiers with attribute registry ----------
def static_validate_ident(parts: List[str], module_registry: ModuleRegistry, attr_registry: AttrRegistry):
    # ensures prefix exists, and if attribute present, attr resolver exists for handle_type
    if not parts: raise ParseError("empty identifier")
    prefix = parts[0]
    mod = module_registry.get(prefix)
    if mod is None:
        raise ParseError(f"Unknown prefix '{prefix}'")
    # we need a handle_type for static validation; ask module
    htype = mod.handle_type_for(parts[1]) if len(parts)>1 else None
    if htype is None:
        raise ParseError(f"Module '{prefix}' did not declare handle type for static validation")
    # if attribute exists in parts[2], check a resolver exists
    if len(parts) >= 3:
        attr = parts[2]
        if not (attr_registry.find(htype, attr) or attr_registry.find_any(attr)):
            raise ParseError(f"Unknown attribute '{attr}' for handle type '{htype}' (from prefix {prefix})")
    # else ok (default will be checked at runtime)
    return True

# ---------- Demo ----------
if __name__ == "__main__":
    # set up registries
    module_registry = ModuleRegistry()
    attr_registry = AttrRegistry()
    # register modules
    buff_mod = BuffModule()
    module_registry.register(buff_mod)
    # register attribute resolvers
    buff_attr_resolver = BuffAttrResolver()
    attr_registry.register(buff_attr_resolver)
    attr_registry.register(ExampleNestedAttrResolver())

    # prepare state
    state = {
        'buffs': {
            'steady_focus': {'remains': 5.0, 'stacks': 1},
            'short_buff': {'remains': 0.0, 'stacks': 0}
        },
        'target_debuffs': {
            'vulnerable': {'remains': 12.0, 'stacks': 2}
        },
        'time': 0.0,
        'active_enemies': 1
    }

    # parse an expression: buff.steady_focus.stack > 0
    expr_txt = "buff.steady_focus.stack > 0"
    toks = lex(expr_txt)
    p = Parser(toks)
    expr = p.parse_expr()

    # static validation (basic)
    idents = expr.walk_idents()
    for ident in idents:
        try:
            static_validate_ident(ident, module_registry, attr_registry)
            print("Static validate OK for", ".".join(ident))
        except Exception as e:
            print("Static validate error for", ".".join(ident), ":", e)

    # runtime eval
    ctx = EvalContext(state, module_registry, attr_registry)
    val = expr.eval(ctx)
    print("Expression:", expr_txt, "=>", val)  # expect true (1.0) because stack==1 so 1>0 -> true

    expr2_txt = "buff.short_buff.up = 1"
    toks2 = lex(expr2_txt); p2 = Parser(toks2); e2 = p2.parse_expr()
    print(e2, "=>", e2.eval(ctx))  # expects 0 because short_buff.remains==0 so up==0, 0==1 -> false (0.0)


