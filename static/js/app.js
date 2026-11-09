const BOT_AVATAR_SVG = `<svg viewBox="0 0 41 41" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M37.532 16.87a9.963 9.963 0 0 0-.856-8.184 10.078 10.078 0 0 0-10.855-4.835 9.964 9.964 0 0 0-7.065-2.937 10.078 10.078 0 0 0-9.52 6.886 9.967 9.967 0 0 0-6.664 4.835 10.079 10.079 0 0 0 1.24 11.817 9.965 9.965 0 0 0 .856 8.185 10.079 10.079 0 0 0 10.855 4.835 9.964 9.964 0 0 0 7.065 2.937 10.078 10.078 0 0 0 9.52-6.886 9.965 9.965 0 0 0 6.664-4.835 10.079 10.079 0 0 0-1.24-11.817z" fill="#fff"/></svg>`;

const IA_CHAT = window.IA_CHAT || {};
const MESSAGE_INITIAL_SIZE = Number(IA_CHAT.initialMessageLimit) || 10;
const MESSAGE_OLDER_PAGE_SIZE = Number(IA_CHAT.olderMessagePageSize) || 10;
const MAX_REF_IMAGES = Number(IA_CHAT.maxReferenceImages) || 8;
const GEN_POLL_INTERVAL_MS = 1500;
const LAST_CONV_STORAGE_PREFIX = "ia_last_conversation_id_";

let state = {
  user: null,
  conversations: [],
  currentId: null,
  messagePage: {},
  loadingOlder: false,
  /** 为 true 时禁止按视口立即拉图/拉 job（渲染阶段 scrollTop 仍在顶部） */
  threadAnchoring: false,
  attachments: [],
  activeGenEs: null,
  genWatchers: {},
  sending: false,
  chatModel: "",
  imageModel: "",
  visionModel: "",
  catalog: null,
  convSearchQuery: "",
  convSearchOpen: false,
  lightboxRefine: null,
  lightboxRefinePoll: null,
  adminUsers: {
    q: "",
    isActive: "all",
    page: 1,
    pageSize: 10,
    totalPages: 1,
    count: 0,
  },
  adminUsersSearchTimer: null,
  shareUserSearch: "",
  shareUserSearchTimer: null,
  currentConvHasMessages: false,
  currentConvIsShared: false,
};

function getCookie(name) {
  const m = document.cookie.match(new RegExp("(^| )" + name + "=([^;]+)"));
  return m ? decodeURIComponent(m[2]) : "";
}

async function api(path, options = {}) {
  const headers = options.headers || {};
  if (!(options.body instanceof FormData)) {
    headers["Content-Type"] = headers["Content-Type"] || "application/json";
  }
  const csrf = getCookie("csrftoken");
  if (csrf) headers["X-CSRFToken"] = csrf;
  const res = await fetch(path, {
    credentials: "same-origin",
    ...options,
    headers,
  });
  if (res.status === 401 || res.status === 403) {
    window.location.href = "/login/";
    throw new Error("未登录");
  }
  const ct = res.headers.get("content-type") || "";
  if (ct.includes("application/json")) {
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "请求失败");
    return data;
  }
  return res;
}

async function ensureCsrf() {
  await fetch("/api/auth/csrf/", { credentials: "same-origin" });
}

function userInitial(name) {
  const s = (name || "U").trim();
  return s ? s.charAt(0).toUpperCase() : "U";
}

function groupLabelForDate(isoString) {
  const d = new Date(isoString);
  const now = new Date();
  const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const startOfDate = new Date(d.getFullYear(), d.getMonth(), d.getDate());
  const diffDays = Math.round((startOfToday - startOfDate) / 86400000);
  if (diffDays === 0) return "今天";
  if (diffDays === 1) return "昨天";
  if (diffDays <= 7) return "过去 7 天";
  return "更早";
}

const ICON_CONV_MORE =
  '<svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><circle cx="5" cy="12" r="1.75"/><circle cx="12" cy="12" r="1.75"/><circle cx="19" cy="12" r="1.75"/></svg>';
const ICON_CONV_PIN =
  '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M12 2v6M9 8h6M8 8l-1 10h10L16 8"/><path d="M9 8c0-1.5 1.5-3 3-3s3 1.5 3 3"/></svg>';

function sortConversationsList(list) {
  return [...list].sort((a, b) => {
    const ap = a.pinned_at ? 1 : 0;
    const bp = b.pinned_at ? 1 : 0;
    if (ap !== bp) return bp - ap;
    if (a.pinned_at && b.pinned_at) {
      return new Date(b.pinned_at) - new Date(a.pinned_at);
    }
    return (
      new Date(b.updated_at || b.created_at) - new Date(a.updated_at || a.created_at)
    );
  });
}

function closeAllConvMenus() {
  document.querySelectorAll(".conv-row.menu-open").forEach((row) => {
    row.classList.remove("menu-open");
    row.querySelector(".conv-dropdown")?.classList.add("hidden");
  });
}

function mergeConversationRow(updated) {
  const idx = state.conversations.findIndex((c) => c.id === updated.id);
  if (idx >= 0) {
    state.conversations[idx] = { ...state.conversations[idx], ...updated };
  }
  state.conversations = sortConversationsList(state.conversations);
}

