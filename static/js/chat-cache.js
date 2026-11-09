/**
 * 会话切换优化：内存缓存对话详情 / 生图 job / 已渲染 DOM，减少重复请求与图片重载。
 */
(function () {
  const MAX_CONV_DETAILS = 40;
  const MAX_THREAD_FRAGMENTS = 15;
  const CONV_STALE_MS = 120_000;
  const JOB_STALE_MS = 45_000;

  const convDetails = new Map();
  const threadFragments = new Map();
  const threadScroll = new Map();
  const jobCache = new Map();
  const lruConv = [];

  function touchLru(id) {
    const i = lruConv.indexOf(id);
    if (i >= 0) lruConv.splice(i, 1);
    lruConv.push(id);
    while (lruConv.length > MAX_CONV_DETAILS) {
      const old = lruConv.shift();
      convDetails.delete(old);
      threadFragments.delete(old);
      threadScroll.delete(old);
    }
    while (threadFragments.size > MAX_THREAD_FRAGMENTS) {
      const drop = threadFragments.keys().next().value;
      threadFragments.delete(drop);
      threadScroll.delete(drop);
    }
  }

  function getDetail(convId) {
    return convDetails.get(convId) || null;
  }

  function setDetail(convId, detail) {
    if (!convId || !detail) return;
    convDetails.set(convId, {
      detail,
      fetchedAt: Date.now(),
    });
    touchLru(convId);
  }

  function isDetailStale(convId) {
    const row = convDetails.get(convId);
    if (!row) return true;
    return Date.now() - row.fetchedAt > CONV_STALE_MS;
  }

  /** 仅丢弃 API 详情缓存；已 park 的 DOM 片段保留，便于秒开切换。 */
  function invalidateConversation(convId) {
    convDetails.delete(convId);
  }

  function parkThread(convId, messagesEl, scrollEl) {
    if (!convId || !messagesEl?.childElementCount) return;
    if (scrollEl) threadScroll.set(convId, scrollEl.scrollTop);
    const frag = document.createDocumentFragment();
    while (messagesEl.firstChild) frag.appendChild(messagesEl.firstChild);
    threadFragments.set(convId, frag);
    touchLru(convId);
  }

  function restoreThread(convId, messagesEl) {
    const frag = threadFragments.get(convId);
    if (!frag || !messagesEl) return false;
    messagesEl.innerHTML = "";
    messagesEl.appendChild(frag);
    return true;
  }

  function hasThread(convId) {
    const frag = threadFragments.get(convId);
    return !!frag && frag.childElementCount > 0;
  }

  function clearThreadFragment(convId) {
    threadFragments.delete(convId);
    threadScroll.delete(convId);
  }

  function getJob(jobId) {
    const row = jobCache.get(jobId);
    if (!row) return null;
    if (Date.now() - row.fetchedAt > JOB_STALE_MS) return null;
    return row.job;
  }

  function setJob(jobId, job) {
    if (!jobId || !job) return;
    jobCache.set(jobId, { job, fetchedAt: Date.now() });
  }

  function invalidateJob(jobId) {
    jobCache.delete(jobId);
  }

  window.ChatCache = {
    CONV_STALE_MS,
    getDetail,
    setDetail,
    isDetailStale,
    invalidateConversation,
    parkThread,
    restoreThread,
    hasThread,
    clearThreadFragment,
    getJob,
    setJob,
    invalidateJob,
  };
})();
