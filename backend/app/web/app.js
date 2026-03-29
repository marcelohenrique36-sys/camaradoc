const TOKEN_KEY = "camaradoc_token";

const state = {
  token: localStorage.getItem(TOKEN_KEY),
  currentUser: null,
  sectors: [],
  documentTypes: [],
  documents: [],
  users: [],
  auditLogs: [],
  stats: null,
};

const loginCard = document.querySelector("#login-card");
const appCard = document.querySelector("#app-card");
const flash = document.querySelector("#flash");
const documentsTableBody = document.querySelector("#documents-table-body");
const sectorsList = document.querySelector("#sectors-list");
const typesList = document.querySelector("#types-list");
const uploadSectorSelect = document.querySelector("#upload-sector");
const uploadTypeSelect = document.querySelector("#upload-document-type");
const searchSectorSelect = document.querySelector("#search-sector");
const searchTypeSelect = document.querySelector("#search-document-type");
const statsTotal = document.querySelector("#stats-total");
const statsOcr = document.querySelector("#stats-ocr");
const uploadForm = document.querySelector("#upload-form");
const sectorForm = document.querySelector("#sector-form");
const typeForm = document.querySelector("#type-form");
const currentRole = document.querySelector("#current-role");
const usersTableBody = document.querySelector("#users-table-body");
const auditTableBody = document.querySelector("#audit-table-body");
const auditFilterForm = document.querySelector("#audit-filter-form");