async function patchConversation(id, payload) {
  return api(`/api/chat/conversations/${id}/`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

async function renameConversation(id) {
  const c = state.conversations.find((x) => x.id === id);
  const next = prompt("重命名对话", c?.title || "新对话");
  if (next == null) return;
  const title = next.trim();
  if (!title) return;
  closeAllConvMenus();
  const updated = await patchConversation(id, { title });
  mergeConversationRow(updated);
  if (state.currentId === id) {
    applyConversationHeader(updated);
  }
  renderConvList();
}

function conversationIsSharedCopy(c) {
  return Boolean(c?.is_shared || c?.shared_by_label);
}

async function removeConversationFromSidebar(id, { sharedCopy = false } = {}) {
  const msg = sharedCopy
    ? "确定解除共享？该对话将从你的列表中移除，不会影响分享者的原对话。"
    : "确定删除该对话？删除后无法恢复。";
  if (!confirm(msg)) return;
  closeAllConvMenus();
  await api(`/api/chat/conversations/${id}/`, { method: "DELETE" });
  state.conversations = state.conversations.filter((c) => c.id !== id);
  ChatCache.invalidateConversation(id);
  ChatCache.clearThreadFragment(id);
  if (state.currentId === id) {
    state.currentId = null;
    const nextId = state.conversations[0]?.id;
    if (nextId) {
      await selectConversation(nextId);
    } else {
      await newConversation();
    }
  } else {
    renderConvList();
  }
}

async function deleteConversation(id) {
  const c = state.conversations.find((x) => x.id === id);
  await removeConversationFromSidebar(id, { sharedCopy: conversationIsSharedCopy(c) });
}

async function dismissSharedConversation(id) {
  await removeConversationFromSidebar(id, { sharedCopy: true });
}

async function togglePinConversation(id) {
  const c = state.conversations.find((x) => x.id === id);
  if (!c) return;
  const updated = await patchConversation(id, { pinned: !c.pinned_at });
  mergeConversationRow(updated);
  renderConvList();
}

function buildConvRow(c) {
  const row = document.createElement("div");
  row.className = "conv-row" + (c.id === state.currentId ? " active" : "");
  row.dataset.convId = String(c.id);

  const btn = document.createElement("button");
  btn.type = "button";
  btn.className = "conv-item" + (c.shared_by_label ? " conv-item-with-note" : "");
  const titleText = c.title || "新对话";
  if (c.shared_by_label) {
    const titleEl = document.createElement("span");
    titleEl.className = "conv-item-title";
    titleEl.textContent = titleText;
    const note = document.createElement("span");
    note.className = "conv-item-share-note";
    note.textContent = `由 ${c.shared_by_label} 分享`;
    btn.append(titleEl, note);
    btn.title = `${titleText}（由 ${c.shared_by_label} 分享）`;
  } else {
    btn.textContent = titleText;
    btn.title = titleText;
  }
  btn.onclick = () => {
    selectConversation(c.id).catch(alert);
    closeSidebarMobile();
  };

  const actions = document.createElement("div");
  actions.className = "conv-item-actions";

  const menuBtn = document.createElement("button");
  menuBtn.type = "button";
  menuBtn.className = "conv-icon-btn conv-menu-btn";
  menuBtn.innerHTML = ICON_CONV_MORE;
  menuBtn.title = "更多";
  menuBtn.setAttribute("aria-label", "更多");
  menuBtn.onclick = (e) => {
    e.stopPropagation();
    const open = row.classList.contains("menu-open");
    closeAllConvMenus();
    if (!open) {
      row.classList.add("menu-open");
      dropdown.classList.remove("hidden");
    }
  };

  const pinBtn = document.createElement("button");
  pinBtn.type = "button";
  pinBtn.className = "conv-icon-btn conv-pin-btn" + (c.pinned_at ? " pinned" : "");
  pinBtn.innerHTML = ICON_CONV_PIN;
  pinBtn.title = c.pinned_at ? "取消置顶" : "置顶";
  pinBtn.setAttribute("aria-label", pinBtn.title);
  pinBtn.onclick = (e) => {
    e.stopPropagation();
    togglePinConversation(c.id).catch(alert);
  };

  const dropdown = document.createElement("div");
  dropdown.className = "conv-dropdown hidden";
  dropdown.setAttribute("role", "menu");

  const renameBtn = document.createElement("button");
  renameBtn.type = "button";
  renameBtn.textContent = "重命名";
  renameBtn.setAttribute("role", "menuitem");
  renameBtn.onclick = (e) => {
    e.stopPropagation();
    renameConversation(c.id).catch(alert);
  };

  const isSharedCopy = conversationIsSharedCopy(c);
  const removeBtn = document.createElement("button");
  removeBtn.type = "button";
  removeBtn.className = isSharedCopy ? "conv-menu-unshare" : "danger";
  removeBtn.textContent = isSharedCopy ? "解除共享" : "删除";
  removeBtn.setAttribute("role", "menuitem");
  removeBtn.onclick = (e) => {
    e.stopPropagation();
    if (isSharedCopy) dismissSharedConversation(c.id).catch(alert);
    else deleteConversation(c.id).catch(alert);
  };

  dropdown.append(renameBtn, removeBtn);
  actions.append(menuBtn, pinBtn);
  row.append(btn, actions, dropdown);
  return row;
}

function appendConvGroup(container, label, items) {
  if (!items?.length) return;
  const section = document.createElement("div");
  section.className = "conv-group";
  const heading = document.createElement("div");
  heading.className = "conv-group-label";
  heading.textContent = label;
  section.appendChild(heading);
  items.forEach((c) => section.appendChild(buildConvRow(c)));
  container.appendChild(section);
}

function conversationsForSidebarList() {
  const q = (state.convSearchQuery || "").trim().toLowerCase();
  let list = sortConversationsList(state.conversations);
  if (!q) return list;
  return list.filter((c) => (c.title || "新对话").toLowerCase().includes(q));
}

function renderConvList() {
  const container = document.getElementById("conversation-groups");
  container.innerHTML = "";
  state.conversations = sortConversationsList(state.conversations);

  const visible = conversationsForSidebarList();
  const pinned = visible.filter((c) => c.pinned_at);
  const unpinned = visible.filter((c) => !c.pinned_at);

  appendConvGroup(container, "已置顶", pinned);

  const groups = new Map();
  unpinned.forEach((c) => {
    const label = groupLabelForDate(c.updated_at || c.created_at);
    if (!groups.has(label)) groups.set(label, []);
    groups.get(label).push(c);
  });

  const order = ["今天", "昨天", "过去 7 天", "更早"];
  order.forEach((label) => appendConvGroup(container, label, groups.get(label)));

  if (state.convSearchQuery.trim() && !visible.length) {
    const empty = document.createElement("div");
    empty.className = "conv-search-empty";
    empty.textContent = "没有匹配的聊天";
    container.appendChild(empty);
  }
}

function updateEmptyState(hasMessages) {
  document.getElementById("empty-state").classList.toggle("hidden", hasMessages);
}

function createTurnElement(role, content) {
  const turn = document.createElement("article");
  turn.className = "turn turn-" + role;

  const av = document.createElement("div");
  av.className = "turn-avatar " + (role === "user" ? "user-av" : "bot-av");
  if (role === "user") {
    av.textContent = userInitial(state.user?.username);
  } else {
    av.innerHTML = BOT_AVATAR_SVG;
  }

  const body = document.createElement("div");
  body.className = "turn-body";
  body.textContent = content || "";

  turn.appendChild(av);
  turn.appendChild(body);
  return { turn, body };
}

function jobIdsInThread(box) {
  if (!box) return [];
  return [...box.querySelectorAll("[data-generation-job]")].map((el) =>
    Number(el.dataset.generationJob)
  );
}

function stopAllGenWatchers() {
  Object.keys(state.genWatchers).forEach((id) => stopGenerationWatch(Number(id)));
  hideGenProgressIfIdle();
}

function isJobRunning(job) {
  return job && !["succeeded", "failed", "cancelled"].includes(job.status);
}

function hideGenProgressIfIdle() {
  const prog = document.getElementById("gen-progress");
  if (!prog) return;
  const anyActive = Object.keys(state.genWatchers).some((id) => isGenWatchActive(Number(id)));
  if (!anyActive) prog.classList.add("hidden");
}

function getGenProgressUi() {
  const root = document.getElementById("gen-progress");
  if (!root) return null;
  const inner = root.querySelector(".gen-progress-inner");
  if (!inner) return null;
  return {
    root,
    inner,
    label: inner.querySelector(".gen-progress-label"),
    spinner: inner.querySelector(".gen-progress-spinner"),
    cancelBtn: inner.querySelector(".gen-cancel-btn"),
  };
}

function setGenProgressUi(message, { running = false, jobId = null } = {}) {
  const ui = getGenProgressUi();
  if (!ui || !ui.label) return;
  ui.root.classList.remove("hidden");
  ui.label.textContent = message || "";
  ui.inner.classList.toggle("is-idle", !running && !jobId);
  if (ui.spinner) ui.spinner.classList.toggle("hidden", !running);
  const btn = ui.cancelBtn;
  if (!btn) return;
  if (running && jobId) {
    btn.classList.remove("hidden");
    btn.disabled = false;
    btn.dataset.jobId = String(jobId);
  } else {
    btn.classList.add("hidden");
    delete btn.dataset.jobId;
  }
}

function isGenWatchActive(jobId) {
  const w = state.genWatchers[jobId];
  return !!w && w.convId === state.currentId && !w.done;
}

/** 回到该会话：仅视口内画廊拉进度；进行中的再恢复轮询 */
async function resumeWatchersForThread(box) {
  if (!state.currentId || !box) return;
  LazyMedia.scan(box);
  for (const jobId of jobIdsInThread(box)) {
    const body = box.querySelector(`[data-generation-job="${jobId}"]`);
    if (!body) continue;
    const statusEl = body.querySelector(".gen-status-line");
    const gridEl = body.querySelector(".gallery");
    if (!gridEl || !LazyMedia.isInViewport(gridEl)) continue;
    window.onGalleryEnterViewport?.(jobId, gridEl, statusEl);
  }
}

function syncMessagePagination(convId, pagination) {
  if (!convId || !pagination) return;
  state.messagePage[convId] = { ...pagination, loadingOlder: false };
}

function updateLoadOlderSentinel() {
  const box = document.getElementById("messages");
  if (!box) return;
  const page = state.messagePage[state.currentId];
  let el = box.querySelector("#load-older-sentinel");
  if (!page?.has_more_older) {
    el?.remove();
    return;
  }
  if (!el) {
    el = document.createElement("div");
    el.id = "load-older-sentinel";
    el.className = "load-older-hint";
    el.textContent = `向上滑动加载更早 ${MESSAGE_OLDER_PAGE_SIZE} 条消息…`;
    box.prepend(el);
  } else if (page.loadingOlder) {
    el.textContent = "正在加载更早消息…";
    el.classList.add("loading");
  } else {
    el.textContent = `向上滑动加载更早 ${MESSAGE_OLDER_PAGE_SIZE} 条消息…`;
    el.classList.remove("loading");
  }
}

function lastConversationStorageKey() {
  const uid = state.user?.id;
  return uid != null ? `${LAST_CONV_STORAGE_PREFIX}${uid}` : `${LAST_CONV_STORAGE_PREFIX}guest`;
}

function persistCurrentConversationId() {
  if (!state.currentId) return;
  try {
    sessionStorage.setItem(lastConversationStorageKey(), String(state.currentId));
  } catch (_) {
    /* private mode */
  }
}

function readStoredConversationId() {
  try {
    const raw = sessionStorage.getItem(lastConversationStorageKey());
    if (!raw) return null;
    const id = parseInt(raw, 10);
    return Number.isFinite(id) ? id : null;
  } catch (_) {
    return null;
  }
}

function resolveInitialConversationId() {
  const stored = readStoredConversationId();
  if (stored && state.conversations.some((c) => c.id === stored)) {
    return stored;
  }
  return state.conversations[0]?.id ?? null;
}

function beginThreadPrepare() {
  state.threadAnchoring = true;
  window.__iaThreadAnchoring = true;
  document.getElementById("thread-container")?.classList.add("thread-preparing");
}

function maxThreadScrollTop() {
  const container = document.getElementById("thread-container");
  if (!container) return 0;
  return Math.max(0, container.scrollHeight - container.clientHeight);
}

function isThreadAnchored() {
  const container = document.getElementById("thread-container");
  if (!container) return true;
  const max = maxThreadScrollTop();
  if (max <= 0) return true;
  return container.scrollTop >= max - 12;
}

function finishThreadPrepare() {
  state.threadAnchoring = false;
  window.__iaThreadAnchoring = false;
  document.getElementById("thread-container")?.classList.remove("thread-preparing");
  const box = document.getElementById("messages");
  if (box) LazyMedia.scan(box);
}

/** 渲染时 scrollTop 仍在顶部，必须锚到底部后再开启视口懒加载 */
function endThreadPrepare() {
  const container = document.getElementById("thread-container");
  if (!container) {
    finishThreadPrepare();
    return;
  }

  let attempts = 0;
  const tryAnchor = () => {
    scrollThreadToBottom();
    attempts += 1;
    if (isThreadAnchored() || attempts >= 30) {
      scrollThreadToBottom();
      finishThreadPrepare();
      setTimeout(scrollThreadToBottom, 80);
      setTimeout(scrollThreadToBottom, 200);
      setTimeout(scrollThreadToBottom, 500);
      return;
    }
    requestAnimationFrame(tryAnchor);
  };

  scrollThreadToBottom();
  requestAnimationFrame(tryAnchor);
}

/** 与后端一致：按 message id 升序；同 id 去重。 */
function sortMessagesForDisplay(messages) {
  const byId = new Map();
  const noId = [];
  for (const m of messages || []) {
    if (m.id != null) {
      if (!byId.has(m.id)) byId.set(m.id, m);
    } else {
      noId.push(m);
    }
  }
  const list = [...byId.values()].sort((a, b) => a.id - b.id);
  return noId.length ? [...list, ...noId] : list;
}

function renderMessages(messages, options = {}) {
  const preserveScroll = !!options.preserveScroll;
  stopAllGenWatchers();
  if (state.currentId) ChatCache.clearThreadFragment(state.currentId);
  beginThreadPrepare();
  const container = document.getElementById("thread-container");
  const prevScroll = preserveScroll && container ? container.scrollTop : 0;
  const prevHeight = preserveScroll && container ? container.scrollHeight : 0;
  const box = document.getElementById("messages");
  box.innerHTML = "";
  if (!preserveScroll) delete box.dataset.expandedOlder;
  const list = sortMessagesForDisplay(messages);
  updateEmptyState(list.length > 0);
  const frag = document.createDocumentFragment();
  for (const m of list) {
    frag.appendChild(buildMessageTurn(m));
  }
  box.appendChild(frag);
  updateLoadOlderSentinel();
  if (preserveScroll) {
    finishThreadPrepare();
    if (container) {
      container.scrollTop = prevScroll + (container.scrollHeight - prevHeight);
    }
  } else {
    endThreadPrepare();
  }
}

function buildMessageTurn(m) {
  const role = m.role === "user" ? "user" : "assistant";
  const { turn, body } = createTurnElement(role, "");

  if (m.id != null) turn.dataset.messageId = String(m.id);

  if (m.content) {
    const textNode = document.createElement("div");
    textNode.className = "msg-text";
    setMessageContent(textNode, m.content, role);
    body.appendChild(textNode);
  }

  if (m.metadata?.attachments?.length) {
    const wrap = document.createElement("div");
    wrap.className = "msg-attachments";
    m.metadata.attachments.forEach((a) => {
      const img = document.createElement("img");
      img.className = "lazy-ref-img";
      img.dataset.src = a.url;
      img.alt = a.name || "参考图";
      wrap.appendChild(img);
      if (!state.threadAnchoring && LazyMedia.isInViewport(img)) {
        img.src = a.url;
        img.dataset.loaded = "1";
      } else {
        LazyMedia.observeRefImage(img);
      }
    });
    body.prepend(wrap);
  }

  if (m.metadata?.generation_snapshot) {
    const snap = m.metadata.generation_snapshot;
    const status = document.createElement("div");
    status.className = "gen-status-line";
    const imageCount = snap.image_count || (snap.images || []).length || 9;
    status.textContent = formatJobProgress({
      id: 0,
      status: snap.status || "succeeded",
      completed_count: snap.completed_count ?? (snap.images || []).filter((x) => x.url).length,
      image_count: imageCount,
    });
    body.appendChild(status);
    const grid = document.createElement("div");
    grid.className = "gallery";
    grid.dataset.generationSnapshot = "1";
    body.appendChild(grid);
    renderGalleryFromJob(
      {
        id: 0,
        image_count: imageCount,
        status: snap.status || "succeeded",
        completed_count: snap.completed_count || 0,
        images: snap.images || [],
      },
      grid
    );
    LazyMedia.scan(grid);
  } else if (m.metadata?.generation_job_id) {
    const jobId = m.metadata.generation_job_id;
    body.dataset.generationJob = String(jobId);
    const running = !["succeeded", "failed", "cancelled"].includes(m.metadata.generation_phase);
    const status = document.createElement("div");
    status.className = "gen-status-line" + (running ? " shimmer" : "");
    status.textContent = formatJobProgress({
      id: jobId,
      status: m.metadata.generation_phase || "running",
      completed_count: m.metadata.completed_count || 0,
      image_count: m.metadata.image_count || 9,
      queue_position: m.metadata.queue_position,
    });
    body.appendChild(status);
    const grid = document.createElement("div");
    grid.className = "gallery";
    grid.dataset.jobGallery = String(jobId);
    body.appendChild(grid);
    LazyMedia.observeJobGallery(grid);
    if (!state.threadAnchoring && LazyMedia.isInViewport(grid)) {
      window.onGalleryEnterViewport?.(jobId, grid, status);
    }
  }

  return turn;
}

function prependMessagesDom(messages) {
  const box = document.getElementById("messages");
  const container = document.getElementById("thread-container");
  if (!box || !messages?.length) return;
  const prevHeight = container.scrollHeight;
  const sentinel = box.querySelector("#load-older-sentinel");
  const anchor = sentinel ? sentinel.nextSibling : box.firstChild;
  for (let i = messages.length - 1; i >= 0; i--) {
    const turn = buildMessageTurn(messages[i]);
    box.insertBefore(turn, anchor);
  }
  box.dataset.expandedOlder = "1";
  container.scrollTop += container.scrollHeight - prevHeight;
  LazyMedia.scan(box);
  updateLoadOlderSentinel();
}

async function loadOlderMessages() {
  const convId = state.currentId;
  if (!convId || state.loadingOlder) return;
  const page = state.messagePage[convId];
  if (!page?.has_more_older) return;

  state.loadingOlder = true;
  page.loadingOlder = true;
  updateLoadOlderSentinel();

  try {
    await loadConversationDetail(convId, { preserveScroll: true });
  } finally {
    state.loadingOlder = false;
    if (state.messagePage[convId]) state.messagePage[convId].loadingOlder = false;
    updateLoadOlderSentinel();
  }
}

function onThreadScrollNearTop() {
  if (state.threadAnchoring) return;
  const container = document.getElementById("thread-container");
  if (!container || container.scrollTop > 80) return;
  loadOlderMessages().catch(() => {});
}

function scrollThreadToBottom() {
  const container = document.getElementById("thread-container");
  if (!container) return;
  container.style.scrollBehavior = "auto";
  container.scrollTop = maxThreadScrollTop();
  const box = document.getElementById("messages");
  const lastTurn = box?.querySelector(".turn:last-of-type");
  if (lastTurn) {
    lastTurn.scrollIntoView({ block: "end", inline: "nearest", behavior: "auto" });
    container.scrollTop = maxThreadScrollTop();
  }
}

/** 进入/刷新会话时滚到最新一条 */
function scrollThreadToLatest() {
  if (state.threadAnchoring) {
    endThreadPrepare();
    return;
  }
  beginThreadPrepare();
  endThreadPrepare();
}

function formatJobProgress(job) {
  const statusMap = {
    pending: "准备中",
    planned: "策划完成，正在生图",
    queued: "排队中",
    running: "正在生成图片",
    succeeded: "已完成",
    failed: "失败",
    cancelled: "已取消",
  };
  const label = statusMap[job.status] || job.status;
  let text = `${label} · ${job.completed_count || 0}/${job.image_count} 张`;
  if (job.id) text += ` · 任务 #${job.id}`;
  if (job.queue_position) text += ` · 队列第 ${job.queue_position} 位`;
  if (job.error_message) {
    const err =
      job.error_message.length > 120 ? job.error_message.slice(0, 120) + "…" : job.error_message;
    if (job.status === "failed" || job.status === "succeeded") text += ` · ${err}`;
  }
  return text;
}

/** 按 message id 升序插入，避免「助手在上、用户提问在下」的错序。 */
function insertTurnInMessageOrder(msg, turn, box) {
  box = box || document.getElementById("messages");
  if (!box || !turn) return turn;
  const id = msg?.id != null ? Number(msg.id) : NaN;
  if (!Number.isFinite(id)) {
    if (turn.parentNode !== box) box.appendChild(turn);
    return turn;
  }
  const existing = box.querySelector(`.turn[data-message-id="${id}"]`);
  if (existing && existing !== turn) {
    existing.replaceWith(turn);
    return turn;
  }
  const positioned = [...box.querySelectorAll(".turn[data-message-id]")];
  for (const t of positioned) {
    if (t === turn) continue;
    const tid = Number(t.dataset.messageId);
    if (Number.isFinite(tid) && id < tid) {
      box.insertBefore(turn, t);
      return turn;
    }
  }
  if (turn.parentNode !== box) box.appendChild(turn);
  return turn;
}

/** 套图任务创建后：用户消息在前，助手进度/结果在后。 */
function syncGenerationMessagesInThread(userMsg, assistantMsg) {
  const box = document.getElementById("messages");
  if (!box) return;

  let userTurn = null;
  if (userMsg?.id) {
    const uid = String(userMsg.id);
    const dupes = [...box.querySelectorAll(`.turn-user[data-message-id="${uid}"]`)];
    if (dupes.length > 1) dupes.slice(1).forEach((el) => el.remove());
    userTurn = box.querySelector(`.turn-user[data-message-id="${uid}"]`);
    if (!userTurn) {
      const orphan = [...box.querySelectorAll(".turn-user:not([data-message-id])")].pop();
      if (orphan) {
        orphan.dataset.messageId = uid;
        userTurn = orphan;
      } else {
        userTurn = buildMessageTurn(userMsg);
        insertTurnInMessageOrder(userMsg, userTurn, box);
      }
    }
  }

  if (assistantMsg?.id) {
    let asTurn = box.querySelector(`.turn[data-message-id="${assistantMsg.id}"]`);
    if (!asTurn) {
      asTurn = buildMessageTurn(assistantMsg);
    }
    if (userTurn) {
      insertTurnInMessageOrder(assistantMsg, asTurn, box);
      if (userTurn.nextElementSibling !== asTurn) {
        box.insertBefore(asTurn, userTurn.nextElementSibling);
      }
    } else {
      insertTurnInMessageOrder(assistantMsg, asTurn, box);
    }
  }

  if (userMsg?.id) {
    const uid = String(userMsg.id);
    const all = [...box.querySelectorAll(`.turn-user[data-message-id="${uid}"]`)];
    if (all.length > 1) all.slice(1).forEach((el) => el.remove());
  }

  LazyMedia.scan(box);
}

function appendMessageDom(m, scroll = true) {
  updateEmptyState(true);
  const box = document.getElementById("messages");
  const turn = buildMessageTurn(m);
  if (m.id != null) insertTurnInMessageOrder(m, turn, box);
  else box.appendChild(turn);
  LazyMedia.scan(turn);
  if (scroll) scrollThreadToBottom();
  return turn.querySelector(".turn-body");
}

function galleryImageSrc(url) {
  return url || "";
}

function bindGalleryImage(img, url, index, jobId) {
  img.src = galleryImageSrc(url);
  img.dataset.slot = String(index);
  img.alt = `套图 ${index}`;
  img.title = "点击查看大图";
  img.tabIndex = 0;
  img.onclick = () => openImageLightbox(url, index, jobId);
  img.onkeydown = (e) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      openImageLightbox(url, index, jobId);
    }
  };
}

