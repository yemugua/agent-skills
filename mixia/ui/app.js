"use strict";

const tauri = window.__TAURI__;
if (!tauri) {
  document.body.textContent = "Tauri 运行时不可用，请通过应用启动。";
  throw new Error("Tauri runtime unavailable");
}

const { invoke } = tauri.core;
const { listen } = tauri.event;

const $ = (id) => document.getElementById(id);

const KIND_LABELS = {
  image: "图片",
  video: "视频",
  document: "文档",
  audio: "音频",
  other: "文件",
};

const IDLE_MS = 10 * 60 * 1000;
const THUMB_CONCURRENCY = 4;

const JOB_LABELS = {
  import: { doing: "正在加密导入…", done: "正在写入加密索引…" },
  export: { doing: "正在解密导出…", done: "正在收尾…" },
};

const state = {
  view: "welcome",
  vaultPath: null,
  lastVault: null,
  createPath: null,
  items: [],
  query: "",
  thumbs: new Map(),
  thumbQueue: [],
  thumbActive: 0,
  busy: false,
  busyKind: null,
  pendingSources: [],
  // 当前走进来的那一层文件夹；"" 表示保险库根目录
  cwd: "",
  // 勾选待批量删除的条目 id
  selected: new Set(),
  idleTimer: null,
  renameId: null,
  confirmAction: null,
};

const thumbObserver = new IntersectionObserver(
  (entries) => {
    for (const entry of entries) {
      if (!entry.isIntersecting) continue;
      const img = entry.target;
      thumbObserver.unobserve(img);
      queueThumb(img.dataset.thumbId, img);
    }
  },
  { rootMargin: "240px" }
);

function setView(view) {
  state.view = view;
  document.querySelectorAll(".view").forEach((el) => {
    el.hidden = el.id !== `view-${view}`;
  });
  if (view !== "vault") {
    clearTimeout(state.idleTimer);
    state.idleTimer = null;
    $("drop-overlay").hidden = true;
    $("import-panel").hidden = true;
  } else {
    resetIdleTimer();
  }
  // 库内视图的顶栏里已经有一个，浮在右上角的那个只在其他视图出现
  $("theme-toggle-page").hidden = view === "vault";
}

function showWelcome(lastVault) {
  state.lastVault = lastVault || null;
  setView("welcome");
  $("last-vault").hidden = !state.lastVault;
  if (state.lastVault) {
    $("last-vault-path").textContent = state.lastVault;
    $("last-vault-path").title = state.lastVault;
  }
}

function vaultName(path) {
  if (!path) return "保险库";
  const parts = path.split(/[\\/]+/).filter(Boolean);
  return parts[parts.length - 1] || "保险库";
}

function showVault() {
  $("vault-name").textContent = vaultName(state.vaultPath);
  $("vault-name").title = state.vaultPath || "";
  $("vault-meta").title = state.vaultPath || "";
  state.query = "";
  $("search").value = "";
  state.cwd = "";
  setView("vault");
  render();
}

async function loadItems() {
  state.items = await invoke("list_items");
  state.thumbs.clear();
  state.thumbQueue = [];
  // 勾选过的条目可能已经不在了（别处删掉、导入失败回滚），别留下幽灵选择
  const alive = new Set(state.items.map((item) => item.id));
  for (const id of [...state.selected]) {
    if (!alive.has(id)) state.selected.delete(id);
  }
}

function filteredItems() {
  const query = state.query.trim().toLowerCase();
  if (!query) return state.items;
  // 也匹配相对路径，这样搜目录名能把整个文件夹筛出来
  return state.items.filter(
    (item) =>
      item.name.toLowerCase().includes(query) ||
      (item.path || "").toLowerCase().includes(query)
  );
}

function isUnder(item, dir) {
  const path = item.dir || "";
  return !dir || path === dir || path.startsWith(`${dir}/`);
}

/// 当前这一层里有什么：直接放着的文件 + 下一级的文件夹（计数和大小按整棵子树汇总）
function currentScope() {
  const cwd = state.cwd;
  const prefix = cwd ? `${cwd}/` : "";
  const files = [];
  const found = new Map();
  for (const item of state.items) {
    const path = item.dir || "";
    if (path === cwd) {
      files.push(item);
      continue;
    }
    if (cwd && !path.startsWith(prefix)) continue;
    const name = path.slice(prefix.length).split("/")[0];
    const full = `${prefix}${name}`;
    let entry = found.get(name);
    if (!entry) {
      entry = { name, path: full, count: 0, bytes: 0 };
      found.set(name, entry);
    }
    entry.count += 1;
    entry.bytes += item.size || 0;
  }
  const dirs = [...found.values()].sort((a, b) => a.name.localeCompare(b.name, "zh-Hans-CN"));
  files.sort((a, b) => a.name.localeCompare(b.name, "zh-Hans-CN"));
  return { files, dirs };
}

function subtreeItems(dir) {
  return state.items.filter((item) => isUnder(item, dir));
}

function subtreeIds(dir) {
  return subtreeItems(dir).map((item) => item.id);
}

