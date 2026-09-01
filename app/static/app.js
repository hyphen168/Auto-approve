// Office AI 自动化办公助手 - 前端逻辑
const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => Array.from(document.querySelectorAll(sel));

let chatHistory = [];
let providersList = [];

/* ---------------- 通用工具 ---------------- */
async function api(url, body, isDownload) {
  const opts = { method: "POST" };
  if (body instanceof FormData) opts.body = body;
  else {
    opts.headers = { "Content-Type": "application/json" };
    opts.body = JSON.stringify(body);
  }
  const resp = await fetch(url, opts);
  if (resp.status === 401) {
    showLogin();
    throw new Error("请先登录");
  }
  if (!resp.ok) {
    let msg = "请求失败 (" + resp.status + ")";
    try { const j = await resp.json(); if (j.error) msg = j.error; } catch (e) {}
    throw new Error(msg);
  }
  return isDownload ? resp.blob() : resp.json();
}

function saveBlob(blob, filename) {
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 5000);
}

function downloadTxt(textareaId, filename) {
  const text = $(textareaId) ? $(textareaId).value : "";
  if (!text.trim()) { alert("没有可下载的内容"); return; }
  saveBlob(new Blob([text], { type: "text/plain;charset=utf-8" }), filename);
}

function setOptions(sel, items) {
  sel.innerHTML = "";
  items.forEach((text, i) => {
    const opt = document.createElement("option");
    opt.value = String(i);
    opt.textContent = text;
    sel.appendChild(opt);
  });
}

function setSheetOptions(sheets) {
  const sel = $("#excelSheet");
  sel.innerHTML = "";
  sheets.forEach((name) => {
    const opt = document.createElement("option");
    opt.value = name;
    opt.textContent = name;
    sel.appendChild(opt);
  });
}

function setBusy(busy) { $("#busyOverlay").hidden = !busy; }

function pickFile(inputId) { $(inputId).click(); }

function onFilePick(inputId, labelId) {
  const f = $(inputId).files[0];
  $(labelId).textContent = f ? f.name : "未选择文件";
}

/* ---------------- 页签切换 ---------------- */
$$("#tabs .tab").forEach((btn) => {
  btn.addEventListener("click", () => {
    $$("#tabs .tab").forEach((b) => b.classList.remove("active"));
    $$(".panel").forEach((p) => p.classList.remove("active"));
    btn.classList.add("active");
    $("#tab-" + btn.dataset.tab).classList.add("active");
  });
});

/* ---------------- 设置 ---------------- */
async function loadSettings() {
  try {
    const resp = await fetch("/api/settings");
    const cfg = await resp.json();
    providersList = cfg.providers || [];
    setOptions($("#providerIndex"), providersList.map((p) => p.name));
    $("#providerIndex").value = String(cfg.provider ?? 0);
    $("#baseUrl").value = cfg.base_url || "";
    $("#model").value = cfg.model || "";
    $("#apiKey").value = (cfg.api_key && cfg.api_key !== "********") ? cfg.api_key : "";
    $("#temperature").value = cfg.temperature ?? 0.7;
    $("#systemPrompt").value = cfg.system_prompt || "";
    $("#modelInfo").textContent = cfg.model ? "模型：" + cfg.model : "AI 尚未配置";
    showHint();
  } catch (e) { console.error("加载设置失败", e); }
}

function showHint() {
  const p = providersList[Number($("#providerIndex").value || 0)];
  $("#providerHint").textContent = p ? p.hint : "";
}

function applyProvider() {
  const p = providersList[Number($("#providerIndex").value || 0)];
  if (!p) return;
  showHint();
  if (p.base_url) $("#baseUrl").value = p.base_url;
  if (p.model) $("#model").value = p.model;
  if (p.api_key) $("#apiKey").value = p.api_key;
}

async function saveSettings() {
  setBusy(true);
  try {
    const body = {
      provider: $("#providerIndex").value,
      base_url: $("#baseUrl").value.trim(),
      model: $("#model").value.trim(),
      temperature: parseFloat($("#temperature").value) || 0.7,
      system_prompt: $("#systemPrompt").value,
    };
    if ($("#apiKey").value.trim()) body.api_key = $("#apiKey").value.trim();
    await api("/api/settings", body);
    alert("设置已保存。");
    $("#testResult").textContent = "";
  } catch (e) { alert("保存失败：" + e.message); }
  setBusy(false);
}

