import pathlib

pages_to_fix = [
    'frontend/templates/dashboard.html',
    'frontend/templates/deployments.html',
    'frontend/templates/reports.html',
    'frontend/templates/profile.html',
]

link_html = """
                    <a class="nav-link" href="./agent.html" data-tooltip="AI Agent">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="11" width="18" height="10" rx="2"></rect><circle cx="12" cy="5" r="2"></circle><path d="M12 7v4"></path><line x1="8" y1="16" x2="8" y2="16"></line><line x1="16" y1="16" x2="16" y2="16"></line></svg>
                        <span>AI Agent</span>
                    </a>"""

for page in pages_to_fix:
    path = pathlib.Path(page)
    if not path.exists(): continue
    content = path.read_text()
    if 'data-tooltip="AI Agent"' in content: continue
    
    # Insert after My Reports
    target = '<span>My Reports</span>\n                    </a>'
    if target in content:
        content = content.replace(target, target + link_html)
        path.write_text(content)
        print(f"Fixed {page}")
    else:
        print(f"Could not find target in {page}")

