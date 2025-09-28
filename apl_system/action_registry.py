"""APL Action Registry - Centralized action management system

Provides a flexible system for registering, managing, and executing actions:
- Dynamic action registration with metadata
- Category-based organization
- Validation and error handling
- Performance monitoring
- Plugin-style extensibility

Actions can be registered from multiple sources and organized by categories
like spells, items, macros, etc.
"""

from typing import Dict, List, Set, Any, Optional, Callable, Union
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from enum import Enum
import time
import inspect


class ActionCategory(Enum):
    """Categories for organizing actions"""
    SPELL = "spell"
    ITEM = "item"
    MACRO = "macro"
    BUFF = "buff"
    DEBUFF = "debuff"
    MOVEMENT = "movement"
    TARGETING = "targeting"
    UTILITY = "utility"
    CUSTOM = "custom"


class ActionResult(Enum):
    """Result of action execution"""
    SUCCESS = "success"
    FAILED = "failed"
    NOT_READY = "not_ready"
    INVALID_TARGET = "invalid_target"
    INSUFFICIENT_RESOURCES = "insufficient_resources"
    ON_COOLDOWN = "on_cooldown"
    INTERRUPTED = "interrupted"


@dataclass
class ActionMetadata:
    """Metadata for an action"""
    name: str
    category: ActionCategory
    description: str = ""
    cooldown: float = 0.0
    cast_time: float = 0.0
    gcd: float = 1.5
    resource_cost: Dict[str, float] = field(default_factory=dict)
    range: float = 0.0
    requires_target: bool = False
    can_interrupt: bool = True
    tags: Set[str] = field(default_factory=set)
    priority: int = 0
    
    def __post_init__(self):
        if isinstance(self.category, str):
            self.category = ActionCategory(self.category)


class ActionHandler(ABC):
    """Abstract base class for action handlers"""
    
    @abstractmethod
    def can_execute(self, context: Any, target: Any = None) -> bool:
        """Check if action can be executed"""
        pass
    
    @abstractmethod
    def execute(self, context: Any, target: Any = None) -> ActionResult:
        """Execute the action"""
        pass
    
    @abstractmethod
    def get_cooldown_remaining(self, context: Any) -> float:
        """Get remaining cooldown time"""
        pass
    
    def get_cast_time(self, context: Any) -> float:
        """Get current cast time (may be modified by buffs)"""
        return 0.0
    
    def get_resource_cost(self, context: Any) -> Dict[str, float]:
        """Get current resource cost (may be modified by buffs)"""
        return {}


class SimpleActionHandler(ActionHandler):
    """Simple action handler using callable functions"""
    
    def __init__(self, 
                 can_execute_func: Callable[[Any, Any], bool],
                 execute_func: Callable[[Any, Any], ActionResult],
                 cooldown_func: Optional[Callable[[Any], float]] = None):
        self.can_execute_func = can_execute_func
        self.execute_func = execute_func
        self.cooldown_func = cooldown_func or (lambda ctx: 0.0)
    
    def can_execute(self, context: Any, target: Any = None) -> bool:
        return self.can_execute_func(context, target)
    
    def execute(self, context: Any, target: Any = None) -> ActionResult:
        return self.execute_func(context, target)
    
    def get_cooldown_remaining(self, context: Any) -> float:
        return self.cooldown_func(context)


@dataclass
class RegisteredAction:
    """A registered action with metadata and handler"""
    metadata: ActionMetadata
    handler: ActionHandler
    registered_at: float = field(default_factory=time.time)
    usage_count: int = 0
    last_used: float = 0.0
    
    def can_execute(self, context: Any, target: Any = None) -> bool:
        """Check if action can be executed"""
        return self.handler.can_execute(context, target)
    
    def execute(self, context: Any, target: Any = None) -> ActionResult:
        """Execute the action"""
        result = self.handler.execute(context, target)
        self.usage_count += 1
        self.last_used = time.time()
        return result
    
    def get_cooldown_remaining(self, context: Any) -> float:
        """Get remaining cooldown"""
        return self.handler.get_cooldown_remaining(context)


