下面这份可直接保存为 `docs/AI_JOB_OS_EXECUTION_SPEC.md`，然后交给 Codex 按工作包实施。

# JobOS-CN：AI 自动求职平台可执行开发规格

**版本：** 1.0 **状态：** 可进入开发 **目标运行环境：** Windows 11，本地优先 **主要技术栈：** Python
3.11+、FastAPI、Playwright、SQLite/PostgreSQL、Vue 3、TypeScript **目标用户：**
寻找软件开发兼职、远程岗位或外包项目的个人求职者 **参考项目：** ApplyPilot **推荐仓库策略：**
新建独立仓库，按本规格重新组织；ApplyPilot 作为参考实现和可复用代码来源

---

# 1. 项目目标

构建一个本地优先、可审计、支持多招聘平台的 AI 求职操作系统，实现：

1. 自动发现符合用户要求的兼职、远程、外包岗位。
2. 获取并标准化职位描述、公司信息和招聘要求。
3. 根据用户真实经历、技能和偏好计算职位匹配度。
4. 为不同职位生成针对性简历、介绍语和求职信。
5. 在用户授权的招聘网站账户中自动沟通或投递。
6. 自动读取并分类 HR 消息。
7. 对安全、低风险的问题自动回复。
8. 对薪资、Offer、合同、入职时间等重要问题转人工确认。
9. 记录职位、投递、沟通、面试和结果数据。
10. 根据回复率、面试率和 Offer 率优化后续策略。

系统最终需要形成以下闭环：

```text
职位发现
  ↓
职位详情补全
  ↓
规则过滤
  ↓
AI 匹配评分
  ↓
事实证据检索
  ↓
定制简历与沟通材料
  ↓
审核策略判断
  ↓
自动沟通或投递
  ↓
HR 消息处理
  ↓
面试与结果跟踪
  ↓
策略反馈优化
```

---

# 2. 现有 ApplyPilot 能力评估

ApplyPilot 已经实现了六段式流水线：

```text
discover → enrich → score → tailor → cover → pdf
```

流水线既支持顺序执行，也支持基于数据库待处理数量的流式并发执行。

其 CLI 已提供初始化、流水线执行、自动投递、状态统计、Dashboard 和环境诊断等入口；自动投递还支持指定 URL、并发 Worker、Dry
Run、失败重置和手动标记结果。

ApplyPilot 的自动投递层当前通过以下组合执行：

```text
Claude Code CLI
    +
Playwright MCP
    +
Chrome CDP
    +
持久化 Chrome Profile
```

它会从数据库原子领取职位、标记 `in_progress`、启动浏览器和 Claude 进程，再将执行结果写回数据库。

其简历生成不是自由生成，而是：

1. 从用户 Profile 读取真实公司、项目、技能和指标。
2. 要求模型返回结构化 JSON。
3. 通过程序校验字段、公司、学校和技能。
4. 检测模型自言自语、虚构技术栈和模板化词汇。
5. 必要时重试并进行第二层 LLM Judge。

ApplyPilot 的职位发现层已经包含传统采集、Workday
API 抓取以及针对未知网站的智能抽取机制。智能抽取会优先分析 JSON-LD、接口响应和 DOM，再决定提取策略。

## 2.1 可以保留的能力

| 现有能力               | 处理决定                         |
| ---------------------- | -------------------------------- |
| LLM Provider 抽象      | 保留思想，重构为标准接口         |
| 顺序和流式 Pipeline    | 保留思想，升级为持久化任务编排器 |
| Profile 驱动的简历生成 | 直接保留核心规则                 |
| 防虚构验证器           | 扩展后保留                       |
| PDF 生成               | 保留                             |
| Chrome CDP 管理        | 保留思想                         |
| Worker 状态和任务领取  | 重构后保留                       |
| Dry Run                | 必须保留                         |
| Dashboard              | 重写为 Vue 3 Web UI              |
| SQLite WAL             | 本地版保留                       |
| YAML 配置              | 保留，但使用 Pydantic 校验       |

## 2.2 需要替换或重构的能力

| 现有实现                     | 目标实现                                         |
| ---------------------------- | ------------------------------------------------ |
| 单一 `jobs` 大表             | 规范化领域数据模型                               |
| Claude Code 作为生产运行时   | Playwright 确定性执行为主，Browser Agent 为辅    |
| 英文海外求职 Prompt          | 中文兼职、远程和外包 Prompt                      |
| 海外招聘平台                 | 国内平台 Provider                                |
| 工签、EEO 等表单字段         | 国内兼职可用时间、合作方式、发票、结算周期等字段 |
| Gmail MCP                    | 招聘平台站内消息 Provider                        |
| URL 作为职位主键             | 平台 ID、外部职位 ID 和规范化 URL 联合标识       |
| 所有配置集中在单文件         | 分域配置系统                                     |
| 一次性长 Prompt 驱动全部操作 | 任务计划、规则引擎和动作执行分离                 |

## 2.3 许可证约束

ApplyPilot README 标明项目使用 AGPL-3.0。将其代码直接复制并用于对外提供网络服务，通常会触发相应的开源义务。

本项目需要在开发前明确选择：

```text
方案 A：接受 AGPL
直接 Fork 或复用大量 ApplyPilot 代码，项目继续采用 AGPL。

方案 B：独立实现
只参考架构思想和接口设计，不复制具体实现，使用自己的许可证。
```

本规格推荐 **方案 B：新仓库独立实现**。对于确实值得复用的代码，应单独记录来源、许可证和修改范围。

---

# 3. 产品范围

## 3.1 必须实现

### 求职资料

- 用户基本信息。
- 联系方式。
- 技术栈。
- 工作经历。
- 项目经历。
- 真实量化指标。
- 教育经历。
- 可接受的职位类型。
- 每周可投入时间。
- 可工作的时间段。
- 最早开始时间。
- 期望时薪、日薪、月薪。
- 是否接受远程。
- 是否接受外包。
- 是否接受短期项目。
- 不可公开的信息。
- 必须人工确认的问题。

### 招聘平台

架构上支持：

- BOSS 直聘。
- 智联招聘。
- 猎聘。
- 拉勾。
- 企业招聘官网。
- 通用网页职位导入。
- 手动粘贴 JD。
- 手动导入职位 URL。

首个生产可用 Provider 为 `boss`，其余 Provider 必须至少完成接口骨架和 Mock 测试。

### 自动化流程

- 搜索职位。
- 获取职位列表。
- 获取职位详情。
- 去重。
- 规则过滤。
- 匹配评分。
- 生成简历版本。
- 生成开场消息。
- 发起沟通。
- 上传或发送简历。
- 接收 HR 消息。
- 自动回复低风险消息。
- 转人工处理高风险消息。
- 记录面试和结果。
- 统计效果。

## 3.2 不做的事情

- 不绕过招聘网站登录验证。
- 不破解或规避 CAPTCHA。
- 不伪造工作经历、学历、技术栈和项目数据。
- 不批量创建招聘平台账号。
- 不模拟多个虚假身份。
- 不绕过平台限流和风控机制。
- 不在未授权情况下读取其他用户数据。
- 不在默认模式下自动接受 Offer、合同或薪资条件。
- 不自动发送任何法律承诺。
- 不自动发送身份证、银行卡等高敏感资料。

---

# 4. 核心设计原则

## 4.1 确定性代码优先

以下工作必须由普通代码完成：

- 状态流转。
- 数据校验。
- 规则判断。
- 去重。
- 限流。
- 数据库存取。
- 浏览器会话管理。
- 文件生成。
- 审计记录。
- 提交前检查。

LLM 仅用于：

- 理解 JD。
- 语义评分。
- 事实相关性选择。
- 简历内容重写。
- 消息分类。
- 消息草拟。
- 不稳定页面的辅助理解。

