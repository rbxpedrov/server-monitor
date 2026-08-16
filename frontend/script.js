/* Server Monitor — frontend
   Sem dependências externas: WebSocket nativo + <canvas> pros gráficos. */

const state = {
  token: localStorage.getItem("sm_token") || "",
  ws: null,
  wsRetryMs: 1000,
  pollTimer: null,
  currentPeriod: "5m",
  currentSort: "cpu",
};

const $ = (id) => document.getElementById(id);

// ---------- Login ----------
function showApp() {
  $("login-screen").classList.add("hidden");
  $("app").classList.remove("hidden");
}

function showLogin(errorMsg) {
  $("app").classList.add("hidden");
  $("login-screen").classList.remove("hidden");
  $("login-error").textContent = errorMsg || "";
}

$("login-btn").addEventListener("click", () => {
  const token = $("token-input").value.trim();
  if (!token) return;
  state.token = token;
  localStorage.setItem("sm_token", token);
  boot();
});

$("token-input").addEventListener("keydown", (e) => {
  if (e.key === "Enter") $("login-btn").click();
});

$("logout-btn").addEventListener("click", () => {
  localStorage.removeItem("sm_token");
  state.token = "";
  if (state.ws) state.ws.close();
  if (state.pollTimer) clearInterval(state.pollTimer);
  showLogin("");
});

// ---------- Fetch helper ----------
async function apiGet(path) {
  const res = await fetch(path, { headers: { Authorization: "Bearer " + state.token } });
  if (res.status === 401) throw new Error("unauthorized");
  if (!res.ok) throw new Error("http " + res.status);
  return res.json();
}

// ---------- Conexão em tempo real ----------
function connectWS() {
  const proto = location.protocol === "https:" ? "wss" : "ws";
  const url = `${proto}://${location.host}/ws?token=${encodeURIComponent(state.token)}`;
  const ws = new WebSocket(url);
  state.ws = ws;

  ws.onopen = () => {
    state.wsRetryMs = 1000;
    setConnBadge(true);
    if (state.pollTimer) { clearInterval(state.pollTimer); state.pollTimer = null; }
  };

  ws.onmessage = (evt) => {
    try {
      const snap = JSON.parse(evt.data);
      renderSnapshot(snap);
    } catch (e) { /* ignora frame inválido */ }
  };

  ws.onclose = (evt) => {
    setConnBadge(false);
    if (evt.code === 4401) { showLogin("Token inválido."); return; }
    startPollingFallback();
    setTimeout(connectWS, state.wsRetryMs);
    state.wsRetryMs = Math.min(state.wsRetryMs * 1.6, 15000);
  };

  ws.onerror = () => ws.close();
}

function startPollingFallback() {
  if (state.pollTimer) return;
  state.pollTimer = setInterval(async () => {
    try {
      const snap = await apiGet("/api/status");
      renderSnapshot(snap);
    } catch (e) {
      if (e.message === "unauthorized") showLogin("Sessão expirada.");
    }
  }, 5000);
}

function setConnBadge(online) {
  const el = $("conn-indicator");
  el.textContent = online ? "● AO VIVO" : "● RECONECTANDO...";
  el.className = "badge " + (online ? "badge-online" : "badge-offline");
}

// ---------- Renderização do snapshot ----------
function fmtBytes(bytes) {
  if (bytes == null) return "—";
  const units = ["B", "KB", "MB", "GB", "TB"];
  let i = 0, v = bytes;
  while (v >= 1024 && i < units.length - 1) { v /= 1024; i++; }
  return `${v.toFixed(1)} ${units[i]}`;
}

function val(field, suffix = "") {
  if (!field || field.available === false || field.value == null) return "Indisponível";
  return `${field.value}${suffix}`;
}

