"""APL Execution Engine - Core APL priority-based decision making

Implements the main APL execution logic:
- Priority-based action selection
- Condition evaluation and filtering
- Action execution with error handling
- Performance monitoring and optimization
- Debugging and tracing capabilities

The executor processes APL action lists and determines the highest priority
action that can be executed based on current game state.
"""

from typing import Dict, List, Optional, Tuple, Any, Set
from dataclasses import dataclass, field
from enum import Enum
import time
import traceback

from ast_nodes import ActionList, ActionLine
from context import APLContext
from evaluator import ExpressionEvaluator, BatchEvaluator
from action_registry import ActionRegistry, RegisteredAction, ActionResult


class ExecutionMode(Enum):
    """Execution modes for the APL engine"""
    NORMAL = "normal"          # Normal execution
    DEBUG = "debug"            # Debug mode with detailed logging
    SIMULATION = "simulation"  # Simulation mode (no actual actions)
    TRACE = "trace"            # Trace mode with full execution history


class ExecutionState(Enum):
    """Current state of the executor"""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"
    STOPPED = "stopped"


@dataclass
class ExecutionResult:
    """Result of APL execution"""
    action_name: Optional[str] = None
    action_result: Optional[ActionResult] = None
    execution_time: float = 0.0
    conditions_evaluated: int = 0
    actions_considered: int = 0
    error: Optional[str] = None
    debug_info: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ActionEvaluation:
    """Evaluation result for a single action"""
    action_line: ActionLine
    registered_action: Optional[RegisteredAction]
    can_execute: bool
    condition_results: Dict[str, float]
    evaluation_time: float
    error: Optional[str] = None


@dataclass
class ExecutionTrace:
    """Trace information for debugging"""
    timestamp: float
    action_evaluations: List[ActionEvaluation]
    selected_action: Optional[str]
    execution_result: ExecutionResult
    context_snapshot: Dict[str, Any] = field(default_factory=dict)


