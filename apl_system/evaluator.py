"""APL Expression Evaluator - Efficient evaluation of APL expressions

Provides optimized evaluation of APL expressions with:
- Caching of frequently accessed values
- Dependency tracking for selective updates
- Short-circuit evaluation for logical operations
- Performance monitoring and optimization hints

The evaluator acts as a layer between AST nodes and the context,
providing caching and optimization to reduce redundant calculations.
"""

from typing import Dict, List, Set, Any, Optional, Tuple
from dataclasses import dataclass, field
from ast_nodes import ExprNode, ActionLine
from context import APLContext
import time


@dataclass
class EvaluationStats:
    """Statistics for expression evaluation performance"""
    total_evaluations: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    total_time: float = 0.0
    
    @property
    def cache_hit_rate(self) -> float:
        """Cache hit rate as percentage"""
        if self.total_evaluations == 0:
            return 0.0
        return (self.cache_hits / self.total_evaluations) * 100.0
    
    @property
    def avg_time_per_eval(self) -> float:
        """Average time per evaluation in milliseconds"""
        if self.total_evaluations == 0:
            return 0.0
        return (self.total_time / self.total_evaluations) * 1000.0


@dataclass
class CacheEntry:
    """Cache entry for expression values"""
    value: float
    timestamp: float
    dependencies: Set[str] = field(default_factory=set)
    hit_count: int = 0
    
    def is_valid(self, current_time: float, ttl: float = 0.1) -> bool:
        """Check if cache entry is still valid (default 100ms TTL)"""
        return (current_time - self.timestamp) <= ttl