function renderGalleryFromJob(job, gridEl) {
  if (!gridEl) return;
  const total = job.image_count || 9;
  const images = job.images || [];
  const byIndex = {};
  images.forEach((img) => {
    byIndex[img.index] = img;
  });

  if (!gridEl.dataset.initialized || gridEl.children.length !== total) {
    gridEl.innerHTML = "";
    gridEl.dataset.initialized = "1";
    for (let i = 1; i <= total; i++) {
      const slot = document.createElement("div");
      slot.className = "gallery-slot";
      slot.dataset.index = String(i);
      slot.textContent = `#${i}`;
      gridEl.appendChild(slot);
    }
  }

  for (let i = 1; i <= total; i++) {
    const slot = gridEl.querySelector(`.gallery-slot[data-index="${i}"]`);
    if (!slot) continue;
    const imgRec = byIndex[i];
    const existingUrl = slot.dataset.imageUrl || "";

    if (imgRec?.url) {
      if (existingUrl === imgRec.url && slot.querySelector("img")) continue;
      slot.dataset.imageUrl = imgRec.url;
      slot.dataset.lazyUrl = imgRec.url;
      slot.dataset.lazyIndex = String(i);
      slot.dataset.lazyJobId = String(job.id);
      slot.className = "gallery-slot done pending-img";
      slot.innerHTML = "";
      slot.textContent = `#${i}`;
      if (!state.threadAnchoring && LazyMedia.isInViewport(slot)) {
        hydrateGallerySlot(slot);
      } else {
        LazyMedia.observeGallerySlot(slot);
      }
    } else if (imgRec?.status === "running") {
      slot.className = "gallery-slot";
      slot.dataset.imageUrl = "";
      slot.textContent = `#${i} 生成中…`;
    } else if (imgRec?.status === "failed") {
      slot.className = "gallery-slot";
      slot.dataset.imageUrl = "";
      slot.textContent = `#${i} 失败`;
    } else if (!imgRec?.url && !slot.querySelector("img")) {
      slot.className = "gallery-slot";
      slot.dataset.imageUrl = "";
      if (job.status === "running" && job.completed_count === i - 1) {
        slot.textContent = `#${i} 生成中…`;
      } else if (!slot.textContent) {
        slot.textContent = `#${i}`;
      }
    }
  }
}

async function refreshJobGallery(jobId, gridEl, statusEl, options = {}) {
  const { force = false } = options;
  let latest = null;
  const applyJob = (job) => {
    latest = job;
    if (statusEl) {
      statusEl.textContent = formatJobProgress(job);
      statusEl.classList.toggle("shimmer", isJobRunning(job));
    }
    renderGalleryFromJob(job, gridEl);
  };

  const cached = !force && ChatCache.getJob(jobId);
  if (cached) applyJob(cached);

  try {
    const job = await api(`/api/generations/${jobId}/`);
    ChatCache.setJob(jobId, job);
    if (!cached || cached.status !== job.status || cached.completed_count !== job.completed_count) {
      applyJob(job);
    }
    return job;
  } catch (_) {
    return latest;
  }
}

function hydrateGallerySlot(slot) {
  if (!slot || slot.querySelector("img")) return;
  const url = slot.dataset.lazyUrl;
  if (!url) return;
  const index = parseInt(slot.dataset.lazyIndex || "0", 10);
  const jobId = parseInt(slot.dataset.lazyJobId || "0", 10);
  slot.textContent = "";
  slot.classList.remove("pending-img");
  const img = document.createElement("img");
  bindGalleryImage(img, url, index, jobId);
  slot.appendChild(img);
  delete slot.dataset.lazyUrl;
}

window.hydrateGallerySlot = hydrateGallerySlot;

window.onGalleryEnterViewport = function onGalleryEnterViewport(jobId, grid, statusEl) {
  if (!jobId || !grid || state.threadAnchoring || window.__iaThreadAnchoring) return;
  refreshJobGallery(jobId, grid, statusEl, { force: grid.dataset.jobHydrated !== "1" })
    .then((job) => {
      grid.dataset.jobHydrated = "1";
      LazyMedia.scan(grid);
      if (isJobRunning(job) && state.currentId) {
        watchGeneration(jobId, state.currentId);
      }
    })
    .catch(() => {});
};

function updateJobInChat(job) {
  const body = document.querySelector(`[data-generation-job="${job.id}"]`);
  if (!body) return;
  const turn = body.closest(".turn");
  if (turn?.parentNode && !turn.previousElementSibling?.classList.contains("turn-user")) {
    const lastUser = turn.parentNode.querySelector(".turn-user:last-of-type");
    if (lastUser && lastUser !== turn) {
      turn.parentNode.insertBefore(turn, lastUser.nextElementSibling);
    }
  }
  const statusEl = body.querySelector(".gen-status-line");
  const gridEl = body.querySelector(".gallery");
  const textEl = body.querySelector(".msg-text");
  if (statusEl) {
    statusEl.textContent = formatJobProgress(job);
    const running = !["succeeded", "failed", "cancelled"].includes(job.status);
    statusEl.classList.toggle("shimmer", running);
  }
  if (textEl && ["succeeded", "failed", "cancelled"].includes(job.status)) {
    const summary =
      job.status === "succeeded"
        ? `已完成 ${job.image_count || job.completed_count || 0} 张套图。`
        : job.status === "failed"
          ? `生成失败（${job.completed_count || 0}/${job.image_count || 0} 张）。`
          : "已取消生成。";
    setMessageContent(textEl, summary, "assistant");
  }
  renderGalleryFromJob(job, gridEl);
  LazyMedia.scan(gridEl);
  refreshLightboxStripFromJobIfOpen(job);
  const container = document.getElementById("thread-container");
  const nearBottom =
    container &&
    container.scrollHeight - container.scrollTop - container.clientHeight < 160;
  if (nearBottom) scrollThreadToBottom();
}

function stopLightboxRefinePoll() {
  if (state.lightboxRefinePoll) {
    clearInterval(state.lightboxRefinePoll);
    state.lightboxRefinePoll = null;
  }
}

function setLightboxRefineStatus(text, isError = false) {
  const el = document.getElementById("lightbox-refine-status");
  if (!el) return;
  if (!text) {
    el.classList.add("hidden");
    el.textContent = "";
    el.classList.remove("error");
    return;
  }
  el.textContent = text;
  el.classList.toggle("error", isError);
  el.classList.remove("hidden");
}

function setLightboxPreviewZoom(on) {
  const zoomed = !!on;
  document.querySelector(".lightbox-preview-stage")?.classList.toggle("is-zoomed", zoomed);
  document.getElementById("image-lightbox")?.classList.toggle("is-preview-zoomed", zoomed);
  document.querySelector(".lightbox-view-layout")?.classList.toggle("is-preview-zoomed", zoomed);
}

function showLightboxViewMode() {
  document.getElementById("lightbox-view-mode")?.classList.remove("hidden");
  document.getElementById("lightbox-compare-mode")?.classList.add("hidden");
  document.querySelector(".lightbox-panel")?.classList.remove("lightbox-wide");
  setLightboxPreviewZoom(false);
}

