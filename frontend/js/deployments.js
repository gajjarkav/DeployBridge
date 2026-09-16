/**
 * DeployBridge - Deployments Page Controller
 * Handles deployment log hydration, filtering, live status sync, modal inspector, and storage.
 */

let allDeployments = [];
let filteredDeployments = [];
let currentPage = 1;
const pageSize = 10;
let currentSession = null;

window.onload = async () => {
    // Initialize session & shell
    currentSession = initializeAppShell("deployments");
    if (!currentSession) {
        return;
    }

    hydrateUserInfo();
    loadDeploymentsData();
    bindEvents();
};

function hydrateUserInfo() {
    const username = localStorage.getItem("gh_username") || "Developer";
    const avatar = localStorage.getItem("gh_avatar") || `https://github.com/identicons/${username}.png`;

    const userDisplayName = document.getElementById("user-display-name");
    const userAvatar = document.getElementById("user-avatar");

    if (userDisplayName) userDisplayName.textContent = username;
    if (userAvatar) {
        userAvatar.src = avatar;
        userAvatar.alt = `${username}'s avatar`;
    }
}

function loadDeploymentsData() {
    allDeployments = readRecentDeployments();

    // If no deployments in local storage yet, add initial welcome sample deployment if user is logged in
    if (!allDeployments || allDeployments.length === 0) {
        const username = localStorage.getItem("gh_username") || "username";
        // Check if there are any seeded sample records
        const sampleDeployments = [
            {
                owner: username,
                repository: `${username}/portfolio-site`,
                repoName: "portfolio-site",
                message: "Deployment workflow successfully committed to repository.",
                profile: "html",
                workflowTemplate: "pages-html.yml",
                branch: "main",
                status: "success",
                pagesUrl: `https://${username.toLowerCase()}.github.io/portfolio-site`,
                actionsUrl: `https://github.com/${username}/portfolio-site/actions`,
                repoUrl: `https://github.com/${username}/portfolio-site`,
                recordedAt: new Date(Date.now() - 1000 * 60 * 35).toISOString(),
            },
            {
                owner: username,
                repository: `${username}/docs-portal`,
                repoName: "docs-portal",
                message: "Node static build pipeline configured and dispatched.",
                profile: "node-static",
                workflowTemplate: "pages-node-static.yml",
                branch: "main",
                status: "live",
                pagesUrl: `https://${username.toLowerCase()}.github.io/docs-portal`,
                actionsUrl: `https://github.com/${username}/docs-portal/actions`,
                repoUrl: `https://github.com/${username}/docs-portal`,
                recordedAt: new Date(Date.now() - 1000 * 60 * 60 * 4).toISOString(),
            }
        ];

        // Only pre-populate if user has never saved before
        if (!localStorage.getItem("db_deployments_initialized")) {
            allDeployments = sampleDeployments;
            localStorage.setItem("deploybridge_recent_deployments", JSON.stringify(sampleDeployments));
            localStorage.setItem("db_deployments_initialized", "true");
        }
    }

    applyFilters();
    updateSummaryStats();
}

function updateSummaryStats() {
    const totalCountNode = document.getElementById("stat-total-deploys");
    const liveCountNode = document.getElementById("stat-live-sites");
    const successRateNode = document.getElementById("stat-success-rate");
    const latestProfileNode = document.getElementById("stat-latest-profile");

    const total = allDeployments.length;
    const liveCount = allDeployments.filter(d => d.status === "live" || d.status === "success" || d.status === "built").length;
    const failedCount = allDeployments.filter(d => d.status === "failed" || d.status === "errored").length;
    
    const rate = total > 0 ? Math.round(((total - failedCount) / total) * 100) : 100;
    const latestProfile = total > 0 && allDeployments[0]?.profile ? allDeployments[0].profile.toUpperCase() : "-";

    if (totalCountNode) totalCountNode.textContent = String(total);
    if (liveCountNode) liveCountNode.textContent = String(liveCount);
    if (successRateNode) successRateNode.textContent = `${rate}%`;
    if (latestProfileNode) latestProfileNode.textContent = latestProfile;
}

