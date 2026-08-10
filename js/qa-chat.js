const SchoolQaChat = (() => {
  let panel = null;
  let entry = null;
  let closeBtn = null;
  let form = null;
  let input = null;
  let messages = null;
  let submitBtn = null;
  let isPending = false;
  const SESSION_KEY = 'school-map-qa-session-id';

  function $(id) {
    return document.getElementById(id);
  }

  function setOpen(open) {
    if (!panel || !entry) return;
    panel.classList.toggle('hidden', !open);
    entry.setAttribute('aria-expanded', String(open));
    if (open) {
      setTimeout(() => input?.focus(), 0);
      scrollToBottom();
    }
  }

  function scrollToBottom() {
    if (!messages) return;
    messages.scrollTop = messages.scrollHeight;
  }

  function appendMessage(role, text, extraClass = '') {
    const el = document.createElement('div');
    el.className = `qa-message qa-message-${role}${extraClass ? ` ${extraClass}` : ''}`;
    const p = document.createElement('p');
    p.textContent = text;
    el.appendChild(p);
    messages.appendChild(el);
    scrollToBottom();
    return el;
  }

  function setPending(pending) {
    isPending = pending;
    submitBtn.disabled = pending;
    input.disabled = pending;
  }

  function createSessionId() {
    if (window.crypto?.randomUUID) {
      return window.crypto.randomUUID();
    }
    return `qa-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
  }

  function getSessionId() {
    let sessionId = localStorage.getItem(SESSION_KEY);
    if (!sessionId) {
      sessionId = createSessionId();
      localStorage.setItem(SESSION_KEY, sessionId);
    }
    return sessionId;
  }

  async function requestAnswer(question) {
    let resp = null;
    const sessionId = getSessionId();
    try {
      resp = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question, sessionId }),
      });
    } catch {
      throw new Error('无法连接智能问答服务。请确认页面是通过 `python3 server.py` 启动，而不是直接打开 HTML 或使用普通静态服务器。');
    }

    let payload = {};
    try {
      payload = await resp.json();
    } catch {
      throw new Error('问答服务没有返回有效 JSON。请确认当前是通过 `python3 server.py` 启动，并且访问同一个端口。');
    }

    if (!resp.ok) {
      throw new Error(payload.error || payload.details || '问答服务请求失败。');
    }
    if (!payload.answer) {
      throw new Error('模型没有返回有效答案。');
    }
    if (payload.sessionId) {
      localStorage.setItem(SESSION_KEY, payload.sessionId);
    }
    return payload.answer;
  }

  async function submitQuestion(question) {
    const text = question.trim();
    if (!text || isPending) return;

    appendMessage('user', text);
    input.value = '';
    setPending(true);

    const loading = appendMessage('assistant', '正在检索本地院校数据、专业排名和录取分，并生成回复...', 'qa-message-loading');
    try {
      loading.querySelector('p').textContent = await requestAnswer(text);
      loading.classList.remove('qa-message-loading');
    } catch (err) {
      loading.querySelector('p').textContent = err.message || '问答服务暂时不可用。';
      loading.classList.remove('qa-message-loading');
    } finally {
      setPending(false);
      input.focus();
      scrollToBottom();
    }
  }

  function bindEvents() {
    entry.addEventListener('click', () => setOpen(panel.classList.contains('hidden')));
    closeBtn.addEventListener('click', () => setOpen(false));

    form.addEventListener('submit', event => {
      event.preventDefault();
      submitQuestion(input.value);
    });

    document.querySelectorAll('.qa-examples [data-question]').forEach(button => {
      button.addEventListener('click', () => {
        setOpen(true);
        submitQuestion(button.dataset.question || '');
      });
    });

    document.addEventListener('keydown', event => {
      if (event.key === 'Escape' && panel && !panel.classList.contains('hidden')) {
        setOpen(false);
      }
    });
  }

  function init() {
    panel = $('qa-panel');
    entry = $('qa-entry');
    closeBtn = $('qa-close');
    form = $('qa-form');
    input = $('qa-input');
    messages = $('qa-messages');
    submitBtn = form?.querySelector('button[type="submit"]') || null;

    if (!panel || !entry || !closeBtn || !form || !input || !messages || !submitBtn) return;
    entry.setAttribute('aria-controls', 'qa-panel');
    entry.setAttribute('aria-expanded', 'false');
    bindEvents();
  }

  return { init };
})();

document.addEventListener('DOMContentLoaded', SchoolQaChat.init);
