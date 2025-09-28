下面是**面向工程移植（将 SimulationCraft 的 APL 迁移到另一种语言）**的完整技术文档。文档先给出**整体结构与要点摘要**，然后逐章展开实现细节（词法/语法/AST/求值/运行时/调度/集成/测试等）。我把每一步都写得尽量详尽——包含数据结构、算法、API 设计建议、测试要点与常见陷阱，便于你直接在目标语言（例如 Java / Go / Rust / Python / C#）中实现。
我在关键设计/语义的地方标注了 SimulationCraft 官方文档或源码注释的引用，便于对照与验证。([GitHub][1])

---

# 一、文档总体组织（导航 / 快览）

1. 目标与范围（为什么要移植、必须保持的语义）
2. 高层架构（模块划分、运行时/数据流图）
3. 语法规范（APL 文件语法、Action 条目语法）
4. 表达式语言（完整 BNF / 运算符优先级 / 内置变量与函数）
5. 词法器（Tokenizer）与解析器（Parser）设计（递归下降实现或生成器）
6. AST 与中间表示（节点类型、属性、序列化/缓存）
7. 表达式求值器（Evaluator）：上下文绑定、短路、类型规则、数值/布尔语义
8. ActionList 执行引擎（ready 判定、条件判定、执行流程）
9. 调度 / 时间推进（轮询 vs 事件驱动、等待与 pool_resource 等）
10. 与游戏状态的绑定（资源、冷却、buff/dot、target、pet、trinket 映射）
11. 细节功能与 Edge Cases（sequence、line_cd、sync、target_if、wait_on_ready、spell_queue）
12. 错误/日志/调试（可读的报错、APL 行号映射、诊断输出）
13. 性能优化（表达式编译、缓存、短路、增量更新）
14. 测试计划（单元/综合/回归/基准）与示例用例
15. 迁移/交付清单（端到端迁移步骤与验收条件）
16. 附录：常用变量 / 内置属性速查表与示例

后续每一条都将细化到足够工程化的细节（数据结构、伪代码、API 设计、测试样例、注意事项）。

---

# 二、目标与不变式（What to preserve）

在移植时**必须保持或显式决定**的语义：

* APL 是“优先级列表（priority list）”，执行时按顺序扫描并选择第一个**可用且条件满足**的动作（action）。这是 APL 的核心运行语义（priority scanning）。([GitHub][1])
* 条件表达式是一种数值表达式：非零视为 true，零视为 false（SimC 的布尔语义基于数值）。表达式支持丰富的内置变量（buff、cooldown、dot、time、active_enemies 等）。([GitHub][2])
* 每条 APL 行可携带若干“选项”（if、interrupt_if、target_if、chain、wait_on_ready、line_cd 等），这些都需在解析后保存在 action-line 对象上，供运行时使用。action_t 的实现表明 APL 行会保留解析后的 expr（if_expr、interrupt_if_expr 等）。([simulationcraft.org][3])

保持以上不变式可以确保行为与 SimC 原语义一致。

---

# 三、高层架构（模块划分 + 数据流）

建议模块（每个模块都应有单元测试）：

1. **Lexer / Tokenizer**：将 APL 文本切成 token（标识符、数字、字符串、操作符、逗号、`/`、`=` 等）。
2. **Parser**：解析 action-list、每条 action-line（包括解析 options）及条件表达式，生成 AST / 中间表示。
3. **AST / IR**：表达式树（expr_t），action_line 对象（包含指向已注册 action 的引用与 expr 指针）。
4. **Expression Evaluator（Evaluator）**：在给定 `EvalContext`（运行时状态访问器）的情况下计算 expr_t → double（0.0 表示 false）。
5. **Action Registry / Action Factory**：负责把 `/spell_name` 映射到具体的 `Action` 对象（包含 ready(), execute() 等）。（在 SimC，这里是类/模块如 sc_hunter.cpp 中的 create_action）
6. **ActionList Executor**：扫描 action list、对每条 line 调用 ready() & if_expr.eval()，触发 execute()。实现优先级顺序、子列表调用、sequence、wait 等。
7. **Scheduler / Simulation Clock**：负责时间推进、事件排队、在需要时唤醒 actor（可实现 poll 或 event 模式）。([GitHub][4])
8. **State & Resolver 层**：把游戏/角色状态暴露给 Evaluator（例如 get_buff(name).remains、get_cooldown(spell).remains、focus、active_enemies 等）。Evaluator 只调用这些 API。([GitHub][2])

