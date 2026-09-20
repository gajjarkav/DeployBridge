import pathlib

path = pathlib.Path('frontend/js/app-shell.js')
content = path.read_text()

# Fix newline replacements
content = content.replace(".replace(/\\\\n/g, '<br>')", ".replace(/\\\\n/g, '<br>').replace(/\\n/g, '<br>')")

# Add missing CSS
if '.cd-input-group' not in content:
    css_to_insert = """
        .cd-input-group { margin-bottom: 16px; }
        .cd-input-group label { display: block; font-size: 0.85rem; font-weight: 600; margin-bottom: 6px; color: var(--text-muted, #aaa); }
        .cd-input-group input { width: 100%; padding: 10px 12px; border: 1px solid var(--border-color, #333); border-radius: 6px; background: var(--bg-color, #111); color: var(--text-color, #fff); font-family: monospace; font-size: 0.95rem; }
        .cd-info-list { background: var(--primary-light, #2a2a2a); padding: 12px; border-radius: 6px; margin-bottom: 20px; font-size: 0.9rem; color: var(--text-color, #fff); }
        .cd-info-list div { margin-bottom: 6px; }
        .cd-info-list strong { color: var(--primary-color, #3b82f6); font-weight: 600; }
"""
    content = content.replace("</style>", css_to_insert + "</style>")

path.write_text(content)
