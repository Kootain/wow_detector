from typing import Union, List, Set
from game_state import *
from item import buff_id_map, buff_name_map

def id(self, attr: str) -> Union[str, int]:
        if attr.startswith('id:'):
            return int(attr[3:])
        return attr

class Identifier(object):
    """Base class providing method registration via a decorator.

    - Use `@Identifier.register` on methods in subclasses to register them.
    - `valid(attr)` returns True if `attr` is a registered method name on the subclass.
    - Supports stacking with `@property`, regardless of decorator order.
    """

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        regs = set()
        types = {}
        depends_on = {}
        reverse_depends_on = {}
        for name, val in cls.__dict__.items():
            # Support normal callables
            if callable(val) and getattr(val, "_identifier_registered", False):
                regs.add(name)
                types[name] = getattr(val, "_identifier_ret_type", None)
                depends_on[name] = getattr(val, "_identifier_depends_on", None)
            # Support properties: check fget/fset/fdel
            elif isinstance(val, property):
                if getattr(val.fget, "_identifier_registered", False):
                    regs.add(name)
                    types[name] = getattr(val.fget, "_identifier_ret_type", None)
                    depends_on[name] = getattr(val.fget, "_identifier_depends_on", None)
                elif val.fset and getattr(val.fset, "_identifier_registered", False):
                    regs.add(name)
                    types[name] = getattr(val.fset, "_identifier_ret_type", None)
                    depends_on[name] = getattr(val.fset, "_identifier_depends_on", None)
                elif val.fdel and getattr(val.fdel, "_identifier_registered", False):
                    regs.add(name)
                    types[name] = getattr(val.fdel, "_identifier_ret_type", None)
                    depends_on[name] = getattr(val.fdel, "_identifier_depends_on", None)
        cls._registered_methods = regs
        cls._registered_method_types = types
        cls._registered_method_depends_on = depends_on

        for k, deps in depends_on.items():
            if deps:
                for dep in deps:
                    reverse_depends_on.setdefault(dep, set()).add(k)
        cls._reverse_depends_on = reverse_depends_on

        def update(self, new_value):
            if not issubclass(new_value.__class__, BaseModel):
                raise TypeError(f"update() requires a BaseModel instance")
            def to_dict(model):
                if hasattr(model, "model_dump"):
                    return model.model_dump()
                if hasattr(model, "dict"):
                    return model.dict()
                return {k: getattr(model, k) for k in dir(model) if not k.startswith('_')}
            current = to_dict(self)
            incoming = to_dict(new_value)

            changes = {}
            effects = {}
            for k, new_v in incoming.items():
                old_v = current.get(k)
                if new_v != old_v:
                    changes[k] = (old_v, new_v)
                    setattr(self, k, new_v)
                    if k in reverse_depends_on:
                        for dep in reverse_depends_on[k]:
                            effects.setdefault(dep, set()).add(k)
            return {"effects": list(effects.keys()), "changes": changes}


        if "update" not in cls.__dict__:
            setattr(cls, "update", update)

    @classmethod
    def register(cls, ret_type, depends_on: List[str] = None):
        def decorator(obj):
            if isinstance(obj, property):
                if obj.fget:
                    setattr(obj.fget, "_identifier_registered", True)
                    setattr(obj.fget, "_identifier_ret_type", ret_type)
                    setattr(obj.fget, "_identifier_depends_on", depends_on)
                if obj.fset:
                    setattr(obj.fset, "_identifier_registered", True)
                    setattr(obj.fset, "_identifier_ret_type", ret_type)
                    setattr(obj.fset, "_identifier_depends_on", depends_on)
                if obj.fdel:
                    setattr(obj.fdel, "_identifier_registered", True)
                    setattr(obj.fdel, "_identifier_ret_type", ret_type)
                    setattr(obj.fdel, "_identifier_depends_on", depends_on)
                return obj
            setattr(obj, "_identifier_registered", True)
            setattr(obj, "_identifier_ret_type", ret_type)
            setattr(obj, "_identifier_depends_on", depends_on)
            return obj
        return decorator

    def valid(self, attr: str):
        types = getattr(self.__class__, "_registered_method_types", {})
        return types.get(attr)

    def registered_methods(self):
        return set(getattr(self.__class__, "_registered_methods", set()))