function showLightboxCompareMode(originalUrl, candidateUrl) {
  const orig = document.getElementById("lightbox-compare-original");
  const cand = document.getElementById("lightbox-compare-candidate");
  if (orig) orig.src = galleryImageSrc(originalUrl);
  if (cand) cand.src = galleryImageSrc(candidateUrl);
  document.getElementById("lightbox-view-mode")?.classList.add("hidden");
  document.getElementById("lightbox-compare-mode")?.classList.remove("hidden");
  document.querySelector(".lightbox-panel")?.classList.add("lightbox-wide");
}

function resolveLightboxSlotUrl(job, index, fallbackUrl) {
  const i = Number(index);
  if (job?.images?.length) {
    const rec = job.images.find((x) => Number(x.index) === i);
    if (rec?.url) return rec.url;
  }
  return fallbackUrl || "";
}

function renderLightboxStrip(job, activeIndex) {
  const strip = document.getElementById("lightbox-strip");
  const wrap = document.getElementById("lightbox-strip-wrap");
  if (!strip || !wrap) return;
  strip.innerHTML = "";
  if (!job?.id) {
    wrap.classList.add("hidden");
    return;
  }
  wrap.classList.remove("hidden");
  const total = Math.max(
    Number(job.image_count) || 0,
    ...((job.images || []).map((x) => Number(x.index)) || [0])
  );
  const n = total > 0 ? total : 9;
  const byIndex = {};
  (job.images || []).forEach((im) => {
    byIndex[im.index] = im;
  });
  const active = Number(activeIndex) || 1;
  strip.style.setProperty("--strip-count", String(n));
  for (let i = 1; i <= n; i++) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "lightbox-strip-item";
    btn.dataset.index = String(i);
    btn.setAttribute("role", "tab");
    const isActive = i === active;
    btn.setAttribute("aria-selected", isActive ? "true" : "false");
    if (isActive) btn.classList.add("is-active");
    const rec = byIndex[i];
    if (rec?.url) {
      const thumb = document.createElement("img");
      thumb.alt = `缩略 #${i}`;
      thumb.loading = "lazy";
      thumb.decoding = "async";
      thumb.src = galleryImageSrc(rec.url);
      btn.appendChild(thumb);
    } else {
      btn.classList.add("placeholder");
      const st = rec?.status || "";
      if (st === "failed") btn.textContent = `#${i} 失败`;
      else if (st === "running") btn.textContent = `#${i} 生成中`;
      else btn.textContent = `#${i} …`;
    }
    btn.addEventListener("click", () => {
      switchLightboxSlot(i).catch(() => {});
    });
    strip.appendChild(btn);
  }
  queueMicrotask(() => {
    strip.querySelector(".lightbox-strip-item.is-active")?.scrollIntoView({
      block: "nearest",
      behavior: "smooth",
    });
  });
}

function refreshLightboxStripFromJobIfOpen(job) {
  if (!job?.id) return;
  const box = document.getElementById("image-lightbox");
  if (!box || box.classList.contains("hidden")) return;
  const ctx = state.lightboxRefine;
  if (!ctx || ctx.jobId !== job.id) return;
  renderLightboxStrip(job, ctx.index || 1);
}

async function switchLightboxSlot(index) {
  const ctx = state.lightboxRefine;
  if (!ctx?.jobId) return;
  stopLightboxRefinePoll();
  await discardLightboxRefineCandidate();
  let job = ChatCache.getJob(ctx.jobId);
  try {
    job = await api(`/api/generations/${ctx.jobId}/`);
    ChatCache.setJob(ctx.jobId, job);
  } catch (_) {
    /* keep cached job if any */
  }
  if (!job) job = ChatCache.getJob(ctx.jobId);
  const idx = Number(index) || 1;
  const url = resolveLightboxSlotUrl(job, idx, ctx.originalUrl);
  ctx.index = idx;
  ctx.originalUrl = url;
  ctx.candidateId = null;
  const img = document.getElementById("lightbox-img");
  const cap = document.getElementById("lightbox-caption");
  if (img) img.src = galleryImageSrc(url);
  if (cap) cap.textContent = `套图 #${idx} · 任务 ${ctx.jobId}`;
  setLightboxRefineStatus("");
  showLightboxViewMode();
  setLightboxPreviewZoom(false);
  const submitBtn = document.getElementById("lightbox-refine-submit");
  if (submitBtn) submitBtn.disabled = !url || !ctx.jobId;
  renderLightboxStrip(job, idx);
  if (!url) {
    setLightboxRefineStatus("该槽位暂无成片，请稍候或等待生成完成后再切换。", false);
  }
}

async function openImageLightbox(url, index, jobId) {
  const box = document.getElementById("image-lightbox");
  const img = document.getElementById("lightbox-img");
  const cap = document.getElementById("lightbox-caption");
  const promptEl = document.getElementById("lightbox-refine-prompt");
  if (!box || !img) return;
  stopLightboxRefinePoll();
  await discardLightboxRefineCandidate();

  const jid = Number(jobId) || null;
  let job = null;
  if (jid) {
    job = ChatCache.getJob(jid);
    if (!job?.images?.length) {
      try {
        job = await api(`/api/generations/${jid}/`);
        ChatCache.setJob(jid, job);
      } catch (_) {
        job = ChatCache.getJob(jid);
      }
    }
  }

  const idx = Number(index) || 1;
  const resolvedUrl = resolveLightboxSlotUrl(job, idx, url);

  state.lightboxRefine = {
    jobId: jid,
    index: idx,
    originalUrl: resolvedUrl,
    candidateId: null,
  };
  showLightboxViewMode();
  setLightboxRefineStatus("");
  setLightboxPreviewZoom(false);
  img.src = galleryImageSrc(resolvedUrl);
  if (cap) {
    cap.textContent = jid ? `套图 #${idx} · 任务 ${jid}` : `套图 #${idx}`;
  }
  if (promptEl && !promptEl.value.trim()) {
    promptEl.placeholder =
      "例如：人物更自然、减少 AI 感；保持构图；产品包装与商品原图一致…";
  }
  const submitBtn = document.getElementById("lightbox-refine-submit");
  if (submitBtn) submitBtn.disabled = !jid || !resolvedUrl;
  renderLightboxStrip(job, idx);
  syncLightboxImageModelSelect(state.imageModel);
  if (jid) {
    resolveLightboxDefaultImageModel(jid).catch(() => {});
  }
  box.classList.remove("hidden");
  document.body.classList.add("lightbox-open");
}

function closeImageLightbox() {
  const box = document.getElementById("image-lightbox");
  const img = document.getElementById("lightbox-img");
  if (!box) return;
  stopLightboxRefinePoll();
  if (state.lightboxRefine?.candidateId) {
    discardLightboxRefineCandidate().catch(() => {});
  }
  state.lightboxRefine = null;
  box.classList.add("hidden");
  document.body.classList.remove("lightbox-open");
  showLightboxViewMode();
  setLightboxRefineStatus("");
  if (img) img.src = "";
  document.getElementById("lightbox-compare-original")?.removeAttribute("src");
  document.getElementById("lightbox-compare-candidate")?.removeAttribute("src");
  const strip = document.getElementById("lightbox-strip");
  const wrap = document.getElementById("lightbox-strip-wrap");
  if (strip) strip.innerHTML = "";
  wrap?.classList.add("hidden");
}

async function downloadAllLightboxImages() {
  const ctx = state.lightboxRefine;
  if (!ctx?.jobId) return;
  const btn = document.getElementById("lightbox-download-all");
  if (btn) btn.disabled = true;
  try {
    const job = await api(`/api/generations/${ctx.jobId}/`);
    ChatCache.setJob(ctx.jobId, job);
    const items = (job.images || [])
      .filter((x) => x.url)
      .sort((a, b) => Number(a.index) - Number(b.index));
    if (!items.length) {
      alert("暂无可下载的成片");
      return;
    }
    for (let i = 0; i < items.length; i++) {
      const rec = items[i];
      const a = document.createElement("a");
      a.href = galleryImageSrc(rec.url);
      a.download = `job${ctx.jobId}_slot${rec.index}.png`;
      a.target = "_blank";
      a.rel = "noopener noreferrer";
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      await new Promise((r) => setTimeout(r, 380));
    }
  } catch (err) {
    alert(err.message || "下载失败");
  } finally {
    if (btn) btn.disabled = false;
  }
}

async function pollLightboxRefineCandidate(candidateId) {
  const ctx = state.lightboxRefine;
  if (!ctx || ctx.candidateId !== candidateId) return;
  try {
    const data = await api(`/api/generations/refine-candidates/${candidateId}/`);
    if (data.status === "succeeded" && data.url) {
      stopLightboxRefinePoll();
      setLightboxRefineStatus("");
      document.getElementById("lightbox-refine-submit").disabled = false;
      showLightboxCompareMode(ctx.originalUrl, data.url);
      return;
    }
    if (data.status === "failed") {
      stopLightboxRefinePoll();
      document.getElementById("lightbox-refine-submit").disabled = false;
      setLightboxRefineStatus(data.error_message || "修复失败", true);
      return;
    }
    setLightboxRefineStatus(
      data.status === "running" ? "正在生成修复版…" : "已提交，等待生成…"
    );
  } catch (err) {
    stopLightboxRefinePoll();
    document.getElementById("lightbox-refine-submit").disabled = false;
    setLightboxRefineStatus(err.message || "查询失败", true);
  }
}

async function submitLightboxRefine() {
  const ctx = state.lightboxRefine;
  if (!ctx?.jobId || !ctx.index) return;
  const prompt = document.getElementById("lightbox-refine-prompt")?.value.trim();
  if (!prompt) {
    setLightboxRefineStatus("请先填写修复说明", true);
    return;
  }
  const submitBtn = document.getElementById("lightbox-refine-submit");
  if (submitBtn) submitBtn.disabled = true;
  setLightboxRefineStatus("正在提交…");
  const imageModel =
    document.getElementById("lightbox-refine-image-model")?.value || state.imageModel;
  try {
    const data = await api(
      `/api/generations/${ctx.jobId}/slots/${ctx.index}/refine/`,
      {
        method: "POST",
        body: JSON.stringify({ prompt, image_model: imageModel }),
      }
    );
    ctx.candidateId = data.id;
    if (data.status === "succeeded" && data.url) {
      showLightboxCompareMode(ctx.originalUrl, data.url);
      setLightboxRefineStatus("");
      if (submitBtn) submitBtn.disabled = false;
      return;
    }
    const modelLabelText =
      modelLabel(state.catalog?.image_models, imageModel) || imageModel || "";
    setLightboxRefineStatus(
      modelLabelText ? `正在用 ${modelLabelText} 生成修复版…` : "正在生成修复版…"
    );
    stopLightboxRefinePoll();
    state.lightboxRefinePoll = setInterval(() => {
      pollLightboxRefineCandidate(data.id).catch(() => {});
    }, 1500);
    pollLightboxRefineCandidate(data.id).catch(() => {});
  } catch (err) {
    if (submitBtn) submitBtn.disabled = false;
    setLightboxRefineStatus(err.message || "提交失败", true);
  }
}

async function applyLightboxRefine() {
  const ctx = state.lightboxRefine;
  if (!ctx?.candidateId) return;
  try {
    const data = await api(
      `/api/generations/refine-candidates/${ctx.candidateId}/apply/`,
      { method: "POST", body: "{}" }
    );
    ChatCache.invalidateJob(ctx.jobId);
    if (data.job) {
      updateJobInChat(data.job);
      ChatCache.setJob(ctx.jobId, data.job);
    }
    closeImageLightbox();
  } catch (err) {
    alert(err.message || "替换失败");
  }
}

async function discardLightboxRefineCandidate() {
  const ctx = state.lightboxRefine;
  if (ctx?.candidateId) {
    try {
      await api(`/api/generations/refine-candidates/${ctx.candidateId}/discard/`, {
        method: "POST",
        body: "{}",
      });
    } catch (_) {
      /* ignore */
    }
    ctx.candidateId = null;
  }
}

async function keepOriginalLightboxImage() {
  await discardLightboxRefineCandidate();
  showLightboxViewMode();
  setLightboxRefineStatus("已保留原图，未做替换");
}

function retryLightboxRefine() {
  discardLightboxRefineCandidate().catch(() => {});
  showLightboxViewMode();
  setLightboxRefineStatus("");
  document.getElementById("lightbox-refine-submit").disabled = false;
}

