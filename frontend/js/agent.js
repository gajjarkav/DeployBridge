// ------------------------------------------------------------------------------
// WHAT THIS IS
//   The chat UI for the Deployment Agent. Talks to:
//     POST   /v1/agent/sessions                     create a session
//     GET    /v1/agent/sessions                     list
//     GET    /v1/agent/sessions/{id}                detail (with messages)
//     POST   /v1/agent/sessions/{id}/messages       send a user message + run loop
//     POST   /v1/agent/messages/{id}/approve        approve a gated plan
//
// THE CONFIRM-GATE (the most important UX decision)
//   When the agent wants a SIDE-EFFECT tool (deploy_*, create_pr, add_domain),
//   the loop PAUSES. The backend persists a role=assistant_plan message
//   whose `plan` field is a list of tool calls. We render that as an
//   [Approve] [Cancel] card inline in the chat. On Approve we POST to
//   /messages/{id}/approve; the loop resumes and we get the next message.
//
// SECRETS RULE
//   Env-var VALUES never enter the LLM conversation. When the plan is a
//   deploy_render with env_var_keys, we render a tiny form for the user
//   to fill in. The values are sent ONLY to the /approve endpoint, which
//   merges them at execution time. The LLM only ever saw the keys.
// ------------------------------------------------------------------------------

const BACKEND_API_URL = "http://127.0.0.1:8000/v1";

// State
let sessionToken = null;
let currentSessionId = null;
let isAgentRunning = false;

// DOM refs
const chatMessages = document.getElementById("chat-messages");
const chatEmpty = document.getElementById("chat-empty");
const chatInput = document.getElementById("chat-input");
const chatSend = document.getElementById("chat-send");
const newChatBtn = document.getElementById("new-chat-btn");

window.onload = async () => {
    sessionToken = localStorage.getItem("db_session_token");
    if (!sessionToken) {
        window.location.href = "./auth.html";
        return;
    }

    // If the user came from [🤖 Ask Agent] on a failed deployment card,
    // there's a pre-fill question in sessionStorage.
    const prefillQuestion = sessionStorage.getItem("agent_prefill_question");
    const prefillDeploymentId = sessionStorage.getItem("agent_prefill_deployment_id");
    if (prefillQuestion) {
        sessionStorage.removeItem("agent_prefill_question");
        sessionStorage.removeItem("agent_prefill_deployment_id");
        await startNewSession(prefillQuestion);
        return;
    }

    // Try to resume the most recent session; otherwise start fresh (lazy).
    await resumeLastSessionOrCreate();

    bindEvents();
};

function bindEvents() {
    chatSend.addEventListener("click", sendMessage);
    chatInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
    newChatBtn.addEventListener("click", () => startNewSession());

    // Example cards in the empty state
    document.querySelectorAll(".example-card").forEach((card) => {
        card.addEventListener("click", () => {
            chatInput.value = card.dataset.q;
            sendMessage();
        });
    });
}

// ============================================================================
// SESSION MANAGEMENT
// ============================================================================

async function resumeLastSessionOrCreate() {
    try {
        const res = await fetch(`${BACKEND_API_URL}/agent/sessions?page=1&page_size=1`, {
            headers: { "Authorization": `Bearer ${sessionToken}` },
        });
        if (!res.ok) throw new Error("Could not load sessions");
        const data = await res.json();
        if (data.items && data.items.length > 0) {
            await loadSession(data.items[0].id);
            return;
        }
    } catch (err) {
        console.error("resumeLastSessionOrCreate error:", err);
    }
    await startNewSession();
}

async function startNewSession(prefillQuestion) {
    try {
        const res = await fetch(`${BACKEND_API_URL}/agent/sessions`, {
            method: "POST",
            headers: {
                "Authorization": `Bearer ${sessionToken}`,
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                title: "New chat",
                prefill_question: prefillQuestion || null,
            }),
        });
        if (!res.ok) throw new Error("Could not create session");
        const session = await res.json();
        currentSessionId = session.id;
        await renderSession(session.id);
        if (prefillQuestion) {
            // The prefill message was appended as a user row but the loop
            // hasn't run. Trigger the loop now.
            await runUserMessage(prefillQuestion);
        }
    } catch (err) {
        showToast(`Failed to start chat: ${err.message}`);
    }
}

async function loadSession(sessionId) {
    currentSessionId = sessionId;
    await renderSession(sessionId);
}

async function renderSession(sessionId) {
    try {
        const res = await fetch(`${BACKEND_API_URL}/agent/sessions/${sessionId}`, {
            headers: { "Authorization": `Bearer ${sessionToken}` },
        });
        if (!res.ok) throw new Error("Could not load session");
        const session = await res.json();
        chatMessages.innerHTML = "";
        if (!session.messages || session.messages.length === 0) {
            chatMessages.appendChild(chatEmpty);
            return;
        }
        for (const msg of session.messages) {
            appendMessageToDOM(msg);
        }
        // If the session is awaiting approval, we don't need to do anything
        // special — the plan card is already rendered with its Approve/Cancel
        // buttons.
        scrollToBottom();
    } catch (err) {
        showToast(`Failed to load session: ${err.message}`);
    }
}

