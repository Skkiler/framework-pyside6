# ui/services/task_runner_adapter.py

import inspect
from typing import Dict, Any

class TaskRunnerAdapter:
    def __init__(self, obj):
        self._obj = obj

    def run_task(self, name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        fn = getattr(self._obj, "run_task", None)
        if not callable(fn):
            return {"ok": False, "error": "run_task não encontrado no runner"}
        result = fn(name, payload)
        if inspect.iscoroutine(result):
            # Bloqueio simples: se quiser, troque por loop/asyncio ou QEventLoop
            import asyncio
            result = asyncio.get_event_loop().run_until_complete(result)
        if isinstance(result, dict) and "ok" in result:
            return result
        return {"ok": True, "data": result}