function stopGenerationWatch(jobId) {
  const w = state.genWatchers[jobId];
  if (!w) return;
  w.done = true;
  if (w.pollTimer) clearInterval(w.pollTimer);
  if (w.es) {
    w.es.close();
  }
  delete state.genWatchers[jobId];
  if (state.activeGenEs === w.es) state.activeGenEs = null;
}

function jobBelongsToActiveConversation(job) {
  if (job.conversation != null && state.currentId != null) {
    return Number(job.conversation) === Number(state.currentId);
  }
  const body = document.querySelector(`[data-generation-job="${job.id}"]`);
  return !!body && document.getElementById("messages")?.contains(body);
}

function applyGenerationJobProgress(job) {
  if (!jobBelongsToActiveConversation(job)) return;
  updateJobInChat(job);
  const terminal = ["succeeded", "failed", "cancelled"].includes(job.status);
  if (terminal) {
    if (job.status === "succeeded") {
      setGenProgressUi(formatJobProgress(job), { running: false });
      setTimeout(hideGenProgressIfIdle, 2500);
    } else {
      hideGenProgressIfIdle();
    }
    return;
  }
  setGenProgressUi(formatJobProgress(job), { running: true, jobId: job.id });
}

async function cancelGenerationJob(jobId) {
  if (!jobId) return null;
  try {
    const job = await api(`/api/generations/${jobId}/cancel/`, { method: "POST", body: "{}" });
    ChatCache.setJob(jobId, job);
    ChatCache.invalidateConversation(state.currentId);
    stopGenerationWatch(jobId);
    updateJobInChat(job);
    hideGenProgressIfIdle();
    await loadConversationDetail(state.currentId).catch(() => {});
    return job;
  } catch (err) {
    alert(err.message || "取消失败");
    return null;
  }
}

async function pollGenerationJob(jobId) {
  if (!isGenWatchActive(jobId)) return null;
  const job = await api(`/api/generations/${jobId}/`);
  ChatCache.setJob(jobId, job);
  if (!isGenWatchActive(jobId)) return job;
  applyGenerationJobProgress(job);
  if (["succeeded", "failed", "cancelled"].includes(job.status)) {
    stopGenerationWatch(jobId);
    hideGenProgressIfIdle();
  }
  return job;
}

function modelLabel(list, id) {
  const item = (list || []).find((m) => m.id === id);
  return item ? item.label : id;
}

function updateModelUI() {
  const chatLabel = modelLabel(state.catalog?.chat_models, state.chatModel);
  document.getElementById("chat-model-label").textContent = chatLabel || state.chatModel || "对话模型";

  const hint = document.getElementById("active-models-hint");
  if (hint) {
    hint.textContent =
      `对话 ${chatLabel} · 识图 ${modelLabel(state.catalog?.vision_models, state.visionModel)} · 生图 ${modelLabel(state.catalog?.image_models, state.imageModel)}`;
  }

  const imageSel = document.getElementById("image-model");
  if (imageSel && state.imageModel) {
    imageSel.value = state.imageModel;
  }

  renderModelPickerLists();
}

function renderModelPickerLists() {
  const chatUl = document.getElementById("chat-model-list");
  const visionUl = document.getElementById("vision-model-list");
  const imageUl = document.getElementById("image-model-list");
  if (!chatUl || !visionUl || !imageUl || !state.catalog) return;

  chatUl.innerHTML = "";
  (state.catalog.chat_models || []).forEach((m) => {
    chatUl.appendChild(createModelPickerItem(m, m.id === state.chatModel, () => selectChatModel(m.id)));
  });

  visionUl.innerHTML = "";
  (state.catalog.vision_models || []).forEach((m) => {
    visionUl.appendChild(createModelPickerItem(m, m.id === state.visionModel, () => selectVisionModel(m.id)));
  });

  imageUl.innerHTML = "";
  (state.catalog.image_models || []).forEach((m) => {
    imageUl.appendChild(createModelPickerItem(m, m.id === state.imageModel, () => selectImageModel(m.id)));
  });
}

function createModelPickerItem(model, active, onClick) {
  const li = document.createElement("li");
  const btn = document.createElement("button");
  btn.type = "button";
  btn.className = "model-picker-item" + (active ? " active" : "");
  btn.innerHTML = `<span>${model.label}</span><span class="check">✓</span>`;
  btn.onclick = () => {
    onClick();
    closeModelPicker();
  };
  li.appendChild(btn);
  return li;
}

function fillImageModelSelectOptions(sel, selectedId) {
  if (!sel || !state.catalog) return;
  sel.innerHTML = "";
  const groups = {};
  (state.catalog.image_models || []).forEach((m) => {
    const g = m.group || "other";
    if (!groups[g]) groups[g] = [];
    groups[g].push(m);
  });
  Object.keys(groups).forEach((g) => {
    const og = document.createElement("optgroup");
    og.label = g;
    groups[g].forEach((m) => {
      const opt = document.createElement("option");
      opt.value = m.id;
      opt.textContent = m.label;
      og.appendChild(opt);
    });
    sel.appendChild(og);
  });
  const pick = selectedId || state.imageModel;
  if (pick) sel.value = pick;
}

function populateImageModelSelect() {
  fillImageModelSelectOptions(document.getElementById("image-model"), state.imageModel);
}

function syncLightboxImageModelSelect(selectedId) {
  fillImageModelSelectOptions(
    document.getElementById("lightbox-refine-image-model"),
    selectedId || state.imageModel
  );
}

async function resolveLightboxDefaultImageModel(jobId) {
  if (!jobId) return;
  let model = ChatCache.getJob(jobId)?.image_model;
  if (!model) {
    try {
      const job = await api(`/api/generations/${jobId}/`);
      ChatCache.setJob(jobId, job);
      model = job.image_model;
    } catch (_) {
      /* ignore */
    }
  }
  if (state.lightboxRefine?.jobId === jobId) {
    state.lightboxRefine.jobImageModel = model || state.imageModel;
  }
  syncLightboxImageModelSelect(model || state.imageModel);
}

async function loadPreferences() {
  const data = await api("/api/auth/preferences/");
  state.catalog = {
    chat_models: data.chat_models,
    vision_models: data.vision_models,
    image_models: data.image_models,
    defaults: data.defaults,
  };
  state.chatModel = data.defaults.chat_model;
  state.visionModel = data.defaults.vision_model;
  state.imageModel = data.defaults.image_model;
  populateImageModelSelect();
  updateModelUI();
}

async function savePreferences(patch) {
  const data = await api("/api/auth/preferences/", {
    method: "PATCH",
    body: JSON.stringify(patch),
  });
  state.user = data.user;
  state.catalog = data.catalog;
  state.chatModel = data.catalog.defaults.chat_model;
  state.visionModel = data.catalog.defaults.vision_model;
  state.imageModel = data.catalog.defaults.image_model;
  populateImageModelSelect();
  updateModelUI();
}

async function selectChatModel(id) {
  if (id === state.chatModel) return;
  await savePreferences({ chat_model: id });
}

async function selectImageModel(id) {
  if (id === state.imageModel) return;
  await savePreferences({ image_model: id });
}

async function selectVisionModel(id) {
  if (id === state.visionModel) return;
  await savePreferences({ vision_model: id });
}

function openModelPicker() {
  document.getElementById("model-picker").classList.remove("hidden");
  document.getElementById("model-selector").setAttribute("aria-expanded", "true");
}

function closeModelPicker() {
  document.getElementById("model-picker").classList.add("hidden");
  document.getElementById("model-selector").setAttribute("aria-expanded", "false");
}

function toggleModelPicker(e) {
  e.stopPropagation();
  const picker = document.getElementById("model-picker");
  if (picker.classList.contains("hidden")) openModelPicker();
  else closeModelPicker();
}

function escapeHtml(s) {
  return String(s ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

const ADMIN_STATUS_LABEL = {
  pending: "待审批",
  approved: "已通过",
  rejected: "已拒绝",
};

function updateAdminMenuVisibility() {
  const isSuper = Boolean(state.user?.is_superuser);
  document.querySelectorAll(".user-dropdown-admin").forEach((el) => {
    el.classList.toggle("hidden", !isSuper);
  });
  if (isSuper) {
    refreshPendingApprovalBadge().catch(() => {});
    startPendingApprovalPolling();
  }
}

let pendingApprovalPollTimer = null;

function applyPendingBadgeCount(n) {
  const menuBadge = document.getElementById("pending-approval-badge");
  const avatarBadge = document.getElementById("avatar-pending-badge");
  const show = n > 0;
  [menuBadge, avatarBadge].forEach((badge) => {
    if (!badge) return;
    if (show) {
      badge.textContent = n > 99 ? "99+" : String(n);
      badge.classList.remove("hidden");
    } else {
      badge.textContent = "";
      badge.classList.add("hidden");
    }
  });
}

function startPendingApprovalPolling() {
  if (pendingApprovalPollTimer) return;
  pendingApprovalPollTimer = window.setInterval(() => {
    if (!state.user?.is_superuser) return;
    refreshPendingApprovalBadge().catch(() => {});
  }, 8000);
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "visible" && state.user?.is_superuser) {
      refreshPendingApprovalBadge().catch(() => {});
    }
  });
}

async function refreshPendingApprovalBadge() {
  if (!state.user?.is_superuser) return;
  const data = await api("/api/auth/admin/pending-count/");
  const n = Number(data.count) || 0;
  applyPendingBadgeCount(n);
}

function closeAdminModal(kind) {
  const id = kind === "users" ? "admin-users-modal" : "admin-approvals-modal";
  document.getElementById(id)?.classList.add("hidden");
}

function openAdminApprovalsModal() {
  document.getElementById("user-dropdown")?.classList.add("hidden");
  document.getElementById("btn-user-menu")?.setAttribute("aria-expanded", "false");
  document.getElementById("admin-approvals-modal")?.classList.remove("hidden");
  loadPendingRegistrations().catch((e) => alert(e.message));
}

function openAdminUsersModal() {
  document.getElementById("user-dropdown")?.classList.add("hidden");
  document.getElementById("btn-user-menu")?.setAttribute("aria-expanded", "false");
  document.getElementById("admin-users-modal")?.classList.remove("hidden");
  syncAdminUsersToolbarFromState();
  loadAdminUsers().catch((e) => alert(e.message));
}

function syncAdminUsersToolbarFromState() {
  const search = document.getElementById("admin-users-search");
  const filter = document.getElementById("admin-users-active-filter");
  if (search) search.value = state.adminUsers.q;
  if (filter) filter.value = state.adminUsers.isActive;
}

function adminUsersQueryString() {
  const p = new URLSearchParams();
  p.set("page", String(state.adminUsers.page));
  p.set("page_size", String(state.adminUsers.pageSize));
  if (state.adminUsers.q.trim()) p.set("q", state.adminUsers.q.trim());
  if (state.adminUsers.isActive !== "all") p.set("is_active", state.adminUsers.isActive);
  return p.toString();
}

function updateAdminUsersPaginationUi() {
  const info = document.getElementById("admin-users-page-info");
  const prev = document.getElementById("admin-users-prev");
  const next = document.getElementById("admin-users-next");
  const au = state.adminUsers;
  if (info) {
    const from = au.count === 0 ? 0 : (au.page - 1) * au.pageSize + 1;
    const to = Math.min(au.page * au.pageSize, au.count);
    info.textContent = `共 ${au.count} 人 · 第 ${au.page}/${au.totalPages} 页（${from}–${to}）`;
  }
  if (prev) prev.disabled = au.page <= 1;
  if (next) next.disabled = au.page >= au.totalPages;
}

function formatAdminDate(iso) {
  if (!iso) return "";
  try {
    const d = new Date(iso);
    return d.toLocaleString("zh-CN", { hour12: false });
  } catch {
    return iso;
  }
}

