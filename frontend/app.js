const API_BASE_URL = window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1"
    ? "http://localhost:8000/api/v1"
    : `${window.location.origin}/api/v1`;

const sectionTitles = {
    upload: ["Upload Brief", "Extract project context and retrieve relevant resources."],
    daily: ["Daily Intelligence", "Schedule and preview the daily learning brief."]
};

let currentBriefId = null;

document.addEventListener("DOMContentLoaded", () => {
    bindNavigation();
    bindTheme();
    bindBriefUpload();
    bindDailyIntelligence();
    loadHealth();
    loadTeamEmailSettings();
    loadEmailHistory();
});

function bindNavigation() {
    document.querySelectorAll(".nav-link").forEach((button) => {
        button.addEventListener("click", () => {
            document.querySelectorAll(".nav-link").forEach((item) => item.classList.remove("active"));
            button.classList.add("active");
            document.querySelectorAll(".section").forEach((section) => section.classList.remove("active"));
            const sectionId = button.dataset.section;
            document.getElementById(sectionId).classList.add("active");
            const [title, subtitle] = sectionTitles[sectionId] || sectionTitles.upload;
            setText("pageTitle", title);
            setText("pageSubtitle", subtitle);
            if (sectionId === "daily") {
                loadTeamEmailSettings();
                loadEmailHistory();
            }
        });
    });
}

function bindTheme() {
    const savedTheme = localStorage.getItem("li-theme") || "light";
    document.documentElement.dataset.theme = savedTheme;
    updateThemeIcon(savedTheme);
    document.getElementById("themeToggle").addEventListener("click", () => {
        const nextTheme = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
        document.documentElement.dataset.theme = nextTheme;
        localStorage.setItem("li-theme", nextTheme);
        updateThemeIcon(nextTheme);
    });
}

function updateThemeIcon(theme) {
    document.querySelector("#themeToggle i").className = theme === "dark" ? "fa-solid fa-sun" : "fa-solid fa-moon";
}

function bindBriefUpload() {
    const form = document.getElementById("briefForm");
    const input = document.getElementById("briefFile");
    const dropZone = document.getElementById("dropZone");

    dropZone.addEventListener("dragover", (event) => {
        event.preventDefault();
        dropZone.classList.add("dragging");
    });
    dropZone.addEventListener("dragleave", () => dropZone.classList.remove("dragging"));
    dropZone.addEventListener("drop", (event) => {
        event.preventDefault();
        dropZone.classList.remove("dragging");
        input.files = event.dataTransfer.files;
        updateDropZoneLabel();
    });
    input.addEventListener("change", updateDropZoneLabel);
    form.addEventListener("submit", uploadBrief);
    document.getElementById("analyzeBriefBtn").addEventListener("click", analyzeBrief);
}

function bindDailyIntelligence() {
    document.getElementById("emailSettingsForm").addEventListener("submit", saveTeamEmailSettings);
    document.getElementById("previewDailyBtn").addEventListener("click", () => loadDailyPreview(true));
    document.getElementById("sendNowBtn").addEventListener("click", sendNow);
}

async function apiFetch(path, options = {}) {
    const response = await fetch(`${API_BASE_URL}${path}`, options);
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
        throw new Error(payload.detail || payload.error || `Request failed: ${response.status}`);
    }
    return payload;
}

async function loadHealth() {
    const pill = document.getElementById("healthPill");
    try {
        const data = await apiFetch("/health");
        pill.className = "status-pill good";
        pill.innerHTML = `<i class="fa-solid fa-circle"></i> ${escapeHtml(data.status || "ok")}`;
    } catch {
        pill.className = "status-pill bad";
        pill.innerHTML = `<i class="fa-solid fa-circle"></i> Offline`;
    }
}

function updateDropZoneLabel() {
    const file = document.getElementById("briefFile").files[0];
    setText("dropTitle", file ? file.name : "Drop brief here");
    setText("dropMeta", file ? `${Math.round(file.size / 1024)} KB` : "or choose a file");
}