function render() {
  const host = $("groups");
  host.replaceChildren();
  const query = state.query.trim();
  const isEmpty = state.items.length === 0;

  $("empty-state").hidden = !isEmpty;
  renderBreadcrumbs();
  $("no-results").hidden = true;
  $("folder-empty").hidden = true;

  let shown = 0;
  if (!isEmpty) {
    if (query) {
      // 搜索是全库范围的：直接平铺命中结果，卡片上标出它原来在哪个文件夹里
      const hits = filteredItems();
      shown = hits.length;
      $("no-results").hidden = hits.length > 0;
      if (hits.length > 0) host.append(createGrid(hits, true));
    } else {
      const scope = currentScope();
      shown = scope.files.length + scope.dirs.length;
      $("folder-empty").hidden = shown > 0;
      if (shown > 0) {
        const grid = document.createElement("div");
        grid.className = "grid";
        grid.replaceChildren(
          ...scope.dirs.map((node) => createFolderTile(node)),
          ...scope.files.map((item) => createCard(item, false))
        );
        host.append(grid);
      }
    }
  }
  updateMeta(shown);
  updateSelectionBar();
}

function createGrid(items, showPath) {
  const grid = document.createElement("div");
  grid.className = "grid";
  grid.replaceChildren(...items.map((item) => createCard(item, showPath)));
  return grid;
}

function renderBreadcrumbs() {
  const nav = $("breadcrumbs");
  nav.replaceChildren();
  const query = state.query.trim();
  nav.hidden = Boolean(query) || !state.cwd;
  if (nav.hidden) return;

  const up = document.createElement("button");
  up.type = "button";
  up.className = "crumb crumb-up";
  up.textContent = "‹ 上一级";
  up.title = "回到上一层文件夹";
  up.addEventListener("click", goUp);
  nav.append(up);

  const crumb = (label, dir, current) => {
    const sep = document.createElement("span");
    sep.className = "crumb-sep";
    sep.textContent = "›";
    nav.append(sep);
    const chip = document.createElement(current ? "span" : "button");
    chip.className = current ? "crumb crumb-current" : "crumb";
    if (!current) chip.type = "button";
    chip.textContent = label;
    chip.title = dir ? `到 ${dir}` : "保险库根目录";
    if (!current) chip.addEventListener("click", () => enterFolder(dir));
    nav.append(chip);
  };

  crumb(vaultName(state.vaultPath) || "全部", "", false);
  const parts = state.cwd.split("/").filter(Boolean);
  parts.forEach((name, index) => {
    crumb(name, parts.slice(0, index + 1).join("/"), index === parts.length - 1);
  });
}

function enterFolder(dir) {
  state.cwd = dir;
  render();
  const content = document.querySelector("#view-vault .content");
  if (content) content.scrollTop = 0;
}

function goUp() {
  const parts = (state.cwd || "").split("/").filter(Boolean);
  parts.pop();
  enterFolder(parts.join("/"));
}

function createFolderTile(node) {
  const tile = document.createElement("article");
  tile.className = "card card-folder";
  tile.dataset.kind = "folder";
  const ids = subtreeIds(node.path);
  const picked = ids.length > 0 && ids.every((id) => state.selected.has(id));
  if (picked) tile.classList.add("selected");

  const check = document.createElement("input");
  check.type = "checkbox";
  check.className = "card-check";
  check.checked = picked;
  check.title = "选中整个文件夹，连里面的子文件夹一起";
  check.setAttribute("aria-label", `选择文件夹 ${node.name}`);
  check.addEventListener("click", (event) => event.stopPropagation());
  check.addEventListener("change", () => {
    for (const id of ids) {
      if (check.checked) state.selected.add(id);
      else state.selected.delete(id);
    }
    tile.classList.toggle("selected", check.checked);
    updateSelectionBar();
  });

  const cover = document.createElement("div");
  cover.className = "thumb folder-cover";
  cover.title = `打开 ${node.name}`;
  cover.innerHTML = `
    <svg viewBox="0 0 48 40" width="58" height="48" aria-hidden="true">
      <path d="M2 9a3 3 0 0 1 3-3h11.5a3 3 0 0 1 2.5 1.3L21.4 10H43a3 3 0 0 1 3 3v20a3 3 0 0 1-3 3H5a3 3 0 0 1-3-3Z"
        fill="var(--folder-back)"></path>
      <path d="M2 15h44v18a3 3 0 0 1-3 3H5a3 3 0 0 1-3-3Z" fill="var(--folder-front)"></path>
    </svg>`;
  cover.addEventListener("click", () => enterFolder(node.path));

  const actions = document.createElement("div");
  actions.className = "card-actions";
  actions.append(
    actionButton("打开", () => enterFolder(node.path)),
    actionButton("删除文件夹", () => confirmDeleteFolder(node), "danger")
  );
  cover.append(actions);

  const meta = document.createElement("div");
  meta.className = "card-meta";
  const name = document.createElement("div");
  name.className = "card-name";
  name.textContent = node.name;
  name.title = node.path;
  const info = document.createElement("div");
  info.className = "card-sub";
  info.textContent = `${node.count} 个 · ${formatSize(node.bytes)}`;
  meta.append(name, info);

  tile.append(check, cover, meta);
  tile.addEventListener("dblclick", () => enterFolder(node.path));
  return tile;
}

function updateMeta(filteredCount) {
  const total = state.items.length;
  $("vault-meta").textContent = `${total} 个文件 · 本地加密`;
  if (state.query && filteredCount !== total) {
    $("status-text").textContent = `筛选出 ${filteredCount} 个文件，共 ${total} 个`;
  } else {
    $("status-text").textContent = `已解锁 · ${total} 个文件`;
  }
}