async function loadPendingRegistrations() {
  const listEl = document.getElementById("admin-approvals-list");
  const emptyEl = document.getElementById("admin-approvals-empty");
  if (!listEl) return;
  const rows = await api("/api/auth/admin/pending-registrations/");
  listEl.innerHTML = "";
  if (!rows.length) {
    emptyEl?.classList.remove("hidden");
    return;
  }
  emptyEl?.classList.add("hidden");
  for (const row of rows) {
    const div = document.createElement("div");
    div.className = "admin-pending-row";
    const title = row.real_name
      ? `${escapeHtml(row.real_name)}（${escapeHtml(row.username)}）`
      : escapeHtml(row.username);
    div.innerHTML = `
      <div class="admin-pending-meta">
        <strong>${title}</strong>
        <span>申请时间：${escapeHtml(formatAdminDate(row.date_joined))}</span>
      </div>
      <div class="admin-row-actions">
        <button type="button" class="admin-btn admin-btn-approve" data-approve-id="${row.id}">通过</button>
        <button type="button" class="admin-btn admin-btn-reject" data-reject-id="${row.id}">拒绝</button>
      </div>`;
    listEl.appendChild(div);
  }
  await refreshPendingApprovalBadge();
}

async function loadAdminUsers() {
  const listEl = document.getElementById("admin-users-list");
  const emptyEl = document.getElementById("admin-users-empty");
  if (!listEl) return;
  const data = await api(`/api/auth/admin/users/?${adminUsersQueryString()}`);
  state.adminUsers.page = data.page || 1;
  state.adminUsers.totalPages = data.total_pages || 1;
  state.adminUsers.count = data.count || 0;
  const rows = data.results || [];
  listEl.innerHTML = "";
  if (!rows.length) {
    emptyEl?.classList.remove("hidden");
  } else {
    emptyEl?.classList.add("hidden");
  }
  updateAdminUsersPaginationUi();
  for (const row of rows) {
    const div = document.createElement("div");
    div.className = "admin-user-row";
    div.dataset.userId = String(row.id);
    const statusClass = row.approval_status || "approved";
    const superTag = row.is_superuser ? " · 超级管理员" : "";
    const activeLabel = row.is_active ? "启用" : "停用";
    const displayName = row.real_name
      ? `${escapeHtml(row.real_name)}（${escapeHtml(row.username)}）`
      : escapeHtml(row.username);
    div.innerHTML = `
      <div class="admin-user-card-top">
        <div class="admin-user-meta">
          <strong>${displayName}${escapeHtml(superTag)}</strong>
          <span>注册：${escapeHtml(formatAdminDate(row.date_joined))} · 账号${escapeHtml(activeLabel)}</span>
        </div>
        <span class="admin-status-tag ${escapeHtml(statusClass)}">${escapeHtml(ADMIN_STATUS_LABEL[statusClass] || statusClass)}</span>
      </div>
      <div class="admin-user-form-grid">
        <div class="admin-field admin-field-span-full">
          <span class="admin-field-label">真实名称</span>
          <input type="text" class="admin-field-input admin-field-input-text" data-field="real_name" value="${escapeHtml(row.real_name || "")}" maxlength="64" placeholder="显示用中文名或昵称" autocomplete="off" />
        </div>
        <div class="admin-field">
          <span class="admin-field-label">审批状态</span>
          <select class="admin-field-input" data-field="approval_status" ${row.is_superuser ? "disabled" : ""}>
            <option value="pending" ${statusClass === "pending" ? "selected" : ""}>待审批</option>
            <option value="approved" ${statusClass === "approved" ? "selected" : ""}>已通过</option>
            <option value="rejected" ${statusClass === "rejected" ? "selected" : ""}>已拒绝</option>
          </select>
        </div>
        <div class="admin-field">
          <span class="admin-field-label">账号启用</span>
          <select class="admin-field-input" data-field="is_active" ${row.is_superuser ? "disabled" : ""}>
            <option value="true" ${row.is_active ? "selected" : ""}>启用</option>
            <option value="false" ${!row.is_active ? "selected" : ""}>停用</option>
          </select>
        </div>
        <div class="admin-field">
          <span class="admin-field-label">日配额</span>
          <input type="number" class="admin-field-input admin-field-input-number" min="0" data-field="daily_image_quota" value="${Number(row.daily_image_quota) || 0}" />
        </div>
        <div class="admin-field">
          <span class="admin-field-label">默认张数</span>
          <input type="number" class="admin-field-input admin-field-input-number" min="1" max="12" data-field="default_image_count" value="${Number(row.default_image_count) || 9}" />
        </div>
        <div class="admin-user-save-row">
          <button type="button" class="admin-btn admin-btn-approve" data-save-user="${row.id}">保存修改</button>
        </div>
      </div>`;
    listEl.appendChild(div);
  }
}

async function approveRegistration(userId) {
  await api(`/api/auth/admin/pending-registrations/${userId}/approve/`, { method: "POST", body: "{}" });
  await loadPendingRegistrations();
}

async function rejectRegistration(userId) {
  if (!confirm("确定拒绝该注册申请？")) return;
  await api(`/api/auth/admin/pending-registrations/${userId}/reject/`, { method: "POST", body: "{}" });
  await loadPendingRegistrations();
}

async function saveAdminUser(userId, rowEl) {
  const body = {};
  rowEl.querySelectorAll("[data-field]").forEach((input) => {
    const key = input.dataset.field;
    if (!key || input.disabled) return;
    if (input.tagName === "SELECT" && (key === "is_active")) {
      body[key] = input.value === "true";
      return;
    }
    if (input.type === "number") {
      body[key] = Number(input.value);
      return;
    }
    body[key] = input.value;
  });
  await api(`/api/auth/admin/users/${userId}/`, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
  await loadAdminUsers();
}

async function loadUser() {
  state.user = await api("/api/auth/me/");
  const label = (state.user.real_name || "").trim() || state.user.username;
  document.getElementById("username-label").textContent = label;
  document.getElementById("user-avatar").textContent = userInitial(label);
  state.chatModel = state.user.chat_model || state.chatModel;
  state.visionModel = state.user.vision_model || state.visionModel;
  state.imageModel = state.user.image_model || state.imageModel;
  const countSel = document.getElementById("image-count");
  if (state.user.default_image_count) {
    countSel.value = String(state.user.default_image_count);
  }
  updateAdminMenuVisibility();
}

async function loadConversations() {
  state.conversations = sortConversationsList(await api("/api/chat/conversations/"));
  renderConvList();
  const cur = state.conversations.find((c) => c.id === state.currentId);
  if (cur) applyConversationHeader(cur);
}

function currentConversationRow() {
  return state.conversations.find((c) => c.id === state.currentId);
}

function updateShareChatButtonState() {
  const btn = document.getElementById("btn-share-chat");
  if (!btn) return;
  const shared =
    state.currentConvIsShared || conversationIsSharedCopy(currentConversationRow());
  const canShare = Boolean(state.currentId) && state.currentConvHasMessages && !shared;
  btn.disabled = !canShare;
  if (shared) {
    btn.title = "他人分享的对话不能再次分享";
  } else if (!state.currentConvHasMessages) {
    btn.title = "有消息后才可分享";
  } else {
    btn.title = "分享当前对话";
  }
}

function updateShareChatBanner(detail) {
  const el = document.getElementById("share-chat-banner");
  if (!el) return;
  const label = (detail?.shared_by_label || "").trim();
  if (detail?.is_shared && label) {
    el.textContent = `此对话由 ${label} 分享给你，你可以在此基础上继续聊天。`;
    el.classList.remove("hidden");
  } else {
    el.textContent = "";
    el.classList.add("hidden");
  }
}

function applyConversationHeader(detail) {
  const title = (detail?.title || "").trim() || "新对话";
  document.title = title === "新对话" ? "AFS GPT" : `${title} · AFS GPT`;
  updateShareChatBanner(detail);
}

function closeShareChatModal() {
  document.getElementById("share-chat-modal")?.classList.add("hidden");
}

function openShareChatModal() {
  const shared =
    state.currentConvIsShared || conversationIsSharedCopy(currentConversationRow());
  if (!state.currentId || !state.currentConvHasMessages || shared) return;
  document.getElementById("share-chat-modal")?.classList.remove("hidden");
  const search = document.getElementById("share-user-search");
  if (search) search.value = state.shareUserSearch;
  loadShareableUsers().catch((e) => alert(e.message));
}

async function loadShareableUsers() {
  const listEl = document.getElementById("share-user-list");
  const emptyEl = document.getElementById("share-user-empty");
  if (!listEl) return;
  const q = (state.shareUserSearch || "").trim();
  const path = q ? `/api/chat/shareable-users/?q=${encodeURIComponent(q)}` : "/api/chat/shareable-users/";
  const rows = await api(path);
  listEl.innerHTML = "";
  if (!rows.length) {
    emptyEl?.classList.remove("hidden");
    return;
  }
  emptyEl?.classList.add("hidden");
  for (const row of rows) {
    const div = document.createElement("div");
    div.className = "share-user-row";
    const name = row.display_name || row.real_name || row.username;
    div.innerHTML = `
      <div>
        <strong>${escapeHtml(name)}</strong>
        <span>@${escapeHtml(row.username)}</span>
      </div>
      <button type="button" class="admin-btn admin-btn-approve" data-share-to="${row.id}">分享</button>`;
    listEl.appendChild(div);
  }
}

async function shareCurrentConversationWith(userId) {
  if (!state.currentId) return;
  const data = await api(`/api/chat/conversations/${state.currentId}/share/`, {
    method: "POST",
    body: JSON.stringify({ user_id: userId }),
  });
  closeShareChatModal();
  alert(data.detail || "分享成功");
}

function parkCurrentConversation() {
  if (!state.currentId) return;
  const box = document.getElementById("messages");
  const scroll = document.getElementById("thread-container");
  jobIdsInThread(box).forEach((jobId) => stopGenerationWatch(jobId));
  ChatCache.parkThread(state.currentId, box, scroll);
  hideGenProgressIfIdle();
}

async function loadConversationDetail(id, { preserveScroll = false } = {}) {
  const detail = await api(`/api/chat/conversations/${id}/?all_messages=1`);
  detail.messages = sortMessagesForDisplay(detail.messages || []);
  syncMessagePagination(id, detail.message_pagination);
  ChatCache.setDetail(id, detail);
  if (state.currentId !== id) return detail;

  applyConversationHeader(detail);
  state.currentConvHasMessages = Boolean((detail.messages || []).length);
  state.currentConvIsShared = Boolean(detail.is_shared || detail.shared_by_label);
  updateShareChatButtonState();
  ChatCache.clearThreadFragment(id);
  renderMessages(detail.messages || [], { preserveScroll });
  return detail;
}

async function selectConversation(id) {
  if (state.currentId && state.currentId !== id) {
    parkCurrentConversation();
  }

  state.currentId = id;
  const convRow = state.conversations.find((c) => c.id === id);
  state.currentConvIsShared = conversationIsSharedCopy(convRow);
  updateShareChatButtonState();
  persistCurrentConversationId();
  renderConvList();
  hideGenProgressIfIdle();

  const messagesEl = document.getElementById("messages");
  messagesEl.innerHTML = "";
  updateEmptyState(false);
  beginThreadPrepare();

  const cachedRow = ChatCache.getDetail(id);
  if (cachedRow?.detail?.messages?.length && !ChatCache.isDetailStale(id)) {
    applyConversationHeader(cachedRow.detail);
    syncMessagePagination(id, cachedRow.detail.message_pagination);
    state.currentConvHasMessages = Boolean((cachedRow.detail.messages || []).length);
    state.currentConvIsShared = Boolean(
      cachedRow.detail.is_shared || cachedRow.detail.shared_by_label
    );
    updateShareChatButtonState();
    renderMessages(cachedRow.detail.messages || []);
    await resumeWatchersForThread(messagesEl);
    return;
  }

  await loadConversationDetail(id);
}

async function newConversation() {
  const conv = await api("/api/chat/conversations/", { method: "POST", body: "{}" });
  state.conversations.unshift(conv);
  state.currentConvHasMessages = false;
  state.currentConvIsShared = false;
  await selectConversation(conv.id);
  updateShareChatButtonState();
  scrollThreadToLatest();
  document.getElementById("prompt-input").focus();
}

async function streamChat(content) {
  const body = appendMessageDom({ role: "assistant", content: "" });
  let textEl = body.querySelector(".msg-text");
  if (!textEl) {
    textEl = document.createElement("div");
    textEl.className = "msg-text md-body";
    body.appendChild(textEl);
  }
  body.classList.add("streaming");
  let streamText = "";

  const res = await fetch(`/api/chat/conversations/${state.currentId}/chat/stream/`, {
    method: "POST",
    credentials: "same-origin",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": getCookie("csrftoken"),
    },
    body: JSON.stringify({
      content,
      attachment_ids: state.attachments.map((a) => a.id),
      chat_model: state.chatModel,
      vision_model: state.visionModel,
    }),
  });
  if (!res.ok) throw new Error("流式聊天失败");

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split("\n\n");
    buffer = parts.pop();
    for (const part of parts) {
      if (!part.startsWith("data: ")) continue;
      const payload = JSON.parse(part.slice(6));
      if (payload.type === "token") {
        streamText += payload.content;
        setMessageContent(textEl, streamText, "assistant");
        scrollThreadToBottom();
      } else if (payload.type === "done") {
        body.classList.remove("streaming");
        ChatCache.invalidateConversation(state.currentId);
        await loadConversations();
        const t = payload.message?.content;
        if (t) setMessageContent(textEl, t, "assistant");
        loadConversationDetail(state.currentId).catch(() => {});
      } else if (payload.type === "error") {
        body.classList.remove("streaming");
        setMessageContent(textEl, "出错了：" + payload.content, "assistant");
      }
    }
  }
  body.classList.remove("streaming");
}

