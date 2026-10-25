import json

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


# ============================================================
# PAGE STYLES
# ============================================================

GLASS_CSS = """
<style>
html {
    background-color: #050B10 !important;
}

body,
.stApp,
[data-testid="stAppViewContainer"],
[data-testid="stHeader"],
[data-testid="stHeader"] > div,
[data-testid="stMain"],
[data-testid="stBottom"],
[data-testid="stBottom"] > div,
[data-testid="stBottomBlockContainer"] {
    background: transparent !important;
}

[data-testid="stSidebar"] {
    background-color: rgba(8, 16, 24, 0.9) !important;
    backdrop-filter: blur(16px);
    border-right: 1px solid rgba(148, 163, 184, 0.1);
}

.studyflow-card {
    background-color: rgba(10, 20, 30, 0.84) !important;
    backdrop-filter: blur(12px);
    border: 1px solid rgba(148, 163, 184, 0.14) !important;
    border-radius: 14px !important;
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.25);
}

[data-testid="stExpander"] details {
    background-color: rgba(10, 20, 30, 0.8);
    backdrop-filter: blur(10px);
    border-color: rgba(148, 163, 184, 0.14) !important;
}

[data-testid="stAlert"] > div {
    backdrop-filter: blur(10px);
}

[data-testid="stMainBlockContainer"] h1,
[data-testid="stMainBlockContainer"] h2,
[data-testid="stMainBlockContainer"] h3,
.studyflow-title,
.greeting {
    text-shadow: 0 1px 12px rgba(0, 0, 0, 0.55);
}

[data-testid="stCaptionContainer"],
[data-testid="stCaptionContainer"] p,
.studyflow-subtitle,
.greeting-date {
    color: #AEB9C8 !important;
}

.stElementContainer:has(.studyflow-glass-marker) {
    display: none;
}
</style>
"""


# ============================================================
# WEBGL SHADER
# ============================================================

VERTEX_SHADER = """
attribute vec2 position;
varying vec2 vUv;
void main() {
  vUv = position * 0.5 + 0.5;
  gl_Position = vec4(position, 0.0, 1.0);
}
"""

FRAGMENT_SHADER = """
precision highp float;
uniform float u_time;
uniform vec3 u_color1;
uniform vec3 u_color2;
uniform vec3 u_color3;
uniform float u_scale;
uniform float u_noise;
uniform vec2 u_resolution;
varying vec2 vUv;

float grain(vec2 st) {
  return fract(sin(dot(st, vec2(12.9898, 78.233))) * 43758.5453);
}

vec2 centered(vec2 uv) {
  vec2 p = uv - 0.5;
  p.x *= u_resolution.x / max(u_resolution.y, 1.0);
  return p;
}

mat2 rot(float a) {
  float s = sin(a);
  float c = cos(a);
  return mat2(c, -s, s, c);
}

vec3 shade(vec2 uv, float time) {
  vec2 q = rot(0.6) * centered(uv) * 2.0 * u_scale;
  float t = time * 0.6;
  float pixel = 2.0 * u_scale / max(u_resolution.y, 1.0);
  vec3 color = mix(u_color2, u_color2 * 0.45, clamp(length(centered(uv)) * 1.3, 0.0, 1.0));

  for (int i = 0; i < 6; i++) {
    float fi = float(i);
    float bend = mod(fi, 2.0) * 2.0 - 1.0;
    float crease = (fi - 2.5) * 0.4
                 + 0.26 * sin(q.x * (1.05 + 0.12 * fi) + fi * 1.9 + t * (0.25 + 0.05 * fi))
                 + 0.1 * bend * q.x * q.x;
    float s = q.y - crease;
    float pane = smoothstep(-pixel, pixel, s);
    float back = max(s, 0.0);
    float body = exp(-back * 1.7);
    float fresnel = exp(-back * 8.0);
    float rim = exp(-back * 80.0);
    float inner = exp(-pow((back - 0.045) / 0.014, 2.0));
    float bloom = exp(-abs(s) * 20.0);
    vec3 tint = mix(u_color1, u_color3, clamp(fresnel * 0.6 + 0.08 + 0.14 * sin(fi * 2.1 + q.x * 0.8 + t * 0.2), 0.0, 1.0));
    vec3 light = tint * pane * (body * 0.42 + fresnel * 0.4)
               + u_color3 * (pane * (rim * 0.6 + inner * 0.12) + bloom * 0.1);
    color += light * (1.0 - color);
  }

  return clamp(color, 0.0, 1.0);
}

void main() {
  vec3 color = shade(vUv, u_time);
  if (u_noise > 0.001) {
    float g = grain(gl_FragCoord.xy + fract(u_time) * 17.0);
    color += (g - 0.5) * u_noise;
  }
  gl_FragColor = vec4(clamp(color, 0.0, 1.0), 1.0);
}
"""


# ============================================================
# BROWSER SCRIPT
# ============================================================

