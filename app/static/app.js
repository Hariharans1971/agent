const state = {
  bootstrap: null,
  user: null,
  activeView: "workspace",
  activeCopilot: "marketing",
  activeTemplate: null,
  knowledge: [],
  drafts: [],
  lastResponse: null,
  conversations: {
    marketing: [],
    hr: [],
  },
};

const dom = {};

document.addEventListener("DOMContentLoaded", async () => {
  cacheDom();
  attachEvents();
  await refreshBootstrap();
  renderAll();
});

function cacheDom() {
  dom.loginModal = document.getElementById("login-modal");
  dom.loginForm = document.getElementById("login-form");
  dom.loginEmail = document.getElementById("login-email");
  dom.loginPassword = document.getElementById("login-password");
  dom.demoAccounts = document.getElementById("demo-accounts");
  dom.logoutButton = document.getElementById("logout-button");

  dom.userName = document.getElementById("user-name");
  dom.userRole = document.getElementById("user-role");
  dom.userEmail = document.getElementById("user-email");
  dom.runtimePill = document.getElementById("runtime-pill");
  dom.accessPill = document.getElementById("access-pill");
  dom.workspaceTitle = document.getElementById("workspace-title");
  dom.recentTasks = document.getElementById("recent-tasks");

  dom.marketingCard = document.getElementById("marketing-card");
  dom.hrCard = document.getElementById("hr-card");
  dom.chatThread = document.getElementById("chat-thread");
  dom.chatForm = document.getElementById("chat-form");
  dom.messageInput = document.getElementById("message-input");
  dom.templateChips = document.getElementById("template-chips");
  dom.activeTemplateLabel = document.getElementById("active-template-label");
  dom.sourceList = document.getElementById("source-list");
  dom.sessionHistory = document.getElementById("session-history");
  dom.outputNote = document.getElementById("output-note");

  dom.templateLibrary = document.getElementById("template-library");
  dom.templateSearch = document.getElementById("template-search");
  dom.knowledgeList = document.getElementById("knowledge-list");
  dom.knowledgeSearch = document.getElementById("knowledge-search");
  dom.savedDrafts = document.getElementById("saved-drafts");

  dom.uploadForm = document.getElementById("upload-form");
  dom.uploadFile = document.getElementById("upload-file");
  dom.uploadCategory = document.getElementById("upload-category");
  dom.uploadVisibility = document.getElementById("upload-visibility");
  dom.uploadNote = document.getElementById("upload-note");

  dom.knowledgeForm = document.getElementById("knowledge-form");
  dom.knowledgeTitle = document.getElementById("knowledge-title");
  dom.knowledgeCategory = document.getElementById("knowledge-category");
  dom.knowledgeVisibility = document.getElementById("knowledge-visibility");
  dom.knowledgeContent = document.getElementById("knowledge-content");
  dom.adminNote = document.getElementById("admin-note");
  dom.adminTemplateSummary = document.getElementById("admin-template-summary");
}

function attachEvents() {
  document.querySelectorAll(".nav-button").forEach((button) => {
    button.addEventListener("click", () => {
      state.activeView = button.dataset.view;
      renderViews();
    });
  });

  document.querySelectorAll(".team-card").forEach((button) => {
    button.addEventListener("click", () => switchCopilot(button.dataset.copilot));
  });

  document.getElementById("open-templates-button").addEventListener("click", () => {
    state.activeView = "templates";
    renderViews();
  });
  document.getElementById("clear-template-button").addEventListener("click", () => {
    state.activeTemplate = null;
    renderTemplateChips();
  });

  dom.chatForm.addEventListener("submit", handleChatSubmit);
  dom.loginForm.addEventListener("submit", handleLoginSubmit);
  dom.logoutButton.addEventListener("click", handleLogout);
  dom.templateSearch.addEventListener("input", renderTemplateLibrary);
  dom.knowledgeSearch.addEventListener("input", renderKnowledge);
  dom.uploadForm.addEventListener("submit", handleUploadSubmit);
  dom.knowledgeForm.addEventListener("submit", handleKnowledgeSave);

  document.getElementById("save-draft-button").addEventListener("click", saveLatestDraft);
  document.getElementById("copy-output-button").addEventListener("click", copyLatestOutput);
  document.getElementById("export-output-button").addEventListener("click", exportLatestOutput);
  document.getElementById("clear-drafts-button").addEventListener("click", clearDrafts);
}