async function uploadBrief(event) {
    event.preventDefault();
    const file = document.getElementById("briefFile").files[0];
    if (!file) {
        showToast("Choose a brief file first.", "bad");
        return;
    }
    const formData = new FormData();
    formData.append("file", file);

    showLoading("Parsing brief");
    setButtonBusy("uploadBriefBtn", true);
    clearWarnings("briefWarnings");
    try {
        const data = await apiFetch("/briefs/upload", { method: "POST", body: formData });
        currentBriefId = data.brief_id;
        document.getElementById("analyzeBriefBtn").disabled = false;
        setCallout("briefStatus", "good", `Parsed ${data.file_name}.`);
        renderBriefFields(data.project_profile || {});
        renderResources([]);
        showToast("Brief parsed.", "good");
    } catch (error) {
        setCallout("briefStatus", "bad", error.message);
        showToast(error.message, "bad");
    } finally {
        setButtonBusy("uploadBriefBtn", false);
        hideLoading();
    }
}

async function analyzeBrief() {
    if (!currentBriefId) {
        showToast("Upload a brief first.", "bad");
        return;
    }
    showLoading("Fetching and ranking resources");
    setButtonBusy("analyzeBriefBtn", true);
    clearWarnings("briefWarnings");
    try {
        const data = await apiFetch(`/briefs/${currentBriefId}/analyze?refresh_sources=true`, { method: "POST" });
        setCallout("briefStatus", "good", data.executive_summary || "Analysis complete.");
        renderBriefFields(data.project_profile || {});
        renderWarnings("briefWarnings", data.warnings || [], data.source_status || []);
        renderResources(data.resource_results || data.results || data.top_evidence_sources || []);
        showToast("Resources ready.", "good");
    } catch (error) {
        setCallout("briefStatus", "bad", error.message);
        showToast(error.message, "bad");
    } finally {
        setButtonBusy("analyzeBriefBtn", false);
        hideLoading();
    }
}

function renderBriefFields(profile) {
    const fields = [
        ["Problem Statement", profile.problem_statement || first(profile.goals) || "-"],
        ["Requirements", profile.requirements || profile.technical_requirements || []],
        ["Technical Keywords", profile.technical_keywords || profile.key_topics || []],
        ["Domain / Industry", profile.industry || profile.domain || "general"],
        ["Expected Deliverables", profile.expected_deliverables || []],
        ["Constraints", profile.constraints || []]
    ];
    const container = document.getElementById("briefFields");
    container.classList.remove("empty-state");
    container.innerHTML = fields.map(([label, value]) => `
        <article class="field-card">
            <strong>${escapeHtml(label)}</strong>
            <span>${escapeHtml(formatFieldValue(value))}</span>
        </article>
    `).join("");
}

function renderResources(items) {
    const validItems = (items || []).filter((item) => isHttpUrl(item.url));
    setText("resourceCount", validItems.length);
    const container = document.getElementById("resourceResults");
    if (!validItems.length) {
        container.className = "result-list empty-state";
        container.innerHTML = "No valid resource links found yet.";
        return;
    }
    container.className = "result-list";
    container.innerHTML = validItems.map(renderResultCard).join("");
}

function renderResultCard(item) {
    const thumb = isHttpUrl(item.thumbnail_url)
        ? `<img class="thumb" src="${escapeAttribute(item.thumbnail_url)}" alt="">`
        : `<div class="thumb placeholder"><i class="fa-solid fa-link"></i></div>`;
    return `
        <article class="result-card">
            ${thumb}
            <div class="result-body">
                <div class="item-meta">
                    <span>${escapeHtml(item.category || formatSource(item.source_type))}</span>
                    <span>${escapeHtml(formatSource(item.source_type))}</span>
                    ${item.relevance_score != null ? `<span>${Math.round(Number(item.relevance_score) * 100)} relevance</span>` : ""}
                </div>
                <h3 class="item-title"><a href="${escapeAttribute(item.url)}" target="_blank" rel="noopener">${escapeHtml(item.title || "Untitled")}</a></h3>
                <p class="item-copy">${escapeHtml(item.summary || item.brief || "No summary available.")}</p>
                <p class="item-copy why">${escapeHtml(item.why_relevant || item.why_it_matters || "")}</p>
            </div>
        </article>
    `;
}

