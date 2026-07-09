const STORAGE_KEY = "livermore-kline-practice-v1";

const els = {
  form: document.getElementById("candleForm"),
  time: document.getElementById("timeInput"),
  open: document.getElementById("openInput"),
  high: document.getElementById("highInput"),
  low: document.getElementById("lowInput"),
  close: document.getElementById("closeInput"),
  volume: document.getElementById("volumeInput"),
  note: document.getElementById("noteInput"),
  message: document.getElementById("formMessage"),
  save: document.getElementById("saveBtn"),
  clearForm: document.getElementById("clearFormBtn"),
  sample: document.getElementById("sampleBtn"),
  export: document.getElementById("exportBtn"),
  import: document.getElementById("importInput"),
  bundled: document.getElementById("bundledSelect"),
  loadBundled: document.getElementById("loadBundledBtn"),
  canvas: document.getElementById("chartCanvas"),
  empty: document.getElementById("emptyState"),
  title: document.getElementById("chartTitle"),
  prev: document.getElementById("prevBtn"),
  play: document.getElementById("playBtn"),
  next: document.getElementById("nextBtn"),
  fit: document.getElementById("fitBtn"),
  range: document.getElementById("timelineRange"),
  jump: document.getElementById("jumpSelect"),
  jumpBtn: document.getElementById("jumpBtn"),
  history: document.getElementById("historyList"),
  countStat: document.getElementById("countStat"),
  changeStat: document.getElementById("changeStat"),
  volumeStat: document.getElementById("volumeStat"),
  cursorStat: document.getElementById("cursorStat"),
};

const ctx = els.canvas.getContext("2d");
const bundledDatasets = Array.isArray(window.BUNDLED_DATASETS) ? window.BUNDLED_DATASETS : [];
const state = {
  candles: [],
  cursor: -1,
  selectedId: null,
  playing: false,
  timer: null,
};

function nowLocalInput() {
  const now = new Date();
  now.setMinutes(now.getMinutes() - now.getTimezoneOffset());
  return now.toISOString().slice(0, 16);
}

function uid() {
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
}

function fmtNumber(value, digits = 2) {
  if (!Number.isFinite(value)) return "-";
  return new Intl.NumberFormat("en-US", {
    maximumFractionDigits: digits,
    minimumFractionDigits: value % 1 === 0 ? 0 : Math.min(2, digits),
  }).format(value);
}

function fmtVolume(value) {
  return new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 }).format(value || 0);
}