function watchGeneration(jobId, convId = state.currentId) {
  if (!convId || convId !== state.currentId) return;
  const existing = state.genWatchers[jobId];
  if (existing?.convId === convId && !existing.done) return;

  stopGenerationWatch(jobId);

  const watcher = { pollTimer: null, es: null, done: false, convId };
  state.genWatchers[jobId] = watcher;

  pollGenerationJob(jobId).catch(() => {});
  watcher.pollTimer = setInterval(() => {
    if (!isGenWatchActive(jobId)) {
      stopGenerationWatch(jobId);
      return;
    }
    pollGenerationJob(jobId).catch(() => {});
  }, GEN_POLL_INTERVAL_MS);

  const es = new EventSource(`/api/generations/${jobId}/stream/`, { withCredentials: true });
  watcher.es = es;
  state.activeGenEs = es;

  es.onmessage = (ev) => {
    if (!isGenWatchActive(jobId)) return;
    let data;
    try {
      data = JSON.parse(ev.data);
    } catch {
      return;
    }
    if (data.type === "done") {
      pollGenerationJob(jobId).catch(() => {});
      stopGenerationWatch(jobId);
      return;
    }
    if (data.job) {
      applyGenerationJobProgress(data.job);
      if (["succeeded", "failed", "cancelled"].includes(data.job.status)) {
        stopGenerationWatch(jobId);
      }
    }
  };

  es.onerror = () => {
    if (watcher.es) {
      watcher.es.close();
      watcher.es = null;
    }
  };
}

function parseImageCountFromText(text) {
  const t = userIntentSnippet(text) || String(text || "");
  const make = t.match(/制作\s*(\d{1,2})\s*[张幅个]/);
  if (make) return Math.max(1, Math.min(12, parseInt(make[1], 10)));
  const all = [...t.matchAll(/(\d{1,2})\s*[张幅个]/g)].map((m) => parseInt(m[1], 10));
  if (!all.length) return null;
  return Math.max(1, Math.min(12, Math.max(...all)));
}

function wantsEcommerceBundle(text) {
  const t = userIntentSnippet(text) || String(text || "");
  const n = parseImageCountFromText(text);
  if (n >= 2 && /生成|制作|主图|套图|详情|白底|电商图/.test(t)) return true;
  if (/主图.*白底|白底.*详情|1\+1\+7|九张|制作\s*9\s*张/.test(t)) return true;
  return false;
}

function userIntentSnippet(text) {
  let t = String(text || "").trim();
  if (!t) return "";
  const cut = t.search(
    /\n\s*(\*\*)?(Subject|Style|Shot|Setting|Scene lighting)\b|\n\s*---\s*\n|\n\s*(\*\*)?回答(\*\*)?\s*\n|图片优化建议/i
  );
  if (cut > 0) t = t.slice(0, cut).trim();
  return t.slice(0, 600);
}

function wantsImageRefine(text) {
  if (wantsEcommerceBundle(text)) return false;
  const t = userIntentSnippet(text);
  if (!t) return false;
  if (/不要生成|不用生成|无需生成|仅分析|只分析|不要出图|不用出图|仅文字|不要图|只要分析|文字建议|不用修|不要修/.test(t)) {
    return false;
  }
  if (/优化.{0,8}(文案|标题|描述|prompt|提示词)|只改文字/.test(t)) return false;
  return (
    /优化(一下)?(这张|这个|这幅|该)?(图|图片|照片|素材)/.test(t) ||
    /帮(我)?(优化|修|改|处理|调整|重塑|重制|重做)(一下)?(这张|这个|这幅|该)?(图|图片|照片)?/.test(t) ||
    /(图|图片|照片).{0,16}(优化|修图|改好|处理|重塑|重制|重做)/.test(t) ||
    /重塑(一下)?(这张|这个|这幅|该)?(图|图片|照片)?/.test(t) ||
    /ai感|AI感|去ai|去 AI|不像真人|更真实|真实感|自然一点|修图|重绘|重画|改图|真人化|去动漫|动漫感|二次元/.test(t) ||
    /人物.{0,10}(太假|很假|假|不真实)|太假了?/.test(t)
  );
}

function wantsImageGeneration(text) {
  const t = userIntentSnippet(text);
  if (!t) return false;
  if (/不要生成|不用生成|无需生成|仅分析|只分析|不要出图|不用出图|仅文字|不要图/.test(t)) {
    return false;
  }
  if (wantsImageRefine(text)) return true;
  if (/生成|制作|做.{0,8}图|出.{0,4}图|主图|套图|详情图|商品图|白底图|宣传图|电商图/.test(t)) {
    return true;
  }
  if (/制作\s*\d+\s*张/.test(t)) return true;
  if (/\d{1,2}\s*[张幅个]/.test(t) && /图/.test(t)) return true;
  return false;
}

function applyRefineFromText(text) {
  if (!wantsImageRefine(text)) return;
  const countSel = document.getElementById("image-count");
  const tplSel = document.getElementById("plan-template");
  if (countSel) countSel.value = "1";
  if (tplSel) tplSel.value = "photo_refine";
}

function applyTemplateFromText(text) {
  const tplSel = document.getElementById("plan-template");
  const countSel = document.getElementById("image-count");
  if (!tplSel) return;
  const t = String(text || "").toLowerCase();
  const isTkNine =
    /制作\s*9\s*张|九张|1\+1\+7|tiktok|tk\b|墨西哥|mexico|西语|西班牙语/.test(t) ||
    (/主图/.test(t) && /白底/.test(t) && /详情/.test(t));
  if (!isTkNine) return;
  tplSel.value = "tk_mx_ecommerce_9";
  if (countSel) countSel.value = "9";
}

async function startGeneration(prompt) {
  const imageCount = parseInt(document.getElementById("image-count").value, 10);
  const planTemplate = document.getElementById("plan-template")?.value || "auto";
  const castSkin =
    document.getElementById("cast-skin-preset")?.value || state.castSkinPreset || "caucasian";
  state.castSkinPreset = castSkin;
  try {
    localStorage.setItem("ia_cast_skin_preset", castSkin);
  } catch (_) {}

  const payload = {
    prompt,
    image_count: imageCount,
    conversation_id: state.currentId,
    image_model: state.imageModel || document.getElementById("image-model").value,
    vision_model: state.visionModel,
    plan_template: planTemplate,
    cast_skin_preset: castSkin,
  };
  const attIds = state.attachments.map((a) => a.id);
  if (attIds.length) payload.attachment_ids = attIds;

  const imageModelId =
    state.imageModel || document.getElementById("image-model")?.value || "";
  let submitMsg = "正在提交套图任务…";
  if (imageModelId) {
    submitMsg = `正在提交套图任务（生图模型：${modelLabel(state.catalog?.image_models, imageModelId) || imageModelId}）…`;
  }
  setGenProgressUi(submitMsg, { running: true });

  const job = await api("/api/generations/", {
    method: "POST",
    body: JSON.stringify(payload),
  });

  ChatCache.invalidateConversation(state.currentId);
  await loadConversationDetail(state.currentId);
  if (job.id) watchGeneration(job.id, state.currentId);
  await loadConversations();
  if (job.image_model && isJobRunning(job)) {
    const progressText =
      formatJobProgress(job) +
      ` · 模型 ${modelLabel(state.catalog?.image_models, job.image_model) || job.image_model}`;
    setGenProgressUi(progressText, { running: true, jobId: job.id });
  }
}

function setSending(on) {
  state.sending = on;
  document.getElementById("btn-send").disabled = on || !document.getElementById("prompt-input").value.trim();
}

async function sendMessage() {
  const input = document.getElementById("prompt-input");
  const text = input.value.trim();
  if (!text || state.sending) return;
  if (!state.currentId) await newConversation();

  state.currentConvHasMessages = true;
  updateShareChatButtonState();

  input.value = "";
  autoResizeTextarea();
  updateSendButton();

  setSending(true);
  try {
    const genMode = document.getElementById("mode-generate").checked;
    const hasAttachment = state.attachments.length > 0;
    const autoGen = hasAttachment && wantsImageGeneration(text);
    const runGeneration = genMode || autoGen;

    if (autoGen || wantsEcommerceBundle(text)) {
      const n = parseImageCountFromText(text);
      if (n) document.getElementById("image-count").value = String(n);
      applyTemplateFromText(text);
    }
    if (hasAttachment && wantsImageRefine(text)) {
      applyRefineFromText(text);
    }

    if (wantsImageRefine(text) && !hasAttachment) {
      alert("重塑/优化图片请先上传原图（点击 + 选择图片），再发送指令。");
      return;
    }

    if (runGeneration) {
      if (!hasAttachment) {
        alert("套图生成需要先上传参考商品图（点击 +，可多选不同色号/SKU）。");
        return;
      }
      const genMeta = {
        attachment_ids: state.attachments.map((a) => a.id),
        attachments: state.attachments.map((a) => ({
          id: a.id,
          url: a.previewUrl,
          name: a.name,
        })),
      };
      appendMessageDom({ role: "user", content: text, metadata: genMeta });
      await startGeneration(text);
      clearAttachment();
    } else {
      const meta = {};
      if (hasAttachment) {
        meta.attachments = state.attachments.map((a) => ({
          id: a.id,
          url: a.previewUrl,
          name: a.name,
        }));
        meta.attachment_ids = state.attachments.map((a) => a.id);
      }
      appendMessageDom({ role: "user", content: text, metadata: meta });
      await streamChat(text);
      if (hasAttachment) {
        clearAttachment();
      }
    }
  } catch (err) {
    alert(err.message || String(err));
  } finally {
    setSending(false);
    updateSendButton();
  }
}

function autoResizeTextarea() {
  const el = document.getElementById("prompt-input");
  el.style.height = "auto";
  el.style.height = Math.min(el.scrollHeight, 200) + "px";
}

function updateSendButton() {
  const hasText = document.getElementById("prompt-input").value.trim().length > 0;
  document.getElementById("btn-send").disabled = state.sending || !hasText;
}

function renderAttachmentPreview() {
  const row = document.getElementById("attachment-preview");
  const list = document.getElementById("attachment-preview-list");
  if (!row || !list) return;
  list.innerHTML = "";
  if (!state.attachments.length) {
    row.classList.add("hidden");
    return;
  }
  row.classList.remove("hidden");
  state.attachments.forEach((att, index) => {
    const item = document.createElement("div");
    item.className = "attachment-preview-item";
    const img = document.createElement("img");
    img.src = att.previewUrl;
    img.alt = att.name || "";
    const chip = document.createElement("span");
    chip.className = "attachment-chip";
    chip.textContent = att.name || `图 ${index + 1}`;
    const rm = document.createElement("button");
    rm.type = "button";
    rm.className = "chip-remove";
    rm.setAttribute("aria-label", "移除");
    rm.textContent = "×";
    rm.onclick = () => removeAttachmentAt(index);
    item.appendChild(img);
    item.appendChild(chip);
    item.appendChild(rm);
    list.appendChild(item);
  });
}

