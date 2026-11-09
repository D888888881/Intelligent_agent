/** 轻量 Markdown → HTML（先转义，防 XSS） */

function escapeHtml(text) {
  return String(text)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function inlineMarkdown(escaped) {
  return escaped
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/__(.+?)__/g, "<strong>$1</strong>")
    .replace(/\*(.+?)\*/g, "<em>$1</em>")
    .replace(/_([^_]+)_/g, "<em>$1</em>")
    .replace(/`([^`]+)`/g, "<code class=\"md-code\">$1</code>");
}

function renderMarkdown(text) {
  if (text == null || text === "") return "";

  const lines = escapeHtml(text).split("\n");
  const out = [];
  let inList = false;

  const closeList = () => {
    if (inList) {
      out.push("</ul>");
      inList = false;
    }
  };

  for (let line of lines) {
    const trimmed = line.trimEnd();
    const bare = trimmed.trim();

    if (bare === "---" || bare === "***") {
      closeList();
      out.push('<hr class="md-hr" />');
      continue;
    }

    if (/^###\s+/.test(bare)) {
      closeList();
      out.push(`<h3 class="md-h3">${inlineMarkdown(bare.slice(4))}</h3>`);
      continue;
    }
    if (/^##\s+/.test(bare)) {
      closeList();
      out.push(`<h2 class="md-h2">${inlineMarkdown(bare.slice(3))}</h2>`);
      continue;
    }
    if (/^#\s+/.test(bare)) {
      closeList();
      out.push(`<h1 class="md-h1">${inlineMarkdown(bare.slice(2))}</h1>`);
      continue;
    }

    if (/^[-*]\s+/.test(bare)) {
      if (!inList) {
        out.push('<ul class="md-ul">');
        inList = true;
      }
      out.push(`<li>${inlineMarkdown(bare.replace(/^[-*]\s+/, ""))}</li>`);
      continue;
    }

    if (bare === "") {
      closeList();
      continue;
    }

    closeList();
    out.push(`<p class="md-p">${inlineMarkdown(trimmed)}</p>`);
  }

  closeList();
  return out.join("");
}

function setMessageContent(el, text, role) {
  if (!el) return;
  const isAssistant = role === "assistant";
  if (!isAssistant) {
    el.classList.remove("md-body");
    el.textContent = text || "";
    return;
  }
  el.classList.add("md-body");
  el.innerHTML = renderMarkdown(text || "");
}
