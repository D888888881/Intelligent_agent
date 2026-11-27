const BOT_AVATAR_SVG = `<svg viewBox="0 0 41 41" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M37.532 16.87a9.963 9.963 0 0 0-.856-8.184 10.078 10.078 0 0 0-10.855-4.835 9.964 9.964 0 0 0-7.065-2.937 10.078 10.078 0 0 0-9.52 6.886 9.967 9.967 0 0 0-6.664 4.835 10.079 10.079 0 0 0 1.24 11.817 9.965 9.965 0 0 0 .856 8.185 10.079 10.079 0 0 0 10.855 4.835 9.964 9.964 0 0 0 7.065 2.937 10.078 10.078 0 0 0 9.52-6.886 9.965 9.965 0 0 0 6.664-4.835 10.079 10.079 0 0 0-1.24-11.817z" fill="#fff"/></svg>`;

const IA_CHAT = window.IA_CHAT || {};
const MESSAGE_INITIAL_SIZE = Number(IA_CHAT.initialMessageLimit) || 10;
const MESSAGE_OLDER_PAGE_SIZE = Number(IA_CHAT.olderMessagePageSize) || 10;
const MAX_REF_IMAGES = Number(IA_CHAT.maxReferenceImages) || 8;
const GEN_POLL_INTERVAL_MS = 1500;
/** 终态后单镜仍无 URL（落盘/对齐滞后）时独立拉图，不依赖 genWatchers */
const GALLERY_SYNC_INTERVAL_MS = 2000;
const GALLERY_SYNC_MAX_TICKS = 180;
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
  planPreviewNotified: {},
  /** 策划预览仅自动锚定滚动一次，避免用户阅读长文案时被反复拽回 */
  planConfirmAnchored: {},
  /** 点击「开始生图」后下一次进度更新前再锚定到该 job 视口 */
  genFollowScrollJobId: null,
  /** 确认生图进行中：阻止全量 loadConversationDetail 抢滚动 */
  confirmingGenJobId: null,
  /** 点击开始生图时锁定 thread scrollTop，避免进度更新把视口拉走 */
  threadScrollLockTop: null,
  threadScrollLockUntil: 0,
  /** 生图确认后短时间内禁止自动贴底/重载抢滚动 */
  generationScrollPinJobId: null,
  generationScrollPinUntil: 0,
  /** 用户手动滚动后不再把视口拽回生图消息 */
  genScrollFollowPaused: false,
  /** 当前会话用户关注的生图 job（完成时优先锚定） */
  focusGenJobId: null,
  /** 已处理终态的 job，避免 SSE+轮询重复全量重绘 */
  genTerminalHandled: {},
  /** 终态后收尾拉图：抑制反复锚定滚动 */
  genGallerySettling: null,
  genFinishWatchActive: {},
  /** jobId -> { timer, ticks, convId } */
  gallerySyncPolls: {},
  genReanchorTimers: {},
  /** endThreadPrepare 延迟贴底，切换/锚定前需清除 */
  threadPrepareScrollTimerIds: [],
  sending: false,
  chatModel: "",
  imageModel: "",
  visionModel: "",
  catalog: null,
  marketplaceId: "tk_shop_mx",
  convSearchQuery: "",
  convSearchOpen: false,
  lightboxRefine: null,
  /** 局部修复「新上传参考」：按上传顺序的 Attachment 列表 */
  lightboxRefineUploads: [],
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
  adminUsage: {
    period: "day",
    anchor: "",
    q: "",
    page: 1,
    pageSize: 20,
    totalPages: 1,
    count: 0,
  },
  adminUsageSearchTimer: null,
  shareUserSearch: "",
  shareUserSearchTimer: null,
  currentConvHasMessages: false,
  currentConvIsShared: false,
  /** 当前选中的 Listing 快捷话术 marketplace_id */
  listingPromptPresetId: null,
  aspectRatio: "1:1",
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
  stopAllGallerySyncPolls();
  hideGenProgressIfIdle();
}

function stopGallerySyncPoll(jobId) {
  const p = state.gallerySyncPolls[jobId];
  if (!p) return;
  if (p.timer) clearInterval(p.timer);
  delete state.gallerySyncPolls[jobId];
}

function stopAllGallerySyncPolls() {
  Object.keys(state.gallerySyncPolls).forEach((id) => stopGallerySyncPoll(Number(id)));
}

function stopGallerySyncPollsForThread(box) {
  if (!box) return;
  jobIdsInThread(box).forEach((id) => stopGallerySyncPoll(id));
}

async function tickGallerySyncPoll(jobId) {
  const poll = state.gallerySyncPolls[jobId];
  if (!poll) return;
  if (poll.convId !== state.currentId) {
    stopGallerySyncPoll(jobId);
    return;
  }
  poll.ticks = (poll.ticks || 0) + 1;
  if (poll.ticks > GALLERY_SYNC_MAX_TICKS) {
    stopGallerySyncPoll(jobId);
    return;
  }
  let job = null;
  try {
    job = await api(`/api/generations/${jobId}/`);
    ChatCache.setJob(jobId, job);
  } catch (_) {
    return;
  }
  if (!state.gallerySyncPolls[jobId]) return;
  if (jobBelongsToActiveConversation(job)) {
    updateJobInChat(job, { skipScroll: true });
  }
  if (!jobGalleryNeedsRefresh(job)) {
    stopGallerySyncPoll(jobId);
    if (jobBelongsToActiveConversation(job)) {
      updateJobInChat(job, { skipScroll: false });
    }
  }
}

/** 任务已终态但画廊仍缺 URL 时持续 reconcile+刷新 DOM（不整页 reload） */
function startGallerySyncPoll(jobId, convId = state.currentId) {
  if (!jobId || !convId) return;
  const cached = ChatCache.getJob(jobId);
  if (cached && !jobGalleryNeedsRefresh(cached)) return;
  const existing = state.gallerySyncPolls[jobId];
  if (existing?.convId === convId && existing.timer) return;
  stopGallerySyncPoll(jobId);
  state.gallerySyncPolls[jobId] = { timer: null, ticks: 0, convId };
  void tickGallerySyncPoll(jobId);
  state.gallerySyncPolls[jobId].timer = setInterval(() => {
    void tickGallerySyncPoll(jobId);
  }, GALLERY_SYNC_INTERVAL_MS);
}

function isJobRunning(job) {
  return job && !["succeeded", "failed", "cancelled"].includes(job.status);
}