数据流：APL 文本 → Lexer → Parser → IR(action_list + expr trees) → （加载时）绑定 action objects → 运行时 Evaluator 使用 Resolver/State 查询变量 → ActionList Executor 选择并执行 action。

---

# 四、语法规范（APL 文件 & 行级语法）—— 完整 BNF（建议）

下面给出一个可直接用于实现解析器的简明 BNF（基于 SimC 语法约定，并加入了必要扩展）。注：`/` 在 APL 用于前缀指定动作（如 `/spell_name`）。字符串/名字采用字母、下划线、数字。

```
<file>           ::= (<action_list_def>)*

<action_list_def>::= "actions" <assign_op> <action_line> (NEWLINE <action_line> )*
<assign_op>      ::= "=" | "+="

<action_line>    ::= "/" <action_name> ("," <option> )*

<option>         ::= <key> "=" <value>
                  | "if" "=" <expr>
                  | "interrupt_if" "=" <expr>
                  | "target_if" "=" <target_if_spec>
                  | "wait_on_ready" "=" <expr>
                  | "line_cd" "=" <expr>
                  | ...  /* other options */

<target_if_spec> ::= <mode> ":" <property>   /* e.g., min:remains or refreshable */

<expr>           ::= <logic_or>

<logic_or>       ::= <logic_xor> ( "|" <logic_xor> )*
<logic_xor>      ::= <logic_and> ( "^" <logic_and> )*
<logic_and>      ::= <comparison> ( "&" <comparison> )*

<comparison>     ::= <arith> ( ("=" | "!=" | "<" | "<=" | ">" | ">=" | "~" | "!~") <arith> )*

<arith>          ::= <term> ( ("+" | "-") <term> )*
<term>           ::= <factor> ( ("*" | "%" | "%%") <factor> )*
<factor>         ::= ("+"|"-"|"!") <factor> | <primary>

<primary>        ::= NUMBER | IDENTIFIER | FUNCTION_CALL | "(" <expr> ")"

FUNCTION_CALL    ::= IDENTIFIER "(" ( <expr> ("," <expr> )* )? ")"
IDENTIFIER       ::= IDENT_PART ( "." IDENT_PART )*
IDENT_PART       ::= [a-zA-Z_][a-zA-Z0-9_]*

NUMBER           ::= [0-9]+("." [0-9]+)?   /* float */

```

说明与要点：

* `IDENTIFIER` 支持点号访问（例如 `buff.raging_blow.remains`、`cooldown.skull_banner.remains`、`pet.water_elemental.cooldown.freeze.remains`）。([GitHub][2])
* 运算符：`&`、`|`、`^` 用作逻辑连接；比较符号 `~`/`!~` 用于模式匹配（见 wiki）。([GitHub][2])
* `FUNCTION_CALL` 支持内置函数（floor, ceil 等）与自定义函数。
* `option` 的 key/value 列表要能包含字符串（例如 `name=some_item`），数值或表达式（例如 `sec=buff.some.remains-2`）。([GitHub][1])

---

# 五、词法器（Tokenizer）实现细节

**目标**：把输入切成 token，并保留位置信息（filename, line, column）用于错误提示与行号映射（非常关键）。

必需 token 类型（建议实现）：

* `SLASH` (`/`) — action 开头
* `IDENT` — 由字母/下划线/数字组成（支持下划线替空格的规则）
* `NUMBER` — 浮点数、整数
* `COMMA`, `COLON`, `DOT`, `LPAREN`, `RPAREN`, `EQUAL`, `PLUS`, `MINUS`, `STAR`, `PERCENT`, `PERCENTS` (for `%%`), `LT`, `GT`, `LE`, `GE`, `EQ` (`=`), `NE` (`!=`), `AMP` (`&`), `PIPE` (`|`), `CARET` (`^`), `BANG` (`!`)
* `NEWLINE` — 换行（用于维持行边界），也可通过扫描器提供行号信息
* `STRING`（可选） — 如果你允许 options 的 value 为带引号字符串（例如 item names with spaces），建议支持引号字符串并在 parser 里 normalize（去引号并转换空格为下划线或直接保留）。SimC 在 action names 中用下划线替代空格，但 item names / name= 参数常常需要原样匹配。([GitHub][1])

