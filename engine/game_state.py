from ast import main
from pydantic import BaseModel
from typing import Literal

class Item(BaseModel):
    name: str
    id: int
    icon: int

    def __hash__(self):
        return self.id

    def __eq__(self, other: 'Item'):
        return self.id == other.id

class Buff(Item, BaseModel):
    remain_ms: int
    stock: int

class Spell(Item, BaseModel):
    remain_ms: int  # 剩余冷却时间

class Action(Spell, BaseModel):
    start_ms: int
    end_ms: int
    type: Literal['cast', 'channel']

class BaseResource(BaseModel):
    health: int
    health_max: int

class MagaResouce(BaseModel):
    mega: int
    mega_max: int

class MagicResouce(BaseResource, MagaResouce):
    xx: int

class CoolDown(Item, BaseModel):
    remain_ms: int


if __name__ == '__main__':
    magic = MagicResouce(**{
        'health': 10,
        'health_max': 100,
        'mega': 100,
        'mega_max': 100,
        'xx': 4
    })
    print(magic)

    a = set()
    a.add(Buff(**{
        'name': '敏锐直觉',
        'id': 123,
        'icon': 456,
        'remain_ms': 1000,
        'stock': 1
    }))
    a.add(Buff(**{
        'name': '敏锐直觉2',
        'id': 124,
        'icon': 456,
        'remain_ms': 1000,
        'stock': 1
    }))
    print(a)