function escapeHtml(value) {
  return String(value || "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function showFlash(message, isError = false) {
  flash.classList.remove("hidden", "error");
  flash.textContent = message;
  if (isError) {
    flash.classList.add("error");
  }
  window.clearTimeout(showFlash._timer);
  showFlash._timer = window.setTimeout(() => flash.classList.add("hidden"), 3500);
}

function authHeaders() {
  return state.token ? { Authorization: `Bearer ${state.token}` } : {};
}

function isAdmin() {
  return state.currentUser?.role === "admin" || Boolean(state.currentUser?.is_admin);
}

function canWriteDocuments() {
  return ["admin", "protocolo_arquivo"].includes(state.currentUser?.role || "");
}

function applyPermissions() {
  uploadForm.classList.toggle("hidden", !canWriteDocuments());
  sectorForm.classList.toggle("hidden", !isAdmin());
  typeForm.classList.toggle("hidden", !isAdmin());
  document.querySelectorAll(".admin-only").forEach((element) => {
    element.classList.toggle("hidden", !isAdmin());
  });
  currentRole.textContent = state.currentUser?.role || "-";
}

async function apiRequest(path, options = {}) {
  const headers = {
    ...(options.headers || {}),
    ...authHeaders(),
  };

  const response = await fetch(path, { ...options, headers });
  if (!response.ok) {
    let detail = `Erro HTTP ${response.status}`;
    try {
      const data = await response.json();
      if (data?.detail) detail = data.detail;
    } catch (err) {
      console.warn("Falha ao interpretar erro da API", err);
    }
    throw new Error(detail);
  }
  return response;
}

function syncAuthUI() {
  if (state.token) {
    loginCard.classList.add("hidden");
    appCard.classList.remove("hidden");
  } else {
    appCard.classList.add("hidden");
    loginCard.classList.remove("hidden");
  }
}

function activateTab(tabId) {
  document.querySelectorAll(".tab").forEach((tab) => {
    tab.classList.toggle("active", tab.dataset.tab === tabId);
  });
  document.querySelectorAll(".tab-panel").forEach((panel) => {
    panel.classList.toggle("active", panel.id === `tab-${tabId}`);
  });
}

function getActiveSectors() {
  return state.sectors.filter((item) => item.is_active);
}

function getActiveTypes() {
  return state.documentTypes.filter((item) => item.is_active);
}

function renderSelectOptions() {
  uploadSectorSelect.innerHTML = getActiveSectors()
    .map((item) => `<option value="${item.id}">${escapeHtml(item.name)}</option>`)
    .join("");

  uploadTypeSelect.innerHTML = getActiveTypes()
    .map((item) => `<option value="${item.id}">${escapeHtml(item.name)}</option>`)
    .join("");

  searchSectorSelect.innerHTML =
    `<option value="">Todos</option>` +
    state.sectors
      .map(
        (item) =>
          `<option value="${item.id}">${escapeHtml(item.name)}${item.is_active ? "" : " (inativo)"}</option>`,
      )
      .join("");

  searchTypeSelect.innerHTML =
    `<option value="">Todos</option>` +
    state.documentTypes
      .map(
        (item) =>
          `<option value="${item.id}">${escapeHtml(item.name)}${item.is_active ? "" : " (inativo)"}</option>`,
      )
      .join("");
}

function renderSectors() {
  sectorsList.innerHTML = state.sectors
    .map((item) => {
      const activeText = item.is_active ? "ativo" : "inativo";
      const actions = isAdmin()
        ? `
          <div class="inline-actions">
            <button data-kind="sector" data-action="edit" data-id="${item.id}">Editar</button>
            <button data-kind="sector" data-action="disable" data-id="${item.id}">Inativar</button>
          </div>
        `
        : "";
      return `
        <li>
          <strong>${escapeHtml(item.name)}</strong> <span class="muted">(${activeText})</span><br />
          <span>${escapeHtml(item.description || "-")}</span>
          ${actions}
        </li>
      `;
    })
    .join("");
}

function renderTypes() {
  typesList.innerHTML = state.documentTypes
    .map((item) => {
      const activeText = item.is_active ? "ativo" : "inativo";
      const actions = isAdmin()
        ? `
          <div class="inline-actions">
            <button data-kind="type" data-action="edit" data-id="${item.id}">Editar</button>
            <button data-kind="type" data-action="disable" data-id="${item.id}">Inativar</button>
          </div>
        `
        : "";
      return `
        <li>
          <strong>${escapeHtml(item.name)}</strong> <span class="muted">(${activeText})</span><br />
          <span>${escapeHtml(item.description || "-")}</span>
          ${actions}
        </li>
      `;
    })
    .join("");
}

function renderStats() {
  const total = state.stats?.total_documents || 0;
  statsTotal.textContent = String(total);
  const statuses = state.stats?.ocr_status || {};
  const statusParts = Object.entries(statuses).map(([k, v]) => `${k}: ${v}`);
  statsOcr.textContent = statusParts.length
    ? `OCR -> ${statusParts.join(" | ")}`
    : "OCR -> sem dados";
}

function renderDocuments() {
  const sectorsMap = Object.fromEntries(state.sectors.map((s) => [s.id, s.name]));
  const typesMap = Object.fromEntries(state.documentTypes.map((t) => [t.id, t.name]));

  documentsTableBody.innerHTML = state.documents
    .map((doc) => {
      const statusClass = String(doc.ocr_status || "pending").toLowerCase();
      const errorInfo = doc.ocr_error
        ? `<br /><small>Erro: ${escapeHtml(doc.ocr_error)}</small>`
        : "";
      const adminActions = isAdmin()
        ? `
              <button data-kind="document" data-action="edit" data-id="${doc.id}">Editar</button>
              <button data-kind="document" data-action="replace" data-id="${doc.id}">Trocar PDF</button>
              <button data-kind="document" data-action="reprocess" data-id="${doc.id}">Reprocessar OCR</button>
              <button data-kind="document" data-action="disable" data-id="${doc.id}">Inativar</button>
        `
        : canWriteDocuments()
          ? `
              <button data-kind="document" data-action="edit" data-id="${doc.id}">Editar</button>
              <button data-kind="document" data-action="replace" data-id="${doc.id}">Trocar PDF</button>
              <button data-kind="document" data-action="reprocess" data-id="${doc.id}">Reprocessar OCR</button>
            `
          : "";
      return `
        <tr>
          <td>${doc.id}</td>
          <td>${escapeHtml(doc.title)}</td>
          <td>${escapeHtml(doc.number || "-")} / ${escapeHtml(doc.year || "-")}</td>
          <td>${escapeHtml(typesMap[doc.document_type_id] || String(doc.document_type_id))}</td>
          <td>${escapeHtml(sectorsMap[doc.sector_id] || String(doc.sector_id))}</td>
          <td>${escapeHtml(doc.status || "-")}</td>
          <td><span class="status-chip ${statusClass}">${escapeHtml(doc.ocr_status)}</span>${errorInfo}</td>
          <td>
            <div class="table-actions">
              <button data-kind="document" data-action="view" data-id="${doc.id}">Ver</button>
              <button data-kind="document" data-action="download" data-id="${doc.id}">Baixar</button>
              ${adminActions}
            </div>
          </td>
        </tr>
      `;
    })
    .join("");
}

function renderUsers() {
  if (!usersTableBody) return;

  usersTableBody.innerHTML = state.users
    .map((user) => {
      const statusText = user.is_active ? "ativo" : "inativo";
      const statusBtnText = user.is_active ? "Inativar" : "Ativar";
      return `
        <tr>
          <td>${user.id}</td>
          <td>${escapeHtml(user.name)}</td>
          <td>${escapeHtml(user.email)}</td>
          <td>${escapeHtml(user.role)}</td>
          <td>${statusText}</td>
          <td>
            <div class="table-actions">
              <button data-kind="user" data-action="change-role" data-id="${user.id}">Alterar perfil</button>
              <button data-kind="user" data-action="toggle-status" data-id="${user.id}" data-active="${user.is_active}">${statusBtnText}</button>
            </div>
          </td>
        </tr>
      `;
    })
    .join("");
}

function renderAuditLogs() {
  if (!auditTableBody) return;

  auditTableBody.innerHTML = state.auditLogs
    .map((entry) => {
      const dt = new Date(entry.created_at);
      return `
        <tr>
          <td>${escapeHtml(isNaN(dt.getTime()) ? entry.created_at : dt.toLocaleString("pt-BR"))}</td>
          <td>${escapeHtml(entry.user_email || "-")}</td>
          <td>${escapeHtml(entry.user_role || "-")}</td>
          <td>${escapeHtml(entry.action)}</td>
          <td>${escapeHtml(entry.entity_type)}</td>
          <td>${escapeHtml(entry.entity_id || "-")}</td>
          <td>${escapeHtml(entry.ip_address || "-")}</td>
        </tr>
      `;
    })
    .join("");
}

async function loadSectors() {
  const response = await apiRequest("/sectors?include_inactive=true");
  state.sectors = await response.json();
  renderSectors();
  renderSelectOptions();
}

async function loadCurrentUser() {
  const response = await apiRequest("/auth/me");
  state.currentUser = await response.json();
}

async function loadDocumentTypes() {
  const response = await apiRequest("/document-types?include_inactive=true");
  state.documentTypes = await response.json();
  renderTypes();
  renderSelectOptions();
}

async function loadStats() {
  const response = await apiRequest("/documents/stats");
  state.stats = await response.json();
  renderStats();
}

async function loadDocuments() {
  const form = document.querySelector("#document-search-form");
  const params = new URLSearchParams();

  const queryFields = {
    q: form.querySelector("#search-q").value.trim(),
    number: form.querySelector("#search-number").value.trim(),
    year: form.querySelector("#search-year").value.trim(),
    title: form.querySelector("#search-title").value.trim(),
    subject: form.querySelector("#search-subject").value.trim(),
    author_origin: form.querySelector("#search-author-origin").value.trim(),
    document_type_id: form.querySelector("#search-document-type").value.trim(),
    sector_id: form.querySelector("#search-sector").value.trim(),
    ocr_status: form.querySelector("#search-ocr-status").value.trim(),
    access_level: form.querySelector("#search-access-level").value.trim(),
  };

  Object.entries(queryFields).forEach(([key, value]) => {
    if (value) params.set(key, value);
  });
  params.set("include_inactive", "true");
  params.set("limit", "100");

  const response = await apiRequest(`/documents?${params.toString()}`);
  state.documents = await response.json();
  renderDocuments();
}

async function loadUsers() {
  if (!isAdmin()) return;
  const response = await apiRequest("/auth/users");
  state.users = await response.json();
  renderUsers();
}

async function loadAuditLogs() {
  if (!isAdmin()) return;
  const action = document.querySelector("#audit-action")?.value.trim();
  const entityType = document.querySelector("#audit-entity")?.value.trim();
  const params = new URLSearchParams({ limit: "100" });
  if (action) params.set("action", action);
  if (entityType) params.set("entity_type", entityType);

  const response = await apiRequest(`/audit-logs?${params.toString()}`);
  state.auditLogs = await response.json();
  renderAuditLogs();
}

async function openDocumentBlob(id, mode) {
  const response = await apiRequest(`/documents/${id}/${mode}`);
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);

  if (mode === "view") {
    window.open(url, "_blank", "noopener,noreferrer");
  } else {
    const a = document.createElement("a");
    a.href = url;
    a.download = `documento_${id}.pdf`;
    a.click();
  }

  window.setTimeout(() => URL.revokeObjectURL(url), 30000);
}

