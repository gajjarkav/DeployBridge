// File: frontend/js/deployments.js
// ------------------------------------------------------------------------------
// WHAT THIS IS
//   The Deployments page logic. Used to be 100% localStorage with fake
//   seed data ("docs-portal"). Now it's 100% API-driven, every row in
//   PostgreSQL, with smart auto-refresh that only polls while a visible
//   row is PENDING/BUILDING and pauses when the tab is hidden.
//
// API
//   GET    /v1/deployments                paginated list, newest first
//   GET    /v1/deployments/{id}           one detail
//   POST   /v1/deployments/{id}/refresh   pull upstream status into the row
//   POST   /v1/deployments/{id}/redeploy  trigger a new deploy on the platform
//   DELETE /v1/deployments/{id}           remove from history (NOT from platform)
//
// STATE MACHINE the cards render
//   pending  → building → live | failed
//   The auto-refresh polls /refresh every 8s for any row whose status is
//   pending/building. Pauses on `document.visibilitychange` to hidden.
//   No polling when every visible row is terminal (live/failed).
// ------------------------------------------------------------------------------

const BACKEND_API_URL = "http://127.0.0.1:8000/v1";

// Module state
let allDeployments = [];
let filteredDeployments = [];
let currentPage = 1;
const pageSize = 10;
let sessionToken = null;

// Auto-refresh bookkeeping (visibility-aware polling)
let autoRefreshTimer = null;
const AUTO_REFRESH_INTERVAL_MS = 8000;

// ============================================================================
// INIT
// ============================================================================

window.onload = async () => {
    const session = initializeAppShell("deployments");
    if (!session) return;
    sessionToken = session.dbSessionToken;

    hydrateUserInfo();
    bindEvents();
    await loadDeploymentsData();
    startAutoRefresh();
    // Pause/resume polling on tab visibility so we don't hammer the
    // platform APIs while the user isn't looking.
    document.addEventListener("visibilitychange", () => {
        if (document.hidden) {
            stopAutoRefresh();
        } else {
            startAutoRefresh();
        }
    });
};

function hydrateUserInfo() {
    const username = localStorage.getItem("gh_username") || "Developer";
    const avatar = localStorage.getItem("gh_avatar") || `https://github.com/identicons/${username}.png`;
    const avatarEl = document.getElementById("user-avatar");
    const nameEl = document.getElementById("user-display-name");
    if (avatarEl) avatarEl.src = avatar;
    if (nameEl) nameEl.textContent = username;
}

// ============================================================================
// DATA LOAD
// ============================================================================

async function loadDeploymentsData() {
    try {
        const res = await fetch(`${BACKEND_API_URL}/deployments?page=${currentPage}&page_size=${pageSize}`, {
            headers: { "Authorization": `Bearer ${sessionToken}` },
        });
        if (res.status === 401) {
            window.location.href = "./auth.html";
            return;
        }
        if (!res.ok) throw new Error(`Failed to load deployments: ${res.status}`);

        const data = await res.json();
        allDeployments = data.items || [];
        // The API already returns newest-first; keep filteredDeployments in sync
        filteredDeployments = [...allDeployments];
        updateSummaryStats();
        applyFilters();
    } catch (err) {
        console.error("loadDeploymentsData error:", err);
        allDeployments = [];
        filteredDeployments = [];
        applyFilters();
        showToast("Could not load deployments — is the backend running?");
    }
}

function updateSummaryStats() {
    const total = allDeployments.length; // page-local count; full total comes from API
    const live = allDeployments.filter((d) => d.status === "live").length;
    const failed = allDeployments.filter((d) => d.status === "failed").length;
    const building = allDeployments.filter((d) => d.status === "building" || d.status === "pending").length;
    const successRate = total > 0 ? Math.round(((live + failed === 0) ? 100 : (live / (live + failed)) * 100)) : 100;

    const elTotal = document.getElementById("stat-total-deploys");
    const elLive = document.getElementById("stat-live-sites");
    const elRate = document.getElementById("stat-success-rate");
    const elProfile = document.getElementById("stat-latest-profile");
    if (elTotal) elTotal.textContent = String(total);
    if (elLive) elLive.textContent = String(live);
    if (elRate) elRate.textContent = `${successRate}%`;
    if (elProfile) {
        const latest = allDeployments[0];
        elProfile.textContent = latest ? (latest.profile || latest.platform) : "-";
    }
}