class APLExecutor:
    """Main APL execution engine"""
    
    def __init__(self, 
                 context: APLContext,
                 action_registry: ActionRegistry,
                 mode: ExecutionMode = ExecutionMode.NORMAL):
        self.context = context
        self.action_registry = action_registry
        self.mode = mode
        
        # Core components
        self.evaluator = ExpressionEvaluator(context)
        self.batch_evaluator = BatchEvaluator(context)
        
        # Execution state
        self.state = ExecutionState.IDLE
        self.current_apl: Optional[ActionList] = None
        
        # Performance tracking
        self.total_executions = 0
        self.total_execution_time = 0.0
        self.action_stats: Dict[str, Dict[str, Any]] = {}
        
        # Debugging and tracing
        self.trace_history: List[ExecutionTrace] = []
        self.max_trace_history = 100
        self.debug_callbacks: List[callable] = []
        
        # Configuration
        self.max_evaluations_per_cycle = 50
        self.enable_performance_monitoring = True
        self.enable_condition_caching = True
        self.stop_on_first_executable = True
    
    def load_apl(self, apl: ActionList) -> bool:
        """Load an APL for execution"""
        try:
            self.current_apl = apl
            self.state = ExecutionState.IDLE
            
            # Validate all actions exist in registry
            missing_actions = []
            for action_line in apl.actions:
                if not self.action_registry.get_action(action_line.action_name):
                    missing_actions.append(action_line.action_name)
            
            if missing_actions:
                error_msg = f"Missing actions in registry: {missing_actions}"
                if self.mode == ExecutionMode.DEBUG:
                    print(f"Warning: {error_msg}")
                return False
            
            return True
        
        except Exception as e:
            self._handle_error(f"Failed to load APL: {e}")
            return False
    
    def execute_next_action(self) -> ExecutionResult:
        """Execute the next highest priority action"""
        start_time = time.perf_counter()
        
        try:
            self.state = ExecutionState.RUNNING
            
            if not self.current_apl:
                return ExecutionResult(error="No APL loaded")
            
            # Evaluate all actions and find the best one
            evaluations = self._evaluate_all_actions()
            
            # Find the first executable action (highest priority)
            selected_action = None
            for evaluation in evaluations:
                if evaluation.can_execute and evaluation.registered_action:
                    selected_action = evaluation
                    break
            
            # Execute the selected action
            result = ExecutionResult(
                actions_considered=len(evaluations),
                conditions_evaluated=sum(len(e.condition_results) for e in evaluations)
            )
            
            if selected_action:
                result.action_name = selected_action.action_line.action_name
                
                if self.mode != ExecutionMode.SIMULATION:
                    # Actually execute the action
                    action_result = selected_action.registered_action.execute(
                        self.context,
                        self._get_target_for_action(selected_action.action_line)
                    )
                    result.action_result = action_result
                    
                    # Update statistics
                    self._update_action_stats(selected_action.action_line.action_name, action_result)
                else:
                    result.action_result = ActionResult.SUCCESS
                    if self.mode == ExecutionMode.DEBUG:
                        print(f"[SIMULATION] Would execute: {result.action_name}")
            
            # Record trace if enabled
            if self.mode == ExecutionMode.TRACE:
                self._record_trace(evaluations, selected_action, result)
            
            self.total_executions += 1
            result.execution_time = time.perf_counter() - start_time
            self.total_execution_time += result.execution_time
            
            self.state = ExecutionState.IDLE
            return result
        
        except Exception as e:
            error_msg = f"Execution error: {e}"
            if self.mode == ExecutionMode.DEBUG:
                error_msg += f"\n{traceback.format_exc()}"
            
            self._handle_error(error_msg)
            return ExecutionResult(
                error=error_msg,
                execution_time=time.perf_counter() - start_time
            )
    
    def execute_continuous(self, duration: float = 60.0, interval: float = 0.1) -> List[ExecutionResult]:
        """Execute APL continuously for a specified duration"""
        results = []
        start_time = time.time()
        
        while time.time() - start_time < duration:
            result = self.execute_next_action()
            results.append(result)
            
            # Break on error
            if result.error:
                break
            
            # Wait for next execution
            time.sleep(interval)
        
        return results
    
    def _evaluate_all_actions(self) -> List[ActionEvaluation]:
        """Evaluate all actions in the current APL"""
        evaluations = []
        
        for action_line in self.current_apl.actions:
            evaluation = self._evaluate_action(action_line)
            evaluations.append(evaluation)
            
            # Stop early if we found an executable action and optimization is enabled
            if (self.stop_on_first_executable and 
                evaluation.can_execute and 
                evaluation.registered_action):
                break
        
        return evaluations
    
    def _evaluate_action(self, action_line: ActionLine) -> ActionEvaluation:
        """Evaluate a single action line"""
        start_time = time.perf_counter()
        
        try:
            # Get registered action
            registered_action = self.action_registry.get_action(action_line.action_name)
            
            if not registered_action:
                return ActionEvaluation(
                    action_line=action_line,
                    registered_action=None,
                    can_execute=False,
                    condition_results={},
                    evaluation_time=time.perf_counter() - start_time,
                    error=f"Action '{action_line.action_name}' not found in registry"
                )
            
            # Evaluate conditions
            can_execute, condition_results = self.evaluator.evaluate_action_conditions(action_line)
            
            # Check if the registered action can execute
            if can_execute:
                target = self._get_target_for_action(action_line)
                can_execute = registered_action.can_execute(self.context, target)
            
            return ActionEvaluation(
                action_line=action_line,
                registered_action=registered_action,
                can_execute=can_execute,
                condition_results=condition_results,
                evaluation_time=time.perf_counter() - start_time
            )
        
        except Exception as e:
            return ActionEvaluation(
                action_line=action_line,
                registered_action=None,
                can_execute=False,
                condition_results={},
                evaluation_time=time.perf_counter() - start_time,
                error=str(e)
            )
    
    def _get_target_for_action(self, action_line: ActionLine) -> Any:
        """Get the target for an action"""
        # This would typically involve target selection logic
        # For now, return the current target from context
        if hasattr(self.context, 'get_current_target'):
            return self.context.get_current_target()
        return None
    
    def _update_action_stats(self, action_name: str, result: ActionResult):
        """Update statistics for an action"""
        if not self.enable_performance_monitoring:
            return
        
        if action_name not in self.action_stats:
            self.action_stats[action_name] = {
                'executions': 0,
                'successes': 0,
                'failures': 0,
                'last_executed': 0.0
            }
        
        stats = self.action_stats[action_name]
        stats['executions'] += 1
        stats['last_executed'] = time.time()
        
        if result == ActionResult.SUCCESS:
            stats['successes'] += 1
        else:
            stats['failures'] += 1
    
    def _record_trace(self, evaluations: List[ActionEvaluation], 
                     selected_action: Optional[ActionEvaluation],
                     result: ExecutionResult):
        """Record execution trace for debugging"""
        trace = ExecutionTrace(
            timestamp=time.time(),
            action_evaluations=evaluations,
            selected_action=selected_action.action_line.action_name if selected_action else None,
            execution_result=result,
            context_snapshot=self._get_context_snapshot()
        )
        
        self.trace_history.append(trace)
        
        # Limit trace history size
        if len(self.trace_history) > self.max_trace_history:
            self.trace_history.pop(0)
    
    def _get_context_snapshot(self) -> Dict[str, Any]:
        """Get a snapshot of the current context state"""
        snapshot = {}
        
        # Add basic context information
        if hasattr(self.context, 'get_current_time'):
            snapshot['time'] = self.context.get_current_time()
        
        # Add resource information
        if hasattr(self.context, 'get_all_resources'):
            snapshot['resources'] = self.context.get_all_resources()
        
        return snapshot
    
    def _handle_error(self, error_msg: str):
        """Handle execution errors"""
        self.state = ExecutionState.ERROR
        
        if self.mode == ExecutionMode.DEBUG:
            print(f"APL Executor Error: {error_msg}")
        
        # Call debug callbacks
        for callback in self.debug_callbacks:
            try:
                callback(error_msg)
            except Exception:
                pass  # Don't let callback errors crash the executor
    
    def get_execution_stats(self) -> Dict[str, Any]:
        """Get execution statistics"""
        avg_time = 0.0
        if self.total_executions > 0:
            avg_time = self.total_execution_time / self.total_executions
        
        return {
            'total_executions': self.total_executions,
            'total_time': self.total_execution_time,
            'average_time': avg_time,
            'current_state': self.state.value,
            'action_stats': self.action_stats.copy(),
            'trace_entries': len(self.trace_history)
        }
    
    def get_debug_info(self) -> Dict[str, Any]:
        """Get detailed debug information"""
        return {
            'mode': self.mode.value,
            'state': self.state.value,
            'loaded_apl': self.current_apl is not None,
            'evaluator_cache_info': self.evaluator.get_cache_info(),
            'recent_traces': self.trace_history[-5:] if self.trace_history else []
        }
    
    def add_debug_callback(self, callback: callable):
        """Add a debug callback function"""
        self.debug_callbacks.append(callback)
    
    def clear_debug_callbacks(self):
        """Clear all debug callbacks"""
        self.debug_callbacks.clear()
    
    def reset_stats(self):
        """Reset all statistics"""
        self.total_executions = 0
        self.total_execution_time = 0.0
        self.action_stats.clear()
        self.trace_history.clear()
    
    def set_mode(self, mode: ExecutionMode):
        """Set execution mode"""
        self.mode = mode
        
        if mode == ExecutionMode.TRACE and not self.trace_history:
            print("Trace mode enabled - execution history will be recorded")
    
    def pause(self):
        """Pause execution"""
        if self.state == ExecutionState.RUNNING:
            self.state = ExecutionState.PAUSED
    
    def resume(self):
        """Resume execution"""
        if self.state == ExecutionState.PAUSED:
            self.state = ExecutionState.IDLE
    
    def stop(self):
        """Stop execution"""
        self.state = ExecutionState.STOPPED