async function bootApp() {
  await loadCurrentUser();
  applyPermissions();
  await Promise.all([
    loadSectors(),
    loadDocumentTypes(),
    loadStats(),
    loadUsers(),
    loadAuditLogs(),
  ]);
  await loadDocuments();
}

async function refreshAll() {
  await Promise.all([
    loadSectors(),
    loadDocumentTypes(),
    loadStats(),
    loadDocuments(),
    loadUsers(),
    loadAuditLogs(),
  ]);
}

async function editSector(sectorId) {
  const current = state.sectors.find((item) => item.id === Number(sectorId));
  if (!current) return;
  const name = prompt("Novo nome do setor:", current.name);
  if (name === null) return;
  const description = prompt("Nova descricao do setor:", current.description || "");
  if (description === null) return;

  await apiRequest(`/sectors/${sectorId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name: name.trim(), description: description.trim() || null }),
  });
  showFlash("Setor atualizado com sucesso.");
  await refreshAll();
}

async function disableSector(sectorId) {
  if (!confirm("Confirmar inativacao do setor?")) return;
  await apiRequest(`/sectors/${sectorId}`, { method: "DELETE" });
  showFlash("Setor inativado.");
  await refreshAll();
}

async function editType(typeId) {
  const current = state.documentTypes.find((item) => item.id === Number(typeId));
  if (!current) return;
  const name = prompt("Novo nome do tipo:", current.name);
  if (name === null) return;
  const description = prompt("Nova descricao do tipo:", current.description || "");
  if (description === null) return;

  await apiRequest(`/document-types/${typeId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name: name.trim(), description: description.trim() || null }),
  });
  showFlash("Tipo atualizado com sucesso.");
  await refreshAll();
}