function renderSnapshot(s) {
  $("last-update").textContent = "Atualizado: " + new Date(s.timestamp * 1000).toLocaleTimeString("pt-BR");

  // CPU
  const cpuVal = s.cpu.usage_total_percent;
  $("cpu-value").textContent = val(cpuVal, "%");
  $("cpu-bar").style.width = (cpuVal.value ?? 0) + "%";

  // RAM
  const ramVal = s.ram.percent_used;
  $("ram-value").textContent = val(ramVal, "%");
  $("ram-bar").style.width = (ramVal.value ?? 0) + "%";

  // Temperatura
  $("temp-value").textContent = val(s.temperature.battery_celsius, "°C");
  $("temp-sub").textContent = s.temperature.cpu_celsius.available
    ? "CPU: " + s.temperature.cpu_celsius.value + "°C"
    : "sensor de CPU indisponível";

  // Bateria
  $("battery-value").textContent = val(s.battery.percentage, "%");
  $("battery-sub").textContent = s.battery.charging.value ? "Carregando" : "Não carregando";

  // Internet
  $("ping-value").textContent = val(s.network.ping_ms, " ms");
  const dl = s.network.download_rate_bps.value;
  const ul = s.network.upload_rate_bps.value;
  $("net-sub").textContent = (dl != null && ul != null)
    ? `↓ ${fmtBytes(dl)}/s  ↑ ${fmtBytes(ul)}/s`
    : "taxa indisponível";

  // Armazenamento
  const stVal = s.storage.percent_used;
  $("storage-value").textContent = val(stVal, "%");
  $("storage-bar").style.width = (stVal.value ?? 0) + "%";

  // Alertas
  renderAlerts(s.alerts);

  // Minecraft
  renderMinecraft(s.minecraft);

  // Git sync
  const gs = s.git_sync;
  $("git-sync-status").textContent = gs && gs.status ? `sync: ${gs.status}` : "sync: —";

  // Info do dispositivo
  renderDeviceInfo(s.android);
}

function renderAlerts(alertList) {
  const bar = $("alerts-bar");
  bar.innerHTML = "";
  (alertList || []).forEach((a) => {
    const div = document.createElement("div");
    div.className = "alert-item alert-" + a.level;
    div.textContent = `${a.icon} ${a.message}`;
    bar.appendChild(div);
  });
}

function renderMinecraft(mc) {
  const online = mc.online.value === true;
  const badge = $("mc-status-badge");
  badge.textContent = online ? "● ONLINE" : "● OFFLINE";
  badge.className = "badge " + (online ? "badge-online" : "badge-offline");

  $("mc-address").textContent = `${val(mc.address)}:${val(mc.port)}`;
  $("mc-version").textContent = val(mc.version);
  $("mc-players").textContent = mc.players_online.available
    ? `${mc.players_online.value} / ${val(mc.players_max)}`
    : "Indisponível";
  $("mc-ping").textContent = val(mc.ping_ms, " ms");
  $("mc-motd").textContent = val(mc.motd);
  $("mc-tps").textContent = val(mc.tps);

  if (mc.process.available) {
    const p = mc.process.value;
    const h = Math.floor(p.uptime_seconds / 3600);
    const m = Math.floor((p.uptime_seconds % 3600) / 60);
    $("mc-uptime").textContent = `${h}h ${m}min`;
    $("mc-proc").textContent = `${p.cpu_percent}% CPU / ${p.ram_percent}% RAM`;
  } else {
    $("mc-uptime").textContent = "Indisponível";
    $("mc-proc").textContent = "Indisponível";
  }
}

function renderDeviceInfo(android) {
  const grid = $("device-info");
  const fields = [
    ["Fabricante", android.manufacturer],
    ["Modelo", android.model],
    ["Android", android.android_version],
    ["SDK", android.sdk],
    ["Arquitetura", android.architecture],
    ["Kernel", android.kernel],
    ["Hostname", android.hostname],
  ];
  grid.innerHTML = fields.map(([label, f]) =>
    `<div><span class="muted small">${label}</span><div>${val(f)}</div></div>`
  ).join("");

  if (android.uptime && android.uptime.available) {
    const u = android.uptime.value;
    grid.innerHTML += `<div><span class="muted small">Uptime do sistema</span><div>${u.days}d ${u.hours}h ${u.minutes}min</div></div>`;
  }
}

// ---------- Processos ----------
async function loadProcesses() {
  try {
    const data = await apiGet(`/api/processes?sort=${state.currentSort}&limit=25`);
    const tbody = document.querySelector("#processes-table tbody");
    tbody.innerHTML = "";
    (data.value || []).forEach((p) => {
      const tr = document.createElement("tr");
      if (p.is_minecraft) tr.className = "mc-row";
      tr.innerHTML = `<td>${p.pid}</td><td>${p.name}</td><td>${p.cpu_percent}%</td><td>${p.ram_percent}%</td><td>${p.user ?? "—"}</td>`;
      tbody.appendChild(tr);
    });
  } catch (e) {
    if (e.message === "unauthorized") showLogin("Sessão expirada.");
  }
}

