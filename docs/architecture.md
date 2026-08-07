# JobOS-CN 架构说明

## 分层

1. Vue Dashboard：职位、简历、申请、消息、审批、平台和分析。
2. FastAPI：本地 API、OpenAPI 和 Worker 状态 WebSocket。
3. Workflow Orchestrator：持久化任务、租约、重试、幂等和恢复。
4. 领域服务：发现、补全、评分、简历、申请、沟通和分析。
5. 规则引擎：硬拒绝、自动化等级、消息风险和额度控制。
6. Provider：BOSS、智联、猎聘、拉勾、通用网页和手动导入。
7. Browser Runtime：独立 Profile、Chrome 进程、CDP 和受控动作。
8. LLM Gateway：OpenAI-compatible、Gemini 和本地模型。
9. Memory：CandidateFact、Evidence Pack 和 Codex Memory 适配。
10. SQLite/PostgreSQL：领域数据、任务和审计日志。

## 关键边界

- Provider 不直接访问业务 Repository，也不决定职位是否值得投递。
- LLM 不负责状态流转、审批、安全规则和副作用执行。
- 所有生成内容必须携带 evidence_id。
- 所有副作用操作必须支持 Dry Run 和幂等键。
- CAPTCHA、登录过期和平台风控统一进入人工处理。

## 数据状态

职位按 `discovered → enriched → filtered → eligible → scored` 流转；申请按 `planned → materials_ready → awaiting_approval → approved → communicating → submitted` 流转。非法迁移由状态机拒绝。