function fmtTime(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

function normalizeTime(value) {
  const raw = String(value || "").trim();
  if (!raw) return "";
  const cleaned = raw.replace(/\//g, "-").replace(" ", "T");
  if (/^\d{4}-\d{2}-\d{2}$/.test(cleaned)) return `${cleaned}T00:00`;
  if (/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}/.test(cleaned)) return cleaned.slice(0, 16);

  const date = new Date(raw);
  if (Number.isNaN(date.getTime())) return raw;
  date.setMinutes(date.getMinutes() - date.getTimezoneOffset());
  return date.toISOString().slice(0, 16);
}

function normalizeCandle(raw) {
  return {
    id: raw.id || uid(),
    time: normalizeTime(raw.time || raw.date || raw.timestamp || raw.datetime),
    open: Number(raw.open),
    high: Number(raw.high),
    low: Number(raw.low),
    close: Number(raw.close),
    volume: Number(raw.volume),
    note: String(raw.note || ""),
  };
}

function sortedCandles(candles) {
  return [...candles].sort((a, b) => new Date(a.time) - new Date(b.time));
}

function validate(candle) {
  const fields = ["open", "high", "low", "close", "volume"];
  if (!candle.time) return "先写时间。";
  if (Number.isNaN(new Date(candle.time).getTime())) return "时间格式不对。";
  for (const field of fields) {
    if (!Number.isFinite(candle[field])) return "价格和成交量都要是数字。";
  }
  if (candle.high < Math.max(candle.open, candle.close)) return "最高价不能低于开盘或收盘。";
  if (candle.low > Math.min(candle.open, candle.close)) return "最低价不能高于开盘或收盘。";
  if (candle.low > candle.high) return "最低价不能高于最高价。";
  if (candle.volume < 0) return "成交量不能为负。";
  return "";
}

function canonicalKey(key) {
  const normalized = String(key || "").trim().toLowerCase().replace(/[^a-z0-9]/g, "");
  const aliases = {
    t: "time",
    time: "time",
    date: "time",
    datetime: "time",
    timestamp: "time",
    tradingtime: "time",
    o: "open",
    open: "open",
    h: "high",
    high: "high",
    l: "low",
    low: "low",
    c: "close",
    close: "close",
    v: "volume",
    vol: "volume",
    volume: "volume",
    amount: "volume",
    note: "note",
    notes: "note",
    comment: "note",
    memo: "note",
  };
  return aliases[normalized] || normalized;
}

function normalizeImportRow(row) {
  const mapped = {};
  Object.entries(row || {}).forEach(([key, value]) => {
    mapped[canonicalKey(key)] = value;
  });
  return normalizeCandle(mapped);
}

function parseCsvLine(line) {
  const cells = [];
  let current = "";
  let quoted = false;

  for (let i = 0; i < line.length; i += 1) {
    const char = line[i];
    const next = line[i + 1];
    if (char === "\"" && quoted && next === "\"") {
      current += "\"";
      i += 1;
    } else if (char === "\"") {
      quoted = !quoted;
    } else if (char === "," && !quoted) {
      cells.push(current.trim());
      current = "";
    } else {
      current += char;
    }
  }
  cells.push(current.trim());
  return cells;
}

function parseCsv(text) {
  const lines = text.split(/\r?\n/).map((line) => line.trim()).filter(Boolean);
  if (lines.length < 2) throw new Error("CSV 至少需要表头和一行数据。");

  const headers = parseCsvLine(lines[0]).map(canonicalKey);
  return lines.slice(1).map((line) => {
    const values = parseCsvLine(line);
    return headers.reduce((row, header, index) => {
      row[header] = values[index] || "";
      return row;
    }, {});
  });
}

function parseImportFile(file, text) {
  const trimmed = text.trim();
  if (!trimmed) throw new Error("文件是空的。");

  if (file.name.toLowerCase().endsWith(".json") || trimmed.startsWith("{") || trimmed.startsWith("[")) {
    const parsed = JSON.parse(trimmed);
    const rows = Array.isArray(parsed) ? parsed : (parsed.candles || parsed.data || parsed.records);
    if (!Array.isArray(rows)) throw new Error("JSON 需要是数组，或包含 candles/data/records 数组。");
    return rows.map(normalizeImportRow);
  }

  return parseCsv(trimmed).map(normalizeImportRow);
}

function validateImportedCandles(candles) {
  if (!candles.length) throw new Error("没有可导入的数据。");
  candles.forEach((candle, index) => {
    const error = validate(candle);
    if (error) throw new Error(`第 ${index + 1} 行：${error}`);
  });

  const seen = new Set();
  candles.forEach((candle, index) => {
    if (seen.has(candle.time)) throw new Error(`第 ${index + 1} 行：时间重复。`);
    seen.add(candle.time);
  });
}

function save() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify({ candles: state.candles }));
}

function load() {
  try {
    const parsed = JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}");
    state.candles = sortedCandles((parsed.candles || []).map(normalizeCandle));
    state.cursor = state.candles.length - 1;
  } catch {
    state.candles = [];
    state.cursor = -1;
  }
}

function initBundledDatasets() {
  els.bundled.innerHTML = "";
  if (!bundledDatasets.length) {
    const option = document.createElement("option");
    option.value = "";
    option.textContent = "无内置数据";
    els.bundled.appendChild(option);
    els.bundled.disabled = true;
    els.loadBundled.disabled = true;
    return;
  }

  bundledDatasets.forEach((dataset, index) => {
    const option = document.createElement("option");
    option.value = String(index);
    option.textContent = `${dataset.symbol} · ${dataset.market} · ${dataset.rows.length} 根`;
    els.bundled.appendChild(option);
  });
}

function readForm() {
  return normalizeCandle({
    id: state.selectedId || uid(),
    time: els.time.value,
    open: els.open.value,
    high: els.high.value,
    low: els.low.value,
    close: els.close.value,
    volume: els.volume.value,
    note: els.note.value,
  });
}

function fillForm(candle) {
  if (!candle) {
    state.selectedId = null;
    els.form.reset();
    els.time.value = nowLocalInput();
    els.message.textContent = "";
    els.save.textContent = "落笔绘制";
    return;
  }
  state.selectedId = candle.id;
  els.time.value = candle.time;
  els.open.value = candle.open;
  els.high.value = candle.high;
  els.low.value = candle.low;
  els.close.value = candle.close;
  els.volume.value = candle.volume;
  els.note.value = candle.note;
  els.save.textContent = "更新这一根";
}

function visibleCandles() {
  if (state.cursor < 0) return [];
  return state.candles.slice(0, state.cursor + 1);
}