// ============================================================================
// FILTERS + RENDER
// ============================================================================

function bindEvents() {
    const search = document.getElementById("deployments-search");
    const filterProfile = document.getElementById("filter-profile");
    const filterStatus = document.getElementById("filter-status");
    const btnSync = document.getElementById("btn-sync-status");
    const btnClear = document.getElementById("btn-clear-history");
    const btnPrev = document.getElementById("btn-prev-page");
    const btnNext = document.getElementById("btn-next-page");
    const btnCloseModal = document.getElementById("btn-close-modal");
    const modalBtnClose = document.getElementById("modal-btn-close");

    if (search) search.addEventListener("input", applyFilters);
    if (filterProfile) filterProfile.addEventListener("change", applyFilters);
    if (filterStatus) filterStatus.addEventListener("change", applyFilters);
    if (btnSync) btnSync.addEventListener("click", syncLiveStatuses);
    if (btnClear) btnClear.addEventListener("click", clearHistory);
    if (btnPrev) btnPrev.addEventListener("click", () => { if (currentPage > 1) { currentPage--; loadDeploymentsData(); } });
    if (btnNext) btnNext.addEventListener("click", () => { currentPage++; loadDeploymentsData(); });
    if (btnCloseModal) btnCloseModal.addEventListener("click", closeModal);
    if (modalBtnClose) modalBtnClose.addEventListener("click", closeModal);

    // Escape closes modal
    document.addEventListener("keydown", (e) => {
        if (e.key === "Escape") closeModal();
    });
}

function applyFilters() {
    const q = (document.getElementById("deployments-search")?.value || "").toLowerCase();
    const profile = document.getElementById("filter-profile")?.value || "all";
    const status = document.getElementById("filter-status")?.value || "all";

    filteredDeployments = allDeployments.filter((d) => {
        const repoName = `${d.owner}/${d.repo}`.toLowerCase();
        const matchesQuery = !q || repoName.includes(q) || (d.profile || "").toLowerCase().includes(q);
        const matchesProfile = profile === "all" || d.profile === profile || d.platform === profile;
        const matchesStatus = status === "all" || d.status === status;
        return matchesQuery && matchesProfile && matchesStatus;
    });
    renderTable();
}

