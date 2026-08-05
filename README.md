# JobOS-CN

JobOS-CN 是一个本地优先、面向国内兼职、远程和项目制岗位的 AI 求职操作系统。

当前仓库处于 **WP-001：仓库初始化** 阶段。现阶段只提供工程骨架、API 健康检查、CLI、Worker 启动入口、Vue 3 首页、质量检查和 CI，不包含真实招聘平台自动化。

完整架构依据见 [`docs/AI_JOB_OS_EXECUTION_SPEC.md`](docs/AI_JOB_OS_EXECUTION_SPEC.md)。

## 当前状态

已实现：

- Python 3.11+ 项目与开发工具链。
- FastAPI `/health` 健康检查。
- Typer CLI：`jobos --version`、`jobos doctor`。
- 最小 Worker 入口。
- Vue 3 + TypeScript + Vite 前端骨架。
- Python 与 Web 测试、lint、type-check、build。
- GitHub Actions CI。

尚未实现：数据库领域模型、工作流队列、LLM Gateway、Provider、BOSS 直聘适配、浏览器自动化、求职业务页面。

## 技术栈

- 后端：Python、FastAPI、Pydantic、SQLAlchemy、Alembic。
- CLI：Typer。
- Worker：Python + structlog。
- 前端：Vue 3、TypeScript、Vite、Pinia、Vue Router、Element Plus。
- 测试：pytest、Vitest、Playwright（后续 E2E）。
- 质量：Ruff、mypy、ESLint、Prettier。

## 仓库结构

```text
apps/          API、Worker、CLI 和 Web 应用
jobos/         JobOS 领域与基础设施包骨架
config/        无敏感信息的示例配置
docs/          架构、Provider、安全和运维文档
tests/         单元、集成、合同和 E2E 测试
src/applypilot 旧 ApplyPilot 参考代码，不属于 JobOS 运行时
```

## Windows 本地安装

```powershell
cd G:\agent\JOB_OS_EXECUTION
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dev]"
```

## 启动 API

```powershell
uvicorn apps.api.main:app --reload --host 127.0.0.1 --port 8000
```

访问 `http://127.0.0.1:8000/health`，应得到：

```json
{"status":"ok","service":"jobos-api"}
```

## 启动 Worker

```powershell
python -m apps.worker.main
```

WP-001 中 Worker 只输出一条结构化启动日志，然后退出。

## CLI

```powershell
jobos --version
jobos doctor
```

## 前端

```powershell
cd apps\web
npm install
npm run dev
```

## Python 质量检查

```powershell
python -m pytest
python -m pytest --cov=jobos --cov=apps
python -m ruff check .
python -m ruff format --check .
python -m mypy jobos apps
```

## Web 质量检查

```powershell
cd apps\web
npm run lint
npm run type-check
npm run test
npm run build
```

## 安全声明

- 不要提交 `.env`、API Key、Cookie、个人简历、招聘账号或浏览器 Profile。
- JobOS 不允许绕过 CAPTCHA、登录验证、平台风控或人工审批。
- 当前版本不会连接招聘平台，也不会自动发送消息或提交申请。

## 旧 ApplyPilot 代码

`src/applypilot` 是前期研究所保留的参考实现。新的 JobOS-CN 代码不得直接依赖该包；后续复用任何代码前必须单独核对许可证和来源。