实现提示：

* 保留注释行（以 `#` 开头）并忽略（或用于注释字段）。
* Tokenizer 应返回 token 对象 `{ type, lexeme, line, column }`。
* 支持 peek / pushback（解析器需要回溯一个 token 的能力）。
* 对非法字符返回明确错误（包含文件与行号）。

---

# 六、Parser（表达式 + 行级解析）设计

推荐使用 **递归下降解析器（Recursive Descent）**：表达式优先级固定且不复杂，递归下降实现直观且易于定制错误消息。若你在目标语言使用现成解析器生成器（ANTLR, peg, parboiled 等），也可直接用语法文件生成。

**解析步骤**：

1. 解析 `actions` 列表（识别 `actions=` / `actions+=`）。
2. 对每行：要求以 `SLASH` 开头，然后解析 `action_name`（IDENT 组成，可能含下划线、数字）。
3. 解析逗号分隔的 `option` 列表：每个 `key=value`。对于 `if=...`、`interrupt_if=...`、`target_if=...`，将 `value` 作为表达式 `expr` 交由表达式解析子模块生成 AST（expr_t）。对于 `name=` 等，value 可能是字符串或 identifier（若需要保留空格的名字，支持字符串引号语法）。
4. 为每个 action_line 返回结构：

```text
ActionLine {
  action_name: string;            // normalized (underscores)
  options: Map<string, OptionValue>;
  if_expr: ExprNode | null;
  interrupt_if_expr: ExprNode | null;
  target_if_expr: ExprNode | null;
  line_cd_expr: ExprNode | null;
  wait_on_ready_expr: ExprNode | null;
  // ... plus positional metadata (file,lineno)
}
```

5. 对 `call_action_list,name=xxx` 或 `sequence,red:blue` 等结构，建立 special ActionLine 类型或内部子-actions 的引用。

**错误处理建议**：

* 报错应包含文件名、行号、列号与上下文（错误 token、周围 1–2 个 token）。
* 若遇到未知 action_name（在绑定阶段才能确认），不要在解析阶段报错，只记录 action_name 字符串；在绑定/校验阶段再提示“未知动作/拼写错误”。

---

# 七、AST / 中间表示（expr_t）与节点类型

设计一套轻量但功能完整的 AST 节点类型（足以表达 SimC 表达式语言）：

```text
abstract class ExprNode { evaluate(ctx): double; /* optional: compile(ctx) */ }

LiteralNode(value: double)
IdentifierNode(parts: string[])   // e.g., ["buff","raging_blow","remains"]
UnaryNode(op: string, child: ExprNode)   // op in {"+","-","!"}
BinaryNode(op: string, left: ExprNode, right: ExprNode)  // op in {"+","-","*","%","%%",">=","<=",">","<","=","!=","&","|","^","~","!~"}
FunctionCallNode(name: string, args: ExprNode[])
```

附加字段（ActionLine）：

* `if_expr: ExprNode | null`（同样适用于 `target_if_expr`、`interrupt_if_expr` 等）。([simulationcraft.org][3])

**注意**：`IdentifierNode` 有两种语义：

* 作为普通变量（例如 `time`, `active_enemies`） → evaluator 会直接从 context 查找返回值。
* 作为“property chain”（例如 `buff.raging_blow.remains`） → evaluator 会把前缀作为“resolver” (buff/debuff/cooldown/pet/etc)，并把后续属性映射成所需属性（up/remains/stack/ticking/...）。SimC 的 wiki 列出了大量可用属性，建议实现一个通用 resolver 层：`resolve(identifier_parts[], ctx)` 并返回 double/number/0.0。如果找不到，返回 0（SimC 的默认很多时候就是 0）。([GitHub][2])

---

# Eight、表达式求值器（Evaluator）—— 精确语义与实现细节

## 8.1 值与布尔语义

* 所有表达式以数值（double）为主，非 0 → true，0 → false。布尔运算仍按数值规则处理（但实现时应保证语义清晰）。([GitHub][2])