LLM 不得直接决定系统权限、安全边界或是否可绕过人工确认。

## 4.2 事实优先

所有生成内容必须能够关联到一个或多个 `evidence_id`。

示例：

```json
{
	"claim": "使用 Python 自动化财务报表流程",
	"evidence_ids": ["fact_project_002", "metric_005"]
}
```

无法找到事实依据的内容禁止写入简历或发送给 HR。

## 4.3 默认可审计

每次重要动作必须记录：

- 谁发起。
- 为什么执行。
- 使用了什么输入。
- 规则判断结果。
- 使用的模型和 Prompt 版本。
- 浏览器动作。
- 页面快照。
- 最终发送或提交内容。
- 执行结果。
- 错误原因。

## 4.4 可中断、可恢复、幂等

任何任务都可能因浏览器关闭、网络中断、登录过期而失败。

任务必须满足：

- 重启后可以继续。
- 同一个职位不会重复沟通。
- 同一条消息不会重复回复。
- 同一份申请不会重复提交。
- Worker 崩溃后任务锁能够自动过期。
- 已完成任务重复执行不会产生副作用。

## 4.5 人工控制等级

系统提供四种自动化等级：

| 等级 | 行为                                           |
| ---- | ---------------------------------------------- |
| L0   | 只采集和分析，不生成、不发送                   |
| L1   | 自动生成，所有发送前人工确认                   |
| L2   | 低风险消息自动发送，投递前确认                 |
| L3   | 符合规则的职位自动沟通和投递，高风险事项转人工 |

默认等级为 `L1`。

---

# 5. 总体架构

```text
┌───────────────────────────────────────────────┐
│                Vue 3 Dashboard                │
│ 职位 / 简历 / 消息 / 审批 / 面试 / 数据分析    │
└───────────────────────┬───────────────────────┘
                        │ HTTP / WebSocket
┌───────────────────────▼───────────────────────┐
│                 FastAPI API                   │
│ Auth / CRUD / Approval / Monitoring / Config  │
└───────────────────────┬───────────────────────┘
                        │
┌───────────────────────▼───────────────────────┐
│              Workflow Orchestrator            │
│ 任务编排 / 状态机 / 重试 / 租约 / 幂等 / 限流   │
└──────┬─────────┬─────────┬─────────┬──────────┘
       │         │         │         │
       ▼         ▼         ▼         ▼
 Discovery   Evaluation  Content   Communication
 Service      Service    Service      Service
       │         │         │         │
       └─────────┴────┬────┴─────────┘
                      ▼
┌───────────────────────────────────────────────┐
│                  Rule Engine                  │
│ 黑白名单 / 自动化等级 / 薪资 / 时间 / 风险判断 │
└───────────────────────┬───────────────────────┘
                        │
       ┌────────────────┼─────────────────┐
       ▼                ▼                 ▼
 Provider Layer     LLM Gateway      Memory Store
 BOSS/智联/猎聘      OpenAI/Gemini     事实/项目/历史
       │
       ▼
 Browser Runtime
 Playwright/CDP/Persistent Profile
       │
       ▼
 SQLite / PostgreSQL + Artifact Storage + Audit Log
```

---

# 6. 技术选型

## 6.1 后端

| 领域         | 技术                                    |
| ------------ | --------------------------------------- |
| 语言         | Python 3.11+                            |
| API          | FastAPI                                 |
| 数据模型     | Pydantic v2                             |
| ORM          | SQLAlchemy 2                            |
| 迁移         | Alembic                                 |
| 本地数据库   | SQLite WAL                              |
| 服务端数据库 | PostgreSQL                              |
| 浏览器       | Playwright                              |
| CLI          | Typer                                   |
| 调度         | 自研数据库任务队列                      |
| 配置         | YAML + `.env` + Pydantic Settings       |
| 日志         | structlog 或标准 logging JSON Formatter |
| 测试         | pytest                                  |
| HTTP         | httpx                                   |
| PDF          | Playwright HTML-to-PDF                  |
| 模板         | Jinja2                                  |
| 加密         | Windows DPAPI 或 keyring                |

## 6.2 前端

| 领域     | 技术                    |
| -------- | ----------------------- |
| 框架     | Vue 3                   |
| 构建     | Vite                    |
| 语言     | TypeScript              |
| 状态     | Pinia                   |
| 路由     | Vue Router              |
| UI       | Element Plus            |
| 请求     | Axios                   |
| 实时状态 | WebSocket               |
| 测试     | Vitest + Playwright E2E |

## 6.3 不引入的基础设施

本地单用户版本不依赖：

- Redis。
- Kafka。
- Kubernetes。
- Celery。
- 云端对象存储。
- 外部向量数据库。

后续多人部署时再增加这些组件。

---

# 7. 代码仓库结构

```text
jobos-cn/
├─ apps/
│  ├─ api/
│  │  ├─ main.py
│  │  ├─ dependencies.py
│  │  └─ routes/
│  ├─ worker/
│  │  ├─ main.py
│  │  └─ scheduler.py
│  ├─ cli/
│  │  └─ main.py
│  └─ web/
│     ├─ src/
│     ├─ package.json
│     └─ vite.config.ts
│
├─ jobos/
│  ├─ core/
│  │  ├─ config/
│  │  ├─ enums.py
│  │  ├─ errors.py
│  │  ├─ logging.py
│  │  ├─ security.py
│  │  └─ idempotency.py
│  │
│  ├─ domain/
│  │  ├─ candidate/
│  │  ├─ jobs/
│  │  ├─ applications/
│  │  ├─ conversations/
│  │  ├─ interviews/
│  │  ├─ policies/
│  │  └─ tasks/
│  │
│  ├─ providers/
│  │  ├─ base.py
│  │  ├─ registry.py
│  │  ├─ boss/
│  │  ├─ zhaopin/
│  │  ├─ liepin/
│  │  ├─ lagou/
│  │  ├─ generic_web/
│  │  └─ manual/
│  │
│  ├─ browser/
│  │  ├─ session_manager.py
│  │  ├─ profile_manager.py
│  │  ├─ action_executor.py
│  │  ├─ page_snapshot.py
│  │  ├─ selectors.py
│  │  └─ risk_detector.py
│  │
│  ├─ llm/
│  │  ├─ base.py
│  │  ├─ gateway.py
│  │  ├─ openai_provider.py
│  │  ├─ gemini_provider.py
│  │  ├─ local_provider.py
│  │  ├─ schemas.py
│  │  └─ usage.py
│  │
│  ├─ memory/
│  │  ├─ base.py
│  │  ├─ local_store.py
│  │  ├─ codex_memory_adapter.py
│  │  └─ retrieval.py
│  │
│  ├─ services/
│  │  ├─ discovery_service.py
│  │  ├─ enrichment_service.py
│  │  ├─ scoring_service.py
│  │  ├─ resume_service.py
│  │  ├─ communication_service.py
│  │  ├─ application_service.py
│  │  └─ analytics_service.py
│  │
│  ├─ workflow/
│  │  ├─ orchestrator.py
│  │  ├─ task_queue.py
│  │  ├─ leases.py
│  │  ├─ retry.py
│  │  └─ handlers/
│  │
│  ├─ rules/
│  │  ├─ engine.py
│  │  ├─ conditions.py
│  │  ├─ actions.py
│  │  └─ schemas.py
│  │
│  ├─ prompts/
│  │  ├─ registry.py
│  │  ├─ scoring/
│  │  ├─ resume/
│  │  ├─ messaging/
│  │  └─ browser/
│  │
│  ├─ artifacts/
│  │  ├─ renderer.py
│  │  ├─ resume_templates/
│  │  └─ storage.py
│  │
│  └─ infrastructure/
│     ├─ db/
│     ├─ repositories/
│     └─ migrations/
│
├─ config/
│  ├─ app.example.yaml
│  ├─ policies.example.yaml
│  ├─ providers.example.yaml
│  └─ prompts.example.yaml
│
├─ tests/
│  ├─ unit/
│  ├─ integration/
│  ├─ contract/
│  ├─ browser_fixtures/
│  └─ e2e/
│
├─ docs/
│  ├─ architecture.md
│  ├─ provider-development.md
│  ├─ safety.md
│  └─ operations.md
│
├─ scripts/
├─ pyproject.toml
├─ docker-compose.yml
└─ README.md
```