function resizeCanvas() {
  const rect = els.canvas.getBoundingClientRect();
  const dpr = window.devicePixelRatio || 1;
  els.canvas.width = Math.max(1, Math.round(rect.width * dpr));
  els.canvas.height = Math.max(1, Math.round(rect.height * dpr));
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  draw();
}

function priceScale(candles, top, height) {
  const highs = candles.map((c) => c.high);
  const lows = candles.map((c) => c.low);
  const max = Math.max(...highs);
  const min = Math.min(...lows);
  const pad = Math.max((max - min) * 0.12, max * 0.006, 1);
  const hi = max + pad;
  const lo = Math.max(0, min - pad);
  return {
    hi,
    lo,
    y(price) {
      if (hi === lo) return top + height / 2;
      return top + ((hi - price) / (hi - lo)) * height;
    },
  };
}

function drawGrid(width, height, chartTop, chartHeight, volumeTop, volumeHeight, scale) {
  ctx.clearRect(0, 0, width, height);
  ctx.fillStyle = "#fffdf8";
  ctx.fillRect(0, 0, width, height);

  ctx.strokeStyle = "rgba(80, 72, 62, 0.14)";
  ctx.lineWidth = 1;
  ctx.beginPath();
  for (let i = 0; i <= 5; i += 1) {
    const y = chartTop + (chartHeight / 5) * i;
    ctx.moveTo(0, y);
    ctx.lineTo(width, y);
  }
  for (let i = 0; i <= 8; i += 1) {
    const x = (width / 8) * i;
    ctx.moveTo(x, chartTop);
    ctx.lineTo(x, volumeTop + volumeHeight);
  }
  ctx.stroke();

  ctx.fillStyle = "#6f6a63";
  ctx.font = "12px Inter, sans-serif";
  ctx.textAlign = "right";
  ctx.textBaseline = "middle";
  for (let i = 0; i <= 5; i += 1) {
    const price = scale.hi - ((scale.hi - scale.lo) / 5) * i;
    const y = chartTop + (chartHeight / 5) * i;
    ctx.fillText(fmtNumber(price), width - 10, y);
  }
}

function drawCandles(candles) {
  const rect = els.canvas.getBoundingClientRect();
  const width = rect.width;
  const height = rect.height;
  const chartTop = 22;
  const volumeHeight = Math.max(74, Math.min(120, height * 0.18));
  const volumeTop = height - volumeHeight - 26;
  const chartHeight = volumeTop - chartTop - 28;
  const scale = priceScale(candles, chartTop, chartHeight);
  drawGrid(width, height, chartTop, chartHeight, volumeTop, volumeHeight, scale);

  const leftPad = 32;
  const rightPad = 70;
  const plotWidth = width - leftPad - rightPad;
  const step = plotWidth / Math.max(candles.length, 1);
  const candleWidth = Math.max(6, Math.min(20, step * 0.54));
  const maxVolume = Math.max(...candles.map((c) => c.volume), 1);

  candles.forEach((candle, index) => {
    const x = leftPad + step * index + step / 2;
    const up = candle.close >= candle.open;
    const color = up ? "#177b57" : "#b13f36";
    const openY = scale.y(candle.open);
    const closeY = scale.y(candle.close);
    const highY = scale.y(candle.high);
    const lowY = scale.y(candle.low);
    const bodyTop = Math.min(openY, closeY);
    const bodyHeight = Math.max(2, Math.abs(openY - closeY));

    ctx.strokeStyle = color;
    ctx.fillStyle = color;
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(x, highY);
    ctx.lineTo(x, lowY);
    ctx.stroke();

    ctx.fillRect(x - candleWidth / 2, bodyTop, candleWidth, bodyHeight);

    const volHeight = (candle.volume / maxVolume) * volumeHeight;
    ctx.globalAlpha = 0.55;
    ctx.fillRect(x - candleWidth / 2, volumeTop + volumeHeight - volHeight, candleWidth, volHeight);
    ctx.globalAlpha = 1;

    if (index === state.cursor) {
      ctx.strokeStyle = "#2f5d73";
      ctx.lineWidth = 2;
      ctx.strokeRect(x - step / 2 + 2, chartTop + 2, step - 4, chartHeight + volumeHeight + 22);
    }
  });

  const last = candles[candles.length - 1];
  ctx.fillStyle = "#22211f";
  ctx.font = "12px Inter, sans-serif";
  ctx.textAlign = "left";
  ctx.textBaseline = "top";
  ctx.fillText(`${fmtTime(candles[0].time)}  →  ${fmtTime(last.time)}`, 16, height - 20);
}

