"""APL Context - Game state access interface for APL expressions

Provides the context interface that APL expressions use to access game state:
- Player stats (health, mana, energy, etc.)
- Buff/debuff states
- Cooldown information
- Target information
- Custom variables and functions

The context acts as a bridge between APL expressions and the actual game state,
allowing expressions to query current conditions without knowing the underlying
implementation details.
"""

from typing import Dict, List, Any, Optional, Callable, Union
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
import time
import math


class ContextError(Exception):
    """Exception raised when context operations fail"""
    pass


@dataclass
class ResourceInfo:
    """Information about a resource (mana, energy, etc.)"""
    current: float = 0.0
    maximum: float = 100.0
    regen_rate: float = 0.0  # per second
    last_update: float = 0.0
    
    @property
    def pct(self) -> float:
        """Resource as percentage (0-100)"""
        if self.maximum <= 0:
            return 0.0
        return (self.current / self.maximum) * 100.0
    
    @property
    def deficit(self) -> float:
        """Amount missing from maximum"""
        return max(0.0, self.maximum - self.current)
    
    @property
    def deficit_pct(self) -> float:
        """Deficit as percentage"""
        if self.maximum <= 0:
            return 0.0
        return (self.deficit / self.maximum) * 100.0
    
    def update(self, current_time: float):
        """Update resource based on regen rate"""
        if self.last_update > 0 and self.regen_rate > 0:
            dt = current_time - self.last_update
            self.current = min(self.maximum, self.current + self.regen_rate * dt)
        self.last_update = current_time


@dataclass
class BuffInfo:
    """Information about a buff/debuff"""
    name: str
    stacks: int = 0
    duration: float = 0.0
    max_stacks: int = 1
    expires_at: float = 0.0
    
    @property
    def up(self) -> float:
        """1.0 if buff is active, 0.0 otherwise"""
        return 1.0 if self.stacks > 0 and self.duration > 0 else 0.0
    
    @property
    def down(self) -> float:
        """1.0 if buff is not active, 0.0 otherwise"""
        return 1.0 - self.up
    
    @property
    def remains(self) -> float:
        """Time remaining on buff"""
        return max(0.0, self.duration)
    
    def update(self, current_time: float):
        """Update buff duration"""
        if self.expires_at > 0 and current_time >= self.expires_at:
            self.stacks = 0
            self.duration = 0.0
            self.expires_at = 0.0
        elif self.expires_at > 0:
            self.duration = self.expires_at - current_time


@dataclass
class CooldownInfo:
    """Information about an ability cooldown"""
    name: str
    duration: float = 0.0
    charges: int = 1
    max_charges: int = 1
    charge_time: float = 0.0
    ready_at: float = 0.0
    
    @property
    def ready(self) -> float:
        """1.0 if ability is ready, 0.0 otherwise"""
        return 1.0 if self.charges > 0 or self.duration <= 0 else 0.0
    
    @property
    def remains(self) -> float:
        """Time remaining on cooldown"""
        return max(0.0, self.duration)
    
    def update(self, current_time: float):
        """Update cooldown state"""
        if self.ready_at > 0 and current_time >= self.ready_at:
            self.charges = min(self.max_charges, self.charges + 1)
            if self.charges < self.max_charges and self.charge_time > 0:
                self.ready_at = current_time + self.charge_time
            else:
                self.ready_at = 0.0
                self.duration = 0.0
        elif self.ready_at > 0:
            self.duration = self.ready_at - current_time


@dataclass
class TargetInfo:
    """Information about current target"""
    name: str = "target"
    health: ResourceInfo = field(default_factory=lambda: ResourceInfo(100, 100))
    distance: float = 0.0
    level: int = 1
    classification: str = "normal"  # normal, elite, boss, etc.
    time_to_die: float = 999.0  # estimated time to die
    adds: int = 0  # number of additional enemies
    
    def update(self, current_time: float):
        """Update target information"""
        self.health.update(current_time)


class APLContext(ABC):
    """Abstract base class for APL execution context"""
    
    @abstractmethod
    def resolve_identifier(self, parts: List[str]) -> float:
        """Resolve a dot-notation identifier to a numeric value"""
        pass
    
    @abstractmethod
    def call_function(self, name: str, args: List[float]) -> float:
        """Call a custom function"""
        pass
    
    @abstractmethod
    def get_current_time(self) -> float:
        """Get current simulation time"""
        pass
    
    @abstractmethod
    def update(self, current_time: float):
        """Update context state to current time"""
        pass