---

# 8. 核心领域模型

## 8.1 CandidateProfile

```text
id
name
preferred_name
email
phone
city
timezone
summary
automation_level
created_at
updated_at
```

敏感字段不得直接写入普通日志。

## 8.2 CandidateFact

用于阻止简历和聊天内容虚构。

```text
id
profile_id
fact_type
statement
source_type
source_reference
confidence
valid_from
valid_until
allowed_for_resume
allowed_for_chat
sensitivity
metadata_json
created_at
updated_at
```

`fact_type` 枚举：

```text
skill
employment
project
achievement
metric
education
availability
compensation
preference
work_authorization
portfolio
other
```

`sensitivity` 枚举：

```text
public
normal
private
restricted
```

`restricted` 内容默认禁止自动发送。

## 8.3 ResumeVersion

```text
id
profile_id
job_id nullable
version_type
language
title
content_json
rendered_text_path
rendered_pdf_path
validation_status
validation_report_json
prompt_version
model_name
created_at
```

`version_type`：

```text
base
template
tailored
manual
```

## 8.4 PlatformAccount

```text
id
provider
display_name
browser_profile_id
status
last_login_check_at
last_sync_at
rate_limit_json
settings_json
created_at
updated_at
```

禁止保存招聘平台明文密码。

## 8.5 Job

```text
id
provider
external_job_id
canonical_url
title
company_name
company_external_id
location
work_mode
employment_type
salary_min
salary_max
salary_period
currency
description_raw
description_normalized
requirements_json
benefits_json
published_at
expires_at
discovered_at
last_seen_at
status
content_hash
metadata_json
```

唯一约束：

```text
UNIQUE(provider, external_job_id)
UNIQUE(provider, canonical_url)
```

`employment_type`：

```text
full_time
part_time
contract
freelance
internship
temporary
unknown
```

`work_mode`：

```text
remote
hybrid
onsite
unknown
```

`status`：

```text
discovered
enriched
filtered
eligible
scored
archived
expired
```

## 8.6 JobScore

```text
id
job_id
profile_id
total_score
technical_score
experience_score
availability_score
compensation_score
remote_score
risk_score
matched_skills_json
missing_skills_json
reasons_json
evidence_ids_json
decision
prompt_version
model_name
created_at
```

`decision`：

```text
reject
review
eligible
priority
```

评分范围统一为 `0–100`。

## 8.7 Application

```text
id
job_id
profile_id
platform_account_id
resume_version_id
status
autonomy_level
intro_message
submitted_at
last_action_at
failure_code
failure_detail
external_application_id
idempotency_key
created_at
updated_at
```

唯一约束：

```text
UNIQUE(profile_id, job_id)
UNIQUE(idempotency_key)
```

`status`：

```text
planned
materials_ready
awaiting_approval
approved
communicating
submitted
viewed
rejected
interviewing
offer
accepted
withdrawn
expired
failed
manual_required
```

## 8.8 Conversation

```text
id
provider
external_conversation_id
job_id
application_id
recruiter_name
recruiter_company
status
last_message_at
unread_count
created_at
updated_at
```

## 8.9 Message

```text
id
conversation_id
external_message_id
direction
sender_type
content
message_type
risk_level
reply_status
generated_reply
sent_at
received_at
metadata_json
```

`message_type`：

```text
greeting
resume_request
availability
experience_question
technical_question
salary
interview_schedule
offer
contract
personal_information
rejection
follow_up
unknown
```

`risk_level`：

```text
low
medium
high
critical
```

## 8.10 ApprovalRequest

```text
id
entity_type
entity_id
approval_type
reason
payload_json
status
requested_at
resolved_at
resolved_by
resolution_note
```

`status`：

```text
pending
approved
rejected
expired
```

## 8.11 WorkflowTask

```text
id
task_type
entity_type
entity_id
status
priority
scheduled_at
available_at
lease_owner
lease_expires_at
attempt_count
max_attempts
input_json
output_json
last_error
idempotency_key
created_at
updated_at
```

`status`：

```text
pending
leased
running
succeeded
retry_wait
failed
cancelled
manual_required
```

## 8.12 AuditEvent

```text
id
event_type
actor_type
actor_id
entity_type
entity_id
trace_id
payload_json
created_at
```

---

# 9. 状态机

## 9.1 职位状态

```text
discovered
  → enriched
  → filtered
      → archived
      → eligible
          → scored
```

非法跳转必须抛出 `InvalidStateTransitionError`。

## 9.2 申请状态

```text
planned
  → materials_ready
  → awaiting_approval
  → approved
  → communicating
  → submitted
  → viewed
  → interviewing
  → offer
  → accepted
```

失败分支：

```text
任意可执行状态
  → failed
  → planned 或 manual_required
```

终止分支：

```text
rejected
withdrawn
expired
accepted
```

## 9.3 消息回复状态

```text
received
  → classified
  → draft_ready
      → awaiting_approval
      → auto_approved
  → sending
  → sent
```

异常：

```text
classification_failed
generation_failed
send_failed
manual_required
```

---

# 10. Provider 插件规范

## 10.1 ProviderCapabilities

```python
@dataclass(frozen=True)
class ProviderCapabilities:
    discovery: bool
    job_detail: bool
    initiate_chat: bool
    send_message: bool
    upload_resume: bool
    direct_apply: bool
    receive_messages: bool
    application_status: bool
```

## 10.2 ProviderAdapter 接口

```python
class ProviderAdapter(Protocol):
    name: str
    capabilities: ProviderCapabilities

    async def check_login(
        self,
        account: PlatformAccount,
    ) -> LoginStatus:
        ...

    async def discover_jobs(
        self,
        account: PlatformAccount,
        query: JobSearchQuery,
        cursor: str | None = None,
    ) -> JobSearchPage:
        ...

    async def fetch_job_detail(
        self,
        account: PlatformAccount,
        job_ref: ExternalJobRef,
    ) -> RawJobDetail:
        ...

    async def initiate_contact(
        self,
        account: PlatformAccount,
        request: ContactRequest,
    ) -> ProviderActionResult:
        ...

    async def submit_application(
        self,
        account: PlatformAccount,
        request: SubmitApplicationRequest,
    ) -> ProviderActionResult:
        ...

    async def list_conversations(
        self,
        account: PlatformAccount,
        cursor: str | None = None,
    ) -> ConversationPage:
        ...

    async def list_messages(
        self,
        account: PlatformAccount,
        conversation_ref: ExternalConversationRef,
        cursor: str | None = None,
    ) -> MessagePage:
        ...

    async def send_message(
        self,
        account: PlatformAccount,
        request: SendMessageRequest,
    ) -> ProviderActionResult:
        ...
```

## 10.3 Provider 禁止事项

Provider 不得：

- 直接修改业务数据库。
- 直接调用 LLM。
- 决定是否值得投递。
- 绕过审批。
- 保存用户密码。
- 在没有幂等键时发送消息。
- 自动处理 CAPTCHA。
- 将页面 HTML 长期写入普通日志。

Provider 只负责平台交互和数据转换。

## 10.4 Provider 错误类型

```text
ProviderLoginRequired
ProviderSessionExpired
ProviderRateLimited
ProviderPageChanged
ProviderJobExpired
ProviderPermissionDenied
ProviderCaptchaDetected
ProviderActionRejected
ProviderTemporaryError
ProviderPermanentError
```

