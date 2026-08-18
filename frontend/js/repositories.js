// BACKEND_API_URL is defined in repositories.html inline script

// ============================================================================
// REPOSITORY INFO MODAL STATE
// ============================================================================

let currentRepoInfo = null; // Store current repo data for action buttons
let currentRepoOwner = "";
let currentRepoName = "";

// ============================================================================
// INITIALIZATION
// ============================================================================

document.addEventListener("DOMContentLoaded", () => {
    // Setup keyboard listener for modal close (Escape key)
    document.addEventListener('keydown', handleGlobalKeydown);
});

// Expose modal handlers globally on window object
window.openRepoModal = openRepoModal;
window.closeRepoModal = closeRepoModal;
window.retryFetchRepoInfo = retryFetchRepoInfo;
window.toggleReadmeSection = toggleReadmeSection;
window.toggleBranchesSection = toggleBranchesSection;

function handleGlobalKeydown(event) {
    // Close modal on Escape key
    if (event.key === 'Escape') {
        const modal = document.getElementById('repo-info-modal');
        if (modal && modal.style.display !== 'none') {
            closeRepoModal();
        }
    }
}

// ============================================================================
// REPOSITORY TABLE RENDERING
// ============================================================================

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
                        <button class="table-button view" onclick="openRepoModal('${repo.owner.login}','${repo.name}', '${repo.html_url}')">View</button>
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



// ============================================================================
// MODAL MANAGEMENT FUNCTIONS
// ============================================================================

/**
 * Opens the repository information modal and fetches data.
 * @param {string} owner - Repository owner username
 * @param {string} repository - Repository name
 * @param {string} htmlUrl - Repository's GitHub URL (for fallback)
 */
async function openRepoModal(owner, repository, htmlUrl = '') {
    currentRepoOwner = owner;
    currentRepoName = repository;
    
    // Store URL for action buttons
    currentRepoInfo = { owner, repository, html_url: htmlUrl };
    
    // Show modal with loading state
    const modal = document.getElementById('repo-info-modal');
    const loadingEl = document.getElementById('modal-loading');
    const contentEl = document.getElementById('modal-content');
    const errorEl = document.getElementById('modal-error');
    
    // Reset states
    loadingEl.style.display = 'flex';
    contentEl.style.display = 'none';
    errorEl.style.display = 'none';
    
    // Set initial title
    document.getElementById('modal-repo-name').textContent = `${owner}/${repository}`;
    
    // Show modal
    modal.style.display = 'flex';
    document.body.style.overflow = 'hidden'; // Prevent background scrolling
    
    // Fetch repository info
    await fetchAndDisplayRepoInfo(owner, repository);
}

/**
 * Closes the repository information modal.
 */
function closeRepoModal() {
    const modal = document.getElementById('repo-info-modal');
    modal.style.display = 'none';
    document.body.style.overflow = ''; // Restore scrolling
    
    // Reset state
    currentRepoInfo = null;
    currentRepoOwner = '';
    currentRepoName = '';
    
    // Hide readme section when closing
    document.getElementById('readme-section').style.display = 'none';
    document.getElementById('btn-toggle-readme').classList.remove('active');
}

/**
 * Retries fetching repository info (used in error state).
 */
async function retryFetchRepoInfo() {
    if (currentRepoOwner && currentRepoName) {
        await fetchAndDisplayRepoInfo(currentRepoOwner, currentRepoName);
    }
}

// ============================================================================
// DATA FETCHING & RENDERING
// ============================================================================

/**
 * Fetches repository info from backend and populates all sections.
 */
