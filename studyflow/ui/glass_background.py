import json
from pathlib import Path

import streamlit as st


GLASS_COLORS = {
    "pane": "#134B5F",
    "background": "#07121A",
    "edge": "#9ED8E5"
}
GLASS_SPEED = 0.15
GLASS_SCALE = 1.0
GLASS_NOISE = 0.035
GLASS_OPACITY = 0.38
MAX_PIXEL_RATIO = 2
MAX_PIXELS = 4_000_000
MAX_FPS = 30

ASSETS_DIR = Path(__file__).resolve().parents[2] / "assets"
STYLE_FILE = ASSETS_DIR / "styles" / "glass.css"
SCRIPT_FILE = ASSETS_DIR / "scripts" / "glass.js"
VERTEX_FILE = ASSETS_DIR / "scripts" / "glass.vert"
FRAGMENT_FILE = ASSETS_DIR / "scripts" / "glass.frag"


# ============================================================
# SHOW IT
# ============================================================

def show():
    settings = json.dumps({
        "colors": GLASS_COLORS,
        "speed": GLASS_SPEED,
        "scale": GLASS_SCALE,
        "noise": GLASS_NOISE,
        "opacity": GLASS_OPACITY,
        "maxPixelRatio": MAX_PIXEL_RATIO,
        "maxPixels": MAX_PIXELS,
        "maxFps": MAX_FPS,
        "vertex": VERTEX_FILE.read_text(encoding="utf-8"),
        "fragment": FRAGMENT_FILE.read_text(encoding="utf-8")
    })
    script = SCRIPT_FILE.read_text(encoding="utf-8").replace("__SETTINGS__", settings)

    style = STYLE_FILE.read_text(encoding="utf-8")

    st.html(
        f'<style>{style}</style><span class="studyflow-glass-marker"></span><script>{script}</script>',
        unsafe_allow_javascript=True
    )