async function apiFetch(path, options = {}) {
  const response = await fetch(path, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });

  const contentType = response.headers.get("content-type") || "";
  const payload = contentType.includes("application/json") ? await response.json() : await response.text();

  if (response.status === 401) {
    state.user = null;
    if (state.bootstrap) {
      state.bootstrap.authenticated = false;
    }
    dom.loginModal.classList.remove("hidden");
    renderSession();
  }

  if (!response.ok) {
    const errorMessage = typeof payload === "object" ? payload.error : "Request failed.";
    throw new Error(errorMessage);
  }

  return payload;
}

async function refreshBootstrap() {
  const payload = await apiFetch("/api/bootstrap", { headers: {} });
  state.bootstrap = payload;
  state.user = payload.user;
  state.knowledge = payload.knowledge || [];
  state.drafts = payload.drafts || [];

  if (!state.user) {
    state.activeCopilot = "marketing";
    dom.loginModal.classList.remove("hidden");
  } else {
    dom.loginModal.classList.add("hidden");
    if (state.user.role === "marketing") {
      state.activeCopilot = "marketing";
    }
    if (state.user.role === "hr" && state.activeCopilot !== "hr") {
      state.activeCopilot = "hr";
    }
  }
}

function renderAll() {
  renderViews();
  renderSession();
  renderTemplateChips();
  renderChat();
  renderSources();
  renderTemplateLibrary();
  renderKnowledge();
  renderDrafts();
  renderAdmin();
  renderVisibilityOptions();
  renderDemoAccounts();
}

function renderViews() {
  document.querySelectorAll(".view").forEach((view) => {
    view.classList.toggle("active", view.id === `${state.activeView}-view`);
  });
  document.querySelectorAll(".nav-button").forEach((button) => {
    button.classList.toggle("active", button.dataset.view === state.activeView);
  });
}

function renderSession() {
  dom.userName.textContent = state.user?.name || "Not signed in";
  dom.userRole.textContent = state.user ? `${capitalize(state.user.role)} access` : "Use a demo account to begin";
  dom.userEmail.textContent = state.user?.email || "No active session";
  dom.logoutButton.disabled = !state.user;

  const runtimeText = state.bootstrap?.runtimeMode === "live_openai" ? "Live OpenAI mode" : "Local grounded mode";
  dom.runtimePill.textContent = runtimeText;
  dom.accessPill.textContent = state.user ? `${capitalize(state.user.role)} session` : "Role unset";
  dom.workspaceTitle.textContent = `${capitalize(state.activeCopilot)} Copilot workspace`;
  dom.marketingCard.classList.toggle("active", state.activeCopilot === "marketing");
  dom.hrCard.classList.toggle("active", state.activeCopilot === "hr");
  dom.hrCard.classList.toggle("locked", !hasHrAccess());

  const recentTasks = state.bootstrap?.recentTasks?.[state.activeCopilot] || [];
  const fallback = state.activeCopilot === "marketing"
    ? ["Build a landing page for product data enrichment", "Write a LinkedIn post on taxonomy", "Create an SEO brief for catalog quality"]
    : ["Draft a JD for Product Data Analyst", "Prepare interview questions for B2B marketer", "Summarize a candidate resume"];
  const items = recentTasks.length ? recentTasks : fallback;
  dom.recentTasks.innerHTML = items.map((task) => `<li>${escapeHtml(task)}</li>`).join("");
}

function renderTemplateChips() {
  const templates = getTemplatesForActiveCopilot();
  dom.templateChips.innerHTML = templates
    .map((template) => {
      const active = state.activeTemplate === template.id ? "active" : "";
      return `<button class="chip ${active}" data-template-id="${template.id}" type="button">${escapeHtml(template.title)}</button>`;
    })
    .join("");

  dom.templateChips.querySelectorAll(".chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      state.activeTemplate = chip.dataset.templateId;
      const template = state.bootstrap.templates.find((item) => item.id === state.activeTemplate);
      dom.messageInput.value = template ? template.prompt : "";
      renderTemplateChips();
    });
  });

  const activeTemplate = state.bootstrap?.templates?.find((item) => item.id === state.activeTemplate);
  dom.activeTemplateLabel.textContent = activeTemplate ? `${activeTemplate.title} selected` : "No template selected";
}