async function testConn() {
  setBusy(true);
  const body = {
    base_url: $("#baseUrl").value.trim(),
    model: $("#model").value.trim(),
  };
  if ($("#apiKey").value.trim()) body.api_key = $("#apiKey").value.trim();
  try {
    const r = await api("/api/test", body);
    $("#testResult").textContent = r.ok ? "✅ 连接成功：" + r.reply : "❌ " + r.error;
  } catch (e) { $("#testResult").textContent = "❌ 连接失败：" + e.message; }
  setBusy(false);
}

/* ---------------- AI 助手 ---------------- */
function appendChat(name, content) {
  const d = document.createElement("div");
  d.className = "msg";
  const b = document.createElement("b");
  b.textContent = name + "：";
  d.appendChild(b);
  d.appendChild(document.createTextNode(content));
  $("#chatLog").appendChild(d);
  $("#chatLog").scrollTop = $("#chatLog").scrollHeight;
}

async function sendChat() {
  const text = $("#chatInput").value.trim();
  if (!text) return;
  $("#chatInput").value = "";
  appendChat("我", text);
  chatHistory.push({ role: "user", content: text });
  setBusy(true);
  try {
    const r = await api("/api/chat", { messages: chatHistory });
    const reply = r.reply || "（无返回内容）";
    chatHistory.push({ role: "assistant", content: reply });
    appendChat(r.provider || "助手", reply);
  } catch (e) {
    chatHistory.pop();
    appendChat("系统", "出错了：" + e.message);
  }
  setBusy(false);
}

function clearChat() {
  $("#chatLog").innerHTML = "";
  chatHistory = [];
}

function saveChat() {
  if (!chatHistory.length) { alert("当前没有对话内容"); return; }
  const lines = chatHistory.map((m) =>
    (m.role === "user" ? "我：" : "助手：") + m.content);
  saveBlob(new Blob([lines.join("\n\n")], { type: "text/plain;charset=utf-8" }), "chat_history.txt");
}

/* ---------------- 登录 ---------------- */
function showLogin() { $("#loginOverlay").hidden = false; }
function hideLogin() { $("#loginOverlay").hidden = true; }

async function checkAuth() {
  try {
    const resp = await fetch("/api/me");
    const data = await resp.json();
    if (data.auth_enabled && !data.authed) showLogin();
    else { hideLogin(); $("#logoutBtn").hidden = !data.authed; }
  } catch (e) { showLogin(); }
}

async function doLogin() {
  const pwd = $("#loginPassword").value;
  if (!pwd) { $("#loginMsg").textContent = "请输入密码"; return; }
  try {
    const resp = await fetch("/api/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ password: pwd }),
    });
    if (resp.ok) {
      hideLogin();
      $("#loginPassword").value = "";
      $("#loginMsg").textContent = "";
      $("#logoutBtn").hidden = false;
      loadSettings();
    } else {
      let msg = "登录失败";
      try { const j = await resp.json(); msg = j.error || msg; } catch (e) {}
      $("#loginMsg").textContent = "❌ " + msg;
    }
  } catch (e) { $("#loginMsg").textContent = "❌ 网络错误"; }
}

function doLogout() {
  fetch("/api/logout", { method: "POST" }).finally(() => {
    $("#logoutBtn").hidden = true;
    chatHistory = [];
    showLogin();
  });
}

async function changePassword() {
  const oldPwd = prompt("请输入当前访问密码：");
  if (oldPwd === null) return;
  const newPwd = $("#newPassword").value;
  if (!newPwd || newPwd.length < 6) { alert("新密码至少 6 位"); return; }
  setBusy(true);
  try {
    await api("/api/password", { old: oldPwd, new: newPwd });
    alert("密码已修改。");
    $("#newPassword").value = "";
  } catch (e) { alert("修改失败：" + e.message); }
  setBusy(false);
}

$("#loginPassword").addEventListener("keydown", (e) => {
  if (e.key === "Enter") doLogin();
});

/* ---------------- Word ---------------- */
async function genWord() {
  const topic = $("#wordTopic").value.trim();
  if (!topic) { alert("请输入文档主题"); return; }
  setBusy(true);
  try {
    const usePdf = $("#wordAsPdf").checked;
    const blob = await api("/api/word/generate",
      { topic, extra: $("#wordExtra").value, as_pdf: usePdf }, true);
    saveBlob(blob, usePdf ? topic + "_AI文档.zip" : topic + ".docx");
  } catch (e) { alert("生成失败：" + e.message); }
  setBusy(false);
}

