---
FINAL ARCHITECTURE FREEZE — High-Risk Reasoning Workflow P0

> **Status: design record (rounds 1–3 frozen spec), 2026-08-15. NOT normative.**
> The ID scheme in this document is pre-adjudication: it writes derivations as `D-XXX` and decisions as `Dec-XXX`. The normative scheme, per `workflow/discussion-sync/protocol.md` §9 (Prefix ownership note): Derivations = `DER-XXX`, Decisions keep the legacy `D-XXX`. Where this document and protocol.md §9 disagree, §9 wins. The worked example `workflow/discussion-sync/example/example-task-002-b1p0-swerve/` was created after this document and uses the normative scheme.

  二、Single Source of Truth（本轮最重要结论）
  
  2.1 单向权威链（冻结，不允许第二种解释）

  User / Spec                          (authority — 事实与变更的唯一合法来源)
     │
     ▼
  Ledger (decisions.md) + Verdicts (evaluation.md)
     │   ← 唯一的持久化事实层:entry 的 status 字段就住在 Ledger entry 上
     │   ← 内容(worker写)、证据(verifier写)、状态(orchestrator写)三权分立
     ▼
  Orchestrator                         (sole state coordinator — 唯一能写 status 字段的角色)
     │  按封闭迁移规则执行;每次 ingest 先 git-diff sweep 再迁移
     ▼
  Derived Projections (state.md):
     ## Reasoning State   = pure_function(ledger entries + verdicts)
     ## Blocked           = pure_function(tainted entries × impl map)
     ▼
  Worker PROMPT snapshot / Session Recovery
     (read-only consumers;永远不被咨询"你记得什么")

  2.2 逐项回答

  1. 谁是事实来源:Ledger + Verdicts。就这一处。
  2. 谁产生状态:Orchestrator 依据迁移规则从事实层计算。
  3. 谁可以修改状态:仅 Orchestrator。Worker 写内容，Verifier 写 Verdict，都不写 status。
  4. Agent 能否直接改 Reasoning State：不能。物理上它只是 state.md
  的一个段落，但协议上它是只读投影；任何手改会在下次 ingest 的 git-diff sweep
  中被发现并被重新生成覆盖。
  5. Orchestrator 是否唯一 State Coordinator：是。这是整个系统免于三答案分裂的唯一结构保证。
  6. State 是持久化事实还是派生:派生。ledger entry 上的 status 字段是事实层的一部分（由
  orchestrator 落笔）;state.md 的 ## Reasoning State 与 ## Blocked
  是可随时删除并重新生成的投影。这是关键区分：status 存在 Ledger 而非 state.md，所以 Ledger
  天然胜出一切不一致。
  7. state.md 与 Ledger 不一致谁优先:Ledger 优先，动作 = 重新生成 state.md（机械操作，零判断）。
  8. Agent 手改 state 怎么办:ingest 时的 sweep(git diff decisions.md / evaluation.md /
  state.md）检测非授权写入 → 重新生成 → 若反复发生，属 prompt 违规，orchestrator escalate
  给人。P0 靠"可检测 + 可自愈"，不靠"不可写入"。
  
  2.3 你提的模型是否正确

  你给的链：Artifact/Verdict → Orchestrator → Derived State → 
  Worker/Recovery。正确，冻结采用。补一条不可省略的反向监督边：Orchestrator 每次 ingest
  先对事实层做 diff sweep——这是回答 §17 Q2/Q7 的命门，成本一行 git diff，零新组件。

  ---
  三、Reasoning Ledger 最终内容（选项 B 的修正版）
  
  结论：Ledger = Assumption + Derivation + Constraint + Decision。但 Decision 不是新增 
  artifact——它是 discussion-sync 已有的 # Decisions bucket;P0 对它的唯一动作是加一个可选字段 
  basis:。
  
  ┌───────────┬───────────────────────────────────────┬────────────────────────────────────┐
  │   类型    │     必须存在的理由（对应 failure      │           能否被已有表达           │
  │           │               scenario)               │                                    │
  ├───────────┼───────────────────────────────────────┼────────────────────────────────────┤
  │ Assumptio │ Scenario 2/3：前提漂移、推测静默升级  │ 不能——Decision 是"选择",Assumption │
  │ n         │ 。没有它，"N=3"这类根基无处可钉       │  是"关于世界的信念"                │
  ├───────────┼───────────────────────────────────────┼────────────────────────────────────┤
  │ Derivatio │ Scenario                              │                                    │
  │ n         │ 1/5：上游推导错误需反向找到下游。没有 │ 不能                               │
  │           │  from: 链则无 influence graph         │                                    │
  ├───────────┼───────────────────────────────────────┼────────────────────────────────────┤
  │ Constrain │ Scenario 6：接线语义（哪信号进哪计算  │ Decision 近义但 Decision 无        │
  │ t         │ ）被静默改，公式与单测全绿但设计已死  │ verify:，无法被 Verdict            │
  │           │                                       │ 锚定；保留独立                     │
  ├───────────┼───────────────────────────────────────┼────────────────────────────────────┤
  │           │ Scenario 5 扩展："因 D-003            │ 已存在；P0 仅补 basis:             │
  │ Decision  │ 成立所以选择 soft-penalty";D-003      │ 可选字段。这是它能进 P0            │
  │ （已有）  │ 死后选择必须                          │ 的唯一理由——它补的是传播图的一个真 │
  │           │ needs_review，否则整个实现方向悬空    │ 实断点，成本一个可选字段           │
  └───────────┴───────────────────────────────────────┴────────────────────────────────────┘

  论证为什么 Decision 不该被砍：没有 basis:，当 D-003 被证伪时，"使用 soft-penalty
  方案"这个决定没有任何机制被复查——它不是推导（无
  verify:)，但它是错的。一个可选字段封堵一类静默失效，ROI 足够。除 basis: 外，Decision 
  语义一律不动。

  ---
  四、Assumption 最终规则
  
  4.1 最小 Schema（冻结）

  - id: A-001
    content: N=3 swerve modules        # 一句话
    source: user | spec | inference    # 封闭三值 — 注意:observation 已被移除
    status: proposed | valid | invalid # 三值,Assumption 无 
  needs_review(它是根,上面没有东西可翻)
    revises: A-000                     # 可选;出现时旧 entry 由 orchestrator 置 invalid(reason: 
  superseded)
    reason: <void|触发说明>             # 仅 invalid 时必填

  4.2 source 词表收敛：删掉 observation，删掉 subagent_inference
  
  - observation 不需要在 Assumption 上：观测证据天生属于 Verdict（实测 = 一次验证行为）。Case B
  的正确路径是：inference 假设 + 一条 observation 型 Verdict PASS → 晋级 valid。词表合并到 
  Verdict 侧，Assumption 侧省一个值。
  - subagent_inference 不需要:orchestrator 视角下，非 user/spec/verdict 的一切断言都是
  inference。子代理无特权，单列一词不带来任何行为差异。

  最终词表：user | spec | inference。三值，不能再多。
  
  4.3 proposed / accepted / superseded 是否需要

  - accepted = valid（不另设）
  - superseded = invalid + reason: superseded by A-0XX（不另设）
  - proposed 必须存在——它是防静默升级的检疫区，无可替代

  4.4 防静默升级的最小机制（冻结版，四件套）
  
  1. Append-only：任何"修改"= 新 entry + revises:；旧 entry 只能由 orchestrator 翻 status。
  2. 出生状态由 source 决定:user/spec → valid;inference → proposed。
  3. 晋级封闭路径:proposed → valid 仅允许 (a) user 确认，or (b) 对该 entry 的 Verdict PASS。
  4. Orchestrator sweep:ingest 时 diff ledger，任何绕开 (1)-(3) 的写入即违规，覆盖修复 +
  escalate。

  四件全是 prompt/协议义务，零代码零组件。

  ---
  五、Derivation 最终规则
  
  5.1 晋级规则（三条须同时满足，逐条过检）
  
  一条自然语言结论必须成为 Derivation artifact，iff：
  
  1. 有明确下游：写出至少一个消费者（另一个 D / 一个 impl map 目标 / 一个 worker prompt 输入）。
  2. 可被检查：能写出 verify:（一个可执行的 fixture/命令/inspection 目标）。
  3. 需要跨上下文存活：session 换人/compact 之后仍然被需要。

  逻辑循环检查：规则 1"会被下游使用"在创建时是按意图判断（我推导它是为了让 X
  构建）——不要求消费者已存在，因此无循环。遗漏检查:"跨 worker 的多方共识性中间结果"——被规则 1
  的消费者定义覆盖（"另一个 worker 的 prompt 输入")，无遗漏。

  5.2 from 必须存在

  强制。from: ≥1 是 Derivation 的构成性条件。 一个 from 为空的结论不是 Derivation——它要么是
  A（关于世界的信念），要么是 Dec（设计选择）。这一条堵死了前两轮遗留的"from-less derivation
  漂流瓶"漏洞，且让传播图永远连通到根(A/Dec 是唯一根类型）。Schema:

  - id: D-002
    content: a_i = (−sinδ_i, cosδ_i, r_y,i sinδ_i + r_x,i cosδ_i)ᵀ
    from: [A-001, A-002]     # ≥1,可指向 A/C/D/Dec 任一 ID — 全图统一 ID 空间
    by: project v_i onto lateral axis   # 一句话方法
    verify: fixture t1: δ=0,v=(1,0,0) ⇒ a_i·v=0   # 一个可执行检查
    status: proposed | valid | needs_review | invalid
    revises: / reason: 同 A 规则

  出生规则（本轮新增，统一化最后一刀）:Derivation 一律 agent-authored → 出生即 proposed，仅由
  Verdict PASS 晋级 valid。配合§五不变量"entry 可 valid 当其 from:/basis: 全线
  valid"，信任不会因转写而膨胀。

  ---
  六、Dependency 最终规则（冻结）
  
  - 存在形式仅三种：D 的 from:(multi)、Dec 的 basis:(optional multi)、V/ImplMap 的
  target:(single)。
  - reverse dependency:P0 不持久化。反向闭包 = orchestrator 在 §9 里 grep
  即时计算。否则就是在维护第二份会漂移的依赖真源——明令禁止。
  - dependency type:P0 拒绝。引入则 needs_review 语义分裂，状态机加倍。
  - confidence:P0 拒绝。与"valid = 流程许可而非真理"的定位冲突。

  任何以"查询方便"为名的反向索引持久化都视为第二 SSoT 违规。

  ---
  七、Verification 最终规则

  7.1 最小 Schema（冻结）
  
  - id: V-501
    target: D-002            # 必填,单一 target
    method: fixture t1 run   # 可执行方式
    expected: a_i·v = 0      # 必填
    actual: 0.31             # 必填
    verdict: FAIL            # PASS | FAIL
    evidence: logs/t1.json   # 路径必填
    author: verifier-session-4c2a

  7.2 逐项回答

  1. PASS 语义:"在当前证据下 workflow 准予继续使用 target。"不声称数学真。此句写入 protocol.md
  防语义通胀。
  2. FAIL 能否直接 INVALID target:FAIL 是权威,Orchestrator 是执行者——Verdict 落盘 → ingest →
  orchestrator 按规则翻 status。分离保留，因为 Verdict 本身是 artifact（可审计、可对抗重查）。
  3. Agent 自然语言质疑:永不可致 INVALID。产物只能是 proposed 反假设或 Q-XXX。INVALID
  合法来源封闭三值：{Verdict FAIL, user 声明， 被 revises：取代}。
  4. D PASS 但 C FAIL 并存：状态按 target 独立。D 守其 PASS,C 因 FAIL 转 invalid
  并独立传播。无"任务级总状态"这种东西——这正是状态机必须 per-entry 的原因。
  5. 必须引用具体 Artifact：必填单 target。空 target 的 Verdict = 非法条目，ingest 拒收。
  6. 一个 V 验多 target？ 不允许。一对多会让 grep 传播复杂化且埋下"部分 PASS"歧义。多 target =
  多 V。
  
  7.3 防"自己证明自己"的最小机制
  
  三件套（全部复用现有机制，零新角色）:① Verdict 只能由 verifier session 写（workflow.md 的
  worker/verifier 分离已是铁律）;② expected/actual/evidence 三必填；③ verify:
  必须指向作者之外可执行的工件。P0 不设 Independent Reviewer——verifier session 已是事实上的独立
  reviewer。
  
  ---
  八、State 最终收敛
  
  8.1 你的三个 Case 判定

  - Case A(D002 被验错）→ invalid ✓
  - Case B(A001 变，D002 未重验）→ needs_review ✓
  - Case C（一切正常）→ valid ✓
  
  三态对 D 充分。加上 A/D 出生侧的 proposed，及§四论证 A 无 needs_review，最终：

  ┌────────────┬────────────────────────────────────────────────────────┐
  │    类型    │                         状态集                         │
  ├────────────┼────────────────────────────────────────────────────────┤
  │ Assumption │ proposed / valid / invalid                             │
  ├────────────┼────────────────────────────────────────────────────────┤
  │ Derivation │ proposed / valid / needs_review / invalid              │
  ├────────────┼────────────────────────────────────────────────────────┤
  │ Constraint │ proposed / valid / needs_review / invalid              │
  ├────────────┼────────────────────────────────────────────────────────┤
  │ Decision   │ valid / needs_review / invalid(user 直出，无检疫需求） │
  └────────────┴────────────────────────────────────────────────────────┘

  8.2 完整状态转换图（冻结）

          birth: source∈{user,spec}          birth: D 必走 / A·C source=inference
                │                                   │
                ▼                                   ▼
          ┌──────────┐                       ┌───────────┐
          │  valid   │                       │ proposed  │
          └──┬───┬───┘                       └──┬───┬───┘
             │   │              Verdict PASS    │   │ Verdict FAIL
     §9: from/ │  │ Verdict FAIL ◄──────────────┘   │  or user 否决
     basis 上游│  │ or user 声明                     ▼
     flip      │  ▼                            ┌─────────┐
             │ ▼                               │ invalid │ (terminal)
             ▼                                  └────▲────┘
       ┌──────────────┐  re-verify FAIL              │
       │ needs_review ├──────────────────────────────┘
       └──────┬───────┘
              │ re-verify PASS
              ▼
          ┌────────┐    复活唯一通道:新 ID + revises:(永不原地翻回)
          │ valid  │
          └────────┘

  不变量（写入 protocol.md)：一个 entry 可为 valid，仅当 from:/basis: 中每个 ID 当前 valid。

  8.3 Blocked 归属判词（你三轮的悬案）

  你的倾向正确：Blocked 不是 Reasoning State，是 Orchestrator 计算出的 Workflow State。

  理由：Blocked = f(tainted entries, impl map)——它是两个事实的派生，本身不产生新事实。它与 ##
  Reasoning State 同为 state.md 里的投影段落。意外红利：state.md 本来就有 ## Blocked 
  section（实例已确认）——P0合适的改动量是"按协议填它"，而不是"新建它"。

  ---
  九、Invalidation Protocol（冻结为 §9，六步）
  
  触发者:Orchestrator（仅两个时机：ingest sync 之时；显式 reasoning sweep 之时。无 watcher、无
  daemon)。

  Step 0  SWEEP      git-diff ledger/verdicts/state.md 自上次 ingest 以来
                     ├─ 发现非授权 status 写入 → 复原 + escalate
                     └─ 发现事件:{Verdict FAIL 落盘 | accepted 的 revises 变更 | user 声明}
  Step 1  SEED       取事件的直接肇事 ID 集(如 target 为 D-002 的 FAIL Verdict → seed={D-002})
  Step 2  CLOSURE    迭代 grep -E '^-.*(from|basis):.*\b<ID>\b' decisions.md 至不动点
                     命中 entry → needs_review(已 invalid 跳过),reason=触发上游 ID
                     (闭包而非一跳:grep 迭代成本为零,漏跳成本是污染)
  Step 3  BLOCK      closure ∩ impl-map targets → file::symbol 集 → 写入 state.md ## Blocked
  Step 4  REGEN      重算并覆写 state.md ## Reasoning State(投影,机械)
  Step 5  NOTIFY+GATE 后续 worker PROMPT 携带 snapshot;暂停派发触及 Blocked symbol 的 worker;
                     在飞的 worker 不打断(其 PROMPT 是自足的),由 verifier 在 diff 检查兜底
  Step 6  RESOLVE    派 Reasoning Worker 重推(新 ID + revises:)→ Verifier 重跑 verify:
                     → Verdict PASS → orchestrator 翻 valid → 重新跑 §9 直至 closure 清空

  逐项回答：
  1. 谁触发：仅 orchestrator，仅两个时机。
  2. 谁算影响面:orchestrator，纯 grep 闭包，无判断。
  3. 谁改状态:orchestrator，按迁移表，无自由裁量。
  4. 谁通知 Worker：下一个 PROMPT（快照内嵌）；在飞 worker 由 verifier diff 兜底，不打断。
  5. 人工介入点：仅两处——proposed 的晋级裁决（非 observation 路径）、ESCALATE
  判断。机械传播零人工。
  6. 下游其实不受影响怎么办:needs_review 不预设损坏，只强制重查；re-verify PASS 即回落
  valid。reason: 记录肇事 ID，让 auditor 只做定点复查，不做全账重审。

  ---
  十、Stop-the-line 最终粒度

  ┌────────────────────────┬─────────────┬───────────────────────────────────────────────────┐
  │          粒度          │    判定     │                       理由                        │
  ├────────────────────────┼─────────────┼───────────────────────────────────────────────────┤
  │ Task                   │ ✗           │ 一个公式错废掉整个任务，明显过杀                  │
  ├────────────────────────┼─────────────┼───────────────────────────────────────────────────┤
  │ Module                 │ ✗           │ module 边界与影响面无关                           │
  ├────────────────────────┼─────────────┼───────────────────────────────────────────────────┤
  │ File                   │ ✗           │ Scenario 7 反例：solver.rs 同文件含无关 logging   │
  ├────────────────────────┼─────────────┼───────────────────────────────────────────────────┤
  │ Line range             │ ✗（仅参考） │ 编辑漂移，三天后行号即谎言                        │
  ├────────────────────────┼─────────────┼───────────────────────────────────────────────────┤
  │ file::symbol（函数名） │ ✓ P0        │ 函数符号编辑稳定、grep 可定位、与 impl map        │
  │                        │             │ 自然对齐                                          │
  └────────────────────────┴─────────────┴───────────────────────────────────────────────────┘
  
  P0 最小粒度 = file::symbol，行号仅 advisory。
  执行机制 = 三件套:PROMPT 铁律（"Blocked symbols 不得触碰，必须触及→ESCALATE")+ Verifier 落
  diff 检查（grep diff hunks 中的 blocked symbol 名）+ Judge 抽查。P0 
  不做自动拦截——检测到违规即修复，而非物理禁止。
  P1 可升级粒度:LSP/symbol-reference 级精确范围；P0 不需要。

  ---
  十一、Recovery Protocol（冻结）
  
  你的 B 选项正确，且必须严格 B（派生、orchestrator 生成、机械覆写）。逐项排除：

  - A（人工维护）：必然漂移 = 再造一个 SSoT 灾难，一票否决。
  - C（结合）：任何"人工部分"都是漂移入口，一票否决。
  - B 唯一存活。但注意精确措辞：snapshot 不是"每次读取时由读者现算"(worker
  各算各的会不一致），而是 orchestrator 在每次 §9/ingest 后重新生成落盘，读者只读。

  Snapshot 字段（删除一切可删后），落在 state.md ## Reasoning State:
  
  ┌─────────────────┬───────────────────┬───────────────────────────────────────────────────┐
  │       段        │      保留？       │                       内容                        │
  ├─────────────────┼───────────────────┼───────────────────────────────────────────────────┤
  │ Goal 指针       │ 保                │ task.md 路径 + 一行目标                           │
  ├─────────────────┼───────────────────┼───────────────────────────────────────────────────┤
  │ Valid           │ 保                │ 每条一行：id + content +                          │
  │ Assumptions     │                   │ source（防前提漂移的命门）                        │
  ├─────────────────┼───────────────────┼───────────────────────────────────────────────────┤
  │ Valid           │                   │ 仅"无 valid                                       │
  │ Derivations     │ 保，frontier-only │ 下游、正被实现消费"的叶节点；内部节点靠 from:     │
  │                 │                   │ 懒加载                                            │
  ├─────────────────┼───────────────────┼───────────────────────────────────────────────────┤
  │ needs_review    │ 保                │ id + reason（触发上游）                           │
  ├─────────────────┼───────────────────┼───────────────────────────────────────────────────┤
  │ invalid         │ 保                │ id + reason 一词（防重新推导死路、防引用死结论）  │
  ├─────────────────┼───────────────────┼───────────────────────────────────────────────────┤
  │ Open            │ 保                │ 未跑/FAIL 待重跑的 Verdict 目标                   │
  │ Verifications   │                   │                                                   │
  ├─────────────────┼───────────────────┼───────────────────────────────────────────────────┤
  │ Blocked         │ 保                │ file::symbol 列表                                 │
  ├─────────────────┼───────────────────┼───────────────────────────────────────────────────┤
  │ Proposed 待裁决 │ 保，≤3 行         │ orchestrator 欠的裁决，不列即烂账                 │
  └─────────────────┴───────────────────┴───────────────────────────────────────────────────┘
  
  体量估算 ≤35 行，state.md 原段 + 新增后仍压在 60 行硬约束内。新 Agent 恢复行为契约：读 task.md
   → 读 ## Reasoning State + ## Blocked → 对所需 entry 懒读 decisions.md → 开工。不读历史
  sync、不读全量 ledger、不读完整设计 doc。

  ---
  十二、Agent / Orchestrator 权限边界（冻结）
  
  ┌──────────────────────┬─────────────┬────────────┬──────────────────┬───────────────────┐
  │         动作         │ Reasoning   │  Develop   │ Verifier Session │   Orchestrator    │
  │                      │   Worker    │   Worker   │                  │                   │
  ├──────────────────────┼─────────────┼────────────┼──────────────────┼───────────────────┤
  │ 写 A/D/C             │             │ ✗（须      │                  │                   │
  │ 内容（出生态按       │ ✓           │ ESCALATE)  │ ✗                │ ✗                 │
  │ §4.4/§5.2)           │             │            │                  │                   │
  ├──────────────────────┼─────────────┼────────────┼──────────────────┼───────────────────┤
  │ 写 Verdict           │ ✗           │ ✗          │ ✓（仅限 verifier │ ✗                 │
  │                      │             │            │  session)        │                   │
  ├──────────────────────┼─────────────┼────────────┼──────────────────┼───────────────────┤
  │ 写 Impl Map 条目     │ ✗           │ ✓          │ 校验（不写）     │ ✗                 │
  ├──────────────────────┼─────────────┼────────────┼──────────────────┼───────────────────┤
  │ 翻 status 字段       │ ✗           │ ✗          │ ✗（产 Verdict    │ ✓（唯一）         │
  │                      │             │            │ 即权力终点）     │                   │
  ├──────────────────────┼─────────────┼────────────┼──────────────────┼───────────────────┤
  │ 写 state.md 投影段   │ ✗           │ ✗          │ ✗                │ ✓（机械覆写）     │
  ├──────────────────────┼─────────────┼────────────┼──────────────────┼───────────────────┤
  │ 提交 revises 变更    │ ✓           │ ✓（经      │ ✗                │ 接受/驳回（user   │
  │                      │             │ ESCALATE)  │                  │ 背书）            │
  ├──────────────────────┼─────────────┼────────────┼──────────────────┼───────────────────┤
  │ 裁决 proposed        │ ✗           │ ✗          │ 证据供给         │ ✓(user 确认 or    │
  │                      │             │            │                  │ Verdict)          │
  ├──────────────────────┼─────────────┼────────────┼──────────────────┼───────────────────┤
  │ 执行 §9 / 计算       │ ✗           │ ✗          │ ✗                │ ✓                 │
  │ Blocked              │             │            │                  │                   │
  ├──────────────────────┼─────────────┼────────────┼──────────────────┼───────────────────┤
  │ 决定 worker 是否继续 │ ✗           │ ✗          │ ✗                │ ✓(Judge)          │
  └──────────────────────┴─────────────┴────────────┴──────────────────┴───────────────────┘
  
  你给的清单整体正确；被收紧的三处：① Verdict 不是"Agent 能创建 Verification"——只有 verifier
  session 能写；② Develop Worker 连 Derivation 都不能新增（前两轮已立，此处冻结）;③ Orchestrator
   不能写内容、不能写 Verdict——三权分立：内容权（worker)、证据权（verifier)、状态权（orchestrato
  r)、最高权威（user)。这个四元分立是整个设计防自我繁殖的根基——单角色无法既供料又盖章。零 RBAC
  组件，靠 prompt 模板 + sweep diff + Judge。

  ---
  十三、High-Risk Gate（冻结判断规则）
  
  硬触发（任一即入）:
  - H1：任务将产生或修改数学推导/公式/闭式解/优化目标
  - H2：任务修改控制/运动学/动力学/调度/并发核心算法
  
  软指标（≥2 即入）:
  - S1：将形成 ≥2 级推导链
  - S2：一个中间错误会静默污染 ≥2 个下游消费者
  - S3：预期跨 session / subagent 交接
  - S4：存在必须幸免于实现的接线约束（哪信号进哪计算）

  判定与豁免:Orchestrator 在 Plan 执行一次判断，结果记入 task.md（一行）。默认走低风险普通
  workflow。用户可双向强制。明令禁止以"Agent
  觉得复杂"为入闸依据——判据全部指向任务结构，不指向感受。

  ---
  十四、Swerve Failure Test（八场景全跑，冻结模型下）

  前置 ledger:A-001..A-004（同前轮）,D-001..D-005,C-001..C-004,Dec-001(basis:[D-003] 选择
  soft-penalty 路线）,Impl Map 四条（build_a_i / closed_form_v_star / waypoint_gen /
  closest_heading_flip)。
  
  Scenario 1：上游公式 D-002 错误
  
  Input:verifier 重跑 fixture t1 发现 a_i·v=0.31≠0。
  → Ledger：不变（append-only)。
  → Verdict:V-501{target:D-002, FAIL, evidence:t1.json} 落盘。
  → State迁移:ingest → orchestrator 翻 D-002=invalid。
  → §9:seed{D-002}→closure{D-003(from:D-002), D-004(from:D-003)}→needs_review;Dec-001 basis 含
  D-003 不直接命中，但 D-003 needs_review 后下一轮传播不触发（needs_review 仅由
  invalid/supersede 触发，不级联——冻结规则：闭包只对 invalid 种子展开，needs_review 
  不二次传播，否则一次失效必拖全图）。
  → Block:build_a_i、closed_form_v_star 入 ## Blocked。
  → Orchestrator：停派触及这两个 symbol 的 worker；派 Reasoning Worker 重推。
  → Agent：其它区域正常；新 D-006(revises:D-002）出生 proposed → 验 PASS → valid → D-003/D-004
  定点重验回落 valid → Blocked 清空。
  
  Scenario 2:autocompact 后忘了 N=3

  Input：新上下文恢复。
  → 读:task.md → ## Reasoning State:valid A: A-001 N=3 (source:spec)…。
  → Agent：前提被 ledger 权威锚定；若仍按 N=4 产出，与 A-001 冲突，verifier 在 Verdict
  阶段捕获。
  → 无需 §9。恢复侧机制闭环成立。

  Scenario 3:Agent 自行推测 N=4

  Input:agent 想"4 轮更合理"。
  → Ledger：它能做的唯一动作 = 写 A-010{content:"N=4", source:inference, revises:A-001,
  status:proposed}。协议上不存在它翻 A-001 的路径。
  → State：全线不动。Snapshot 的 Proposed 段列 A-010。
  → Orchestrator:ingest 见 proposed → 升级 user，或派 verifier 实测（读机器人配置 → Verdict →
  observation 路径晋级）。A-010 晋级瞬间 → A-001 翻 invalid(superseded)→ §9 跑 Scenario 4 流程。
  → 防静默升级：协议级成立。

  Scenario 4：用户正式改 N=4

  Input:sync 带来用户指令。
  → Ledger:A-011{source:user, valid, revises:A-001};orchestrator 翻
  A-001=invalid(reason:superseded)。
  → §9:seed{A-001}→closure{D-001,D-002,D-003,D-004,D-005 全部 needs_review};Dec-001(from
  图不受影响）保持 valid。
  → Block：四个 mapped symbol 全冻结。
  → 注意:D-003("N≥4 过约束"）在此变体下真值非但没死反而更强——但机制不看真值看点检：定点
  re-verify PASS 即回落。needs_review 不是死刑，是点检单。
  → Orchestrator：串行派发重验，链路每清一段解锁一段。

  Scenario 5:Verification FAIL(D-003)

  → V-502{target:D-003, FAIL} → D-003=invalid → closure{D-004} + Dec-001 basis:[D-003] → 
  needs_review(basis: 字段在此场景赚到存在价值：方案选型悬空被显式标出）。
  → Block:closed_form_v_star。Orchestrator 面临的不是"改公式"而是"重选路线"——ESCALATE 给
  user。这是 basis: 唯一但致命的用武之地。
  
  Scenario 6:Constraint 被改
  
  Input:user 决定"filter 收敛后 drive 可切回 reference twist"。
  → Ledger:C-005{source:user, valid, revises:C-002};C-002=invalid(superseded)。
  → §9:from 图命中 C-002 的 entry（若有）needs_review;impl map 中 C-002 的 target
  symbol(drive_update)→ 入 Blocked，点检接线改动。
  → 约束与推导走同一张图、同一协议——无第二套机制。

  Scenario 7:D-002 invalid + 同文件无关函数

  → Blocked = {build_a_i, closed_form_v_star};solver.rs::log_tick 不在 impl map tainted 集 →
  可动。
  → verifier 对后续 diff 做 blocked-symbol grep，越界即 FAIL。
  → 函数符号粒度通过反例检验。
  
  Scenario 8：新 Session 恢复
  
  → 读 task.md(2 行）+ ## Reasoning State + ## Blocked（约 30 行）→ 5
  分钟恢复"现在可信什么、哪里冻结、还欠什么验"。
  → 懒读 decisions.md 具体 entry；不读历史 envelope。
  → 恢复成本与任务长度解耦——设计目标达成。
  
  八场景全部闭合。P0 对最初定义的失效类无缺口。
  
  ---
  十五、FINAL P0（冻结，7 项）

  FINAL_P0:
    1_High-Risk_Gate:
      type: Behavior
      purpose: 把机制锁在高风险任务上,普通任务零成本
      minimum: §十三 触发规则 + task.md 一行记录
      owner: Orchestrator
      why_P0: 无它则机制被用进每个任务,复杂度税拖垮日常开发

    2_Reasoning_Ledger:
      type: Artifact(SSoT)
      purpose: 假设/推导/约束/选型依据的唯一权威存放,append-only
      minimum: decisions.md 三区扩展(A/D 新增 + C 加 verify: + Dec 加可选 basis:);
               字段 {id,content,source|from+by+verify|verify|basis, status, revises, reason};
               sync schema 不动
      owner: Worker 写内容 / Orchestrator 写状态 / Verifier 写证据
      why_P0: Scenario 2/3/5 唯一防线

    3_Verdict:
      type: Artifact + 状态迁移权威
      purpose: 唯一机器可信货币;防自证
      minimum: evaluation.md ## 
  Verdicts;{id,target(单),method,expected,actual,verdict,evidence,author};
               仅 verifier session 可写;"PASS=流程许可"写入 protocol
      owner: Verifier Session
      why_P0: Scenario 1/5 触发源;无它 Ledger 只是意见簿

    4_State_Machine:
      type: State + 封闭迁移规则
      purpose: 定义"当前可信"的精确语义
      minimum: 状态集{proposed,valid,needs_review,invalid}(A/Dec 子集见§8.1);
               INVALID 来源封闭{FAIL,user,supersede};
               valid 不变量(from/basis 全线 valid);
               写入 protocol.md §9
      owner: Orchestrator 执行
      why_P0: 无它 Ledger/Verdict 无法回答"现在信什么"

    5_Invalidation_Protocol:
      type: Behavior
      purpose: 失效沿依赖闭包传播并落进 Blocked
      minimum: §九 Step0-6;sweep+闭包 grep+Blocked 计算+投影重生成;
               needs_review 不二次传播(冻结规则)
      owner: Orchestrator
      why_P0: 无它 Dependency 是死数据,Scenario 1/4/5 失救

    6_Reasoning_State_Snapshot:
      type: State 投影(派生,可重生成)
      purpose: autocompact/session/subagent 的最小恢复集
      minimum: state.md ## Reasoning State + ## Blocked 按 §十一 八段;
               frontier-only 压缩;≤35 行;仅 orchestrator 机械覆写
      owner: Orchestrator 生成 / 全员只读
      why_P0: Scenario 2/8 唯一防线

    7_Impl_Map_And_Block:
      type: Relationship + Behavior
      purpose: 让失效抵达代码且只冻结该冻结的
      minimum: evaluation.md ## Implementation Map: D/C ↔ file::symbol;
               Blocked=tainted×mapped;执行=PROMPT 铁律+verifier diff grep+Judge 抽查
      owner: Develop Worker 写 / Orchestrator 算 / Verifier 查
      why_P0: 无它 stop-the-line 无从落地(S7),有它则不过杀(S7 反例通过)

  总量:7 项能力；落点 = 2 个既有 ledger 文件扩展 + state.md 1 个投影段 + protocol.md 增 §9 + 2
  个既有 prompt 增段 + workflow.md 增 Gate 一段。零新目录、零新系统、零持久化反向索引、零 
  watcher。

  ---
  十六、P1 / P2 排除清单（冻结）
  
  ┌───────────────────────────┬─────────────────────────────┬───────────────────────────────┐
  │            项             │            处置             │          一句话理由           │
  ├───────────────────────────┼─────────────────────────────┼───────────────────────────────┤
  │ Decision Record           │ 已存在，排除出"新增 P0";P0  │ Scenario 5 已论证             │
  │                           │ 仅补 basis: 字段            │                               │
  ├─────────────────────────┼────────────────────────────┼─────────────────────────────────┤
  │ Evidence Ontology       │ P2 拒绝                    │ evidence=路径字段已够           │
  ├─────────────────────────┼────────────────────────────┼─────────────────────────────────┤
  │ Claim                   │ P2 拒绝                    │ = Derivation，无独立语义        │
  ├─────────────────────────┼────────────────────────────┼─────────────────────────────────┤
  │ Fact Ontology           │ P2 拒绝                    │ source+status 已承载区分        │
  ├─────────────────────────┼────────────────────────────┼─────────────────────────────────┤
  │ Independent Reviewer    │ P1（可选 prompt 模板）,P0  │ worker/verifier                 │
  │                         │ 拒绝                       │ 分离铁律已是事实独立复核        │
  ├─────────────────────────┼────────────────────────────┼─────────────────────────────────┤
  │ Symbolic Verification / │ P2 拒绝                    │ 超出 workflow 职责，且无        │
  │  Theorem Proving        │                            │ scenario 需要                   │
  ├─────────────────────────┼────────────────────────────┼─────────────────────────────────┤
  │ Knowledge Graph /       │                            │                                 │
  │ Database / MCP /        │ P2 拒绝                    │ 八场景证明 markdown+grep 可达   │
  │ Reasoning Service       │                            │                                 │
  ├─────────────────────────┼────────────────────────────┼─────────────────────────────────┤
  │ Complex Approval        │ P2 拒绝                    │ proposed 检疫区已最小覆盖       │
  │ Workflow                │                            │                                 │
  ├─────────────────────────┼────────────────────────────┼─────────────────────────────────┤
  │ Advanced Provenance     │ P2                         │ from/basis/revises/source 在    │
  │                         │                            │ task 范围内审计闭合             │
  └─────────────────────────┴────────────────────────────┴─────────────────────────────────┘

  自检：任一项升入 P0 是否能对应一个 §十四 无解 scenario？不能。清单冻结。

  ---
  十七、IMPLEMENTATION READINESS CHECK
  
  ┌─────┬─────────────────┬──────────────────────────────────────────────────────┬─────────┐
  │  #  │     检查项      │                         判定                         │ 证据位  │
  │     │                 │                                                      │   置    │
  │ 1   │ 多 SSoT?       │ 通过。事实层唯一（decisions.md+evaluation.md);stat │ §二         │
  │     │                │ e.md 为可重生成投影，Ledger 优先（§2.2-6/7)        │             │
  ├─────┼────────────────┼────────────────────────────────────────────────────┼─────────────┤
  │     │ Agent 绕       │ 通过。status 写法唯一（orchestrator);sweep diff    │             │
  │ 2   │ Orchestrator 改  │ 可检测违规并自愈（§2.2-8, §9                      │ §二、§九   │
  │     │ State 的路径？   │ Step0)。残余=约定违规需靠检测，P0 明示接受        │            │
  ├─────┼───────────────────┼─────────────────────────────────────────────────┼────────────┤
  │     │ State 无法从      │ 通过。投影=纯函数；每个 status                  │            │
  │ 3   │ Artifact/Verdict  │ 有迁移规则与触发权威（§8)                       │ §八        │
  │     │ 推导？            │                                                 │            │
  ├─────┼───────────────────┼─────────────────────────────────────────────────┼────────────┤
  │     │ Dependency        │ 通过。from: 强制≥1;basis:                       │            │
  │ 4   │ 无法传播？        │ 可选但覆盖选型悬空（S5);ID 全域唯一，闭包 grep  │ §五、§九   │
  │     │                   │ 可算（§5.2, §9 Step2)                           │            │
  ├─────┼───────────────────┼─────────────────────────────────────────────────┼────────────┤
  │ 5   │ Verification      │ 通过。单 target 必填，空 reject(§7.2-5/6)       │ §七        │
  │     │ 无法定位 target?  │                                                 │            │
  ├─────┼───────────────────┼─────────────────────────────────────────────────┼────────────┤
  │ 6   │ Autocompact       │ 通过。投影随 §9 重生成；恢复契约=2 文件≤35      │ §十一、§十 │
  │     │ 后无法恢复？      │ 行；S8 实跑闭合                                 │ 四         │
  ├─────┼───────────────────┼─────────────────────────────────────────────────┼────────────┤
  │     │ Agent 自改事实无  │ 通过。source                                    │            │
  │ 7   │ 法识别？          │ 封闭词表+append-only+出生态规则+sweep           │ §四        │
  │     │                   │ git-diff(§4.4)                                  │            │
  ├─────┼───────────────────┼─────────────────────────────────────────────────┼────────────┤
  │     │ Invalid 理论仍可  │ 通过（约定级）。Blocked=tainted×impl-map;PROMPT │            │
  │ 8   │ 改相关代码？      │  禁令+verifier diff grep+Judge                  │ §十        │
  │     │                   │ 抽查（§十）。残余风险：P0 无物理拦截，已声明    │            │
  ├─────┼───────────────────┼─────────────────────────────────────────────────┼────────────┤
  │ 9   │ 引入了不必要组件  │ 通过。7 能力逐项映射 ≥1 scenario(S              │ §十五      │
  │     │ ？                │ 场景映射表见§十四）；无孤儿项                   │            │
  ├─────┼───────────────────┼─────────────────────────────────────────────────┼────────────┤
  │ 10  │ 能用 B1P0 Swerve  │ 通过。八场景均已逐步闭合（§十四）               │ §十四      │
  │     │ 验证？            │                                                 │            │
  └─────┴───────────────────┴─────────────────────────────────────────────────┴────────────┘

  READY。10/10，无必须先修正的设计缺口。 唯二显式接受的 P0 级残余风险（写入 protocol
  防遗忘）:(a) status/投影写入约束靠"sweep 检测+自愈"而非物理只读；(b) Blocked 靠"PROMPT+diff
  抽查"而非自动拦截。两者升级为 P1 候选。
  