function renderTable() {
    const tableBody = document.getElementById("deployments-table-body");
    if (!tableBody) return;

    // Re-create header row
    const header = `
        <div class="card-table__row header-row">
            <div class="card-table__item" style="justify-content:center;">#</div>
            <div class="card-table__item">Repository & Branch</div>
            <div class="card-table__item">Platform / Profile</div>
            <div class="card-table__item">Status</div>
            <div class="card-table__item">Live Endpoint</div>
            <div class="card-table__item">Triggered</div>
            <div class="card-table__item">Actions</div>
        </div>
    `;

    if (filteredDeployments.length === 0) {
        tableBody.innerHTML = header + `
            <div class="card-table__row placeholder-row">
                <div class="card-table__item" style="grid-column: span 7; justify-content: center; opacity: 0.6; padding: 40px;">
                    <div style="text-align:center;">
                        <div style="font-size: 36px; margin-bottom: 12px; opacity: 0.5;">📦</div>
                        <div style="margin-bottom: 16px;">No deployments yet</div>
                        <a href="./repositories.html" class="btn-primary-action">Deploy A Repository</a>
                    </div>
                </div>
            </div>
        `;
        const showingLabel = document.getElementById("showing-entries-label");
        if (showingLabel) showingLabel.textContent = "Showing 0 deployments";
        const prev = document.getElementById("btn-prev-page");
        const next = document.getElementById("btn-next-page");
        if (prev) prev.disabled = true;
        if (next) next.disabled = true;
        return;
    }

    tableBody.innerHTML = header;

    filteredDeployments.forEach((d, index) => {
        const row = document.createElement("div");
        row.className = "card-table__row";
        row.dataset.deploymentId = d.id;
        row.dataset.status = d.status;

        const platformBadge = d.platform === "render"
            ? `<span style="background:#6E49E0; color:#fff; padding:2px 8px; border-radius:4px; font-size:11px; font-weight:600;">RENDER</span>`
            : `<span style="background:#24292F; color:#fff; padding:2px 8px; border-radius:4px; font-size:11px; font-weight:600;">PAGES</span>`;
        const profileChip = d.profile
            ? `<span style="background:var(--primary-light); color:var(--text-color); padding:2px 6px; border-radius:4px; font-size:10px; font-family:'JetBrains Mono', monospace;">${escapeHtml(d.profile)}</span>`
            : "";

        const statusBadge = renderStatusBadge(d.status);
        const liveUrl = d.url
            ? `<a href="${d.url}" target="_blank" style="color:#3b82f6; text-decoration:none; font-size:12px;">${escapeHtml(d.url.replace(/^https?:\/\//, ""))}</a>
               <button class="action-btn" style="padding:2px 6px; margin-left:4px;" onclick="copyToClipboard('${d.url}')" title="Copy URL"><span class="btn-icon">📋</span></button>`
            : `<span style="color: var(--text-muted); font-size:12px;">—</span>`;
        const timeAgo = formatTimeAgo(d.created_at);

        const actionRow = `
            <div class="action-group" style="gap: 4px;">
                <button class="action-btn" data-action="refresh" data-id="${d.id}" title="Refresh status"><span class="btn-label">Refresh</span><span class="btn-icon">⟳</span></button>
                <button class="action-btn" data-action="redeploy" data-id="${d.id}" title="Redeploy"><span class="btn-label">Redeploy</span><span class="btn-icon">🚀</span></button>
                ${d.platform === "render" && d.service_id ? `
                    <a class="action-btn" href="https://dashboard.render.com/web/${d.service_id}" target="_blank" title="Open in Render" style="text-decoration:none;">
                        <span class="btn-label">Logs</span><span class="btn-icon">↗</span>
                    </a>` : d.platform === "github_pages" ? `
                    <a class="action-btn" href="https://github.com/${d.owner}/${d.repo}/actions" target="_blank" title="Open GitHub Actions" style="text-decoration:none;">
                        <span class="btn-label">Actions</span><span class="btn-icon">↗</span>
                    </a>` : ""}
                <button class="action-btn" data-action="inspect" data-id="${d.id}" title="Inspect"><span class="btn-label">Details</span><span class="btn-icon">👁</span></button>
                <button class="action-btn" data-action="delete" data-id="${d.id}" style="color:#ef4444;" title="Delete from history"><span class="btn-label">Delete</span><span class="btn-icon">🗑</span></button>
                ${d.status === "failed" ? `
                    <button class="action-btn" data-action="ask-agent" data-id="${d.id}" style="color:#8b5cf6;" title="Ask AI Agent to diagnose">
                        <span class="btn-label">Ask Agent</span><span class="btn-icon">🤖</span>
                    </button>` : ""}
                ${d.platform === "render" ? `
                    <button class="action-btn" data-action="add-domain" data-id="${d.id}" style="color:#0891b2;" title="Add custom domain">
                        <span class="btn-label">+ Domain</span><span class="btn-icon">🌐</span>
                    </button>` : ""}
            </div>
        `;

        // Expandable error row (only when status=failed and error text present)
        const errorBox = (d.status === "failed" && d.error)
            ? `<details style="margin-top:6px; grid-column: span 7; padding: 6px 12px; background: var(--status-danger-bg); border-left: 3px solid var(--status-danger-text); border-radius: 4px;">
                <summary style="cursor:pointer; font-size: 11px; color: var(--status-danger-text); font-weight: 600;">⚠ Show build error</summary>
                <pre style="margin-top:6px; padding: 8px; background: rgba(0,0,0,0.04); border-radius: 4px; font-size: 11px; font-family: 'JetBrains Mono', monospace; white-space: pre-wrap; max-height: 280px; overflow: auto;">${escapeHtml(d.error.slice(0, 4000))}</pre>
            </details>`
            : "";

        row.innerHTML = `
            <div class="card-table__item" style="justify-content:center;">${index + 1}</div>
            <div class="card-table__item">
                <div style="font-weight: 600; font-size: 13px;">${escapeHtml(d.owner)}/${escapeHtml(d.repo)}</div>
                <div style="font-size: 11px; color: var(--text-muted); margin-top: 2px;">
                    <span style="opacity:0.7;">⌥</span> ${escapeHtml(d.branch)}
                </div>
            </div>
            <div class="card-table__item" style="gap:6px;">
                ${platformBadge}
                ${profileChip}
            </div>
            <div class="card-table__item">
                ${statusBadge}
            </div>
            <div class="card-table__item">${liveUrl}</div>
            <div class="card-table__item" style="font-size: 12px; color: var(--text-muted);">${timeAgo}</div>
            <div class="card-table__item">${actionRow}</div>
            ${errorBox}
        `;
        tableBody.appendChild(row);
    });

    const showingLabel = document.getElementById("showing-entries-label");
    if (showingLabel) showingLabel.textContent = `Showing ${filteredDeployments.length} deployment(s)`;

    // Wire action buttons
    tableBody.querySelectorAll(".action-btn[data-action]").forEach((btn) => {
        btn.addEventListener("click", () => handleAction(btn.dataset.action, btn.dataset.id));
    });
}

