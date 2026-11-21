"""顶边缩放与输入框选字的回归：python scripts/check-input-select.py"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "examples" / "floating-chat"))

CHAR_W = 10

failures: list[str] = []


def check(name, cond, detail=""):
    if not cond:
        failures.append(f"{name}{(': ' + detail) if detail else ''}")


class FakeFont:
    def measure(self, s):
        return len(s) * CHAR_W


class FakeFonts:
    def get(self, _size, _bold=False):
        return FakeFont()


class FakeRoot:
    def __init__(self, w, h):
        self.w, self.h = w, h

    def winfo_width(self):
        return self.w

    def winfo_height(self):
        return self.h


def stub(w=760, h=560):
    from window import LiveGlass

    s = object.__new__(LiveGlass)
    s.root = FakeRoot(w, h)
    s.fonts = FakeFonts()
    return s


def check_top_edge():
    import window
    from window import LiveGlass

    s = stub()
    w = s.root.w
    top = getattr(window, "TOP_EDGE_PX", 14)
    for x in (40, w // 2, w - 40):
        check(f"顶边 y=0 x={x} 往上拉", LiveGlass._edge_at(s, x, 0) == "n",
              repr(LiveGlass._edge_at(s, x, 0)))
        check(f"顶边 y={top} x={x} 往上拉", LiveGlass._edge_at(s, x, top) == "n")
        check(f"顶边 y={top + 1} x={x} 拖窗", LiveGlass._edge_at(s, x, top + 1) is None,
              repr(LiveGlass._edge_at(s, x, top + 1)))
    check("左上角", LiveGlass._edge_at(s, 5, 5) == "nw")
    check("右上角", LiveGlass._edge_at(s, w - 5, 5) == "ne")
    check("右边", LiveGlass._edge_at(s, w - 3, 300) == "e")
    check("左边", LiveGlass._edge_at(s, 3, 300) == "w")
    check("底边", LiveGlass._edge_at(s, 300, s.root.h - 3) == "s")
    check("中间", LiveGlass._edge_at(s, 300, 300) is None)
    check("命中带不压到标题栏 item", top < 17, f"TOP_EDGE_PX={top}")


def check_index_at():
    from window import LiveGlass

    if not hasattr(LiveGlass, "_input_index_at"):
        check("点击定位", False, "LiveGlass 没有 _input_index_at")
        return
    s = stub()
    x0 = 100
    s._input_view = (x0, 0, "abcdef")
    cases = {x0 - 50: 0, x0: 0, x0 + 4: 0, x0 + 5: 1, x0 + 14: 1, x0 + 15: 2,
             x0 + 59: 6, x0 + 500: 6}
    for px, want in cases.items():
        got = LiveGlass._input_index_at(s, px)
        check(f"可见段从 0 起 px={px}", got == want, f"got {got} want {want}")
    s._input_view = (x0, 7, "hijk")
    check("可见段偏移 px=x0", LiveGlass._input_index_at(s, x0) == 7)
    check("可见段偏移 px=x0+25", LiveGlass._input_index_at(s, x0 + 25) == 10)
    check("可见段偏移 末尾", LiveGlass._input_index_at(s, x0 + 999) == 11)
    s._input_view = None
    check("没有视图时返回 0", LiveGlass._input_index_at(s, 123) == 0)


def check_ctrl_a():
    try:
        import tkinter as tk
        root = tk.Tk()
    except Exception as exc:
        print(f"SKIP: Ctrl+A 需要 Tk（{type(exc).__name__}）")
        return
    try:
        from window import LiveGlass

        if not hasattr(LiveGlass, "_input_select_all"):
            check("Ctrl+A 全选", False, "LiveGlass 没有 _input_select_all")
            return
        root.geometry("200x40+-3000+-3000")
        entry = tk.Entry(root)
        entry.pack()
        s = object.__new__(LiveGlass)
        s._entry = entry
        s._render_input = lambda: None
        for seq in ("<Control-a>", "<Control-A>"):
            entry.bind(seq, lambda e: LiveGlass._input_select_all(s, e))
        entry.insert(0, "你好世界 hello")
        entry.icursor(3)
        root.update()
        entry.focus_force()
        root.update()
        entry.event_generate("<Control-a>")
        root.update()
        sel = (entry.index("sel.first"), entry.index("sel.last")) if entry.select_present() else None
        check("Ctrl+A 选中全文", sel == (0, len("你好世界 hello")), repr(sel))
        check("Ctrl+A 后插入点在末尾", entry.index("insert") == len("你好世界 hello"))
    finally:
        root.destroy()


def main() -> int:
    check_top_edge()
    check_index_at()
    check_ctrl_a()
    if failures:
        print(f"FAIL: {len(failures)} 项")
        for f in failures:
            print("  -", f)
        return 1
    print("OK: 顶边可往上拉、标题栏照样拖窗、点击定位下标正确、Ctrl+A 全选")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