function createCard(item, showPath) {
  const card = document.createElement("article");
  card.className = "card";
  card.dataset.kind = item.kind;
  if (state.selected.has(item.id)) card.classList.add("selected");

  const check = document.createElement("input");
  check.type = "checkbox";
  check.className = "card-check";
  check.checked = state.selected.has(item.id);
  check.title = "选中，用于批量删除";
  check.setAttribute("aria-label", `选择 ${item.name}`);
  check.addEventListener("click", (event) => event.stopPropagation());
  check.addEventListener("change", () => {
    if (check.checked) state.selected.add(item.id);
    else state.selected.delete(item.id);
    card.classList.toggle("selected", check.checked);
    updateSelectionBar();
  });

  const thumb = document.createElement("div");
  thumb.className = "thumb";
  thumb.title = "点击打开";
  thumb.addEventListener("click", () => openItem(item));

  if (item.hasThumb) {
    const img = document.createElement("img");
    img.alt = "";
    img.loading = "lazy";
    const cached = state.thumbs.get(item.id);
    if (cached) {
      img.src = cached;
    } else {
      img.dataset.thumbId = item.id;
      thumbObserver.observe(img);
    }
    thumb.append(img);
  } else {
    const tile = document.createElement("div");
    tile.className = "tile";
    tile.textContent = item.ext
      ? item.ext.toUpperCase().slice(0, 5)
      : KIND_LABELS[item.kind] || "文件";
    thumb.append(tile);
  }

  const actions = document.createElement("div");
  actions.className = "card-actions";
  actions.append(
    actionButton("打开", () => openItem(item)),
    actionButton("导出", () => exportItem(item)),
    actionButton("重命名", () => openRename(item)),
    actionButton("删除", () => confirmDelete(item), "danger")
  );
  thumb.append(actions);

  const meta = document.createElement("div");
  meta.className = "card-meta";
  const name = document.createElement("div");
  name.className = "card-name";
  name.textContent = item.name;
  name.title = item.name;
  const sub = document.createElement("div");
  sub.className = "card-sub";
  sub.textContent = `${KIND_LABELS[item.kind] || "文件"} · ${formatSize(item.size)}`;
  meta.append(name, sub);
  if (showPath && item.dir) {
    // 搜索是全库范围的，命中项得让人一眼看出它原来在哪个文件夹里
    const where = document.createElement("div");
    where.className = "card-where";
    where.textContent = item.dir;
    where.title = item.dir;
    meta.append(where);
  }

  card.append(check, thumb, meta);
  return card;
}

function actionButton(label, handler, extraClass) {
  const button = document.createElement("button");
  button.type = "button";
  button.textContent = label;
  if (extraClass) button.classList.add(extraClass);
  button.addEventListener("click", (event) => {
    event.stopPropagation();
    handler();
  });
  return button;
}

function formatSize(bytes) {
  if (!Number.isFinite(bytes) || bytes < 1024) return `${bytes || 0} B`;
  const units = ["KB", "MB", "GB", "TB"];
  let value = bytes / 1024;
  let index = 0;
  while (value >= 1024 && index < units.length - 1) {
    value /= 1024;
    index += 1;
  }
  return `${value >= 10 ? Math.round(value) : value.toFixed(1)} ${units[index]}`;
}

function queueThumb(id, img) {
  if (!id) return;
  const cached = state.thumbs.get(id);
  if (cached) {
    img.src = cached;
    return;
  }
  state.thumbQueue.push({ id, img });
  pumpThumbs();
}

function pumpThumbs() {
  while (state.thumbActive < THUMB_CONCURRENCY && state.thumbQueue.length > 0) {
    const { id, img } = state.thumbQueue.shift();
    state.thumbActive += 1;
    invoke("get_thumb", { id })
      .then((data) => {
        if (!data) return;
        const url = `data:image/jpeg;base64,${data}`;
        state.thumbs.set(id, url);
        if (img.isConnected) img.src = url;
      })
      .catch(() => {})
      .finally(() => {
        state.thumbActive -= 1;
        pumpThumbs();
      });
  }
}

async function openItem(item) {
  try {
    await invoke("open_item", { id: item.id });
    toast("已用系统默认程序打开；锁定时会删除临时副本", "info", 5200);
    resetIdleTimer();
  } catch (err) {
    toast(friendlyError(err, "打开失败"), "error", 7000);
  }
}

async function exportItem(item) {
  try {
    const saved = await invoke("export_item", { id: item.id });
    if (saved) toast(`已导出到 ${saved}`, "success", 6000);
  } catch (err) {
    toast(friendlyError(err, "导出失败"), "error", 7000);
  }
}

function confirmDelete(item) {
  askConfirm(
    "删除文件？",
    `“${item.name}”将从保险库中永久删除，无法恢复。`,
    "删除",
    async () => {
      try {
        await invoke("delete_item", { id: item.id });
        state.items = state.items.filter((entry) => entry.id !== item.id);
        state.thumbs.delete(item.id);
        state.selected.delete(item.id);
        render();
        toast("已删除", "success");
      } catch (err) {
        toast(friendlyError(err, "删除失败"), "error");
      }
    }
  );
}

/* ---------- 多选与批量删除 ---------- */

function selectedItems() {
  return state.items.filter((item) => state.selected.has(item.id));
}

function selectAllVisible() {
  const ids = selectableIds();
  if (ids.length === 0) {
    toast("当前没有可选中的文件", "info");
    return;
  }
  const allPicked = ids.every((id) => state.selected.has(id));
  if (allPicked) ids.forEach((id) => state.selected.delete(id));
  else ids.forEach((id) => state.selected.add(id));
  render();
}