class ActionRegistry:
    """Central registry for all actions"""
    
    def __init__(self):
        self.actions: Dict[str, RegisteredAction] = {}
        self.categories: Dict[ActionCategory, Set[str]] = {}
        self.tags: Dict[str, Set[str]] = {}
        self.aliases: Dict[str, str] = {}
        
        # Initialize categories
        for category in ActionCategory:
            self.categories[category] = set()
    
    def register(self, 
                 name: str,
                 handler: ActionHandler,
                 category: Union[ActionCategory, str] = ActionCategory.CUSTOM,
                 description: str = "",
                 **metadata_kwargs) -> bool:
        """Register an action"""
        if name in self.actions:
            print(f"Warning: Action '{name}' already registered, overwriting")
        
        # Create metadata
        if isinstance(category, str):
            category = ActionCategory(category)
        
        metadata = ActionMetadata(
            name=name,
            category=category,
            description=description,
            **metadata_kwargs
        )
        
        # Create registered action
        action = RegisteredAction(metadata=metadata, handler=handler)
        
        # Store action
        self.actions[name] = action
        self.categories[category].add(name)
        
        # Update tags
        for tag in metadata.tags:
            if tag not in self.tags:
                self.tags[tag] = set()
            self.tags[tag].add(name)
        
        return True
    
    def register_simple(self,
                       name: str,
                       can_execute_func: Callable[[Any, Any], bool],
                       execute_func: Callable[[Any, Any], ActionResult],
                       cooldown_func: Optional[Callable[[Any], float]] = None,
                       **metadata_kwargs) -> bool:
        """Register a simple action using functions"""
        handler = SimpleActionHandler(can_execute_func, execute_func, cooldown_func)
        return self.register(name, handler, **metadata_kwargs)
    
    def register_spell(self, 
                      spell_name: str,
                      spell_id: Optional[int] = None,
                      **metadata_kwargs) -> bool:
        """Register a spell action"""
        def can_execute(context, target):
            # Check if spell is known and off cooldown
            if hasattr(context, 'is_spell_known') and not context.is_spell_known(spell_name):
                return False
            if hasattr(context, 'get_spell_cooldown'):
                return context.get_spell_cooldown(spell_name) <= 0
            return True
        
        def execute(context, target):
            # Cast the spell
            if hasattr(context, 'cast_spell'):
                return context.cast_spell(spell_name, target)
            return ActionResult.SUCCESS
        
        def get_cooldown(context):
            if hasattr(context, 'get_spell_cooldown'):
                return context.get_spell_cooldown(spell_name)
            return 0.0
        
        return self.register_simple(
            spell_name,
            can_execute,
            execute,
            get_cooldown,
            category=ActionCategory.SPELL,
            **metadata_kwargs
        )
    
    def register_item(self,
                     item_name: str,
                     item_id: Optional[int] = None,
                     **metadata_kwargs) -> bool:
        """Register an item action"""
        def can_execute(context, target):
            # Check if item is available and off cooldown
            if hasattr(context, 'has_item') and not context.has_item(item_name):
                return False
            if hasattr(context, 'get_item_cooldown'):
                return context.get_item_cooldown(item_name) <= 0
            return True
        
        def execute(context, target):
            # Use the item
            if hasattr(context, 'use_item'):
                return context.use_item(item_name, target)
            return ActionResult.SUCCESS
        
        def get_cooldown(context):
            if hasattr(context, 'get_item_cooldown'):
                return context.get_item_cooldown(item_name)
            return 0.0
        
        return self.register_simple(
            item_name,
            can_execute,
            execute,
            get_cooldown,
            category=ActionCategory.ITEM,
            **metadata_kwargs
        )
    
    def add_alias(self, alias: str, action_name: str) -> bool:
        """Add an alias for an action"""
        if action_name not in self.actions:
            return False
        self.aliases[alias] = action_name
        return True
    
    def get_action(self, name: str) -> Optional[RegisteredAction]:
        """Get an action by name or alias"""
        # Check direct name first
        if name in self.actions:
            return self.actions[name]
        
        # Check aliases
        if name in self.aliases:
            return self.actions[self.aliases[name]]
        
        return None
    
    def get_actions_by_category(self, category: ActionCategory) -> List[RegisteredAction]:
        """Get all actions in a category"""
        if category not in self.categories:
            return []
        
        return [self.actions[name] for name in self.categories[category]]
    
    def get_actions_by_tag(self, tag: str) -> List[RegisteredAction]:
        """Get all actions with a specific tag"""
        if tag not in self.tags:
            return []
        
        return [self.actions[name] for name in self.tags[tag]]
    
    def find_actions(self, 
                    category: Optional[ActionCategory] = None,
                    tags: Optional[Set[str]] = None,
                    name_pattern: Optional[str] = None) -> List[RegisteredAction]:
        """Find actions matching criteria"""
        results = []
        
        for name, action in self.actions.items():
            # Check category
            if category and action.metadata.category != category:
                continue
            
            # Check tags
            if tags and not tags.intersection(action.metadata.tags):
                continue
            
            # Check name pattern
            if name_pattern and name_pattern.lower() not in name.lower():
                continue
            
            results.append(action)
        
        return results
    
    def get_available_actions(self, context: Any, target: Any = None) -> List[RegisteredAction]:
        """Get all actions that can currently be executed"""
        available = []
        
        for action in self.actions.values():
            try:
                if action.can_execute(context, target):
                    available.append(action)
            except Exception as e:
                print(f"Warning: Error checking action {action.metadata.name}: {e}")
        
        return available
    
    def unregister(self, name: str) -> bool:
        """Unregister an action"""
        if name not in self.actions:
            return False
        
        action = self.actions[name]
        
        # Remove from categories
        self.categories[action.metadata.category].discard(name)
        
        # Remove from tags
        for tag in action.metadata.tags:
            if tag in self.tags:
                self.tags[tag].discard(name)
                if not self.tags[tag]:
                    del self.tags[tag]
        
        # Remove aliases
        aliases_to_remove = [alias for alias, target in self.aliases.items() if target == name]
        for alias in aliases_to_remove:
            del self.aliases[alias]
        
        # Remove action
        del self.actions[name]
        
        return True
    
    def clear(self):
        """Clear all registered actions"""
        self.actions.clear()
        self.aliases.clear()
        self.tags.clear()
        for category in self.categories:
            self.categories[category].clear()
    
    def get_registry_info(self) -> Dict[str, Any]:
        """Get registry statistics"""
        return {
            'total_actions': len(self.actions),
            'categories': {cat.value: len(actions) for cat, actions in self.categories.items()},
            'total_aliases': len(self.aliases),
            'total_tags': len(self.tags),
            'most_used': max(self.actions.values(), key=lambda a: a.usage_count, default=None)
        }
    
    def list_actions(self) -> List[str]:
        """List all registered action names"""
        return list(self.actions.keys())
    
    def validate_actions(self, context: Any) -> Dict[str, List[str]]:
        """Validate all registered actions"""
        issues = {'errors': [], 'warnings': []}
        
        for name, action in self.actions.items():
            try:
                # Try to check if action can execute
                action.can_execute(context)
            except Exception as e:
                issues['errors'].append(f"Action '{name}': {e}")
        
        return issues