GLASS_SCRIPT = """
<span class="studyflow-glass-marker"></span>
<script>
(() => {
  const markCards = () => {
    document.querySelectorAll('[data-testid="stVerticalBlock"]').forEach((block) => {
      const bordered = getComputedStyle(block).borderTopStyle === "solid";
      if (bordered !== block.classList.contains("studyflow-card")) block.classList.toggle("studyflow-card", bordered);
    });
  };

  if (!window.__studyflowCards) {
    window.__studyflowCards = true;
    let queued = false;
    new MutationObserver(() => {
      if (queued) return;
      queued = true;
      requestAnimationFrame(() => {
        queued = false;
        markCards();
      });
    }).observe(document.body, { childList: true, subtree: true });
  }
  markCards();

  if (document.getElementById("studyflow-glass")) return;

  const settings = __SETTINGS__;
  const canvas = document.createElement("canvas");
  canvas.id = "studyflow-glass";
  canvas.setAttribute("aria-hidden", "true");
  Object.assign(canvas.style, {
    position: "fixed",
    inset: "0",
    width: "100vw",
    height: "100vh",
    zIndex: "-2",
    pointerEvents: "none",
    opacity: String(settings.opacity)
  });

  const scrim = document.createElement("div");
  scrim.id = "studyflow-glass-scrim";
  scrim.setAttribute("aria-hidden", "true");
  Object.assign(scrim.style, {
    position: "fixed",
    inset: "0",
    zIndex: "-1",
    pointerEvents: "none",
    background: "radial-gradient(ellipse 70% 80% at 55% 45%, rgba(5, 11, 16, 0.55), rgba(5, 11, 16, 0.15))"
  });

  const gl = canvas.getContext("webgl", { antialias: false, alpha: false, powerPreference: "low-power" });
  if (!gl) return;

  const compile = (type, source) => {
    const shader = gl.createShader(type);
    gl.shaderSource(shader, source);
    gl.compileShader(shader);
    return shader;
  };

  const program = gl.createProgram();
  gl.attachShader(program, compile(gl.VERTEX_SHADER, settings.vertex));
  gl.attachShader(program, compile(gl.FRAGMENT_SHADER, settings.fragment));
  gl.linkProgram(program);
  if (!gl.getProgramParameter(program, gl.LINK_STATUS)) return;
  gl.useProgram(program);

  document.body.prepend(scrim);
  document.body.prepend(canvas);

  const buffer = gl.createBuffer();
  gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
  gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 1, -1, -1, 1, -1, 1, 1, -1, 1, 1]), gl.STATIC_DRAW);
  const position = gl.getAttribLocation(program, "position");
  gl.enableVertexAttribArray(position);
  gl.vertexAttribPointer(position, 2, gl.FLOAT, false, 0, 0);

  const uniform = (name) => gl.getUniformLocation(program, name);
  const u = {
    time: uniform("u_time"),
    color1: uniform("u_color1"),
    color2: uniform("u_color2"),
    color3: uniform("u_color3"),
    scale: uniform("u_scale"),
    noise: uniform("u_noise"),
    resolution: uniform("u_resolution")
  };

  const hexToVec3 = (hex) => {
    const h = hex.replace("#", "");
    const full = h.length === 3 ? h.split("").map((c) => c + c).join("") : h;
    const n = parseInt(full, 16);
    return [((n >> 16) & 255) / 255, ((n >> 8) & 255) / 255, (n & 255) / 255];
  };

  gl.uniform3fv(u.color1, hexToVec3(settings.colors.pane));
  gl.uniform3fv(u.color2, hexToVec3(settings.colors.background));
  gl.uniform3fv(u.color3, hexToVec3(settings.colors.edge));
  gl.uniform1f(u.scale, settings.scale);
  gl.uniform1f(u.noise, settings.noise);

  const resize = () => {
    let factor = Math.min(window.devicePixelRatio || 1, settings.maxPixelRatio);
    const area = canvas.clientWidth * canvas.clientHeight * factor * factor;
    if (area > settings.maxPixels) factor *= Math.sqrt(settings.maxPixels / area);
    const width = Math.max(1, Math.round(canvas.clientWidth * factor));
    const height = Math.max(1, Math.round(canvas.clientHeight * factor));
    if (canvas.width !== width || canvas.height !== height) {
      canvas.width = width;
      canvas.height = height;
    }
    gl.viewport(0, 0, width, height);
  };

  let elapsed = 0;
  let last = null;
  let lastDraw = 0;
  const frameGap = 1000 / settings.maxFps;

  const draw = (now) => {
    if (last !== null) elapsed += Math.min((now - last) / 1000, 0.1) * settings.speed;
    last = now;
    resize();
    gl.uniform1f(u.time, elapsed);
    gl.uniform2f(u.resolution, canvas.width, canvas.height);
    gl.drawArrays(gl.TRIANGLES, 0, 6);
  };

  const still = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const loop = (now) => {
    if (now - lastDraw >= frameGap) {
      draw(now);
      lastDraw = now;
    }
    if (!still) requestAnimationFrame(loop);
  };
  requestAnimationFrame(loop);

  if (still) {
    new ResizeObserver(() => draw(performance.now())).observe(canvas);
  }
})();
</script>
"""


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
        "vertex": VERTEX_SHADER,
        "fragment": FRAGMENT_SHADER
    })
    st.html(GLASS_CSS + GLASS_SCRIPT.replace("__SETTINGS__", settings), unsafe_allow_javascript=True)