async function fetchAndDisplayRepoInfo(owner, repository) {
    const token = (typeof getAuthSession === 'function' ? getAuthSession()?.token : null) || localStorage.getItem("gh_access_token");
    
    if (!token) {
        showModalError('Authentication required. Please sign in again.');
        return;
    }
    
    try {
        const response = await fetch(`${BACKEND_API_URL}/github/repos/info`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`,
            },
            body: JSON.stringify({
                owner: owner,
                repository: repository,
            }),
        });
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || `Failed to fetch repository info (${response.status})`);
        }
        
        const data = await response.json();
        
        // Store full data for action buttons
        currentRepoInfo = { ...currentRepoInfo, ...data };
        
        // Hide loading, show content
        document.getElementById('modal-loading').style.display = 'none';
        document.getElementById('modal-content').style.display = 'flex';
        
        // Instead of tab switching, scroll to overview to reset position
        const mainContent = document.querySelector('.modal-main-content');
        if (mainContent) {
            mainContent.scrollTop = 0;
        }        
        // Populate all sections
        populateModalHeader(data.basic_info);
        populateOverviewSection(data.basic_info);
        populateDeploymentSection(data.deployment_status);
        populateLanguagesSection(data.languages);
        populateTechStackSection(data.tech_stack);
        populateCommitsSection(data.commits);
        populateContributorsSection(data.contributors);
        populateBranchesSection(data.branches);
        
        // Store README data (not shown by default)
        if (data.readme && data.readme.content) {
            populateReadmeSection(data.readme);
        }
        
        // Update footer info
        updateModalFooter(data);
        
        // Setup action button URLs
        setupActionButtons(data.basic_info);
        
    } catch (error) {
        console.error('Error fetching repo info:', error);
        showModalError(error.message || 'Failed to load repository information.');
    }
}

/**
 * Shows error state in modal.
 */
function showModalError(message) {
    document.getElementById('modal-loading').style.display = 'none';
    document.getElementById('modal-content').style.display = 'none';
    document.getElementById('modal-error').style.display = 'flex';
    document.getElementById('modal-error-message').textContent = message;
}

// ============================================================================
// SECTION POPULATION FUNCTIONS
// ============================================================================

/**
 * Populates modal header with basic info.
 */
function populateModalHeader(basicInfo) {
    if (!basicInfo) return;
    
    // Title
    document.getElementById('modal-repo-name').textContent = 
        basicInfo.full_name || basicInfo.name || 'Repository';
    
    // Visibility badge
    const badge = document.getElementById('modal-visibility-badge');
    badge.textContent = basicInfo.private ? 'Private' : 'Public';
    badge.className = `visibility-badge ${basicInfo.private ? 'private' : 'public'}`;
    
    // Meta text (stars, forks, updated)
    const metaParts = [];
    if (basicInfo.stars_count > 0) metaParts.push(`<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="width:12px;height:12px;margin-right:2px;"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon></svg> ${basicInfo.stars_count}`);
    if (basicInfo.forks_count > 0) metaParts.push(`<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="width:12px;height:12px;margin-right:2px;"><line x1="6" y1="3" x2="6" y2="15"></line><circle cx="18" cy="6" r="3"></circle><circle cx="6" cy="18" r="3"></circle><path d="M18 9a9 9 0 0 1-9 9"></path></svg> ${basicInfo.forks_count}`);
    if (basicInfo.updated_at) {
        const updatedDate = new Date(basicInfo.updated_at).toLocaleDateString('en-US', {
            month: 'short',
            day: 'numeric',
            year: 'numeric',
        });
        metaParts.push(`Updated ${updatedDate}`);
    }
    
    document.getElementById('modal-repo-meta').textContent = metaParts.join(' • ');
}

/**
 * Populates Overview section.
 */
function populateOverviewSection(info) {
    const container = document.getElementById('section-overview');
    
    if (!info) {
        container.innerHTML = '<p style="color: var(--text-muted);">No overview data available.</p>';
        return;
    }
    
    let html = '';
    
    // Description
    if (info.description) {
        html += `<div class="overview-item">
            <span class="overview-label">Description</span>
            <span class="overview-value">${escapeHtml(info.description)}</span>
        </div>`;
    }
    
    // Owner
    if (info.owner_login) {
        html += `<div class="overview-item">
            <span class="overview-label">Owner</span>
            <span class="overview-value">@${escapeHtml(info.owner_login)}</span>
        </div>`;
    }
    
    // License
    html += `<div class="overview-item">
        <span class="overview-label">License</span>
        <span class="overview-value">${info.license_name || 'None'}</span>
    </div>`;
    
    // Default Branch
    html += `<div class="overview-item">
        <span class="overview-label">Default Branch</span>
        <span class="overview-value" style="font-family: monospace;">${escapeHtml(info.default_branch)}</span>
    </div>`;
    
    // Size
    const sizeFormatted = formatFileSize(info.size);
    html += `<div class="overview-item">
        <span class="overview-label">Size</span>
        <span class="overview-value">${sizeFormatted}</span>
    </div>`;
    
    // Created date
    if (info.created_at) {
        const createdDate = new Date(info.created_at).toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'long',
            day: 'numeric',
        });
        html += `<div class="overview-item">
            <span class="overview-label">Created</span>
            <span class="overview-value">${createdDate}</span>
        </div>`;
    }
    
    // Last push
    if (info.pushed_at) {
        const pushedDate = new Date(info.pushed_at).toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
        });
        html += `<div class="overview-item">
            <span class="overview-label">Last Push</span>
            <span class="overview-value">${pushedDate}</span>
        </div>`;
    }
    
    // Stats row (stars, forks, size, license)
    html += `<div style="display: flex; border: 1px solid var(--border-color); border-radius: 8px; overflow: hidden; margin-top: 16px; text-align: center;">
        <div style="flex: 1; padding: 16px; border-right: 1px solid var(--border-color);">
            <div style="font-size: 1.5rem; font-weight: 700; color: var(--text-color);">${Number(info.stars_count || 0).toLocaleString()}</div>
            <div style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase; margin-top: 4px; letter-spacing: 0.5px;">Stars</div>
        </div>
        <div style="flex: 1; padding: 16px; border-right: 1px solid var(--border-color);">
            <div style="font-size: 1.5rem; font-weight: 700; color: var(--text-color);">${Number(info.forks_count || 0).toLocaleString()}</div>
            <div style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase; margin-top: 4px; letter-spacing: 0.5px;">Forks</div>
        </div>
        <div style="flex: 1; padding: 16px; border-right: 1px solid var(--border-color);">
            <div style="font-size: 1.5rem; font-weight: 700; color: var(--text-color);">${sizeFormatted}</div>
            <div style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase; margin-top: 4px; letter-spacing: 0.5px;">Size</div>
        </div>
        <div style="flex: 1; padding: 16px;">
            <div style="font-size: 1.5rem; font-weight: 700; color: var(--text-color);">${info.license_name || 'None'}</div>
            <div style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase; margin-top: 4px; letter-spacing: 0.5px;">License</div>
        </div>
    </div>`;
    
    // Topics/Tags (Breadcrumbs)
    if (info.topics && info.topics.length > 0) {
        html += `<div style="margin-top: 16px;">
            <div style="display: inline-flex; flex-wrap: wrap; border: 1px solid var(--border-color); border-radius: 6px; overflow: hidden; background: var(--primary-light);">
            ${info.topics.map((topic, i) => `<span style="padding: 6px 12px; font-size: 0.85rem; font-family: monospace; color: var(--text-color); border-right: ${i < info.topics.length - 1 ? '1px solid var(--border-color)' : 'none'};">${escapeHtml(topic)}</span>`).join('')}
            </div>
        </div>`;
    }
    
    // Status flags
    const statusFlags = [];
    if (info.is_archived) statusFlags.push('<span style="color: var(--status-danger-text);">Archived</span>');
    if (info.has_wiki) statusFlags.push('Wiki');
    if (info.has_issues) statusFlags.push('Issues');
    if (info.has_projects) statusFlags.push('Projects');
    
    if (statusFlags.length > 0) {
        html += `<div style="margin-top: 12px; display: flex; gap: 8px; flex-wrap: wrap;">
            ${statusFlags.join('')}
        </div>`;
    }
    
    container.innerHTML = html;
}

/**
 * Populates Deployment Status section.
 */
function populateDeploymentSection(deployment) {
    const container = document.getElementById('section-deployment');
    
    if (!deployment) {
        container.innerHTML = '<p style="color: var(--text-muted);">No deployment data available.</p>';
        return;
    }
    
    let html = '';
    
    // GitHub Pages Status
    if (deployment.enabled) {
        const buildStatus = deployment.latest_build?.status;
        let statusClass = 'neutral';
        let statusText = 'Unknown';
        
        if (buildStatus === 'success' || deployment.status === 'built') {
            statusClass = 'success';
            statusText = 'Active';
        } else if (buildStatus === 'failed' || buildStatus === 'error') {
            statusClass = 'error';
            statusText = 'Build Failed';
        } else if (buildStatus === 'building' || deployment.status === 'building') {
            statusClass = 'warning';
            statusText = 'Building...';
        } else {
            statusText = deployment.status || 'Configured';
        }
        
        html += `<div class="deployment-status-row">
            <span class="status-indicator ${statusClass}"></span>
            <div>
                <strong>GitHub Pages</strong><br>
                <span style="font-size: 0.85rem; color: var(--text-muted);">${statusText}</span>
            </div>
        </div>`;
        
        // Pages URL
        if (deployment.url) {
            html += `<div style="margin-bottom: 12px;">
                <strong style="font-size: 0.85rem; color: var(--text-muted);">Live URL:</strong><br>
                <a href="${escapeHtml(deployment.url)}" target="_blank" class="deployment-url">${escapeHtml(deployment.url)}</a>
            </div>`;
        }
        
        // Custom Domain
        if (deployment.cname) {
            html += `<div style="margin-bottom: 12px;">
                <strong style="font-size: 0.85rem; color: var(--text-muted);">Custom Domain:</strong><br>
                <span style="font-family: monospace;">${escapeHtml(deployment.cname)}</span>
                ${deployment.https_enabled ? '<span style="color: var(--status-success-text); margin-left: 8px;"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="width:12px;height:12px;display:inline-block;"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect><path d="M7 11V7a5 5 0 0 1 10 0v4"></path></svg> HTTPS</span>' : ''}
            </div>`;
        }
        
        // Source Branch
        if (deployment.source_branch) {
            html += `<div style="margin-bottom: 12px; font-size: 0.85rem; color: var(--text-muted);">
                Source branch: <code style="background: var(--primary-light); padding: 2px 6px; border-radius: 4px;">${escapeHtml(deployment.source_branch)}</code>
            </div>`;
        }
        
        // Latest Build Info
        if (deployment.latest_build) {
            const build = deployment.latest_build;
            html += `<div style="padding: 10px; background: var(--primary-light); border-radius: 6px; font-size: 0.85rem;">
                <strong>Latest Build</strong><br>
                Status: <span style="color: ${build.status === 'success' ? 'var(--status-success-text)' : 'var(--status-danger-text)'}; font-weight: 600;">${build.status || 'N/A'}</span>
                ${build.duration ? `<br>Duration: ${build.duration} min` : ''}
                ${build.updated_at ? `<br>Updated: ${new Date(build.updated_at).toLocaleString()}` : ''}
            </div>`;
        }
    } else {
        html += `<div class="deployment-status-row">
            <span class="status-indicator neutral"></span>
            <div>
                <strong>GitHub Pages</strong><br>
                <span style="font-size: 0.85rem; color: var(--text-muted);">Not Configured</span>
            </div>
        </div>
        <p style="font-size: 0.85rem; color: var(--text-muted); margin-top: 12px;">
            Use the Deploy button to set up GitHub Pages for this repository.
        </p>`;
    }
    
    // Other Platform Detection
    const otherPlatforms = deployment.other_platforms || {};
    const detectedPlatforms = Object.entries(otherPlatforms).filter(([_, detected]) => detected);
    
    if (detectedPlatforms.length > 0) {
        html += `<div style="margin-top: 16px;">
            <strong style="font-size: 0.85rem; color: var(--text-muted); display: block; margin-bottom: 8px;">Other Platforms Detected:</strong>
            <div class="platform-detection">
                ${detectedPlatforms.map(([platform, _]) => `
                    <span class="platform-badge detected">${getPlatformIcon(platform)} ${platform.charAt(0).toUpperCase() + platform.slice(1)}</span>
                `).join('')}
            </div>
        </div>`;
    }
    
    container.innerHTML = html;
}

/**
 * Populates Languages section with progress bars.
 */
function populateLanguagesSection(languages) {
    const container = document.getElementById('section-languages');
    
    if (!languages || !languages.languages || languages.languages.length === 0) {
        container.innerHTML = '<p style="color: var(--text-muted);">No language data available.</p>';
        return;
    }
    
    // Language colors (GitHub's approximate colors)
    const languageColors = {
        'JavaScript': '#f1e05a',
        'TypeScript': '#3178c6',
        'Python': '#3572A5',
        'Java': '#b07219',
        'Ruby': '#701516',
        'Go': '#00ADD8',
        'Rust': '#dea584',
        'PHP': '#4F5D95',
        'C#': '#239120',
        'C++': '#f34b7d',
        'C': '#555555',
        'Swift': '#F05138',
        'Kotlin': '#A97BFF',
        'Dart': '#00B4AB',
        'HTML': '#e34c26',
        'CSS': '#563d7c',
        'SCSS': '#c6538c',
        'Shell': '#89e051',
        'Vue': '#41b883',
        'Svelte': '#ff3e00',
        'Jupyter Notebook': '#DA5B0B',
        'Markdown': '#083fa1',
        'YAML': '#cb171e',
        'Dockerfile': '#384d54',
        'Lua': '#000080',
        'Rust': '#dea584',
    };
    
    let html = '';
    
    languages.languages.forEach(lang => {
        const color = languageColors[lang.name] || getLanguageColorFromName(lang.name);
        
        html += `
            <div class="language-bar-container">
                <div class="language-bar-header">
                    <span class="language-name">${escapeHtml(lang.name)}</span>
                    <span class="language-percentage">${lang.percentage}%</span>
                </div>
                <div class="language-bar">
                    <div class="language-fill" style="width: ${lang.percentage}%; background-color: ${color};"></div>
                </div>
            </div>
        `;
    });
    
    // Total info
    if (languages.total_bytes > 0) {
        const totalKB = Math.round(languages.total_bytes / 1024);
        html += `<div style="margin-top: 12px; padding: 8px; background: var(--primary-light); border-radius: 6px; font-size: 0.85rem; color: var(--text-muted);">
            Total: ${languages.languages.length} language${languages.languages.length !== 1 ? 's' : ''} • ~${totalKB.toLocaleString()} KB of code
        </div>`;
    }
    
    container.innerHTML = html;
}

/**
 * Populates Tech Stack section.
 */
function populateTechStackSection(techStack) {
    const container = document.getElementById('section-techstack');
    
    if (!techStack) {
        container.innerHTML = '<p style="color: var(--text-muted);">No tech stack data detected.</p>';
        return;
    }
    
    let html = '<div class="tech-stack-grid">';
    
    // Framework
    html += createTechItem('Framework', techStack.framework);
    
    // Build Tool
    html += createTechItem('Build Tool', techStack.build_tool);
    
    // Runtime
    html += createTechItem('Runtime', techStack.runtime);
    
    // Package Manager
    html += createTechItem('Package Manager', techStack.package_manager);
    
    // Styling
    html += createTechItem('Styling', techStack.styling);
    
    html += '</div>'; // End grid
    
    // Testing tools
    if (techStack.testing && techStack.testing.length > 0) {
        html += `<div style="margin-top: 12px;">
            <strong style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px;">Testing</strong>
            <div style="display: flex; flex-wrap: wrap; gap: 6px; margin-top: 6px;">
                ${techStack.testing.map(tool => `<span class="stat-chip" style="font-size: 0.8rem;">${escapeHtml(tool)}</span>`).join('')}
            </div>
        </div>`;
    }
    
    // Confidence badge
    if (techStack.confidence) {
        const confidenceClass = techStack.confidence === 'high' ? 'confidence-high' :
                               techStack.confidence === 'medium' ? 'confidence-medium' : 'confidence-low';
        html += `<div style="margin-top: 12px;">
            <span class="confidence-badge ${confidenceClass}">
                Detection Confidence: ${techStack.confidence.toUpperCase()}
            </span>
        </div>`;
    }
    
    // Deployment Profile (from your detection)
    if (techStack.deployment_profile) {
        html += `<div style="margin-top: 8px; padding: 10px; background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); color: white; border-radius: 8px; text-align: center;">
            <strong style="font-size: 0.85rem;">Recommended Deploy Profile</strong><br>
            <span style="font-size: 1.1rem; font-weight: 700; font-family: monospace;">${escapeHtml(techStack.deployment_profile)}</span>
        </div>`;
    }
    
    container.innerHTML = html;
}

/**
 * Helper to create tech stack item HTML.
 */
function createTechItem(label, value) {
    return `
        <div class="tech-item">
            <span class="tech-label">${label}</span>
            <span class="tech-value">${value || '<span style="color: var(--text-muted);">Not detected</span>'}</span>
        </div>
    `;
}

/**
 * Populates Recent Commits section.
 */
function populateCommitsSection(commits) {
    const container = document.getElementById('section-commits');
    
    if (!commits || !commits.commits || commits.commits.length === 0) {
        container.innerHTML = '<p style="color: var(--text-muted);">No commit history available.</p>';
        return;
    }
    
    let html = '';
    
    commits.commits.forEach(commit => {
        const authorAvatar = commit.author?.avatar_url || '';
        const authorName = commit.author?.login || 'Unknown';
        const commitDate = commit.date ? formatDateRelative(commit.date) : '';
        
        html += `
            <div class="commit-item">
                <div class="commit-header">
                    <span class="commit-sha">${escapeHtml(commit.short_sha)}</span>
                    ${authorAvatar ? `<img src="${escapeHtml(authorAvatar)}" alt="" class="commit-author-avatar">` : ''}
                    <span class="commit-author-name">${escapeHtml(authorName)}</span>
                </div>
                <div class="commit-message">${escapeHtml(commit.message)}</div>
                ${commitDate ? `<div class="commit-date">${commitDate}</div>` : ''}
            </div>
        `;
    });
    
    container.innerHTML = html;
}

/**
 * Populates Contributors section.
 */
function populateContributorsSection(contributors) {
    const container = document.getElementById('section-contributors');
    
    if (!contributors || !contributors.contributors || contributors.contributors.length === 0) {
        container.innerHTML = '<p style="color: var(--text-muted);">No contributor data available.</p>';
        return;
    }
    
    let html = '';
    
    contributors.contributors.forEach(contributor => {
        const avatarUrl = contributor.avatar_url || `https://github.com/${contributor.login}.png?size=36`;
        const profileUrl = `https://github.com/${contributor.login}`;
        
        html += `<div class="contributor-item">
                <img src="${escapeHtml(avatarUrl)}" alt="${escapeHtml(contributor.login)}" class="contributor-avatar">
                <div class="contributor-info">
                    <a href="${escapeHtml(profileUrl)}" target="_blank" class="contributor-name">${escapeHtml(contributor.login)}</a>
                    <div class="contributor-commits">${contributor.contributions} commit${contributor.contributions !== 1 ? 's' : ''}</div>
                </div>
                <span class="contributor-percentage">${contributor.percentage}%</span>
            </div>`;
    });
    
    // Total count
    if (contributors.total_count > 0) {
        html += `<div style="margin-top: 12px; text-align: center; font-size: 0.85rem; color: var(--text-muted);">
            ${contributors.total_count} contributor${contributors.total_count !== 1 ? 's' : ''} total
        </div>`;
    }
    
    container.innerHTML = html;
}