function bindEvents() {
    const searchInput = document.getElementById("deployments-search");
    const filterProfile = document.getElementById("filter-profile");
    const filterStatus = document.getElementById("filter-status");
    const btnSyncStatus = document.getElementById("btn-sync-status");
    const btnClearHistory = document.getElementById("btn-clear-history");
    const btnCloseModal = document.getElementById("btn-close-modal");
    const modalBtnClose = document.getElementById("modal-btn-close");
    const deploymentModal = document.getElementById("deployment-modal");
    const btnPrev = document.getElementById("btn-prev-page");
    const btnNext = document.getElementById("btn-next-page");

    if (searchInput) {
        searchInput.addEventListener("input", () => {
            currentPage = 1;
            applyFilters();
        });
    }

    if (filterProfile) {
        filterProfile.addEventListener("change", () => {
            currentPage = 1;
            applyFilters();
        });
    }

    if (filterStatus) {
        filterStatus.addEventListener("change", () => {
            currentPage = 1;
            applyFilters();
        });
    }

    if (btnSyncStatus) {
        btnSyncStatus.addEventListener("click", syncLiveStatuses);
    }

    if (btnClearHistory) {
        btnClearHistory.addEventListener("click", () => {
            if (confirm("Are you sure you want to clear your local deployment history?")) {
                allDeployments = [];
                localStorage.setItem("deploybridge_recent_deployments", JSON.stringify([]));
                applyFilters();
                updateSummaryStats();
                showToast("Deployment history cleared.");
            }
        });
    }

    if (btnCloseModal) {
        btnCloseModal.addEventListener("click", closeModal);
    }

    if (modalBtnClose) {
        modalBtnClose.addEventListener("click", closeModal);
    }

    if (deploymentModal) {
        deploymentModal.addEventListener("click", (e) => {
            if (e.target === deploymentModal) {
                closeModal();
            }
        });
    }

    document.addEventListener("keydown", (e) => {
        if (e.key === "Escape") {
            closeModal();
        }
    });

    if (btnPrev) {
        btnPrev.addEventListener("click", () => {
            if (currentPage > 1) {
                currentPage--;
                renderTable();
            }
        });
    }

    if (btnNext) {
        btnNext.addEventListener("click", () => {
            const maxPage = Math.ceil(filteredDeployments.length / pageSize) || 1;
            if (currentPage < maxPage) {
                currentPage++;
                renderTable();
            }
        });
    }
}

function applyFilters() {
    const searchVal = (document.getElementById("deployments-search")?.value || "").trim().toLowerCase();
    const profileVal = document.getElementById("filter-profile")?.value || "all";
    const statusVal = document.getElementById("filter-status")?.value || "all";

    filteredDeployments = allDeployments.filter(entry => {
        const repoName = (entry.repository || entry.repoName || "").toLowerCase();
        const branch = (entry.branch || "").toLowerCase();
        const profile = (entry.profile || "").toLowerCase();
        const message = (entry.message || "").toLowerCase();
        const status = (entry.status || "success").toLowerCase();

        // Search match
        const matchesSearch = !searchVal || 
            repoName.includes(searchVal) || 
            branch.includes(searchVal) || 
            profile.includes(searchVal) || 
            message.includes(searchVal);

        // Profile match
        const matchesProfile = profileVal === "all" || profile.includes(profileVal);

        // Status match
        let matchesStatus = true;
        if (statusVal === "success") {
            matchesStatus = status === "success" || status === "live" || status === "built";
        } else if (statusVal === "building") {
            matchesStatus = status === "building" || status === "queued" || status === "pending";
        } else if (statusVal === "failed") {
            matchesStatus = status === "failed" || status === "errored";
        }

        return matchesSearch && matchesProfile && matchesStatus;
    });

    renderTable();
}