function renderStatusBadge(s) {
    const map = {
        pending: { label: "Pending", bg: "var(--status-info-bg)", text: "var(--status-info-text)" },
        building: { label: "Building", bg: "var(--status-warning-bg)", text: "var(--status-warning-text)" },
        live: { label: "Live", bg: "var(--status-success-bg)", text: "var(--status-success-text)" },
        failed: { label: "Failed", bg: "var(--status-danger-bg)", text: "var(--status-danger-text)" },
    };
    const cfg = map[s] || map.pending;
    return `<span style="background:${cfg.bg}; color:${cfg.text}; padding: 3px 10px; border-radius: 4px; font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;">${cfg.label}</span>`;
}

// ============================================================================
// ACTIONS (Refresh / Redeploy / Inspect / Delete / Ask Agent / Add Domain)
// ============================================================================

async function handleAction(action, deploymentId) {
    if (action === "refresh") return refreshOne(deploymentId);
    if (action === "redeploy") return redeployOne(deploymentId);
    if (action === "inspect") return inspectDeployment(deploymentId);
    if (action === "delete") return deleteDeployment(deploymentId);
    if (action === "ask-agent") return askAgentAboutFailure(deploymentId);
    if (action === "add-domain") return openCustomDomainModal(deploymentId);
}

async function refreshOne(deploymentId) {
    try {
        const res = await fetch(`${BACKEND_API_URL}/deployments/${deploymentId}/refresh`, {
            method: "POST",
            headers: { "Authorization": `Bearer ${sessionToken}` },
        });
        if (!res.ok) {
            const err = await res.json().catch(() => ({ detail: res.statusText }));
            throw new Error(err.detail || `Refresh failed (${res.status})`);
        }
        const updated = await res.json();
        // Patch the row in place
        const idx = allDeployments.findIndex((d) => d.id === deploymentId);
        if (idx >= 0) allDeployments[idx] = updated;
        applyFilters();
    } catch (err) {
        showToast(`Refresh failed: ${err.message}`);
    }
}