/**
 * Populates Branches section.
 */
function populateBranchesSection(branches) {
    const container = document.getElementById('section-branches');
    
    if (!branches || !branches.branches || branches.branches.length === 0) {
        container.innerHTML = '<p style="color: var(--text-muted);">No branches data available.</p>';
        return;
    }
    
    let html = '';
    
    branches.branches.forEach(branch => {
        const isDefault = branch.is_default || branch.name === branches.default_branch;
        html += `
            <div class="branch-item" style="padding: 12px; border-bottom: 1px solid var(--border-color); display: flex; align-items: center; justify-content: space-between;">
                <div style="display: flex; align-items: center; gap: 8px;">
                    <span class="branch-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="width:16px;height:16px;"><line x1="6" y1="3" x2="6" y2="15"></line><circle cx="18" cy="6" r="3"></circle><circle cx="6" cy="18" r="3"></circle><path d="M18 9a9 9 0 0 1-9 9"></path></svg></span>
                    <strong style="font-family: monospace;">${escapeHtml(branch.name)}</strong>
                    ${isDefault ? '<span class="visibility-badge public" style="font-size: 0.65rem;">Default</span>' : ''}
                </div>
                ${branch.protected ? '<span style="font-size: 0.75rem; color: var(--text-muted);"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="width:12px;height:12px;"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect><path d="M7 11V7a5 5 0 0 1 10 0v4"></path></svg></span>' : ''}
            </div>
        `;
    });
    
    container.innerHTML = html;
}