class GameContext(APLContext):
    """Concrete implementation of APL context for game state"""
    
    def __init__(self):
        # Core resources
        self.health = ResourceInfo(100, 100, 0)
        self.mana = ResourceInfo(100, 100, 5.0)
        self.energy = ResourceInfo(100, 100, 10.0)
        self.focus = ResourceInfo(100, 100, 5.0)
        self.rage = ResourceInfo(0, 100, 0)
        
        # Buffs and debuffs
        self.buffs: Dict[str, BuffInfo] = {}
        self.debuffs: Dict[str, BuffInfo] = {}
        
        # Cooldowns
        self.cooldowns: Dict[str, CooldownInfo] = {}
        
        # Target information
        self.target = TargetInfo()
        
        # Custom variables
        self.variables: Dict[str, float] = {}
        
        # Custom functions
        self.functions: Dict[str, Callable] = {}
        
        # Time tracking
        self.current_time = 0.0
        self.start_time = time.time()
        
        # Combat state
        self.in_combat = False
        self.gcd_remains = 0.0
        self.cast_time = 0.0
        
        # Player info
        self.level = 60
        self.class_name = "hunter"
        self.spec_name = "marksmanship"
    
    def resolve_identifier(self, parts: List[str]) -> float:
        """Resolve dot-notation identifier to numeric value"""
        if not parts:
            return 0.0
        
        root = parts[0].lower()
        
        # Resource access
        if root in ["health", "mana", "energy", "focus", "rage"]:
            resource = getattr(self, root)
            if len(parts) == 1:
                return resource.current
            elif len(parts) == 2:
                attr = parts[1].lower()
                if hasattr(resource, attr):
                    value = getattr(resource, attr)
                    return float(value) if isinstance(value, (int, float)) else 0.0
        
        # Buff access
        elif root == "buff":
            if len(parts) >= 2:
                buff_name = parts[1].lower()
                buff = self.buffs.get(buff_name)
                if buff is None:
                    return 0.0
                
                if len(parts) == 2:
                    return buff.up
                elif len(parts) == 3:
                    attr = parts[2].lower()
                    if hasattr(buff, attr):
                        value = getattr(buff, attr)
                        return float(value) if isinstance(value, (int, float)) else 0.0
        
        # Debuff access
        elif root == "debuff":
            if len(parts) >= 2:
                debuff_name = parts[1].lower()
                debuff = self.debuffs.get(debuff_name)
                if debuff is None:
                    return 0.0
                
                if len(parts) == 2:
                    return debuff.up
                elif len(parts) == 3:
                    attr = parts[2].lower()
                    if hasattr(debuff, attr):
                        value = getattr(debuff, attr)
                        return float(value) if isinstance(value, (int, float)) else 0.0
        
        # Cooldown access
        elif root == "cooldown":
            if len(parts) >= 2:
                cd_name = parts[1].lower()
                cooldown = self.cooldowns.get(cd_name)
                if cooldown is None:
                    return 0.0
                
                if len(parts) == 2:
                    return cooldown.ready
                elif len(parts) == 3:
                    attr = parts[2].lower()
                    if hasattr(cooldown, attr):
                        value = getattr(cooldown, attr)
                        return float(value) if isinstance(value, (int, float)) else 0.0
        
        # Target access
        elif root == "target":
            if len(parts) == 1:
                return 1.0 if self.target else 0.0
            elif len(parts) >= 2:
                attr = parts[1].lower()
                
                # Target health
                if attr == "health":
                    if len(parts) == 2:
                        return self.target.health.current
                    elif len(parts) == 3:
                        health_attr = parts[2].lower()
                        if hasattr(self.target.health, health_attr):
                            value = getattr(self.target.health, health_attr)
                            return float(value) if isinstance(value, (int, float)) else 0.0
                
                # Other target attributes
                elif hasattr(self.target, attr):
                    value = getattr(self.target, attr)
                    return float(value) if isinstance(value, (int, float)) else 0.0
        
        # Time-related
        elif root == "time":
            return self.current_time
        
        # Combat state
        elif root == "gcd":
            if len(parts) == 1:
                return self.gcd_remains
            elif len(parts) == 2 and parts[1].lower() == "remains":
                return self.gcd_remains
        
        # Custom variables
        elif root in self.variables:
            return self.variables[root]
        
        # Player info
        elif root == "level":
            return float(self.level)
        
        # Default: return 0 for unknown identifiers
        return 0.0
    
    def call_function(self, name: str, args: List[float]) -> float:
        """Call custom function"""
        name = name.lower()
        
        # Built-in utility functions
        if name == "time_to_pct":
            # time_to_pct(resource, target_pct) - time to reach target percentage
            if len(args) >= 2:
                # This would need resource name resolution - simplified for now
                return 10.0  # placeholder
        
        elif name == "time_to_max":
            # time_to_max(resource) - time to reach maximum
            if len(args) >= 1:
                return 20.0  # placeholder
        
        # Custom functions
        elif name in self.functions:
            return self.functions[name](*args)
        
        # Unknown function
        raise ValueError(f"Unknown function: {name}")
    
    def get_current_time(self) -> float:
        """Get current simulation time"""
        return self.current_time
    
    def update(self, current_time: float):
        """Update all context state to current time"""
        self.current_time = current_time
        
        # Update resources
        self.health.update(current_time)
        self.mana.update(current_time)
        self.energy.update(current_time)
        self.focus.update(current_time)
        self.rage.update(current_time)
        
        # Update buffs
        for buff in self.buffs.values():
            buff.update(current_time)
        
        # Update debuffs
        for debuff in self.debuffs.values():
            debuff.update(current_time)
        
        # Update cooldowns
        for cooldown in self.cooldowns.values():
            cooldown.update(current_time)
        
        # Update target
        self.target.update(current_time)
        
        # Update GCD
        if self.gcd_remains > 0:
            self.gcd_remains = max(0.0, self.gcd_remains - 0.1)  # Assume 100ms updates
    
    # Convenience methods for setting up state
    def set_resource(self, name: str, current: float, maximum: float = None, regen: float = None):
        """Set resource values"""
        if hasattr(self, name):
            resource = getattr(self, name)
            resource.current = current
            if maximum is not None:
                resource.maximum = maximum
            if regen is not None:
                resource.regen_rate = regen
    
    def add_buff(self, name: str, duration: float = 0.0, stacks: int = 1, max_stacks: int = 1):
        """Add or update a buff"""
        name = name.lower()
        expires_at = self.current_time + duration if duration > 0 else 0.0
        self.buffs[name] = BuffInfo(name, stacks, duration, max_stacks, expires_at)
    
    def remove_buff(self, name: str):
        """Remove a buff"""
        name = name.lower()
        if name in self.buffs:
            del self.buffs[name]
    
    def add_debuff(self, name: str, duration: float = 0.0, stacks: int = 1, max_stacks: int = 1):
        """Add or update a debuff"""
        name = name.lower()
        expires_at = self.current_time + duration if duration > 0 else 0.0
        self.debuffs[name] = BuffInfo(name, stacks, duration, max_stacks, expires_at)
    
    def remove_debuff(self, name: str):
        """Remove a debuff"""
        name = name.lower()
        if name in self.debuffs:
            del self.debuffs[name]
    
    def set_cooldown(self, name: str, duration: float, charges: int = 1, max_charges: int = 1):
        """Set cooldown state"""
        name = name.lower()
        ready_at = self.current_time + duration if duration > 0 else 0.0
        self.cooldowns[name] = CooldownInfo(name, duration, charges, max_charges, duration, ready_at)
    
    def trigger_gcd(self, duration: float = 1.5):
        """Trigger global cooldown"""
        self.gcd_remains = duration
    
    def set_variable(self, name: str, value: float):
        """Set custom variable"""
        self.variables[name] = value
    
    def register_function(self, name: str, func: Callable):
        """Register custom function"""
        self.functions[name] = func