async function redeployOne(deploymentId) {
    if (!(await window.showCustomConfirm("Deploy", "Trigger a new deploy on the platform?"))) return;
    try {
        const res = await fetch(`${BACKEND_API_URL}/deployments/${deploymentId}/redeploy`, {
            method: "POST",
            headers: { "Authorization": `Bearer ${sessionToken}` },
        });
        if (!res.ok) {
            const err = await res.json().catch(() => ({ detail: res.statusText }));
            throw new Error(err.detail || `Redeploy failed (${res.status})`);
        }
        showToast("Redeploy triggered. Status will refresh shortly.");
        await refreshOne(deploymentId);
    } catch (err) {
        showToast(`Redeploy failed: ${err.message}`);
    }
}

async function deleteDeployment(deploymentId) {
    if (!(await window.showCustomConfirm("Remove Deployment", "Remove this deployment from history?\n(The actual Render service / Pages site keeps running — only the history entry is removed.)"))) return;
    try {
        const res = await fetch(`${BACKEND_API_URL}/deployments/${deploymentId}`, {
            method: "DELETE",
            headers: { "Authorization": `Bearer ${sessionToken}` },
        });
        if (!res.ok) {
            const err = await res.json().catch(() => ({ detail: res.statusText }));
            throw new Error(err.detail || `Delete failed (${res.status})`);
        }
        allDeployments = allDeployments.filter((d) => d.id !== deploymentId);
        applyFilters();
        updateSummaryStats();
        showToast("Deployment removed from history.");
    } catch (err) {
        showToast(`Delete failed: ${err.message}`);
    }
}

async function syncLiveStatuses() {
    // Refresh every visible row in one pass
    const ids = filteredDeployments.map((d) => d.id);
    await Promise.all(ids.map(refreshOne));
    showToast("Status synced.");
}

async function clearHistory() {
    if (!(await window.showCustomConfirm("Clear History", "Clear ALL failed/pending deployments from history?\n(Live ones will be kept.)"))) return;
    // Delete every non-live deployment row
    const toDelete = allDeployments.filter((d) => d.status !== "live");
    await Promise.all(toDelete.map((d) =>
        fetch(`${BACKEND_API_URL}/deployments/${d.id}`, {
            method: "DELETE",
            headers: { "Authorization": `Bearer ${sessionToken}` },
        }).catch(() => null)
    ));
    await loadDeploymentsData();
    showToast("History cleared.");
}

function inspectDeployment(deploymentId) {
    const d = allDeployments.find((x) => x.id === deploymentId);
    if (!d) return;
    const modal = document.getElementById("deployment-modal");
    if (!modal) return;

    document.getElementById("modal-repo-title").textContent = `${d.owner}/${d.repo}`;
    document.getElementById("modal-field-repo").textContent = `${d.owner}/${d.repo}`;
    document.getElementById("modal-field-branch").textContent = d.branch;
    document.getElementById("modal-field-profile").textContent = d.profile || d.platform;
    document.getElementById("modal-field-workflow").textContent = d.service_id || d.external_deploy_id || "-";
    document.getElementById("modal-field-url").textContent = d.url || "(not yet live)";
    document.getElementById("modal-field-message").textContent = d.error || d.status;
    document.getElementById("modal-field-time").textContent = formatTimeAgo(d.created_at);
    document.getElementById("modal-field-status").textContent = d.status;

    const openSite = document.getElementById("modal-btn-open-site");
    const openActions = document.getElementById("modal-btn-open-actions");
    if (openSite) openSite.href = d.url || "#";
    if (openActions) {
        openActions.href = d.platform === "render" && d.service_id
            ? `https://dashboard.render.com/web/${d.service_id}`
            : `https://github.com/${d.owner}/${d.repo}/actions`;
    }
    modal.classList.add("active");
    modal.style.display = "flex";
}

function closeModal() {
    const modal = document.getElementById("deployment-modal");
    if (modal) {
        modal.classList.remove("active");
        modal.style.display = "none";
    }
}