所有异常必须映射为标准错误类型，不得只返回字符串。

---

# 11. BOSS 直聘 Provider 规格

## 11.1 登录

登录采用持久化 Chrome Profile：

1. 用户通过真实 Chrome 窗口手动登录。
2. 系统验证登录状态。
3. Profile 与 `PlatformAccount` 绑定。
4. 后续任务复用该 Profile。
5. 检测到登录失效时创建人工任务。
6. 不自动输入账号密码。
7. 不自动处理扫码或验证码。

默认一个 BOSS 账号只允许一个活动浏览器任务，避免会话冲突。

## 11.2 职位发现

输入：

```json
{
	"keywords": ["Vue", "C#", "Python", "软件架构师"],
	"employment_types": ["part_time", "contract", "freelance"],
	"work_modes": ["remote", "hybrid"],
	"locations": ["全国", "上海"],
	"salary_min": null,
	"page_limit": 5
}
```

输出：

```json
{
	"items": [
		{
			"external_job_id": "...",
			"canonical_url": "...",
			"title": "...",
			"company_name": "...",
			"location": "...",
			"salary_text": "...",
			"job_card_text": "...",
			"metadata": {}
		}
	],
	"next_cursor": "..."
}
```

## 11.3 DOM 适配策略

按以下顺序定位元素：

1. ARIA Role 和可见文本。
2. 稳定的 `data-*` 属性。
3. 稳定 CSS 类组合。
4. 页面结构相对定位。
5. 页面 Snapshot 规则。
6. LLM 生成临时动作计划。

禁止仅依赖随机类名或绝对 XPath。

每个 Provider 必须维护：

```text
selectors/
  login.yaml
  search.yaml
  job_detail.yaml
  conversation.yaml
  resume.yaml
```

选择器配置包含：

```yaml
key: search.job_cards
strategies:
    - type: role
      role: listitem
    - type: css
      value: '.job-card-wrapper'
validation:
    minimum_count: 1
```

## 11.4 沟通动作

支持：

- 打开职位。
- 检查职位是否仍有效。
- 检查是否已经沟通过。
- 点击沟通入口。
- 发送开场语。
- 发送或上传简历。
- 记录发送结果。
- 读取新消息。

执行前必须再次判断：

- 职位是否过期。
- 公司是否被屏蔽。
- 是否已经投递。
- 是否超过每日额度。
- 是否命中人工审批规则。
- 页面是否出现风控提示。

## 11.5 是否需要平台开发人员对接

个人账号的浏览器自动化模式不要求招聘平台开发人员配合。

只有以下场景需要官方商务或开发接口：

- 使用官方开放 API。
- 企业级批量数据合作。
- 获取非页面公开数据。
- 以 SaaS 形式服务大量用户。
- 需要官方授权的大规模自动化。

本项目默认使用用户本人浏览器会话，不依赖官方 API，但必须遵守平台规则和限流要求。

---

# 12. Browser Runtime

## 12.1 浏览器会话管理

```python
class BrowserSessionManager:
    async def acquire(
        self,
        account_id: UUID,
        purpose: str,
    ) -> BrowserSession:
        ...

    async def release(
        self,
        session: BrowserSession,
    ) -> None:
        ...

    async def invalidate(
        self,
        account_id: UUID,
        reason: str,
    ) -> None:
        ...
```

每个会话包含：

```text
session_id
account_id
browser_profile_path
cdp_port
process_id
started_at
last_heartbeat_at
purpose
```

## 12.2 Profile 策略

```text
data/browser-profiles/
  boss-primary/
  zhaopin-primary/
  liepin-primary/
```

规则：

- 不直接操作用户日常 Chrome Profile。
- 第一次初始化时复制必要 Profile 数据或创建独立 Profile。
- 初始化后由用户在独立窗口完成登录。
- 同一 Profile 禁止同时被两个 Chrome 进程写入。
- 浏览器崩溃后清理 Singleton 文件和残留端口。
- Cookie 不输出到日志。
- Profile 目录不提交到 Git。

## 12.3 浏览器动作模型

```python
@dataclass
class BrowserAction:
    action_type: Literal[
        "goto",
        "click",
        "fill",
        "select",
        "upload",
        "wait",
        "snapshot",
        "extract",
    ]
    selector: SelectorSpec | None
    value: str | None
    timeout_ms: int
    expected_state: ExpectedState | None
```

每个动作执行后必须检查预期状态。

## 12.4 Agent 辅助浏览

LLM Browser Agent 只在以下情况下启用：

- 页面结构无法被已知选择器识别。
- 页面出现未见过的表单字段。
- 需要判断按钮或文字语义。
- 需要从复杂页面提取职位要求。

Agent 返回动作计划，不直接绕过 Action Executor：

```json
{
	"page_state": "job_detail",
	"actions": [
		{
			"type": "click",
			"target_description": "立即沟通按钮",
			"selector_candidates": []
		}
	],
	"confidence": 0.84,
	"requires_human": false
}
```

Action Executor 仍负责权限、限流、截图和结果验证。

## 12.5 CAPTCHA 和风控

检测到以下内容立即停止任务：

```text
验证码
滑块
安全验证
访问过于频繁
异常请求
账号风险
请重新登录
扫码登录
```

任务状态设为：

```text
manual_required
```

不得尝试自动破解或规避。

---

# 13. LLM Gateway

## 13.1 接口

```python
class LLMProvider(Protocol):
    async def generate(
        self,
        request: LLMRequest,
    ) -> LLMResponse:
        ...

    async def health_check(self) -> ProviderHealth:
        ...
```

`LLMRequest`：

```text
task_type
messages
response_schema
temperature
max_tokens
timeout_seconds
trace_id
metadata
```

`LLMResponse`：

```text
content
parsed
model
provider
prompt_tokens
completion_tokens
latency_ms
request_id
```

## 13.2 Provider 支持

优先级：

```text
OpenAI-compatible
Gemini
本地 Ollama / llama.cpp
```

通过配置选择：

```yaml
llm:
    default_provider: openai
    tasks:
        scoring:
            provider: openai
            model: configured-model
        resume:
            provider: openai
            model: configured-model
        message_classification:
            provider: local
            model: configured-local-model
```

代码不得写死具体模型名称。

## 13.3 结构化输出

以下任务必须返回 JSON Schema：

- 职位标准化。
- 职位评分。
- 事实选择。
- 简历生成。
- 消息分类。
- 回复草稿。
- 页面动作计划。

解析失败时：

1. 尝试提取 JSON。
2. 使用修复 Prompt 重试一次。
3. 切换备用模型。
4. 标记任务失败或人工处理。

## 13.4 重试

允许重试：

- 超时。
- 429。
- 502、503、504。
- 无效 JSON。
- Schema 校验失败。

禁止盲目重试：

- 认证失败。
- 余额不足。
- 内容策略拒绝。
- 输入超过限制。
- 已被判定为虚构。

---

# 14. Memory 和事实系统

## 14.1 MemoryProvider 接口

```python
class MemoryProvider(Protocol):
    async def search(
        self,
        profile_id: UUID,
        query: str,
        filters: MemoryFilters,
        limit: int = 20,
    ) -> list[CandidateFact]:
        ...

    async def upsert_fact(
        self,
        fact: CandidateFact,
    ) -> CandidateFact:
        ...

    async def invalidate_fact(
        self,
        fact_id: UUID,
        reason: str,
    ) -> None:
        ...
```

## 14.2 Codex Memory 接入

`codex_memory_adapter.py` 只负责：

- 将用户已有项目、经历和指标同步到 `CandidateFact`。
- 保留外部记录 ID。
- 记录同步时间。
- 不直接将检索结果发给模型。
- 通过事实过滤器移除敏感或过期内容。