class BuffState(Buff, Identifier):

    @property
    @Identifier.register(bool, depends_on=["stock", "remain_ms"])
    def up(self):
        return self.stock > 0 or self.remain_ms > 0

    @property
    @Identifier.register(int, depends_on=["remain_ms"])
    def remains(self):
        return self.remain_ms

    @property
    @Identifier.register(int, depends_on=["stock"])
    def stock(self):
        return self.stock

class SpellState(Spell, Identifier):
    
    @property
    @Identifier.register(int, depends_on=["remain_ms"])
    def remains(self):
        return self.remain_ms

    @property
    @Identifier.register(bool, depends_on=["remain_ms"])
    def ready(self):
        return self.remain_ms <= 0


class CoolDownManager(Identifier):
    def __init__(self):
        self.spells: Set[SpellState]= set()

    def valid(self, attr: str):
        spell_id = id(attr)
        for spell in self.spells:
            if spell.id == spell_id or spell.name == spell_id:
                return True
        return False

    def __getattr__(self, attr: str):
        spell_id = id(attr)
        if isinstance(spell_id, int):
            for spell in self.spells:
                if spell.id == spell_id or spell.name == spell_id:
                    return spell
        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{attr}'")

empty_buff = BuffState(id=0, name='empty', icon=0, stock=0, remain_ms=0)

class BuffManager(Identifier):
    def __init__(self):
        self.buffs: Set[BuffState]= set()

    def update(self, buffs: Set[Buff]):
        # 将 self.buffs 转为以 id 为键的字典，方便查找
        old_buffs = {b.id: b for b in self.buffs}
        new_buffs = {b.id: b for b in buffs}

        added = set()      # 新增的 Buff
        removed = set()    # 删除的 Buff
        updated = set()    # 更新的 Buff
        effects = set()
        changes = {}

        # 找出新增和需要更新的
        for new_b in buffs:
            if new_b.id not in old_buffs:
                # 新增：创建 BuffState 并加入
                # 直接将 BaseModel 作为入参（Pydantic v2）：避免显式转 dict
                added.add(BuffState(**new_b.model_dump()))
                effects.add(f"id:{new_b.id}")
                changes[f"id:{new_b.id}"] = (None, new_b)
                effects.add(f"{new_b.name}")
                changes[f"{new_b.name}"] = (None, new_b)
                
            else:
                # 已存在，调用 update 更新
                old_buff = old_buffs[new_b.id]
                tmp = old_buff.update(new_b)
                es, cs = tmp["effects"], tmp["changes"]
                for e in es:
                    effects.add(f"id:{old_buff.id}.{e}")
                    effects.add(f"{old_buff.name}.{e}")
                    changes[f"id:{old_buff.id}.{e}"] = cs
                    changes[f"{old_buff.name}.{e}"] = cs

        # 找出删除的
        for old_b in self.buffs:
            if old_b.id not in new_buffs:
                removed.add(old_b)
                effects.add(f"id:{old_b.id}")
                changes[f"id:{old_b.id}"] = (old_b, None)
                effects.add(f"{old_b.name}")
                changes[f"{old_b.name}"] = (old_b, None)


        # 应用变更：移除已删除的，加入新增的
        self.buffs -= removed
        self.buffs |= added
        return dict(effects=effects, changes=changes)
        
    def valid(self, attr: str):
        buff_id = id(attr)
        if isinstance(buff_id, int):
            return buff_id_map.get(buff_id) is not None, BuffState
        return buff_name_map.get(buff_id) is not None, BuffState

    def __getattr__(self, attr: str):
        buff_id = id(attr)
        if isinstance(buff_id, int):
            for buff in self.buffs:
                if buff.id == buff_id:
                    return buff
            return empty_buff
        for buff in self.buffs:
            if buff.name == buff_id:
                return buff
        return empty_buff
    

if __name__ == "__main__":
    from item import buffs
    bufs = [Buff(**b) for b in buffs]
    manager = BuffManager()
    print(manager.update(set(bufs)))
    print(manager.测试buff2.up)
    print(manager.测试buff1.remains)
    print(manager.测试buff1.up)
    bufs = [Buff(**b) for b in buffs] 
    bufs[0].remain_ms = 300
    print(manager.update(set(bufs)))
    print(manager.测试buff1.remains)
    print(manager.测试buff1.up)
