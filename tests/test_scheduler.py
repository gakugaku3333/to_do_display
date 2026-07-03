from __future__ import annotations

import glob
import os

from unittest.mock import patch

from app import scheduler


def test_backup_database_creates_copy_and_rotates(tmp_path, monkeypatch):
    db_path = tmp_path / "dashboard.db"
    db_path.write_text("dummy sqlite content")
    backup_dir = tmp_path / "backups"

    monkeypatch.setattr(scheduler, "DB_PATH", str(db_path))
    monkeypatch.setattr(scheduler, "BACKUP_DIR", str(backup_dir))
    monkeypatch.setattr(scheduler, "BACKUP_KEEP", 2)

    # 3世代分の古いバックアップが既にある状態から実行し、2世代までローテーションされることを確認
    os.makedirs(backup_dir, exist_ok=True)
    for day in ("2026-01-01", "2026-01-02", "2026-01-03"):
        (backup_dir / f"dashboard-{day}.db").write_text("old")

    with patch("app.scheduler.date") as mock_date:
        mock_date.today.return_value.isoformat.return_value = "2026-01-04"
        scheduler.backup_database()

    backups = sorted(glob.glob(os.path.join(backup_dir, "dashboard-*.db")))
    assert len(backups) == 2
    assert backups[-1].endswith("dashboard-2026-01-04.db")


def test_backup_database_noop_when_db_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(scheduler, "DB_PATH", str(tmp_path / "missing.db"))
    backup_dir = tmp_path / "backups"
    monkeypatch.setattr(scheduler, "BACKUP_DIR", str(backup_dir))

    scheduler.backup_database()

    assert not backup_dir.exists()


def test_get_sync_status_has_all_sources():
    status = scheduler.get_sync_status()
    assert set(status.keys()) == {"calendar", "reminders", "weather"}
    for source in status.values():
        assert "success_at" in source
        assert "error" in source