由于 Codex Memory 的具体本地接口尚未在现有源码中明确，本项目必须先实现
`LocalMemoryStore`，再通过适配器接入用户已有系统。

## 14.3 事实检索流程

```text
JD
 ↓
提取核心要求
 ↓
生成事实查询
 ↓
Memory 搜索
 ↓
权限和有效期过滤
 ↓
事实相关性排序
 ↓
生成 Evidence Pack
 ↓
交给简历或消息 Agent
```

`EvidencePack`：

```json
{
	"job_id": "...",
	"facts": [
		{
			"evidence_id": "fact-001",
			"statement": "...",
			"fact_type": "project",
			"confidence": 1.0
		}
	],
	"forbidden_claims": [],
	"missing_requirements": []
}
```

---

# 15. 职位规则引擎

## 15.1 规则优先级

```text
安全硬规则
  >
用户拒绝规则
  >
平台限流规则
  >
自动化审批规则
  >
AI 匹配结果
```

AI 高评分不得覆盖硬规则。

## 15.2 兼职求职规则示例

```yaml
version: 1

job_policy:
    accepted_employment_types:
        - part_time
        - contract
        - freelance
        - temporary

    accepted_work_modes:
        - remote
        - hybrid

    preferred_keywords:
        - Vue
        - Vue 3
        - C#
        - .NET
        - Python
        - FastAPI
        - 软件架构
        - 系统设计
        - 技术顾问

    rejected_keywords:
        - 驻场全职
        - 纯销售
        - 培训招生
        - 无薪
        - 拉新
        - 刷单

    blocked_companies: []
    blocked_company_patterns:
        - 培训
        - 人力外包转包

    weekly_hours:
        minimum: 5
        maximum: 25

    score_thresholds:
        reject_below: 55
        review_below: 72
        auto_contact_above: 82

automation:
    level: L1
    daily_contact_limit: 15
    daily_application_limit: 8
    minimum_seconds_between_actions: 20
    allow_auto_greeting: true
    allow_auto_resume_send: false
```

## 15.3 消息审批规则

```yaml
message_policy:
    auto_reply_types:
        - greeting
        - resume_request
        - availability
        - experience_question

    manual_review_types:
        - salary
        - interview_schedule
        - technical_question
        - personal_information

    always_manual_types:
        - offer
        - contract

    forbidden_auto_content:
        - 身份证
        - 银行卡
        - 当前公司内部数据
        - 客户保密信息
        - 法律承诺
```

---

# 16. 职位评分

总分 100：

| 维度               | 权重 |
| ------------------ | ---: |
| 技术匹配           |   30 |
| 项目和经验匹配     |   20 |
| 兼职或合作方式匹配 |   15 |
| 远程和地点匹配     |   10 |
| 时间投入匹配       |   10 |
| 薪资匹配           |    5 |
| 职位可信度         |    5 |
| 公司和风险偏好     |    5 |

输出 Schema：

```json
{
	"total_score": 86,
	"decision": "priority",
	"dimension_scores": {
		"technical": 27,
		"experience": 17,
		"employment_type": 15,
		"work_mode": 10,
		"availability": 8,
		"compensation": 4,
		"credibility": 3,
		"risk": 2
	},
	"matched_requirements": [],
	"missing_requirements": [],
	"matched_evidence_ids": [],
	"hard_reject_reasons": [],
	"summary": ""
}
```

评分必须先执行硬规则，再调用 LLM。

---

# 17. 简历生成

## 17.1 输入

```text
基础简历
Candidate Profile
Evidence Pack
标准化 JD
目标职位
输出模板
语言
长度限制
```

## 17.2 输出

```json
{
	"target_title": "",
	"summary": "",
	"skills": [
		{
			"category": "",
			"items": []
		}
	],
	"experiences": [
		{
			"source_fact_ids": [],
			"company": "",
			"role": "",
			"period": "",
			"bullets": []
		}
	],
	"projects": [],
	"education": [],
	"excluded_requirements": [],
	"validation_notes": []
}
```

## 17.3 强制要求

- 姓名、联系方式由代码注入。
- 公司、学校、时间段不得由模型改写。
- 所有 Bullet 必须关联事实 ID。
- 不允许将“了解”改写成“精通”。
- 不允许添加未发生的项目。
- 不允许改变量化指标。
- 对缺失技能明确标记，不通过文字掩盖。
- 生成后必须执行程序化验证。
- 验证失败不得进入自动投递。

## 17.4 验证层

第一层：Schema 校验。第二层：事实 ID 校验。第三层：公司、学校、日期、指标校验。第四层：技能边界校验。第五层：敏感信息检查。第六层：LLM
Judge，可配置关闭。第七层：PDF 渲染检查。

---

# 18. HR 消息助手

## 18.1 消息处理流程

```text
同步消息
 ↓
外部消息 ID 去重
 ↓
消息分类
 ↓
风险等级判断
 ↓
检索相关事实
 ↓
生成回复草稿
 ↓
规则审批
 ├─ 自动发送
 └─ 人工审批
 ↓
写入审计日志
```

## 18.2 低风险自动回复

可以自动处理：

- “方便发一下简历吗？”
- “每周可以投入多少时间？”
- “可以远程吗？”
- “什么时候可以开始？”
- “有 Vue/C#/Python 经验吗？”
- “是否接受兼职或项目制？”

回复必须基于 Profile 和 CandidateFact。

## 18.3 必须人工确认

- 期望薪资或具体报价。
- 面试具体时间。
- Offer。
- 合同。
- 入职承诺。
- 是否从当前公司离职。
- 身份证、银行卡、住址等敏感资料。
- 涉及当前公司或客户机密的问题。
- 无法由事实库回答的问题。
- 模型置信度低于阈值的问题。

## 18.4 消息分类输出

```json
{
	"message_type": "availability",
	"risk_level": "low",
	"intent": "询问每周可投入时间",
	"required_fact_types": ["availability"],
	"requires_human": false,
	"confidence": 0.96
}
```

## 18.5 回复输出

```json
{
	"reply": "可以远程兼职，每周可稳定投入 15 至 20 小时，工作日晚间和周末均可安排。",
	"evidence_ids": ["availability-001"],
	"requires_human": false,
	"risk_flags": []
}
```

---

# 19. 工作流编排

## 19.1 任务类型

```text
DISCOVER_JOBS
ENRICH_JOB
NORMALIZE_JOB
EVALUATE_RULES
SCORE_JOB
BUILD_EVIDENCE_PACK
GENERATE_RESUME
VALIDATE_RESUME
RENDER_RESUME
CREATE_APPLICATION
REQUEST_APPLICATION_APPROVAL
INITIATE_CONTACT
SEND_RESUME
SYNC_CONVERSATIONS
SYNC_MESSAGES
CLASSIFY_MESSAGE
GENERATE_REPLY
REQUEST_REPLY_APPROVAL
SEND_REPLY
CHECK_APPLICATION_STATUS
GENERATE_ANALYTICS
```

## 19.2 任务领取

Worker 使用租约模式：

```sql
UPDATE workflow_tasks
SET
  status = 'leased',
  lease_owner = :worker_id,
  lease_expires_at = :expires_at
WHERE id = (
  SELECT id
  FROM workflow_tasks
  WHERE status IN ('pending', 'retry_wait')
    AND available_at <= CURRENT_TIMESTAMP
  ORDER BY priority DESC, created_at ASC
  LIMIT 1
)
RETURNING *;
```

SQLite 版本需使用事务和 `BEGIN IMMEDIATE`。

## 19.3 租约

- 默认租约 5 分钟。
- Worker 每 30 秒续租。
- 超过租约时间的任务可重新领取。
- 发送消息和提交申请前必须再次获取实体级锁。
- 执行副作用前必须检查幂等键。

## 19.4 重试策略