## 8.2 运算符优先级（与 Parser 一致）

* 与上文 BNF 一致（`*`/`%` 高于 `+`/`-`，比较高于逻辑运算，括号可覆盖）。

## 8.3 逻辑运算的短路行为（推荐）

* 推荐**实现短路**（`a & b`：若 `a` 为 0，则不求 `b`）。短路可显著提高性能并避免不必要的状态查询（例如 `buff.exist & cooldown.spell.remains < 3` 中若 `buff.exist` 为 0 则无需查询 cooldown）。**注意**：SimC 文档未明确说明是否短路；在移植时，短路是安全且高效的实现选择，但需在测试中验证与原实现的行为兼容性（如果有副作用的属性查询则需谨慎）。([GitHub][2])

## 8.4 标识符 / 属性解析（关键）

Evaluator 不直接包含游戏状态；而是通过 `EvalContext` 抽象接口访问状态。例如：

```text
interface EvalContext {
  double get_global(string name);                       // e.g., time, active_enemies
  BuffSnapshot get_buff(string buffname);               // returns object or null
  CooldownSnapshot get_cooldown(string spellname);
  DotSnapshot get_dot(string dotname);
  PetSnapshot get_pet(string petname);
  ActionSnapshot get_action(string actionname);
  double get_custom(string identifier[]);               // extensibility hook
}
```

* `IdentifierNode.evaluate(ctx)` 的处理逻辑（伪代码）：

```text
if identifier parts[0] in { "buff","debuff" }:
  return ctx.get_buff(parts[1]).property(parts[2]) or 0
else if identifier parts[0] == "cooldown":
  return ctx.get_cooldown(parts[1]).property(parts[2]) or 0
else if identifier parts[0] == "dot":
  return ctx.get_dot(parts[1]).property(parts[2]) or 0
else:
  return ctx.get_global(identifier_join("."))
```

* `property` 支持例如: `up`, `remains`, `duration`, `stack`, `ticking`, `refreshable` 等（详见 wiki 的 Dot / Buff / Cooldown 列表）。([GitHub][2])

## 8.5 内置函数

* 支持 `floor()`, `ceil()`, `min(a,b)`, `max(a,b)`, `abs()` 等并在 AST 中实现 `FunctionCallNode`。如需扩展特性（例如 `active_dot.xxx`），把它们映射到 `EvalContext` 的特殊查询。

## 8.6 错误与未定义标识

* 如果 `Identifier` 对应资源不存在或不可用于当前 context，Evaluator 返回 `0`，并可在 debug 模式中记录一次警告（避免每次都报错淹没日志）。

---

# 九、Action Registry 与绑定（create_action 阶段）

SimC 在类模块（如 sc_hunter.cpp）里有 `create_action()` 的实现，把技能映射到 `action_t` 对象。移植实现时要有**动作注册阶段**与**APL 绑定阶段**两个分离步骤：

1. **注册动作（静态）**：在系统初始化或加载角色模板时，构建 `Action` 实例表（名字→ActionFactory）。每个 `Action` 对象包含：name、base_costs、cooldown 表示（或冷却 resolver）、是否触发 GCD、是否 channeled、可用条件（range 等），执行回调（apply_effect）。SimC 的 action_t 结构非常丰富（参见 Doxygen 文档），移植时请至少保留 `if_expr`、`line_cooldown`、`use_off_gcd`、`use_while_casting` 等选项。([simulationcraft.org][3])

2. **绑定 APL 行 → Action 对象**：Parser 只存字符串名；在绑定阶段解析器/加载器将 action_name 查表并把 `Action` 引用填入 `ActionLine.action_ref`，并把解析好的表达式树赋给 `ActionLine.if_expr` 等字段，构成最终 `ActionLine`。

   * 对于找不到的 action（例如拼写错误），记录错误并继续（可选：在严格模式下中止）。
   * `line_cd`（每行冷却）等选项需要创建 `line_cooldown` 对象（action_t::line_cooldown 在 SimC 中存在）。([simulationcraft.org][3])

---

# 十、ActionList 执行引擎（决策循环）——算法与伪代码

核心循环（简化伪码）：

