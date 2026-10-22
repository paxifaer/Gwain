# 接口对齐与 schema 同源

「前端按钮与后端不一致」的根治办法是双端只有一份 schema 事实源，其余产物全部生成。

## 三件套（推荐组合）

1. **后端导出 OpenAPI**：Rust/Axum 用 `utoipa`，给请求/响应定义 `ToSchema` 结构体，路由加 `#[utoipa::path]`，暴露 `GET /api/openapi.json`。
2. **前端生成类型**：`openapi-typescript` 从 `openapi.json` 生成 `*.gen.ts`（文件头带 `generated` 标记）；业务代码 import 生成类型，禁止手写同名接口。
3. **运行时校验**：`zod`（或同类）校验响应，字段缺失/类型不符立刻报错，禁止 `undefined` 静默渲染。

## 漂移门禁

一条脚本管住三方：重新生成 → 与提交的产物 diff → 非空即红。

```bash
# 生成产物入库；CI 或本地门禁脚本做等价检查
cargo test -p <backend> export_openapi     # 写 openapi.json
bun run openapi:gen                        # 写 apps/web/**/*.gen.ts
git diff --exit-code openapi.json apps/web/src/**/*.gen.ts
```

验收要求演示一次红灯：故意改一个后端字段 → 门禁报红 → 恢复。

## 错误语义对齐清单

- 状态码与业务错误字段（`ok` / `error`）分工明确，不混用。
- 超时、忙、关闭三类失败可区分（如 504 / 409 / 503），前端各有对应文案。
- 响应里的计数类字段定义唯一计数对象（例如「停止的播报条数」到底按 occurrence 还是按播放段计），并写进契约表。
- 幂等语义明确：重复点击、重复调用返回什么。

## 部署一致性

- 双组件（前端包 + 后端包）版本号一起核对后才能宣布上线；单侧成功不算成功。
- 运行中进程的可执行文件替换前先停服务（`Text file busy` 教训）。
- 上线后用真实接口冒烟（按钮级调用一次成功 + 一次预期失败），再向用户报「已部署」。
