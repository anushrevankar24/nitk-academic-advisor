// ================================================
// NITK Academic Advisor — Frontend JavaScript
// ================================================

// --- State ---
let currentScope = 'ug';

// --- Init ---
window.addEventListener('DOMContentLoaded', () => {
    checkStatus();
    autoResizeTextarea();
    loadThemePreference();

    // Ctrl+Enter to submit
    document.getElementById('questionInput').addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
            e.preventDefault();
            askQuestion();
        }
    });
});


// --- Status Check ---
async function checkStatus() {
    const dot = document.getElementById('statusDot');
    const text = document.getElementById('statusText');

    try {
        const response = await fetch('/status');
        const data = await response.json();

        if (data.status === 'ready') {
            dot.className = 'status-dot online';
            text.textContent = `${data.total_chunks || 0} chunks indexed`;
        } else {
            dot.className = 'status-dot offline';
            text.textContent = 'Not ready';
        }
    } catch {
        dot.className = 'status-dot offline';
        text.textContent = 'Offline';
    }
}


// --- Scope Toggle ---
function setScope(el) {
    document.querySelectorAll('.scope-pill').forEach(pill => {
        pill.classList.remove('active');
        pill.setAttribute('aria-checked', 'false');
    });
    el.classList.add('active');
    el.setAttribute('aria-checked', 'true');
    currentScope = el.dataset.value;
}


// --- Example Queries ---
function fillQuestion(text) {
    const input = document.getElementById('questionInput');
    input.value = text;
    input.focus();
    resizeTextarea(input);
}


// --- Auto-resize Textarea ---
function autoResizeTextarea() {
    const textarea = document.getElementById('questionInput');
    textarea.addEventListener('input', () => resizeTextarea(textarea));
}

function resizeTextarea(el) {
    el.style.height = 'auto';
    el.style.height = Math.min(el.scrollHeight, 140) + 'px';
}


// --- Ask Question ---
async function askQuestion() {
    const input = document.getElementById('questionInput');
    const btn = document.getElementById('askButton');
    const question = input.value.trim();

    if (!question) return;

    // Hide welcome
    const welcome = document.getElementById('welcomeMessage');
    if (welcome) welcome.style.display = 'none';

    // Disable input
    btn.disabled = true;
    input.disabled = true;

    // Append user message
    const chatPair = document.createElement('div');
    chatPair.className = 'chat-pair';

    const userMsg = document.createElement('div');
    userMsg.className = 'user-message';
    userMsg.textContent = question;
    chatPair.appendChild(userMsg);

    // Append loading bot message
    const botMsg = createBotSkeleton();
    chatPair.appendChild(botMsg);

    const chatHistory = document.getElementById('chatHistory');
    chatHistory.appendChild(chatPair);
    scrollToBottom();

    // Clear input
    input.value = '';
    resizeTextarea(input);

    try {
        const response = await fetch('/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ question, level: currentScope })
        });

        if (!response.ok) throw new Error(`Server error: ${response.status}`);

        const data = await response.json();

        // Replace skeleton with real answer
        chatPair.removeChild(botMsg);
        const realBot = createBotMessage(data);
        chatPair.appendChild(realBot);

    } catch (error) {
        chatPair.removeChild(botMsg);
        const errorBot = createErrorMessage(error.message);
        chatPair.appendChild(errorBot);
    } finally {
        btn.disabled = false;
        input.disabled = false;
        input.focus();
        scrollToBottom();
    }
}


// --- Create Bot Skeleton (Loading) ---
function createBotSkeleton() {
    const el = document.createElement('div');
    el.className = 'bot-message';
    el.innerHTML = `
        <div class="typing-indicator">
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
        </div>
    `;
    return el;
}


