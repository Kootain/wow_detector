from abc import ABCMeta, abstractmethod
from pydantic import BaseModel

class TODO():
    pass


# 用于定义一个可以链式访问的
class Identifier(ABCMeta):
    @abstractmethod
    def can_resolve(self, attr: str) -> (bool, 'Identifier'):
        pass

    @abstractmethod
    def update(self, data: TODO) -> List[str]:
        # 更新数据，且返回 哪些 identifier 发生了变化
        pass


class Buff(Identifier):
    def can_resolve(self, attr: str) -> (bool, Identifier):
       # TODO: buff 的一些基本操作
       pass

    @property
    def up():
        pass

    @property
    def remains():
        pass


class BuffManager(Identifier):
    def can_resolve(self, attr: str) -> (bool, Identifier):
        # TODO: 从维护的buff列表中判断，访问的buff是否存在
        pass

    def __getattr__(attr: str) -> Buff:
        # TODO: 返回获取的buff
        pass

class StateManager(object):
    def __init__(self) -> None:
        self.buff = BuffManager()
        pass

class StateMonitor(object):
    def __init__(self, state_mananger) -> None:
        self.state_manager: StateManager = state_mananger
        self.strategy_observer = {} # key: identifier链 value: 监听的strategy的最大priority

    def update_state(self, state: TODO):
        # TODO: 把state里的数据更新到 state_manager里
        # TODO: 所有被更新的字段，需要给到一个
        changes = self.state_manager.update()
        for change in changes:
            # TODO: 需要按照priority 的优先级来遍历，一个高优先级的条件变更，则可以短路后面的所有判断
            for condition, priority in self.strategy_observer:
                # has effect 是一个前缀判断， 比如 buff.敏锐直觉.remains 会因为 buff.敏锐直接 变更而受影响
                if has_effect(change, condition):
                    return priority

    def register_strategy(self, strategy: str):
        strateies = parse_strategy(strategy)
        for (priority, strategy_conditions) in strateies:
            for condition in strategy_conditions:
                identifier = self.state_manager
                for i, identifier_name in enumerate(condition):
                    suc, identifier = identifier.can_resolve(identifier_name)
                    if not suc:
                        # TODO: 报错
                        error_chain = '.'.join(condition[:i])
                        raise ValueError(f'{error_chain} not exists')
                self.strategy_observer[condition] = min(priority, self.strategy_observer.get(condition, 9999))


class Engine(object):
    def __init__(self) -> None:
        self.state_mananger = StateManager()
        self.state_monitor = StateMonitor(self.state_mananger)
        self.current_action = None
        self.wait_for_execute_action = None

    def fetch_update():
        # 获取ingame的变化
        pass

    def do_strategy():
        # 执行策略推理
        pass

    def state_loop(self):
        # 状态变化后 1.更新predict 2. 检查是否需要更新当前待执行计划 3. 如果更新待执行计划，则要触发action_scedule
        state = self.fetch_update()
        change_priority = self.state_monitor.update_state(state)
        #TODO:
        if self.wait_for_execute_action.priority <= change_priority:
            self.wait_for_execute_action = self.do_strategy()
    
    def action_loop():
        select