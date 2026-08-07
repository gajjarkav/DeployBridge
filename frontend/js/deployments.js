window.onload = async () => {
    const session = initializeAppShell("deployments");
    if (!session) {
        return;
    }

    renderDeploymentHistory();
};

function renderDeploymentHistory() {
    const items = readRecentDeployments();
    const container = document.getElementById("deployments-list");
    const countNode = document.getElementById("deployment-history-count");
    countNode.textContent = String(items.length);

    if (!items.length) {
        container.innerHTML = `
            <div class="empty-state">
                <h2>No deployment history yet</h2>
                <p>Deployments launched from the repositories page will be stored in your browser here so you can track what profile and workflow were used.</p>
            </div>
        `;
        return;
    }

    container.innerHTML = items.map((entry) => `
        <div class="timeline-card">
            <strong>${entry.repository}</strong>
            <p>${entry.message}</p>
            <div class="timeline-meta">
                <span class="info-chip status-info">${entry.profile}</span>
                <span class="info-chip">${entry.workflowTemplate}</span>
                <span class="info-chip">${new Date(entry.recordedAt).toLocaleString("en-US", {
                    month: "short",
                    day: "numeric",
                    hour: "numeric",
                    minute: "2-digit",
                })}</span>
            </div>
        </div>
    `).join("");
}
