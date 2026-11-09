/**
 * 视口懒加载：参考图、套图 job API、单张 gallery 缩略图。
 */
(function () {
  function scrollRoot() {
    return document.getElementById("thread-container");
  }

  let jobObs = null;
  let refImgObs = null;
  let slotObs = null;

  function ensureObservers() {
    const root = scrollRoot();
    if (!root) return false;
    if (jobObs) return true;

    const base = { root, rootMargin: "160px 0px" };

    refImgObs = new IntersectionObserver((entries) => {
      entries.forEach((e) => {
        if (window.__iaThreadAnchoring) return;
        if (!e.isIntersecting) return;
        const img = e.target;
        const src = img.dataset.src;
        if (src && !img.dataset.loaded) {
          img.src = src;
          img.dataset.loaded = "1";
        }
        refImgObs.unobserve(img);
      });
    }, base);

    jobObs = new IntersectionObserver((entries) => {
      entries.forEach((e) => {
        if (window.__iaThreadAnchoring) return;
        if (!e.isIntersecting) return;
        const grid = e.target;
        const jobId = Number(grid.dataset.jobGallery);
        if (!jobId) return;
        const body = grid.closest("[data-generation-job]");
        const statusEl = body?.querySelector(".gen-status-line");
        if (typeof window.onGalleryEnterViewport === "function") {
          window.onGalleryEnterViewport(jobId, grid, statusEl);
        }
      });
    }, base);

    slotObs = new IntersectionObserver((entries) => {
      entries.forEach((e) => {
        if (window.__iaThreadAnchoring) return;
        if (!e.isIntersecting) return;
        const slot = e.target;
        if (typeof window.hydrateGallerySlot === "function") {
          window.hydrateGallerySlot(slot);
        }
        slotObs.unobserve(slot);
      });
    }, { root, rootMargin: "100px 0px" });

    return true;
  }

  function observeRefImage(img) {
    if (!ensureObservers() || !img?.dataset?.src) return;
    refImgObs.observe(img);
  }

  function observeJobGallery(grid) {
    if (!ensureObservers() || !grid?.dataset?.jobGallery) return;
    jobObs.observe(grid);
  }

  function observeGallerySlot(slot) {
    if (!ensureObservers() || !slot?.dataset?.lazyUrl) return;
    slotObs.observe(slot);
  }

  function scan(rootEl) {
    if (!rootEl) return;
    ensureObservers();
    if (rootEl.matches?.("img.lazy-ref-img")) observeRefImage(rootEl);
    rootEl.querySelectorAll?.("img.lazy-ref-img").forEach(observeRefImage);
    rootEl.querySelectorAll?.(".gallery[data-job-gallery]").forEach(observeJobGallery);
    rootEl.querySelectorAll?.(".gallery-slot[data-lazy-url]").forEach(observeGallerySlot);
  }

  function isInViewport(el) {
    const root = scrollRoot();
    if (!el || !root) return false;
    const er = el.getBoundingClientRect();
    const rr = root.getBoundingClientRect();
    return er.bottom >= rr.top - 160 && er.top <= rr.bottom + 160;
  }

  window.LazyMedia = {
    scan,
    observeRefImage,
    observeJobGallery,
    observeGallerySlot,
    isInViewport,
  };
})();
