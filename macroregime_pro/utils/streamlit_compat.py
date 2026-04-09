from __future__ import annotations

try:
    import streamlit as st  # type: ignore
except Exception:  # pragma: no cover
    class _DummyStreamlit:
        @staticmethod
        def cache_data(*args, **kwargs):
            def decorator(fn):
                return fn
            return decorator
    st = _DummyStreamlit()

__all__ = ["st"]
