# -*- coding: utf-8 -*-
"""跨平台 data_dir 独占写锁（OS 文件锁，进程退出自动释放）。"""

from __future__ import annotations

import json
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class LockConflictError(RuntimeError):
    """同一 data_dir 已被其他写入实例占用。"""

    def __init__(self, message: str, *, holder: dict[str, Any] | None = None):
        super().__init__(message)
        self.holder = holder or {}
        self.code = "lock_conflict"


@dataclass
class ProcessLock:
    path: Path
    instance_id: str
    data_dir: Path
    _fh: Any = None

    @classmethod
    def for_data_dir(cls, data_dir: Path, *, instance_id: str) -> "ProcessLock":
        root = Path(data_dir).resolve()
        lock_path = root / "runtime" / "service.lock"
        return cls(path=lock_path, instance_id=instance_id, data_dir=root)

    def _meta(self) -> dict[str, Any]:
        return {
            "pid": os.getpid(),
            "instance_id": self.instance_id,
            "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "data_dir": str(self.data_dir),
            "lock_path": str(self.path),
        }

    def _read_holder(self) -> dict[str, Any]:
        try:
            raw = self.path.read_text(encoding="utf-8").strip()
            if not raw:
                return {}
            return json.loads(raw)
        except (OSError, json.JSONDecodeError):
            return {}

    def acquire(self, *, blocking: bool = False) -> dict[str, Any]:
        if self._fh is not None:
            return self._meta()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # 保持句柄打开；锁随进程/句柄释放
        self._fh = open(self.path, "a+b")  # noqa: SIM115
        try:
            self._fh.seek(0)
            if sys.platform == "win32":
                import msvcrt

                # 锁文件首字节；非阻塞失败即冲突
                mode = msvcrt.LK_LOCK if blocking else msvcrt.LK_NBLCK
                try:
                    msvcrt.locking(self._fh.fileno(), mode, 1)
                except OSError as exc:
                    holder = self._read_holder()
                    self.release()
                    raise LockConflictError(
                        f"data_dir locked by another process: {self.data_dir}",
                        holder=holder,
                    ) from exc
            else:
                import fcntl

                flags = fcntl.LOCK_EX
                if not blocking:
                    flags |= fcntl.LOCK_NB
                try:
                    fcntl.flock(self._fh.fileno(), flags)
                except OSError as exc:
                    holder = self._read_holder()
                    self.release()
                    raise LockConflictError(
                        f"data_dir locked by another process: {self.data_dir}",
                        holder=holder,
                    ) from exc

            meta = self._meta()
            payload = (json.dumps(meta, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
            self._fh.seek(0)
            self._fh.truncate(0)
            # 保留首字节给 msvcrt 锁区域，元数据从偏移 1 写入
            self._fh.write(b"\0" + payload)
            self._fh.flush()
            return meta
        except Exception:
            self.release()
            raise

    def release(self) -> None:
        fh = self._fh
        self._fh = None
        if fh is None:
            return
        try:
            if sys.platform == "win32":
                import msvcrt

                try:
                    fh.seek(0)
                    msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)
                except OSError:
                    pass
            else:
                import fcntl

                try:
                    fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
                except OSError:
                    pass
        finally:
            try:
                fh.close()
            except OSError:
                pass

    def __enter__(self) -> "ProcessLock":
        self.acquire()
        return self

    def __exit__(self, *args: object) -> None:
        self.release()