async function disableType(typeId) {
  if (!confirm("Confirmar inativacao do tipo?")) return;
  await apiRequest(`/document-types/${typeId}`, { method: "DELETE" });
  showFlash("Tipo inativado.");
  await refreshAll();
}

async function editDocument(documentId) {
  const response = await apiRequest(`/documents/${documentId}`);
  const current = await response.json();
  const admin = isAdmin();

  const title = prompt("Titulo:", current.title);
  if (title === null) return;
  const number = prompt("Numero:", current.number || "");
  if (number === null) return;
  const yearRaw = prompt("Ano:", current.year || "");
  if (yearRaw === null) return;
  const subject = prompt("Assunto:", current.subject || "");
  if (subject === null) return;
  const authorOrigin = prompt("Autor/Origem:", current.author_origin || "");
  if (authorOrigin === null) return;

  const payload = {
    title: title.trim(),
    number: number.trim() || null,
    year: yearRaw.trim() ? Number(yearRaw.trim()) : null,
    subject: subject.trim() || null,
    author_origin: authorOrigin.trim() || null,
  };

  if (admin) {
    const status = prompt("Status (ativo/inativo):", current.status || "ativo");
    if (status === null) return;
    const access = prompt(
      "Nivel de acesso (publico/interno/restrito):",
      current.access_level || "interno",
    );
    if (access === null) return;
    payload.status = status.trim() || "ativo";
    payload.access_level = access.trim() || "interno";
  }

  await apiRequest(`/documents/${documentId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  showFlash("Documento atualizado.");
  await refreshAll();
}

async function reprocessDocument(documentId) {
  await apiRequest(`/documents/${documentId}/reprocess-ocr`, { method: "POST" });
  showFlash("Documento reenfileirado para OCR.");
  await refreshAll();
}

async function disableDocument(documentId) {
  if (!confirm("Confirmar inativacao do documento?")) return;
  await apiRequest(`/documents/${documentId}`, { method: "DELETE" });
  showFlash("Documento inativado.");
  await refreshAll();
}

async function replaceDocumentFile(documentId) {
  const input = document.createElement("input");
  input.type = "file";
  input.accept = "application/pdf";

  input.onchange = async () => {
    const file = input.files?.[0];
    if (!file) return;
    const formData = new FormData();
    formData.append("file", file);

    try {
      await apiRequest(`/documents/${documentId}/replace-file`, {
        method: "POST",
        body: formData,
      });
      showFlash("Arquivo substituido. OCR reiniciado.");
      await refreshAll();
    } catch (error) {
      showFlash(error.message || "Erro ao substituir arquivo", true);
    }
  };

  input.click();
}

async function changeUserRole(userId) {
  const current = state.users.find((item) => item.id === Number(userId));
  if (!current) return;

  const role = prompt(
    "Novo perfil (admin | protocolo_arquivo | consulta_interna | consulta_publica):",
    current.role,
  );
  if (role === null) return;

  await apiRequest(`/auth/users/${userId}/role`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ role: role.trim() }),
  });
  showFlash("Perfil atualizado.");
  await refreshAll();
}

async function toggleUserStatus(userId, currentlyActive) {
  const activate = String(currentlyActive) !== "true";
  const confirmed = confirm(
    activate ? "Confirmar ativacao do usuario?" : "Confirmar inativacao do usuario?",
  );
  if (!confirmed) return;

  await apiRequest(`/auth/users/${userId}/status`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ is_active: activate }),
  });
  showFlash(activate ? "Usuario ativado." : "Usuario inativado.");
  await refreshAll();
}

document.querySelector("#login-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const email = document.querySelector("#login-email").value.trim();
  const password = document.querySelector("#login-password").value;

  try {
    const response = await fetch("/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    if (!response.ok) {
      let message = "Falha de autenticacao";
      try {
        const data = await response.json();
        if (data?.detail) message = data.detail;
      } catch (_err) {
        // no-op
      }
      throw new Error(message);
    }
    const data = await response.json();
    state.token = data.access_token;
    localStorage.setItem(TOKEN_KEY, state.token);
    syncAuthUI();
    await bootApp();
    showFlash("Login realizado com sucesso.");
  } catch (error) {
    showFlash(error.message || "Erro no login", true);
  }
});

document.querySelector("#logout-btn").addEventListener("click", () => {
  state.token = null;
  localStorage.removeItem(TOKEN_KEY);
  syncAuthUI();
  showFlash("Sessao encerrada.");
});

document.querySelectorAll(".tab").forEach((button) => {
  button.addEventListener("click", () => activateTab(button.dataset.tab));
});

document
  .querySelector("#document-search-form")
  .addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      await loadDocuments();
      showFlash("Busca atualizada.");
    } catch (error) {
      showFlash(error.message || "Erro ao buscar documentos", true);
    }
  });

document.querySelector("#upload-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const formData = new FormData(event.target);

  try {
    await apiRequest("/documents/upload", {
      method: "POST",
      body: formData,
    });
    event.target.reset();
    await refreshAll();
    showFlash("Documento enviado com sucesso.");
  } catch (error) {
    showFlash(error.message || "Erro no upload", true);
  }
});

document.querySelector("#sector-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const name = document.querySelector("#sector-name").value.trim();
  const description = document.querySelector("#sector-description").value.trim();

  try {
    await apiRequest("/sectors", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, description: description || null }),
    });
    event.target.reset();
    await refreshAll();
    showFlash("Setor cadastrado com sucesso.");
  } catch (error) {
    showFlash(error.message || "Erro ao cadastrar setor", true);
  }
});

document.querySelector("#type-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const name = document.querySelector("#type-name").value.trim();
  const description = document.querySelector("#type-description").value.trim();

  try {
    await apiRequest("/document-types", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, description: description || null }),
    });
    event.target.reset();
    await refreshAll();
    showFlash("Tipo cadastrado com sucesso.");
  } catch (error) {
    showFlash(error.message || "Erro ao cadastrar tipo", true);
  }
});

documentsTableBody.addEventListener("click", async (event) => {
  const target = event.target;
  if (!(target instanceof HTMLButtonElement)) return;
  const id = target.dataset.id;
  const action = target.dataset.action;
  if (!id || !action) return;

  try {
    if (action === "view" || action === "download") {
      await openDocumentBlob(id, action);
      return;
    }
    if (action === "edit") {
      await editDocument(id);
      return;
    }
    if (action === "reprocess") {
      await reprocessDocument(id);
      return;
    }
    if (action === "disable") {
      await disableDocument(id);
      return;
    }
    if (action === "replace") {
      await replaceDocumentFile(id);
      return;
    }
  } catch (error) {
    showFlash(error.message || "Erro na acao do documento", true);
  }
});

sectorsList.addEventListener("click", async (event) => {
  const target = event.target;
  if (!(target instanceof HTMLButtonElement)) return;
  const id = target.dataset.id;
  const action = target.dataset.action;
  if (!id || !action) return;

  try {
    if (action === "edit") {
      await editSector(id);
      return;
    }
    if (action === "disable") {
      await disableSector(id);
      return;
    }
  } catch (error) {
    showFlash(error.message || "Erro na acao do setor", true);
  }
});

typesList.addEventListener("click", async (event) => {
  const target = event.target;
  if (!(target instanceof HTMLButtonElement)) return;
  const id = target.dataset.id;
  const action = target.dataset.action;
  if (!id || !action) return;

  try {
    if (action === "edit") {
      await editType(id);
      return;
    }
    if (action === "disable") {
      await disableType(id);
      return;
    }
  } catch (error) {
    showFlash(error.message || "Erro na acao do tipo", true);
  }
});

usersTableBody?.addEventListener("click", async (event) => {
  const target = event.target;
  if (!(target instanceof HTMLButtonElement)) return;
  const id = target.dataset.id;
  const action = target.dataset.action;
  if (!id || !action) return;

  try {
    if (action === "change-role") {
      await changeUserRole(id);
      return;
    }
    if (action === "toggle-status") {
      await toggleUserStatus(id, target.dataset.active);
      return;
    }
  } catch (error) {
    showFlash(error.message || "Erro na acao de usuario", true);
  }
});

auditFilterForm?.addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    await loadAuditLogs();
    showFlash("Auditoria atualizada.");
  } catch (error) {
    showFlash(error.message || "Erro ao consultar auditoria", true);
  }
});

syncAuthUI();
if (state.token) {
  bootApp().catch((error) => {
    showFlash(error.message || "Sessao expirada", true);
    state.token = null;
    localStorage.removeItem(TOKEN_KEY);
    syncAuthUI();
  });
}