function renderTable() {
    const tableBody = document.getElementById("deployments-table-body");
    const showingEntriesLabel = document.getElementById("showing-entries-label");
    const btnPrev = document.getElementById("btn-prev-page");
    const btnNext = document.getElementById("btn-next-page");

    if (!tableBody) return;

    // Remove old rows except header
    const rows = tableBody.querySelectorAll(".card-table__row:not(.header-row)");
    rows.forEach(r => r.remove());

    const totalFiltered = filteredDeployments.length;
    const totalPages = Math.ceil(totalFiltered / pageSize) || 1;
    if (currentPage > totalPages) currentPage = totalPages;

    const startIdx = (currentPage - 1) * pageSize;
    const pageItems = filteredDeployments.slice(startIdx, startIdx + pageSize);

    if (showingEntriesLabel) {
        showingEntriesLabel.textContent = `Showing ${pageItems.length > 0 ? startIdx + 1 : 0}-${startIdx + pageItems.length} of ${totalFiltered} deployment${totalFiltered === 1 ? '' : 's'}`;
    }

    if (btnPrev) btnPrev.disabled = currentPage <= 1;
    if (btnNext) btnNext.disabled = currentPage >= totalPages;

    if (pageItems.length === 0) {
        const emptyRow = document.createElement("div");
        emptyRow.className = "card-table__row";
        emptyRow.innerHTML = `
            <div class="card-table__item empty-state-card">
                <div class="empty-icon-wrap">
                    <svg viewBox="0 0 24 24" width="28" height="28" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="color:var(--text-muted);"><path d="M4.5 16.5c-1.5 1.26-2 5-2 5s3.74-.5 5-2c.71-.84.7-2.13-.09-2.91a2.18 2.18 0 0 0-2.91-.09z"></path><path d="m12 15-3-3a22 22 0 0 1 2-3.95A12.88 12.88 0 0 1 22 2c0 2.72-.78 7.5-6 11a22.35 22.35 0 0 1-4 2z"></path></svg>
                </div>
                <h3>No Deployments Found</h3>
                <p>No deployment records match your current filter query. You can deploy repositories directly with automated GitHub Pages workflows.</p>
                <a href="./repositories.html" class="btn-primary-action" style="margin-top:8px;">
                    <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 5v14M5 12h14"></path></svg>
                    <span>Deploy A Repository</span>
                </a>
            </div>
        `;
        tableBody.appendChild(emptyRow);
        return;
    }

    pageItems.forEach((entry, idx) => {
        const indexNumber = startIdx + idx + 1;
        const row = document.createElement("div");
        row.className = "card-table__row";

        const owner = entry.owner || (entry.repository ? entry.repository.split("/")[0] : "user");
        const repoShort = entry.repoName || (entry.repository ? entry.repository.split("/")[1] || entry.repository : "repo");
        const fullRepo = entry.repository || `${owner}/${repoShort}`;
        const branch = entry.branch || "main";
        const profile = entry.profile || "html";
        const workflowTemplate = entry.workflowTemplate || "pages.yml";
        const status = (entry.status || "success").toLowerCase();
        
        let statusBadgeClass = "live";
        let statusLabel = "Live";
        if (status === "building" || status === "queued" || status === "pending") {
            statusBadgeClass = "building";
            statusLabel = "Building";
        } else if (status === "failed" || status === "errored") {
            statusBadgeClass = "failed";
            statusLabel = "Failed";
        } else if (status === "configured") {
            statusBadgeClass = "configured";
            statusLabel = "Ready";
        }

        const pagesUrl = entry.pagesUrl || `https://${owner.toLowerCase()}.github.io/${repoShort}`;
        const repoUrl = entry.repoUrl || `https://github.com/${fullRepo}`;
        const actionsUrl = entry.actionsUrl || `https://github.com/${fullRepo}/actions`;
        const timeAgo = formatTimeAgo(entry.recordedAt);

        row.innerHTML = `
            <div class="card-table__item" style="justify-content:center; color:var(--text-muted); font-weight:700;">${indexNumber}</div>
            
            <div class="card-table__item">
                <div class="repo-meta-cell">
                    <a href="${escapeHtml(repoUrl)}" target="_blank" class="repo-title-link" title="Open ${escapeHtml(fullRepo)} on GitHub">
                        <span>${escapeHtml(fullRepo)}</span>
                        <svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="opacity:0.6;"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path><polyline points="15 3 21 3 21 9"></polyline><line x1="10" y1="14" x2="21" y2="3"></line></svg>
                    </a>
                    <span class="branch-badge">
                        <svg viewBox="0 0 24 24" width="10" height="10" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="6" y1="3" x2="6" y2="15"></line><circle cx="18" cy="6" r="3"></circle><circle cx="6" cy="18" r="3"></circle><path d="M18 9a9 9 0 0 1-9 9"></path></svg>
                        ${escapeHtml(branch)}
                    </span>
                </div>
            </div>

            <div class="card-table__item">
                <div style="display:flex; flex-direction:column; gap:4px;">
                    <span class="profile-tag">
                        <span style="opacity:0.6;">engine:</span>${escapeHtml(profile)}
                    </span>
                    <span style="font-size:10.5px; color:var(--text-muted); font-family:'JetBrains Mono', monospace;">${escapeHtml(workflowTemplate)}</span>
                </div>
            </div>

            <div class="card-table__item">
                <span class="status-badge ${statusBadgeClass}">
                    <span class="status-indicator-dot"></span>
                    ${statusLabel}
                </span>
            </div>

            <div class="card-table__item">
                <div class="url-link-wrapper">
                    <a href="${escapeHtml(pagesUrl)}" target="_blank" class="pages-link" title="${escapeHtml(pagesUrl)}">
                        ${escapeHtml(pagesUrl.replace(/^https?:\/\//, ''))}
                    </a>
                    <button class="copy-url-btn" onclick="copyToClipboard('${escapeHtml(pagesUrl)}')" title="Copy URL">
                        <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>
                    </button>
                </div>
            </div>

            <div class="card-table__item" style="font-size:12px; color:var(--text-muted); font-family:'JetBrains Mono', monospace;" title="${new Date(entry.recordedAt || Date.now()).toLocaleString()}">
                ${timeAgo}
            </div>

            <div class="card-table__item">
                <div class="action-group">
                    <a href="${escapeHtml(pagesUrl)}" target="_blank" class="action-btn" title="Open Site">
                        <span>Visit</span>
                    </a>
                    <button class="action-btn" onclick="inspectDeployment(${indexNumber - 1})" title="Inspect Details">
                        <span>Details</span>
                    </button>
                    <a href="${escapeHtml(actionsUrl)}" target="_blank" class="action-btn" title="GitHub Actions">
                        <span>Actions</span>
                    </a>
                    <button class="action-btn delete-btn" onclick="deleteDeployment(${indexNumber - 1})" title="Remove Record">
                        &times;
                    </button>
                </div>
            </div>
        `;

        tableBody.appendChild(row);
    });
}

