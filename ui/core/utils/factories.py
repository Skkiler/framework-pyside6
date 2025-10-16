# ui/core/utils/factories.py

from __future__ import annotations
import inspect

def call_with_known_kwargs(factory, /, **deps):
    """Chama a factory apenas com kwargs que ela aceita (DIP)."""
    params = inspect.signature(factory).parameters
    use = {k: v for k, v in deps.items() if k in params}
    return factory(**use)