class APLSimulator:
    """APL simulator for testing and optimization"""
    
    def __init__(self, context: APLContext, action_registry: ActionRegistry):
        self.context = context
        self.action_registry = action_registry
        self.executor = APLExecutor(context, action_registry, ExecutionMode.SIMULATION)
    
    def simulate_rotation(self, apl: ActionList, duration: float = 60.0) -> Dict[str, Any]:
        """Simulate an APL rotation for analysis"""
        self.executor.load_apl(apl)
        
        results = []
        start_time = time.time()
        simulation_time = 0.0
        
        while simulation_time < duration:
            result = self.executor.execute_next_action()
            results.append(result)
            
            if result.error:
                break
            
            # Advance simulation time
            if result.action_name:
                # Simulate action execution time (GCD, cast time, etc.)
                action = self.action_registry.get_action(result.action_name)
                if action:
                    time_advance = max(action.metadata.gcd, action.metadata.cast_time)
                    simulation_time += time_advance
                    
                    # Update context time
                    if hasattr(self.context, 'advance_time'):
                        self.context.advance_time(time_advance)
            else:
                # No action available, advance by small amount
                simulation_time += 0.1
                if hasattr(self.context, 'advance_time'):
                    self.context.advance_time(0.1)
        
        # Analyze results
        return self._analyze_simulation_results(results, simulation_time)
    
    def _analyze_simulation_results(self, results: List[ExecutionResult], duration: float) -> Dict[str, Any]:
        """Analyze simulation results"""
        action_counts = {}
        total_actions = 0
        errors = 0
        
        for result in results:
            if result.error:
                errors += 1
            elif result.action_name:
                action_counts[result.action_name] = action_counts.get(result.action_name, 0) + 1
                total_actions += 1
        
        return {
            'duration': duration,
            'total_actions': total_actions,
            'actions_per_minute': (total_actions / duration) * 60 if duration > 0 else 0,
            'action_breakdown': action_counts,
            'error_count': errors,
            'execution_results': results
        }