```text
function run_actor_cycle(actor, now):
  // called when actor is candidate to act (polling or event wake)
  for each action_line in actor.action_list in order:
    action = action_line.action_ref
    // 1. check action general readiness (range, GCD, action specific ready)
    if !action.ready(actor, now):
      continue
    // 2. check options that are not expressions (e.g., target constraints)
    if !action_line.options_satisfied(actor, now):
      continue
    // 3. evaluate condition expression (if present)
    if action_line.if_expr != null:
      val = action_line.if_expr.evaluate(new EvalContext(actor, now))
      if val == 0:
        continue
    // 4. evaluate interrupt_if / early_chain_if if applicable (or store them)
    // 5. select this action: execute
    action.execute(actor, now, action_line)   // consumes resources, starts CD, logs
    // 6. apply line_cd or for_next semantics
    // 7. exit loop (one action per cycle)
    return
  // if none matched: idle / schedule next wake
```

关键细节：

* **ready() 检查**：action.ready 应包含：资源是否足够、冷却是否到、是否在正确阶段（execute-only）、range OK、是否在 GCD 限制内（或 use_off_gcd）、是否 target 可用。SimC 将很多隐式检查放在 ready() 内部，APL 的 `if=` 不需要重复这些隐式判断。建议把这些隐式检查放在 Action 实现层，这样 APL 作者不会重复。([GitHub][1])
* **只执行第一个可用动作**（priority scanning），并在执行后从头重新开始（下一 GCD/下一 schedule）。这是 SimC 的核心语义。([GitHub][1])

---

# 十一、调度与时间推进（Polling vs Event-Driven）

SimC 支持两种调度策略：**Poll（默认）** 和 **Event-based**。在 Poll 模式下，ActionList 会按固定间隔（如 100ms）轮询 actor 是否有动作可做；Event-based 则在特定状态变化（冷却到期、buff 变动、资源达到阈值）触发唤醒。([GitHub][4])

**实现建议**：

* 开发初期实现 Poll 模式（简单且更易还原 SimC 默认行为），间隔可配置（默认 0.1s）。
* 为性能优化和大型场景实现 Event-driven：维护一个“唤醒事件队列”，在解析表达式时收集依赖（见下），当某依赖变化时唤醒 actor。

  * 例如，若 `if` 中引用 `cooldown.trueshot.remains`，当该 cooldown 减少到某阈值时，scheduler 可发出唤醒事件。
  * 但要注意：表达式的任意组合与函数会使依赖静态收集变复杂；可先实现保守的事件依赖（buff/cooldown/resource/dot/time）。

**wait / wait_until_ready / pool_resource**（SimC 特有）：

* `wait`：暂停 processing actions list 指定秒数（auto-attacks 仍进行）。`sec` 可以是表达式。([GitHub][1])
* `wait_until_ready`：最多等 `sec`，不会响应某些事件（仅用于性能优化）。
* `pool_resource`：用于“攒资源”行为，强制暂停处理直到资源恢复到阈值（建议实现为短时间周期轮询或事件触发）。([GitHub][1])

---

# 十二、关键功能详解（sequence、call_action_list、target_if、line_cd、sync）

这些是 SimC APL 的常见高级特性，需逐一实现：

1. **sequence**：一组子动作按顺序尝试（内部有自己的执行语义：每次只执行 sequence 中满足条件且可用的第一个动作；执行完所有子动作后 sequence 不再循环，除非显式 reset）。SimC 的文档描述了序列执行的行为（如果序列中的动作都不是 ready 会跳过）。实现需要在 `ActionLine` 支持 `sequence` 子列表与状态（index、completed）字段。([GitHub][1])

2. **call_action_list / run_action_list**：支持子列表调用。实现时把子列表解析为 `ActionList` 并在执行时递归/嵌套扫描（注意无限递归保护）。Disambiguate `call` vs `run`（SimC 的讨论区提到有区别；建议在实现时提供两种调用语义并写测试以确定行为是否相同或有细微差异）。([GitHub][5])

3. **target_if**：在多目标情形选择目标（`min:remains` / `refreshable` 等）。实现应允许 `target_if_expr` 返回一个选择模式，并在执行前通过 `EvalContext` 的目标查询 API 返回最佳 target id。