/// 当前这一层管得着的文件：搜索时是全库命中结果，平时是走进来的这个文件夹（含子文件夹）里的全部
function selectableIds() {
  if (state.query.trim()) return filteredItems().map((item) => item.id);
  return state.items.filter((item) => isUnder(item, state.cwd)).map((item) => item.id);
}

function clearSelection() {
  if (state.selected.size === 0) return;
  state.selected.clear();
  render();
}

function updateSelectionBar() {
  const count = state.selected.size;
  const selectable = selectableIds();
  const allPicked = selectable.length > 0 && selectable.every((id) => state.selected.has(id));
  const toggle = $("btn-select-all");
  toggle.textContent = allPicked ? "取消全选" : "全选";
  toggle.disabled = state.busy || selectable.length === 0;
  toggle.title = state.query.trim()
    ? "选中本次搜索命中的全部文件；再点一次取消"
    : state.cwd
      ? `选中「${state.cwd}」里的全部文件，连子文件夹里的也算；再点一次取消`
      : "选中保险库里的全部文件；再点一次取消";

  const bar = $("selection-bar");
  if (count === 0) {
    bar.hidden = true;
    return;
  }
  bar.hidden = state.view !== "vault";
  const bytes = selectedItems().reduce((sum, item) => sum + (item.size || 0), 0);
  $("selection-text").textContent = `已选 ${count} 个 · ${formatSize(bytes)}`;
  $("btn-select-none").disabled = state.busy;
  $("btn-delete-selected").disabled = state.busy;
}

function confirmDeleteSelected() {
  const items = selectedItems();
  if (items.length === 0) {
    toast("先勾选要删除的文件", "info");
    return;
  }
  const bytes = items.reduce((sum, item) => sum + (item.size || 0), 0);
  const names = items
    .slice(0, 3)
    .map((item) => `“${item.name}”`)
    .join("、");
  const more = items.length > 3 ? ` 等 ${items.length} 个文件` : "";
  askConfirm(
    `删除 ${items.length} 个文件？`,
    `将从保险库永久删除 ${names}${more}（共 ${formatSize(
      bytes
    )}），无法恢复。保险库里只有一份密文：如果对应的原件之前已经被删掉，这些文件就彻底没有了。`,
    `删除 ${items.length} 个`,
    deleteSelectedItems
  );
}

/// 整个文件夹一次删掉：连里面的子文件夹一起，只删保险库里的密文
function confirmDeleteFolder(node) {
  const items = subtreeItems(node.path);
  if (items.length === 0) {
    toast(`「${node.name}」里已经没有文件了`, "info");
    return;
  }
  const bytes = items.reduce((sum, item) => sum + (item.size || 0), 0);
  const ids = items.map((item) => item.id);
  askConfirm(
    `删除文件夹「${node.name}」？`,
    `保险库里这个文件夹下的 ${items.length} 个文件（共 ${formatSize(
      bytes
    )}）会连里面的子文件夹一起永久删除，无法恢复。磁盘上你自己的文件夹不动；但如果对应的原件之前已经被删掉，这些文件就彻底没有了。`,
    `删除 ${items.length} 个文件`,
    async () => {
      await runBatchDelete(ids, null);
    }
  );
}

async function deleteSelectedItems() {
  const ids = [...state.selected];
  if (ids.length === 0) return;
  await runBatchDelete(ids, $("btn-delete-selected"));
}

async function runBatchDelete(ids, button) {
  state.busy = true;
  updateImportControls();
  setBusy(button, true, "删除中…");
  try {
    const report = await invoke("delete_items", { ids });
    for (const id of ids) state.selected.delete(id);
    await loadItems();
    render();
    if (report.deleted > 0) {
      toast(
        `已从保险库删除 ${report.deleted} 个文件，共 ${formatSize(report.bytes)}`,
        "success",
        6500
      );
    } else if (!report.failed || report.failed.length === 0) {
      toast("这些文件已经不在保险库里了", "info");
    }
    if (report.failed && report.failed.length > 0) {
      toast(
        `${report.failed.length} 个文件没有删除：${report.failed[0]}`,
        "error",
        9000
      );
    }
  } catch (err) {
    toast(friendlyError(err, "删除失败"), "error", 7000);
  } finally {
    state.busy = false;
    updateImportControls();
    setBusy(button, false);
  }
}

function askConfirm(title, text, okLabel, action, okClass = "btn-danger") {
  $("confirm-title").textContent = title;
  $("confirm-text").textContent = text;
  $("confirm-ok").textContent = okLabel;
  $("confirm-ok").className = `btn ${okClass}`;
  state.confirmAction = action;
  if (!$("confirm-dialog").open) $("confirm-dialog").showModal();
}

async function runConfirmedAction() {
  const action = state.confirmAction;
  $("confirm-dialog").close();
  if (action) await action();
}

function openRename(item) {
  state.renameId = item.id;
  $("rename-input").value = item.name;
  hideError("rename");
  if (!$("rename-dialog").open) $("rename-dialog").showModal();
  setTimeout(() => {
    const input = $("rename-input");
    input.focus();
    input.select();
  }, 30);
}

