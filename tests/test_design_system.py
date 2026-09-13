"""Guard the shared theme across native widgets, pages, charts and iframes."""

from pathlib import Path
import re
import tomllib

import plotly.graph_objects as go

from services.design_system import COPY_BUTTON_CSS, TOKENS, apply_chart_theme, token


ROOT = Path(__file__).resolve().parents[1]


def test_native_theme_matches_shared_tokens() -> None:
    theme = tomllib.loads((ROOT / '.streamlit/config.toml').read_text(encoding='utf-8'))['theme']
    for config_key, name in [('primaryColor', 'accent'), ('backgroundColor', 'canvas'), ('secondaryBackgroundColor', 'white'), ('textColor', 'ink')]:
        assert theme[config_key].lower() == token(name)


def test_all_pages_use_shared_theme_without_local_palette() -> None:
    for page in [ROOT / 'app.py', *sorted((ROOT / 'pages').glob('*.py'))]:
        content = page.read_text(encoding='utf-8')
        assert 'apply_saas_theme(' in content, page
        assert not re.search(r'#[0-9a-fA-F]{6}\b', content), page
        assert '<style>' not in content.replace('<style>{COPY_BUTTON_CSS}</style>', ''), page


def test_chart_theme_preserves_data_and_axis_semantics() -> None:
    figure = go.Figure(go.Bar(x=[0, 2], y=['A', 'B'], orientation='h'))
    figure.update_layout(title='数量', xaxis_range=[0, 100], height=380)
    apply_chart_theme(figure)
    assert list(figure.data[0].x) == [0, 2]
    assert figure.data[0].orientation == 'h'
    assert figure.layout.xaxis.range == (0, 100)
    assert figure.layout.title.text == '数量'
    assert figure.layout.height == 380
    assert figure.layout.font.color == token('ink')


def test_iframe_has_complete_tokens_and_keyboard_focus() -> None:
    assert set(re.findall(r'var\(--hr-([\w-]+)\)', COPY_BUTTON_CSS)) <= TOKENS.keys()
    assert ':focus-visible' in COPY_BUTTON_CSS
    assert '--hr-accent: ' + token('accent') in COPY_BUTTON_CSS