4. **line_cd**：每个 APL 行可以设置独立的“line cooldown”——执行该行后直到 line_cd 过期才允许这行再次触发。`ActionLine` 保存 `line_cooldown`（在 SimC action_t 中已有对应字段）。([simulationcraft.org][3])

5. **sync (sync=spell_name)**：把当前 action 与另一个 action 同步，直到另一个 action 冷却准备好才执行（在绑定阶段将 `sync_action` 字段指向目标 action）。实现时，在 ready 检查中增加 `if (sync_action && !sync_action.ready()) skip`。

---

# 十三、集成：State ↔ EvalContext 映射（必须详尽）

Evaluator 需要访问大量内置字段。下面给出建议的 `EvalContext` 接口及每个内置变量应如何映射（便于在目标语言实现）——并把 SimC wiki 的关键字段摘录映射到接口方法（此表可作为移植的“契约”）。

## EvalContext API（建议）

```text
interface EvalContext {
  // General
  double time();                        // elapsed fight time in s
  int active_enemies();

  // Resources
  double resource(name);                // e.g., focus, mana, rage
  double resource_max(name);
  double resource_deficit(name);

  // Cooldowns
  CooldownSnapshot cooldown(spell_name);

  // Buff / Debuff
  AuraSnapshot buff(aura_name);         // Searches player's buffs only
  AuraSnapshot debuff(aura_name);       // Searches target debuffs first then player

  // Dots
  DotSnapshot dot(dot_name);

  // Action snapshots
  ActionSnapshot action(spell_name);

  // Pets
  PetSnapshot pet(pet_name);

  // Triggers (raid events)
  RaidEventSnapshot raid_event(type_or_name);

  // Target properties
  TargetSnapshot target(index_or_id?);

  // Helpers and extensibility
  double get_custom_identifier(String[] parts);
}
```

## 常用属性与应返回的字段（摘要，完整参见 wiki）

* `buff.xxx.up` → 1 if buff present, else 0；`buff.xxx.remains` → seconds；`buff.xxx.stack` → stack count。([GitHub][2])
* `cooldown.xxx.remains`, `cooldown.xxx.charges`, `cooldown.xxx.duration_expected` 等。([GitHub][2])
* `dot.xxx.refreshable`, `dot.xxx.remains`, `dot.xxx.ticking` 等（支持 pandemic 计算规则）。([GitHub][2])
* `action.something.in_flight`, `action.something.in_flight_remains`（用于投射物）等。([GitHub][2])

**实现注意事项**：

* `debuff.*` 将先查目标，再查 player（SimC 的设计）。`buff.*` 只查 player。([GitHub][2])
* 未定义或不可用的字段返回 `0`（按 SimC 习惯）。
* 对于复杂字段（例如 `trinket.stat.strength.cooldown_remains`），实现时可以把 `trinket.*` 映射到一个合并查询：如果有两件 trinket 则返回最大值（SimC 的做法）。([GitHub][2])

---

# 十四、错误处理、调试输出与诊断

**必做**：

* **解析/绑定错误**：要在绑定阶段（当把字符串 action_name 映射到具体 Action）报出清晰错误（文件:line:col, 消息）。
* **表达式解析错误**：指明 token/位置与期望的符号。
* **运行时警告**：当表达式引用了不存在的 buff/set_bonus/item 时记录一次警告（避免重复噪音）。
* **可选**：实现 `--dump-parsed-apl` / `save_actions`，能把解析后的 IR（含 AST）序列化回文本，便于对比与回归测试（SimC 有类似导出功能）。([GitHub][1])

---

# 十五、性能 & 优化建议

* **编译/缓存 AST**：在加载时把表达式解析成 AST 并缓存，运行时直接 eval，避免反复解析字符串。SimC 在 action_t 内保存 `if_expr` 的 AST 指针（expr_t）。([simulationcraft.org][3])
* **短路求值**：对逻辑运算实现短路，减少不必要变量访问（尤其是冷却/套装/目标计数查询）。
* **增量更新 & 事件触发**：对大型并发模拟，优先实现 event-driven 调度并尝试收集表达式依赖（conservative static analysis：如果表达式里出现 `time`、`cooldown.X`、`buff.Y`，就把这些项目加入唤醒依赖集）。
* **表达式预计算**：对纯常量子表达式或与角色静态配置（talents/gear）相关的子表达式，在绑定/初始化阶段进行预计算或折叠。
* **内置函数优化**：对频繁调用的内置函数（e.g., `active_dot.xxx`）做缓存或 O(1) 查询实现。

