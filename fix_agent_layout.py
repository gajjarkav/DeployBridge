import pathlib

agent_path = pathlib.Path('frontend/templates/agent.html')
dash_path = pathlib.Path('frontend/templates/dashboard.html')

agent_content = agent_path.read_text()
dash_content = dash_path.read_text()

# Get standard aside
start_idx = dash_content.find('<aside class="sidebar">')
if start_idx == -1:
    print("Could not find sidebar in dashboard")
    exit(1)
end_idx = dash_content.find('</aside>', start_idx) + len('</aside>')
standard_aside = dash_content[start_idx:end_idx]

# Update active link
standard_aside = standard_aside.replace('data-active="true" ', '')
standard_aside = standard_aside.replace(
    'href="./agent.html" data-tooltip="AI Agent">',
    'data-active="true" href="./agent.html" data-tooltip="AI Agent">'
)

# Get standard top nav
nav_start = dash_content.find('<div class="top-nav">')
nav_end = dash_content.find('</div>', dash_content.find('</svg>', dash_content.find('<label for="themeToggle"'))) + len('</div>')
if nav_end < nav_start or nav_end - nav_start > 5000:
    nav_end = dash_content.find('</div>', dash_content.find('</label>')) + len('</div>')
standard_top_nav = dash_content[nav_start:nav_end].strip()

# Replace in agent.html
# 1. Replace aside
old_aside_start = agent_content.find('<aside class="sidebar">')
old_aside_end = agent_content.find('</aside>', old_aside_start) + len('</aside>')
agent_content = agent_content[:old_aside_start] + standard_aside + agent_content[old_aside_end:]

# 2. Add style.css to head
if 'style.css' not in agent_content:
    head_end = agent_content.find('</head>')
    agent_content = agent_content[:head_end] + '    <link rel="stylesheet" href="../css/style.css">\n' + agent_content[head_end:]

# 3. Rename main class and insert top nav
# We want the agent to not scroll the whole page, so we add overflow: hidden and flex column.
old_main = '<main class="main">'
agent_content = agent_content.replace(old_main, f'<main class="main-shell" style="background: transparent; overflow: hidden; display: flex; flex-direction: column;">\n{standard_top_nav}')

agent_path.write_text(agent_content)
print("Updated agent.html successfully.")
