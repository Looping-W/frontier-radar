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

命令面板第一行显示英文命令，第二行按界面语言说明用途。带参数的命令只预填前缀，
需要自行填写查询词、名称或文章编号。

### TUI 命令清单

以下命令在 TUI 输入框中输入，不是在 PowerShell 中执行。
大写参数是占位符，使用时替换成实际值；`[LIMIT]` 表示可选参数。

| 命令 | 作用与参数 |
| --- | --- |
| `/help` | 查看白名单命令清单 |
| `/health` | 检查应用与数据库连接状态 |
| `/model` | 查看已保存的模型配置，不显示 API key |
| `/collect hn` | 采集 Hacker News 热门条目并保存原始响应 |
| `/collect arxiv QUERY` | 按 QUERY 采集近期 arXiv 论文并保存原始响应，例如 `/collect arxiv AI agent` |
| `/collect all` | 采集 HN 和三组固定 arXiv 查询 |
| `/normalize` | 从已保存快照离线解析、标准化与去重，生成文章记录 |
| `/rank` | 根据当前兴趣与反馈重算并保存排名，显示正分且未反馈的推荐 |
| `/refresh` | 依次执行默认来源采集、清洗与排序，不生成日报 |
| `/digest [LIMIT]` | 根据当前语言生成日报；LIMIT 是候选文章上限，默认 10，范围 1–20 |
| `/topics` | 查看默认画像的主题与手动权重 |
| `/topic add WEIGHT NAME` | 添加主题；同名主题已存在时更新其权重 |
| `/topic update WEIGHT NAME` | 更新已有主题的权重，主题不存在时失败 |
| `/topic remove NAME` | 删除已有主题 |
| `/keywords` | 查看默认画像的关键词与手动权重 |
| `/keyword add WEIGHT NAME` | 添加关键词；同名关键词已存在时更新其权重 |
| `/keyword update WEIGHT NAME` | 更新已有关键词的权重，关键词不存在时失败 |
| `/keyword remove NAME` | 删除已有关键词 |
| `/feedback` | 查看反馈记录，包括文章标题、反馈选择与时间 |
| `/like ARTICLE_ID` | 标记喜欢并立即重排；ARTICLE_ID 是文章编号 |
| `/dislike ARTICLE_ID` | 标记不感兴趣并立即重排 |
| `/undo ARTICLE_ID` | 撤销该文章的已有反馈并立即重排 |
| `/feedback reset` | 弹窗确认后清空默认画像反馈并立即重排 |
| `/lang zh` | 切换为中文界面；后续日报使用中文 |
| `/lang en` | 切换为英文界面；后续日报使用英文 |
| `/quit` | 退出当前 TUI 会话 |

`WEIGHT` 是 1–5 的整数，越大表示越关注。`NAME` 是非空主题或关键词名称，允许包含空格，
例如 `/topic add 5 AI Agent`、`/keyword add 4 tool calling`。`QUERY` 是本次 arXiv 查询词，
不会自动加入长期兴趣，也不会改变 `/collect all` 的固定查询。

### 快捷键与资料抽屉

| 按键 | 作用 |
| --- | --- |
| `Enter` | 提交输入框中的命令 |
| `Ctrl+P` | 打开命令面板，搜索并选择命令 |
| `Ctrl+B` | 打开或关闭资料抽屉 |
| `Ctrl+L` | 将焦点放回命令输入框 |
| `Ctrl+Q` | 退出 TUI |
| 方向键、`PageUp` / `PageDown`、`Home` / `End` | 资料正文获得焦点时滚动内容 |

资料抽屉支持鼠标滚轮；选择栏目后正文获得焦点。四个栏目分别显示：

| 栏目 | 内容 | 退出后是否保留 |
| --- | --- | --- |
| 执行记录 | 当前会话中的命令与执行状态 | 否 |
| 推荐文章 | 数据库中已保存的正分、未反馈推荐 | 是 |
| 今日简报 | 当前会话最近一次生成的日报 | 否 |
| 反馈记录 | 默认画像当前的反馈选择 | 是 |

长耗时命令在后台执行，运行期间输入框禁用；当前一次执行一条命令。

## CLI 命令清单

