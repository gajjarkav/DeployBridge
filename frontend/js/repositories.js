const BACKEND_API_URL = "http://127.0.0.1:8000/v1";

window.onload = async () => {
    const session = initializeAppShell("repositories");
    if (!session) {
        return;
    }

    await fetchAndRenderRepos(session.token);
};

async function fetchAndRenderRepos(token) {
    const tableBody = document.getElementById("repo-table-body");

    try {
        const response = await fetch("https://api.github.com/user/repos?sort=updated&per_page=50", {
            headers: {
                "Authorization": `Bearer ${token}`,
            },
        });

        if (!response.ok) {
            throw new Error("Failed to fetch repositories. Your GitHub token may be expired.");
        }

        const repos = await response.json();
        document.getElementById("repo-count").textContent = String(repos.length);
        tableBody.innerHTML = "";

        repos.forEach((repo, index) => {
            const tr = document.createElement("tr");
            const updatedAt = new Date(repo.updated_at).toLocaleDateString("en-US", {
                year: "numeric",
                month: "short",
                day: "numeric",
            });
            const status = repo.archived ? "Archived" : (repo.disabled ? "Disabled" : "Active");
            const statusClass = repo.archived ? "status-danger" : "status-success";

            tr.innerHTML = `
                <td>${index + 1}</td>
                <td>
                    <a class="repo-link" href="${repo.html_url}" target="_blank">${repo.name}</a>
                </td>
                <td>${repo.language || "Unknown"}</td>
                <td>${repo.visibility}</td>
                <td><span class="info-chip ${statusClass}">${status}</span></td>
                <td>${updatedAt}</td>
                <td>
                    <div class="row-actions">
                        <button class="table-button view" onclick="window.open('${repo.html_url}', '_blank')">View</button>
                        <button class="table-button scan" onclick="analyzeRepo('${repo.name}')">Analyze</button>
                        <button class="table-button deploy" onclick="deployGitHubPages('${repo.owner.login}','${repo.name}')">Deploy</button>
                    </div>
                </td>
            `;
            tableBody.appendChild(tr);
        });
    } catch (error) {
        console.error("Error:", error);
        tableBody.innerHTML = '<tr><td colspan="7" style="text-align:center;color:#b54a3a;">Error loading repositories.</td></tr>';
    }
}

window.analyzeRepo = (repoName) => {
    alert(`Initializing deep scan for: ${repoName}...\n\n(Backend hit!!)`);
};

window.deployGitHubPages = async (owner, repository) => {
    const session = getAuthSession();

    if (!session.token) {
        alert("GitHub login session is missing. Please sign in again.");
        return;
    }

    try {
        const detectData = await postGitHubPagesRequest("/github-pages/detect", session.token, {
            owner,
            repository,
        });

        const overrideInput = window.prompt(
            [
                `Detected profile for "${repository}": ${detectData.detected_profile}`,
                `Reason: ${detectData.reason}`,
                "",
                `Supported options: ${detectData.supported_profiles.join(", ")}`,
                'Type a profile name to override, or leave blank to use "auto".',
            ].join("\n"),
            "auto"
        );

        if (overrideInput === null) {
            return;
        }

        const selectedProfile = (overrideInput.trim() || "auto").toLowerCase();
        if (!detectData.supported_profiles.includes(selectedProfile)) {
            alert(`Unsupported deployment profile: ${selectedProfile}`);
            return;
        }

        const confirmed = window.confirm(
            `Deploy "${repository}" to GitHub Pages using "${selectedProfile === "auto" ? detectData.detected_profile : selectedProfile}"?`
        );

        if (!confirmed) {
            return;
        }

        const deployData = await postGitHubPagesRequest("/github-pages/deploy", session.token, {
            owner,
            repository,
            deployment_profile: selectedProfile,
        });

        rememberDeployment({
            repository,
            profile: deployData.resolved_profile,
            message: deployData.message,
            workflowTemplate: deployData.workflow_template,
        });

        alert(
            `${deployData.message}\n\nResolved profile: ${deployData.resolved_profile}\nWorkflow: ${deployData.workflow_template}`
        );
    } catch (error) {
        console.error(error);
        alert(error.message || "Deployment failed.");
    }
};

async function postGitHubPagesRequest(path, token, body) {
    const response = await fetch(`${BACKEND_API_URL}${path}`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${token}`,
        },
        body: JSON.stringify(body),
    });

    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
        throw new Error(data.detail || "GitHub Pages request failed.");
    }

    return data;
}
