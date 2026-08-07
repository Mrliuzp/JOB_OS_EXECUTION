# Provider 开发指南

## 实现步骤

1. 继承或实现 `ProviderAdapter` 协议。
2. 声明 `ProviderCapabilities`，不支持的能力必须抛出 `CapabilityNotSupported`。
3. 使用平台外部职位 ID 和规范化 URL。
4. 页面选择器优先采用 ARIA、可见文本和稳定 `data-*` 属性。
5. 为搜索、详情、会话、消息、登录过期、验证码和职位过期保存脱敏 Fixture。
6. 所有发送、上传和提交动作接收 `dry_run` 与 `idempotency_key`。
7. 检测到验证码、滑块、访问过频或重新登录提示时立即停止。
8. 通过统一 Provider Contract Test。

## 禁止事项

- 不保存账号密码。
- 不尝试破解验证码。
- 不调用 LLM 决定权限或审批。
- 不绕过平台限流。
- 不在日志中保存 Cookie、完整页面隐私数据或简历原文。