async function wordSummarize() {
  const f = $("#wordFile").files[0];
  if (!f) { alert("请先选择 Word 文档"); return; }
  const fd = new FormData();
  fd.append("file", f);
  setBusy(true);
  try {
    const r = await api("/api/word/summarize", fd);
    $("#wordSummary").value = r.summary || "";
  } catch (e) { alert("摘要生成失败：" + e.message); }
  setBusy(false);
}

async function wordTranslate() {
  const f = $("#wordFile").files[0];
  if (!f) { alert("请先选择 Word 文档"); return; }
  const fd = new FormData();
  fd.append("file", f);
  fd.append("target", $("#wordTarget").value);
  setBusy(true);
  try {
    const blob = await api("/api/word/translate", fd, true);
    saveBlob(blob, "translated_" + f.name);
  } catch (e) { alert("翻译失败：" + e.message); }
  setBusy(false);
}

async function convertToPdf(inputId) {
  const f = $(inputId).files[0];
  if (!f) { alert("请先选择文件"); return; }
  const fd = new FormData();
  fd.append("file", f);
  setBusy(true);
  try {
    const blob = await api("/api/pdf/convert", fd, true);
    saveBlob(blob, f.name.replace(/\.(docx|pptx)$/i, "") + ".pdf");
  } catch (e) { alert("PDF 转换失败：" + e.message); }
  setBusy(false);
}

/* ---------------- Word 模板套用 ---------------- */
let tplFieldsArr = [];

async function tplFields() {
  const f = $("#tplFile").files[0];
  if (!f) { alert("请先选择模板文件"); return; }
  const fd = new FormData();
  fd.append("file", f);
  setBusy(true);
  try {
    const r = await api("/api/template/fields", fd);
    tplFieldsArr = r.fields || [];
    renderTplFields();
  } catch (e) { alert("识别失败：" + e.message); }
  setBusy(false);
}

function renderTplFields() {
  const box = $("#tplFieldsBox");
  box.innerHTML = "";
  if (!tplFieldsArr.length) {
    box.innerHTML = '<p class="hint">没有找到 {{占位符}}，请检查模板。</p>';
    return;
  }
  tplFieldsArr.forEach((f) => {
    const row = document.createElement("div");
    row.className = "tpl-row";
    const lab = document.createElement("label");
    lab.textContent = f + "：";
    const inp = document.createElement("input");
    inp.dataset.field = f;
    inp.placeholder = "填写 " + f;
    row.appendChild(lab);
    row.appendChild(inp);
    box.appendChild(row);
  });
}

async function tplAiSuggest() {
  const f = $("#tplFile").files[0];
  if (!f) { alert("请先选择模板文件"); return; }
  const fd = new FormData();
  fd.append("file", f);
  fd.append("context", $("#tplContext").value);
  setBusy(true);
  try {
    const r = await api("/api/template/ai-suggest", fd);
    const vals = r.values || {};
    document.querySelectorAll("#tplFieldsBox input").forEach((inp) => {
      if (vals[inp.dataset.field] !== undefined) inp.value = vals[inp.dataset.field];
    });
  } catch (e) { alert("AI 填值失败：" + e.message); }
  setBusy(false);
}

async function tplFill() {
  const f = $("#tplFile").files[0];
  if (!f) { alert("请先选择模板文件"); return; }
  const values = {};
  document.querySelectorAll("#tplFieldsBox input").forEach((inp) => {
    values[inp.dataset.field] = inp.value;
  });
  const fd = new FormData();
  fd.append("file", f);
  fd.append("values", JSON.stringify(values));
  setBusy(true);
  try {
    const blob = await api("/api/template/fill", fd, true);
    saveBlob(blob, "filled_" + f.name);
  } catch (e) { alert("填写失败：" + e.message); }
  setBusy(false);
}

/* ---------------- Excel ---------------- */
async function onExcelPick(event) {
  const f = event.target.files[0];
  $("#excelFileName").textContent = f ? f.name : "未选择文件";
  setSheetOptions([]);
  if (!f) return;
  const fd = new FormData();
  fd.append("file", f);
  setBusy(true);
  try {
    const r = await api("/api/excel/info", fd);
    setSheetOptions(r.sheets || []);
  } catch (e) { console.error(e); }
  setBusy(false);
}