/**
 * Populates README section (stores data but doesn't show it).
 */
function populateReadmeSection(readme) {
    const container = document.getElementById('section-readme');
    const filenameEl = document.getElementById('readme-filename');
    
    if (!readme || !readme.content) {
        container.innerHTML = '<p style="color: var(--text-muted);">No README found in this repository.</p>';
        filenameEl.textContent = 'README';
        return;
    }
    
    // Set filename
    filenameEl.textContent = readme.filename || 'README.md';
    
    // Simple markdown to HTML conversion (basic)
    let htmlContent = simpleMarkdownToHtml(readme.content);
    
    container.innerHTML = htmlContent;
}

/**
 * Updates modal footer with fetch metadata.
 */
function updateModalFooter(data) {
    const infoEl = document.getElementById('modal-fetch-info');
    const errorsEl = document.getElementById('modal-errors-count');
    
    // Fetch timestamp
    if (data.fetched_at) {
        const fetchedDate = new Date(data.fetched_at).toLocaleTimeString();
        infoEl.textContent = `Fetched at ${fetchedDate} • ${data.api_calls_made || 0} API calls`;
    }
    
    // Errors count
    if (data.errors && data.errors.length > 0) {
        errorsEl.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="#eab308" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="width:14px;height:14px;vertical-align:middle;margin-right:4px;"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg> ${data.errors.length} section(s) had errors`;
        errorsEl.style.display = 'inline';
    } else {
        errorsEl.style.display = 'none';
    }
}

/**
 * Sets up action button click handlers with correct URLs.
 */
function setupActionButtons(basicInfo) {
    const githubBtn = document.getElementById('btn-view-github');
    const actionsBtn = document.getElementById('btn-actions');
    const deployBtn = document.getElementById('btn-deploy-pages');
    
    const repoUrl = basicInfo?.html_url || currentRepoInfo?.html_url || '';
    const owner = currentRepoOwner;
    const repo = currentRepoName;
    
    // View on GitHub button
    githubBtn.onclick = () => {
        if (repoUrl) window.open(repoUrl, '_blank');
    };
    
    // GitHub Actions button
    actionsBtn.onclick = () => {
        if (owner && repo) {
            window.open(`https://github.com/${owner}/${repo}/actions`, '_blank');
        }
    };
    
    // Deploy button - triggers existing deploy function
    deployBtn.onclick = () => {
        if (owner && repo) {
            // Close modal first for better UX during deploy flow
            closeRepoModal();
            // Call existing deploy function
            setTimeout(() => {
                window.deployGitHubPages(owner, repo);
            }, 300);
        }
    };
}