function inspectDeployment(filteredIndex) {
    const entry = filteredDeployments[filteredIndex];
    if (!entry) return;

    const owner = entry.owner || (entry.repository ? entry.repository.split("/")[0] : "user");
    const repoShort = entry.repoName || (entry.repository ? entry.repository.split("/")[1] || entry.repository : "repo");
    const fullRepo = entry.repository || `${owner}/${repoShort}`;
    const branch = entry.branch || "main";
    const profile = entry.profile || "html";
    const workflowTemplate = entry.workflowTemplate || "pages.yml";
    const status = entry.status || "success";
    const pagesUrl = entry.pagesUrl || `https://${owner.toLowerCase()}.github.io/${repoShort}`;
    const actionsUrl = entry.actionsUrl || `https://github.com/${fullRepo}/actions`;

    document.getElementById("modal-repo-title").textContent = fullRepo;
    document.getElementById("modal-field-repo").textContent = fullRepo;
    document.getElementById("modal-field-branch").textContent = branch;
    document.getElementById("modal-field-profile").textContent = profile.toUpperCase();
    document.getElementById("modal-field-workflow").textContent = workflowTemplate;
    document.getElementById("modal-field-url").textContent = pagesUrl;
    document.getElementById("modal-field-message").textContent = entry.message || "Deployment initiated through DeployBridge automated engine.";
    document.getElementById("modal-field-time").textContent = new Date(entry.recordedAt || Date.now()).toLocaleString("en-US", {
        weekday: 'short',
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    });
    document.getElementById("modal-field-status").textContent = status.toUpperCase();

    const openSiteBtn = document.getElementById("modal-btn-open-site");
    const openActionsBtn = document.getElementById("modal-btn-open-actions");

    if (openSiteBtn) openSiteBtn.href = pagesUrl;
    if (openActionsBtn) openActionsBtn.href = actionsUrl;

    const modal = document.getElementById("deployment-modal");
    if (modal) modal.classList.add("active");
}

