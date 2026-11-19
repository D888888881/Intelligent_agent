/**
 * WebGL 失败时：全屏星系海起伏（无顶部线条假波浪）
 */
(function () {
  const root = document.querySelector(".auth-bg");
  const canvas = document.getElementById("auth-bg-canvas");
  if (!root || !canvas) return;

  let started = false;

  function seaOffset2d(x, y, t) {
    const swell = Math.sin(x * 0.009 + t * 0.5) * 22 + Math.cos(y * 0.007 + t * 0.38) * 16;
    const shear = Math.sin(y * 0.011 + t * 0.44) * 14;
    return { dx: Math.sin(t * 0.3 + y * 0.01) * 10, dy: swell + shear * 0.4 };
  }

  window.__authBgFallback = function () {
    if (started || root.classList.contains("auth-bg-webgl")) return;
    started = true;
    root.classList.add("auth-bg-fallback");

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let w = 0;
    let h = 0;
    const galaxies = [];

    function resize() {
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      w = window.innerWidth;
      h = window.innerHeight;
      canvas.width = Math.floor(w * dpr);
      canvas.height = Math.floor(h * dpr);
      canvas.style.width = w + "px";
      canvas.style.height = h + "px";
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      if (!galaxies.length) {
        for (let i = 0; i < 90; i++) {
          galaxies.push({
            bx: Math.random() * w,
            by: Math.random() * h,
            r: 6 + Math.random() * 22,
            hue: Math.random() < 0.33 ? 38 : Math.random() < 0.66 ? 210 : 275,
            phase: Math.random() * 6.28,
          });
        }
      }
    }

    function draw() {
      ctx.fillStyle = "#000";
      ctx.fillRect(0, 0, w, h);
      const t = Date.now() * 0.001;
      for (const g of galaxies) {
        const o = seaOffset2d(g.bx, g.by, t + g.phase);
        const x = g.bx + o.dx;
        const y = g.by + o.dy;
        const grd = ctx.createRadialGradient(x, y, 0, x, y, g.r);
        grd.addColorStop(0, `hsla(${g.hue},75%,72%,0.38)`);
        grd.addColorStop(0.55, `hsla(${g.hue},65%,55%,0.1)`);
        grd.addColorStop(1, "transparent");
        ctx.fillStyle = grd;
        ctx.beginPath();
        ctx.arc(x, y, g.r, 0, Math.PI * 2);
        ctx.fill();
      }
      for (let i = 0; i < 500; i++) {
        const bx = ((Math.sin(i * 127.1) * 43758.5453) % 1 + 1) % 1 * w;
        const by = ((Math.sin(i * 311.7) * 53491.236) % 1 + 1) % 1 * h;
        const o = seaOffset2d(bx, by, t);
        ctx.fillStyle = `rgba(255,255,255,${0.06 + (i % 5) * 0.04})`;
        ctx.fillRect(bx + o.dx * 0.3, by + o.dy * 0.3, 1, 1);
      }
      requestAnimationFrame(draw);
    }

    resize();
    window.addEventListener("resize", resize);
    draw();
  };

  window.addEventListener(
    "error",
    (e) => {
      const f = e.filename || "";
      if (f.includes("auth-bg.js") || f.includes("/vendor/three/")) {
        window.__authBgFallback("script");
      }
    },
    true
  );

  setTimeout(() => {
    if (!root.classList.contains("auth-bg-webgl")) {
      window.__authBgFallback("timeout");
    }
  }, 12000);
})();