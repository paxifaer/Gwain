# 14 个历史坑 → 条款对照矩阵（回放验收 C7）

来源：2026-10-21 「关闭音响」开发会话复盘。每个坑必须有条款管住，否则 skill 不合格。

| # | 坑（实证） | 管住它的条款 | 位置 |
|---|---|---|---|
| 1 | 「关闭音响」被自行解释成「抑制本次触发」，用户未批准 | 阶段 0 歧义选择题、禁止自行选择；阶段 2 批准门 | SKILL.md |
| 2 | 「对面机器」被自行解释成本机 | 阶段 0 目标机器/范围确认 | SKILL.md |
| 3 | 405 被直接诊断为「浏览器缓存」，未抓真实请求 | 对抗取证顺序：先抓请求再定因；示例反面教材 | examples/close-audio-chain.md |
| 4 | mock 忙文案批量替换误改 preview 分支 | 契约表一接口一行；各接口独立契约测试；改动后无关接口回归 | templates/contract-table.md + templates/test-boundaries.md |
| 5 | `stopped:2` 语义不清（计数对象未定义） | 契约表「计数定义」写进响应栏 | templates/contract-table.md |
| 6 | `Text file busy` 导致半部署仍报上线 | 部署一致性：双组件版本核对、停服务再替换、真接口冒烟后才报上线 | references/api-alignment.md |
| 7 | 喂数器进程活着但端点错、无数据 | 「进程活着 ≠ 链路可用」；源→订阅→界面全链路验证 | references/evidence-levels.md |
| 8 | 假数据只口头披露，用户误当真 | mock 边界表 + 数据来源持续标识；mock 只限 L0-L1 | templates/test-boundaries.md + references/evidence-levels.md |
| 9 | 切真实数据源未验证真帧就宣称完成 | 阶段 3：切源后核验来源、新鲜时间、真实观测；完成态只写 READY_FOR_USER_ACCEPTANCE | SKILL.md |
| 10 | 「日志无 warn」被当成「循环健康」 | 硬性推论禁令 1：无报错 ≠ 正向证据 | references/evidence-levels.md |
| 11 | `remote_controller.connected` 直接称作「急停手表」 | 契约字段语义确认（计数定义/错误语义栏）；硬件映射需 L4 受控变化对照 | templates/contract-table.md + templates/test-boundaries.md |
| 12 | 告警 ACTIVE 被当成「物理已静音」 | 硬性推论禁令 2：软件状态不推断物理效果 | references/evidence-levels.md |
| 13 | 管道过滤吞掉命令退出码，失败仍报绿 | 假绿拒绝规则：保留原始退出码，非零即 FAIL | references/evidence-levels.md |
| 14 | 明知工具策略禁止仍原样重试同一调用 | 红旗：被拒绝/违规的调用不得原样重试，改方案或报告阻塞 | SKILL.md |

## 回放方法

验收时抽查任意 3 行：按条款要求产出对应产物（表、证据、门禁红灯演示），缺任何一样即该行 FAIL。
