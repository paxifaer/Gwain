# SPEC-3 — demo app + argogateway-server log/tracing 充足性审查 (read-only code review)

## Goal

W1 + W2 已确认：
- windev2 demoapp (Tauri 2 + React) 点击 TLS 连接 SP000065:50053 失败，UI 显示 "TLS handshake failed. Choose to abort or fall back to plaintext." reason 字段 `[object Object]` — 真实 TLS 错误被吞。
- `argo_tls.rs` (apps/demo/src-tauri/src/) **零 tracing**。
- JS 路径 `String(error)` 把 Tauri invoke 拒绝返回的 plain object (`{name, message}`) 变成 `"[object Object]"`。
- 服务端 `argo-gateway-server` 在 prior session 报告 "NO new TLS attempts after 08:40 UTC restart"，但实际是否打 log、打哪些 log 尚未系统审查。

用户最新指令："派人你看看代码里面的 log 是不是还不够完善,是不是需要加一些"。

W3 是 **read-only 代码审查** worker：审查现有 log/tracing 覆盖度，产出**具体建议**（哪个文件、哪个函数、哪一行、建议加什么样的日志调用）。**不写代码、不修改文件**。

## Why

W1/W2 在 production runtime 现场找不到错误，因为代码根本不打 log。在加 tracing + rebuild 之前，先系统盘点：
1. **客户端 Rust 侧**（`argo_tls.rs` 等）：mTLS 握手路径关键决策点（CA 加载、identity 构建、URL 解析、reqwest 错误）是否有任何 log？
2. **客户端 JS 侧**（transport.ts/robot-sdk.ts/manage-robot.tsx）：invoke 失败时错误对象如何传播？`String(error)` bug 在哪些位置？
3. **服务端 Rust 侧**（argo-gateway-server）：TLS accept、cert verify 失败、handshake error 是否有 log？
4. **既有日志基建**（`tauri-app-log` crate + `append_app_data_log_line_with_limit` + `DOUBAO_DEBUG=1` eprintln 模式）：能否复用做 TLS 调试？release 构建（`windows_subsystem = "windows"`）stderr 是否丢失？

W3 输出一份逐文件、逐函数、逐行号的日志充足性矩阵，供 orchestrator 决定下一步是否派 W4 加 tracing + rebuild。

## Inputs

- 客户端代码根目录：`/home/wangdang/work/ai-stack/code/frontend/robot-app-platform/`
  - `apps/demo/src-tauri/src/argo_tls.rs` — mTLS 客户端核心
  - `apps/demo/src-tauri/src/error.rs` — AppError serde 表示
  - `apps/demo/src-tauri/src/lib.rs` — Tauri 命令注册 + CryptoProvider install + 既有 debug log 命令
  - `apps/demo/src-tauri/Cargo.toml` — rustls/reqwest/tauri-app-log 依赖
  - `crates/tauri-app-log/src/lib.rs` — app_data_dir 日志基建
  - `packages/gateway-client/src/lib/transport.ts` — invokeMtlsFetch + JS error 传播
  - `apps/demo/src/services/robot-sdk.ts` — RobotSDK.connect catch
  - `apps/demo/src/routes/manage-robot.tsx` — handleAddRobot catch
  - `apps/demo/src/components/manage-robot/TlsFailDialog.tsx` — UI 静态串
- 服务端代码根目录：`/home/wangdang/work/ai-stack/code/ArgoGateway/src/argo-gateway-server/`
  - `src/main.rs` — 服务入口（已知 line 135 有 CryptoProvider install）
  - `src/connect.rs` 或同类文件 — TLS accept 路径
  - `src/direct_service.rs` 或同类 — 直接 mTLS 服务
  - `Cargo.toml` — tracing/log 依赖
- W1 报告：`/home/wangdang/work/ai-stack/code/Gawain/workflow/handoffs/windev2-demoapp-log-check/out-W1.log`
- W2 报告（若已完成）：`/home/wangdang/work/ai-stack/code/Gawain/workflow/handoffs/windev2-demoapp-log-check/out-W2.log`

## Constraints

