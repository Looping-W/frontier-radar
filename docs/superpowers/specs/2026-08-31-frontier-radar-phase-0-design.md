# Frontier Radar Phase 0 设计

## 范围

Phase 0 仅为 Frontier Radar 建立 CLI 基础：本机 MySQL 配置与连接、
Alembic 迁移基础设施、两个 Typer 命令、测试、Ruff 与项目文档。本阶段不实现
采集器、Agent 行为、Web API、前端、定时任务或业务领域数据表。

## 项目结构

项目采用 `src/` 布局，应用包名为 `frontier_radar`。Phase 0 中各模块保持精简，
职责如下：

- `core`：使用 Pydantic 读取并校验 `MYSQL_*` 环境变量。
- `db`：创建 SQLAlchemy Engine 和会话工厂，并提供 Alembic 所需的元数据基类。
- `repositories`：仅处理数据库访问。初始健康检查仓储执行 `SELECT 1`。
- `services`：处理应用行为。健康检查服务将应用状态和数据库状态组合为 CLI 可用的结果。
- `cli`：仅定义 Typer 命令与输出展示；命令中不包含 SQL 或业务逻辑。

未来的 `models`、`schemas`、`collectors` 和 `agents` 分层会在 `AGENTS.md`
中说明，但 Phase 0 不创建或填充这些模块。

## 配置与数据库

`.env.example` 说明 `MYSQL_HOST`、`MYSQL_PORT`、`MYSQL_DATABASE`、
`MYSQL_USER` 和 `MYSQL_PASSWORD`，并以 `frontier_radar` 作为示例数据库名。
不会创建或提交真实 `.env`；应用仅从进程环境变量读取配置，用户可自行通过本地
环境工具加载变量。

本机 MySQL 数据库由用户单独创建。SQLAlchemy 使用 MySQL PyMySQL 驱动，并通过
独立的会话工厂获取数据库会话。今后所有数据表结构变更必须通过 Alembic revision
执行。

## 命令与行为

`fradar health` 调用 `HealthService`，再由服务调用数据库健康检查仓储。命令输出
应用状态和数据库状态。配置有效且 `SELECT 1` 成功时，退出码为 0；配置缺失、连接
或查询失败时，输出简洁的错误原因并以非零退出码结束。

`fradar db-upgrade` 调用 Alembic，将已配置的数据库升级到 `head`。初始 Alembic
revision 为无操作的基线迁移：它建立迁移版本追踪，不创建 Phase 1 及以后阶段的表。

## 错误处理与测试策略

配置错误和数据库连接错误在服务层形成统一的健康检查结果，使 CLI 可以一致地展示。
数据库健康检查仓储负责处理 SQLAlchemy 相关异常。

Pytest 通过可替换的仓储依赖，测试健康检查命令与服务在数据库可用、不可用两种状态
下的行为，不要求测试机器运行本机 MySQL。Ruff 对应用代码和测试代码执行静态检查。

## 文档与仓库

根目录 `AGENTS.md` 按用户提供的项目规则原样写入。
`docs/PROJECT_PLAN.md` 记录用户提供的 Phase 0–7 路线图。
`docs/PROJECT_STATUS.md` 必须以以下内容作为初始状态：

`Current phase: Phase 0 — CLI initialization`

项目会先初始化为本地 Git 仓库；确认 GitHub 身份验证可用后，再创建并推送名为
`frontier-radar` 的公开 GitHub 远程仓库。
