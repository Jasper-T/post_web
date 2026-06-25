from __future__ import annotations

import warnings

from backend.pipeline_core import get_pipeline_display_name, get_pipeline_names_list


warnings.warn(
    "config.py is deprecated. Use backend.pipeline_core and the external data directory instead.",
    DeprecationWarning,
    stacklevel=2,
)


PIPELINES = {
    name: None
    for name in get_pipeline_names_list()
}

CHNAMES = {
    name: get_pipeline_display_name(name)
    for name in get_pipeline_names_list()
}


__all__ = ["PIPELINES", "CHNAMES"]