| 错误          | 行为                               |
| ------------- | ---------------------------------- |
| 网络超时      | 指数退避，最多 3 次                |
| 平台限流      | 按 Provider 冷却时间重试           |
| 页面变化      | 保存快照，标记 ProviderPageChanged |
| 登录失效      | manual_required                    |
| CAPTCHA       | manual_required                    |
| 职位过期      | application 设为 expired           |
| LLM 无效 JSON | 重试 1 次，再切备用模型            |
| 事实校验失败  | 不自动重试，进入人工检查           |
| 已经沟通过    | 视为幂等成功                       |
| 已经投递      | 视为幂等成功                       |

---

# 20. API 规格

## 20.1 Profile

```text
GET    /api/v1/profile
PUT    /api/v1/profile
GET    /api/v1/profile/facts
POST   /api/v1/profile/facts
PUT    /api/v1/profile/facts/{id}
DELETE /api/v1/profile/facts/{id}
```

## 20.2 Jobs

```text
GET  /api/v1/jobs
GET  /api/v1/jobs/{id}
POST /api/v1/jobs/import-url
POST /api/v1/jobs/import-text
POST /api/v1/jobs/{id}/score
POST /api/v1/jobs/{id}/archive
```

## 20.3 Applications

```text
GET  /api/v1/applications
POST /api/v1/applications
GET  /api/v1/applications/{id}
POST /api/v1/applications/{id}/generate-materials
POST /api/v1/applications/{id}/approve
POST /api/v1/applications/{id}/submit
POST /api/v1/applications/{id}/withdraw
```

## 20.4 Conversations

```text
GET  /api/v1/conversations
GET  /api/v1/conversations/{id}/messages
POST /api/v1/conversations/{id}/sync
POST /api/v1/messages/{id}/generate-reply
POST /api/v1/messages/{id}/approve-reply
POST /api/v1/messages/{id}/send
```

## 20.5 Providers

```text
GET  /api/v1/providers
GET  /api/v1/providers/accounts
POST /api/v1/providers/accounts
POST /api/v1/providers/accounts/{id}/login-window
POST /api/v1/providers/accounts/{id}/check-login
POST /api/v1/providers/accounts/{id}/sync
```

## 20.6 Workflow

```text
GET  /api/v1/tasks
POST /api/v1/tasks/{id}/retry
POST /api/v1/tasks/{id}/cancel
GET  /api/v1/audit-events
GET  /api/v1/system/health
```

---

# 21. CLI 规格

```powershell
jobos init
jobos doctor
jobos api
jobos worker

jobos provider list
jobos provider add boss
jobos provider login boss
jobos provider check boss

jobos discover --provider boss
jobos discover --all
jobos sync-messages --provider boss

jobos run
jobos run --dry-run
jobos run --automation-level L1

jobos job import-url "<URL>"
jobos job import-text ".\jd.txt"
jobos job score "<JOB_ID>"

jobos application prepare "<JOB_ID>"
jobos application submit "<APPLICATION_ID>"
jobos application mark-submitted "<APPLICATION_ID>"

jobos approvals list
jobos approvals approve "<APPROVAL_ID>"
jobos approvals reject "<APPROVAL_ID>"

jobos status
jobos dashboard
```

`jobos run` 默认行为：

```text
发现职位
→ 补全
→ 规则过滤
→ 评分
→ 生成高匹配职位材料
→ 根据自动化等级创建审批或执行沟通
→ 同步消息
```

---

# 22. 前端页面

## 22.1 总览

显示：

- 今日发现职位数。
- 符合规则职位数。
- 已生成简历数。
- 待审批数。
- 已沟通数。
- HR 未读消息数。
- 面试数。
- 回复率。
- 各 Provider 登录状态。
- Worker 状态。

## 22.2 职位页面

支持：

- 条件筛选。
- AI 分数和维度分数。
- 匹配技能。
- 缺失技能。
- 硬规则拒绝原因。
- 原始 JD 和标准化 JD 对比。
- 创建申请。
- 忽略职位。

## 22.3 简历页面

支持：

- 基础简历。
- 模板简历。
- 职位定制简历。
- 事实来源。
- 验证结果。
- PDF 预览。
- 手动编辑。
- 锁定事实。
- 批准使用。

## 22.4 消息中心

支持：

- 按平台和职位展示会话。
- 查看消息分类。
- 查看 AI 草稿。
- 查看引用事实。
- 批准、编辑、拒绝。
- 手动发送。
- 风险标签。

## 22.5 审批中心

审批类型：

- 投递审批。
- 简历审批。
- 消息回复审批。
- 薪资审批。
- 面试时间审批。
- 敏感信息审批。
- 登录和 CAPTCHA 处理。

## 22.6 数据分析

指标：

```text
发现职位数
规则通过率
平均匹配分
沟通率
简历发送率
HR 回复率
面试率
Offer 率
按关键词的回复率
按平台的回复率
按简历版本的回复率
平均首次回复时间
```

---

# 23. 配置系统

## 23.1 app.yaml

```yaml
app:
    data_dir: '~/.jobos'
    timezone: 'Asia/Shanghai'
    language: 'zh-CN'
    automation_level: 'L1'

database:
    url: 'sqlite:///~/.jobos/jobos.db'
    wal: true

worker:
    concurrency: 2
    lease_seconds: 300
    heartbeat_seconds: 30

browser:
    executable_path: null
    headless: false
    action_timeout_ms: 15000
    page_timeout_ms: 45000
    screenshot_on_error: true

security:
    redact_logs: true
    encrypt_secrets: true
```

## 23.2 providers.yaml

```yaml
providers:
    boss:
        enabled: true
        account: primary
        max_concurrency: 1
        daily_action_limit: 30
        minimum_action_interval_seconds: 20

    zhaopin:
        enabled: false

    liepin:
        enabled: false

    lagou:
        enabled: false
```

## 23.3 llm.yaml

```yaml
providers:
    openai:
        base_url: '${OPENAI_BASE_URL}'
        api_key: '${OPENAI_API_KEY}'

    gemini:
        api_key: '${GEMINI_API_KEY}'

    local:
        base_url: '${LLM_URL}'
        api_key: '${LLM_API_KEY}'

tasks:
    score_job:
        provider: openai
        model: '${JOBOS_SCORING_MODEL}'

    generate_resume:
        provider: openai
        model: '${JOBOS_RESUME_MODEL}'

    classify_message:
        provider: local
        model: '${JOBOS_CLASSIFIER_MODEL}'
```

---

# 24. 安全和隐私

必须实现：

1. `.env` 不进入 Git。
2. 浏览器 Profile 不进入 Git。
3. 招聘平台密码不写数据库。
4. API Key 使用系统 Keyring 或 DPAPI。
5. 日志自动屏蔽手机号、邮箱、身份证和 Cookie。
6. 页面截图按 Profile 设置保存时间。
7. 高敏感事实不得传给非必要模型。
8. 审计日志不可被普通业务操作修改。
9. Web API 默认仅监听 `127.0.0.1`。
10. 启用远程访问时必须增加身份认证。
11. Prompt 中不得包含无关的全部个人资料。
12. 导出调试包前必须执行脱敏。
13. 数据删除需要覆盖数据库记录和关联文件。
14. 所有自动发送均需要保存最终文本。

---

# 25. 可观测性

## 25.1 日志字段

```json
{
	"timestamp": "",
	"level": "INFO",
	"event": "provider.action.completed",
	"trace_id": "",
	"task_id": "",
	"provider": "boss",
	"account_id": "",
	"job_id": "",
	"application_id": "",
	"duration_ms": 1234,
	"status": "success"
}
```

## 25.2 指标

```text
workflow_tasks_total
workflow_task_duration_seconds
workflow_task_failures_total
provider_actions_total
provider_rate_limits_total
provider_login_required_total
llm_requests_total
llm_tokens_total
llm_schema_failures_total
resume_validation_failures_total
messages_sent_total
applications_submitted_total
```