// ============================================================================
// TOGGLE FUNCTIONS (MODAL TABS)
// ============================================================================

/**
 * Scrolls the main modal content to a specific section.
 */
function scrollToSection(sectionId) {
    const pane = document.getElementById(sectionId);
    if (pane) {
        pane.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
    
    // Update active state in sidebar
    const tabBtns = document.querySelectorAll('.modal-sidebar .tab-btn');
    tabBtns.forEach(btn => {
        if (btn.getAttribute('onclick') && btn.getAttribute('onclick').includes(sectionId)) {
            btn.classList.add('active');
        } else {
            btn.classList.remove('active');
        }
    });
}
window.scrollToSection = scrollToSection;

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

/**
 * Escapes HTML special characters to prevent XSS.
 */
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Formats file size from KB to human readable string.
 */
function formatFileSize(kb) {
    if (!kb || kb === 0) return '0 B';
    
    const units = ['B', 'KB', 'MB', 'GB'];
    let size = kb * 1024; // Convert KB to bytes first
    let unitIndex = 0;
    
    while (size >= 1024 && unitIndex < units.length - 1) {
        size /= 1024;
        unitIndex++;
    }
    
    return `${size.toFixed(1)} ${units[unitIndex]}`;
}

/**
 * Formats date as relative time (e.g., "2 hours ago").
 */
function formatDateRelative(dateStr) {
    if (!dateStr) return '';
    
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now - date;
    const diffSecs = Math.floor(diffMs / 1000);
    const diffMins = Math.floor(diffSecs / 60);
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);
    const diffWeeks = Math.floor(diffDays / 7);
    const diffMonths = Math.floor(diffDays / 30);
    const diffYears = Math.floor(diffDays / 365);
    
    if (diffSecs < 60) return 'just now';
    if (diffMins < 60) return `${diffMins} minute${diffMins !== 1 ? 's' : ''} ago`;
    if (diffHours < 24) return `${diffHours} hour${diffHours !== 1 ? 's' : ''} ago`;
    if (diffDays < 7) return `${diffDays} day${diffDays !== 1 ? 's' : ''} ago`;
    if (diffWeeks < 4) return `${diffWeeks} week${diffWeeks !== 1 ? 's' : ''} ago`;
    if (diffMonths < 12) return `${diffMonths} month${diffMonths !== 1 ? 's' : ''} ago`;
    return `${diffYears} year${diffYears !== 1 ? 's' : ''} ago`;
}

