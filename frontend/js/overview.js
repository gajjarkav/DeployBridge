window.onload = async () => {
    const session = initializeAppShell("dashboard");
    if (!session) {
        return;
    }

    await hydrateOverview(session.token);
};

async function hydrateOverview(token) {
    const metrics = {
        repos: document.getElementById("metric-repos"),
        publicRepos: document.getElementById("metric-public"),
        privateRepos: document.getElementById("metric-private"),
        deployments: document.getElementById("metric-deployments"),
    };
    const recentDeployments = document.getElementById("recent-deployments");

    try {
        const response = await fetch("https://api.github.com/user/repos?sort=updated&per_page=50", {
            headers: {
                "Authorization": `Bearer ${token}`,
            },
        });

        if (!response.ok) {
            throw new Error("Could not load your GitHub overview data.");
        }

        const repos = await response.json();
        const publicRepos = repos.filter((repo) => repo.visibility === "public").length;
        const privateRepos = repos.filter((repo) => repo.visibility === "private").length;
        const deployments = readRecentDeployments();

        metrics.repos.textContent = String(repos.length);
        metrics.publicRepos.textContent = String(publicRepos);
        metrics.privateRepos.textContent = String(privateRepos);
        metrics.deployments.textContent = String(deployments.length);

        renderRecentDeployments(recentDeployments, deployments);
        renderFreshActivity(repos);
    } catch (error) {
        console.error(error);
        metrics.repos.textContent = "-";
        metrics.publicRepos.textContent = "-";
        metrics.privateRepos.textContent = "-";
        metrics.deployments.textContent = "-";
        recentDeployments.innerHTML = "<div class=\"timeline-card\"><strong>Overview unavailable</strong><p>GitHub data could not be loaded right now.</p></div>";
    }
}

function renderRecentDeployments(container, deployments) {
    if (!deployments.length) {
        container.innerHTML = "<div class=\"timeline-card\"><strong>No deployments yet</strong><p>Your successful DeployBridge GitHub Pages actions will appear here after you launch them from the repositories page.</p></div>";
        return;
    }

    container.innerHTML = deployments.map((entry) => `
        <div class="timeline-card">
            <strong>${entry.repository}</strong>
            <p>${entry.message}</p>
            <div class="timeline-meta">
                <span class="info-chip status-info">${entry.profile}</span>
                <span class="info-chip">${formatShortDate(entry.recordedAt)}</span>
            </div>
        </div>
    `).join("");
}

function renderFreshActivity(repos) {
    const container = document.getElementById("fresh-activity");
    const topRepos = repos.slice(0, 4);

    container.innerHTML = topRepos.map((repo) => `
        <div class="mini-stat">
            <strong>${repo.name}</strong>
            <span>${repo.visibility} repository · ${repo.language || "No primary language"}</span>
        </div>
    `).join("");
}

function formatShortDate(value) {
    return new Date(value).toLocaleString("en-US", {
        month: "short",
        day: "numeric",
        hour: "numeric",
        minute: "2-digit",
    });
}