function askAgentAboutFailure(deploymentId) {
    const d = allDeployments.find((x) => x.id === deploymentId);
    if (!d) return;
    // Persist the question the agent page should pre-fill
    sessionStorage.setItem("agent_prefill_question",
        `Why did my deploy of ${d.owner}/${d.repo} fail? Read the logs and tell me how to fix it.`);
    sessionStorage.setItem("agent_prefill_deployment_id", deploymentId);
    window.location.href = "./agent.html";
}

// ============================================================================
// AUTO-REFRESH — only polls when a visible row is pending/building
// ============================================================================

function startAutoRefresh() {
    if (autoRefreshTimer) return;
    autoRefreshTimer = setInterval(async () => {
        const pending = allDeployments.filter(
            (d) => d.status === "pending" || d.status === "building"
        );
        if (pending.length === 0) {
            // Nothing to refresh — stop the timer; restart on next manual refresh.
            stopAutoRefresh();
            return;
        }
        await Promise.all(pending.map((d) => refreshOne(d.id)));
    }, AUTO_REFRESH_INTERVAL_MS);
}

function stopAutoRefresh() {
    if (autoRefreshTimer) {
        clearInterval(autoRefreshTimer);
        autoRefreshTimer = null;
    }
}

// ============================================================================
// CUSTOM DOMAIN MODAL  (Feature ① — Render UI side, lives here for now)
// ============================================================================

async function openCustomDomainModal(deploymentId) {
    const d = allDeployments.find((x) => x.id === deploymentId);
    if (!d || d.platform !== "render") {
        showToast("Custom domains are only supported for Render services right now.");
        return;
    }
    // Reuse the deployment modal by injecting a domain block at the bottom.
    inspectDeployment(deploymentId);

    const modal = document.getElementById("deployment-modal");
    let domainBlock = document.getElementById("custom-domain-block");
    if (!domainBlock) {
        domainBlock = document.createElement("div");
        domainBlock.id = "custom-domain-block";
        domainBlock.style.cssText = "margin-top: 16px; padding: 12px; border-top: 1px solid var(--border-color);";
        modal.querySelector(".modal-content")?.appendChild(domainBlock);
    }

    domainBlock.innerHTML = `
        <h4 style="margin-bottom: 8px; font-size: 14px;">Add Custom Domain</h4>
        <input id="custom-domain-input" type="text" placeholder="notes.kumar.dev"
               style="width: 100%; padding: 8px; border: 1px solid var(--border-color); border-radius: 4px; background: var(--surface-color); color: var(--text-color); margin-bottom: 8px;" />
        <button id="custom-domain-add-btn" class="btn-primary-action" style="font-size: 12px; padding: 6px 12px;">Claim on Render</button>
        <div id="custom-domain-result" style="margin-top: 12px;"></div>
    `;

    document.getElementById("custom-domain-add-btn").addEventListener("click", async () => {
        const domain = document.getElementById("custom-domain-input").value.trim().toLowerCase();
        if (!domain || !/^[a-z0-9.-]+\.[a-z]{2,}$/.test(domain)) {
            showToast("Enter a valid domain like notes.kumar.dev (no https://, no path).");
            return;
        }
        await claimRenderCustomDomain(d, domain);
    });
}