// --- Create Bot Message ---
function createBotMessage(data) {
    const el = document.createElement('div');
    el.className = 'bot-message';

    // Confidence
    const confPercent = Math.round(data.confidence * 100);
    const confClass = confPercent >= 80 ? 'high' : confPercent >= 60 ? 'mid' : 'low';
    const confLabel = confPercent >= 80 ? 'High' : confPercent >= 60 ? 'Medium' : 'Low';

    // Header
    const header = document.createElement('div');
    header.className = 'bot-message-header';
    header.innerHTML = `
        <span class="bot-label">
            <span class="bot-label-icon">🎓</span>
            Academic Advisor
        </span>
        <div class="bot-actions">
            <span class="confidence-badge ${confClass}" title="Confidence: ${confPercent}%">
                ${confLabel} ${confPercent}%
            </span>
            <span class="response-time">${data.time_ms.toFixed(0)} ms</span>
            <button class="copy-btn" onclick="copyAnswer(this)" title="Copy answer">
                📋 Copy
            </button>
        </div>
    `;
    el.appendChild(header);

    // Answer content
    const content = document.createElement('div');
    content.className = 'answer-content';

    marked.setOptions({ breaks: true, gfm: true, tables: true });
    content.innerHTML = marked.parse(data.answer_markdown);

    // Post-process: style inline citations [Source — p.X]
    styleCitations(content);
    el.appendChild(content);

    // Sources
    if (data.sources && data.sources.length > 0) {
        const sourcesSection = createSourcesSection(data.sources);
        el.appendChild(sourcesSection);
    }

    return el;
}


// --- Create Sources Section ---
function createSourcesSection(sources) {
    const section = document.createElement('div');
    section.className = 'sources-section';

    // Toggle button
    const toggle = document.createElement('button');
    toggle.className = 'sources-toggle';
    toggle.innerHTML = `
        <span class="sources-toggle-left">
            📚 Sources
            <span class="sources-count">${sources.length}</span>
        </span>
        <span class="sources-chevron">▼</span>
    `;

    // Sources list
    const list = document.createElement('div');
    list.className = 'sources-list hidden';

    sources.forEach(source => {
        const card = document.createElement('div');
        card.className = 'source-card';

        const scorePercent = Math.round(source.score * 100);
        const barColor = getConfidenceColor(source.score);

        const pages = source.page_start === source.page_end
            ? `p. ${source.page_start}`
            : `pp. ${source.page_start}–${source.page_end}`;

        card.innerHTML = `
            <div class="source-info">
                <span class="source-name">${escapeHtml(source.pdf_name)}</span>
                <span class="source-pages">${pages}</span>
            </div>
            <div class="relevance-bar-container">
                <div class="relevance-bar">
                    <div class="relevance-bar-fill" style="width: ${scorePercent}%; background: ${barColor};"></div>
                </div>
                <span class="relevance-percent" style="color: ${barColor};">${scorePercent}%</span>
            </div>
        `;
        list.appendChild(card);
    });

    toggle.addEventListener('click', () => {
        list.classList.toggle('hidden');
        toggle.classList.toggle('open');
    });

    section.appendChild(toggle);
    section.appendChild(list);
    return section;
}


// --- Create Error Message ---
function createErrorMessage(msg) {
    const el = document.createElement('div');
    el.className = 'bot-message';
    el.innerHTML = `
        <div class="answer-content" style="color: var(--confidence-low);">
            <strong>⚠️ Error:</strong> ${escapeHtml(msg)}. Please try again.
        </div>
    `;
    return el;
}


// --- Copy Answer ---
function copyAnswer(btn) {
    const answerContent = btn.closest('.bot-message').querySelector('.answer-content');
    const text = answerContent.innerText;

    navigator.clipboard.writeText(text).then(() => {
        btn.classList.add('copied');
        btn.innerHTML = '✓ Copied';
        setTimeout(() => {
            btn.classList.remove('copied');
            btn.innerHTML = '📋 Copy';
        }, 2000);
    }).catch(() => {
        // Fallback
        const textArea = document.createElement('textarea');
        textArea.value = text;
        document.body.appendChild(textArea);
        textArea.select();
        document.execCommand('copy');
        document.body.removeChild(textArea);
        btn.innerHTML = '✓ Copied';
        setTimeout(() => { btn.innerHTML = '📋 Copy'; }, 2000);
    });
}