if __name__ == "__main__":
    # Test the context
    context = GameContext()
    
    # Set up some test state
    context.set_resource("mana", 75, 100, 5.0)
    context.set_resource("health", 80, 100)
    context.add_buff("arcane_power", 15.0)
    context.add_debuff("hunter_mark", 30.0)
    context.set_cooldown("arcane_shot", 0.0)  # Ready
    context.set_cooldown("aimed_shot", 5.0)   # On cooldown
    
    # Test identifier resolution
    test_identifiers = [
        ["mana"],
        ["mana", "pct"],
        ["health", "deficit"],
        ["buff", "arcane_power", "up"],
        ["buff", "arcane_power", "remains"],
        ["debuff", "hunter_mark", "up"],
        ["cooldown", "arcane_shot", "ready"],
        ["cooldown", "aimed_shot", "remains"],
        ["target", "health", "pct"],
        ["time"]
    ]
    
    print("Testing identifier resolution:")
    for identifier in test_identifiers:
        value = context.resolve_identifier(identifier)
        print(f"  {'.'.join(identifier)} = {value}")
    
    # Test time progression
    print("\nTesting time progression:")
    for i in range(3):
        context.update(context.current_time + 5.0)
        mana_pct = context.resolve_identifier(["mana", "pct"])
        buff_remains = context.resolve_identifier(["buff", "arcane_power", "remains"])
        cd_remains = context.resolve_identifier(["cooldown", "aimed_shot", "remains"])
        print(f"  Time {context.current_time}: mana={mana_pct:.1f}%, buff={buff_remains:.1f}s, cd={cd_remains:.1f}s")