async function claimRenderCustomDomain(deployment, domain) {
    const resultBox = document.getElementById("custom-domain-result");
    resultBox.innerHTML = `<div style="color: var(--text-muted); font-size: 12px;">Claiming ${domain} on Render…</div>`;

    try {
        const res = await fetch(`${BACKEND_API_URL}/render/services/${deployment.service_id}/custom-domain`, {
            method: "POST",
            headers: {
                "Authorization": `Bearer ${sessionToken}`,
                "Content-Type": "application/json",
            },
            body: JSON.stringify({ domain }),
        });
        if (!res.ok) {
            const err = await res.json().catch(() => ({ detail: res.statusText }));
            throw new Error(err.detail || `Failed (${res.status})`);
        }
        const data = await res.json();
        const cname = data.cname_target || `${deployment.service_id}.onrender.com`;
        resultBox.innerHTML = `
            <div style="background: var(--status-success-bg); color: var(--status-success-text); padding: 12px; border-radius: 4px; font-size: 12px;">
                <div style="font-weight: 600; margin-bottom: 6px;">✓ Claimed. Add this DNS record:</div>
                <div style="background: rgba(0,0,0,0.05); padding: 8px; border-radius: 4px; font-family: 'JetBrains Mono', monospace;">
                    Type: <strong>CNAME</strong><br>
                    Name: <strong>${domain.split(".")[0]}</strong><br>
                    Value: <strong>${cname}</strong>
                    <button onclick="copyToClipboard('CNAME ${domain.split('.')[0]} ${cname}')" style="margin-left:8px; padding:2px 6px; background:transparent; border:1px solid currentColor; border-radius:3px; cursor:pointer; font-size:11px;">Copy</button>
                </div>
                <button id="custom-domain-verify-btn" class="btn-primary-action" style="margin-top: 8px; font-size: 12px;">I've added it → Verify</button>
            </div>
        `;
        document.getElementById("custom-domain-verify-btn").addEventListener("click", async () => {
            await verifyRenderCustomDomain(deployment, domain);
        });
    } catch (err) {
        resultBox.innerHTML = `<div style="color: var(--status-danger-text); font-size: 12px;">✗ ${err.message}</div>`;
    }
}

async function verifyRenderCustomDomain(deployment, domain) {
    const resultBox = document.getElementById("custom-domain-result");
    resultBox.innerHTML += `<div id="verify-msg" style="color: var(--text-muted); font-size: 12px; margin-top: 6px;">Verifying…</div>`;
    const verifyMsg = document.getElementById("verify-msg");

    try {
        const res = await fetch(`${BACKEND_API_URL}/render/services/${deployment.service_id}/custom-domain/${domain}/verify`, {
            method: "POST",
            headers: { "Authorization": `Bearer ${sessionToken}` },
        });
        if (!res.ok) {
            const err = await res.json().catch(() => ({ detail: res.statusText }));
            throw new Error(err.detail || `Failed (${res.status})`);
        }
        const data = await res.json();
        const status = data.verification_status || "unverified";
        if (status === "verified") {
            verifyMsg.innerHTML = `🔒 <strong>Verified.</strong> TLS cert will be issued shortly. Live at <a href="https://${domain}" target="_blank" style="color:#3b82f6;">https://${domain}</a>`;
        } else {
            verifyMsg.innerHTML = `⏳ DNS not yet detected (status: ${status}). Check back in a few minutes — DNS propagation can take 5 min – 48 h.`;
        }
    } catch (err) {
        verifyMsg.innerHTML = `✗ ${err.message}`;
    }
}

// ============================================================================
// UTILITIES
// ============================================================================

function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => showToast("Copied to clipboard"));
}

function showToast(message) {
    const toast = document.getElementById("toast");
    const toastText = document.getElementById("toast-text");
    if (!toast || !toastText) return;
    toastText.textContent = message;
    toast.classList.add("show");
    setTimeout(() => toast.classList.remove("show"), 3000);
}

function formatTimeAgo(isoString) {
    if (!isoString) return "—";
    const date = new Date(isoString);
    const seconds = Math.floor((Date.now() - date.getTime()) / 1000);
    if (seconds < 60) return "just now";
    const minutes = Math.floor(seconds / 60);
    if (minutes < 60) return `${minutes}m ago`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours}h ago`;
    const days = Math.floor(hours / 24);
    if (days < 30) return `${days}d ago`;
    return date.toLocaleDateString();
}

function escapeHtml(str) {
    if (str == null) return "";
    return String(str)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

// Expose for inline onclick handlers
window.copyToClipboard = copyToClipboard;
window.inspectDeployment = inspectDeployment;
window.deleteDeployment = deleteDeployment;
window.closeModal = closeModal;