以下命令在 PowerShell 中执行。示例使用已激活虚拟环境后的 `fradar`；未激活时，
把 `fradar` 替换为 `.\.venv\Scripts\fradar.exe`。

### 启动、采集与日报

| 命令 | 作用 |
| --- | --- |
| `fradar` | 打开 TUI |
| `fradar --help` | 查看 CLI 帮助；子命令也支持 `--help` |
| `fradar health` | 检查应用与 MySQL 连接状态 |
| `fradar db-upgrade` | 将配置的数据库升级到最新 Alembic 迁移版本 |
| `fradar collect hn` | 采集 HN Top Stories 的前 30 个条目 |
| `fradar collect arxiv --query "AI agent"` | 按提交日期倒序采集最多 50 篇匹配的 arXiv 论文 |
| `fradar collect all` | 采集 HN，以及 AI agent、large language model、open source software 三组 arXiv 查询 |
| `fradar normalize` | 离线处理既有快照，标准化、去重并保存文章和来源关联 |
| `fradar rank` | 重算并保存默认画像的排名；输出分数、文章 ID 和标题 |
| `fradar refresh` | 依次执行 collect all、normalize 和 rank |
| `fradar digest --limit 10 --lang zh` | 从本地候选文章生成中文 Markdown 日报 |

采集命令会访问外部公开 API 并保存快照，**不会自动清洗或排序**；可以随后执行
`normalize` 和 `rank`，也可以直接使用 `refresh` 完成默认流程。

日报需要已配置模型、API key 和本地正分且未反馈的候选文章。`--limit` 默认 10，范围 1–20，
控制提供给 Agent 的候选数量上限；Agent 最终选择 1–5 篇，并不保证与 LIMIT 相同。
CLI 的 `--lang` 支持 `zh` / `en`，默认 `en`；TUI 的 `/digest` 使用当前界面语言。
生成日报会请求模型 API，但 Agent 只读取本地情报，不会抓取外链正文。

### 兴趣画像

| 命令 | 作用 |
| --- | --- |
| `fradar interest topic add "AI Agent" --weight 5` | 添加主题，或更新同名主题的权重 |
| `fradar interest topic list` | 列出主题与权重 |
| `fradar interest topic update "AI Agent" --weight 4` | 更新已有主题的权重 |
| `fradar interest topic remove "AI Agent"` | 删除已有主题 |
| `fradar interest keyword add "tool calling" --weight 4` | 添加关键词，或更新同名关键词的权重 |
| `fradar interest keyword list` | 列出关键词与权重 |
| `fradar interest keyword update "tool calling" --weight 3` | 更新已有关键词的权重 |
| `fradar interest keyword remove "tool calling"` | 删除已有关键词 |

所有兴趣与反馈操作使用本地 `default` 画像。权重必须为 1–5 的整数，CLI 中含空格的名称
需要加引号。修改兴趣后执行 `fradar rank` 或 TUI 的 `/rank`，使已保存排名反映新规则。

### 文章反馈

| 命令 | 作用 |
| --- | --- |
| `fradar feedback like ARTICLE_ID` | 标记喜欢并重排 |
| `fradar feedback dislike ARTICLE_ID` | 标记不感兴趣并重排 |
| `fradar feedback list` | 查看文章标题、当前反馈与记录时间 |
| `fradar feedback undo ARTICLE_ID` | 撤销单篇已有反馈并重排 |
| `fradar feedback reset` | 输入 y/n 确认后清空默认画像反馈并重排 |

ARTICLE_ID 必须替换为正整数，可从 `rank` 输出或 TUI 推荐列表取得。首次标记应选择默认画像中
已有正向排名的文章；同一反馈重复提交是幂等的，更改选择会替换原反馈。已反馈文章不会继续
出现在推荐和日报候选中，撤销后会重新参与筛选。

反馈只调整独立的自动权重修正值，不覆盖手动主题或关键词权重。撤销和重置不会删除文章、
原始条目或采集快照。

### 模型配置

模型配置通过 CLI 设置，TUI 的 `/model` 仅负责查看。

```powershell
fradar llm configure --label "My provider" --base-url "https://api.example.com/v1" --model "MODEL_NAME"
fradar llm show
```

上面的 endpoint 和模型名仅为占位示例，需要替换为服务商提供的实际值。

