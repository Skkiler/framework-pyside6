# ui/core/utils/guard.py

def assert_true(cond: bool, msg: str = "Invalid state"):
    if not cond:
        raise AssertionError(msg)

def safe_call(fn, *a, **kw):
    try:
        return fn(*a, **kw)
    except Exception as e:  # noqa: BLE001
        print("[WARN] safe_call:", e)