// ============================================================================
// SEND MESSAGE + RUN LOOP
// ============================================================================

async function sendMessage() {
    const content = chatInput.value.trim();
    if (!content || isAgentRunning || !currentSessionId) return;
    chatInput.value = "";

    // If this is the user's first message in a brand-new session, the
    // session was created with the message already appended — skip sending twice.
    if (chatEmpty.parentNode) {
        chatEmpty.remove();
    }
    appendUserMessage(content);

    await runUserMessage(content);
}

async function runUserMessage(content) {
    setRunning(true);
    showTypingIndicator();

    try {
        const res = await fetch(`${BACKEND_API_URL}/agent/sessions/${currentSessionId}/messages`, {
            method: "POST",
            headers: {
                "Authorization": `Bearer ${sessionToken}`,
                "Content-Type": "application/json",
            },
            body: JSON.stringify({ content }),
        });
        if (!res.ok) {
            const err = await res.json().catch(() => ({ detail: res.statusText }));
            throw new Error(err.detail || `Agent call failed (${res.status})`);
        }
        const data = await res.json();
        hideTypingIndicator();

        if (data.message) {
            appendMessageToDOM(data.message, data.trace || []);
        }
        if (data.session_state === "error") {
            showToast("Agent returned an error state. Try rephrasing.");
        }
    } catch (err) {
        hideTypingIndicator();
        showToast(`Agent error: ${err.message}`);
    } finally {
        setRunning(false);
    }
}

// ============================================================================
// APPROVE / CANCEL PLAN
// ============================================================================

async function approvePlan(messageId, envVarValues) {
    setRunning(true);
    try {
        const res = await fetch(`${BACKEND_API_URL}/agent/messages/${messageId}/approve`, {
            method: "POST",
            headers: {
                "Authorization": `Bearer ${sessionToken}`,
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                approved: true,
                env_var_values: envVarValues || null,
            }),
        });
        if (!res.ok) {
            const err = await res.json().catch(() => ({ detail: res.statusText }));
            throw new Error(err.detail || `Approve failed (${res.status})`);
        }
        const data = await res.json();
        if (data.message) {
            appendMessageToDOM(data.message, data.trace || []);
        }
    } catch (err) {
        showToast(`Approve failed: ${err.message}`);
    } finally {
        setRunning(false);
    }
}

async function cancelPlan(messageId) {
    setRunning(true);
    try {
        const res = await fetch(`${BACKEND_API_URL}/agent/messages/${messageId}/approve`, {
            method: "POST",
            headers: {
                "Authorization": `Bearer ${sessionToken}`,
                "Content-Type": "application/json",
            },
            body: JSON.stringify({ approved: false }),
        });
        if (!res.ok) {
            const err = await res.json().catch(() => ({ detail: res.statusText }));
            throw new Error(err.detail || `Cancel failed (${res.status})`);
        }
        const data = await res.json();
        if (data.message) {
            appendMessageToDOM(data.message, data.trace || []);
        }
    } catch (err) {
        showToast(`Cancel failed: ${err.message}`);
    } finally {
        setRunning(false);
    }
}

// ============================================================================
// RENDER
// ============================================================================

function appendUserMessage(content) {
    const div = document.createElement("div");
    div.className = "msg user";
    div.innerHTML = `<div class="msg-bubble">${escapeHtml(content)}</div>`;
    chatMessages.appendChild(div);
    scrollToBottom();
}

function appendMessageToDOM(msg, trace = []) {
    // Skip DeployBridge-internal roles in the chat view:
    //   - assistant_tool_call (the LLM's tool_calls payload — handled via trace)
    //   - tool (tool results — handled via trace)
    //   - user_approval (the approve/cancel marker)
    //   - user (already rendered separately by appendUserMessage)
    if (msg.role === "user") return;
    if (msg.role === "assistant_tool_call") return;
    if (msg.role === "tool") return;
    if (msg.role === "user_approval") return;

    const div = document.createElement("div");
    div.className = "msg assistant";
    div.dataset.messageId = msg.id;

    if (msg.role === "assistant_plan") {
        div.innerHTML = renderPlanCard(msg);
    } else if (msg.role === "assistant") {
        div.innerHTML = `<div class="msg-bubble">${renderMarkdown(msg.content || "")}</div>`;
    } else {
        // Fallback: render the role + content raw so we never lose data.
        div.innerHTML = `<div class="msg-bubble"><em>[${escapeHtml(msg.role)}]</em><br>${escapeHtml(msg.content || "")}</div>`;
    }

    // Append trace (if any) — collapsible
    if (trace && trace.length > 0) {
        const traceEl = document.createElement("details");
        traceEl.className = "trace";
        traceEl.innerHTML = `
            <summary>Trace (${trace.length} step${trace.length === 1 ? "" : "s"})</summary>
            <ul>${trace.map((t) => `<li><code>${escapeHtml(t)}</code></li>`).join("")}</ul>
        `;
        div.querySelector(".msg-bubble")?.after(traceEl);
    }

    chatMessages.appendChild(div);

    // Wire plan-card buttons (if any)
    if (msg.role === "assistant_plan") {
        wirePlanCard(div, msg);
    }

    scrollToBottom();
}

