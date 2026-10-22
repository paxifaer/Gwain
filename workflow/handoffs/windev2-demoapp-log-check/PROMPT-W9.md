# PROMPT-W9 — demoapp TLS 修复经过白话文档撰写 (kimi-k3, write single doc)

```
Before doing anything else:
1. Read /home/wangdang/work/ai-stack/code/Gawain/workflow/bootstrap.md
   (and rule-map.md if it points you to more files).
2. Classify this task per bootstrap.md's three questions and follow every
   rule that applies.
3. You run non-interactively. Open judgment calls → record an ESCALATE in
   your final message; never try to ask the user.
4. Your write-set is exactly the files declared in this prompt. Report every
   file created or modified, with line numbers, in your final message.

HEAD-guard: before any git touchpoint, run `git log --oneline -1 && git status --short`.

model_selection:
  model: t9s/kimi-k3
  mode: automatic
  reason: documentation
  permission_mode: bypassPermissions   # write-set = single new doc file, non-destructive
```

---

You are **W9** — a one-shot, **documentation** worker. demo app 的 TLS 修复经过 5 个 worker（W1-W5 + W8 skyline 审查）协作完成。用户要求把整个排查经过 + 报错原因整理成一份**白话能读懂**的文档（不要堆术语、不要规格号、用类比和故事讲清楚），给非该领域专家的同事看。

## CRITICAL: NO PARTIAL RETURNS

文档必须按输出契约完整交付，不要 outline/status update。3-min no-response = ESCALATE + move on。

## Normative reads（必读全部）

1. `/home/wangdang/work/ai-stack/code/Gawain/workflow/handoffs/windev2-demoapp-log-check/out-W1.log` — W1 现场 baseline
2. `/home/wangdang/work/ai-stack/code/Gawain/workflow/handoffs/windev2-demoapp-log-check/out-W2.log` — W2 找到根因（**核心**）
3. `/home/wangdang/work/ai-stack/code/Gawain/workflow/handoffs/windev2-demoapp-log-check/out-W3.log` — W3 代码审查
4. `/home/wangdang/work/ai-stack/code/Gawain/workflow/handoffs/windev2-demoapp-log-check/out-W4.log` — W4 实施 P0（tracing + JS bug fix）
5. `/home/wangdang/work/ai-stack/code/Gawain/workflow/handoffs/windev2-demoapp-log-check/out-W5.log` — W5 修 `client_dir()` USERPROFILE 兜底
6. `/home/wangdang/work/ai-stack/code/Gawain/workflow/handoffs/windev2-demoapp-log-check/out-W8.log` — W8 skyline 审查（skyline 也有相同 bug，引用到后续待办）
7. `/home/wangdang/work/ai-stack/code/Gawain/workflow/bootstrap.md` — workflow rules

## Write-set

**只写这 1 个新文件**：
- `/home/wangdang/work/ai-stack/code/frontend/robot-app-platform/docs/guides/demo-tls-fix-2026-08-18.md`

如果该路径不存在父目录，先 `mkdir -p`。**不要修改任何其他文件**。

## 文档风格要求（最重要）

1. **白话能读懂**：给一个不熟悉 Tauri / rustls / Tauri invoke 错误传播链的工程师同事看，他能看懂"问题是什么 / 怎么排查 / 根因是什么 / 怎么修的"。
2. **用类比 + 故事**，不要堆术语。比如：
   - 把 `HOME` env var 比作"程序找文件的地址簿"
   - Windows 不自动设 HOME 比作"Windows 程序员习惯用另一个名字（USERPROFILE）记地址，但代码假设大家都用 Linux 习惯的 HOME"
   - `String(error)` 把 plain object 变成 `"[object Object]"` 比作"中文错误消息被一个只懂英文的翻译器当成不认识的对象，输出'对象对象'"
   - 服务器日志 0 条记录比作"快递员根本没出门，你查快递公司发货记录当然找不到"
3. **避免规格号轰炸**：行号/SHA1/版本号可以提，但**只提关键一两个**（比如"`argo_tls.rs` 第 60 行附近"），不要每个细节都标行号。
4. **结构清晰**：用 H2/H3 分章节，每章开头一句话点题。
5. **时间线讲排查**：5 个 worker 怎么一棒接一棒找到根因的。
6. **保持中文**，全篇中文。
7. **长度 1500-2500 字**（不要太长，简洁但有料）。

## 文档大纲（建议但不强制）

