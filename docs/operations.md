# 运行与维护

## 进程

- API：`jobos api`
- Worker：`jobos worker`
- Dashboard：`cd apps/web; npm run dev`

## 故障恢复

Worker 使用数据库租约。进程意外退出后，租约到期的任务会进入 `retry_wait` 并可由其他 Worker 领取。浏览器进程退出后应调用 `cleanup_dead` 清理 Profile 锁和 Singleton 文件。

## 页面变化

出现 `ProviderPageChanged` 时检查 `debug-snapshots/<trace_id>` 下的脱敏 HTML、可访问性树和任务上下文。更新选择器 YAML 和本地 Fixture 后再运行合同测试。

## 真实动作上线检查

1. Provider 登录状态有效。
2. CAPTCHA 和风控检测正常。
3. Daily Limit 已配置。
4. 申请已批准。
5. 简历验证状态为 `valid`。
6. Dry Run 已成功执行。
7. 仅在用户明确操作时启用真实动作。