function renderChat() {
  ensureWelcomeMessage(state.activeCopilot);
  const conversation = state.conversations[state.activeCopilot];
  dom.chatThread.innerHTML = conversation
    .map((item) => `<article class="message ${item.role}">${renderMarkdown(item.content)}</article>`)
    .join("");
  dom.chatThread.scrollTop = dom.chatThread.scrollHeight;

  dom.sessionHistory.innerHTML = conversation
    .filter((item) => item.role === "user")
    .slice(-6)
    .reverse()
    .map((item) => `<li>${escapeHtml(shorten(item.content, 72))}</li>`)
    .join("");
}

function renderSources() {
  const sources = state.lastResponse?.sources || [];
  if (!sources.length) {
    dom.sourceList.innerHTML = `<div class="source-item"><strong>No sources yet</strong><p>Run the copilot to see the context used in the latest answer.</p></div>`;
    dom.outputNote.textContent = "Your latest assistant draft will appear here after the first response.";
    return;
  }

  dom.sourceList.innerHTML = sources
    .map(
      (source) => `
        <article class="source-item">
          <strong>${escapeHtml(source.title)}</strong>
          <p>${escapeHtml(source.category)} · ${escapeHtml(source.path)}</p>
          <p>${escapeHtml(source.excerpt)}</p>
        </article>
      `
    )
    .join("");
  dom.outputNote.textContent = `Latest output came from ${state.lastResponse.mode === "live_openai" ? "the live OpenAI path" : "the server-grounded path"}.`;
}

function renderTemplateLibrary() {
  const query = dom.templateSearch.value.trim().toLowerCase();
  const templates = (state.bootstrap?.templates || []).filter((template) =>
    [template.title, template.description, template.team, template.prompt].join(" ").toLowerCase().includes(query)
  );

  dom.templateLibrary.innerHTML = templates
    .map(
      (template) => `
        <article class="template-card">
          <p class="eyebrow">${escapeHtml(capitalize(template.team))}</p>
          <strong>${escapeHtml(template.title)}</strong>
          <p>${escapeHtml(template.description)}</p>
          <p>${escapeHtml(template.prompt)}</p>
          <footer>
            <button class="secondary-button" data-template-use="${template.id}">Use Template</button>
            <span class="eyebrow">${escapeHtml(template.team)}</span>
          </footer>
        </article>
      `
    )
    .join("");

  dom.templateLibrary.querySelectorAll("[data-template-use]").forEach((button) => {
    button.addEventListener("click", () => {
      const template = state.bootstrap.templates.find((item) => item.id === button.dataset.templateUse);
      if (!template) return;
      if (template.team === "hr" && !hasHrAccess()) {
        alert("HR templates are restricted to HR or admin sessions.");
        return;
      }
      state.activeCopilot = template.team;
      state.activeTemplate = template.id;
      state.activeView = "workspace";
      dom.messageInput.value = template.prompt;
      renderAll();
    });
  });
}

function renderKnowledge() {
  const query = dom.knowledgeSearch.value.trim().toLowerCase();
  const documents = state.knowledge.filter((document) =>
    [document.title, document.category, document.source, document.path, document.excerpt, document.visibility]
      .join(" ")
      .toLowerCase()
      .includes(query)
  );

  dom.knowledgeList.innerHTML = documents
    .map(
      (document) => `
        <article class="knowledge-card">
          <p class="eyebrow">${escapeHtml(document.category)} · ${escapeHtml(document.visibility)}</p>
          <strong>${escapeHtml(document.title)}</strong>
          <p>${escapeHtml(document.source)} · ${escapeHtml(document.path)}</p>
          <p>${escapeHtml(document.excerpt)}</p>
        </article>
      `
    )
    .join("");
}