function closeModal() {
    const modal = document.getElementById("deployment-modal");
    if (modal) modal.classList.remove("active");
}

function deleteDeployment(filteredIndex) {
    const entry = filteredDeployments[filteredIndex];
    if (!entry) return;

    allDeployments = allDeployments.filter(item => item !== entry);
    localStorage.setItem("deploybridge_recent_deployments", JSON.stringify(allDeployments));
    applyFilters();
    updateSummaryStats();
    showToast("Deployment record removed.");
}

async function syncLiveStatuses() {
    const pipelineStatus = document.getElementById("pipeline-status");
    const token = localStorage.getItem("db_session_token") || localStorage.getItem("gh_access_token");

    if (pipelineStatus) pipelineStatus.textContent = "STATUS: SYNCING...";
    showToast("Syncing live deployment statuses with GitHub...");

    let updatedCount = 0;

    // Check each deployment against GitHub Pages / Actions
    for (const item of allDeployments) {
        try {
            const owner = item.owner || (item.repository ? item.repository.split("/")[0] : "");
            const repo = item.repoName || (item.repository ? item.repository.split("/")[1] : "");

            if (!owner || !repo) continue;

            // Attempt direct fetch to GitHub Pages endpoint if token is present
            if (token) {
                const response = await fetch(`https://api.github.com/repos/${owner}/${repo}/pages`, {
                    headers: {
                        'Accept': 'application/vnd.github.v3+json',
                        'Authorization': `Bearer ${token}`
                    }
                });

                if (response.ok) {
                    const data = await response.json();
                    if (data.html_url) item.pagesUrl = data.html_url;
                    if (data.status) {
                        item.status = data.status === "built" ? "live" : data.status;
                    }
                    if (data.source && data.source.branch) {
                        item.branch = data.source.branch;
                    }
                    updatedCount++;
                }
            }
        } catch (err) {
            console.warn("[DeployBridge] Sync error for repo:", item.repository, err);
        }
    }

    localStorage.setItem("deploybridge_recent_deployments", JSON.stringify(allDeployments));
    applyFilters();
    updateSummaryStats();

    if (pipelineStatus) pipelineStatus.textContent = "STATUS: SYNCD";
    showToast(`Status sync complete (${allDeployments.length} repos scanned).`);
}

function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        showToast("Live URL copied to clipboard!");
    }).catch(() => {
        showToast("Copied: " + text);
    });
}

function showToast(message) {
    const toast = document.getElementById("toast");
    const toastText = document.getElementById("toast-text");
    if (!toast || !toastText) return;

    toastText.textContent = message;
    toast.classList.add("show");

    setTimeout(() => {
        toast.classList.remove("show");
    }, 3000);
}

function formatTimeAgo(isoString) {
    if (!isoString) return "just now";
    const date = new Date(isoString);
    const now = new Date();
    const elapsedSeconds = Math.floor((now - date) / 1000);

    if (isNaN(elapsedSeconds) || elapsedSeconds < 0) return "just now";
    if (elapsedSeconds < 60) return `${elapsedSeconds}s ago`;
    const minutes = Math.floor(elapsedSeconds / 60);
    if (minutes < 60) return `${minutes}m ago`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours}h ago`;
    const days = Math.floor(hours / 24);
    if (days < 30) return `${days}d ago`;

    return date.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

function escapeHtml(str) {
    if (!str) return "";
    return String(str)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

// Global helper attachments for inline handlers
window.copyToClipboard = copyToClipboard;
window.inspectDeployment = inspectDeployment;
window.deleteDeployment = deleteDeployment;