---

# 十六、测试计划（必须详尽）

1. **Lexer / Parser 单元测试**

   * 基本 tokens 测试；边界（连续 `%`、`%%`、字符串）
   * 行级解析测试：`/spell_name,if=cond`, `actions+=/a,if=1` 等（带错误注入测试）

2. **Expression Evaluator 单元测试**

   * 运算优先级测试：`1+2*3 == 7`
   * 比较/逻辑测试：`(1&0)|1 == 1`，`!0 == 1`
   * 标识符解析：模拟 EvalContext 返回值并测试 `buff.x.up`, `cooldown.y.remains` 等
   * FunctionCall 测试（floor/ceil/min/max）

3. **ActionList 行为测试（集成）**

   * 优先级扫描测试：多行 APL，确保第一个满足的被执行
   * wait / wait_until_ready / pool_resource 行为测试（时间推进场景）
   * sequence 与 call_action_list 嵌套测试（边界：空子序列、循环调用）

4. **对比测试（回归）**

   * 取一组已知的 SimC APL 和在 SimC 上的输出（Combat log / action trace），在移植实现中对同一初始 state 做一小段模拟，对比首 N 次动作序列（expect identical or allowed diffs）。这是验证移植正确性的关键步骤。([GitHub][1])

5. **性能基准**

   * 单次仿真内每秒循环次数、表达式 eval 次数、内存使用、GC 或分配压力（取目标语言特性）。

---

# 十七、迁移（移植）步骤清单（实践路线图）

1. **解析器与表达式子系统**（优先）

   * 实现 Lexer/Parser 并通过单元测试覆盖表达式子语言。
   * 实现 AST 和 Evaluator，绑入一个假的 EvalContext（可用硬编码值进行测试）。

2. **Action Registry 与 Parser 绑定**

   * 实现 action 注册表（用最小动作集合作为 PoC），解析 APL 中 action_name 并绑定。
   * 将 `if_expr` 等挂载到 action_line。

3. **简单 Executor + Scheduler（Poll 模式）**

   * 实现简单循环（每 100ms）扫描 action list 并执行第一个满足的动作；实现 execute() 的最小副作用（消耗资源、设置 cooldown、记录执行日志）。
   * 用几条 APL 验证优先级行为（例如 SimC 的示例 warrior list）。([GitHub][1])

4. **扩展 EvalContext：资源、buff、cooldown**

   * 实现真实的 `get_buff`, `get_cooldown` 等，使表达式能评估真实变量。对每个内置变量写单元测试。([GitHub][2])

5. **实现高级特性**：sequence、line_cd、target_if、pool_resource、wait_until_ready、spell_queue（可选）。测试覆盖。([GitHub][1])

6. **性能优化**：缓存 AST、短路、事件驱动（可选）。

7. **对齐 SimC 行为**：用 SimC 的 APL 和样本初始状态做逐步对照（动作序列、技能冷却/资源曲线），修正语义差异。

8. **完善日志/错误/调试**：增加 `--dump-parsed-apl`、详细 action trace 输出。([GitHub][1])

---

# 十八、示例：关键组件伪代码（Python 风格）

## 18.1 Expr AST evaluate（伪代码）

```python
class Literal(Node):
  def eval(self, ctx): return self.value

class Identifier(Node):
  def eval(self, ctx):
    parts = self.parts
    # example resolver
    if parts[0] == 'buff':
      return ctx.buff(parts[1]).property(parts[2]) or 0.0
    elif parts[0] == 'cooldown':
      return ctx.cooldown(parts[1]).property(parts[2]) or 0.0
    else:
      return ctx.get_global(".".join(parts)) or 0.0

class Binary(Node):
  def eval(self, ctx):
    if self.op == '&':
      left = self.left.eval(ctx)
      if left == 0.0: return 0.0    # short circuit
      right = self.right.eval(ctx)
      return 1.0 if (left != 0.0 and right != 0.0) else 0.0
    # handle other ops similarly
```