async function submitRename(event) {
  event.preventDefault();
  const id = state.renameId;
  if (!id) return;
  const name = $("rename-input").value.trim();
  hideError("rename");
  if (!name) {
    showError("rename", "名称不能为空");
    return;
  }
  const item = state.items.find((entry) => entry.id === id);
  if (item && item.name === name) {
    $("rename-dialog").close();
    return;
  }

  const button = $("rename-save");
  setBusy(button, true, "保存中…");
  try {
    await invoke("rename_item", { id, name });
    if (item) item.name = name;
    $("rename-dialog").close();
    render();
    toast("已重命名", "success");
  } catch (err) {
    showError("rename", friendlyError(err, "重命名失败"));
  } finally {
    setBusy(button, false);
  }
}

function openPasswordDialog() {
  $("new-password").value = "";
  $("new-password-confirm").value = "";
  hideError("password");
  if (!$("password-dialog").open) $("password-dialog").showModal();
  setTimeout(() => $("new-password").focus(), 30);
}

async function submitPasswordChange(event) {
  event.preventDefault();
  const password = $("new-password").value;
  const confirm = $("new-password-confirm").value;
  hideError("password");
  if (password.length < 8) {
    showError("password", "新密码至少需要 8 位");
    return;
  }
  if (password !== confirm) {
    showError("password", "两次输入的密码不一致");
    return;
  }

  const button = $("password-save");
  setBusy(button, true, "修改中…");
  try {
    await invoke("change_password", { newPassword: password });
    $("password-dialog").close();
    toast("密码已修改", "success");
  } catch (err) {
    showError("password", friendlyError(err, "修改失败"));
  } finally {
    setBusy(button, false);
  }
}

async function runImport(kind) {
  if (state.busy) return;
  startJob(kind);
  try {
    const summary =
      kind === "folder"
        ? await invoke("import_folder")
        : await invoke("import_files");
    await handleImportSummary(summary);
  } catch (err) {
    toast(friendlyError(err, "导入失败"), "error", 7000);
  } finally {
    endJob();
  }
}

async function handleImportSummary(summary) {
  if (!summary) return;
  if (summary.total === 0) {
    // 取消选择时后端不给 note；真的选不到东西时必须说清原因，不能毫无反应
    if (summary.note) toast(summary.note, "info", 9000);
    return;
  }
  const fresh = new Set((summary.sources || []).map((source) => source.id));
  await loadItems();
  // 刚导进去的东西得当场看得见：当前这一层扫不到就退回保险库根目录
  const visible = state.items.some((item) => fresh.has(item.id) && isUnder(item, state.cwd));
  if (!visible) state.cwd = "";
  render();
  if (summary.cancelled) {
    toast(`已取消：${summary.imported} / ${summary.total} 个文件完成加密`, "info", 6000);
  } else if (summary.imported > 0) {
    toast(`已加密导入 ${summary.imported} 个文件`, "success");
  }
  if (summary.failed && summary.failed.length > 0) {
    toast(
      `${summary.failed.length} 个文件导入失败：${summary.failed[0]}`,
      "error",
      9000
    );
  }
  const sources = summary.sources || [];
  if (sources.length > 0) openCleanupDialog(sources, summary.bytes || 0);
}

function openCleanupDialog(sources, bytes, options = {}) {
  state.pendingSources = sources;
  const locations = [...new Set(sources.map((source) => parentOf(source.path)))];
  const where =
    locations.length === 1
      ? locations[0]
      : `${locations[0]} 等 ${locations.length} 个位置`;
  $("cleanup-title").textContent = options.title || "导入完成";
  $("cleanup-text").textContent =
    options.text ||
    `${sources.length} 个原件（${formatSize(bytes)}）仍留在原处：${where}`;
  $("cleanup-text").title = where;
  const sample = $("cleanup-sample");
  const names = sources.slice(0, 6).map((source) => source.name);
  sample.textContent =
    names.join("、") +
    (sources.length > names.length ? ` 等 ${sources.length} 个文件` : "");
  sample.hidden = !options.showSample;
  $("cleanup-keep").textContent = options.keepLabel || "保留原件";
  $("cleanup-ack").checked = false;
  $("cleanup-delete").disabled = true;
  if (!$("cleanup-dialog").open) $("cleanup-dialog").showModal();
}

// 扫描一个文件夹，把「文件名 + 大小都能在库里对上」的原件一次挑出来删。
// 真正的把关仍在后端：逐个验密文、比大小、保险库自己的条目一律拒绝。
async function runCleanupScan() {
  if (state.busy) return;
  const button = $("btn-scan-originals");
  let folder;
  try {
    folder = await invoke("pick_folder", { title: "选择要清理原件的文件夹" });
  } catch (err) {
    toast(friendlyError(err, "无法选择文件夹"), "error");
    return;
  }
  if (!folder) return;

  setBusy(button, true, "扫描中…");
  try {
    const scan = await invoke("scan_originals", { folder });
    const found = scan.matched || [];
    if (found.length === 0) {
      toast(
        `扫了 ${scan.scanned} 个文件，${folder} 里没有已经加密进库的原件`,
        "info",
        8000
      );
      return;
    }
    openCleanupDialog(found, scan.bytes, {
      title: "清理原件",
      text: `在 ${scan.folder} 里扫了 ${scan.scanned} 个文件，找到 ${found.length} 个已经加密进库的原件（${formatSize(scan.bytes)}）`,
      showSample: true,
      keepLabel: "先不删",
    });
  } catch (err) {
    toast(friendlyError(err, "扫描失败"), "error", 7000);
  } finally {
    setBusy(button, false);
  }
}