// --- Theme Toggle ---
function toggleTheme() {
    const html = document.documentElement;
    const current = html.getAttribute('data-theme');
    const next = current === 'dark' ? 'light' : 'dark';
    html.setAttribute('data-theme', next);
    document.getElementById('themeIcon').textContent = next === 'dark' ? '☀️' : '🌙';
    localStorage.setItem('theme', next);
}

function loadThemePreference() {
    const saved = localStorage.getItem('theme');
    if (saved) {
        document.documentElement.setAttribute('data-theme', saved);
        document.getElementById('themeIcon').textContent = saved === 'dark' ? '☀️' : '🌙';
    } else if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
        document.documentElement.setAttribute('data-theme', 'dark');
        document.getElementById('themeIcon').textContent = '☀️';
    }
}


// --- Helpers ---
function scrollToBottom() {
    const chat = document.getElementById('chatHistory');
    requestAnimationFrame(() => {
        chat.scrollTop = chat.scrollHeight;
    });
}

function getConfidenceColor(score) {
    if (score >= 0.8) return '#22c55e';
    if (score >= 0.6) return '#f59e0b';
    return '#ef4444';
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}


// --- Style Inline Citations ---
function styleCitations(container) {
    // Match patterns like [Btech_Curriculum_2023 — p.215, p.131, p.254]
    const walker = document.createTreeWalker(container, NodeFilter.SHOW_TEXT, null, false);
    const textNodes = [];
    while (walker.nextNode()) textNodes.push(walker.currentNode);

    textNodes.forEach(node => {
        const text = node.textContent;
        // Match [anything with — and p.] pattern
        if (!/\[.*?—.*?p\..*?\]/.test(text)) return;

        const frag = document.createDocumentFragment();
        let lastIdx = 0;
        const regex = /\[([^\]]*?—[^\]]*?p\.[^\]]*?)\]/g;
        let match;

        while ((match = regex.exec(text)) !== null) {
            // Text before citation
            if (match.index > lastIdx) {
                frag.appendChild(document.createTextNode(text.slice(lastIdx, match.index)));
            }
            // Citation chip
            const chip = document.createElement('span');
            chip.className = 'citation-chip';
            chip.textContent = match[1].trim();
            chip.title = match[1].trim();
            frag.appendChild(chip);
            lastIdx = match.index + match[0].length;
        }

        if (lastIdx > 0) {
            if (lastIdx < text.length) {
                frag.appendChild(document.createTextNode(text.slice(lastIdx)));
            }
            node.parentNode.replaceChild(frag, node);
        }
    });
}


// --- New Chat ---
function newChat() {
    const chatHistory = document.getElementById('chatHistory');
    chatHistory.innerHTML = '';

    // Re-create welcome message
    const welcome = document.createElement('div');
    welcome.className = 'welcome-message';
    welcome.id = 'welcomeMessage';
    welcome.innerHTML = `

        <h2>Welcome to NITK Academic Advisor</h2>
        <p>Ask me anything about NITK academic policies, regulations, curriculum, grading, attendance, and more.</p>
        <div class="example-queries">
            <p class="example-label">Try asking:</p>
            <button class="example-chip" onclick="fillQuestion('What is the minimum attendance required to appear for exams?')">📋 Minimum attendance for exams?</button>
            <button class="example-chip" onclick="fillQuestion('How can I complete my liberal arts credits?')">🎨 Liberal arts credit requirements?</button>
            <button class="example-chip" onclick="fillQuestion('What is the grading system for B.Tech?')">📊 B.Tech grading system?</button>
            <button class="example-chip" onclick="fillQuestion('How do I apply for a course drop?')">📝 Course drop procedure?</button>
        </div>
    `;
    chatHistory.appendChild(welcome);
    document.getElementById('questionInput').focus();
}
