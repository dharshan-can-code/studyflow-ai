(() => {
  const markCards = () => {
    document.querySelectorAll('[data-testid="stVerticalBlock"]').forEach((block) => {
      const bordered = getComputedStyle(block).borderTopStyle === "solid";
      if (bordered !== block.classList.contains("studyflow-card")) block.classList.toggle("studyflow-card", bordered);
    });
  };

  // Streamlit's theme sets the page's text color, so its brightness tells light from dark.
  const currentTheme = () => {
    const [r, g, b] = (getComputedStyle(document.body).color.match(/\d+/g) || [255, 255, 255]).map(Number);
    return 0.299 * r + 0.587 * g + 0.114 * b > 128 ? "dark" : "light";
  };

  // Calendar iframes can't see the page's attribute, so copy it into each one.
  const themeFrames = (theme) => {
    document.querySelectorAll("iframe").forEach((frame) => {
      if (!frame.__studyflowThemed) {
        frame.__studyflowThemed = true;
        frame.addEventListener("load", () => themeFrames(document.documentElement.dataset.sfTheme));
      }
      try {
        const root = frame.contentDocument && frame.contentDocument.documentElement;
        if (root && root.dataset.sfTheme !== theme) root.dataset.sfTheme = theme;
      } catch (error) {
        // A frame from another site: nothing to theme.
      }
    });
  };

  const syncTheme = () => {
    const theme = currentTheme();
    if (document.documentElement.dataset.sfTheme !== theme) document.documentElement.dataset.sfTheme = theme;
    themeFrames(theme);
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
        syncTheme();
      });
    }).observe(document.body, { childList: true, subtree: true, attributes: true, attributeFilter: ["class"] });
    window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => requestAnimationFrame(syncTheme));
    document.addEventListener("click", (event) => {
      const tab = event.target.closest('[data-testid="stTab"]');
      if (!tab || tab.closest('[data-testid="stTabPanel"]') || !window.matchMedia("(max-width: 640px)").matches) return;
      const main = document.querySelector('[data-testid="stMain"]');
      if (main) main.scrollTo({ top: 0 });
      window.scrollTo({ top: 0 });
    }, true);
  }
  markCards();
  syncTheme();

  try {
    const host = window.parent !== window ? window.parent.document : null;
    if (host && !host.getElementById("studyflow-host-style")) {
      const hostStyle = host.createElement("style");
      hostStyle.id = "studyflow-host-style";
      hostStyle.textContent = 'a[class*="_viewerBadge_"], a[href^="https://streamlit.io/cloud"], [class*="_profileContainer_"], [class*="_profilePreview_"] { display: none !important; }';
      host.head.appendChild(hostStyle);
    }
  } catch (error) {
  }

  if (document.getElementById("studyflow-glass")) return;

  const settings = __SETTINGS__;
  const canvas = document.createElement("canvas");
  canvas.id = "studyflow-glass";
  canvas.setAttribute("aria-hidden", "true");
  Object.assign(canvas.style, {
    position: "fixed",
    inset: "0",
    width: "100vw",
    height: CSS.supports("height", "100lvh") ? "100lvh" : "100vh",
    zIndex: "-2",
    pointerEvents: "none"
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
    base: uniform("u_base"),
    opacity: uniform("u_opacity"),
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
  gl.uniform3fv(u.base, hexToVec3(settings.colors.page));
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
    gl.uniform1f(u.opacity, document.documentElement.dataset.sfTheme === "light" ? 1 : settings.opacity);
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
    new MutationObserver(() => draw(performance.now())).observe(document.documentElement, { attributes: true, attributeFilter: ["data-sf-theme"] });
  }
})();
