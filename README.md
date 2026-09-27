# Frontier Radar

一个 CLI-first 的本地个性化技术情报工具：采集 Hacker News 与 arXiv，保留原始快照，离线
清洗去重，按兴趣与反馈进行确定性排序，并让受限只读 Agent 生成日报。

## 快速开始

项目需要 Python 3.11+ 与本机 MySQL。复制 `.env.example` 的字段到你自己的 `.env` 并填写本地
配置；真实 `.env` 和 API key 不应提交到 Git。

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\fradar.exe db-upgrade
```

直接运行 `fradar` 会打开 Textual TUI：

```powershell
.\.venv\Scripts\fradar.exe
```

已有命令式入口保持可用，例如：

```powershell
.\.venv\Scripts\fradar.exe health
.\.venv\Scripts\fradar.exe refresh
.\.venv\Scripts\fradar.exe digest --limit 5 --lang zh
```

## TUI

TUI 默认使用中文阅读文案，并只接受明确的英文斜杠命令。输入 `/lang en` 可切换为英文，输入
`/lang zh` 切回中文；语言只在当前会话有效。`/digest` 会按当前界面语言直接生成对应语言的策展
概览与推荐理由，来源文章标题、URL、模型名和 ID 等技术信息保持原样。

输入 `/help` 查看完整清单，`Ctrl+P` 打开命令面板，`Ctrl+B` 展开推荐、当前会话日报、反馈和
执行记录抽屉，`Ctrl+L` 回到输入框。抽屉正文支持鼠标滚轮、方向键、PageUp/PageDown 和
Home/End，数据库与模型状态固定在底部。

Phase 6 不把普通自然语言解释为动作，不执行模型生成的 Shell/SQL/Python/CLI 字符串，也不保存
会话或日报历史。`/feedback reset` 必须在界面内再次确认。命令由 TUI 直接调用 service 层；
Phase 4 策展 Agent 的工具继续保持只读。

## 验证

```powershell
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
```
