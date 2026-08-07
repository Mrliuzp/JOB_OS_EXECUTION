# JobOS-CN

JobOS-CN 是一个本地优先、面向国内兼职、远程岗位和外包项目的 AI 求职操作系统。系统以真实候选人事实为唯一生成依据，把职位发现、匹配评分、定制简历、人工审批、平台沟通、HR 消息处理和效果分析组织成可审计工作流。

> 当前代码已完成规格中的核心工程实现和离线验收。真实招聘平台操作仍要求用户本人手动登录，并默认使用 Dry Run。系统不会绕过验证码、登录验证或平台风控。

## 核心能力

- Pydantic 分域配置、环境变量替换和密钥脱敏。
- SQLite WAL 与 PostgreSQL URL 支持、SQLAlchemy 模型和 Alembic 迁移。
- 数据库任务队列、租约、心跳、失败恢复、重试和幂等。
- CandidateFact 事实系统、敏感性过滤和 Evidence Pack。
- OpenAI-compatible、Gemini 和本地模型网关。
- 职位硬规则、消息风险规则和 L0–L3 自动化等级。
- Provider 插件合同、BOSS 离线解析、智联/猎聘/拉勾等接口骨架。
- 独立 Chrome Profile、CDP 会话、验证码检测和失败快照。
- 职位评分、定制简历、防虚构校验和 PDF 输出。
- 申请审批、消息分类、事实型回复、幂等发送和效果分析。
- FastAPI、Vue 3 Dashboard、CLI、Worker 和 GitHub Actions。

## 安全边界

- 不保存招聘平台明文密码。
- 不自动处理 CAPTCHA、滑块或扫码登录。
- 不伪造工作经历、学历、技能、项目或量化指标。
- 薪资、Offer、合同、入职承诺和敏感个人信息必须人工确认。
- 所有平台副作用操作默认 Dry Run，并要求幂等键。
- API 默认仅监听 `127.0.0.1`。

## Windows 安装

前置环境：

- Python 3.11 或更高版本。
- Node.js 22.13.0 或更高版本。
- 本机 Chrome，用于需要人工登录的招聘平台流程。

先确认版本：

```powershell
py --version
node --version
```

项目根目录的 `.nvmrc` 固定为 Node.js 22.13.0。使用版本管理器时，请切换到该版本后再安装依赖。

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\install.ps1
.\.venv\Scripts\Activate.ps1
jobos init
jobos doctor
```

也可以手动安装：

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dev]"
```

从 Node.js 18 等旧版本升级后，应清理旧的前端依赖并重新安装：

```powershell
cd apps\web
Remove-Item -Recurse -Force node_modules -ErrorAction SilentlyContinue
npm ci
```

## 启动

终端一：

```powershell
jobos api
```

终端二：

```powershell
jobos worker
```

终端三：

```powershell
cd apps\web
npm ci
npm run dev
```

## 常用命令

```powershell
jobos --version
jobos doctor
jobos provider list
jobos provider add mock
jobos discover --provider mock --keyword Python
jobos sync-messages --provider mock
jobos status
jobos dashboard
```

真实平台登录：

1. 在 Dashboard 创建 BOSS 平台账号。
2. 点击“打开登录窗口”。
3. 在独立 Chrome 窗口中手动扫码或登录。
4. 验证登录状态。
5. 首先执行 Dry Run。
6. 只有完成页面复核后才显式开启真实动作。

## 质量检查

```powershell
python -m ruff check .
python -m ruff format --check .
python -m mypy jobos apps
python -m pytest --cov=jobos --cov=apps
```

前端：

```powershell
cd apps\web
npm ci
npm run lint
npm run type-check
npm run test
npm run build
```

## 数据备份

```powershell
.\scripts\backup.ps1
```

恢复前请停止 API、Worker 和浏览器任务：

```powershell
.\scripts\restore.ps1 -ArchivePath .\backups\jobos-backup-YYYYMMDD-HHMMSS.zip
```

## 项目结构

- `apps/api`：FastAPI 和 WebSocket。
- `apps/worker`：数据库任务 Worker。
- `apps/cli`：Typer 命令行。
- `apps/web`：Vue 3 Dashboard。
- `jobos`：领域、服务、Provider、浏览器、LLM、规则和基础设施。
- `tests`：单元、集成、合同、浏览器 Fixture 和 E2E 测试。
- `docs/AI_JOB_OS_EXECUTION_SPEC.md`：唯一架构规格。
- `src/applypilot`：历史参考代码，不属于 JobOS 运行时。

## 已知限制

- BOSS 的真实 DOM 可能随平台更新，需要使用脱敏 Fixture 和调试快照维护选择器。
- 智联、猎聘和拉勾目前提供完整 Provider 接口骨架，尚未连接真实页面。
- 真实浏览器流程需要本机 Chrome、有效登录状态和用户明确授权。
- Codex Memory 的具体外部接口未固定，当前通过适配器接收标准记录。
- 分析指标只描述相关性，不代表某个策略直接导致面试或 Offer。
