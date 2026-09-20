const BACKEND_API_URL = "http://127.0.0.1:8000/v1";

document.addEventListener("DOMContentLoaded", () => {
    const session = {
        token: localStorage.getItem("db_session_token"),
        dbSessionToken: localStorage.getItem("db_session_token"),
    };

    if (!session.dbSessionToken) {
        window.location.href = "./auth.html";
        return;
    }

    let currentPage = 1;
    const pageSize = 10;
    
    const tableBody = document.getElementById("reports-table");
    const statusText = document.getElementById("reports-status");
    const prevBtn = document.getElementById("prev-page");
    const nextBtn = document.getElementById("next-page");
    const pageInfo = document.getElementById("page-info");
    const refreshBtn = document.getElementById("refresh-reports-btn");

    const modal = document.getElementById("report-modal");
    const modalClose = document.getElementById("close-modal");
    const modalTitle = document.getElementById("modal-repo-name");
    const modalContent = document.getElementById("modal-report-content");
    const modalModel = document.getElementById("modal-model");
    const modalTokens = document.getElementById("modal-tokens");

    async function fetchReports(page) {
        statusText.textContent = "STATUS: SYNCING...";
        statusText.style.color = "var(--text-muted)";
        
        try {
            const res = await fetch(`${BACKEND_API_URL}/reports/history?page=${page}&page_size=${pageSize}`, {
                headers: { "Authorization": `Bearer ${session.dbSessionToken}` }
            });
            
            if (!res.ok) throw new Error("Failed to fetch reports");
            
            const data = await res.json();
            renderReports(data.items);
            
            currentPage = data.page;
            const totalPages = Math.ceil(data.total / data.page_size) || 1;
            
            pageInfo.textContent = `Page ${currentPage} of ${totalPages}`;
            prevBtn.disabled = currentPage <= 1;
            nextBtn.disabled = currentPage >= totalPages;
            
            statusText.textContent = "STATUS: SYNCED";
            statusText.style.color = "#22c55e";
        } catch (error) {
            console.error(error);
            statusText.textContent = "STATUS: ERROR";
            statusText.style.color = "#ef4444";
            tableBody.innerHTML = `<div class="card-table__row"><div class="card-table__item" style="grid-column: span 6; text-align: center; color: var(--text-muted);">Failed to load reports.</div></div>`;
        }
    }

    function renderReports(reports) {
        const header = `
            <div class="card-table__row header-row">
                <div class="card-table__item">#</div>
                <div class="card-table__item">Repository</div>
                <div class="card-table__item">Status</div>
                <div class="card-table__item">Generated</div>
                <div class="card-table__item">Model</div>
                <div class="card-table__item">Actions</div>
            </div>
        `;
        
        if (!reports || reports.length === 0) {
            tableBody.innerHTML = header + `<div class="card-table__row"><div class="card-table__item" style="grid-column: span 6; justify-content: center; color: var(--text-muted);">No reports found.</div></div>`;
            return;
        }

        tableBody.innerHTML = header;
        
        reports.forEach((report, index) => {
            const date = new Date(report.generated_at).toLocaleString();
            let statusColor = "var(--text-color)";
            if (report.status === "generated" || report.status === "delivered") statusColor = "#22c55e";
            if (report.status === "failed") statusColor = "#ef4444";
            if (report.status === "pending" || report.status === "generating") statusColor = "#eab308";

            let extraButtons = '';
            if (report.status === "generated" || report.status === "delivered") {
                extraButtons = `
                    <button class="action-btn download-btn" data-id="${report.id}" style="color:#3b82f6;"><span class="btn-label">PDF</span><span class="btn-icon">📥</span></button>
                    <button class="action-btn email-btn" data-id="${report.id}" style="color:#8b5cf6;"><span class="btn-label">Email</span><span class="btn-icon">✉️</span></button>
                `;
            }

            const row = document.createElement("div");
            row.className = "card-table__row";
            row.innerHTML = `
                <div class="card-table__item">${(currentPage - 1) * pageSize + index + 1}</div>
                <div class="card-table__item" style="font-weight:bold;">${report.repo_full_name}</div>
                <div class="card-table__item" style="color:${statusColor}; text-transform:capitalize;">${report.status}</div>
                <div class="card-table__item">${date}</div>
                <div class="card-table__item">${report.model_used || '-'}</div>
                <div class="card-table__item">
                    <div class="action-group">
                        <button class="action-btn view-btn" data-id="${report.id}"><span class="btn-label">View</span><span class="btn-icon">👁</span></button>
                        ${extraButtons}
                        <button class="action-btn delete-btn" data-id="${report.id}" style="color:#ef4444;"><span class="btn-label">Delete</span><span class="btn-icon">🗑</span></button>
                    </div>
                </div>
            `;
            tableBody.appendChild(row);
        });

        document.querySelectorAll(".view-btn").forEach(btn => {
            btn.addEventListener("click", () => openReport(btn.dataset.id));
        });
        document.querySelectorAll(".delete-btn").forEach(btn => {
            btn.addEventListener("click", () => deleteReport(btn.dataset.id));
        });
        document.querySelectorAll(".download-btn").forEach(btn => {
            btn.addEventListener("click", () => downloadReport(btn.dataset.id));
        });
        document.querySelectorAll(".email-btn").forEach(btn => {
            btn.addEventListener("click", () => resendEmail(btn.dataset.id));
        });
    }

    async function openReport(id) {
        modalTitle.textContent = "Loading...";
        modalContent.innerHTML = "Fetching report content...";
        modalModel.textContent = "";
        modalTokens.textContent = "";
        modal.style.display = "flex";

        try {
            const res = await fetch(`${BACKEND_API_URL}/reports/${id}`, {
                headers: { "Authorization": `Bearer ${session.dbSessionToken}` }
            });
            if (!res.ok) throw new Error("Failed to load report details");
            
            const data = await res.json();
            modalTitle.textContent = `${data.repo_full_name} Analysis`;
            
            if (data.report_markdown) {
                // If marked is available, parse markdown, otherwise display as text
                if (window.marked) {
                    modalContent.innerHTML = marked.parse(data.report_markdown);
                } else {
                    modalContent.textContent = data.report_markdown;
                    modalContent.style.whiteSpace = "pre-wrap";
                }
            } else if (data.status === 'failed') {
                modalContent.innerHTML = `<div style="color:#ef4444"><b>Error:</b> ${data.error_message || 'Generation failed.'}</div>`;
            } else {
                modalContent.textContent = `Report is currently in status: ${data.status}`;
            }

            modalModel.textContent = `Model: ${data.model_used || 'N/A'}`;
            modalTokens.textContent = `Tokens: ${data.prompt_tokens} (prompt) + ${data.completion_tokens} (comp) | Time: ${data.duration_ms}ms`;
        } catch (error) {
            console.error(error);
            modalContent.innerHTML = `<span style="color:#ef4444">Error loading report.</span>`;
        }
    }

    async async function deleteReport(id) {
        if (!(await window.showCustomConfirm("Delete Report", "Are you sure you want to delete this report?"))) return;
        
        try {
            const res = await fetch(`${BACKEND_API_URL}/reports/${id}`, {
                method: "DELETE",
                headers: { "Authorization": `Bearer ${session.dbSessionToken}` }
            });
            if (!res.ok) throw new Error("Failed to delete report");
            
            fetchReports(currentPage);
        } catch (error) {
            console.error(error);
            window.showCustomAlert("Report", "Error deleting report.");
        }
    }

    async function downloadReport(id) {
        try {
            const res = await fetch(`${BACKEND_API_URL}/reports/${id}/pdf`, {
                headers: { "Authorization": `Bearer ${session.dbSessionToken}` }
            });
            if (!res.ok) throw new Error("Failed to download PDF");
            
            const blob = await res.blob();
            const url = window.URL.createObjectURL(blob);
            window.open(url, '_blank');
        } catch (e) {
            console.error(e);
            window.showCustomAlert("Report", "Error downloading report");
        }
    }

    async function resendEmail(id) {
        if (!(await window.showCustomConfirm("Resend Report", "Are you sure you want to resend this report via email?"))) return;
        try {
            const res = await fetch(`${BACKEND_API_URL}/reports/${id}/send-email`, {
                method: "POST",
                headers: { "Authorization": `Bearer ${session.dbSessionToken}` }
            });
            if (!res.ok) throw new Error("Failed to resend email");
            window.showCustomAlert("Report", "Email dispatch started!");
        } catch (e) {
            console.error(e);
            window.showCustomAlert("Report", "Error resending email");
        }
    }

    prevBtn.addEventListener("click", () => fetchReports(currentPage - 1));
    nextBtn.addEventListener("click", () => fetchReports(currentPage + 1));
    refreshBtn.addEventListener("click", () => fetchReports(currentPage));
    modalClose.addEventListener("click", () => modal.style.display = "none");
    
    // Close modal on outside click
    modal.addEventListener("click", (e) => {
        if (e.target === modal) modal.style.display = "none";
    });

    fetchReports(currentPage);
});
