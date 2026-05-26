const BASE_PATH =
  window.BASE_PATH || document.querySelector('meta[name="base-path"]')?.content || "";
const STORAGE_KEY = "bilibilitopic_llm_config";

function apiUrl(path) {
  return `${BASE_PATH}${path}`;
}

function formatErrorDetail(detail, status) {
  if (typeof detail === "string" && detail.trim()) {
    return detail;
  }
  if (Array.isArray(detail)) {
    return detail.map((item) => item.msg || JSON.stringify(item)).join("；");
  }
  if (detail && typeof detail === "object") {
    return JSON.stringify(detail);
  }
  return `请求失败（HTTP ${status}）`;
}

const form = document.getElementById("analyze-form");
const statusBox = document.getElementById("status");
const statusText = document.getElementById("status-text");
const submitBtn = document.getElementById("submit-btn");
const resultsEmpty = document.getElementById("results-empty");
const resultsContent = document.getElementById("results-content");
const reportEl = document.getElementById("report");
const videoList = document.getElementById("video-list");
const resultTitle = document.getElementById("result-title");
const resultMeta = document.getElementById("result-meta");
const videoCount = document.getElementById("video-count");
const keywordInput = document.getElementById("keyword");
const llmApiKeyInput = document.getElementById("llm-api-key");
const llmBaseUrlInput = document.getElementById("llm-base-url");
const llmModelInput = document.getElementById("llm-model");

const DEFAULT_LLM = {
  api_key: "",
  base_url: "https://api.openai.com/v1",
  model: "gpt-4o-mini",
};

function loadLlmConfig() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) {
      return { ...DEFAULT_LLM };
    }
    const parsed = JSON.parse(raw);
    return {
      api_key: parsed.api_key || "",
      base_url: parsed.base_url || DEFAULT_LLM.base_url,
      model: parsed.model || DEFAULT_LLM.model,
    };
  } catch {
    return { ...DEFAULT_LLM };
  }
}

function saveLlmConfig() {
  const config = {
    api_key: llmApiKeyInput.value.trim(),
    base_url: llmBaseUrlInput.value.trim() || DEFAULT_LLM.base_url,
    model: llmModelInput.value.trim() || DEFAULT_LLM.model,
  };
  localStorage.setItem(STORAGE_KEY, JSON.stringify(config));
  return config;
}

function applyLlmConfig(config) {
  llmApiKeyInput.value = config.api_key || "";
  llmBaseUrlInput.value = config.base_url || DEFAULT_LLM.base_url;
  llmModelInput.value = config.model || DEFAULT_LLM.model;
}

function getLlmPayload() {
  const config = saveLlmConfig();
  if (!config.api_key) {
    throw new Error("请先填写 LLM API Key");
  }
  return config;
}

[llmApiKeyInput, llmBaseUrlInput, llmModelInput].forEach((input) => {
  input.addEventListener("input", saveLlmConfig);
  input.addEventListener("change", saveLlmConfig);
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();

  let llm;
  try {
    llm = getLlmPayload();
  } catch (error) {
    alert(error.message);
    document.getElementById("llm-panel").open = true;
    llmApiKeyInput.focus();
    return;
  }

  const payload = {
    keyword: keywordInput.value.trim(),
    days: Number(document.getElementById("days").value),
    limit: Number(document.getElementById("limit").value),
    min_play: Number(document.getElementById("min-play").value),
    llm,
  };

  if (!payload.keyword) {
    return;
  }

  setLoading(true, `正在搜索 B 站「${payload.keyword}」...`);
  resultsContent.classList.add("hidden");
  resultsEmpty.classList.remove("hidden");
  reportEl.innerHTML = "";
  videoList.innerHTML = "";

  try {
    setLoading(true, "正在调用 LLM 生成报告，请稍候...");
    const analyzeUrl = apiUrl("/api/analyze");
    const response = await fetch(analyzeUrl, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    let data = {};
    try {
      data = await response.json();
    } catch {
      data = {};
    }
    if (!response.ok) {
      throw new Error(
        `${formatErrorDetail(data.detail, response.status)}（${analyzeUrl}）`
      );
    }
    renderResults(data);
  } catch (error) {
    reportEl.innerHTML = `<p class="error">${escapeHtml(error.message)}</p>`;
    videoList.innerHTML = "";
    resultsEmpty.classList.add("hidden");
    resultsContent.classList.remove("hidden");
  } finally {
    setLoading(false);
  }
});

function formatMinPlay(minPlay) {
  if (!minPlay || minPlay <= 0) {
    return "播放不限";
  }
  return `播放≥${minPlay.toLocaleString()}`;
}

function renderResults(data) {
  resultTitle.textContent = `搜索「${data.keyword}」的分析报告`;
  resultMeta.textContent = `搜索关键词：${data.keyword} · 生成于 ${data.generated_at} · 近 ${data.days} 天 · ${data.video_count} 条样本 · 综合排序 · ${formatMinPlay(data.min_play)}`;
  videoCount.textContent = `${data.video_count} 条`;
  reportEl.innerHTML = marked.parse(data.report || "暂无报告");

  videoList.innerHTML = data.videos
    .map(
      (video, index) => `
        <article class="video-card">
          <h3>${index + 1}. ${escapeHtml(video.title)}</h3>
          <div class="video-meta">
            <span>UP主：${escapeHtml(video.author)}</span>
            <span>播放：${video.play.toLocaleString()}</span>
            <span>弹幕：${video.danmaku.toLocaleString()}</span>
            <span>发布：${escapeHtml(video.pubdate)}</span>
            ${video.tag ? `<span>标签：${escapeHtml(video.tag)}</span>` : ""}
          </div>
          ${video.url ? `<a href="${escapeAttr(video.url)}" target="_blank" rel="noopener">查看视频</a>` : ""}
        </article>
      `
    )
    .join("");

  resultsEmpty.classList.add("hidden");
  resultsContent.classList.remove("hidden");
}

function setLoading(loading, message) {
  submitBtn.disabled = loading;
  statusBox.classList.toggle("hidden", !loading);
  statusText.textContent = message || "正在分析...";
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function escapeAttr(value) {
  return escapeHtml(value).replaceAll("`", "&#96;");
}

applyLlmConfig(loadLlmConfig());