function drawEmpty() {
  const rect = els.canvas.getBoundingClientRect();
  ctx.clearRect(0, 0, rect.width, rect.height);
  ctx.fillStyle = "#fffdf8";
  ctx.fillRect(0, 0, rect.width, rect.height);
}

function draw() {
  const candles = visibleCandles();
  els.empty.classList.toggle("hidden", candles.length > 0);
  if (!candles.length) {
    drawEmpty();
    return;
  }
  drawCandles(candles);
}

function renderTimeline() {
  const max = Math.max(state.candles.length - 1, 0);
  els.range.max = String(max);
  els.range.value = String(Math.max(state.cursor, 0));
  els.range.disabled = state.candles.length === 0;

  els.jump.innerHTML = "";
  state.candles.forEach((candle, index) => {
    const option = document.createElement("option");
    option.value = String(index);
    option.textContent = `${index + 1}. ${fmtTime(candle.time)}`;
    option.selected = index === state.cursor;
    els.jump.appendChild(option);
  });
  els.jump.disabled = state.candles.length === 0;
}

function renderHistory() {
  els.history.innerHTML = "";
  if (!state.candles.length) {
    const blank = document.createElement("div");
    blank.className = "history-item";
    blank.innerHTML = "<strong>暂无记录</strong><span>第一根行情会出现在这里。</span>";
    els.history.appendChild(blank);
    return;
  }

  state.candles.forEach((candle, index) => {
    const item = document.createElement("button");
    item.type = "button";
    item.className = `history-item${index === state.cursor ? " active" : ""}`;
    item.innerHTML = `
      <strong>${index + 1}. ${fmtTime(candle.time)}</strong>
      <span>O ${fmtNumber(candle.open)}  H ${fmtNumber(candle.high)}  L ${fmtNumber(candle.low)}  C ${fmtNumber(candle.close)}</span>
      <span>V ${fmtVolume(candle.volume)}${candle.note ? ` · ${escapeHtml(candle.note)}` : ""}</span>
    `;
    item.addEventListener("click", () => {
      state.cursor = index;
      fillForm(candle);
      render();
    });
    els.history.appendChild(item);
  });
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    "\"": "&quot;",
    "'": "&#39;",
  }[char]));
}

function renderStats() {
  const candles = visibleCandles();
  els.countStat.textContent = String(state.candles.length);
  if (!candles.length) {
    els.changeStat.textContent = "-";
    els.volumeStat.textContent = "-";
    els.cursorStat.textContent = "-";
    els.title.textContent = "空白练习本";
    return;
  }
  const first = candles[0];
  const last = candles[candles.length - 1];
  const change = last.close - first.open;
  const pct = first.open ? (change / first.open) * 100 : 0;
  const totalVolume = candles.reduce((sum, item) => sum + item.volume, 0);
  els.changeStat.textContent = `${change >= 0 ? "+" : ""}${fmtNumber(change)} (${pct >= 0 ? "+" : ""}${fmtNumber(pct)}%)`;
  els.changeStat.style.color = change >= 0 ? "var(--green)" : "var(--red)";
  els.volumeStat.textContent = fmtVolume(totalVolume);
  els.cursorStat.textContent = `${Math.max(state.cursor + 1, 0)}/${state.candles.length}`;
  els.title.textContent = `${fmtTime(last.time)} · C ${fmtNumber(last.close)}`;
}

function render() {
  state.candles = sortedCandles(state.candles);
  if (state.candles.length === 0) state.cursor = -1;
  if (state.cursor >= state.candles.length) state.cursor = state.candles.length - 1;
  renderTimeline();
  renderHistory();
  renderStats();
  draw();
}

function upsertCandle(candle) {
  const error = validate(candle);
  if (error) {
    els.message.textContent = error;
    return;
  }
  const sameTime = state.candles.find((item) => item.time === candle.time && item.id !== candle.id);
  if (sameTime) {
    els.message.textContent = "这个时间点已经有记录。";
    return;
  }

  const existingIndex = state.candles.findIndex((item) => item.id === candle.id);
  if (existingIndex >= 0) {
    state.candles[existingIndex] = candle;
  } else {
    state.candles.push(candle);
  }
  state.candles = sortedCandles(state.candles);
  state.cursor = state.candles.findIndex((item) => item.id === candle.id);
  save();
  fillForm(candle);
  els.message.textContent = "";
  render();
}

function step(delta) {
  if (!state.candles.length) return;
  state.cursor = Math.max(0, Math.min(state.candles.length - 1, state.cursor + delta));
  fillForm(state.candles[state.cursor]);
  render();
}

function stopPlayback() {
  state.playing = false;
  els.play.textContent = "播放";
  if (state.timer) window.clearInterval(state.timer);
  state.timer = null;
}