function parentOf(path) {
  const trimmed = String(path || "").replace(/[\\/]+$/, "");
  const cut = Math.max(trimmed.lastIndexOf("\\"), trimmed.lastIndexOf("/"));
  return cut > 0 ? trimmed.slice(0, cut) : trimmed;
}

async function deleteOriginals() {
  const sources = state.pendingSources;
  if (sources.length === 0) return;
  const button = $("cleanup-delete");
  setBusy(button, true, "删除中…");
  try {
    const report = await invoke("delete_sources", {
      sources: sources.map((source) => ({ id: source.id, path: source.path })),
    });
    $("cleanup-dialog").close();
    if (report.deleted > 0) {
      toast(
        `已删除 ${report.deleted} 个原件，释放 ${formatSize(report.bytes)}`,
        "success",
        7000
      );
    }
    if (report.failed && report.failed.length > 0) {
      toast(
        `${report.failed.length} 个原件没有删除：${report.failed[0]}`,
        "error",
        10000
      );
    }
  } catch (err) {
    toast(friendlyError(err, "删除失败"), "error", 7000);
  } finally {
    setBusy(button, false);
  }
}

function startJob(kind) {
  state.busy = true;
  state.busyKind = kind;
  updateImportControls();
  showJobPanel(kind);
}

function endJob() {
  state.busy = false;
  state.busyKind = null;
  updateImportControls();
  hideImportPanel();
}

async function runExportAll() {
  if (state.busy) return;
  if (state.items.length === 0) {
    toast("保险库还是空的", "info");
    return;
  }
  let dest;
  try {
    dest = await invoke("pick_folder", {
      title: "选择解密后文件的存放文件夹",
    });
  } catch (err) {
    toast(friendlyError(err, "无法选择文件夹"), "error");
    return;
  }
  if (!dest) return;
  const bytes = state.items.reduce((sum, item) => sum + (item.size || 0), 0);
  askConfirm(
    "导出全部文件？",
    `将把 ${state.items.length} 个文件（${formatSize(
      bytes
    )}）解密写入 ${dest}，按导入时的文件夹结构还原。明文不会自动删除，请自己保管好那个文件夹。`,
    "导出",
    () => exportAllTo(dest),
    "btn-primary"
  );
}

async function exportAllTo(dest) {
  if (state.busy) return;
  startJob("export");
  try {
    const summary = await invoke("export_all", { dest });
    if (summary.cancelled) {
      toast(`已取消：${summary.exported} / ${summary.total} 个文件已解出`, "info", 6000);
    } else if (summary.exported > 0) {
      toast(`已解密导出 ${summary.exported} 个文件到 ${dest}`, "success", 7000);
    }
    if (summary.failed && summary.failed.length > 0) {
      toast(
        `${summary.failed.length} 个文件导出失败：${summary.failed[0]}`,
        "error",
        10000
      );
    }
  } catch (err) {
    toast(friendlyError(err, "导出失败"), "error", 7000);
  } finally {
    endJob();
  }
}

async function cancelJob() {
  const button = $("btn-cancel-job");
  if (button.disabled) return;
  button.disabled = true;
  $("import-current").textContent = "正在取消…当前这个文件会做完";
  try {
    await invoke("cancel_operation");
  } catch (err) {
    button.disabled = false;
    toast(friendlyError(err, "取消失败"), "error");
  }
}

function updateImportControls() {
  const disabled = state.busy;
  [
    "btn-import-files",
    "btn-import-folder",
    "btn-import-empty",
    "btn-export-all",
    "btn-scan-originals",
    "btn-lock",
    "btn-change-password",
  ].forEach((id) => {
    const el = $(id);
    if (el) el.disabled = disabled;
  });
  updateSelectionBar();
}

function showJobPanel(kind) {
  $("import-panel").hidden = false;
  $("import-bar").style.width = "0%";
  $("import-count").textContent = "";
  $("import-current").textContent = "";
  $("import-title").textContent = (JOB_LABELS[kind] || JOB_LABELS.import).doing;
  $("btn-cancel-job").disabled = false;
}

function updateJobProgress(done, total, current) {
  if (total === 0) return;
  if ($("import-panel").hidden) showJobPanel(state.busyKind || "import");
  const percent = Math.min(100, Math.round((done / total) * 100));
  $("import-bar").style.width = `${percent}%`;
  $("import-count").textContent = `${done} / ${total}`;
  $("import-current").textContent = current || "";
  const labels = JOB_LABELS[state.busyKind] || JOB_LABELS.import;
  $("import-title").textContent = done >= total ? labels.done : labels.doing;
}

function hideImportPanel() {
  $("import-panel").hidden = true;
}

async function pickCreateFolder() {
  try {
    const folder = await invoke("pick_folder", {
      title: "选择存放保险库的文件夹",
    });
    if (!folder) return;
    state.createPath = folder;
    $("create-path").textContent = folder;
    $("create-path").title = folder;
    hideError("create");
  } catch (err) {
    toast(friendlyError(err, "无法选择文件夹"), "error");
  }
}

async function pickOpenVault() {
  try {
    const folder = await invoke("pick_folder", {
      title: "选择保险库文件夹",
    });
    if (folder) await openVault(folder);
  } catch (err) {
    toast(friendlyError(err, "无法选择文件夹"), "error");
  }
}