/**
 * Gets platform icon emoji.
 */
function getPlatformIcon(platform) {
    const icons = {
        'vercel': '<svg viewBox="0 0 24 24" fill="currentColor" stroke="none" style="width:14px;height:14px;vertical-align:middle;margin-right:4px;"><path d="M24 22.525H0l12-21.05 12 21.05z"/></svg>',
        'netlify': '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="width:14px;height:14px;vertical-align:middle;margin-right:4px;"><circle cx="12" cy="12" r="10"></circle><line x1="2" y1="12" x2="22" y2="12"></line><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"></path></svg>',
        'railway': '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="width:14px;height:14px;vertical-align:middle;margin-right:4px;"><rect x="4" y="3" width="16" height="18" rx="2" ry="2"></rect><line x1="4" y1="8" x2="20" y2="8"></line><line x1="4" y1="16" x2="20" y2="16"></line><line x1="9" y1="3" x2="9" y2="21"></line></svg>',
        'render': '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="width:14px;height:14px;vertical-align:middle;margin-right:4px;"><path d="M17.5 19h-11a5.5 5.5 0 0 1-1.3-10.8 7 7 0 0 1 13.6 0A5.5 5.5 0 0 1 17.5 19z"></path></svg>',
        'heroku': '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="width:14px;height:14px;vertical-align:middle;margin-right:4px;"><path d="M4 14.5V11a7 7 0 0 1 14 0v3.5"></path><path d="M4 14.5A2.5 2.5 0 0 0 6.5 17h11a2.5 2.5 0 0 0 2.5-2.5"></path><path d="M12 17v4"></path></svg>',
        'docker': '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="width:14px;height:14px;vertical-align:middle;margin-right:4px;"><rect x="2" y="7" width="20" height="14" rx="2" ry="2"></rect><path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"></path></svg>',
    };
    
    return icons[platform] || '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="width:14px;height:14px;vertical-align:middle;margin-right:4px;"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect></svg>';
}