async function loadTeamEmailSettings() {
    try {
        const data = await apiFetch("/settings/team-email");
        document.getElementById("teamEmail").value = data.team_email || "";
        document.getElementById("sendTime").value = data.send_time || "08:00";
        document.getElementById("emailTimezone").value = data.timezone || "UTC";
        document.getElementById("emailProvider").value = data.provider || "disabled";
        document.getElementById("emailEnabled").checked = Boolean(data.enabled);
        document.getElementById("emailTopics").value = (data.topics || []).join(", ");
        renderDailyConfig(data);
    } catch (error) {
        setCallout("dailyConfigStatus", "bad", error.message);
    }
}

async function saveTeamEmailSettings(event) {
    event.preventDefault();
    const payload = {
        team_email: document.getElementById("teamEmail").value.trim(),
        send_time: document.getElementById("sendTime").value || "08:00",
        timezone: document.getElementById("emailTimezone").value.trim() || "UTC",
        provider: document.getElementById("emailProvider").value,
        enabled: document.getElementById("emailEnabled").checked,
        topics: splitTopics(document.getElementById("emailTopics").value),
        updated_by: "dashboard"
    };
    setButtonBusy("saveSettingsBtn", true);
    try {
        const data = await apiFetch("/settings/team-email", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        renderDailyConfig(data);
        showToast("Email settings saved.", "good");
    } catch (error) {
        setCallout("dailyConfigStatus", "bad", error.message);
        showToast(error.message, "bad");
    } finally {
        setButtonBusy("saveSettingsBtn", false);
    }
}

function renderDailyConfig(data) {
    const enabled = data.enabled ? "enabled" : "disabled";
    const email = data.team_email || "no email";
    const provider = data.provider || "disabled";
    setCallout("dailyConfigStatus", data.enabled && data.team_email ? "good" : "neutral", `${enabled}: ${email}, ${data.send_time || "08:00"} ${data.timezone || "UTC"}, ${provider}`);
}

async function loadDailyPreview(refresh) {
    showLoading(refresh ? "Refreshing daily intelligence" : "Loading daily intelligence");
    setButtonBusy("previewDailyBtn", true);
    clearWarnings("dailyWarnings");
    try {
        const data = await apiFetch(`/intelligence/daily${refresh ? "?refresh=true" : ""}`);
        renderDailyPreview(data);
        renderWarnings("dailyWarnings", data.warnings || [], data.source_status || []);
    } catch (error) {
        renderDailyError(error.message);
        showToast(error.message, "bad");
    } finally {
        setButtonBusy("previewDailyBtn", false);
        hideLoading();
    }
}

function renderDailyPreview(report) {
    setText("dailyCount", (report.top_updates || []).length);
    const container = document.getElementById("dailyPreview");
    const updates = report.top_updates || [];
    if (!updates.length) {
        container.className = "result-list empty-state";
        container.innerHTML = escapeHtml(report.summary || "No updates found.");
        return;
    }
    container.className = "result-list";
    container.innerHTML = `
        <div class="callout neutral">${escapeHtml(report.summary || "")}</div>
        ${updates.map((update) => renderResultCard({
            ...update,
            summary: update.brief,
            why_relevant: update.why_it_matters,
            relevance_score: update.impact_score,
            category: update.category || first(update.category_tags)
        })).join("")}
    `;
}

function renderDailyError(message) {
    setText("dailyCount", 0);
    const container = document.getElementById("dailyPreview");
    container.className = "result-list empty-state";
    container.innerHTML = escapeHtml(message);
}

async function sendNow() {
    showLoading("Generating and sending daily brief");
    setButtonBusy("sendNowBtn", true);
    clearWarnings("dailyWarnings");
    try {
        const data = await apiFetch("/intelligence/send-now", { method: "POST" });
        const log = data.email_log || {};
        renderDailyPreview(data.report || {});
        renderWarnings("dailyWarnings", data.report?.warnings || [], data.report?.source_status || []);
        loadEmailHistory();
        if (log.status === "sent") {
            showToast("Daily brief sent.", "good");
        } else {
            showToast(`Send failed: ${log.error_message || "provider unavailable"}`, "bad");
        }
    } catch (error) {
        renderDailyError(error.message);
        showToast(error.message, "bad");
    } finally {
        setButtonBusy("sendNowBtn", false);
        hideLoading();
    }
}

async function loadEmailHistory() {
    try {
        const data = await apiFetch("/intelligence/email-history");
        renderEmailHistory(data.logs || []);
    } catch (error) {
        const container = document.getElementById("emailHistory");
        container.className = "history-list empty-state";
        container.innerHTML = escapeHtml(error.message);
    }
}

function renderEmailHistory(logs) {
    const container = document.getElementById("emailHistory");
    if (!logs.length) {
        container.className = "history-list empty-state";
        container.innerHTML = "No email history yet.";
        return;
    }
    container.className = "history-list";
    container.innerHTML = logs.map((log) => `
        <article class="history-item">
            <strong>${escapeHtml(log.subject || "Daily brief")}</strong>
            <div class="item-meta">
                <span>${escapeHtml(log.recipient_email || "")}</span>
                <span>${escapeHtml(log.provider || "")}</span>
                <span>${escapeHtml(log.status || "")}</span>
                <span>${formatDate(log.sent_at || log.created_at)}</span>
            </div>
            ${log.error_message ? `<p class="item-copy">${escapeHtml(log.error_message)}</p>` : ""}
        </article>
    `).join("");
}

function renderWarnings(containerId, warnings, sourceStatus) {
    const container = document.getElementById(containerId);
    const warningRows = [...new Set(warnings || [])];
    const statusRows = (sourceStatus || [])
        .filter((item) => item.status && item.status !== "ok")
        .map((item) => `${item.source_id}: ${item.status}${item.error ? ` - ${item.error}` : ""}`);
    const rows = [...warningRows, ...statusRows].filter(Boolean);
    if (!rows.length) {
        container.innerHTML = "";
        return;
    }
    container.innerHTML = rows.slice(0, 8).map((row) => `<div class="warning-row"><i class="fa-solid fa-triangle-exclamation"></i>${escapeHtml(row)}</div>`).join("");
}

function clearWarnings(containerId) {
    document.getElementById(containerId).innerHTML = "";
}

function splitTopics(value) {
    return value.split(",").map((item) => item.trim()).filter(Boolean);
}

function first(value) {
    return Array.isArray(value) && value.length ? value[0] : "";
}

function formatFieldValue(value) {
    if (Array.isArray(value)) {
        return value.length ? value.join("; ") : "-";
    }
    return value || "-";
}

function formatSource(value) {
    return String(value || "source").replace(/_/g, " ").replace(/\b\w/g, (char) => char.toUpperCase());
}

function isHttpUrl(value) {
    return typeof value === "string" && (value.startsWith("http://") || value.startsWith("https://"));
}

function setText(id, value) {
    const node = document.getElementById(id);
    if (node) node.textContent = String(value);
}

function setCallout(id, type, text) {
    const node = document.getElementById(id);
    node.className = `callout ${type}`;
    node.textContent = text;
}

function setButtonBusy(id, busy) {
    const button = document.getElementById(id);
    if (!button) return;
    button.disabled = busy || (id === "analyzeBriefBtn" && !currentBriefId);
}

function showLoading(text) {
    setText("loadingText", text || "Working");
    document.getElementById("loadingOverlay").classList.remove("hidden");
}

function hideLoading() {
    document.getElementById("loadingOverlay").classList.add("hidden");
}

function showToast(message, type = "neutral") {
    const container = document.getElementById("toastContainer");
    const toast = document.createElement("div");
    toast.className = `toast ${type}`;
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(() => toast.remove(), 5200);
}

function formatDate(value) {
    if (!value) return "-";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return String(value).slice(0, 10);
    return date.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
}

function escapeHtml(value) {
    return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}

function escapeAttribute(value) {
    return escapeHtml(value).replaceAll("`", "&#096;");
}
