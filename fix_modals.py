import pathlib
import re

def update_app_shell():
    path = pathlib.Path('frontend/js/app-shell.js')
    content = path.read_text()
    if 'window.showCustomConfirm' in content:
        return
    
    js_to_append = """
// Global Modals
window.showCustomAlert = function(title, message) {
    return new Promise((resolve) => {
        ensureCustomDialogDOM();
        const overlay = document.getElementById('db-custom-dialog-overlay');
        document.getElementById('custom-dialog-title').textContent = title;
        document.getElementById('custom-dialog-body').innerHTML = `<p>${(message || '').toString().replace(/\\n/g, '<br>')}</p>`;
        
        const footer = document.getElementById('custom-dialog-footer');
        footer.innerHTML = `<button class="cd-btn cd-btn-primary" id="cd-btn-ok">OK</button>`;
        
        overlay.style.display = 'flex';
        
        document.getElementById('cd-btn-ok').onclick = () => {
            overlay.style.display = 'none';
            resolve();
        };
        
        document.querySelector('.custom-dialog-close').onclick = () => {
            overlay.style.display = 'none';
            resolve();
        };
    });
};

window.showCustomConfirm = function(title, message) {
    return new Promise((resolve) => {
        ensureCustomDialogDOM();
        const overlay = document.getElementById('db-custom-dialog-overlay');
        document.getElementById('custom-dialog-title').textContent = title;
        document.getElementById('custom-dialog-body').innerHTML = `<p>${(message || '').toString().replace(/\\n/g, '<br>')}</p>`;
        
        const footer = document.getElementById('custom-dialog-footer');
        footer.innerHTML = `
            <button class="cd-btn cd-btn-secondary" id="cd-btn-cancel">Cancel</button>
            <button class="cd-btn cd-btn-primary" id="cd-btn-confirm">Confirm</button>
        `;
        
        overlay.style.display = 'flex';
        
        let resolved = false;
        
        document.getElementById('cd-btn-cancel').onclick = () => {
            if (resolved) return; resolved = true;
            overlay.style.display = 'none';
            resolve(false);
        };
        document.getElementById('cd-btn-confirm').onclick = () => {
            if (resolved) return; resolved = true;
            overlay.style.display = 'none';
            resolve(true);
        };
        document.querySelector('.custom-dialog-close').onclick = () => {
            if (resolved) return; resolved = true;
            overlay.style.display = 'none';
            resolve(false);
        };
    });
};

function ensureCustomDialogDOM() {
    if (document.getElementById('db-custom-dialog-overlay')) return;

    const style = document.createElement('style');
    style.innerHTML = `
        .custom-dialog-overlay {
            position: fixed; top: 0; left: 0; width: 100%; height: 100%;
            background: rgba(0, 0, 0, 0.5); backdrop-filter: blur(4px);
            z-index: 10000; display: flex; align-items: center; justify-content: center;
            padding: 20px;
        }
        .custom-dialog-container {
            background: var(--surface-color, #1e1e1e); border-radius: 12px;
            width: 100%; max-width: 500px;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2); border: 1px solid var(--border-color, #333);
            display: flex; flex-direction: column; overflow: hidden;
            animation: slideUp 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }
        @keyframes slideUp { from { transform: translateY(20px); opacity: 0; } to { transform: translateY(0); opacity: 1; } }
        .custom-dialog-header {
            padding: 16px 24px; border-bottom: 1px solid var(--border-color, #333);
            background: var(--primary-light, #2a2a2a); display: flex;
            justify-content: space-between; align-items: center;
        }
        .custom-dialog-header h3 { font-family: 'Ubuntu', sans-serif; font-size: 1.2rem; color: var(--text-color, #fff); margin: 0; }
        .custom-dialog-close { background: transparent; border: none; font-size: 1.5rem; color: var(--text-muted, #aaa); cursor: pointer; line-height: 1; }
        .custom-dialog-body { padding: 24px; font-size: 0.95rem; color: var(--text-color, #fff); line-height: 1.5; max-height: 60vh; overflow-y: auto; }
        .custom-dialog-footer { padding: 16px 24px; border-top: 1px solid var(--border-color, #333); background: var(--surface-color, #1e1e1e); display: flex; justify-content: flex-end; gap: 12px; }
        .cd-btn { padding: 8px 16px; border-radius: 6px; font-family: 'Ubuntu', sans-serif; font-weight: 600; font-size: 0.9rem; cursor: pointer; transition: all 0.2s ease; }
        .cd-btn-secondary { background: transparent; border: 1px solid var(--border-color, #333); color: var(--text-color, #fff); }
        .cd-btn-secondary:hover { background: var(--primary-light, #2a2a2a); }
        .cd-btn-primary { background: var(--primary-color, #3b82f6); border: 1px solid var(--primary-color, #3b82f6); color: var(--bg-color, #fff); }
        .cd-btn-primary:hover { opacity: 0.9; }
    `;
    document.head.appendChild(style);

    const overlay = document.createElement('div');
    overlay.id = 'db-custom-dialog-overlay';
    overlay.className = 'custom-dialog-overlay';
    overlay.style.display = 'none';
    overlay.innerHTML = `
        <div class="custom-dialog-container">
            <div class="custom-dialog-header">
                <h3 id="custom-dialog-title">Dialog</h3>
                <button class="custom-dialog-close">&times;</button>
            </div>
            <div class="custom-dialog-body" id="custom-dialog-body"></div>
            <div class="custom-dialog-footer" id="custom-dialog-footer"></div>
        </div>
    `;
    document.body.appendChild(overlay);
}
"""
    path.write_text(content + "\n" + js_to_append)

update_app_shell()