# Global registry instance
_global_registry = ActionRegistry()


def get_global_registry() -> ActionRegistry:
    """Get the global action registry"""
    return _global_registry


def register_action(name: str, handler: ActionHandler, **kwargs) -> bool:
    """Register an action in the global registry"""
    return _global_registry.register(name, handler, **kwargs)


def register_simple_action(name: str, 
                          can_execute_func: Callable[[Any, Any], bool],
                          execute_func: Callable[[Any, Any], ActionResult],
                          **kwargs) -> bool:
    """Register a simple action in the global registry"""
    return _global_registry.register_simple(name, can_execute_func, execute_func, **kwargs)


def get_action(name: str) -> Optional[RegisteredAction]:
    """Get an action from the global registry"""
    return _global_registry.get_action(name)


if __name__ == "__main__":
    # Test the action registry
    from .context import GameContext
    
    # Create test context
    context = GameContext()
    context.set_resource("mana", 80, 100)
    context.set_cooldown("fireball", 0.0)
    context.set_cooldown("frostbolt", 2.5)
    
    # Create registry
    registry = ActionRegistry()
    
    # Register some test actions
    def fireball_can_execute(ctx, target):
        return ctx.get_resource("mana").current >= 30 and ctx.get_cooldown("fireball").remaining <= 0
    
    def fireball_execute(ctx, target):
        print(f"Casting Fireball on {target or 'current target'}")
        ctx.consume_resource("mana", 30)
        ctx.set_cooldown("fireball", 2.5)
        return ActionResult.SUCCESS
    
    def fireball_cooldown(ctx):
        return ctx.get_cooldown("fireball").remaining
    
    registry.register_simple(
        "fireball",
        fireball_can_execute,
        fireball_execute,
        fireball_cooldown,
        category=ActionCategory.SPELL,
        description="A powerful fire spell",
        cooldown=2.5,
        cast_time=2.5,
        resource_cost={"mana": 30},
        tags={"damage", "fire"}
    )
    
    # Register using spell helper
    registry.register_spell(
        "frostbolt",
        description="A frost spell that slows the target",
        cooldown=1.5,
        cast_time=2.0,
        resource_cost={"mana": 25},
        tags={"damage", "frost", "slow"}
    )
    
    # Add aliases
    registry.add_alias("fb", "fireball")
    registry.add_alias("frost", "frostbolt")
    
    # Test the registry
    print("Testing Action Registry:")
    print(f"Total actions: {len(registry.actions)}")
    
    # Test getting actions
    fireball = registry.get_action("fireball")
    if fireball:
        print(f"\nFireball action:")
        print(f"  Category: {fireball.metadata.category.value}")
        print(f"  Description: {fireball.metadata.description}")
        print(f"  Can execute: {fireball.can_execute(context)}")
        print(f"  Cooldown remaining: {fireball.get_cooldown_remaining(context)}")
    
    # Test alias
    fb_alias = registry.get_action("fb")
    print(f"\nAlias 'fb' points to: {fb_alias.metadata.name if fb_alias else 'None'}")
    
    # Test finding actions
    fire_actions = registry.get_actions_by_tag("fire")
    print(f"\nFire actions: {[a.metadata.name for a in fire_actions]}")
    
    spell_actions = registry.get_actions_by_category(ActionCategory.SPELL)
    print(f"Spell actions: {[a.metadata.name for a in spell_actions]}")
    
    # Test available actions
    available = registry.get_available_actions(context)
    print(f"\nAvailable actions: {[a.metadata.name for a in available]}")
    
    # Test execution
    if fireball and fireball.can_execute(context):
        print(f"\nExecuting fireball...")
        result = fireball.execute(context, "enemy")
        print(f"Result: {result.value}")
        print(f"Mana after cast: {context.get_resource('mana').current}")
        print(f"Fireball cooldown: {fireball.get_cooldown_remaining(context)}")
    
    # Print registry info
    info = registry.get_registry_info()
    print(f"\nRegistry info: {info}")