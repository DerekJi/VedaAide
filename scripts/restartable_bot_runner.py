#!/usr/bin/env python3
"""
本地 bot 启动器：支持手动热重启。

用法：
  py scripts/restartable_bot_runner.py

按键：
  Ctrl+R  重启 bot 进程
  Ctrl+C  退出启动器
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import threading
import time
from typing import Optional


def _terminate_process(proc: subprocess.Popen) -> None:
    """尽量优雅地终止子进程，超时后强杀。"""
    if proc.poll() is not None:
        return

    try:
        if os.name == "nt":
            proc.terminate()
        else:
            proc.send_signal(signal.SIGTERM)
        proc.wait(timeout=5)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass


def _keyboard_watcher(restart_event: threading.Event, stop_event: threading.Event) -> None:
    """监听键盘 Ctrl+R（ASCII 18）请求重启。"""
    if os.name == "nt":
        import msvcrt

        while not stop_event.is_set():
            if not msvcrt.kbhit():
                time.sleep(0.05)
                continue
            ch = msvcrt.getch()
            if ch == b"\x12":  # Ctrl+R
                restart_event.set()
            elif ch == b"\x03":  # Ctrl+C
                stop_event.set()
                return
    else:
        import termios
        import tty

        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            while not stop_event.is_set():
                ch = sys.stdin.read(1)
                if not ch:
                    continue
                if ord(ch) == 18:  # Ctrl+R
                    restart_event.set()
                elif ord(ch) == 3:  # Ctrl+C
                    stop_event.set()
                    return
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


def _build_env() -> dict[str, str]:
    env = os.environ.copy()
    env.setdefault("OLLAMA_URL", "http://localhost:11434")
    env.setdefault("DB_URL", "http://localhost:5000")
    return env


def main() -> int:
    restart_event = threading.Event()
    stop_event = threading.Event()

    print("[bot:watch] Starting VedaAide bot runner")
    print("[bot:watch] Ctrl+R to restart bot, Ctrl+C to quit")

    t = threading.Thread(target=_keyboard_watcher, args=(restart_event, stop_event), daemon=True)
    t.start()

    cmd = [sys.executable, "-m", "bot_app.main"]
    env = _build_env()

    proc: Optional[subprocess.Popen] = None
    try:
        while not stop_event.is_set():
            if proc is None or proc.poll() is not None:
                proc = subprocess.Popen(cmd, env=env)
                print(f"[bot:watch] Bot started with PID {proc.pid}")

            if restart_event.is_set():
                restart_event.clear()
                print("\n[bot:watch] Ctrl+R received, restarting bot...")
                _terminate_process(proc)
                proc = None
                continue

            if proc.poll() is not None:
                code = proc.returncode
                print(f"[bot:watch] Bot exited with code {code}, restarting in 1s...")
                time.sleep(1)
                proc = None
                continue

            time.sleep(0.1)

    except KeyboardInterrupt:
        pass
    finally:
        stop_event.set()
        if proc is not None:
            _terminate_process(proc)
        print("\n[bot:watch] Runner stopped")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