class ExpressionEvaluator:
    """Optimized evaluator for APL expressions"""
    
    def __init__(self, context: APLContext, enable_caching: bool = True):
        self.context = context
        self.enable_caching = enable_caching
        
        # Expression cache
        self.cache: Dict[str, CacheEntry] = {}
        self.cache_ttl = 0.1  # 100ms default TTL
        
        # Dependency tracking
        self.dependency_map: Dict[str, Set[str]] = {}  # identifier -> expressions that depend on it
        self.expression_deps: Dict[str, Set[str]] = {}  # expression -> identifiers it depends on
        
        # Performance statistics
        self.stats = EvaluationStats()
        
        # Optimization settings
        self.max_cache_size = 1000
        self.enable_dependency_tracking = True
        self.enable_short_circuit = True
    
    def evaluate(self, expr: ExprNode, cache_key: Optional[str] = None) -> float:
        """Evaluate expression with caching and optimization"""
        start_time = time.time()
        
        try:
            # Generate cache key if not provided
            if cache_key is None:
                cache_key = self._generate_cache_key(expr)
            
            # Check cache first
            if self.enable_caching and cache_key in self.cache:
                entry = self.cache[cache_key]
                if entry.is_valid(self.context.get_current_time(), self.cache_ttl):
                    entry.hit_count += 1
                    self.stats.cache_hits += 1
                    self.stats.total_evaluations += 1
                    return entry.value
                else:
                    # Cache entry expired
                    del self.cache[cache_key]
            
            # Evaluate expression
            value = expr.evaluate(self.context)
            
            # Cache the result
            if self.enable_caching:
                self._cache_result(cache_key, value, expr)
            
            self.stats.cache_misses += 1
            self.stats.total_evaluations += 1
            
            return value
        
        finally:
            self.stats.total_time += time.time() - start_time
    
    def evaluate_action_conditions(self, action: ActionLine) -> Tuple[bool, Dict[str, float]]:
        """Evaluate all conditions for an action line"""
        results = {}
        
        # Evaluate if condition
        if action.if_expr:
            if_result = self.evaluate(action.if_expr, f"action_{action.action_name}_if")
            results['if'] = if_result
            if if_result == 0.0:
                return False, results
        
        # Evaluate other conditions
        if action.target_if_expr:
            results['target_if'] = self.evaluate(action.target_if_expr, f"action_{action.action_name}_target_if")
        
        if action.wait_on_ready_expr:
            results['wait_on_ready'] = self.evaluate(action.wait_on_ready_expr, f"action_{action.action_name}_wait_on_ready")
        
        if action.line_cd_expr:
            results['line_cd'] = self.evaluate(action.line_cd_expr, f"action_{action.action_name}_line_cd")
        
        return True, results
    
    def invalidate_dependencies(self, changed_identifiers: Set[str]):
        """Invalidate cached expressions that depend on changed identifiers"""
        if not self.enable_dependency_tracking:
            return
        
        to_invalidate = set()
        
        for identifier in changed_identifiers:
            if identifier in self.dependency_map:
                to_invalidate.update(self.dependency_map[identifier])
        
        for cache_key in to_invalidate:
            if cache_key in self.cache:
                del self.cache[cache_key]
    
    def clear_cache(self):
        """Clear all cached values"""
        self.cache.clear()
        self.dependency_map.clear()
        self.expression_deps.clear()
    
    def get_cache_info(self) -> Dict[str, Any]:
        """Get cache statistics and information"""
        return {
            'cache_size': len(self.cache),
            'max_cache_size': self.max_cache_size,
            'hit_rate': self.stats.cache_hit_rate,
            'total_evaluations': self.stats.total_evaluations,
            'avg_time_ms': self.stats.avg_time_per_eval,
            'dependency_count': len(self.dependency_map)
        }
    
    def optimize_cache(self):
        """Optimize cache by removing least used entries"""
        if len(self.cache) <= self.max_cache_size:
            return
        
        # Sort by hit count (ascending) and remove least used
        sorted_entries = sorted(self.cache.items(), key=lambda x: x[1].hit_count)
        to_remove = len(self.cache) - self.max_cache_size
        
        for i in range(to_remove):
            cache_key = sorted_entries[i][0]
            self._remove_cache_entry(cache_key)
    
    def set_cache_ttl(self, ttl: float):
        """Set cache time-to-live in seconds"""
        self.cache_ttl = ttl
    
    def enable_optimization(self, feature: str, enabled: bool = True):
        """Enable/disable optimization features"""
        if feature == "caching":
            self.enable_caching = enabled
        elif feature == "dependency_tracking":
            self.enable_dependency_tracking = enabled
        elif feature == "short_circuit":
            self.enable_short_circuit = enabled
        else:
            raise ValueError(f"Unknown optimization feature: {feature}")
    
    def _generate_cache_key(self, expr: ExprNode) -> str:
        """Generate a cache key for an expression"""
        # Use string representation as cache key
        # In a production system, you might want a more sophisticated approach
        return f"expr_{hash(str(expr))}"
    
    def _cache_result(self, cache_key: str, value: float, expr: ExprNode):
        """Cache evaluation result with dependency tracking"""
        current_time = self.context.get_current_time()
        
        # Get dependencies
        dependencies = set(expr.get_dependencies()) if hasattr(expr, 'get_dependencies') else set()
        
        # Create cache entry
        entry = CacheEntry(
            value=value,
            timestamp=current_time,
            dependencies=dependencies
        )
        
        self.cache[cache_key] = entry
        
        # Update dependency tracking
        if self.enable_dependency_tracking:
            self.expression_deps[cache_key] = dependencies
            
            for dep in dependencies:
                if dep not in self.dependency_map:
                    self.dependency_map[dep] = set()
                self.dependency_map[dep].add(cache_key)
        
        # Optimize cache if needed
        if len(self.cache) > self.max_cache_size:
            self.optimize_cache()
    
    def _remove_cache_entry(self, cache_key: str):
        """Remove cache entry and update dependency tracking"""
        if cache_key not in self.cache:
            return
        
        # Remove from dependency tracking
        if cache_key in self.expression_deps:
            dependencies = self.expression_deps[cache_key]
            for dep in dependencies:
                if dep in self.dependency_map:
                    self.dependency_map[dep].discard(cache_key)
                    if not self.dependency_map[dep]:
                        del self.dependency_map[dep]
            del self.expression_deps[cache_key]
        
        # Remove from cache
        del self.cache[cache_key]