function renderDrafts() {
  if (!state.drafts.length) {
    dom.savedDrafts.innerHTML = `<article class="draft-card"><strong>No drafts saved yet</strong><p>Save an output from the workspace to keep it here for reuse.</p></article>`;
    return;
  }

  dom.savedDrafts.innerHTML = state.drafts
    .map(
      (draft) => `
        <article class="draft-card">
          <p class="eyebrow">${escapeHtml(capitalize(draft.copilot))} · ${escapeHtml(formatDate(draft.updatedAt || draft.createdAt))}</p>
          <strong>${escapeHtml(draft.title)}</strong>
          <p>${escapeHtml(shorten(draft.content, 240))}</p>
          <footer>
            <button class="secondary-button" data-draft-open="${draft.id}">Open</button>
            <button class="ghost-button" data-draft-delete="${draft.id}">Delete</button>
          </footer>
        </article>
      `
    )
    .join("");

  dom.savedDrafts.querySelectorAll("[data-draft-open]").forEach((button) => {
    button.addEventListener("click", () => {
      const draft = state.drafts.find((item) => String(item.id) === button.dataset.draftOpen);
      if (!draft) return;
      if (draft.copilot === "hr" && !hasHrAccess()) {
        alert("That draft belongs to the HR workspace and requires HR or admin access.");
        return;
      }
      state.activeCopilot = draft.copilot;
      state.activeView = "workspace";
      state.lastResponse = { answer: draft.content, sources: draft.sources || [], mode: draft.mode || "saved" };
      ensureWelcomeMessage(state.activeCopilot);
      state.conversations[state.activeCopilot].push({ role: "assistant", content: draft.content });
      renderAll();
    });
  });

  dom.savedDrafts.querySelectorAll("[data-draft-delete]").forEach((button) => {
    button.addEventListener("click", async () => {
      try {
        const payload = await apiFetch("/api/drafts/delete", {
          method: "POST",
          body: JSON.stringify({ draftId: Number(button.dataset.draftDelete) }),
        });
        state.drafts = payload.drafts || [];
        renderDrafts();
      } catch (error) {
        alert(error.message);
      }
    });
  });
}

function renderAdmin() {
  const isAdmin = state.user?.role === "admin";
  dom.knowledgeForm.querySelectorAll("input, textarea, select, button").forEach((element) => {
    element.disabled = !isAdmin;
  });
  dom.adminNote.textContent = isAdmin
    ? "Add approved notes and choose who can access them."
    : "This area is read-only unless you open the workspace as an admin user.";

  dom.adminTemplateSummary.innerHTML = (state.bootstrap?.templates || [])
    .map(
      (template) => `
        <article class="template-summary-item">
          <strong>${escapeHtml(template.title)}</strong>
          <p>${escapeHtml(capitalize(template.team))} · ${escapeHtml(template.description)}</p>
        </article>
      `
    )
    .join("");
}

function renderVisibilityOptions() {
  const options = state.bootstrap?.visibilityOptions || [];
  const optionMarkup = options
    .map((value) => `<option value="${escapeHtml(value)}">${escapeHtml(capitalize(value))}</option>`)
    .join("");
  dom.uploadVisibility.innerHTML = optionMarkup;
  dom.knowledgeVisibility.innerHTML = optionMarkup;
}

function renderDemoAccounts() {
  dom.demoAccounts.innerHTML = (state.bootstrap?.loginHints || [])
    .map(
      (hint) => `
        <button type="button" class="demo-account" data-demo-email="${escapeHtml(hint.email)}" data-demo-password="${escapeHtml(hint.password)}">
          <strong>${escapeHtml(capitalize(hint.role))} demo</strong>
          <p>${escapeHtml(hint.email)}</p>
          <p>${escapeHtml(hint.password)}</p>
        </button>
      `
    )
    .join("");

  dom.demoAccounts.querySelectorAll(".demo-account").forEach((button) => {
    button.addEventListener("click", () => {
      dom.loginEmail.value = button.dataset.demoEmail;
      dom.loginPassword.value = button.dataset.demoPassword;
    });
  });
}

