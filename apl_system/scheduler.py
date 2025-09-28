#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
APL调度器模块

负责时间推进、事件调度和APL轮换的时间管理。
提供事件驱动的调度机制，支持定时事件、条件事件和优先级调度。

主要功能：
- 时间推进和管理
- 事件调度和处理
- APL轮换的时间控制
- 性能监控和统计
"""

import time
import heapq
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Any, Set
from enum import Enum
from collections import defaultdict


class EventType(Enum):
    """事件类型枚举"""
    TIMER = "timer"                    # 定时器事件
    COOLDOWN = "cooldown"              # 冷却完成事件
    BUFF_EXPIRE = "buff_expire"        # Buff过期事件
    RESOURCE_CHANGE = "resource_change" # 资源变化事件
    COMBAT_START = "combat_start"      # 战斗开始事件
    COMBAT_END = "combat_end"          # 战斗结束事件
    CUSTOM = "custom"                  # 自定义事件


class EventPriority(Enum):
    """事件优先级"""
    CRITICAL = 0    # 关键事件（立即处理）
    HIGH = 1        # 高优先级
    NORMAL = 2      # 普通优先级
    LOW = 3         # 低优先级


@dataclass
class ScheduledEvent:
    """调度事件"""
    event_id: str
    event_type: EventType
    scheduled_time: float
    priority: EventPriority = EventPriority.NORMAL
    data: Dict[str, Any] = field(default_factory=dict)
    callback: Optional[Callable] = None
    repeating: bool = False
    interval: float = 0.0
    max_repeats: int = -1  # -1表示无限重复
    repeat_count: int = 0
    
    def __lt__(self, other):
        """用于优先队列排序"""
        if self.scheduled_time != other.scheduled_time:
            return self.scheduled_time < other.scheduled_time
        return self.priority.value < other.priority.value


@dataclass
class SchedulerStats:
    """调度器统计信息"""
    total_events: int = 0
    processed_events: int = 0
    pending_events: int = 0
    events_by_type: Dict[EventType, int] = field(default_factory=lambda: defaultdict(int))
    average_processing_time: float = 0.0
    total_processing_time: float = 0.0
    simulation_time: float = 0.0
    real_time_elapsed: float = 0.0


class EventHandler(ABC):
    """事件处理器抽象基类"""
    
    @abstractmethod
    def handle_event(self, event: ScheduledEvent, scheduler: 'APLScheduler') -> bool:
        """处理事件
        
        Args:
            event: 要处理的事件
            scheduler: 调度器实例
            
        Returns:
            bool: 是否成功处理
        """
        pass


class DefaultEventHandler(EventHandler):
    """默认事件处理器"""
    
    def handle_event(self, event: ScheduledEvent, scheduler: 'APLScheduler') -> bool:
        """默认事件处理逻辑"""
        if event.callback:
            try:
                event.callback(event, scheduler)
                return True
            except Exception as e:
                print(f"事件处理错误: {e}")
                return False
        return True


class APLScheduler:
    """APL调度器
    
    负责管理时间推进、事件调度和APL轮换的时间控制。
    """
    
    def __init__(self):
        self.current_time: float = 0.0
        self.real_start_time: float = time.time()
        self.time_scale: float = 1.0  # 时间缩放因子
        
        # 事件队列（优先队列）
        self.event_queue: List[ScheduledEvent] = []
        self.event_handlers: Dict[EventType, EventHandler] = {}
        self.default_handler = DefaultEventHandler()
        
        # 事件管理
        self.active_events: Dict[str, ScheduledEvent] = {}
        self.event_counter: int = 0
        
        # 统计信息
        self.stats = SchedulerStats()
        
        # 调度控制
        self.running: bool = False
        self.paused: bool = False
        self.max_events_per_tick: int = 100
        
    def register_handler(self, event_type: EventType, handler: EventHandler):
        """注册事件处理器"""
        self.event_handlers[event_type] = handler
        
    def schedule_event(self, 
                      event_type: EventType,
                      delay: float,
                      priority: EventPriority = EventPriority.NORMAL,
                      data: Optional[Dict[str, Any]] = None,
                      callback: Optional[Callable] = None,
                      repeating: bool = False,
                      interval: float = 0.0,
                      max_repeats: int = -1) -> str:
        """调度事件
        
        Args:
            event_type: 事件类型
            delay: 延迟时间（秒）
            priority: 事件优先级
            data: 事件数据
            callback: 回调函数
            repeating: 是否重复
            interval: 重复间隔
            max_repeats: 最大重复次数
            
        Returns:
            str: 事件ID
        """
        self.event_counter += 1
        event_id = f"event_{self.event_counter}"
        
        scheduled_time = self.current_time + delay
        
        event = ScheduledEvent(
            event_id=event_id,
            event_type=event_type,
            scheduled_time=scheduled_time,
            priority=priority,
            data=data or {},
            callback=callback,
            repeating=repeating,
            interval=interval,
            max_repeats=max_repeats
        )
        
        heapq.heappush(self.event_queue, event)
        self.active_events[event_id] = event
        self.stats.total_events += 1
        self.stats.pending_events += 1
        
        return event_id
        
    def cancel_event(self, event_id: str) -> bool:
        """取消事件"""
        if event_id in self.active_events:
            event = self.active_events[event_id]
            # 标记为已取消（实际从队列中移除比较复杂）
            event.callback = None
            del self.active_events[event_id]
            self.stats.pending_events -= 1
            return True
        return False
        
    def schedule_timer(self, delay: float, callback: Callable, repeating: bool = False) -> str:
        """调度定时器"""
        return self.schedule_event(
            EventType.TIMER,
            delay,
            callback=callback,
            repeating=repeating,
            interval=delay if repeating else 0.0
        )
        
    def schedule_cooldown_event(self, ability_name: str, cooldown_time: float, callback: Optional[Callable] = None) -> str:
        """调度冷却完成事件"""
        return self.schedule_event(
            EventType.COOLDOWN,
            cooldown_time,
            data={"ability": ability_name},
            callback=callback
        )
        
    def schedule_buff_expire(self, buff_name: str, duration: float, callback: Optional[Callable] = None) -> str:
        """调度Buff过期事件"""
        return self.schedule_event(
            EventType.BUFF_EXPIRE,
            duration,
            data={"buff": buff_name},
            callback=callback
        )
        
    def advance_time(self, delta_time: float):
        """推进时间"""
        if self.paused:
            return
            
        self.current_time += delta_time * self.time_scale
        self.stats.simulation_time = self.current_time
        self.stats.real_time_elapsed = time.time() - self.real_start_time
        
    def process_events(self) -> int:
        """处理当前时间的所有事件
        
        Returns:
            int: 处理的事件数量
        """
        if self.paused:
            return 0
            
        processed_count = 0
        events_this_tick = 0
        
        while (self.event_queue and 
               self.event_queue[0].scheduled_time <= self.current_time and
               events_this_tick < self.max_events_per_tick):
            
            event = heapq.heappop(self.event_queue)
            events_this_tick += 1
            
            # 检查事件是否已被取消
            if event.event_id not in self.active_events:
                continue
                
            # 处理事件
            start_time = time.time()
            success = self._handle_event(event)
            processing_time = time.time() - start_time
            
            if success:
                processed_count += 1
                self.stats.processed_events += 1
                self.stats.events_by_type[event.event_type] += 1
                self.stats.total_processing_time += processing_time
                
                # 更新平均处理时间
                if self.stats.processed_events > 0:
                    self.stats.average_processing_time = (
                        self.stats.total_processing_time / self.stats.processed_events
                    )
                
                # 处理重复事件
                if event.repeating and (event.max_repeats == -1 or event.repeat_count < event.max_repeats):
                    event.repeat_count += 1
                    event.scheduled_time = self.current_time + event.interval
                    heapq.heappush(self.event_queue, event)
                else:
                    # 移除已完成的事件
                    if event.event_id in self.active_events:
                        del self.active_events[event.event_id]
                        self.stats.pending_events -= 1
            
        return processed_count
        
    def _handle_event(self, event: ScheduledEvent) -> bool:
        """处理单个事件"""
        handler = self.event_handlers.get(event.event_type, self.default_handler)
        return handler.handle_event(event, self)
        
    def tick(self, delta_time: float) -> int:
        """调度器时钟周期
        
        Args:
            delta_time: 时间增量
            
        Returns:
            int: 处理的事件数量
        """
        self.advance_time(delta_time)
        return self.process_events()
        
    def run_for_duration(self, duration: float, tick_rate: float = 0.1) -> SchedulerStats:
        """运行调度器指定时间
        
        Args:
            duration: 运行时长（模拟时间）
            tick_rate: 时钟频率（秒）
            
        Returns:
            SchedulerStats: 运行统计
        """
        self.running = True
        start_time = self.current_time
        
        while self.running and (self.current_time - start_time) < duration:
            self.tick(tick_rate)
            
            # 如果没有待处理事件，可以跳过空闲时间
            if not self.event_queue:
                break
                
        self.running = False
        return self.stats
        
    def pause(self):
        """暂停调度器"""
        self.paused = True
        
    def resume(self):
        """恢复调度器"""
        self.paused = False
        
    def stop(self):
        """停止调度器"""
        self.running = False
        
    def reset(self):
        """重置调度器"""
        self.current_time = 0.0
        self.real_start_time = time.time()
        self.event_queue.clear()
        self.active_events.clear()
        self.event_counter = 0
        self.stats = SchedulerStats()
        self.running = False
        self.paused = False
        
    def get_pending_events(self) -> List[ScheduledEvent]:
        """获取待处理事件列表"""
        return sorted(self.event_queue, key=lambda e: e.scheduled_time)
        
    def get_stats(self) -> SchedulerStats:
        """获取统计信息"""
        return self.stats


class APLRotationScheduler:
    """APL轮换调度器
    
    专门用于管理APL轮换的高级调度器。
    """
    
    def __init__(self, scheduler: APLScheduler):
        self.scheduler = scheduler
        self.rotation_active = False
        self.gcd_duration = 1.5  # 全局冷却时间
        self.last_gcd_time = 0.0
        self.action_queue: List[str] = []
        
    def can_cast_now(self) -> bool:
        """检查是否可以立即施法"""
        return (self.scheduler.current_time - self.last_gcd_time) >= self.gcd_duration
        
    def schedule_action(self, action_name: str, cast_time: float = 0.0) -> str:
        """调度动作执行"""
        if not self.can_cast_now():
            # 等待GCD结束
            delay = self.gcd_duration - (self.scheduler.current_time - self.last_gcd_time)
        else:
            delay = 0.0
            
        def execute_action(event, scheduler):
            self.last_gcd_time = scheduler.current_time
            print(f"执行动作: {action_name} (时间: {scheduler.current_time:.2f})")
            
        return self.scheduler.schedule_event(
            EventType.CUSTOM,
            delay,
            data={"action": action_name, "cast_time": cast_time},
            callback=execute_action
        )
        
    def start_rotation(self):
        """开始轮换"""
        self.rotation_active = True
        
    def stop_rotation(self):
        """停止轮换"""
        self.rotation_active = False


# 测试代码
if __name__ == "__main__":
    # 创建调度器
    scheduler = APLScheduler()
    
    # 测试基本事件调度
    def test_callback(event, sched):
        print(f"事件触发: {event.event_type.value} (ID: {event.event_id}, 时间: {sched.current_time:.2f})")
    
    # 调度一些测试事件
    scheduler.schedule_timer(1.0, test_callback)
    scheduler.schedule_timer(2.5, test_callback)
    scheduler.schedule_cooldown_event("火球术", 3.0, test_callback)
    scheduler.schedule_buff_expire("法师护甲", 4.0, test_callback)
    
    # 调度重复事件
    scheduler.schedule_timer(0.5, test_callback, repeating=True)
    
    print("开始调度器测试...")
    print(f"初始待处理事件: {len(scheduler.get_pending_events())}")
    
    # 运行调度器
    stats = scheduler.run_for_duration(5.0, 0.1)
    
    print(f"\n调度器统计:")
    print(f"总事件数: {stats.total_events}")
    print(f"已处理事件: {stats.processed_events}")
    print(f"待处理事件: {stats.pending_events}")
    print(f"平均处理时间: {stats.average_processing_time:.6f}秒")
    print(f"模拟时间: {stats.simulation_time:.2f}秒")
    
    # 测试APL轮换调度器
    print("\n测试APL轮换调度器...")
    scheduler.reset()
    rotation_scheduler = APLRotationScheduler(scheduler)
    
    # 模拟一个简单的轮换
    rotation_scheduler.start_rotation()
    rotation_scheduler.schedule_action("火球术")
    rotation_scheduler.schedule_action("冰箭术")
    rotation_scheduler.schedule_action("奥术飞弹")
    
    scheduler.run_for_duration(10.0, 0.1)
    
    print("调度器测试完成！")