class BatchEvaluator:
    """Batch evaluator for multiple expressions"""
    
    def __init__(self, context: APLContext):
        self.context = context
        self.evaluator = ExpressionEvaluator(context)
    
    def evaluate_batch(self, expressions: List[Tuple[str, ExprNode]]) -> Dict[str, float]:
        """Evaluate multiple expressions in batch"""
        results = {}
        
        for name, expr in expressions:
            try:
                results[name] = self.evaluator.evaluate(expr, f"batch_{name}")
            except Exception as e:
                print(f"Warning: Failed to evaluate {name}: {e}")
                results[name] = 0.0
        
        return results
    
    def evaluate_action_list(self, actions: List[ActionLine]) -> List[Tuple[ActionLine, bool, Dict[str, float]]]:
        """Evaluate conditions for a list of actions"""
        results = []
        
        for action in actions:
            try:
                ready, condition_results = self.evaluator.evaluate_action_conditions(action)
                results.append((action, ready, condition_results))
            except Exception as e:
                print(f"Warning: Failed to evaluate action {action.action_name}: {e}")
                results.append((action, False, {}))
        
        return results


class ProfiledEvaluator(ExpressionEvaluator):
    """Expression evaluator with detailed profiling"""
    
    def __init__(self, context: APLContext):
        super().__init__(context)
        self.profile_data: Dict[str, List[float]] = {}
        self.enable_profiling = True
    
    def evaluate(self, expr: ExprNode, cache_key: Optional[str] = None) -> float:
        """Evaluate with profiling"""
        if not self.enable_profiling:
            return super().evaluate(expr, cache_key)
        
        start_time = time.perf_counter()
        result = super().evaluate(expr, cache_key)
        end_time = time.perf_counter()
        
        # Record timing
        if cache_key:
            if cache_key not in self.profile_data:
                self.profile_data[cache_key] = []
            self.profile_data[cache_key].append(end_time - start_time)
        
        return result
    
    def get_profile_report(self) -> Dict[str, Dict[str, float]]:
        """Get detailed profiling report"""
        report = {}
        
        for cache_key, times in self.profile_data.items():
            if times:
                report[cache_key] = {
                    'count': len(times),
                    'total_time': sum(times),
                    'avg_time': sum(times) / len(times),
                    'min_time': min(times),
                    'max_time': max(times)
                }
        
        return report
    
    def clear_profile_data(self):
        """Clear profiling data"""
        self.profile_data.clear()


if __name__ == "__main__":
    # Test the evaluator
    from .context import GameContext
    from .parser import APLParser
    
    # Set up test context
    context = GameContext()
    context.set_resource("mana", 75, 100)
    context.add_buff("arcane_power", 10.0)
    context.set_cooldown("arcane_shot", 0.0)
    
    # Create evaluator
    evaluator = ExpressionEvaluator(context)
    
    # Parse and evaluate some expressions
    parser = APLParser()
    
    test_expressions = [
        "mana.pct > 50",
        "buff.arcane_power.up & mana.pct > 30",
        "cooldown.arcane_shot.ready",
        "floor(mana.pct / 10) * 2"
    ]
    
    print("Testing expression evaluation:")
    for expr_text in test_expressions:
        try:
            expr = parser.parse_expression(expr_text)
            
            # Evaluate multiple times to test caching
            for i in range(3):
                result = evaluator.evaluate(expr)
                print(f"  '{expr_text}' = {result}")
        except Exception as e:
            print(f"  '{expr_text}' -> ERROR: {e}")
    
    # Print cache statistics
    cache_info = evaluator.get_cache_info()
    print(f"\nCache statistics:")
    for key, value in cache_info.items():
        print(f"  {key}: {value}")
    
    # Test batch evaluation
    print("\nTesting batch evaluation:")
    batch_evaluator = BatchEvaluator(context)
    
    expressions = [
        ("mana_check", parser.parse_expression("mana.pct > 50")),
        ("buff_check", parser.parse_expression("buff.arcane_power.up")),
        ("cd_check", parser.parse_expression("cooldown.arcane_shot.ready"))
    ]
    
    batch_results = batch_evaluator.evaluate_batch(expressions)
    for name, result in batch_results.items():
        print(f"  {name}: {result}")