- **READ-ONLY**：不修改任何代码文件、不修改 cargo 配置、不 git 操作。
- 不 SSH 到 windev2 或 SP000065（W3 纯代码审查，不查 runtime 状态）。
- 不调度子 agent。
- 3-min no-response = ESCALATE + move on。
- 不臆造：找不到的文件/函数明说 "NOT FOUND"。
- 建议具体到行号 + 建议的 tracing/eprintln/log 调用文本，不要泛泛说"应该加日志"。

## Output contract (Chinese, <800 words)

### 1. 客户端 Rust 侧日志现状

逐文件列出：
- 文件路径 + 关键函数 + 起止行号
- 当前 log 状态（无 / eprintln / tracing / app_data_log）
- 关键决策点列表（CA 加载、identity 构建、URL 解析、reqwest 调用、错误返回）
- 哪些决策点缺日志 + 建议加什么（具体到 `tracing::info!("...")` 或 `eprintln!("[tls] ...")` 文本）

重点审查 `argo_tls.rs`：
- `apply_mtls` (line ~142)
- `build_http_client` (line ~180)
- `client_ca_cert_pem` (line ~115)
- `gateway_mtls_proxy` (line ~300)
- `gateway_mtls_proxy_stream` (line ~472)
- `forward_mtls_stream` (line ~383)
- `parse_allowed_gateway_url` (如果存在)

### 2. 客户端 JS 侧错误传播链

逐文件列出：
- `transport.ts` line ~362 invoke 失败处：error 是什么形状？catch 块如何处理？
- `robot-sdk.ts` line ~136 `String(error)` bug：建议改为什么？（如 `error?.message ?? JSON.stringify(error)`）
- `manage-robot.tsx` line ~523 同样 bug
- `TlsFailDialog.tsx` reason prop 渲染处
- 列出所有 `String(error)` / `error.message` 位置 + 建议改法（具体代码片段）

### 3. 服务端 Rust 侧 TLS accept 路径日志

逐文件列出：
- `argo-gateway-server/src/main.rs` — TLS listener 启动 + accept loop 是否有 log
- `connect.rs` / `direct_service.rs`（或同类）— TLS 握手、cert verify 失败、IncompatibleVersions、alert 是否有 log
- rustls 0.23 server-side是否有自定义 Logger 实现？
- 服务端 `RUST_LOG` 环境变量是否能打开 rustls 内部日志？
- 列出关键决策点缺日志 + 建议加什么

### 4. 既有日志基建可用性

- `tauri-app-log` crate 的 `append_app_data_log_line_with_limit` 签名 + 现有调用方
- `lib.rs` 既有 `DOUBAO_DEBUG=1` eprintln 模式（如 `[doubao] ...`）— 列出所有出现位置
- `apps/demo/src-tauri/Cargo.toml` 是否有 `windows_subsystem = "windows"` 配置？如有，release build 下 stderr 会丢失，eprintln 不可见 — 建议 TLS log 必须走 app_data_log 文件而非 eprintln。
- `tracing` / `tracing-subscriber` 依赖是否在 Cargo.toml？是否初始化？

### 5. 推荐方案矩阵

简短列出 W4 应该加哪些 tracing（按优先级）：
- P0：客户端 `argo_tls.rs` 关键决策点 tracing（CA 加载结果、identity 构建结果、URL 解析结果、reqwest 错误返回点）
- P0：JS 侧 `String(error)` bug 修复（3 处）
- P1：服务端 TLS accept 路径 tracing
- P2：客户端 release 构建日志走 app_data_log（如果 windows_subsystem 隐藏 stderr 确认）

### 6. ESCALATEs

所有未找到的文件/函数、不明确的代码路径、判断分歧。

End with one line: `Elapsed: <m>min<s>s`.

## Verification

W3 报告 IS 审查交付物。orchestrator 读后决定：
- 直接派 W4 实施 P0 tracing + JS bug fix + rebuild
- 或先派 verifier 复核 W3 的逐行号建议是否准确
- 或先等 W2 完成，根据 W2 服务端 log 证据交叉确认
