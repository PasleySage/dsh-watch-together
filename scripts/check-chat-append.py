"""`append_user` 在 EACCES 下要能自愈：python scripts/check-chat-append.py

社区 issue（dsh-see-now#75）：同一台机器上 PowerShell 能写 chat.jsonl、Python append 报
`Permission denied`。`append_user` 现在失败时会"整份读出来 + 新行写成临时文件再 os.replace"，
用目录继承的 ACL 把坏文件换掉。这个脚本把两条路都钉住：

  1. 正常 append：只多一行，历史不动
  2. append 抛 PermissionError：仍然写得进去，历史一行不丢，临时文件不残留
  3. 连 replace 都失败：把**第一个** PermissionError 抛给上层（状态栏要显示真因），临时文件清掉
"""
from __future__ import annotations

import builtins
import json
import os
import sys
import tempfile
import types
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "examples" / "floating-chat"))

# 本机可能没装 mss（窗口只在抓屏时才用它，模块顶层却 import）
if "mss" not in sys.modules:
    stub = types.ModuleType("mss")
    stub.mss = lambda *a, **k: None
    sys.modules["mss"] = stub

tmp = Path(tempfile.mkdtemp(prefix="chat-append-"))
os.environ["DSH_VIDEO_CACHE_DIR"] = str(tmp)
os.environ["DSH_HOME"] = str(tmp / "home")

import window  # noqa: E402

failures: list[str] = []


def check(name, cond, detail=""):
    if not cond:
        failures.append(f"{name}{(': ' + detail) if detail else ''}")


def reset(text="历史一行\n"):
    (tmp / "chat.jsonl").write_text(text, encoding="utf-8")


def lines():
    return (tmp / "chat.jsonl").read_text(encoding="utf-8").splitlines()


def check_normal():
    reset()
    window.append_user("正常一句")
    got = lines()
    check(len(got) == 2, f"正常 append 只多一行（{len(got)}）")
    check(json.loads(got[-1])["text"] == "正常一句", "最后一行是新消息")
    check(json.loads(got[-1])["role"] == "user", "role 是 user")
    check(not list(tmp.glob("*.tmp")), "正常路径不留临时文件")


def check_self_heal():
    reset("assistant 写的\n")
    real_open = builtins.open
    target = Path(window.CHAT_FILE)

    def blocked(file, mode="r", *a, **k):
        if "a" in str(mode) and Path(file) == target:
            raise PermissionError(13, "Permission denied", str(file))
        return real_open(file, mode, *a, **k)

    builtins.open = blocked
    try:
        window.append_user("坏了也要发出去")
    except Exception as exc:                     # noqa: BLE001
        check("append 被拒后仍能写进去", False, repr(exc))
    finally:
        builtins.open = real_open
    got = lines()
    check(len(got) == 2, f"自愈后历史 + 1 行（{len(got)}）")
    check(got[0] == "assistant 写的", "历史一行没丢")
    check(json.loads(got[-1])["text"] == "坏了也要发出去", "新消息真的落盘了")
    check(not list(tmp.glob("*.tmp")), "自愈路径不留临时文件")


def check_replace_fails():
    reset()
    real_open = builtins.open
    real_replace = os.replace
    target = Path(window.CHAT_FILE)

    def blocked(file, mode="r", *a, **k):
        if "a" in str(mode) and Path(file) == target:
            raise PermissionError(13, "Permission denied", "append")
        return real_open(file, mode, *a, **k)

    def no_replace(src, dst, *a, **k):
        raise PermissionError(13, "Permission denied", "replace")

    builtins.open = blocked
    os.replace = no_replace
    try:
        window.append_user("写不进去")
        check("replace 也失败时要抛出", False, "没抛异常")
    except PermissionError as exc:
        check("抛的是 append 那条 PermissionError", "append" in str(exc), str(exc))
    except Exception as exc:                      # noqa: BLE001
        check("抛的是 PermissionError", False, repr(exc))
    finally:
        builtins.open = real_open
        os.replace = real_replace
    check(not list(tmp.glob("*.tmp")), "失败路径也要清掉临时文件")
    check(lines() == ["历史一行"], "失败时不动原文件")


def main() -> int:
    check_normal()
    check_self_heal()
    check_replace_fails()
    if failures:
        print(f"FAIL: {len(failures)} 项")
        for f in failures:
            print("  -", f)
        return 1
    print("OK: 正常 append / EACCES 自愈 / 连 replace 都失败时抛真因")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