function isJobActivelyGenerating(job) {
  if (!isJobRunning(job)) return false;
  const plan = job.plan_json || {};
  if (job.status === "pending" && plan.awaiting_generation_confirm) return false;
  return true;
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

/** 回到该会话：恢复进行中的轮询；视口内画廊可立即拉一次进度 */
async function resumeWatchersForThread(box, options = {}) {
  const forceAll = !!options.forceAll;
  if (!state.currentId || !box) return;
  LazyMedia.scan(box);
  for (const jobId of jobIdsInThread(box)) {
    const body = box.querySelector(`[data-generation-job="${jobId}"]`);
    if (!body) continue;
    const statusEl = body.querySelector(".gen-status-line");
    const gridEl = body.querySelector(".gallery");

    if (forceAll) {
      try {
        const job = await api(`/api/generations/${jobId}/`);
        ChatCache.setJob(jobId, job);
        updateJobInChat(job);
        if (jobGalleryNeedsRefresh(job)) {
          startGallerySyncPoll(jobId, state.currentId);
        }
        if (isJobRunning(job) && !jobAwaitingPlanConfirm(job)) {
          watchGeneration(jobId, state.currentId);
          const ui = getGenProgressUi();
          if (ui?.label) {
            setGenProgressUi(formatJobProgress(job), { running: true, jobId });
          }
        } else if (jobGalleryNeedsRefresh(job)) {
          void finishGenerationWatchWhenReady(jobId);
        }
      } catch (_) {
        /* ignore */
      }
      continue;
    }

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

function clearThreadPrepareScrollTimers() {
  for (const id of state.threadPrepareScrollTimerIds || []) {
    clearTimeout(id);
  }
  state.threadPrepareScrollTimerIds = [];
}

function beginThreadPrepare() {
  clearThreadPrepareScrollTimers();
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
  container?.classList.remove("thread-preparing");
  if (isThreadScrollLocked()) {
    finishThreadPrepare();
    enforceThreadScrollLock();
    return;
  }
  if (isGenerationScrollPinned()) {
    finishThreadPrepare();
    const jid = state.generationScrollPinJobId ?? state.focusGenJobId;
    if (jid && !isJobDomUpdateFrozen(jid)) scrollToGenerationJobTurn(jid);
    else scrollThreadToBottom({ force: true });
    return;
  }
  if (!container) {
    finishThreadPrepare();
    return;
  }

  scrollThreadToBottom({ force: true });
  let attempts = 0;
  const tryAnchor = () => {
    scrollThreadToBottom({ force: true });
    attempts += 1;
    if (isThreadAnchored() || attempts >= 12) {
      scrollThreadToBottom({ force: true });
      finishThreadPrepare();
      armStickToBottom();
      return;
    }
    requestAnimationFrame(tryAnchor);
  };
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
  if (shouldBlockThreadFullReload() && !options.forceFullRender) {
    return;
  }
  const stickToBottom = !!options.stickToBottom;
  const preserveScroll = !!options.preserveScroll && !stickToBottom;
  const anchorJobId =
    !stickToBottom && options.anchorGenerationJobId
      ? Number(options.anchorGenerationJobId)
      : null;
  if (anchorJobId && !isThreadScrollLocked()) {
    pinScrollToGenerationJob(anchorJobId, 4, 180000);
  }
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
  if (preserveScroll && !anchorJobId) {
    finishThreadPrepare();
    if (container) {
      markProgrammaticThreadScroll();
      container.scrollTop = prevScroll + (container.scrollHeight - prevHeight);
    }
  } else if (anchorJobId) {
    finishThreadPrepare();
    scrollToGenerationJobTurn(anchorJobId);
  } else {
    endThreadPrepare();
  }
  void resumeWatchersForThread(box, { forceAll: true });
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

  if (role === "assistant" && m.metadata?.planning_summary && !messageAwaitingPlanConfirm(m)) {
    const summaryMd = String(m.metadata.planning_summary);
    if (summaryMd.trim()) {
      const actions = document.createElement("div");
      actions.className = "gen-plan-actions";
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "gen-plan-btn";
      btn.textContent = "查看策划摘要";
      btn.onclick = () => {
        const box = turn.querySelector(".msg-plan-summary");
        if (box) {
          box.classList.toggle("hidden");
          btn.textContent = box.classList.contains("hidden") ? "查看策划摘要" : "收起策划摘要";
          return;
        }
        const detail = document.createElement("div");
        detail.className = "msg-text msg-plan-summary";
        setMessageContent(detail, summaryMd, "assistant");
        body.appendChild(detail);
        btn.textContent = "收起策划摘要";
      };
      actions.appendChild(btn);
      body.appendChild(actions);
    }
  }

  if (m.metadata?.generation_job_id) {
    const jobId = m.metadata.generation_job_id;
    body.dataset.generationJob = String(jobId);
    const awaitingPlan = messageAwaitingPlanConfirm(m);
    const phase = m.metadata.generation_phase || "pending";
    const running =
      !awaitingPlan && !["succeeded", "failed", "cancelled"].includes(phase);
    const status = document.createElement("div");
    status.className = "gen-status-line" + (running ? " shimmer" : "");
    if (awaitingPlan) {
      status.textContent = `策划完成，待确认生图 · 0/${m.metadata.image_count || 9} 张 · 任务 #${jobId}`;
    } else {
      const cachedJob = ChatCache.getJob(jobId);
      if (cachedJob) {
        status.textContent = formatJobProgress(cachedJob);
      } else {
        status.textContent = formatJobProgress({
          id: jobId,
          status: phase,
          completed_count: m.metadata.completed_count || 0,
          image_count: m.metadata.image_count || 9,
          queue_position: m.metadata.queue_position,
          plan_json: {},
        });
      }
    }
    body.appendChild(status);
    if (awaitingPlan) {
      attachPlanConfirmActions(body, Number(jobId), null);
    }
    const grid = document.createElement("div");
    grid.className = "gallery";
    grid.dataset.jobGallery = String(jobId);
    body.appendChild(grid);
    LazyMedia.observeJobGallery(grid);
    if (!state.threadAnchoring && LazyMedia.isInViewport(grid)) {
      window.onGalleryEnterViewport?.(jobId, grid, status);
    }
  } else if (m.metadata?.generation_snapshot) {
    const snap = m.metadata.generation_snapshot;
    const snapJobId = Number(m.metadata.generation_job_id) || 0;
    if (snapJobId) body.dataset.generationJob = String(snapJobId);
    const status = document.createElement("div");
    status.className = "gen-status-line";
    const imageCount = snap.image_count || (snap.images || []).length || 9;
    status.textContent = formatJobProgress({
      id: snapJobId || 0,
      status: snap.status || "succeeded",
      completed_count: snap.completed_count ?? (snap.images || []).filter((x) => x.url).length,
      image_count: imageCount,
    });
    body.appendChild(status);
    const grid = document.createElement("div");
    grid.className = "gallery";
    grid.dataset.generationSnapshot = "1";
    if (snapJobId) grid.dataset.jobGallery = String(snapJobId);
    body.appendChild(grid);
    renderGalleryFromJob(
      {
        id: snapJobId || 0,
        image_count: imageCount,
        status: snap.status || "succeeded",
        completed_count: snap.completed_count || 0,
        images: snap.images || [],
      },
      grid
    );
    LazyMedia.scan(grid);
  }

  return turn;
}

function prependMessagesDom(messages) {
  const box = document.getElementById("messages");
  const container = document.getElementById("thread-container");
  if (!box || !messages?.length) return;
  const existing = new Set(
    [...box.querySelectorAll(".turn[data-message-id]")].map((el) => el.dataset.messageId)
  );
  const fresh = messages.filter((m) => m.id == null || !existing.has(String(m.id)));
  if (!fresh.length) return;
  const prevHeight = container.scrollHeight;
  const sentinel = box.querySelector("#load-older-sentinel");
  const anchor = sentinel ? sentinel.nextSibling : box.firstChild;
  for (const message of fresh) {
    box.insertBefore(buildMessageTurn(message), anchor);
  }
  box.dataset.expandedOlder = "1";
  markProgrammaticThreadScroll();
  container.scrollTop += container.scrollHeight - prevHeight;
  LazyMedia.scan(box);
  updateLoadOlderSentinel();
}

async function loadOlderMessages() {
  const convId = state.currentId;
  if (!convId || state.loadingOlder) return;
  const page = state.messagePage[convId];
  if (!page?.has_more_older || !page.oldest_message_id) return;

  state.loadingOlder = true;
  page.loadingOlder = true;
  updateLoadOlderSentinel();

  try {
    const detail = await api(
      `/api/chat/conversations/${convId}/?before_id=${page.oldest_message_id}&limit=${MESSAGE_OLDER_PAGE_SIZE}`
    );
    if (state.currentId !== convId) return;
    const older = sortMessagesForDisplay(detail.messages || []);
    const info = detail.message_pagination || {};
    state.messagePage[convId] = {
      has_more_older: Boolean(info.has_more_older) && older.length > 0,
      oldest_message_id: older[0]?.id || page.oldest_message_id,
      newest_message_id: page.newest_message_id,
      limit: info.limit || MESSAGE_OLDER_PAGE_SIZE,
      loadingOlder: false,
    };
    const cached = ChatCache.getDetail(convId)?.detail;
    if (cached) {
      cached.messages = sortMessagesForDisplay([...(cached.messages || []), ...older]);
      cached.message_pagination = { ...state.messagePage[convId] };
      ChatCache.setDetail(convId, cached);
    }
    prependMessagesDom(older);
  } finally {
    state.loadingOlder = false;
    if (state.messagePage[convId]) state.messagePage[convId].loadingOlder = false;
    updateLoadOlderSentinel();
  }
}

function onThreadScrollNearTop() {
  if (state.threadAnchoring || isGenerationScrollPinned()) return;
  const container = document.getElementById("thread-container");
  if (!container || container.scrollTop > 80) return;
  if (container.scrollHeight <= container.clientHeight + 8) return;
  loadOlderMessages().catch(() => {});
}

function isGenerationScrollPinned() {
  return (
    state.generationScrollPinUntil &&
    Date.now() < state.generationScrollPinUntil &&
    state.generationScrollPinJobId != null
  );
}

function isThreadScrollLocked() {
  return Boolean(state.threadScrollLockUntil && Date.now() < state.threadScrollLockUntil);
}

/** 仅在提交后极短时间内防止程序性滚动抢位；不阻止用户手动滑屏 */
function preserveThreadScroll(ms = 1500) {
  const container = document.getElementById("thread-container");
  if (!container) return;
  state.threadScrollLockTop = container.scrollTop;
  state.threadScrollLockUntil = Date.now() + ms;
}

function beginThreadScrollLock(jobId, { markConfirming = false, scrollBurstMs = 1500 } = {}) {
  const container = document.getElementById("thread-container");
  if (!container) return;
  state.genScrollFollowPaused = false;
  state.threadScrollLockTop = container.scrollTop;
  state.threadScrollLockUntil = Date.now() + scrollBurstMs;
  if (jobId) {
    state.focusGenJobId = jobId;
    state.generationScrollPinJobId = jobId;
    state.generationScrollPinUntil = Date.now() + 120000;
    if (markConfirming) state.confirmingGenJobId = jobId;
  }
}

function markProgrammaticThreadScroll() {
  state._threadScrollProgrammatic = true;
  clearTimeout(state._progScrollTimer);
  state._progScrollTimer = setTimeout(() => {
    state._threadScrollProgrammatic = false;
  }, 120);
}

function pauseGenerationScrollFollow() {
  if (state._threadScrollProgrammatic) return;
  state.genScrollFollowPaused = true;
  releaseOpenThreadStick();
  clearThreadScrollLock();
}

function releaseThreadScrollLockFromUser() {
  pauseGenerationScrollFollow();
}

/** 发送生图后：把本地乐观用户气泡与后端 user_message 对齐，避免再全量拉会话 */
function syncServerUserMessage(msg) {
  if (!msg) return;
  const box = document.getElementById("messages");
  if (!box) return;
  if (msg.id != null) {
    const existing = box.querySelector(`.turn-user[data-message-id="${msg.id}"]`);
    if (existing) return;
  }
  const userTurns = [...box.querySelectorAll(".turn-user")];
  const last = userTurns[userTurns.length - 1];
  if (last && !last.dataset.messageId) {
    if (msg.id != null) last.dataset.messageId = String(msg.id);
    const textEl = last.querySelector(".msg-text");
    if (textEl && msg.content) setMessageContent(textEl, msg.content, "user");
    return;
  }
  if (msg.id != null && !box.querySelector(`.turn-user[data-message-id="${msg.id}"]`)) {
    appendMessageDom(msg, false);
  }
}

function mergeServerMessagesIntoCache(convId, userMsg, assistantMsg) {
  if (!convId) return;
  const row = ChatCache.getDetail(convId);
  if (!row?.detail) return;
  const list = sortMessagesForDisplay(row.detail.messages || []);
  const byId = new Map(list.filter((m) => m.id != null).map((m) => [m.id, m]));
  for (const m of [userMsg, assistantMsg]) {
    if (m?.id != null) byId.set(m.id, m);
  }
  row.detail.messages = sortMessagesForDisplay([...byId.values()]);
  ChatCache.setDetail(convId, row.detail);
}

function clearThreadScrollLock() {
  state.threadScrollLockTop = null;
  state.threadScrollLockUntil = 0;
}

function clearGenerationScrollPin(jobId) {
  if (jobId == null) return;
  if (Number(state.generationScrollPinJobId) === Number(jobId)) {
    state.generationScrollPinJobId = null;
    state.generationScrollPinUntil = 0;
  }
  if (Number(state.focusGenJobId) === Number(jobId)) {
    state.focusGenJobId = null;
  }
  if (Number(state.genFollowScrollJobId) === Number(jobId)) {
    delete state.genFollowScrollJobId;
  }
}

function scheduleGalleryLayoutReanchor(jobId) {
  if (!jobId) return;
  if (Number(state.genGallerySettling) === Number(jobId)) return;
  const key = String(jobId);
  if (state.genReanchorTimers[key]) return;
  state.genReanchorTimers[key] = window.setTimeout(() => {
    delete state.genReanchorTimers[key];
    maybeReanchorGenerationJobTurn(jobId);
  }, 160);
}

function enforceThreadScrollLock() {
  if (state.genScrollFollowPaused) return;
  if (!isThreadScrollLocked()) return;
  const container = document.getElementById("thread-container");
  if (!container || state.threadScrollLockTop == null) return;
  if (Math.abs(container.scrollTop - state.threadScrollLockTop) > 1) {
    markProgrammaticThreadScroll();
    container.style.scrollBehavior = "auto";
    container.scrollTop = state.threadScrollLockTop;
    container.style.scrollBehavior = "";
  }
}

function isJobDomUpdateFrozen(jobId) {
  return (
    (state.confirmingGenJobId && Number(state.confirmingGenJobId) === Number(jobId)) ||
    (isThreadScrollLocked() &&
      state.generationScrollPinJobId != null &&
      Number(state.generationScrollPinJobId) === Number(jobId))
  );
}

function hasActiveGenWatcherOnCurrentConv() {
  if (!state.currentId) return false;
  for (const w of Object.values(state.genWatchers)) {
    if (w?.convId === state.currentId && !w.done) return true;
  }
  return false;
}

function shouldBlockThreadFullReload() {
  return Boolean(state.confirmingGenJobId || hasActiveGenWatcherOnCurrentConv());
}

function generationJobTurnIsLatest(jobId) {
  const body = primaryGenerationJobBody(jobId);
  const turn = body?.closest(".turn");
  const lastTurn = document.getElementById("messages")?.querySelector(".turn:last-of-type");
  return !!(turn && lastTurn && turn === lastTurn);
}

function scrollThreadToBottom({ force = false } = {}) {
  if (!force) {
    if (state.genScrollFollowPaused) return;
    if (state.threadAnchoring || isThreadScrollLocked()) return;
    if (
      isGenerationScrollPinned() &&
      !generationJobTurnIsLatest(state.generationScrollPinJobId)
    ) {
      return;
    }
  }
  const container = document.getElementById("thread-container");
  if (!container) return;
  markProgrammaticThreadScroll();
  container.style.scrollBehavior = "auto";
  container.scrollTop = maxThreadScrollTop();
  container.style.scrollBehavior = "";
}

function releaseOpenThreadStick() {
  state.openThreadStickBottomUntil = 0;
  state._stickBottomObserver?.disconnect();
  state._stickBottomObserver = null;
  clearTimeout(state._stickBottomTimer);
}

/** 打开会话后短时间内贴住底部，图片撑开高度时也保持在最底下。 */
function armStickToBottom() {
  state.openThreadStickBottomUntil = Date.now() + 1600;
  scrollThreadToBottom({ force: true });
  const box = document.getElementById("messages");
  if (!box) return;
  state._stickBottomObserver?.disconnect();
  const observer = new ResizeObserver(() => {
    if (!state.openThreadStickBottomUntil || Date.now() > state.openThreadStickBottomUntil) {
      releaseOpenThreadStick();
      return;
    }
    scrollThreadToBottom({ force: true });
  });
  observer.observe(box);
  state._stickBottomObserver = observer;
  clearTimeout(state._stickBottomTimer);
  state._stickBottomTimer = setTimeout(() => {
    scrollThreadToBottom({ force: true });
    releaseOpenThreadStick();
  }, 1600);
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

function generationJobBodies(jobId) {
  const jid = String(jobId);
  return [
    ...document.querySelectorAll(`[data-generation-job="${jid}"]`),
    ...document.querySelectorAll(`[data-generation-job="${Number(jobId)}"]`),
  ];
}

function primaryGenerationJobBody(jobId) {
  const bodies = generationJobBodies(jobId);
  return bodies.length ? bodies[bodies.length - 1] : null;
}

function shouldHoldGenerationScroll(jobId) {
  if (state.genScrollFollowPaused) return false;
  if (isThreadScrollLocked() || isJobDomUpdateFrozen(jobId)) return false;
  return (
    isGenerationScrollPinned() ||
    (state.focusGenJobId != null && Number(state.focusGenJobId) === Number(jobId))
  );
}

function maybeReanchorGenerationJobTurn(jobId) {
  if (!shouldHoldGenerationScroll(jobId)) return;
  scrollToGenerationJobTurn(jobId);
}

/** 将视口滚到指定生图任务；若该 job 在会话末尾则贴底（靠近输入框） */
function scrollToGenerationJobTurn(jobId, { preferBottom = true } = {}) {
  if (state.genScrollFollowPaused) return false;
  if (isThreadScrollLocked() && Number(state.generationScrollPinJobId) === Number(jobId)) {
    enforceThreadScrollLock();
    return true;
  }
  const container = document.getElementById("thread-container");
  const body = primaryGenerationJobBody(jobId);
  if (!container || !body) return false;
  const turn = body.closest(".turn");
  markProgrammaticThreadScroll();
  container.style.scrollBehavior = "auto";
  if (preferBottom && generationJobTurnIsLatest(jobId) && turn) {
    turn.scrollIntoView({ block: "end", inline: "nearest", behavior: "auto" });
    container.scrollTop = maxThreadScrollTop();
    container.style.scrollBehavior = "";
    return true;
  }
  const focus = turn || body.querySelector(".gen-status-line") || body;
  const cRect = container.getBoundingClientRect();
  const tRect = focus.getBoundingClientRect();
  const top = tRect.top - cRect.top + container.scrollTop - 20;
  container.scrollTop = Math.max(0, Math.min(top, maxThreadScrollTop()));
  container.style.scrollBehavior = "";
  return true;
}

function pinScrollToGenerationJob(jobId, maxAttempts = 5, pinMs = 120000) {
  if (!jobId) return;
  state.generationScrollPinJobId = jobId;
  state.generationScrollPinUntil = Date.now() + pinMs;
  state.focusGenJobId = jobId;
  clearThreadPrepareScrollTimers();
  let attempt = 0;
  const tick = () => {
    if (state.genScrollFollowPaused) return;
    if (state.generationScrollPinJobId == null || Number(state.generationScrollPinJobId) !== Number(jobId)) {
      return;
    }
    if (Date.now() > state.generationScrollPinUntil) return;
    const ok = scrollToGenerationJobTurn(jobId);
    attempt += 1;
    if (!ok && attempt < maxAttempts) {
      setTimeout(tick, attempt < 3 ? 32 : 120);
    } else if (attempt < 2) {
      setTimeout(tick, 48);
    }
  };
  tick();
}

function consumeGenFollowScroll(jobId) {
  if (state.genFollowScrollJobId == null || Number(state.genFollowScrollJobId) !== Number(jobId)) {
    return false;
  }
  delete state.genFollowScrollJobId;
  scrollToGenerationJobTurn(jobId);
  return true;
}

/** 策划预览完成后将视口锚定到该条助手消息（仅一次） */
function scrollToPlanConfirmTurn(jobId) {
  if (state.planConfirmAnchored[jobId]) return;
  const container = document.getElementById("thread-container");
  const body = document.querySelector(`[data-generation-job="${jobId}"]`);
  const turn = body?.closest(".turn");
  if (!container || !turn) return;
  state.planConfirmAnchored[jobId] = true;
  requestAnimationFrame(() => {
    if (state.genScrollFollowPaused) return;
    markProgrammaticThreadScroll();
    const cRect = container.getBoundingClientRect();
    const tRect = turn.getBoundingClientRect();
    const top = tRect.top - cRect.top + container.scrollTop - 16;
    container.style.scrollBehavior = "auto";
    container.scrollTop = Math.max(0, top);
    container.style.scrollBehavior = "";
  });
}

function jobAwaitingPlanConfirm(job) {
  const plan = job?.plan_json || {};
  if (!job || job.status !== "pending" || !plan.awaiting_generation_confirm) return false;
  return plan.plan_ready || (Array.isArray(plan.shots) && plan.shots.length > 0);
}

function messageAwaitingPlanConfirm(m) {
  if (!m?.metadata?.awaiting_generation_confirm) return false;
  const phase = String(m.metadata.generation_phase || "").toLowerCase();
  if (["running", "queued", "succeeded", "failed", "cancelled"].includes(phase)) return false;
  return true;
}

function removePlanConfirmActions(body) {
  const host = body || null;
  if (!host) return;
  host.querySelectorAll(".gen-plan-actions").forEach((el) => el.remove());
}

function attachPlanConfirmActions(body, jobId, job) {
  if (!body || !jobId) return;
  if (job && !jobAwaitingPlanConfirm(job)) {
    removePlanConfirmActions(body);
    return;
  }
  if (body.querySelector(".gen-plan-actions")) return;
  const actions = document.createElement("div");
  actions.className = "gen-plan-actions";
  const runBtn = document.createElement("button");
  runBtn.type = "button";
  runBtn.className = "gen-plan-btn gen-plan-btn-primary";
  runBtn.textContent = "开始生图";
  runBtn.onclick = () => {
    runBtn.disabled = true;
    const sib = actions.querySelector(".gen-plan-btn:not(.gen-plan-btn-primary)");
    if (sib) sib.disabled = true;
    confirmGenerationPlan(jobId).catch((e) => {
      alert(e.message);
      runBtn.disabled = false;
      if (sib) sib.disabled = false;
    });
  };
  const optBtn = document.createElement("button");
  optBtn.type = "button";
  optBtn.className = "gen-plan-btn";
  optBtn.textContent = "仅优化卖点";
  optBtn.onclick = () => reoptimizeGenerationPlan(jobId).catch((e) => alert(e.message));
  actions.append(runBtn, optBtn);
  body.appendChild(actions);
}

function syncPlanPreviewInChat(job) {
  if (!jobAwaitingPlanConfirm(job)) return;
  const body = document.querySelector(`[data-generation-job="${job.id}"]`);
  if (!body) return;
  const plan = job.plan_json || {};
  const summary = (plan.planning_summary || "").trim();
  const textEl = body.querySelector(".msg-text");
  if (textEl && summary) {
    const hint =
      "\n\n——\n确认策划无误后，点击下方 **「开始生图」**，或 **「仅优化卖点」** 后再生图。";
    setMessageContent(textEl, summary + hint, "assistant");
  } else if (textEl) {
    setMessageContent(
      textEl,
      `已完成 ${job.image_count || 0} 条 Listing 主图策划，请确认后开始生图。`,
      "assistant"
    );
  }
  attachPlanConfirmActions(body, job.id, job);
  const statusEl = body.querySelector(".gen-status-line");
  if (statusEl) {
    statusEl.textContent = formatJobProgress(job);
    statusEl.classList.remove("shimmer");
  }
}

async function handlePlanPreviewReady(job) {
  if (!job?.id || !state.currentId) return;
  if (state.planPreviewNotified[job.id]) return;
  if (state.confirmingGenJobId && Number(state.confirmingGenJobId) === Number(job.id)) return;
  state.planPreviewNotified[job.id] = true;
  try {
    const refreshed = await api(`/api/generations/${job.id}/`);
    ChatCache.setJob(job.id, refreshed);
    const hasDom = !!primaryGenerationJobBody(job.id);
    if (hasDom) {
      syncPlanPreviewInChat(refreshed);
      scrollToPlanConfirmTurn(job.id);
    } else {
      ChatCache.invalidateConversation(state.currentId);
      await loadConversationDetail(state.currentId, { anchorGenerationJobId: job.id });
      syncPlanPreviewInChat(refreshed);
      scrollToPlanConfirmTurn(job.id);
    }
  } catch (_) {
    syncPlanPreviewInChat(job);
    scrollToPlanConfirmTurn(job.id);
  }
  setGenProgressUi("策划已完成，请在对话中点击「开始生图」", { running: false, jobId: null });
  stopGenerationWatch(job.id);
}

function effectiveJobStatus(job) {
  if (!job) return "pending";
  if (
    (job.completed_count || 0) > 0 &&
    job.status === "pending" &&
    !jobAwaitingPlanConfirm(job)
  ) {
    return "running";
  }
  return job.status;
}

function assistantBubbleTextForJob(job) {
  if (!job) return "";
  if (jobAwaitingPlanConfirm(job)) {
    return `已完成 ${job.image_count || 0} 条 Listing 主图策划，请确认后开始生图。`;
  }
  const st = effectiveJobStatus(job);
  if (st === "queued") return "排队等待生图…";
  if (st === "running") {
    return `正在生成图片…（${job.completed_count || 0}/${job.image_count || 0}）`;
  }
  if (st === "pending") return "正在分析参考图并策划套图…";
  if (st === "succeeded") {
    return `已完成 ${job.image_count || job.completed_count || 0} 张套图。`;
  }
  if (st === "failed") {
    return `生成失败（${job.completed_count || 0}/${job.image_count || 0} 张）。`;
  }
  if (st === "cancelled") return "已取消生成。";
  return formatJobProgress(job);
}

function formatJobProgress(job) {
  const status = effectiveJobStatus(job);
  const view = job ? { ...job, status } : job;
  if (jobAwaitingPlanConfirm(view)) {
    let text = `策划完成，待确认生图 · 0/${job.image_count || 0} 张`;
    if (job.id) text += ` · 任务 #${job.id}`;
    return text;
  }
  const statusMap = {
    pending: "准备中",
    planned: "策划完成，正在生图",
    queued: "排队中",
    running: "正在生成图片",
    succeeded: "已完成",
    failed: "失败",
    cancelled: "已取消",
  };
  const label = statusMap[status] || status;
  let text = `${label} · ${view.completed_count || 0}/${view.image_count} 张`;
  if (view.id) text += ` · 任务 #${view.id}`;
  if (view.queue_position) text += ` · 队列第 ${view.queue_position} 位`;
  if (view.error_message) {
    const err =
      view.error_message.length > 120
        ? view.error_message.slice(0, 120) + "…"
        : view.error_message;
    if (status === "failed" || status === "succeeded") text += ` · ${err}`;
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
  if (scroll && !isThreadScrollLocked()) scrollThreadToBottom();
  else if (scroll && isThreadScrollLocked()) {
    const container = document.getElementById("thread-container");
    if (container) {
      markProgrammaticThreadScroll();
      container.scrollTop = maxThreadScrollTop();
      state.threadScrollLockTop = container.scrollTop;
    }
  }
  enforceThreadScrollLock();
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
  const resolveJob = () => {
    const slot = img.closest(".gallery-slot");
    const fromSlot = Number(slot?.dataset?.lazyJobId);
    if (fromSlot > 0) return fromSlot;
    const fromGrid = Number(slot?.closest(".gallery")?.dataset?.jobGallery);
    if (fromGrid > 0) return fromGrid;
    const fromTurn = Number(slot?.closest("[data-generation-job]")?.dataset?.generationJob);
    if (fromTurn > 0) return fromTurn;
    const j = Number(jobId);
    return j > 0 ? j : null;
  };
  const open = () => openImageLightbox(url, index, resolveJob());
  img.onclick = open;
  img.onkeydown = (e) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      open();
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
    const st = String(imgRec?.status || "").toLowerCase();

    if (imgRec?.url) {
      const hasImg = !!slot.querySelector("img");
      const staleLabel = /失败|生成中|待重试|同步中|重试中/.test(slot.textContent || "");
      if (existingUrl === imgRec.url && hasImg && !staleLabel) continue;
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
    } else if (st === "succeeded") {
      slot.className = "gallery-slot pending-img";
      slot.dataset.imageUrl = "";
      slot.textContent = `#${i} 加载中…`;
    } else if (st === "running") {
      slot.className = "gallery-slot";
      slot.dataset.imageUrl = "";
      slot.innerHTML = "";
      slot.textContent = `#${i} 生成中…`;
    } else if (st === "failed") {
      const jobLive = effectiveJobStatus(job);
      const jobTerminal = ["succeeded", "failed", "cancelled"].includes(job.status);
      slot.className = "gallery-slot";
      slot.dataset.imageUrl = "";
      slot.innerHTML = "";
      if (imageStillLanding(imgRec)) {
        slot.textContent = `#${i} 生成中…`;
      } else if (!jobTerminal && (jobLive === "running" || jobLive === "queued")) {
        slot.textContent = `#${i} 待重试`;
      } else {
        slot.textContent = `#${i} 失败`;
      }
    } else if (!imgRec?.url && !slot.querySelector("img")) {
      slot.className = "gallery-slot";
      slot.dataset.imageUrl = "";
      slot.innerHTML = "";
      const jobLive = effectiveJobStatus(job);
      if (jobLive === "running" && job.completed_count === i - 1) {
        slot.textContent = `#${i} 生成中…`;
      } else {
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
    const sig = generationJobImagesSignature(job);
    const domStale =
      force ||
      [...(gridEl?.querySelectorAll(".gallery-slot") || [])].some((slot) =>
        /同步中/.test(slot.textContent || "")
      );
    if (
      domStale ||
      !cached ||
      cached.status !== job.status ||
      cached.completed_count !== job.completed_count ||
      generationJobImagesSignature(cached) !== sig
    ) {
      applyJob(job);
    }
    if (jobGalleryNeedsRefresh(job)) {
      startGallerySyncPoll(jobId, state.currentId);
    } else {
      stopGallerySyncPoll(jobId);
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
  if (jobId) {
    const onLayout = () => scheduleGalleryLayoutReanchor(jobId);
    img.addEventListener("load", onLayout, { once: true });
    img.addEventListener("error", onLayout, { once: true });
  }
}

window.hydrateGallerySlot = hydrateGallerySlot;

window.onGalleryEnterViewport = function onGalleryEnterViewport(jobId, grid, statusEl) {
  if (!jobId || !grid || state.threadAnchoring || window.__iaThreadAnchoring) return;
  refreshJobGallery(jobId, grid, statusEl, { force: grid.dataset.jobHydrated !== "1" })
    .then((job) => {
      grid.dataset.jobHydrated = "1";
      LazyMedia.scan(grid);
      if (isJobRunning(job) && state.currentId && !jobAwaitingPlanConfirm(job)) {
        watchGeneration(jobId, state.currentId);
      }
    })
    .catch(() => {});
};

function updateJobInChat(job, opts = {}) {
  const skipScroll = !!opts.skipScroll;
  const body = primaryGenerationJobBody(job.id);
  if (!body) return;
  const frozen = isJobDomUpdateFrozen(job.id);
  const terminal = ["succeeded", "failed", "cancelled"].includes(job.status);
  if (jobAwaitingPlanConfirm(job) && state.planPreviewNotified[job.id]) {
    return;
  }
  const turn = body.closest(".turn");
  if (
    !frozen &&
    !terminal &&
    !jobAwaitingPlanConfirm(job) &&
    turn?.parentNode &&
    !turn.previousElementSibling?.classList.contains("turn-user")
  ) {
    const lastUser = turn.parentNode.querySelector(".turn-user:last-of-type");
    if (lastUser && lastUser !== turn) {
      turn.parentNode.insertBefore(turn, lastUser.nextElementSibling);
    }
  }
  if (jobAwaitingPlanConfirm(job)) {
    attachPlanConfirmActions(body, job.id, job);
    const statusElEarly = body.querySelector(".gen-status-line");
    if (statusElEarly) {
      statusElEarly.textContent = formatJobProgress(job);
      statusElEarly.classList.remove("shimmer");
    }
    return;
  }
  removePlanConfirmActions(body);
  const statusEl = body.querySelector(".gen-status-line");
  const gridEl = body.querySelector(".gallery");
  const textEl = body.querySelector(".msg-text");
  if (statusEl) {
    statusEl.textContent = formatJobProgress(job);
    const running =
      !jobAwaitingPlanConfirm(job) &&
      !["succeeded", "failed", "cancelled"].includes(effectiveJobStatus(job));
    statusEl.classList.toggle("shimmer", running);
  }
  if (textEl && isJobRunning(job) && !jobAwaitingPlanConfirm(job)) {
    const live = assistantBubbleTextForJob(job);
    if (live) setMessageContent(textEl, live, "assistant");
  } else if (textEl && ["succeeded", "failed", "cancelled"].includes(job.status)) {
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
  if (frozen) {
    if (isThreadScrollLocked()) enforceThreadScrollLock();
    return;
  }
  if (!skipScroll && consumeGenFollowScroll(job.id)) return;
  if (terminal && !skipScroll && Number(state.genGallerySettling) !== Number(job.id)) {
    scheduleGalleryLayoutReanchor(job.id);
    return;
  }
  const container = document.getElementById("thread-container");
  const nearBottom =
    container &&
    container.scrollHeight - container.scrollTop - container.clientHeight < 160;
  if (nearBottom && !isGenerationScrollPinned()) scrollThreadToBottom();
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
    btn.dataset.jobId = String(job.id);
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
      if (st === "failed") {
        const live = effectiveJobStatus(job);
        if (imageStillLanding(rec)) btn.textContent = `#${i} 生成中`;
        else if (live === "running" || live === "queued") btn.textContent = `#${i} 待重试`;
        else btn.textContent = `#${i} 失败`;
      } else if (st === "running") btn.textContent = `#${i} 生成中`;
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
  const resolvedJobId = resolveLightboxJobId(ctx);
  if (!resolvedJobId) return;
  ctx.jobId = resolvedJobId;
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

function resetLightboxRefineUploadUi() {
  state.lightboxRefineUploads = [];
  const cb = document.getElementById("lightbox-refine-use-upload");
  if (cb) cb.checked = false;
  const wrap = document.getElementById("lightbox-refine-upload-wrap");
  wrap?.classList.add("hidden");
  const input = document.getElementById("lightbox-refine-upload-input");
  if (input) input.value = "";
  renderLightboxRefineUploads();
  syncLightboxRefineHint();
}

function renderLightboxRefineUploads() {
  const list = document.getElementById("lightbox-refine-upload-list");
  const label = document.getElementById("lightbox-refine-upload-btn-label");
  if (label) label.textContent = state.lightboxRefineUploads.length ? "继续添加" : "选择参考图片";
  if (!list) return;
  list.innerHTML = "";
  if (!state.lightboxRefineUploads.length) {
    list.classList.add("hidden");
    return;
  }
  list.classList.remove("hidden");
  state.lightboxRefineUploads.forEach((item, i) => {
    const row = document.createElement("div");
    row.className = "lightbox-refine-upload-preview";
    const img = document.createElement("img");
    img.alt = `图${i + 1}`;
    if (item.url) img.src = item.url;
    const meta = document.createElement("div");
    meta.className = "lightbox-refine-upload-meta";
    const nameEl = document.createElement("span");
    nameEl.className = "lightbox-refine-upload-name";
    nameEl.textContent = `图${i + 1}`;
    const statusEl = document.createElement("span");
    statusEl.className = "lightbox-refine-upload-status";
    statusEl.textContent = item.name || "已就绪";
    meta.append(nameEl, statusEl);
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "lightbox-refine-upload-clear";
    btn.title = "移除这张参考图";
    btn.textContent = "移除";
    btn.addEventListener("click", () => {
      state.lightboxRefineUploads.splice(i, 1);
      renderLightboxRefineUploads();
    });
    row.append(img, meta, btn);
    list.appendChild(row);
  });
}

function syncLightboxRefineHint() {
  const el = document.getElementById("lightbox-refine-hint");
  const useUpload = document.getElementById("lightbox-refine-use-upload")?.checked;
  if (!el) return;
  const promptEl = document.getElementById("lightbox-refine-prompt");
  if (useUpload) {
    const n = state.lightboxRefineUploads.length;
    const count = n ? `已选 ${n} 张，` : "";
    el.innerHTML =
      `${count}按上传顺序称为 <span class="lightbox-refine-tag">图1</span>、<span class="lightbox-refine-tag">图2</span>… ` +
      "只使用这些新图，不使用商品原图与当前成图。例如：图1是产品，模仿图2的设计和排版。";
    if (promptEl && !promptEl.value.trim()) {
      promptEl.placeholder = "例如：图1是产品图，模仿图2的设计和排版来生图…";
    }
  } else {
    el.innerHTML =
      "参考 <span class=\"lightbox-refine-tag\">商品原图</span> " +
      "<span class=\"lightbox-refine-plus\">+</span> " +
      "<span class=\"lightbox-refine-tag\">当前成图</span> 双图生成，确认后才会替换套图槽位。";
    if (promptEl && !promptEl.value.trim()) {
      promptEl.placeholder = "例如：人物更自然、减少 AI 感；保持构图；产品包装与商品原图一致…";
    }
  }
}

async function uploadLightboxRefineReferences(files) {
  const incoming = [...files];
  if (!incoming.length) return;
  const room = MAX_REF_IMAGES - state.lightboxRefineUploads.length;
  if (room <= 0) {
    setLightboxRefineStatus(`最多上传 ${MAX_REF_IMAGES} 张参考图`, true);
    return;
  }
  const batch = incoming.slice(0, room);
  if (batch.length < incoming.length) {
    setLightboxRefineStatus(`已选 ${incoming.length} 张，仅添加前 ${batch.length} 张（上限 ${MAX_REF_IMAGES} 张）`);
  } else {
    setLightboxRefineStatus("正在上传参考图…");
  }
  for (const file of batch) {
    const fd = new FormData();
    fd.append("file", file);
    const data = await api("/api/uploads/", { method: "POST", body: fd });
    state.lightboxRefineUploads.push({
      id: data.id,
      name: data.original_name || file.name,
      url: data.url,
    });
  }
  renderLightboxRefineUploads();
  syncLightboxRefineHint();
}

async function openImageLightbox(url, index, jobId) {
  const box = document.getElementById("image-lightbox");
  const img = document.getElementById("lightbox-img");
  const cap = document.getElementById("lightbox-caption");
  const promptEl = document.getElementById("lightbox-refine-prompt");
  if (!box || !img) return;
  stopLightboxRefinePoll();
  await discardLightboxRefineCandidate();
  resetLightboxRefineUploadUi();

  let jid = Number(jobId);
  if (!jid || jid <= 0) {
    const capHint = Number(document.getElementById("image-lightbox")?.dataset?.activeJobId);
    if (capHint > 0) jid = capHint;
    else jid = resolveLightboxJobId({ jobId }) || null;
  } else {
    jid = jid || null;
  }
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
  syncLightboxRefineHint();
  const submitBtn = document.getElementById("lightbox-refine-submit");
  if (submitBtn) submitBtn.disabled = !jid || !resolvedUrl;
  renderLightboxStrip(job, idx);
  syncLightboxImageModelSelect(state.imageModel);
  if (jid) {
    resolveLightboxDefaultImageModel(jid).catch(() => {});
  }
  if (box) box.dataset.activeJobId = jid ? String(jid) : "";
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
  resetLightboxRefineUploadUi();
  box.classList.add("hidden");
  delete box.dataset.activeJobId;
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

function resolveLightboxJobId(ctx) {
  const fromBox = Number(document.getElementById("image-lightbox")?.dataset?.activeJobId);
  if (Number.isFinite(fromBox) && fromBox > 0) return fromBox;
  const n = Number(ctx?.jobId);
  if (Number.isFinite(n) && n > 0) return n;
  const fj = Number(state.focusGenJobId);
  if (Number.isFinite(fj) && fj > 0) return fj;
  const fromStrip = Number(
    document.querySelector("#lightbox-strip .lightbox-strip-item.is-active")?.dataset?.jobId
  );
  if (Number.isFinite(fromStrip) && fromStrip > 0) return fromStrip;
  const gallery = document.querySelector(
    `.gallery[data-job-gallery="${fj}"]`
  );
  const fromGallery = Number(gallery?.dataset?.jobGallery);
  if (Number.isFinite(fromGallery) && fromGallery > 0) return fromGallery;
  const fromDom = Number(
    document.querySelector(`[data-generation-job="${fj}"]`)?.dataset?.generationJob
  );
  if (Number.isFinite(fromDom) && fromDom > 0) return fromDom;
  const cap = document.getElementById("lightbox-caption")?.textContent || "";
  const capMatch = cap.match(/任务\s*(\d+)/);
  if (capMatch) return Number(capMatch[1]);
  const any = document.querySelector("[data-generation-job]");
  const fallback = Number(any?.dataset?.generationJob);
  if (Number.isFinite(fallback) && fallback > 0) return fallback;
  const anyGallery = Number(document.querySelector(".gallery[data-job-gallery]")?.dataset?.jobGallery);
  return Number.isFinite(anyGallery) && anyGallery > 0 ? anyGallery : null;
}

async function downloadAllLightboxImages() {
  const ctx = state.lightboxRefine;
  const jobId = resolveLightboxJobId(ctx);
  const btn = document.getElementById("lightbox-download-all");
  if (!jobId) {
    alert("无法识别套图任务，请从本对话的套图画廊打开大图后再下载");
    return;
  }
  const label = btn?.textContent;
  if (btn) {
    btn.disabled = true;
    btn.textContent = "打包下载中…";
  }
  try {
    const res = await fetch(`/api/generations/${jobId}/download-all/`, {
      method: "GET",
      credentials: "same-origin",
      headers: {
        Accept: "application/zip, application/json;q=0.9, */*;q=0.8",
        "X-CSRFToken": getCookie("csrftoken") || "",
      },
    });
    if (!res.ok) {
      let detail = "下载失败";
      try {
        const data = await res.json();
        if (data?.detail) detail = data.detail;
      } catch (_) {
        /* ignore */
      }
      throw new Error(detail);
    }
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `generation_${jobId}.zip`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  } catch (err) {
    alert(err.message || "下载失败");
  } finally {
    if (btn) {
      btn.disabled = false;
      if (label) btn.textContent = label;
    }
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
  const useUpload = Boolean(document.getElementById("lightbox-refine-use-upload")?.checked);
  const body = { prompt, image_model: imageModel, reference_mode: useUpload ? "upload_only" : "dual" };
  if (useUpload) {
    const ids = state.lightboxRefineUploads.map((item) => item.id).filter(Boolean);
    if (!ids.length) {
      setLightboxRefineStatus("请先上传参考图片", true);
      if (submitBtn) submitBtn.disabled = false;
      return;
    }
    body.reference_attachment_ids = ids;
    body.reference_attachment_id = ids[0];
  }
  try {
    const data = await api(
      `/api/generations/${ctx.jobId}/slots/${ctx.index}/refine/`,
      {
        method: "POST",
        body: JSON.stringify(body),
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

function generationJobImagesSignature(job) {
  if (!job?.images?.length) return "";
  return job.images
    .map((im) => `${im.index}:${String(im.status || "").toLowerCase()}:${im.url || ""}`)
    .sort()
    .join("|");
}

function imageStillLanding(im) {
  if (!im || im.url) return false;
  const err = String(im.error_message || "");
  return /未落盘|单张超时|待回收/.test(err);
}

function jobGalleryNeedsRefresh(job) {
  if (!job) return false;
  const total = Number(job.image_count) || 0;
  if (total <= 0) return false;
  const images = job.images || [];
  const byIndex = {};
  images.forEach((im) => {
    byIndex[Number(im.index)] = im;
  });
  for (let i = 1; i <= total; i++) {
    const im = byIndex[i];
    if (!im) return true;
    const st = String(im.status || "").toLowerCase();
    if (st === "running" || st === "pending") return true;
    if (st === "succeeded" && !im.url) return true;
    if (st === "failed" && imageStillLanding(im)) return true;
  }
  if (job.status === "running" && (job.completed_count || 0) < total) return true;
  return false;
}

function shouldStopGenerationWatch(job) {
  if (!job) return true;
  if (!["succeeded", "failed", "cancelled"].includes(job.status)) return false;
  return !jobGalleryNeedsRefresh(job);
}

/** 任务终态后画廊仍可能落后（末镜落盘/SSE 提前结束），再拉几轮 */
async function finishGenerationWatchWhenReady(jobId) {
  if (!jobId) return;
  if (state.genFinishWatchActive[jobId]) return;
  state.genFinishWatchActive[jobId] = true;
  const prevSettling = state.genGallerySettling;
  state.genGallerySettling = jobId;
  const FINISH_POLL_MS = 1200;
  const FINISH_MAX_ROUNDS = 14;
  let lastSig = "";
  try {
    for (let i = 0; i < FINISH_MAX_ROUNDS; i++) {
      let job = null;
      try {
        job = await api(`/api/generations/${jobId}/`);
        ChatCache.setJob(jobId, job);
      } catch (_) {
        await new Promise((r) => setTimeout(r, FINISH_POLL_MS));
        continue;
      }
      const sig = `${job.status}:${job.completed_count}:${generationJobImagesSignature(job)}`;
      if (jobBelongsToActiveConversation(job) && sig !== lastSig) {
        lastSig = sig;
        updateJobInChat(job, { skipScroll: true });
      }
      if (shouldStopGenerationWatch(job)) {
        if (jobBelongsToActiveConversation(job)) {
          updateJobInChat(job, { skipScroll: false });
        }
        stopGallerySyncPoll(jobId);
        stopGenerationWatch(jobId);
        hideGenProgressIfIdle();
        return;
      }
      await new Promise((r) => setTimeout(r, FINISH_POLL_MS));
    }
    try {
      const job = await api(`/api/generations/${jobId}/`);
      ChatCache.setJob(jobId, job);
      if (jobBelongsToActiveConversation(job)) {
        updateJobInChat(job, { skipScroll: false });
      }
    } catch (_) {}
    stopGenerationWatch(jobId);
    hideGenProgressIfIdle();
    try {
      const job = ChatCache.getJob(jobId);
      if (job && jobGalleryNeedsRefresh(job)) {
        startGallerySyncPoll(jobId, state.currentId);
      }
    } catch (_) {}
  } finally {
    delete state.genFinishWatchActive[jobId];
    state.genGallerySettling = prevSettling;
    clearGenerationScrollPin(jobId);
    clearThreadScrollLock();
    delete state.confirmingGenJobId;
  }
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
  if (Object.keys(state.genWatchers).length === 0) {
    clearThreadScrollLock();
  }
}

function jobBelongsToActiveConversation(job) {
  if (job.conversation != null && state.currentId != null) {
    return Number(job.conversation) === Number(state.currentId);
  }
  const body = primaryGenerationJobBody(job.id);
  return !!body && document.getElementById("messages")?.contains(body);
}

function applyGenerationJobProgress(job, opts = {}) {
  if (!jobBelongsToActiveConversation(job)) return;
  if (Number(state.genGallerySettling) === Number(job.id) && !opts.forceProgress) {
    return;
  }
  const frozen = isJobDomUpdateFrozen(job.id);
  updateJobInChat(job, { skipScroll: !!opts.skipScroll });
  if (frozen) {
    if (jobGalleryNeedsRefresh(job) && isGenWatchActive(job.id)) {
      void pollGenerationJob(job.id);
    }
    const terminalEarly = ["succeeded", "failed", "cancelled"].includes(job.status);
    if (terminalEarly) {
      resetGenCancelButton();
      if (job.status === "succeeded") {
        setGenProgressUi(formatJobProgress(job), { running: false });
        setTimeout(hideGenProgressIfIdle, 2500);
      } else {
        hideGenProgressIfIdle();
      }
      enforceThreadScrollLock();
      setTimeout(() => {
        delete state.confirmingGenJobId;
        clearThreadScrollLock();
      }, 2500);
      return;
    }
    if (!jobAwaitingPlanConfirm(job)) {
      const active = isJobActivelyGenerating(job);
      setGenProgressUi(formatJobProgress(job), {
        running: active,
        jobId: active ? job.id : null,
      });
    }
    enforceThreadScrollLock();
    return;
  }
  if (jobGalleryNeedsRefresh(job) && isGenWatchActive(job.id)) {
    void pollGenerationJob(job.id);
  }
  if (jobAwaitingPlanConfirm(job)) {
    handlePlanPreviewReady(job).catch(() => {
      syncPlanPreviewInChat(job);
      setGenProgressUi("策划已完成，请在对话中点击「开始生图」", { running: false, jobId: null });
      stopGenerationWatch(job.id);
    });
    return;
  }
  const terminal = ["succeeded", "failed", "cancelled"].includes(job.status);
  if (terminal) {
    const pinBody = primaryGenerationJobBody(job.id);
    removePlanConfirmActions(pinBody);
    delete state.planPreviewNotified[job.id];
    delete state.planConfirmAnchored[job.id];
    if (job.status === "succeeded") {
      setGenProgressUi(formatJobProgress(job), { running: false });
      setTimeout(hideGenProgressIfIdle, 2500);
    } else {
      hideGenProgressIfIdle();
    }
    resetGenCancelButton();
    state.focusGenJobId = job.id;
    clearThreadPrepareScrollTimers();
    if (state.currentId) {
      state.genTerminalHandled[job.id] = true;
      ChatCache.invalidateConversation(state.currentId);
      const hasDom = !!primaryGenerationJobBody(job.id);
      if (!hasDom && !shouldBlockThreadFullReload()) {
        loadConversationDetail(state.currentId, { anchorGenerationJobId: job.id }).catch(() => {});
      }
      if (isThreadScrollLocked()) enforceThreadScrollLock();
    }
    if (jobGalleryNeedsRefresh(job)) {
      startGallerySyncPoll(job.id, state.currentId);
      void finishGenerationWatchWhenReady(job.id);
    }
    return;
  }
  const active = isJobActivelyGenerating(job);
  setGenProgressUi(formatJobProgress(job), {
    running: active,
    jobId: active ? job.id : null,
  });
  if (!active) hideGenProgressIfIdle();
}

function resetGenCancelButton() {
  const btn = document.querySelector(".gen-cancel-btn");
  if (!btn) return;
  btn.disabled = false;
  const textEl = btn.querySelector(".gen-cancel-btn-text");
  if (textEl) textEl.textContent = "停止生图";
}

async function cancelGenerationJob(jobId) {
  if (!jobId) return null;
  beginThreadScrollLock(jobId);
  enforceThreadScrollLock();
  try {
    const job = await api(`/api/generations/${jobId}/cancel/`, { method: "POST", body: "{}" });
    ChatCache.setJob(jobId, job);
    stopGenerationWatch(jobId);
    updateJobInChat(job);
    if (jobGalleryNeedsRefresh(job)) {
      startGallerySyncPoll(jobId, state.currentId);
    }
    hideGenProgressIfIdle();
    enforceThreadScrollLock();
    return job;
  } catch (err) {
    alert(err.message || "取消失败");
    return null;
  } finally {
    resetGenCancelButton();
    setTimeout(() => {
      if (Number(state.generationScrollPinJobId) === Number(jobId)) {
        delete state.confirmingGenJobId;
        clearThreadScrollLock();
      }
    }, 2500);
  }
}

async function pollGenerationJob(jobId) {
  if (!isGenWatchActive(jobId)) return null;
  const job = await api(`/api/generations/${jobId}/`);
  ChatCache.setJob(jobId, job);
  if (!isGenWatchActive(jobId)) return job;
  applyGenerationJobProgress(job);
  if (shouldStopGenerationWatch(job)) {
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
    marketplaces: data.marketplaces || [],
    listing_prompt_presets: data.listing_prompt_presets || [],
    aspect_ratio_options: data.aspect_ratio_options || [],
    defaults: data.defaults,
  };
  state.chatModel = data.defaults.chat_model;
  state.visionModel = data.defaults.vision_model;
  state.imageModel = data.defaults.image_model;
  state.marketplaceId = data.defaults.marketplace_id || "tk_shop_mx";
  let savedAr = "1:1";
  try {
    savedAr = localStorage.getItem("ia_aspect_ratio") || data.defaults?.aspect_ratio || "1:1";
  } catch (_) {
    savedAr = data.defaults?.aspect_ratio || "1:1";
  }
  state.aspectRatio = savedAr;
  populateImageModelSelect();
  populateMarketplaceSelect();
  populateAspectRatioSelect();
  syncMarketplaceToTemplateCount(state.marketplaceId);
  renderListingPromptPresets();
  updateModelUI();
}

function populateAspectRatioSelect() {
  const sel = document.getElementById("aspect-ratio");
  if (!sel) return;
  const opts = state.catalog?.aspect_ratio_options || [{ id: "1:1", label_zh: "1:1 方图（默认）" }];
  sel.innerHTML = "";
  for (const o of opts) {
    const opt = document.createElement("option");
    opt.value = o.id;
    opt.textContent = o.label_zh || o.id;
    sel.appendChild(opt);
  }
  const want = state.aspectRatio || "1:1";
  if ([...sel.options].some((o) => o.value === want)) {
    sel.value = want;
  } else {
    sel.value = "1:1";
    state.aspectRatio = "1:1";
  }
}

function syncAspectRatioFromUi() {
  const sel = document.getElementById("aspect-ratio");
  if (!sel) return;
  state.aspectRatio = sel.value || "1:1";
  try {
    localStorage.setItem("ia_aspect_ratio", state.aspectRatio);
  } catch (_) {}
}

function listingPromptPresets() {
  return state.catalog?.listing_prompt_presets || [];
}

function renderListingPromptPresets() {
  const wrap = document.getElementById("listing-prompt-presets");
  const chipsEl = document.getElementById("listing-prompt-presets-chips");
  if (!wrap || !chipsEl) return;
  const presets = listingPromptPresets();
  if (!presets.length) {
    wrap.classList.add("hidden");
    chipsEl.innerHTML = "";
    return;
  }
  wrap.classList.remove("hidden");
  chipsEl.innerHTML = "";
  for (const p of presets) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "listing-prompt-chip";
    btn.dataset.marketplaceId = p.marketplace_id;
    btn.title = p.prompt_zh;
    btn.textContent = p.chip_label || p.marketplace_id;
    if (state.listingPromptPresetId === p.marketplace_id) {
      btn.classList.add("is-active");
    }
    btn.addEventListener("click", () => applyListingPromptPreset(p.marketplace_id));
    chipsEl.appendChild(btn);
  }
}

function applyListingPromptPreset(marketplaceId) {
  const preset = listingPromptPresets().find((p) => p.marketplace_id === marketplaceId);
  if (!preset?.prompt_zh) return;
  const input = document.getElementById("prompt-input");
  if (!input) return;
  const hasText = input.value.trim().length > 0;
  const switching = state.listingPromptPresetId && state.listingPromptPresetId !== marketplaceId;
  if (hasText && (switching || input.value.trim() !== preset.prompt_zh.trim())) {
    const ok = confirm(
      "将用快捷话术替换输入框内容，并同步投放站点、套图模板与张数，同时勾选「强制套图」。继续？"
    );
    if (!ok) return;
  }
  input.value = preset.prompt_zh;
  autoResizeTextarea();
  state.listingPromptPresetId = marketplaceId;
  const mSel = document.getElementById("marketplace-id");
  if (mSel && [...mSel.options].some((o) => o.value === marketplaceId)) {
    mSel.value = marketplaceId;
    state.marketplaceId = marketplaceId;
    syncMarketplaceToTemplateCount(marketplaceId);
  }
  const tplSel = document.getElementById("plan-template");
  if (tplSel && preset.plan_template) {
    const exists = [...tplSel.options].some((o) => o.value === preset.plan_template);
    if (exists) tplSel.value = preset.plan_template;
  }
  const countSel = document.getElementById("image-count");
  if (countSel && preset.image_count) {
    const v = String(preset.image_count);
    if ([...countSel.options].some((o) => o.value === v)) countSel.value = v;
  }
  const genCb = document.getElementById("mode-generate");
  if (genCb) genCb.checked = true;
  renderListingPromptPresets();
  updateSendButton();
  input.focus();
}

function populateMarketplaceSelect() {
  const sel = document.getElementById("marketplace-id");
  if (!sel) return;
  const rows = state.catalog?.marketplaces || [];
  sel.innerHTML = "";
  for (const m of rows) {
    const opt = document.createElement("option");
    opt.value = m.id;
    opt.textContent = m.label;
    sel.appendChild(opt);
  }
  const def = state.marketplaceId || state.catalog?.defaults?.marketplace_id || "tk_shop_mx";
  if (def) sel.value = def;
}

function marketplaceMeta(marketplaceId) {
  return (state.catalog?.marketplaces || []).find((m) => m.id === marketplaceId) || null;
}

function syncMarketplaceToTemplateCount(marketplaceId) {
  const meta = marketplaceMeta(marketplaceId);
  if (!meta) return;
  const tplSel = document.getElementById("plan-template");
  const countSel = document.getElementById("image-count");
  if (countSel && meta.image_count) {
    const v = String(meta.image_count);
    if ([...countSel.options].some((o) => o.value === v)) countSel.value = v;
  }
  if (!tplSel) return;
  if (meta.platform === "amazon") {
    tplSel.value = "amazon_listing_7";
  } else if (meta.platform === "tiktok_shop") {
    tplSel.value = "tk_mx_ecommerce_9";
  }
}

async function onMarketplaceChange() {
  const sel = document.getElementById("marketplace-id");
  if (!sel) return;
  state.marketplaceId = sel.value;
  syncMarketplaceToTemplateCount(sel.value);
  try {
    await savePreferences({ marketplace_id: sel.value });
  } catch (e) {
    alert(e.message);
    return;
  }
  if (state.currentId) {
    try {
      await api(`/api/chat/conversations/${state.currentId}/`, {
        method: "PATCH",
        body: JSON.stringify({ marketplace_id: sel.value }),
      });
      const row = state.conversations.find((c) => c.id === state.currentId);
      if (row) row.marketplace_id = sel.value;
    } catch (e) {
      alert(e.message);
    }
  }
}

function applyMarketplaceFromConversation(detail) {
  const sel = document.getElementById("marketplace-id");
  if (!sel) return;
  const convMid = (detail?.marketplace_id || "").trim();
  const mid =
    convMid ||
    state.user?.marketplace_id ||
    state.catalog?.defaults?.marketplace_id ||
    "tk_shop_mx";
  state.marketplaceId = mid;
  sel.value = mid;
  syncMarketplaceToTemplateCount(mid);
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
  const id =
    kind === "users"
      ? "admin-users-modal"
      : kind === "usage"
        ? "admin-usage-modal"
        : "admin-approvals-modal";
  document.getElementById(id)?.classList.add("hidden");
}

function localDateInputValue(d = new Date()) {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

function syncAdminUsageToolbarFromState() {
  const anchor = document.getElementById("admin-usage-anchor");
  const search = document.getElementById("admin-usage-search");
  if (anchor) anchor.value = state.adminUsage.anchor || localDateInputValue();
  if (search) search.value = state.adminUsage.q;
  document.querySelectorAll(".admin-usage-period-btn").forEach((btn) => {
    btn.classList.toggle("is-active", btn.dataset.usagePeriod === state.adminUsage.period);
  });
}

function adminUsageQueryString() {
  const p = new URLSearchParams();
  p.set("period", state.adminUsage.period);
  p.set("page", String(state.adminUsage.page));
  p.set("page_size", String(state.adminUsage.pageSize));
  const anchor = (state.adminUsage.anchor || document.getElementById("admin-usage-anchor")?.value || "").trim();
  if (anchor) p.set("anchor", anchor);
  if (state.adminUsage.q.trim()) p.set("q", state.adminUsage.q.trim());
  return p.toString();
}

function formatUsageModelList(models) {
  if (!models?.length) return "—";
  return models
    .map((m) => `${escapeHtml(m.label || m.model_id)} ×${m.uses}`)
    .join("<br>");
}

function updateAdminUsagePaginationUi() {
  const info = document.getElementById("admin-usage-page-info");
  const prev = document.getElementById("admin-usage-prev");
  const next = document.getElementById("admin-usage-next");
  const { page, totalPages, count } = state.adminUsage;
  if (info) {
    info.textContent =
      totalPages > 1 ? `第 ${page} / ${totalPages} 页 · 共 ${count} 人有记录` : `共 ${count} 人有记录`;
  }
  if (prev) prev.disabled = page <= 1;
  if (next) next.disabled = page >= totalPages;
}

async function loadAdminUsageStats() {
  const tbody = document.getElementById("admin-usage-tbody");
  const emptyEl = document.getElementById("admin-usage-empty");
  const summaryEl = document.getElementById("admin-usage-summary");
  const modelsEl = document.getElementById("admin-usage-model-totals");
  if (!tbody) return;

  const data = await api(`/api/auth/admin/usage-stats/?${adminUsageQueryString()}`);
  state.adminUsage.page = data.page || 1;
  state.adminUsage.totalPages = data.total_pages || 1;
  state.adminUsage.count = data.count || 0;

  const periodLabel =
    { day: "日", week: "周", month: "月" }[data.period] || data.period;
  if (summaryEl) {
    const t = data.totals || {};
    summaryEl.textContent = [
      `统计范围（按${periodLabel}）：${data.range_label || "—"}`,
      `任务 ${t.job_count ?? 0} · 成图 ${t.images_succeeded ?? 0} · 修复 ${t.refine_images ?? 0} · 合计调用 ${t.usage_count ?? 0}`,
      data.timezone ? `时区 ${data.timezone}` : "",
    ]
      .filter(Boolean)
      .join(" · ");
  }

  if (modelsEl) {
    const chips = (data.model_totals || [])
      .slice(0, 12)
      .map(
        (m) =>
          `<span class="admin-usage-model-chip">${escapeHtml(m.label || m.model_id)}：成图 ${m.image_generations ?? 0}（任务 ${m.job_count ?? 0}）</span>`
      )
      .join("");
    modelsEl.innerHTML = chips || '<span class="muted">暂无模型用量</span>';
  }

  tbody.innerHTML = "";
  const rows = data.results || [];
  if (!rows.length) {
    emptyEl?.classList.remove("hidden");
  } else {
    emptyEl?.classList.add("hidden");
    for (const row of rows) {
      const tr = document.createElement("tr");
      const name = row.real_name
        ? `${escapeHtml(row.real_name)}（${escapeHtml(row.username)}）`
        : escapeHtml(row.username);
      tr.innerHTML = `
        <td class="admin-usage-user"><strong>${name}</strong>${row.is_superuser ? '<span class="admin-status-tag approved">超管</span>' : ""}</td>
        <td>${row.job_count ?? 0}</td>
        <td>${row.images_succeeded ?? 0}</td>
        <td>${row.refine_images ?? 0}</td>
        <td class="admin-usage-models">${formatUsageModelList(row.image_models)}</td>`;
      tbody.appendChild(tr);
    }
  }
  updateAdminUsagePaginationUi();
}

function openAdminUsageModal() {
  document.getElementById("user-dropdown")?.classList.add("hidden");
  document.getElementById("btn-user-menu")?.setAttribute("aria-expanded", "false");
  if (!state.adminUsage.anchor) state.adminUsage.anchor = localDateInputValue();
  document.getElementById("admin-usage-modal")?.classList.remove("hidden");
  syncAdminUsageToolbarFromState();
  loadAdminUsageStats().catch((e) => alert(e.message));
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
  if (state.user.marketplace_id) {
    state.marketplaceId = state.user.marketplace_id;
    const mSel = document.getElementById("marketplace-id");
    if (mSel) {
      mSel.value = state.user.marketplace_id;
      syncMarketplaceToTemplateCount(state.user.marketplace_id);
    }
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
  applyMarketplaceFromConversation(detail);
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
  stopGallerySyncPollsForThread(box);
  ChatCache.parkThread(state.currentId, box, scroll);
  hideGenProgressIfIdle();
}

async function loadConversationDetail(id, { preserveScroll = false, anchorGenerationJobId = null, forceFullRender = false, stickToBottom = false } = {}) {
  if (shouldBlockThreadFullReload() && state.currentId === id && !forceFullRender) {
    return ChatCache.getDetail(id)?.detail || null;
  }
  let anchorId = stickToBottom ? null : anchorGenerationJobId;
  if (!stickToBottom) {
    const pinJob = isGenerationScrollPinned() ? state.generationScrollPinJobId : null;
    anchorId = anchorId || pinJob || state.focusGenJobId || null;
    if (anchorId || isGenerationScrollPinned()) {
      preserveScroll = false;
    }
  }
  const detail = await api(`/api/chat/conversations/${id}/?limit=${MESSAGE_INITIAL_SIZE}`);
  const incoming = sortMessagesForDisplay(detail.messages || []);
  const cachedMessages = ChatCache.getDetail(id)?.detail?.messages || [];
  const incomingOldest = incoming[0]?.id;
  const olderKept =
    incomingOldest == null
      ? []
      : cachedMessages.filter((m) => m.id != null && Number(m.id) < Number(incomingOldest));
  detail.messages = sortMessagesForDisplay([...olderKept, ...incoming]);
  const page = { ...(detail.message_pagination || {}) };
  if (olderKept.length) {
    const prev = state.messagePage[id] || {};
    page.oldest_message_id = detail.messages[0]?.id ?? page.oldest_message_id;
    page.newest_message_id = detail.messages[detail.messages.length - 1]?.id ?? page.newest_message_id;
    page.has_more_older = prev.has_more_older != null ? prev.has_more_older : true;
  }
  detail.message_pagination = page;
  syncMessagePagination(id, detail.message_pagination);
  ChatCache.setDetail(id, detail);
  if (state.currentId !== id) return detail;

  applyConversationHeader(detail);
  state.currentConvHasMessages = Boolean((detail.messages || []).length);
  state.currentConvIsShared = Boolean(detail.is_shared || detail.shared_by_label);
  updateShareChatButtonState();
  ChatCache.clearThreadFragment(id);
  renderMessages(detail.messages || [], {
    preserveScroll,
    anchorGenerationJobId: anchorId,
    forceFullRender,
    stickToBottom,
  });
  return detail;
}

async function selectConversation(id) {
  if (state.currentId && state.currentId !== id) {
    parkCurrentConversation();
  }

  state.currentId = id;
  state.genScrollFollowPaused = false;
  state.generationScrollPinJobId = null;
  state.generationScrollPinUntil = 0;
  state.focusGenJobId = null;
  clearThreadScrollLock();
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
    renderMessages(cachedRow.detail.messages || [], { stickToBottom: true });
    await resumeWatchersForThread(messagesEl);
    return;
  }

  await loadConversationDetail(id, { stickToBottom: true });
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
        const anchor = state.focusGenJobId
          ? { anchorGenerationJobId: state.focusGenJobId }
          : {};
        loadConversationDetail(state.currentId, anchor).catch(() => {});
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
  delete state.genTerminalHandled[jobId];
  state.focusGenJobId = jobId;
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
      const cached = ChatCache.getJob(jobId);
      if (cached && jobGalleryNeedsRefresh(cached)) {
        startGallerySyncPoll(jobId, convId);
      }
      void finishGenerationWatchWhenReady(jobId);
      return;
    }
    if (data.job) {
      applyGenerationJobProgress(data.job);
      if (shouldStopGenerationWatch(data.job)) {
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

function wantsReferenceGuidedFromText(text) {
  const t = String(text || "");
  return (
    /图\s*[1-4一二三四]\s*是/.test(t) ||
    (/模仿/.test(t) && /(首图|模特|尺码|参考)/.test(t)) ||
    /参考图导演|不用.*模板|不走.*九职能/.test(t)
  );
}

function applyTemplateFromText(text) {
  const tplSel = document.getElementById("plan-template");
  const countSel = document.getElementById("image-count");
  if (!tplSel) return;
  const t = String(text || "").toLowerCase();
  if (wantsReferenceGuidedFromText(text)) {
    tplSel.value = "reference_guided";
    const n = parseImageCountFromText(text);
    if (n && countSel) countSel.value = String(n);
    return;
  }
  const isTkNine =
    /制作\s*9\s*张|九张|1\+1\+7|tiktok|tk\b|墨西哥|mexico|西语|西班牙语/.test(t) ||
    (/主图/.test(t) && /白底/.test(t) && /详情/.test(t));
  if (!isTkNine) return;
  tplSel.value = "tk_mx_ecommerce_9";
  if (countSel) countSel.value = "9";
}

async function confirmGenerationPlan(jobId) {
  const body = primaryGenerationJobBody(jobId) || document.querySelector(`[data-generation-job="${jobId}"]`);
  removePlanConfirmActions(body);
  document.querySelectorAll(`[data-generation-job="${jobId}"] .gen-plan-actions`).forEach((el) => el.remove());
  delete state.planPreviewNotified[jobId];
  delete state.planConfirmAnchored[jobId];
  state.genFollowScrollJobId = jobId;
  clearThreadPrepareScrollTimers();
  beginThreadScrollLock(jobId, { markConfirming: true });
  const textEl = body?.querySelector(".msg-text");
  if (textEl) {
    setMessageContent(textEl, "已确认策划，正在排队/生图…", "assistant");
  }
  enforceThreadScrollLock();
  try {
    await api(`/api/generations/${jobId}/confirm-run/`, { method: "POST", body: "{}" });
    let job = null;
    try {
      job = await api(`/api/generations/${jobId}/`);
      ChatCache.setJob(jobId, job);
      updateJobInChat(job);
    } catch (_) {
      /* ignore */
    }
    enforceThreadScrollLock();
    watchGeneration(jobId, state.currentId);
    ChatCache.setJob(jobId, job || ChatCache.getJob(jobId));
  } finally {
    enforceThreadScrollLock();
    requestAnimationFrame(enforceThreadScrollLock);
  }
}

async function reoptimizeGenerationPlan(jobId) {
  await api(`/api/generations/${jobId}/restrategy/`, {
    method: "POST",
    body: JSON.stringify({ regenerate_images: false }),
  });
  if (state.currentId) {
    ChatCache.invalidateConversation(state.currentId);
    await loadConversationDetail(state.currentId);
  }
}

async function startGeneration(prompt) {
  const imageCount = parseInt(document.getElementById("image-count").value, 10);
  const planTemplate = document.getElementById("plan-template")?.value || "auto";
  const castSkin =
    document.getElementById("cast-skin-preset")?.value || state.castSkinPreset || "caucasian";
  state.castSkinPreset = castSkin;
  const backgroundMode =
    document.getElementById("background-mode")?.value || "random";
  try {
    localStorage.setItem("ia_cast_skin_preset", castSkin);
    localStorage.setItem("ia_background_mode", backgroundMode);
  } catch (_) {}

  syncAspectRatioFromUi();
  const payload = {
    prompt,
    image_count: imageCount,
    conversation_id: state.currentId,
    image_model: state.imageModel || document.getElementById("image-model").value,
    vision_model: state.visionModel,
    plan_template: planTemplate,
    marketplace_id: document.getElementById("marketplace-id")?.value || state.marketplaceId,
    cast_skin_preset: castSkin,
    background_mode: backgroundMode,
    aspect_ratio: state.aspectRatio || "1:1",
  };
  const attIds = state.attachments.map((a) => a.id);
  if (attIds.length) payload.attachment_ids = attIds;
  if (document.getElementById("plan-preview-first")?.checked) {
    payload.plan_preview_only = true;
  }

  const imageModelId =
    state.imageModel || document.getElementById("image-model")?.value || "";
  let submitMsg = "正在提交套图任务…";
  if (imageModelId) {
    submitMsg = `正在提交套图任务（生图模型：${modelLabel(state.catalog?.image_models, imageModelId) || imageModelId}）…`;
  }
  setGenProgressUi(submitMsg, { running: true });
  preserveThreadScroll(1500);
  enforceThreadScrollLock();

  const job = await api("/api/generations/", {
    method: "POST",
    body: JSON.stringify(payload),
  });

  const userMsg = job.user_message;
  const assistantMsg = job.assistant_message;
  if (userMsg) syncServerUserMessage(userMsg);
  if (assistantMsg) {
    const existingAsst = assistantMsg.id
      ? document.querySelector(`[data-message-id="${assistantMsg.id}"]`)
      : null;
    if (!existingAsst) appendMessageDom(assistantMsg, false);
  }
  mergeServerMessagesIntoCache(state.currentId, userMsg, assistantMsg);
  enforceThreadScrollLock();

  if (job.id) {
    beginThreadScrollLock(job.id, { markConfirming: false });
    const jobRow = { ...job };
    delete jobRow.user_message;
    delete jobRow.assistant_message;
    delete jobRow.dispatch;
    ChatCache.setJob(job.id, jobRow);
    watchGeneration(job.id, state.currentId);
  }
  await loadConversations();
  enforceThreadScrollLock();
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
  state.genScrollFollowPaused = false;
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
      appendMessageDom({ role: "user", content: text, metadata: genMeta }, true);
      collapseToolsPanel();
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

function collapseToolsPanel() {
  document.getElementById("tools-panel")?.classList.add("hidden");
}

function toggleToolsPanel() {
  document.getElementById("tools-panel").classList.toggle("hidden");
}

function toggleUserMenu() {
  const dd = document.getElementById("user-dropdown");
  const open = dd.classList.toggle("hidden");
  document.getElementById("btn-user-menu").setAttribute("aria-expanded", String(!open));
}

const threadScrollEl = document.getElementById("thread-container");
threadScrollEl?.addEventListener(
  "scroll",
  () => {
    if (!state._threadScrollProgrammatic) pauseGenerationScrollFollow();
    clearTimeout(state._scrollLoadOlderTimer);
    state._scrollLoadOlderTimer = setTimeout(onThreadScrollNearTop, 120);
  },
  { passive: true }
);
for (const ev of ["wheel", "touchmove"]) {
  threadScrollEl?.addEventListener(ev, releaseThreadScrollLockFromUser, { passive: true });
}
threadScrollEl?.addEventListener("keydown", (e) => {
  if (["ArrowUp", "ArrowDown", "PageUp", "PageDown", "Home", "End", " "].includes(e.key)) {
    pauseGenerationScrollFollow();
  }
});

document.getElementById("btn-send").onclick = () => sendMessage().catch(alert);
document.getElementById("prompt-input").addEventListener("input", () => {
  const presets = listingPromptPresets();
  const text = document.getElementById("prompt-input")?.value.trim() || "";
  const match = presets.find((p) => p.prompt_zh.trim() === text);
  state.listingPromptPresetId = match ? match.marketplace_id : null;
  renderListingPromptPresets();
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
document.getElementById("btn-admin-usage")?.addEventListener("click", (e) => {
  e.stopPropagation();
  openAdminUsageModal();
});
document.querySelectorAll(".admin-usage-period-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    state.adminUsage.period = btn.dataset.usagePeriod || "day";
    state.adminUsage.page = 1;
    syncAdminUsageToolbarFromState();
    loadAdminUsageStats().catch((err) => alert(err.message));
  });
});
document.getElementById("admin-usage-anchor")?.addEventListener("change", (e) => {
  state.adminUsage.anchor = e.target.value;
  state.adminUsage.page = 1;
  loadAdminUsageStats().catch((err) => alert(err.message));
});
document.getElementById("admin-usage-search")?.addEventListener("input", (e) => {
  state.adminUsage.q = e.target.value;
  state.adminUsage.page = 1;
  if (state.adminUsageSearchTimer) clearTimeout(state.adminUsageSearchTimer);
  state.adminUsageSearchTimer = setTimeout(() => {
    loadAdminUsageStats().catch((err) => alert(err.message));
  }, 350);
});
document.getElementById("admin-usage-prev")?.addEventListener("click", () => {
  if (state.adminUsage.page <= 1) return;
  state.adminUsage.page -= 1;
  loadAdminUsageStats().catch((err) => alert(err.message));
});
document.getElementById("admin-usage-next")?.addEventListener("click", () => {
  if (state.adminUsage.page >= state.adminUsage.totalPages) return;
  state.adminUsage.page += 1;
  loadAdminUsageStats().catch((err) => alert(err.message));
});
function closeDocsDropdown() {
  const dd = document.getElementById("topbar-docs-dropdown");
  const btn = document.getElementById("btn-docs-literature");
  dd?.classList.add("hidden");
  btn?.setAttribute("aria-expanded", "false");
}

function toggleDocsDropdown() {
  const dd = document.getElementById("topbar-docs-dropdown");
  const btn = document.getElementById("btn-docs-literature");
  if (!dd || !btn) return;
  const open = dd.classList.contains("hidden");
  if (open) {
    dd.classList.remove("hidden");
    btn.setAttribute("aria-expanded", "true");
  } else {
    closeDocsDropdown();
  }
}

function openDocsModal(kind) {
  closeDocsDropdown();
  const id = kind === "usage" ? "docs-usage-modal" : "docs-templates-modal";
  document.getElementById(id)?.classList.remove("hidden");
}

function closeDocsModal(kind) {
  const id = kind === "usage" ? "docs-usage-modal" : "docs-templates-modal";
  document.getElementById(id)?.classList.add("hidden");
}

function applyColorTheme(theme) {
  const next = theme === "light" ? "light" : "dark";
  if (next === "light") document.documentElement.setAttribute("data-theme", "light");
  else document.documentElement.removeAttribute("data-theme");
  document.querySelectorAll(".theme-switch-btn").forEach((btn) => {
    const on = btn.dataset.themeValue === next;
    btn.classList.toggle("is-active", on);
    btn.setAttribute("aria-pressed", on ? "true" : "false");
  });
  try {
    localStorage.setItem("ia_color_theme", next);
  } catch (_) {}
}

(function initColorTheme() {
  let saved = "dark";
  try {
    saved = localStorage.getItem("ia_color_theme") || "dark";
  } catch (_) {}
  applyColorTheme(saved);
  document.querySelectorAll(".theme-switch-btn").forEach((btn) => {
    btn.addEventListener("click", () => applyColorTheme(btn.dataset.themeValue));
  });
})();

document.getElementById("btn-docs-literature")?.addEventListener("click", (e) => {
  e.stopPropagation();
  toggleDocsDropdown();
});

document.getElementById("btn-docs-usage")?.addEventListener("click", () => openDocsModal("usage"));
document.getElementById("btn-docs-templates")?.addEventListener("click", () => openDocsModal("templates"));

document.getElementById("topbar-docs-wrap")?.addEventListener("click", (e) => e.stopPropagation());

document.querySelectorAll("[data-docs-close]").forEach((el) => {
  el.addEventListener("click", () => {
    const kind = el.getAttribute("data-docs-close");
    if (kind) closeDocsModal(kind);
  });
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
  closeDocsDropdown();
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
document.getElementById("aspect-ratio")?.addEventListener("change", syncAspectRatioFromUi);
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
document.getElementById("lightbox-refine-upload-btn")?.addEventListener("click", () => {
  document.getElementById("lightbox-refine-upload-input")?.click();
});
document.getElementById("lightbox-refine-use-upload")?.addEventListener("change", (e) => {
  const on = e.target.checked;
  const wrap = document.getElementById("lightbox-refine-upload-wrap");
  if (on) wrap?.classList.remove("hidden");
  else {
    wrap?.classList.add("hidden");
    state.lightboxRefineUploads = [];
    const input = document.getElementById("lightbox-refine-upload-input");
    if (input) input.value = "";
    renderLightboxRefineUploads();
  }
  syncLightboxRefineHint();
});
document.getElementById("lightbox-refine-upload-input")?.addEventListener("change", async (e) => {
  const files = e.target.files;
  if (!files?.length) return;
  try {
    await uploadLightboxRefineReferences(files);
    if (!document.getElementById("lightbox-refine-status")?.classList.contains("error")) {
      setLightboxRefineStatus("");
    }
  } catch (err) {
    setLightboxRefineStatus(err.message || "上传失败", true);
  } finally {
    e.target.value = "";
  }
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

function clipboardImageFiles(event) {
  const dt = event.clipboardData;
  if (!dt) return [];
  const files = [];
  if (dt.files?.length) {
    for (const file of dt.files) {
      if (file?.type?.startsWith("image/")) files.push(file);
    }
  }
  if (!files.length && dt.items) {
    for (const item of dt.items) {
      if (item.kind === "file" && item.type?.startsWith("image/")) {
        const file = item.getAsFile();
        if (file) files.push(file);
      }
    }
  }
  return files;
}

document.getElementById("composer-box")?.addEventListener("paste", async (e) => {
  const files = clipboardImageFiles(e);
  if (!files.length) return;
  e.preventDefault();
  try {
    await addAttachmentFiles(files);
  } catch (err) {
    alert(err.message || "粘贴图片失败");
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
    const previewFirst = localStorage.getItem("ia_plan_preview_first");
    const previewCb = document.getElementById("plan-preview-first");
    if (previewCb && previewFirst === "1") previewCb.checked = true;
    previewCb?.addEventListener("change", () => {
      try {
        localStorage.setItem("ia_plan_preview_first", previewCb.checked ? "1" : "0");
      } catch (_) {}
    });
  } catch (_) {}
  document.getElementById("marketplace-id")?.addEventListener("change", () => {
    onMarketplaceChange().catch((e) => alert(e.message));
  });
  try {
    const savedSkin = localStorage.getItem("ia_cast_skin_preset");
    if (savedSkin && ["caucasian", "diverse", "black_only"].includes(savedSkin)) {
      state.castSkinPreset = savedSkin;
      const skinSel = document.getElementById("cast-skin-preset");
      if (skinSel) skinSel.value = savedSkin;
    }
    const savedBg = localStorage.getItem("ia_background_mode");
    if (savedBg && ["random", "solid_virtual", "real_environment"].includes(savedBg)) {
      const bgSel = document.getElementById("background-mode");
      if (bgSel) bgSel.value = savedBg;
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