```markdown
# demo app TLS 连接失败排查与修复（白话版）

> 日期：2026-08-18
> 涉及机器：windev2（开发机） → SP000065（机器人 192.168.110.65:50053 mTLS）
> 关键代码：`apps/demo/src-tauri/src/argo_tls.rs` + JS invoke 路径

## 一句话总结

demo app 在 Windows 上连机器人 mTLS 失败，根因是代码假设 Linux 风格的 `HOME` 环境变量在 Windows 上也存在，找不到证书直接报错；同时 JS 把真实错误吞成 `[object Object]`，排查难度被放大。修复用了 5 步：找现场 → 找根因 → 看代码缺什么 → 加日志 + 修 JS bug → 修环境变量兜底。验证：用户重连后日志显示 `client_dir resolved dir=C:\Users\jack\.argo-tls` + `gateway_mtls_proxy ok status=200`。

## 故障现象

（用户在 UI 看到什么 — "TLS handshake failed. Choose to abort or fall back to plaintext." reason 字段 `[object Object]`。机器人连不上。）

## 排查经过（5 个 worker 的故事）

### W1：看现场（17:14 出发，17:15 回来）

派 W1 去 windev2 上看：Tauri 进程在不在跑？证书文件在不在？TCP 通不通？OS 层 TLS 握手能不能成？

W1 回来报告：
- Tauri 进程在跑（debug build，16:50 启动）
- 证书全在 `~/.argo-tls/` 下，ca.crt SHA1 = `2C7A91D4...`，client.crt 有效期 2026-08-14 → 2027-08-14
- TCP 通到 `192.168.110.65:50053`，OS 层 SslStream 握手 TLS_OK
- 但 `argo_tls.rs` 全文 0 条 log — 当前 debug 进程压根没写过 TLS 日志
- robot-config.json 显示 `robot_ip` 是 `192.168.100.100:50051`（其实不通的那个 IP+端口）

一句话：现场证都在，但代码不打日志，看不到内部出了什么。

### W2：找根因（17:08 出发，17:34 回来，跑了 12 分钟）

用户改用 `192.168.110.65:50053`（W1 确认能通的那个）重试，还是失败。派 W2 看最新 log + 服务端 log + CA 指纹对比。

W2 回来报告（铁证）：
- 服务端 SP000065 自 16:40 启动后 **0 条 TLS 连接日志** — 客户端的请求根本没出门
- 客户端证书、CA、网络、服务器全健康 — W2 用同一组证书离线跑 reqwest+rustls 探针，HTTP 200 成功
- **决定性发现**：`argo_tls.rs` 第 60 行附近 `client_dir()` 函数：
  ```rust
  let home = std::env::var("HOME").unwrap_or_else(|_| ".".to_string());
  PathBuf::from(home).join(".argo-tls")
  ```
  代码假设 `HOME` 环境变量一定存在。Linux/macOS 是这样，**Windows 不是** — Windows 用 `USERPROFILE`，注册表里压根没有 `HOME` 这个键。`HOME` 取不到时代码回退到 `"."`（当前工作目录），那里当然没有 `.argo-tls/` 目录 → `apply_mtls` 立刻报错 "mTLS client cert missing"，请求没出门。

一句话：Windows 不像 Linux 自动设 HOME，代码假设错了，证书找不到，请求没出门，服务器当然没记录。

### W3：审查代码（17:20 出发，17:23 回来，3 分 28 秒）

派 W3 看代码日志充足性 — 不是现场查，是查"如果以后再出问题，能不能从日志看出来"。

W3 回来报告：
- `argo_tls.rs` 1179 行生产代码，**0 条 tracing/eprintln/app_data_log** — 所有 TLS 决策点全静默
- `AppError::RequestFailed` 序列化成 plain object `{name, message}`，但**没有 cause 字段** — 错误链被 `format!("...{e}")` 拍平丢失
- JS 侧 5 处 `String(error)` bug，把 Tauri invoke 拒绝返回的 plain object 变成 `"[object Object]"` — 这就是 UI 显示 `[object Object]` 的原因
- 服务端 `argo-gateway-server` 有 tracing 基建，但 TLS accept 路径 0 条 log

一句话：代码里外都不打日志，错误链又在传播过程中被吃掉，所以现场什么都看不到。

### W4：加日志 + 修 JS bug（17:30 出发，17:37 回来，6 分 42 秒）

派 W4 实施 W3 推荐的 P0 方案：
- 在 `argo_tls.rs` 加 `tls_log` 函数，写到 `~/.argo-tls/argo-tls-debug.log`，10+ 决策点埋点（CA 加载、identity 构建、URL 解析、reqwest 错误等）
- `AppError::RequestFailed` 加 `cause: Option<String>` 字段 + `request_failed_with_cause` helper，保留 `{:?}` Debug 链
- JS 侧加 `extractInvokeErrorMessage` helper + 5 处 `String(error)` 修复
- `cargo check` 2.55s 0 错误

一句话：把眼睛装上（log），把错误链补全（cause），把 JS 翻译器修对（helper）。

### W5：修根因（17:36 出发，17:36 回来，50 秒）

派 W5 修 `client_dir()` 的 HOME bug — 1 行 patch：
- 优先 `USERPROFILE`（Windows）→ 然后 `HOME`（Linux/macOS）→ 最后 `"."` 兜底
- 加 `tls_log` 记录解析出的路径，下次出问题能直接看到
- `cargo check` 2.08s 0 错误

一句话：把"找地址簿"的逻辑改成"先翻 Windows 的 USERPROFILE，再翻 Linux 的 HOME"。

### 同步代码到 windev2 + 释放端口

W4/W5 改的是 Linux 工作站的代码，windev2 上跑的是独立副本 — 用 scp 把 5 个改动文件同步过去。同时 windev2 上残留的 vite/bun 孤儿进程占着 1420 端口（Tauri dev 默认端口），杀掉释放。

### 验证

用户在 windev2 上 `just dev-tauri-demo` 重新编译 + 启动，点 TLS 连接。查 `C:\Users\jack\.argo-tls\argo-tls-debug.log`：
- `client_dir resolved dir=C:\Users\jack\.argo-tls` ✓（W5 修复生效，找到了正确路径）
- `load_client_identity ok certs=1` ✓
- `client_ca_cert_pem hit=ca_crt path=C:\Users\jack\.argo-tls\ca.crt bytes=615` ✓
- `apply_mtls ok ca_loaded bytes=615` ✓
- `build_http_client ok use_tls=true` ✓
- `gateway_mtls_proxy ok status=200` ✓ — TLS 通了，HTTP 200！

只有 `FrontendRobotControlService/DebugQuery` 返回 status=500，那是业务层错误（gRPC 服务端处理时出错），不是 TLS。

## 根因白话解释

（展开讲 3 层根因）

### 第 1 层：环境变量假设错了

程序要找证书文件，路径是 `~/.argo-tls/ca.crt`。代码用 `HOME` 环境变量来代表 `~`。Linux/macOS 自动设 `HOME`，但 Windows 不设 — Windows 用 `USERPROFILE`。代码没考虑这点，取不到 `HOME` 时退而求其次用当前工作目录 `"."`，但工作目录下没有 `.argo-tls/` → 找不到证书。

类比：代码假设"打开地址簿第一个标签页就一定能找到地址"，但 Windows 的地址簿第一页叫另一个名字（USERPROFILE），代码没翻那一页，直接默认地址簿是空的。

### 第 2 层：真实错误被 JS 翻译器吃了

Tauri 拒绝 invoke 时，Rust 侧返回的是 `AppError::RequestFailed { message: "mTLS client cert missing..." }`，序列化成 plain object `{name: "RequestFailed", message: "..."}`。

JS 侧 catch 这个错误后想做字符串化展示，代码是：
```js
const message = error instanceof Error ? error.message : String(error);
```

`error instanceof Error` 是 false（plain object 不是 Error 实例），走到 `String(error)` 分支。`String({name: "RequestFailed", message: "..."})` 在 JS 里就是 `"[object Object]"` — 对象的默认 toString。

类比：中文错误消息被一个只懂英文的翻译器当成不认识的对象，输出"对象对象"，意思全丢了。

### 第 3 层：没日志让现场变成黑盒

`argo_tls.rs` 1179 行，0 条 tracing/eprintln/app_data_log。所有 TLS 决策点（CA 加载、identity 构建、URL 解析、reqwest 错误等）失败时直接 `?` 或返回 `None`，不留任何痕迹。所以 W1 去现场只能看到"证书文件在、TCP 通、OS 握手成"，但不知道 Tauri 进程内部走到哪一步就退出了。

类比：快递员出门前就因为找不到送货单放弃了，但他没在派件系统里登记，你查物流当然查不到。

## 修复内容白话讲

### 修复 1：找地址簿逻辑改成跨平台

`client_dir()` 改成：先翻 Windows 的 `USERPROFILE`，再翻 Linux 的 `HOME`，都没有再退到当前目录。还加了一行 `tls_log` 把解析出的路径写进日志，下次出问题一眼能看见。

### 修复 2：把眼睛装上

加了 `tls_log` 函数，写到 `~/.argo-tls/argo-tls-debug.log`。在 10+ 关键决策点埋点：CA 从哪加载、加载成功没、URL 解析成什么、reqwest 发送成功没、HTTP 状态码是多少。下次再出问题，看这个日志就能定位到哪一步出问题，不用再派人 SSH 上 windev2 现场查。

### 修复 3：错误链补全 + JS 翻译器修对

Rust 侧 `AppError::RequestFailed` 加了 `cause: Option<String>` 字段，把底层错误的 `{:?}` Debug 字符串保留下来，不再被 `format!("...{e}")` 拍平。JS 侧加 `extractInvokeErrorMessage` helper：如果是 Error 实例，取 `message`；如果是 plain object，取 `message` 字段；如果都没有，JSON.stringify 兜底。5 处 catch 块全部换成这个 helper。UI 上的 `[object Object]` 不会再出现，会显示真实错误消息。

## 经验教训

1. **跨平台代码不要假设环境变量**：`HOME` 是 Unix 概念，Windows 不保证存在。要取 home 目录，要么 `USERPROFILE` + `HOME` 双兜底，要么用 `dirs::home_dir()` 这种跨平台 crate。
2. **错误传播链要保留 cause**：每层 catch 都要把底层错误的 Debug/Display 串起来，否则到了 UI 就只剩一个顶层 message，丢失所有上下文。
3. **Tauri invoke 返回 tagged enum 时，JS 不能用 `String(error)`**：要写 `extractInvokeErrorMessage` 这种 helper，识别 `{name, message}` 形状。
4. **关键路径必须有日志**：TLS 握手、关键 IO、关键决策点都要埋点。出问题时没有日志就只能盲猜，浪费几个 worker 几十分钟。
5. **加日志不算工程难点，但能省下后续 80% 的排查时间**：W4 加 log 用了 6 分钟，W2 找根因用了 12 分钟 — log 提前埋好，根因现场就暴露。

## 后续待办

### skyline 也有同样 bug（W8 已审查）

W8 审查了 skyline studio 的代码，发现：
- **skyline `argo_tls.rs` 第 60 行附近 `client_dir()` 与 demo 修复前完全一致** — 同样的 HOME bug，需要复制 W5 修复
- **skyline `argo_tls.rs` 全文 0 tracing** — 与 demo pre-W4 一致，需要加 `tls_log`（建议复用 skyline 已有的 `runtime_log/` 模块，比 demo 简陋版强）
- **skyline JS 侧不需要修 `String(error)` bug** — skyline Rust 命令返回 `Result<_, String>` 而非 tagged enum，`String(error)` no-op 正确；而且 skyline 复用 `packages/gateway-client`，已经自动获得 W4 的 `extractInvokeErrorMessage` helper
- **skyline 没有 `AppError`** — 用 `Result<_, String>`，所以 W4 的 `cause` 字段修复不适用

下次派 W10 处理 skyline 的 P0：复制 W5 的 USERPROFILE 兜底 + 加 TLS log。

### 其他遗留

- `argo-tls-debug.log` 并发写入字符交错（多个请求同时写文件，无文件锁）— 不影响业务，日志可读性差，P2 优化项
- 服务端 `argo-gateway-server` TLS accept 路径 0 log — W3 报告里有建议加 `tracing-log` bridge + middleware 记录 peer IP/SNI/cipher，留 P1
```

## Constraints

- **只写 1 个新文件**（`docs/guides/demo-tls-fix-2026-08-18.md`）
- 不修改任何现有文件
- 不创建除该文件外的其他新文件
- 全篇中文
- 1500-2500 字
- 不跑 cargo/build/test
- 不 SSH
- 不 git commit/push
- 3-min no-response = ESCALATE

## Output contract (Chinese, <300 words)

### 1. 文档创建

- 文件路径
- 总字数
- 章节大纲（H2 列表）

### 2. 关键引用

列出文档中引用的 W1-W8 报告关键证据点（每条 1 句话）

### 3. ESCALATEs

如有

End with: `Elapsed: <m>min<s>s`.

## Don't

- Don't write files outside the declared write-set (1 file only).
- Don't modify any existing file.
- Don't run cargo/build/test/just.
- Don't SSH to any host.
- Don't git commit/push.
- Don't ask the user any questions.
- Don't dispatch sub-agents.