## 18.2 ActionList Executor（伪码）

```python
def execute_action_list(actor, now):
  for line in actor.action_list:
    action = line.action_ref
    if not action.ready(actor, now): continue
    if line.if_expr:
      if line.if_expr.eval(actor.ctx, now) == 0: continue
    # passed; execute:
    action.execute(actor, now, line)
    apply_line_cd(line, now)
    return
  # no action found -> schedule next wake
```

---

# 十九、测试示例（具体用例）

1. **优先级测试**

   * APL:

     ```
     actions=auto_attack
     actions+=/ability_A,if=cooldown.B.remains>10
     actions+=/ability_B
     ```
   * 期望：若 B 可用（ready），则 first run picks `ability_B`（因为 `ability_A` 的条件 false），否则 `ability_A` 选中。

2. **buff/dot refresh 测试**

   * APL:

     ```
     actions+=/apply_dot,if=dot.my_dot.refreshable
     ```
   * 将 `dot` 状态设成 `remains=1`（若 duration=10 且 pandemic=30%，refreshable 为 true），验证会触发。

3. **sequence 行为**（见上文 sequence 说明）([GitHub][1])

---

# 二十、常见陷阱 & 注意事项（总结）

* **表达式副作用**：在表达式求值中避免副作用（例如查询函数不应改变状态），否则短路/求值次序会带来不可预测行为。
* **短路与兼容性**：如前所述，短路是推荐实现，但务必通过测试确保与 SimC 行为对齐（如果 SimC 在某些场景没有短路，则可能有差异）。([GitHub][2])
* **时间/精度**：SimC 使用秒为单位，时间比较需考虑浮点精度；在 `time_to_die` 等表达式中建议用 epsilon 检查。
* **line_cd 与 action cooldown 区别**：`line_cd` 是 APL 行级的额外限制（不同于 action 自带的 cooldown）。要在执行后同时设置两个。([simulationcraft.org][3])
* **aura 名称标准化**：SimC 用下划线替代空格并忽略非字母数字字符；在解析时应统一标准化策略。([GitHub][2])

---

# 二一、交付/验收条件（建议）

* **解析器 & Evaluator**：通过全部表达式语法的单元测试（覆盖运算/函数/identifiers）。
* **Executor**：通过一套与 SimC 在同等初始条件下的动作序列对比（至少前 100 个动作一致或合理差异说明）。
* **性能**：在目标语言上单次仿真（指定配置）在预期时间内完成（与语言特性相关，需基准测试）。
* **日志**：支持 `dump-parsed-apl` 与 `action trace` 输出，便于回归与调试。([GitHub][1])

---

# 二二、参考（关键文档 & 源）——（移植时必须对照）

* ActionLists（SimC Wiki） — APL 高层语义、动作与选项说明（优先级扫描、wait、sequence、line_cd 等）。([GitHub][1])
* Action-List-Conditional-Expressions（SimC Wiki） — 条件表达式语法、内置变量（buff/dot/cooldown/target 等）的完整字段说明。([GitHub][2])
* SimC action_t Doxygen（struct action）— 展示 action_t 中保存 `if_expr`、`line_cooldown`、`target_if_expr` 等字段，直接映射 APL 行实现细节。([simulationcraft.org][3])
* Characters（SimC Wiki）— 调度（Schedule Ready）、初始配置与一些评估细节（poll-based vs event-based scheduling）。([GitHub][4])


[1]: https://github.com/simulationcraft/simc/wiki/ActionLists "ActionLists · simulationcraft/simc Wiki · GitHub"
[2]: https://github.com/simulationcraft/simc/wiki/Action-List-Conditional-Expressions "Action List Conditional Expressions · simulationcraft/simc Wiki · GitHub"
[3]: https://simulationcraft.org/doc/structmonk_1_1actions_1_1spells_1_1black__ox__brew__t.html "SimulationCraft: monk::actions::spells::black_ox_brew_t Struct Reference"
[4]: https://github.com/simulationcraft/simc/wiki/Characters "Characters · simulationcraft/simc Wiki · GitHub"
[5]: https://github.com/simulationcraft/simc/discussions?utm_source=chatgpt.com "simulationcraft simc · Discussions"
