"""Shared tokens for isolated HTML components and Plotly; CSS is the source."""

from pathlib import Path
import re
from plotly.graph_objects import Figure


TOKEN_CSS = Path(__file__).with_name("design_tokens.css").read_text(encoding="utf-8")
TOKENS = dict(re.findall(r"--hr-([\w-]+):\s*([^;]+);", TOKEN_CSS))


def token(name: str) -> str:
    """Fail on unknown names rather than silently introducing a new style."""
    return TOKENS[name]


def apply_chart_theme(figure: Figure) -> Figure:
    """Apply shared presentation without changing chart data or its semantics."""
    figure.update_layout(
        paper_bgcolor=token("white"), plot_bgcolor=token("white"),
        font={"family": token("font"), "size": int(token("text-body").removesuffix("px")), "color": token("ink")},
        colorway=[token(name) for name in ("accent", "chart-secondary", "chart-tertiary", "chart-quaternary")],
        title_font={"size": int(token("text-card").removesuffix("px")), "color": token("ink")},
        margin={"l": 48, "r": 24, "t": 56, "b": 48},
    )
    figure.update_xaxes(gridcolor=token("line"), zerolinecolor=token("line"))
    figure.update_yaxes(gridcolor=token("line"), zerolinecolor=token("line"))
    return figure


COPY_BUTTON_CSS = TOKEN_CSS + """
body { margin: 0; font-family: var(--hr-font); display: flex; justify-content: flex-end;
       align-items: center; gap: var(--hr-space-2); }
button { min-height: var(--hr-control-height); padding: var(--hr-space-2) var(--hr-space-4);
         border: 1px solid var(--hr-control-line); border-radius: var(--hr-control-radius);
         background: var(--hr-white); color: var(--hr-ink); cursor: pointer;
         font-size: var(--hr-text-body); font-family: var(--hr-font); }
button:hover { background: var(--hr-hover); border-color: var(--hr-accent); }
button:focus-visible { outline: 2px solid var(--hr-focus); outline-offset: 2px; }
span { color: var(--hr-muted); font-size: var(--hr-text-xs); white-space: nowrap; }
"""
