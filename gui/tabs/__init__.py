# tabs package - individual tab builders live here
try:
    from .fractals import build_fractals_tab
    __all__ = ["build_fractals_tab"]
except ImportError:
    __all__ = []

try:
    from .trends import build_trends_tab
    __all__.append("build_trends_tab")
except ImportError:
    pass