document.querySelectorAll(".sort-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".sort-btn").forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
    state.currentSort = btn.dataset.sort;
    loadProcesses();
  });
});

// ---------- Notificações (eventos) ----------
async function loadEvents() {
  try {
    const data = await apiGet("/api/events?limit=30");
    const list = $("notifications-list");
    list.innerHTML = "";
    (data.events || []).forEach((ev) => {
      const div = document.createElement("div");
      div.className = "notification-item";
      const time = new Date(ev.ts * 1000).toLocaleTimeString("pt-BR");
      div.innerHTML = `<span class="notification-time">${time}</span>${ev.message}`;
      list.appendChild(div);
    });
    if (!data.events || data.events.length === 0) {
      list.innerHTML = '<div class="notification-item muted">Nenhum evento registrado ainda.</div>';
    }
  } catch (e) { /* silencioso */ }
}

// ---------- Gráficos (canvas simples, sem libs) ----------
const chartConfigs = {
  "chart-cpu": { key: "cpu", color: "#3b82f6", max: 100 },
  "chart-ram": { key: "ram", color: "#22c55e", max: 100 },
  "chart-temp": { key: "temp", color: "#f59e0b", max: null },
  "chart-ping": { key: "ping", color: "#a855f7", max: null },
  "chart-net": { key: "net", color: "#38bdf8", max: null },
  "chart-players": { key: "players", color: "#ef4444", max: null },
};

function drawLineChart(canvasId, points, color, maxHint) {
  const canvas = $(canvasId);
  const dpr = window.devicePixelRatio || 1;
  const cssW = canvas.clientWidth || 260;
  const cssH = canvas.clientHeight || 110;
  canvas.width = cssW * dpr;
  canvas.height = cssH * dpr;
  const ctx = canvas.getContext("2d");
  ctx.scale(dpr, dpr);
  ctx.clearRect(0, 0, cssW, cssH);

  if (!points || points.length < 2) {
    ctx.fillStyle = "rgba(255,255,255,0.25)";
    ctx.font = "12px sans-serif";
    ctx.fillText("sem dados suficientes", 8, cssH / 2);
    return;
  }

  const values = points.map((p) => (p == null ? 0 : p));
  const maxVal = maxHint ?? Math.max(...values, 1);
  const minVal = Math.min(...values, 0);
  const range = Math.max(maxVal - minVal, 1);

  ctx.beginPath();
  points.forEach((p, i) => {
    const x = (i / (points.length - 1)) * (cssW - 4) + 2;
    const y = cssH - ((p - minVal) / range) * (cssH - 8) - 4;
    if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
  });
  ctx.strokeStyle = color;
  ctx.lineWidth = 1.8;
  ctx.stroke();

  // preenchimento sutil
  ctx.lineTo(cssW - 2, cssH);
  ctx.lineTo(2, cssH);
  ctx.closePath();
  ctx.fillStyle = color + "22";
  ctx.fill();
}

async function loadHistory() {
  try {
    const data = await apiGet(`/api/history?period=${state.currentPeriod}`);
    const series = data.series || [];
    Object.entries(chartConfigs).forEach(([canvasId, cfg]) => {
      let points;
      if (cfg.key === "net") {
        // usamos ping como proxy indisponível -> mostramos ping mesmo (placeholder até termos série de banda)
        points = series.map((s) => s.ping);
      } else {
        points = series.map((s) => s[cfg.key]);
      }
      drawLineChart(canvasId, points, cfg.color, cfg.max);
    });
  } catch (e) { /* silencioso */ }
}

document.querySelectorAll(".period-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".period-btn").forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
    state.currentPeriod = btn.dataset.period;
    loadHistory();
  });
});

// ---------- Boot ----------
function boot() {
  showApp();
  connectWS();
  loadProcesses();
  loadEvents();
  loadHistory();
  setInterval(loadProcesses, 10000);
  setInterval(loadEvents, 15000);
  setInterval(loadHistory, 20000);
}

if (state.token) {
  boot();
} else {
  showLogin("");
}
