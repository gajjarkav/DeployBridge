import pathlib
import re

# 1. Update deployments.js
path = pathlib.Path('frontend/js/deployments.js')
content = path.read_text()
content = content.replace(
    'if (!confirm("Trigger a new deploy on the platform?")) return;',
    'if (!(await window.showCustomConfirm("Deploy", "Trigger a new deploy on the platform?"))) return;'
)
content = content.replace(
    'if (!confirm("Remove this deployment from history?\\n(The actual Render service / Pages site keeps running — only the history entry is removed.)")) return;',
    'if (!(await window.showCustomConfirm("Remove Deployment", "Remove this deployment from history?\\n(The actual Render service / Pages site keeps running — only the history entry is removed.)"))) return;'
)
content = content.replace(
    'if (!confirm("Clear ALL failed/pending deployments from history?\\n(Live ones will be kept.)")) return;',
    'if (!(await window.showCustomConfirm("Clear History", "Clear ALL failed/pending deployments from history?\\n(Live ones will be kept.)"))) return;'
)
# Ensure the functions are async
content = content.replace('function retryDeploy(id)', 'async function retryDeploy(id)')
content = content.replace('function deleteDeploy(id)', 'async function deleteDeploy(id)')
content = content.replace('function clearFailedDeploys()', 'async function clearFailedDeploys()')
content = content.replace('alert(', 'window.showCustomAlert("Deployment", ')
path.write_text(content)

# 2. Update reports.js
path = pathlib.Path('frontend/js/reports.js')
content = path.read_text()
content = content.replace(
    'if (!confirm("Are you sure you want to delete this report?")) return;',
    'if (!(await window.showCustomConfirm("Delete Report", "Are you sure you want to delete this report?"))) return;'
)
content = content.replace(
    'if (!confirm("Are you sure you want to resend this report via email?")) return;',
    'if (!(await window.showCustomConfirm("Resend Report", "Are you sure you want to resend this report via email?"))) return;'
)
content = content.replace('function deleteReport(id)', 'async function deleteReport(id)')
content = content.replace('function resendReport(id)', 'async function resendReport(id)')
content = content.replace('alert(', 'window.showCustomAlert("Report", ')
path.write_text(content)

# 3. Update settings.html
path = pathlib.Path('frontend/templates/settings.html')
content = path.read_text()
content = content.replace(
    'if (!confirm("Disconnect Render integration? Your existing Render services keep running, but DeployBridge will no longer be able to manage them.")) return;',
    'if (!(await window.showCustomConfirm("Disconnect Render", "Disconnect Render integration? Your existing Render services keep running, but DeployBridge will no longer be able to manage them."))) return;'
)
content = content.replace('alert(', 'window.showCustomAlert("Settings", ')
path.write_text(content)

# 4. Cleanup repositories.html
path = pathlib.Path('frontend/templates/repositories.html')
content = path.read_text()

# Remove the showCustomConfirm and showCustomAlert definitions block.
# We will just replace them with empty strings. They are between `function showCustomConfirm` and the end of `showCustomAlert`.
def remove_between(text, start_str, end_str):
    start = text.find(start_str)
    if start == -1: return text
    end = text.find(end_str, start)
    if end == -1: return text
    end += len(end_str)
    return text[:start] + text[end:]

content = remove_between(content, 'function showCustomConfirm(title, message) {', 'window.showCustomAlert = showCustomAlert;')

# Remove the db-custom-dialog-overlay HTML block
content = remove_between(content, '<!-- Custom Dialog Overlay -->', '</div>\n    </div>')

# Remove the CSS block for Custom Dialog
content = remove_between(content, '/* ====== CUSTOM DIALOG ====== */', '        .cd-info-list strong {\n            color: var(--text-color);\n        }')

path.write_text(content)