function startPlayback() {
  if (!state.candles.length) return;
  state.playing = true;
  els.play.textContent = "暂停";
  state.timer = window.setInterval(() => {
    if (state.cursor >= state.candles.length - 1) {
      stopPlayback();
      return;
    }
    step(1);
  }, 820);
}

function sampleCandles() {
  const base = new Date();
  base.setHours(9, 30, 0, 0);
  base.setMinutes(base.getMinutes() - base.getTimezoneOffset());
  const rows = [
    [100, 102, 99.2, 101.4, 8200, "第一根只记录，不解释。"],
    [101.4, 103.8, 100.8, 103.2, 11200, "量跟上，价格走出前高。"],
    [103.2, 104.1, 101.9, 102.4, 9300, "突破后回踩。"],
    [102.4, 105.9, 102.1, 105.5, 15800, "重新转强。"],
    [105.5, 107.7, 104.9, 107.1, 18100, "强势延续。"],
    [107.1, 107.4, 103.8, 104.2, 22400, "放量长上影。"],
    [104.2, 105.3, 102.7, 103.1, 14600, "观察支撑。"],
    [103.1, 106.2, 102.9, 105.8, 13100, "未破前低，重新收复。"],
    [105.8, 109.6, 105.4, 109.1, 24600, "关键点突破。"],
    [109.1, 111.2, 108.6, 110.8, 26800, "领导形态。"],
    [110.8, 111.0, 107.8, 108.2, 21900, "缩回突破区。"],
    [108.2, 112.6, 107.9, 112.0, 30100, "再次验证。"],
  ];
  return rows.map((row, index) => {
    const t = new Date(base.getTime() + index * 60 * 60 * 1000);
    return normalizeCandle({
      id: uid(),
      time: t.toISOString().slice(0, 16),
      open: row[0],
      high: row[1],
      low: row[2],
      close: row[3],
      volume: row[4],
      note: row[5],
    });
  });
}

els.form.addEventListener("submit", (event) => {
  event.preventDefault();
  upsertCandle(readForm());
});

els.clearForm.addEventListener("click", () => fillForm(null));
els.prev.addEventListener("click", () => step(-1));
els.next.addEventListener("click", () => step(1));
els.fit.addEventListener("click", () => {
  state.cursor = state.candles.length - 1;
  fillForm(state.candles[state.cursor] || null);
  render();
});
els.play.addEventListener("click", () => {
  if (state.playing) stopPlayback();
  else startPlayback();
});
els.range.addEventListener("input", () => {
  stopPlayback();
  state.cursor = Number(els.range.value);
  fillForm(state.candles[state.cursor]);
  render();
});
els.jumpBtn.addEventListener("click", () => {
  state.cursor = Number(els.jump.value);
  fillForm(state.candles[state.cursor]);
  render();
});
els.sample.addEventListener("click", () => {
  stopPlayback();
  state.candles = sampleCandles();
  state.cursor = state.candles.length - 1;
  save();
  fillForm(state.candles[state.cursor]);
  render();
});
els.export.addEventListener("click", () => {
  const blob = new Blob([JSON.stringify({ candles: state.candles }, null, 2)], { type: "application/json" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = "livermore-tape-ledger.json";
  link.click();
  URL.revokeObjectURL(link.href);
});
els.import.addEventListener("change", async (event) => {
  const file = event.target.files?.[0];
  if (!file) return;
  try {
    const candles = parseImportFile(file, await file.text());
    validateImportedCandles(candles);
    state.candles = sortedCandles(candles);
    state.cursor = state.candles.length - 1;
    save();
    fillForm(state.candles[state.cursor] || null);
    render();
    els.message.textContent = `已导入 ${state.candles.length} 根行情。`;
  } catch (error) {
    els.message.textContent = `导入失败：${error.message}`;
  } finally {
    event.target.value = "";
  }
});

els.loadBundled.addEventListener("click", () => {
  const dataset = bundledDatasets[Number(els.bundled.value)];
  if (!dataset) return;
  const candles = dataset.rows.map(normalizeImportRow);
  validateImportedCandles(candles);
  stopPlayback();
  state.candles = sortedCandles(candles);
  state.cursor = state.candles.length - 1;
  save();
  fillForm(state.candles[state.cursor] || null);
  render();
  els.message.textContent = `已载入 ${dataset.symbol}：${state.candles.length} 根行情。`;
});

window.addEventListener("resize", resizeCanvas);

load();
initBundledDatasets();
fillForm(state.candles[state.cursor] || null);
requestAnimationFrame(resizeCanvas);