async function excelAnalyze() {
  const f = $("#excelFile").files[0];
  if (!f) { alert("请先选择 Excel 文件"); return; }
  const fd = new FormData();
  fd.append("file", f);
  fd.append("extra", $("#excelExtra").value);
  setBusy(true);
  try {
    const r = await api("/api/excel/analyze", fd);
    $("#excelAnalysis").value = r.analysis || "";
    if (r.sheets && r.sheets.length) setSheetOptions(r.sheets);
  } catch (e) { alert("分析失败：" + e.message); }
  setBusy(false);
}

async function excelReport() {
  const f = $("#excelFile").files[0];
  const analysis = $("#excelAnalysis").value.trim();
  if (!f) { alert("请先选择 Excel 文件"); return; }
  if (!analysis) { alert("请先生成 AI 分析结果"); return; }
  const fd = new FormData();
  fd.append("file", f);
  fd.append("analysis", analysis);
  setBusy(true);
  try {
    const blob = await api("/api/excel/report", fd, true);
    saveBlob(blob, "with_ai_report.xlsx");
  } catch (e) { alert("失败：" + e.message); }
  setBusy(false);
}

async function excelGenRows() {
  const f = $("#excelFile").files[0];
  if (!f) { alert("请先选择 Excel 文件"); return; }
  const sheet = $("#excelSheet").value || "";
  if (!sheet) { alert("请先选择工作表（选择文件后会自动列出）"); return; }
  const n = parseInt($("#excelN").value, 10) || 10;
  const fd = new FormData();
  fd.append("file", f);
  fd.append("sheet", sheet);
  fd.append("n", n);
  fd.append("extra", $("#excelExtra2").value);
  setBusy(true);
  try {
    const blob = await api("/api/excel/generate-rows", fd, true);
    saveBlob(blob, "generated_data.xlsx");
  } catch (e) { alert("生成失败：" + e.message); }
  setBusy(false);
}

async function excelChart() {
  const f = $("#excelFile").files[0];
  if (!f) { alert("请先选择 Excel 文件"); return; }
  const sheet = $("#excelSheet").value || "";
  const fd = new FormData();
  fd.append("file", f);
  fd.append("sheet", sheet);
  fd.append("chart_type", $("#excelChartType").value);
  setBusy(true);
  try {
    const blob = await api("/api/excel/chart", fd, true);
    saveBlob(blob, "with_chart.xlsx");
  } catch (e) { alert("图表生成失败：" + e.message); }
  setBusy(false);
}

/* ---------------- PPT ---------------- */
async function genPpt() {
  const topic = $("#pptTopic").value.trim();
  if (!topic) { alert("请输入 PPT 主题"); return; }
  setBusy(true);
  try {
    const slides = parseInt($("#pptSlides").value, 10) || 6;
    const usePdf = $("#pptAsPdf").checked;
    const blob = await api("/api/ppt/generate",
      { topic, slides, extra: $("#pptExtra").value, as_pdf: usePdf }, true);
    saveBlob(blob, usePdf ? topic + "_AI演示.zip" : topic + ".pptx");
  } catch (e) { alert("生成失败：" + e.message); }
  setBusy(false);
}

async function pptSummarize() {
  const f = $("#pptFile").files[0];
  if (!f) { alert("请先选择 PPT 文件"); return; }
  const fd = new FormData();
  fd.append("file", f);
  setBusy(true);
  try {
    const r = await api("/api/ppt/summarize", fd);
    $("#pptSummary").value = r.summary || "";
  } catch (e) { alert("摘要失败：" + e.message); }
  setBusy(false);
}

/* ---------------- 批量处理 ---------------- */
function onBatchPick(event) {
  const fs = event.target.files;
  $("#batchFileName").textContent = fs.length ? (fs.length + " 个文件") : "未选择文件";
}

async function batchRun() {
  const files = $("#batchFile").files;
  if (!files.length) { alert("请先选择文件"); return; }
  const fd = new FormData();
  Array.from(files).forEach((f) => fd.append("files", f));
  fd.append("op", $("#batchOp").value);
  fd.append("target", $("#batchTarget").value);
  setBusy(true);
  try {
    const blob = await api("/api/batch", fd, true);
    saveBlob(blob, "batch_result.zip");
  } catch (e) { alert("批量处理失败：" + e.message); }
  setBusy(false);
}

/* ---------------- 初始化 ---------------- */
checkAuth();
loadSettings();