/**
 * Generates a color based on language name hash (for unknown languages).
 */
function getLanguageColorFromName(name) {
    if (!name) return '#888888';
    
    // Simple hash to generate consistent colors
    let hash = 0;
    for (let i = 0; i < name.length; i++) {
        hash = name.charCodeAt(i) + ((hash << 5) - hash);
    }
    
    const hue = Math.abs(hash % 360);
    return `hsl(${hue}, 65%, 50%)`;
}

/**
 * Very simple Markdown to HTML converter (handles basics only).
 * For production, consider using a proper library like marked.js.
 */
function simpleMarkdownToHtml(markdown) {
    if (!markdown) return '';
    
    let html = escapeHtml(markdown);
    
    // Headers
    html = html.replace(/^### (.+)$/gm, '<h3>$1</h3>');
    html = html.replace(/^## (.+)$/gm, '<h2>$1</h2>');
    html = html.replace(/^# (.+)$/gm, '<h1>$1</h1>');
    
    // Bold and Italic
    html = html.replace(/\*\*\*(.+?)\*\*\*/g, '<strong><em>$1</em></strong>');
    html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    html = html.replace(/\*(.+?)\*/g, '<em>$1</em>');
    
    // Code blocks (inline and block)
    html = html.replace(/`([^`]+)`/g, '<code>$1</code>');
    html = html.replace(/```[\s\S]*?```/g, (match) => {
        const code = match.replace(/```\w*\n?/, '').replace(/\n?```$/, '');
        return `<pre><code>${code}</code></pre>`;
    });
    
    // Links
    html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank">$1</a>');
    
    // Lists (basic)
    html = html.replace(/^[\-\*] (.+)$/gm, '<li>$1</li>');
    html = html.replace(/(<li>.*<\/li>\n?)+/g, '<ul>$&</ul>');
    
    // Numbered lists
    html = html.replace(/^\d+\. (.+)$/gm, '<li>$1</li>');
    
    // Blockquotes
    html = html.replace(/^&gt; (.+)$/gm, '<blockquote>$1</blockquote>');
    
    // Horizontal rules
    html = html.replace(/^---$/gm, '<hr>');
    
    // Paragraphs (double newline)
    html = html.replace(/\n\n/g, '</p><p>');
    html = `<p>${html}</p>`;
    
    // Clean up empty paragraphs
    html = html.replace(/<p><\/p>/g, '');
    html = html.replace(/<p>(<h[1-6]>)/g, '$1');
    html = html.replace(/(<\/h[1-6]>)<\/p>/g, '$1');
    html = html.replace(/<p>(<ul>|<ol>|<blockquote>|<pre>|<hr>)/g, '$1');
    html = html.replace(/(<\/ul>|<\/ol>|<\/blockquote>|<\/pre>)<\/p>/g, '$1');
    
    // Line breaks within paragraphs
    html = html.replace(/\n/g, '<br>');
    
    return html;
}


// Duplicate functions removed. They are defined in repositories.html inline script.