async function openVault(path) {
  try {
    const info = await invoke("open_vault", { path });
    state.vaultPath = info.path;
    $("unlock-path").textContent = info.path;
    $("unlock-path").title = info.path;
    $("unlock-password").value = "";
    hideError("unlock");
    setView("unlock");
    setTimeout(() => $("unlock-password").focus(), 30);
  } catch (err) {
    toast(friendlyError(err, "无法打开保险库"), "error", 6000);
  }
}

async function submitUnlock(event) {
  event.preventDefault();
  const password = $("unlock-password").value;
  hideError("unlock");
  if (!password) {
    showError("unlock", "请输入密码");
    return;
  }

  const button = $("unlock-submit");
  setBusy(button, true, "正在解锁…");
  try {
    const info = await invoke("unlock_vault", { password });
    state.vaultPath = info.path;
    await loadItems();
    $("unlock-password").value = "";
    showVault();
  } catch (err) {
    showError("unlock", friendlyError(err, "解锁失败"));
    $("unlock-password").select();
  } finally {
    setBusy(button, false);
  }
}

async function submitCreate(event) {
  event.preventDefault();
  if (!state.createPath) {
    showError("create", "请先选择存放保险库的文件夹");
    return;
  }
  const password = $("create-password").value;
  const confirm = $("create-confirm").value;
  hideError("create");
  if (password.length < 8) {
    showError("create", "密码至少需要 8 位");
    return;
  }
  if (password !== confirm) {
    showError("create", "两次输入的密码不一致");
    return;
  }
  if (!$("create-ack").checked) {
    showError("create", "请先勾选下方的风险确认");
    return;
  }

  const button = $("create-submit");
  setBusy(button, true, "正在创建…");
  try {
    const info = await invoke("create_vault", {
      path: state.createPath,
      password,
    });
    state.vaultPath = info.path;
    await loadItems();
    $("create-password").value = "";
    $("create-confirm").value = "";
    showVault();
    toast("保险库已创建", "success");
  } catch (err) {
    showError("create", friendlyError(err, "创建失败"));
  } finally {
    setBusy(button, false);
  }
}

async function lockVault(auto) {
  try {
    await invoke("lock_vault");
  } catch (err) {
    console.warn("锁定失败", err);
  }
  state.items = [];
  state.thumbs.clear();
  state.thumbQueue = [];
  state.selected.clear();
  updateSelectionBar();
  // 下次解锁重新从保险库根目录那一层看起
  state.cwd = "";
  state.query = "";
  $("search").value = "";
  closeDialogs();
  clearTimeout(state.idleTimer);
  state.idleTimer = null;

  if (auto) toast("已自动锁定", "info");
  if (state.vaultPath) {
    $("unlock-path").textContent = state.vaultPath;
    $("unlock-password").value = "";
    hideError("unlock");
    setView("unlock");
    setTimeout(() => $("unlock-password").focus(), 30);
  } else {
    showWelcome(state.lastVault);
  }
}

function closeDialogs() {
  ["rename-dialog", "confirm-dialog", "password-dialog", "cleanup-dialog"].forEach(
    (id) => {
      const dialog = $(id);
      if (dialog && dialog.open) dialog.close();
    }
  );
  state.pendingSources = [];
}

function resetIdleTimer() {
  if (state.view !== "vault") return;
  clearTimeout(state.idleTimer);
  state.idleTimer = setTimeout(() => {
    if (state.busy) {
      resetIdleTimer();
      return;
    }
    if (state.view === "vault") lockVault(true);
  }, IDLE_MS);
}

function setupShortcuts() {
  window.addEventListener("keydown", (event) => {
    if (
      event.ctrlKey &&
      !event.shiftKey &&
      !event.altKey &&
      event.key.toLowerCase() === "l"
    ) {
      if (state.view === "vault" && !state.busy) {
        event.preventDefault();
        lockVault(false);
      }
    }
    // 弹层自己处理 Esc，别抢
    if (event.key === "Escape" && !document.querySelector("dialog[open]")) {
      if (state.view === "vault" && state.selected.size > 0) {
        event.preventDefault();
        clearSelection();
        toast("已取消选择", "info", 2000);
      } else if (state.view === "vault" && state.cwd && !state.query.trim()) {
        event.preventDefault();
        goUp();
      }
    }
  });
}

function setupIdleWatcher() {
  const bump = () => {
    if (state.view === "vault" && !state.busy) resetIdleTimer();
  };
  ["mousemove", "mousedown", "keydown", "wheel", "touchstart"].forEach((name) => {
    window.addEventListener(name, bump, { passive: true });
  });
}

async function setupDragDrop() {
  try {
    await listen("tauri://drag-enter", () => {
      if (state.view === "vault" && !state.busy) {
        $("drop-overlay").hidden = false;
      }
    });
    await listen("tauri://drag-leave", () => {
      $("drop-overlay").hidden = true;
    });
    await listen("tauri://drag-drop", async (event) => {
      $("drop-overlay").hidden = true;
      if (state.view !== "vault" || state.busy) return;
      const paths = (event.payload && event.payload.paths) || [];
      if (paths.length === 0) return;

      startJob("paths");
      try {
        const summary = await invoke("import_paths", { paths });
        await handleImportSummary(summary);
      } catch (err) {
        toast(friendlyError(err, "导入失败"), "error", 7000);
      } finally {
        endJob();
      }
    });
  } catch (err) {
    console.warn("拖拽事件注册失败", err);
  }
}