function renderPlanCard(msg) {
    const plan = msg.plan || [];
    const hasEnvVars = plan.some(
        (p) => p.tool === "deploy_render" && (p.args.env_var_keys || []).length > 0
    );
    const envFormHtml = hasEnvVars ? `
        <div class="env-form">
            <div style="font-size: 12px; font-weight: 600; margin-bottom: 8px;">
                Env vars (values are NEVER sent to the LLM — only to Render at deploy time)
            </div>
            ${plan.flatMap((p, pi) =>
        (p.args.env_var_keys || []).map((k, ki) => `
                    <div class="env-row">
                        <label>${escapeHtml(k)}</label>
                        <input type="password" data-plan="${pi}" data-key="${escapeHtml(k)}" placeholder="value…" />
                    </div>
                `)
    ).join("")}
        </div>
    ` : "";

    return `
        <div class="msg-bubble">
            🤖 I'm about to run ${plan.length === 1 ? "this action" : `${plan.length} actions`}:
            <div class="plan-card">
                <h4>⚠ Action requires approval</h4>
                ${plan.map((p, i) => `
                    <div class="plan-step">
                        <strong>${i + 1}. ${escapeHtml(p.tool)}</strong>
                        <span class="summary">${escapeHtml(p.summary || "")}</span>
                    </div>
                `).join("")}
                ${envFormHtml}
                <div class="plan-actions">
                    <button class="btn-primary-action" data-action="approve">✓ Approve</button>
                    <button class="btn-secondary-action" data-action="cancel">Cancel</button>
                </div>
            </div>
        </div>
    `;
}

function wirePlanCard(container, msg) {
    const approveBtn = container.querySelector('[data-action="approve"]');
    const cancelBtn = container.querySelector('[data-action="cancel"]');
    if (approveBtn) {
        approveBtn.addEventListener("click", () => {
            // Collect env var values from the form (if any)
            const envVarValues = {};
            container.querySelectorAll(".env-form input").forEach((input) => {
                envVarValues[input.dataset.key] = input.value;
            });
            // Disable the card so the user can't double-click
            approveBtn.disabled = true;
            cancelBtn.disabled = true;
            approvePlan(msg.id, envVarValues);
        });
    }
    if (cancelBtn) {
        cancelBtn.addEventListener("click", () => {
            cancelBtn.disabled = true;
            approveBtn.disabled = true;
            cancelPlan(msg.id);
        });
    }
}

function renderMarkdown(text) {
    // Lightweight markdown: code blocks + inline code + bold + line breaks.
    // If `marked` is loaded, prefer it.
    if (window.marked) {
        try { return marked.parse(text); } catch (e) { /* fall through */ }
    }
    let html = escapeHtml(text);
    html = html.replace(/```(\w*)\n?([\s\S]*?)```/g, (_, lang, code) =>
        `<pre style="background:var(--primary-light); padding:8px; border-radius:4px; overflow:auto; font-family:'JetBrains Mono', monospace; font-size:12px;">${code}</pre>`
    );
    html = html.replace(/`([^`]+)`/g, '<code>$1</code>');
    html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
    return html;
}

function showTypingIndicator() {
    const existing = document.getElementById("typing-indicator");
    if (existing) return;
    const div = document.createElement("div");
    div.id = "typing-indicator";
    div.className = "msg assistant";
    div.innerHTML = `
        <div class="msg-bubble">
            <div class="typing">
                <span class="dot"></span><span class="dot"></span><span class="dot"></span>
                <span style="margin-left:8px; color:var(--text-muted); font-size:12px;">Thinking…</span>
            </div>
        </div>
    `;
    chatMessages.appendChild(div);
    scrollToBottom();
}

function hideTypingIndicator() {
    const el = document.getElementById("typing-indicator");
    if (el) el.remove();
}

function setRunning(running) {
    isAgentRunning = running;
    chatSend.disabled = running;
}

function scrollToBottom() {
    requestAnimationFrame(() => {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    });
}

// ============================================================================
// UTILITIES
// ============================================================================

function escapeHtml(str) {
    if (str == null) return "";
    return String(str)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

function showToast(message) {
    const toast = document.getElementById("toast");
    const toastText = document.getElementById("toast-text");
    if (!toast || !toastText) return;
    toastText.textContent = message;
    toast.classList.add("show");
    setTimeout(() => toast.classList.remove("show"), 3000);
}
