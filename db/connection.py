"""Connection helper to obtain SQLAlchemy engine for the project.
This file centralizes the logic to find/build a DB engine. It attempts to call
existing helper functions in other modules (preferred order) so we don't
duplicate configuration. If none are found it raises.
"""
from typing import Optional


def ensure_engine() -> object:
    """Return a SQLAlchemy engine-like object.

    Tries several known engine builders used in the repo. Returns the first
    working engine. Caller should handle exceptions.
    """
    # Try commonly used helpers in repo modules in order
    try:
        import fractal_breaks as fb
        if hasattr(fb, '_ensure_engine'):
            return fb._ensure_engine()
    except Exception:
        pass

    try:
        import rsi_fractals as rf
        if hasattr(rf, '_ensure_engine'):
            return rf._ensure_engine()
    except Exception:
        pass

    try:
        import import_nifty_index as ini
        if hasattr(ini, 'build_engine'):
            return ini.build_engine()
    except Exception:
        pass

    try:
        import reporting_adv_decl as rad
        if hasattr(rad, 'engine'):
            return rad.engine()
    except Exception:
        pass

    raise RuntimeError('No DB engine provider found; please provide one or extend db.connection.ensure_engine')