function ensureWelcomeMessage(copilot) {
  if (state.conversations[copilot].length) return;
  const greeting =
    copilot === "marketing"
      ? "## Marketing Copilot\nTell me the service, audience, and asset type you want. I can generate landing pages, ad copy, LinkedIn posts, email drafts, SEO briefs, and campaign summaries."
      : "## HR Copilot\nTell me the role or hiring task you need. I can draft job descriptions, interview kits, onboarding plans, recruiter emails, and resume summaries.";
  state.conversations[copilot].push({ role: "assistant", content: greeting });
}

async function handleLoginSubmit(event) {
  event.preventDefault();
  try {
    await apiFetch("/api/login", {
      method: "POST",
      body: JSON.stringify({
        email: dom.loginEmail.value.trim(),
        password: dom.loginPassword.value,
      }),
    });
    dom.loginForm.reset();
    await refreshBootstrap();
    renderAll();
  } catch (error) {
    alert(error.message);
  }
}

async function handleLogout() {
  if (!state.user) return;
  try {
    await apiFetch("/api/logout", { method: "POST", body: JSON.stringify({}) });
  } catch (_) {
    // Ignore logout network noise and reset the client state anyway.
  }
  state.user = null;
  state.lastResponse = null;
  state.drafts = [];
  state.knowledge = [];
  state.conversations = { marketing: [], hr: [] };
  await refreshBootstrap();
  renderAll();
}

async function handleChatSubmit(event) {
  event.preventDefault();
  if (!state.user) {
    dom.loginModal.classList.remove("hidden");
    return;
  }
  if (state.activeCopilot === "hr" && !hasHrAccess()) {
    alert("HR workspace is restricted to HR or admin sessions.");
    return;
  }

  const message = dom.messageInput.value.trim();
  if (!message) return;

  ensureWelcomeMessage(state.activeCopilot);
  const conversation = state.conversations[state.activeCopilot];
  conversation.push({ role: "user", content: message });
  renderChat();
  dom.messageInput.value = "";
  setBusy(true);

  try {
    const payload = await apiFetch("/api/chat", {
      method: "POST",
      body: JSON.stringify({
        copilot: state.activeCopilot,
        message,
        templateId: state.activeTemplate,
        conversation,
      }),
    });

    conversation.push({ role: "assistant", content: payload.answer });
    state.lastResponse = payload;
    await refreshBootstrap();
    renderChat();
    renderSources();
    renderSession();
  } catch (error) {
    conversation.push({ role: "assistant", content: `## Error\n${error.message}` });
    renderChat();
  } finally {
    setBusy(false);
  }
}

async function saveLatestDraft() {
  if (!state.lastResponse?.answer) {
    alert("Run the copilot first so there is an output to save.");
    return;
  }
  try {
    const payload = await apiFetch("/api/drafts/save", {
      method: "POST",
      body: JSON.stringify({
        title: `${capitalize(state.activeCopilot)} draft`,
        copilot: state.activeCopilot,
        content: state.lastResponse.answer,
        sources: state.lastResponse.sources || [],
        mode: state.lastResponse.mode || "local_grounded",
      }),
    });
    state.drafts = payload.drafts || [];
    renderDrafts();
    alert("Draft saved.");
  } catch (error) {
    alert(error.message);
  }
}

async function clearDrafts() {
  if (!state.user) return;
  try {
    const payload = await apiFetch("/api/drafts/clear", {
      method: "POST",
      body: JSON.stringify({}),
    });
    state.drafts = payload.drafts || [];
    renderDrafts();
  } catch (error) {
    alert(error.message);
  }
}

async function handleKnowledgeSave(event) {
  event.preventDefault();
  if (state.user?.role !== "admin") {
    alert("Only admin users can add shared knowledge notes.");
    return;
  }
  try {
    const payload = await apiFetch("/api/admin/knowledge", {
      method: "POST",
      body: JSON.stringify({
        title: dom.knowledgeTitle.value.trim(),
        category: dom.knowledgeCategory.value.trim(),
        visibility: dom.knowledgeVisibility.value,
        content: dom.knowledgeContent.value.trim(),
      }),
    });
    state.knowledge = payload.knowledge || [];
    dom.knowledgeForm.reset();
    renderKnowledge();
    alert("Knowledge note saved.");
  } catch (error) {
    alert(error.message);
  }
}