| 参数 / 命令 | 作用 |
| --- | --- |
| `--label` | 必填，模型提供方的显示名称 |
| `--base-url` | 必填，绝对 HTTPS API 地址 |
| `--model` | 必填，服务商支持的模型标识；需要支持工具调用 |
| `--protocol` | 可选，默认 `openai-compatible`；当前只支持此协议 |
| `fradar llm show` | 显示已保存的提供方、协议、API 地址和模型名 |

API key 通过本地配置或进程环境中的 `LLM_API_KEY` 提供，不作为 CLI 参数输入，也不存入数据库
或显示在配置列表中。采集、清洗、规则排序和反馈不需要模型；生成日报才需要模型配置与 key。

## 常用操作流程

第一次使用时，在完成安装、数据库配置与迁移后，先配置兴趣，再获取推荐：

```powershell
.\.venv\Scripts\Activate.ps1
fradar health
fradar interest topic add "AI Agent" --weight 5
fradar interest keyword add "LLM" --weight 4
fradar refresh
```

完成模型配置后，可以执行 `fradar digest --limit 10 --lang zh` 生成中文日报。
反馈时，例如排名输出的文章编号为 12，可以执行 `fradar feedback like 12`；
这里的 12 只是示例，使用实际推荐文章的编号。

在 TUI 中，相同推荐流程为：

```text
/health
/topic add 5 AI Agent
/keyword add 4 LLM
/refresh
/digest 10
```

如果只想采集一个临时 arXiv 主题，可依次执行：

```text
/collect arxiv robotics
/normalize
/rank
```

该流程仍按长期兴趣对全部本地文章排序，不会单独返回“本次 robotics 查询的结果”。
HN 当前只采集热门列表，不支持按主题搜索。

## 功能清单

已勾选的功能当前可用；未勾选的功能为后续计划或待评估扩展，不代表已支持，也不承诺交付时间。

### 情报采集与推荐

- [x] Hacker News 热门资讯与 arXiv 论文采集
- [x] 按临时查询词采集 arXiv 论文
- [x] 原始响应快照保存与文章来源追溯
- [x] 离线清洗、标准化与去重
- [x] 主题、关键词与权重管理
- [x] 按兴趣与反馈进行确定性排序
- [x] 喜欢、不感兴趣、撤销和重置反馈，自动重排并避免重复推荐
- [x] 一键采集、清洗与排序
- [ ] 更多信息源，包括 GitHub 技术动态
- [ ] 临时主题搜索结果展示，区分本次采集与既有内容
- [ ] 定时采集与刷新

### Agent 与内容阅读

- [x] 自定义 OpenAI-compatible 模型配置
- [x] 受限只读策展 Agent，生成结构化 Markdown 日报与推荐理由
- [x] 中英文日报与来源追溯信息
- [x] 模型输出结构校验与有限纠正重试
- [ ] 基于本地情报的自然语言只读问答
- [ ] 自然语言行动规划，展示计划并经确认后受控执行
- [ ] 外链文章正文获取与可追溯正文快照
- [ ] 基于已保存正文生成多语言标题、摘要，并缓存以避免重复生成
- [ ] 模型厂商与模型的选择式配置
- [ ] 非 OpenAI-compatible 模型协议支持
- [ ] 跨厂商兼容性评测与更完善的结构化输出支持

### 交互与交付

- [x] CLI 命令入口与终端 TUI
- [x] 白名单斜杠命令、命令面板与参数预填
- [x] 后台执行、过程状态与结果展示
- [x] 推荐、反馈、当前会话执行记录与日报资料抽屉
- [x] 静态中英文界面切换、键盘操作与资料滚动
- [x] 离线 fixture 与自动化测试
- [x] 安装说明、命令清单与使用示例
- [ ] 专门的离线评测套件、评测报告与演示材料
- [ ] 会话和日报历史保存、恢复与查询
- [ ] 模型流式输出与任务中断后恢复
- [ ] 多任务并行、自定义主题与更丰富的鼠标交互
- [ ] Web API 与浏览器界面

当前 TUI 使用明确的英文命令；策展 Agent 只读取本地情报，不执行采集或数据库写入。
中文日报中的“策展概述”基于本地已有元数据，不能当作阅读全文后的正式摘要，来源标题保留原文。

## 验证

```powershell
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
```
