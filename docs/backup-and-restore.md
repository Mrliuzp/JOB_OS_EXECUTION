# 数据备份与恢复

## 备份范围

默认备份 `~/.jobos`，包括数据库、配置、生成简历、审计日志和平台 Profile。备份文件可能包含敏感信息，应保存在受控磁盘并加密。

## 备份

```powershell
.\scripts\backup.ps1
```

## 恢复

先停止 API、Worker 和所有 Chrome 任务，再执行：

```powershell
.\scripts\restore.ps1 -ArchivePath .\backups\jobos-backup-YYYYMMDD-HHMMSS.zip
```

恢复完成后运行：

```powershell
jobos doctor
python -m alembic upgrade head
```