function removeAttachmentAt(index) {
  const att = state.attachments[index];
  if (att?.previewUrl?.startsWith("blob:")) {
    URL.revokeObjectURL(att.previewUrl);
  }
  state.attachments.splice(index, 1);
  renderAttachmentPreview();
}

function clearAttachment() {
  state.attachments.forEach((att) => {
    if (att.previewUrl?.startsWith("blob:")) URL.revokeObjectURL(att.previewUrl);
  });
  state.attachments = [];
  renderAttachmentPreview();
  document.getElementById("file-input").value = "";
}

async function addAttachmentFiles(files) {
  const incoming = Array.from(files || []).filter((f) => f && f.type?.startsWith("image/"));
  if (!incoming.length) return;
  const room = MAX_REF_IMAGES - state.attachments.length;
  if (room <= 0) {
    alert(`最多上传 ${MAX_REF_IMAGES} 张参考图`);
    return;
  }
  const batch = incoming.slice(0, room);
  if (incoming.length > batch.length) {
    alert(`已选 ${incoming.length} 张，仅添加前 ${batch.length} 张（上限 ${MAX_REF_IMAGES} 张）`);
  }
  for (const file of batch) {
    const fd = new FormData();
    fd.append("file", file);
    const data = await api("/api/uploads/", { method: "POST", body: fd });
    state.attachments.push({
      id: data.id,
      name: data.original_name || file.name || "图片",
      previewUrl: URL.createObjectURL(file),
    });
  }
  renderAttachmentPreview();
  document.getElementById("tools-panel")?.classList.remove("hidden");
}

function openSidebarMobile() {
  document.getElementById("sidebar").classList.add("open");
  document.getElementById("sidebar-backdrop").classList.remove("hidden");
}

function closeSidebarMobile() {
  document.getElementById("sidebar").classList.remove("open");
  document.getElementById("sidebar-backdrop").classList.add("hidden");
}

function isMobileSidebarLayout() {
  return window.matchMedia("(max-width: 768px)").matches;
}

function setSidebarCollapsed(collapsed) {
  document.querySelector(".app-shell")?.classList.toggle("sidebar-collapsed", collapsed);
  try {
    sessionStorage.setItem("ia_sidebar_collapsed", collapsed ? "1" : "0");
  } catch (_) {
    /* ignore */
  }
}

function toggleSidebarCollapsed() {
  if (isMobileSidebarLayout()) {
    closeSidebarMobile();
    return;
  }
  const shell = document.querySelector(".app-shell");
  setSidebarCollapsed(!shell?.classList.contains("sidebar-collapsed"));
}

function openSidebarFromCollapsed() {
  if (isMobileSidebarLayout()) {
    openSidebarMobile();
    return;
  }
  setSidebarCollapsed(false);
}

function toggleConvSearchPanel() {
  const wrap = document.getElementById("sidebar-search-wrap");
  const input = document.getElementById("conv-search-input");
  if (!wrap || !input) return;
  state.convSearchOpen = !state.convSearchOpen;
  wrap.classList.toggle("hidden", !state.convSearchOpen);
  if (state.convSearchOpen) {
    input.focus();
  } else {
    state.convSearchQuery = "";
    input.value = "";
    renderConvList();
  }
}

function toggleToolsPanel() {
  document.getElementById("tools-panel").classList.toggle("hidden");
}

function toggleUserMenu() {
  const dd = document.getElementById("user-dropdown");
  const open = dd.classList.toggle("hidden");
  document.getElementById("btn-user-menu").setAttribute("aria-expanded", String(!open));
}

document.getElementById("thread-container")?.addEventListener(
  "scroll",
  () => {
    clearTimeout(state._scrollLoadOlderTimer);
    state._scrollLoadOlderTimer = setTimeout(onThreadScrollNearTop, 120);
  },
  { passive: true }
);

document.getElementById("btn-send").onclick = () => sendMessage().catch(alert);
document.getElementById("prompt-input").addEventListener("input", () => {
  autoResizeTextarea();
  updateSendButton();
});
document.getElementById("prompt-input").addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    sendMessage().catch(alert);
  }
});
document.getElementById("btn-new-chat").onclick = () => {
  newConversation().catch(alert);
  closeSidebarMobile();
};
document.getElementById("btn-logout").onclick = async () => {
  await api("/api/auth/logout/", { method: "POST", body: "{}" });
  window.location.href = "/login/";
};
document.getElementById("btn-admin-approvals")?.addEventListener("click", (e) => {
  e.stopPropagation();
  openAdminApprovalsModal();
});
document.getElementById("btn-admin-users")?.addEventListener("click", (e) => {
  e.stopPropagation();
  openAdminUsersModal();
});
document.getElementById("btn-share-chat")?.addEventListener("click", () => openShareChatModal());
document.querySelectorAll("[data-share-close]").forEach((el) => {
  el.addEventListener("click", closeShareChatModal);
});
document.getElementById("share-user-search")?.addEventListener("input", (e) => {
  state.shareUserSearch = e.target.value;
  clearTimeout(state.shareUserSearchTimer);
  state.shareUserSearchTimer = setTimeout(() => {
    loadShareableUsers().catch((err) => alert(err.message));
  }, 300);
});
document.getElementById("share-user-list")?.addEventListener("click", (e) => {
  const btn = e.target.closest("[data-share-to]");
  if (!btn) return;
  const userId = Number(btn.dataset.shareTo);
  if (!userId) return;
  btn.disabled = true;
  shareCurrentConversationWith(userId).catch((err) => {
    alert(err.message);
    btn.disabled = false;
  });
});
document.getElementById("admin-approvals-list")?.addEventListener("click", (e) => {
  const approve = e.target.closest("[data-approve-id]");
  const reject = e.target.closest("[data-reject-id]");
  if (approve) approveRegistration(Number(approve.dataset.approveId)).catch((err) => alert(err.message));
  if (reject) rejectRegistration(Number(reject.dataset.rejectId)).catch((err) => alert(err.message));
});
document.getElementById("admin-users-list")?.addEventListener("click", (e) => {
  const save = e.target.closest("[data-save-user]");
  if (!save) return;
  const row = save.closest(".admin-user-row");
  if (!row) return;
  saveAdminUser(Number(save.dataset.saveUser), row).catch((err) => alert(err.message));
});
document.getElementById("admin-users-search")?.addEventListener("input", (e) => {
  state.adminUsers.q = e.target.value;
  state.adminUsers.page = 1;
  clearTimeout(state.adminUsersSearchTimer);
  state.adminUsersSearchTimer = setTimeout(() => {
    loadAdminUsers().catch((err) => alert(err.message));
  }, 320);
});
document.getElementById("admin-users-active-filter")?.addEventListener("change", (e) => {
  state.adminUsers.isActive = e.target.value;
  state.adminUsers.page = 1;
  loadAdminUsers().catch((err) => alert(err.message));
});
document.getElementById("admin-users-prev")?.addEventListener("click", () => {
  if (state.adminUsers.page <= 1) return;
  state.adminUsers.page -= 1;
  loadAdminUsers().catch((err) => alert(err.message));
});
document.getElementById("admin-users-next")?.addEventListener("click", () => {
  if (state.adminUsers.page >= state.adminUsers.totalPages) return;
  state.adminUsers.page += 1;
  loadAdminUsers().catch((err) => alert(err.message));
});
document.querySelectorAll("[data-admin-close]").forEach((el) => {
  el.addEventListener("click", () => closeAdminModal(el.dataset.adminClose));
});
document.getElementById("user-dropdown")?.addEventListener("click", (e) => e.stopPropagation());
document.getElementById("btn-user-menu").onclick = (e) => {
  e.stopPropagation();
  toggleUserMenu();
};
document.addEventListener("click", () => {
  document.getElementById("user-dropdown").classList.add("hidden");
  document.getElementById("btn-user-menu").setAttribute("aria-expanded", "false");
  closeModelPicker();
  closeAllConvMenus();
});
document.getElementById("btn-sidebar-open").onclick = openSidebarFromCollapsed;
document.getElementById("btn-sidebar-collapse").onclick = toggleSidebarCollapsed;
document.getElementById("sidebar-backdrop").onclick = closeSidebarMobile;
document.getElementById("btn-conv-search").onclick = (e) => {
  e.stopPropagation();
  toggleConvSearchPanel();
};
document.getElementById("conv-search-input")?.addEventListener("input", (e) => {
  state.convSearchQuery = e.target.value;
  renderConvList();
});
document.getElementById("btn-tools").onclick = toggleToolsPanel;
document.getElementById("model-selector").onclick = toggleModelPicker;
document.getElementById("model-picker-wrap")?.addEventListener("click", (e) => e.stopPropagation());
document.getElementById("image-model")?.addEventListener("change", (e) => {
  selectImageModel(e.target.value).catch(alert);
});
document.getElementById("btn-pick-file").onclick = () => document.getElementById("file-input").click();
document.getElementById("btn-clear-attachment").onclick = clearAttachment;

function onLightboxBackdropClick() {
  if (document.getElementById("image-lightbox")?.classList.contains("is-preview-zoomed")) {
    setLightboxPreviewZoom(false);
    return;
  }
  closeImageLightbox();
}

document.getElementById("lightbox-close")?.addEventListener("click", closeImageLightbox);
document.getElementById("lightbox-backdrop")?.addEventListener("click", onLightboxBackdropClick);
document.getElementById("lightbox-img")?.addEventListener("click", (e) => {
  e.stopPropagation();
  const stage = e.currentTarget.closest(".lightbox-preview-stage");
  if (stage) stage.classList.toggle("is-zoomed");
});
document.getElementById("lightbox-refine-submit")?.addEventListener("click", () => {
  submitLightboxRefine().catch((e) => setLightboxRefineStatus(e.message, true));
});
document.getElementById("lightbox-download-all")?.addEventListener("click", () => {
  downloadAllLightboxImages().catch((e) => alert(e.message || "下载失败"));
});
document.getElementById("lightbox-apply")?.addEventListener("click", () => {
  applyLightboxRefine().catch(alert);
});
document.getElementById("lightbox-keep")?.addEventListener("click", () => {
  keepOriginalLightboxImage().catch(() => {});
});
document.getElementById("lightbox-retry")?.addEventListener("click", () => retryLightboxRefine());
document.addEventListener("keydown", (e) => {
  if (e.key !== "Escape") return;
  const box = document.getElementById("image-lightbox");
  if (!box || box.classList.contains("hidden")) return;
  if (box.classList.contains("is-preview-zoomed")) {
    setLightboxPreviewZoom(false);
    return;
  }
  closeImageLightbox();
});

document.getElementById("file-input").addEventListener("change", async (e) => {
  const files = e.target.files;
  if (!files?.length) return;
  try {
    await addAttachmentFiles(files);
  } catch (err) {
    alert(err.message);
  } finally {
    e.target.value = "";
  }
});

document.querySelector(".gen-cancel-btn")?.addEventListener("click", (e) => {
  const btn = e.currentTarget;
  const jobId = Number(btn.dataset.jobId);
  if (!jobId) return;
  btn.disabled = true;
  const textEl = btn.querySelector(".gen-cancel-btn-text");
  if (textEl) textEl.textContent = "正在停止…";
  cancelGenerationJob(jobId);
});

(async function init() {
  if ("scrollRestoration" in history) {
    history.scrollRestoration = "manual";
  }
  try {
    if (sessionStorage.getItem("ia_sidebar_collapsed") === "1" && !isMobileSidebarLayout()) {
      setSidebarCollapsed(true);
    }
  } catch (_) {
    /* ignore */
  }
  await ensureCsrf();
  await loadPreferences();
  await loadUser();
  try {
    const savedSkin = localStorage.getItem("ia_cast_skin_preset");
    if (savedSkin && ["caucasian", "diverse", "black_only"].includes(savedSkin)) {
      state.castSkinPreset = savedSkin;
      const skinSel = document.getElementById("cast-skin-preset");
      if (skinSel) skinSel.value = savedSkin;
    }
  } catch (_) {}
  updateModelUI();
  beginThreadPrepare();
  await loadConversations();
  const initialId = resolveInitialConversationId();
  if (initialId) {
    await selectConversation(initialId);
  } else if (state.conversations.length) {
    await selectConversation(state.conversations[0].id);
  } else {
    await newConversation();
    updateEmptyState(false);
  }
  autoResizeTextarea();
  updateSendButton();
})();
