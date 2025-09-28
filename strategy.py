import abc
from pydantic import BaseModel
from typing import Optional, Literal

class Buff(BaseModel):
    spell_id: int
    stacks: int
    remaining_ms: int
    name: str
    icon: int

    def can_resolve(self, attr: str) -> bool:
        return attr in ["stack", "up", "remains"]

    @property
    def stack(self) -> int:
        return self.stacks
    
    @property
    def up(self) -> bool:
        return self.remaining_ms > 0
    
    @property
    def remains(self) -> int:
        return float(self.remaining_ms) / 1000


class Cooldown(BaseModel):
    spell_id: int
    remaining_ms: int
    name: str
    icon: int

class Spell(BaseModel):
    spell_id: int
    name: str
    icon: int
    start_ms: int
    end_ms: int
    remaining_ms: int
    type: Literal['cast', 'channel']

class Action(BaseModel):
    type: Literal['cast', 'channel']
    spell_id: int


class State(BaseModel):
    buffs: list[Buff] = []
    debuffs: list[Buff] = []
    cooldowns: list[Cooldown] = []
    casting: Optional[Spell] = None


class Identifier(abc.ABC):
    @abc.abstractmethod
    def can_resolve(self, attr: str) -> bool:
        pass
    

class BuffManager(Identifier):
    ALL_BUFFS = [
        "敏锐直觉",
        "白炽耀焰",
        "奥术迅疾",
        "力量的重担",
        "虚空精准",
        "节能施法",
        "法术火焰宝珠", "id449400",
        "奥术涌动",
        "奥术之魂"
    ]
    empty_buff = Buff(spell_id=0, stacks=0, remaining_ms=0, name="", icon=0)
    def __init__(self, state: State):
        self.state = state

    def can_resolve(self, attr: str) -> bool:
        return attr in self.ALL_BUFFS
    
    def __getattr__(self, attr: str) -> Optional[Buff]:
        if not self.can_resolve(attr):
            raise AttributeError(f"BuffManager has no attribute {attr}")
        for buff in self.state.buffs:
            if buff.name == attr or f"id{buff.spell_id}" == attr:
                return buff
        return self.empty_buff


def dummy_strategy(state: State):
    gcd = 2
    f"""
    actions=noraml
    # 敏锐最高优
    actions+=/奥术弹幕,if=buff.敏锐直觉.remains>0

    # 白炽耀焰: 有飞弹无精准打一下子飞弹，如果奥术迅疾要断了高优续上
    actions+=/奥术弹幕,if=buff.白炽耀焰.remains==0 & buff.奥术迅疾.stack>4 & buff.奥术迅疾.remains < gcd
    actions+=/奥术飞弹,if=buff.白炽耀焰.remains>gcd & buff.虚空精准.stack==0 & buff.节能施法.remains>0
    actions+=/奥术弹幕,if=buff.白炽耀焰.remains>0

    # 力量的重担的处理: 有虚空精准 则打了, 没有精准且有节能打飞弹
    actions+=/奥术飞弹,if=buff.力量的重担.remains>2.5 & buff.虚空精准.stack==0 & buff.节能施法.remains>0
    actions+=/奥术冲击,if=buff.力量的重担.remains>1 & buff.虚空精准.stack>1

    # 飞弹的填充, 1,2层的时候直接补精准, 3层及以上要在有2个节能施法时再补, 
    # TOOD 测试少补一些飞弹的效果
    # TODO奥术迅疾剩余时间不多的时候考虑下是不是少打点
    actions+=/奥术飞弹,if=buff.虚空精准.stack==0 & buff.法术火焰宝珠.stack<3
    actions+=/奥术飞弹,if=buff.虚空精准.stack==0 & buff.节能施法.stack>1
    
    actions+=/奥术冲击
    """    
    buff = BuffManager(state)

    # 爆发二段
    if buff.奥术之魂.remains > 1 and buff.虚空精准.stack > 0:
        return "爆发-奥术弹幕", "奥术之魂爆发"

    if buff.奥术之魂.remains > 1 and buff.虚空精准.stack == 0 and buff.节能施法.stack > 0:
        return "爆发-奥术飞弹", "奥术之魂爆发-飞弹"

    if buff.奥术之魂.remains < 1 and buff.奥术之魂.up:
        return "奥术弹幕", "收尾"
    
    # 敏锐直觉：剩余时间>0 则打奥术弹幕
    if buff.敏锐直觉.remains > 0:
        return "奥术弹幕", "敏锐直觉：剩余时间>0 则打奥术弹幕"

    # 白炽耀焰：若buff消失且奥术迅疾层数>4且剩余时间<gcd，则打奥术弹幕
    if buff.白炽耀焰.remains == 0 and buff.奥术迅疾.stack > 4 and buff.奥术迅疾.remains < gcd:
        return "奥术弹幕", "白炽耀焰：若buff消失且奥术迅疾层数>4且剩余时间<gcd，则打奥术弹幕"

    # 白炽耀焰：若buff剩余>gcd且虚空精准层数=0且节能施法剩余>0，则打奥术飞弹
    if buff.白炽耀焰.remains > gcd and buff.虚空精准.stack == 0 and buff.节能施法.remains > 0:
        return "奥术飞弹", "白炽耀焰：若buff剩余>gcd且虚空精准层数=0且节能施法剩余>0，则打奥术飞弹"

    # 白炽耀焰：若buff剩余>0，则打奥术弹幕
    if buff.白炽耀焰.remains > 0:
        return "奥术弹幕", "白炽耀焰：若buff剩余>0，则打奥术弹幕"

    # 力量的重担：若剩余>2.5且虚空精准层数=0且节能施法剩余>0，则打奥术飞弹
    if buff.力量的重担.remains > 2.5 and buff.虚空精准.stack == 0 and buff.节能施法.remains > 0:
        return "奥术飞弹", "力量的重担：若剩余>2.5且虚空精准层数=0且节能施法剩余>0，则打奥术飞弹"

    # 力量的重担：若剩余>1且虚空精准层数>1，则打奥术冲击
    if buff.力量的重担.remains > 1 and buff.虚空精准.stack > 1:
        return "奥术冲击", "力量的重担：若剩余>1且虚空精准层数>1，则打奥术冲击"

    # 飞弹填充：若虚空精准层数=0且法术火焰宝珠层数<3且节能施法层数>0，则打奥术飞弹
    if buff.虚空精准.stack == 0 and buff.id449400.stack < 3 and buff.节能施法.stack > 0:
        return "奥术飞弹", "飞弹填充：若虚空精准层数=0且法术火焰宝珠层数<3且节能施法层数>0，则打奥术飞弹"   

    # 飞弹填充：若虚空精准层数=0且节能施法层数>1，则打奥术飞弹
    if buff.虚空精准.stack == 0 and buff.节能施法.stack > 1:
        return "奥术飞弹", "飞弹填充：若虚空精准层数=0且节能施法层数>1，则打奥术飞弹"

    # 默认：奥术冲击
    return "奥术冲击", "默认：奥术冲击"


if __name__ == "__main__":
    state = State(
        buffs=[
            Buff(spell_id=1, stacks=1, remaining_ms=100, name="虚空精准", icon=0),
            Buff(spell_id=1, stacks=1, remaining_ms=100, name="敏锐直觉", icon=0),
        ]
    )
    print(dummy_strategy(state))