## 25.3 调试资料

Provider 页面错误时保存：

```text
screenshot.png
page.html
accessibility-tree.json
browser-console.log
network-summary.json
task-context.json
```

其中敏感字段必须脱敏。

---

# 26. 测试策略

## 26.1 单元测试

覆盖：

- 状态机。
- 规则引擎。
- 评分计算。
- 去重。
- 幂等键。
- 数据脱敏。
- Prompt Schema。
- 事实校验。
- 重试策略。
- 租约回收。

最低覆盖率目标：

```text
核心领域和规则模块：90%
全仓库：75%
```

## 26.2 Provider Contract Test

每个 Provider 必须通过相同的合同测试：

```text
check_login
discover_jobs
fetch_job_detail
initiate_contact
send_message
list_conversations
list_messages
```

没有某项能力时必须返回 `CapabilityNotSupported`，不能静默成功。

## 26.3 浏览器 Fixture

将脱敏后的招聘页面保存为本地 Fixture：

```text
search-results.html
job-detail.html
conversation-list.html
conversation-detail.html
login-expired.html
captcha.html
job-expired.html
```

Provider 的大多数测试应针对 Fixture，不应依赖线上页面。

## 26.4 Live Smoke Test

线上测试规则：

- 默认 Dry Run。
- 每次最多测试一个职位。
- 不点击最终提交按钮。
- 不发送真实消息。
- 需要显式环境变量才能开启真实操作：

```text
JOBOS_ALLOW_LIVE_ACTIONS=true
```

## 26.5 E2E 场景

场景一：

```text
导入 JD
→ 匹配评分
→ 检索事实
→ 生成简历
→ 验证通过
→ 创建审批
```

场景二：

```text
BOSS 登录 Profile
→ 搜索远程兼职 Vue 岗位
→ 获取详情
→ 规则过滤
→ 生成沟通材料
→ Dry Run 到发送前
```

场景三：

```text
导入 HR 消息
→ 分类为 availability
→ 检索可用时间
→ 生成回复
→ 自动审批
→ Mock 发送成功
```

场景四：

```text
导入薪资问题
→ 分类为 salary
→ 创建人工审批
→ 未审批前禁止发送
```

场景五：

```text
页面出现验证码
→ ProviderCaptchaDetected
→ 任务进入 manual_required
→ Dashboard 显示人工处理
```

---

# 27. 验收标准

系统完成必须同时满足以下条件。

## 27.1 基础验收

- `jobos doctor` 能检查 Python、Node、Chrome、数据库、模型和 Provider。
- 能创建和编辑 Profile。
- 能导入基础简历。
- 能创建和管理 CandidateFact。
- 能运行 API、Worker 和 Web UI。
- 重启后任务数据不丢失。

## 27.2 职位流程验收

- 能从 BOSS 获取职位列表。
- 能获取职位详情。
- 能按平台职位 ID 去重。
- 能识别兼职、远程、外包相关信息。
- 能按规则拒绝不符合岗位。
- 能输出 0–100 匹配分。
- 每个得分理由可追踪。

## 27.3 简历验收

- 能为职位生成独立简历。
- 公司、学校、日期和真实指标不被修改。
- 每条生成经历关联事实 ID。
- 虚构内容会导致验证失败。
- 能生成可打开的 PDF。
- PDF 文件和数据库记录一致。

## 27.4 自动化验收

- 可以打开独立 Chrome Profile。
- 首次登录由用户手动完成。
- 后续任务能够复用登录状态。
- 登录失效能被识别。
- Dry Run 不执行最终提交或发送。
- 同一职位不会重复沟通或投递。
- CAPTCHA 出现时自动停止。
- 每个动作都留下审计记录。

## 27.5 消息验收

- 能同步会话和消息。
- 相同外部消息不会重复入库。
- 能分类常见 HR 消息。
- 低风险回复可以自动生成。
- 高风险问题必须进入审批。
- 未批准的高风险回复不能发送。
- 发送成功后记录外部消息 ID。

## 27.6 稳定性验收

- Worker 意外退出后任务锁能恢复。
- 浏览器崩溃不会永久占用任务。
- 429 会进入冷却和重试。
- 页面结构变化会生成调试资料。
- 所有副作用接口具备幂等性。
- 单个 Provider 故障不影响其他 Provider。

---

# 28. Codex 工作包

所有工作包共同构成一个完整产品目标，不应被解释为多个互相独立的临时版本。

## WP-001：仓库初始化

**输出：**

- Monorepo 目录。
- Python 和 Node 项目。
- Ruff、mypy、pytest、ESLint、Prettier。
- GitHub Actions。
- 基础 README。

**验收：**

```powershell
python -m pytest
python -m ruff check .
python -m mypy jobos
npm run lint
npm run test
```

全部通过。

## WP-002：配置系统

**输出：**

- Pydantic Settings。
- YAML 加载。
- 环境变量替换。
- 配置 Schema。
- `jobos doctor`。

**验收：**

- 非法配置启动失败并指出字段。
- 密钥不打印。
- Windows 路径正确解析。

## WP-003：数据库和迁移

**输出：**

- SQLAlchemy 模型。
- Alembic 初始化。
- 本规格中的核心表。
- SQLite WAL。
- Repository 层。

**验收：**

- 空数据库可一键初始化。
- 升级和降级迁移可运行。
- PostgreSQL 测试通过。

## WP-004：任务队列和状态机

**输出：**

- WorkflowTask。
- 租约领取。
- Heartbeat。
- 重试。
- 幂等。
- 状态机验证。

**验收：**

- 两个 Worker 不会领取同一任务。
- Worker 崩溃后任务可恢复。
- 非法状态跳转被拒绝。

## WP-005：Profile 和事实系统

**输出：**

- Profile CRUD。
- CandidateFact CRUD。
- 事实权限。
- 敏感性分类。
- 基础简历导入。

**验收：**

- 能检索与职位相关事实。
- Restricted 事实不会进入普通 Prompt。

## WP-006：LLM Gateway

**输出：**

- Provider 接口。
- OpenAI-compatible 实现。
- Gemini 实现。
- Local 实现。
- Schema 解析。
- 重试和用量记录。

**验收：**

- 可通过配置切换 Provider。
- Schema 错误可检测。
- Provider 不可用时可切换备用模型。

## WP-007：规则引擎

**输出：**

- 条件解析。
- 动作执行。
- 规则优先级。
- 兼职规则模板。
- 消息审批规则。

**验收：**

- 硬拒绝规则不能被 AI 分数覆盖。
- 每个决策返回命中的规则 ID。

## WP-008：职位领域服务

**输出：**

- Job 模型。
- 标准化。
- 去重。
- JobScore。
- 手动 URL 和文本导入。

**验收：**

- 同一职位不会重复创建。
- 原始内容和标准化内容均保留。

## WP-009：Provider 基础框架

**输出：**

- ProviderAdapter。
- Capability。
- Registry。
- 标准异常。
- Contract Test。

**验收：**

- Mock Provider 通过全部合同测试。

## WP-010：Browser Runtime

**输出：**

- ProfileManager。
- SessionManager。
- CDP 端口管理。
- ActionExecutor。
- Snapshot。
- RiskDetector。

**验收：**

- Windows 可启动和关闭独立 Chrome。
- 进程异常退出后能清理。
- CAPTCHA Fixture 能被识别。

## WP-011：BOSS 登录和搜索

**输出：**

- `boss.check_login`。
- `boss.discover_jobs`。
- 选择器配置。
- 本地页面 Fixture。

**验收：**

- 未登录返回 `ProviderLoginRequired`。
- 登录后可解析职位列表。
- 不执行发送或投递动作。

