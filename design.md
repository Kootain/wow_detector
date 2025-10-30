# 模块设计

## 模块拆分
- Ingame State
 - Buff、Debuff、TargetBuff、Aura:监控玩家、玩家目标等身上的buff、debuff光环等
 - Spelling Status: 施法状态
 - Combat Log: 战斗信息
 - Resource: 血量、蓝量
- State Predict
- Strategy
- Action Execute
- Ingame Config Panel

## 模块数据交互
Game -> Ingame State(inspector) -> Ingame State(monitor) -> Ingame State(StateManager)

Predict:
> 这里可能有两种方式，一种是定期loop去查询最新的state
> 另一种是监听一些特定的变化
  Predict -query-> StateManager
  Predict Config  
  > TODO: define how to build a predict strategy, maybe a new dsl?
  > 一个预测例子：如果 xxx buf = 4 层, 正在施法 xxx , 如果xxx 成功，则buf = 5层
  Predict Execute: 执行预测，将预测结果输出为一种 Ingame State
  Predict Monitor: 监控预测的等待条件，如果等待条件执行成功，则预测成功。否则预测失败，依赖于这个预测结果的Strategy 需要重新评估

Strategy:
策略生成时机：
- 定期Loop，低效，且可能不实时?但是胜在简单
- 从逻辑上来说，策略生成的时机：
  - 等待执行命令中
策略demo:
- 

- 执行中动作
- 预备动作

Action Execute
- 执行一个法术
  - 执行时可以设置是否可以打断。
  - 吟唱类法术默认可以打断，可以设置预期执行时间
  - 如果设置了不可打断，后续预备任务
- 监控法术是否执行成功
  - 有过读条
  - cd了
  - 瞬发，gcd怎么办，得依赖combatlog。不依赖应该也还好，如果技能没放出去，或者人工放了其他法术打断了，就当成功释放了。如果实际没成功，策略里的下一个动作应该还是它，在执行一遍就行了
- 避让一些关键保命技能。当检测到保命技能的输入，退让一个gcd
- gcd检测
  