async function handleUploadSubmit(event) {
  event.preventDefault();
  if (!state.user) {
    dom.loginModal.classList.remove("hidden");
    return;
  }

  const file = dom.uploadFile.files?.[0];
  if (!file) {
    alert("Choose a file to upload.");
    return;
  }

  try {
    dom.uploadNote.textContent = "Uploading and indexing document...";
    const contentBase64 = await fileToBase64(file);
    const payload = await apiFetch("/api/upload", {
      method: "POST",
      body: JSON.stringify({
        fileName: file.name,
        mimeType: file.type || "application/octet-stream",
        contentBase64,
        category: dom.uploadCategory.value.trim(),
        visibility: dom.uploadVisibility.value,
      }),
    });
    state.knowledge = payload.knowledge || [];
    dom.uploadForm.reset();
    renderVisibilityOptions();
    renderKnowledge();
    dom.uploadNote.textContent = "Document uploaded and indexed successfully.";
  } catch (error) {
    dom.uploadNote.textContent = error.message;
  }
}

function switchCopilot(copilot) {
  if (copilot === "hr" && !hasHrAccess()) {
    alert("HR workspace is restricted to HR or admin sessions.");
    return;
  }
  state.activeCopilot = copilot;
  state.activeTemplate = null;
  state.lastResponse = null;
  renderAll();
}

async function copyLatestOutput() {
  if (!state.lastResponse?.answer) {
    alert("No output available yet.");
    return;
  }
  await navigator.clipboard.writeText(state.lastResponse.answer);
  alert("Latest output copied.");
}

function exportLatestOutput() {
  if (!state.lastResponse?.answer) {
    alert("No output available yet.");
    return;
  }
  const blob = new Blob([state.lastResponse.answer], { type: "text/markdown;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `altiusnxt-${state.activeCopilot}-draft.md`;
  link.click();
  URL.revokeObjectURL(url);
}

function hasHrAccess() {
  return state.user?.role === "hr" || state.user?.role === "admin";
}

function getTemplatesForActiveCopilot() {
  return (state.bootstrap?.templates || []).filter((template) => template.team === state.activeCopilot);
}

function setBusy(value) {
  dom.messageInput.disabled = value;
  document.getElementById("send-button").disabled = value;
}

function renderMarkdown(markdown) {
  const lines = escapeHtml(markdown).split("\n");
  let html = "";
  let inList = false;

  const closeList = () => {
    if (inList) {
      html += "</ul>";
      inList = false;
    }
  };

  lines.forEach((line) => {
    if (line.startsWith("### ")) {
      closeList();
      html += `<h4>${line.slice(4)}</h4>`;
      return;
    }
    if (line.startsWith("## ")) {
      closeList();
      html += `<h3>${line.slice(3)}</h3>`;
      return;
    }
    if (line.startsWith("# ")) {
      closeList();
      html += `<h2>${line.slice(2)}</h2>`;
      return;
    }
    if (line.startsWith("- ")) {
      if (!inList) {
        html += "<ul>";
        inList = true;
      }
      html += `<li>${line.slice(2)}</li>`;
      return;
    }
    if (!line.trim()) {
      closeList();
      html += "<br>";
      return;
    }
    closeList();
    html += `<p>${line}</p>`;
  });

  closeList();
  return html;
}

function fileToBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const bytes = new Uint8Array(reader.result);
      let binary = "";
      const chunkSize = 0x8000;
      for (let index = 0; index < bytes.length; index += chunkSize) {
        binary += String.fromCharCode(...bytes.subarray(index, index + chunkSize));
      }
      resolve(btoa(binary));
    };
    reader.onerror = () => reject(new Error("Could not read the selected file."));
    reader.readAsArrayBuffer(file);
  });
}

function formatDate(value) {
  if (!value) return "Unknown time";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}

function shorten(value, maxLength) {
  return value.length > maxLength ? `${value.slice(0, maxLength - 1)}…` : value;
}

function capitalize(value) {
  return value.charAt(0).toUpperCase() + value.slice(1);
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}