function showError(prefix, message) {
  const el = $(`${prefix}-error`);
  if (!el) return;
  el.textContent = message;
  el.hidden = false;
}

function hideError(prefix) {
  const el = $(`${prefix}-error`);
  if (!el) return;
  el.hidden = true;
  el.textContent = "";
}

function setBusy(button, busy, label) {
  if (!button) return;
  if (busy) {
    if (!button.dataset.label) button.dataset.label = button.textContent;
    button.disabled = true;
    if (label) button.textContent = label;
  } else {
    button.disabled = false;
    if (button.dataset.label) button.textContent = button.dataset.label;
  }
}

function friendlyError(err, fallback) {
  if (typeof err === "string" && err.trim()) return err;
  if (err && typeof err.message === "string" && err.message.trim()) {
    return err.message;
  }
  return fallback;
}

let toastTimer = null;

function toast(message, type = "info", ms = 4200) {
  const el = $("toast");
  el.textContent = message;
  el.dataset.type = type;
  el.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => el.classList.remove("show"), ms);
}

/* ---------- 配色 ---------- */

const THEME_KEY = "mixia-theme";

function toggleTheme() {
  const next = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
  document.documentElement.dataset.theme = next;
  // 只在磁盘上记一个词：偏好，不是秘密
  try {
    localStorage.setItem(THEME_KEY, next);
  } catch (err) {}
}

function bindEvents() {
  document.querySelectorAll(".theme-toggle").forEach((btn) => {
    btn.addEventListener("click", toggleTheme);
  });

  $("btn-new").addEventListener("click", () => {
    state.createPath = null;
    $("create-path").textContent = "尚未选择";
    $("create-path").title = "";
    $("create-password").value = "";
    $("create-confirm").value = "";
    $("create-ack").checked = false;
    hideError("create");
    setView("create");
    setTimeout(() => $("create-password").focus(), 30);
  });
  $("btn-open").addEventListener("click", pickOpenVault);
  $("btn-last").addEventListener("click", () => {
    if (state.lastVault) openVault(state.lastVault);
  });
  $("btn-unlock-back").addEventListener("click", () => showWelcome(state.lastVault));
  $("btn-create-back").addEventListener("click", () => showWelcome(state.lastVault));
  $("btn-pick-create").addEventListener("click", pickCreateFolder);

  $("unlock-form").addEventListener("submit", submitUnlock);
  $("create-form").addEventListener("submit", submitCreate);

  $("btn-import-files").addEventListener("click", () => runImport("files"));
  $("btn-import-empty").addEventListener("click", () => runImport("files"));
  $("btn-import-folder").addEventListener("click", () => runImport("folder"));
  $("btn-export-all").addEventListener("click", runExportAll);
  $("btn-scan-originals").addEventListener("click", runCleanupScan);
  $("btn-select-all").addEventListener("click", selectAllVisible);
  $("btn-folder-up").addEventListener("click", goUp);
  $("btn-select-none").addEventListener("click", clearSelection);
  $("btn-delete-selected").addEventListener("click", confirmDeleteSelected);
  $("btn-cancel-job").addEventListener("click", cancelJob);
  $("btn-lock").addEventListener("click", () => lockVault(false));
  $("btn-change-password").addEventListener("click", openPasswordDialog);

  $("cleanup-ack").addEventListener("change", (event) => {
    $("cleanup-delete").disabled = !event.target.checked;
  });
  $("cleanup-keep").addEventListener("click", () => $("cleanup-dialog").close());
  $("cleanup-delete").addEventListener("click", deleteOriginals);
  $("cleanup-dialog").addEventListener("close", () => {
    state.pendingSources = [];
    $("cleanup-ack").checked = false;
    $("cleanup-delete").disabled = true;
  });

  $("search").addEventListener("input", (event) => {
    state.query = event.target.value;
    render();
  });

  $("rename-form").addEventListener("submit", submitRename);
  $("rename-cancel").addEventListener("click", () => $("rename-dialog").close());
  $("rename-dialog").addEventListener("close", () => {
    state.renameId = null;
    hideError("rename");
  });

  $("confirm-cancel").addEventListener("click", () => $("confirm-dialog").close());
  $("confirm-ok").addEventListener("click", runConfirmedAction);
  $("confirm-dialog").addEventListener("close", () => {
    state.confirmAction = null;
  });

  $("password-form").addEventListener("submit", submitPasswordChange);
  $("password-cancel").addEventListener("click", () => $("password-dialog").close());
  $("password-dialog").addEventListener("close", () => hideError("password"));
}

async function init() {
  bindEvents();
  setupIdleWatcher();
  setupShortcuts();
  await setupDragDrop();
  await listen("import-progress", (event) => {
    const { done = 0, total = 0, current = "" } = event.payload || {};
    updateJobProgress(done, total, current);
  });
  await listen("export-progress", (event) => {
    const { done = 0, total = 0, current = "" } = event.payload || {};
    updateJobProgress(done, total, current);
  });

  try {
    const info = await invoke("get_state");
    state.lastVault = info.lastVault || null;
    if (info.unlocked) {
      state.vaultPath = info.vaultPath;
      await loadItems();
      showVault();
    } else {
      showWelcome(info.lastVault || null);
    }
  } catch (err) {
    toast(`初始化失败：${friendlyError(err, "未知错误")}`, "error", 8000);
    showWelcome(null);
  }
}

init();