## WP-012：BOSS 职位详情

**输出：**

- 职位详情抓取。
- 公司信息抓取。
- 工作方式和职位类型解析。
- 过期职位检测。

**验收：**

- 输出标准 `RawJobDetail`。
- 页面变化时生成调试包。

## WP-013：职位评分

**输出：**

- 硬规则预判。
- Evidence Pack。
- LLM 评分。
- 维度分。
- Prompt 版本管理。

**验收：**

- 输出符合 Schema。
- 评分理由包含证据 ID。
- 缺少模型时能明确失败。

## WP-014：简历生成和验证

**输出：**

- Resume Generator。
- Fact Validator。
- Skill Boundary。
- 模型泄漏检查。
- 指标一致性检查。

**验收：**

- 虚构公司、项目、学历和技术栈会失败。
- 合法定制可以通过。

## WP-015：PDF 渲染

**输出：**

- HTML 模板。
- Vue/C#/Python 技术简历模板。
- Playwright PDF。
- 页面溢出检查。

**验收：**

- PDF 可正常打开。
- 不截断联系方式和核心经历。
- 支持中文字体环境。

## WP-016：申请审批

**输出：**

- Application Service。
- ApprovalRequest。
- L0–L3 策略。
- 投递前检查。

**验收：**

- L1 下未经批准不能提交。
- L3 下命中高风险规则仍然必须审批。

## WP-017：BOSS 发起沟通

**输出：**

- initiate_contact。
- 开场语发送。
- 简历发送。
- 幂等检查。
- Dry Run。

**验收：**

- Dry Run 停在最终发送前。
- 已沟通过职位不会重复发送。
- 登录失效或验证码时立即停止。

## WP-018：消息同步

**输出：**

- 会话列表同步。
- 消息同步。
- 外部 ID 去重。
- 未读数更新。

**验收：**

- 重复同步不产生重复消息。
- 会话和职位正确关联。

## WP-019：消息分类和回复

**输出：**

- Message Classifier。
- Risk Classifier。
- Reply Generator。
- Evidence 引用。
- 自动审批策略。

**验收：**

- 薪资、Offer、合同必须人工处理。
- 可用时间问题可自动生成事实型回复。

## WP-020：消息发送

**输出：**

- send_message。
- 幂等键。
- 发送前复核。
- 结果同步。

**验收：**

- 同一回复不会重复发送。
- 修改后的人工回复以最终版本为准。

## WP-021：FastAPI

**输出：**

- 本规格中的 API。
- OpenAPI。
- WebSocket 事件。
- 本地身份保护。

**验收：**

- API 测试覆盖关键流程。
- 默认仅监听本机。

## WP-022：Vue Dashboard

**输出：**

- 总览。
- 职位。
- 简历。
- 申请。
- 消息。
- 审批。
- 系统状态。
- Provider 登录。

**验收：**

- 能完成一次完整人工审批。
- Worker 状态实时更新。

## WP-023：分析和优化

**输出：**

- 回复率。
- 面试率。
- 平台效果。
- 关键词效果。
- 简历版本效果。
- 每日摘要。

**验收：**

- 统计数据可从测试数据正确计算。
- 不将相关性误报为因果关系。

## WP-024：E2E 和操作文档

**输出：**

- 完整 E2E。
- Windows 安装脚本。
- 初始化文档。
- Provider 调试文档。
- 数据备份和恢复文档。

**验收：**

新 Windows 环境可按照 README 完成：

```text
安装
→ 初始化
→ 手动登录 BOSS
→ 导入简历
→ 发现职位
→ 生成定制简历
→ Dry Run 沟通
→ 查看审批和日志
```

---

# 29. Codex 开发规则

Codex 执行任何工作包时必须遵守：

1. 开始前阅读本规格。
2. 只处理当前工作包。
3. 不擅自改变架构和技术栈。
4. 不删除已有测试。
5. 不通过放宽断言让测试通过。
6. 每个公开接口必须有类型标注。
7. 每个数据库变化必须提供迁移。
8. 每个 Provider 动作必须支持 Dry Run。
9. 每个副作用操作必须有幂等键。
10. 不把密钥、Cookie、Profile 或真实简历提交到仓库。
11. 不在代码中写死用户信息。
12. 不绕过 CAPTCHA。
13. 不使用宽泛 `except Exception` 吞掉错误。
14. 错误必须映射成领域异常。
15. 完成后运行测试、类型检查和静态检查。
16. 最终报告列出修改文件、测试结果、遗留问题和风险。

---

# 30. 交给 Codex 的总控提示词

```text
你正在开发 JobOS-CN，一个本地优先、面向国内兼职和远程岗位的 AI 求职操作系统。

项目的唯一架构依据是：
docs/AI_JOB_OS_EXECUTION_SPEC.md

执行规则：

1. 首先完整阅读规格文件。
2. 检查当前仓库状态、已有代码、测试和迁移。
3. 输出当前工作包的简短实施计划。
4. 只实现用户指定的工作包，不提前实现后续工作包。
5. 必须遵守规格中的领域边界、状态机、Provider 接口、安全规则、幂等规则和 Dry Run 规则。
6. 不允许绕过 CAPTCHA、登录验证、平台风控或人工审批。
7. 不允许在代码中写死任何个人资料、API Key、Cookie 或招聘平台账号。
8. LLM 仅用于语义任务，状态流转、规则、安全和副作用操作必须由确定性代码控制。
9. 所有生成内容必须使用 CandidateFact 和 evidence_id，禁止生成无事实依据的履历内容。
10. 所有数据库修改必须包含 Alembic 迁移。
11. 所有新增代码必须包含测试。
12. 结束前运行项目约定的 lint、type check 和 test。
13. 不通过删除测试、跳过测试或降低断言来完成任务。
14. 输出：
    - 实现摘要
    - 修改文件
    - 数据库迁移
    - 测试结果
    - 手工验证步骤
    - 已知限制
    - 下一工作包的依赖情况

当前工作包：
<在这里填写 WP 编号和名称>

验收标准：
<从规格中复制该工作包的验收标准>
```

---

# 31. Definition of Done

只有满足以下全部条件，工作包才可以标记完成：

```text
[ ] 功能符合规格
[ ] 数据模型符合规格
[ ] 状态流转合法
[ ] 具备幂等性
[ ] 支持 Dry Run
[ ] 具备结构化日志
[ ] 错误映射为领域异常
[ ] 单元测试通过
[ ] 集成测试通过
[ ] 类型检查通过
[ ] 静态检查通过
[ ] 无密钥和隐私数据进入 Git
[ ] 文档已更新
[ ] 手工验收步骤可复现
```

---

# 32. 最终技术决策

1. ApplyPilot 不作为未来架构中心，仅作为参考实现。
2. 新系统采用独立领域模型和 Provider 插件架构。
3. 生产浏览器自动化以 Playwright 确定性执行为主。
4. Codex 用于开发系统，不作为必须绑定的生产运行时。
5. Claude Code、OpenAI、Gemini 或本地模型均通过适配器接入。
6. 登录状态通过独立持久化 Chrome Profile 保存。
7. 个人浏览器自动化不需要招聘平台开发人员配合。
8. 官方 API 作为可选 Provider，不作为基础依赖。
9. 所有简历和回复必须由事实系统约束。
10. 默认人工审批，逐步调整自动化等级。
11. SQLite 支持本地使用，PostgreSQL 支持未来部署。
12. Vue 3 Dashboard 作为主要操作入口。
13. 所有平台动作可审计、可中断、可恢复。
14. 不绕过验证码、风控或平台安全机制。
15. 系统优化目标不是投递数量最大化，而是有效沟通率和兼职收入机会最大化。

实施时，先把本文保存进新仓库，再将第 30 节总控提示词交给 Codex，并指定从 `WP-001` 开始。