if __name__ == "__main__":
    # Test the executor
    from .context import GameContext
    from .parser import APLParser
    from .action_registry import ActionRegistry, ActionCategory, ActionResult
    
    # Set up test environment
    context = GameContext()
    context.set_resource("mana", 100, 100)
    context.set_resource("health", 80, 100)
    context.set_cooldown("fireball", 0.0)
    context.set_cooldown("frostbolt", 0.0)
    
    registry = ActionRegistry()
    
    # Register test actions
    def fireball_can_execute(ctx, target):
        return ctx.get_resource("mana").current >= 30
    
    def fireball_execute(ctx, target):
        print("Casting Fireball")
        ctx.consume_resource("mana", 30)
        return ActionResult.SUCCESS
    
    registry.register_simple(
        "fireball",
        fireball_can_execute,
        fireball_execute,
        category=ActionCategory.SPELL,
        resource_cost={"mana": 30}
    )
    
    def frostbolt_can_execute(ctx, target):
        return ctx.get_resource("mana").current >= 25
    
    def frostbolt_execute(ctx, target):
        print("Casting Frostbolt")
        ctx.consume_resource("mana", 25)
        return ActionResult.SUCCESS
    
    registry.register_simple(
        "frostbolt",
        frostbolt_can_execute,
        frostbolt_execute,
        category=ActionCategory.SPELL,
        resource_cost={"mana": 25}
    )
    
    # Parse test APL
    parser = APLParser()
    apl_text = """
    actions.precombat=flask
    actions=fireball,if=mana.pct>30
    actions+=/frostbolt,if=mana.pct>25
    """
    
    try:
        apl = parser.parse(apl_text)
        
        # Create executor
        executor = APLExecutor(context, registry, ExecutionMode.DEBUG)
        executor.load_apl(apl)
        
        print("Testing APL Executor:")
        
        # Execute a few actions
        for i in range(5):
            print(f"\nExecution {i+1}:")
            result = executor.execute_next_action()
            
            if result.error:
                print(f"  Error: {result.error}")
                break
            elif result.action_name:
                print(f"  Executed: {result.action_name}")
                print(f"  Result: {result.action_result.value if result.action_result else 'None'}")
                print(f"  Time: {result.execution_time*1000:.2f}ms")
                print(f"  Mana: {context.get_resource('mana').current}")
            else:
                print("  No action available")
            
            if context.get_resource("mana").current < 25:
                print("  Out of mana!")
                break
        
        # Print statistics
        stats = executor.get_execution_stats()
        print(f"\nExecution Statistics:")
        for key, value in stats.items():
            if key != 'action_stats':
                print(f"  {key}: {value}")
        
        # Test simulator
        print("\nTesting APL Simulator:")
        simulator = APLSimulator(context, registry)
        
        # Reset context
        context.set_resource("mana", 100, 100)
        
        sim_results = simulator.simulate_rotation(apl, 10.0)  # 10 second simulation
        print(f"Simulation Results:")
        for key, value in sim_results.items():
            if key != 'execution_results':
                print(f"  {key}: {value}")
    
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()