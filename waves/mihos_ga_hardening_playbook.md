# MIHOS GA Hardening Playbook

This checklist gates GA rollout after the recent search/normalization waves.

## 1) Performance target (P95 find)

- Target: `find` P95 <= **80ms** on MIHOS dataset.
- Command:
  - `D:/GoBP/venv/Scripts/python.exe scripts/mihos_find_p95_check.py --root D:/MIHOS-v1 --runs 30 --target-p95-ms 80`
- Artifact:
  - `.gobp/history/mihos_find_p95.json`
- Gate:
  - `ok=true` and `p95_ms <= target_p95_ms`

## 2) Health checks + alerting

- Run health check:
  - `D:/GoBP/venv/Scripts/python.exe scripts/mihos_health_check.py --root D:/MIHOS-v1`
- Optional alerting:
  - set `ALERT_WEBHOOK_URL`
  - failing health check posts JSON payload to webhook
- Artifact:
  - `.gobp/history/mihos_health_check.json`
- Gate:
  - `ok=true`
  - `find: session` does not leak Session
  - `find:Session` returns Session

## 3) Rollback + backup/restore drill

- Run drill:
  - `D:/GoBP/venv/Scripts/python.exe scripts/mihos_backup_restore_drill.py --root D:/MIHOS-v1 --backup-dir D:/MIHOS-backups`
- Artifact:
  - `.gobp/history/mihos_backup_restore_drill.json`
- Gate:
  - `ok=true`
  - restored node/edge counts equal source

## 4) Rollout order

1. Run full tests in repo:
   - `D:/GoBP/venv/Scripts/python.exe -m pytest tests/ -q --tb=no`
2. Run perf gate
3. Run health gate
4. Run backup/restore gate
5. If all green, proceed with GA rollout

## 5) Rollback procedure

If post-release health check fails:

1. Freeze writes to MIHOS GoBP
2. Restore latest backup into standby path
3. Validate restored graph with `mihos_health_check.py`
4. Switch service/project root to restored snapshot
5. Re-run full health check and notify stakeholders
