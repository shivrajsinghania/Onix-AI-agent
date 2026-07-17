// ─── admin-dashboard.js ─────────────────────────────────────────────

let allServices = window.__ADMIN_BOOT__.services
let dueReviews = window.__ADMIN_BOOT__.dueReviews
let loadTimer = null
let expandedRows = new Set()   
let variantChildrenCache = {}  

function escapeHtml(s) {
  return String(s || "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]))
}

function confidencePill(score) {
  score = score || 0
  let cls = score >= 70 ? "pill-confidence-high" : score >= 40 ? "pill-confidence-mid" : "pill-confidence-low"
  return `<span class="pill ${cls}">${score}/100</span>`
}

function renderTable() {
  let body = document.getElementById("serviceTableBody")
  let emptyMsg = document.getElementById("serviceEmptyMsg")
  if (!allServices.length) {
    body.innerHTML = ""
    emptyMsg.style.display = "block"
    return
  }
  emptyMsg.style.display = "none"
  body.innerHTML = allServices.map(s => serviceRowHtml(s)).join("")

  expandedRows.forEach(key => {
    if (variantChildrenCache[key]) {
      renderVariantChildRows(key, variantChildrenCache[key])
    } else {
      fetchVariantChildren(key)
    }
  })
}

function fetchVariantChildren(serviceKey) {
  let slot = document.getElementById("variantSlot-" + serviceKey)
  if (!slot) return
  slot.innerHTML = `<td colspan="7"><span class="variant-child-loading">Loading variants…</span></td>`
  fetch("/admin/api/service/" + encodeURIComponent(serviceKey) + "/variants")
    .then(r => r.json())
    .then(data => {
      if (data.status !== "success") {
        slot.innerHTML = `<td colspan="7"><span class="variant-child-loading">Couldn't load variants</span></td>`
        return
      }
      variantChildrenCache[serviceKey] = data.variants || []
      renderVariantChildRows(serviceKey, variantChildrenCache[serviceKey])
    })
    .catch(() => {
      slot.innerHTML = `<td colspan="7"><span class="variant-child-loading">Network error</span></td>`
    })
}

function serviceRowHtml(s) {
  let scopePill = (s.state || "").toLowerCase() === "central"
    ? `<span class="pill pill-central">🇮🇳 Central</span>`
    : `<span class="pill">📍 ${escapeHtml(s.state || "")}</span>`
  let inactivePill = s.active ? "" : `<span class="pill pill-inactive">Inactive</span>`
  let isExpanded = expandedRows.has(s.service_key)

  return `
  <tr class="${s.active ? '' : 'inactive-row'} ${s.has_variants ? 'service-row-parent' : ''} ${isExpanded ? 'expanded' : ''}" data-service-key="${escapeHtml(s.service_key)}">
    <td style="cursor: pointer;" onclick="if(${s.has_variants}) toggleVariantRows('${s.service_key}')">
      ${s.has_variants ? `<span class="expand-toggle">▸</span>` : ''}
      <strong>${escapeHtml(s.service_name)}</strong><br>
      <span class="muted">${escapeHtml(s.service_key)}</span>
    </td>
    <td onclick="if(${s.has_variants}) toggleVariantRows('${s.service_key}')">${scopePill} ${inactivePill}</td>
    <td onclick="if(${s.has_variants}) toggleVariantRows('${s.service_key}')">${escapeHtml(s.category || "—")}</td>
    <td onclick="if(${s.has_variants}) toggleVariantRows('${s.service_key}')">${s.has_variants ? `<span class="pill pill-variants">🗂️ Variants Inside</span>` : `<span class="muted">—</span>`}</td>
    <td onclick="if(${s.has_variants}) toggleVariantRows('${s.service_key}')">${s.has_variants ? '<span class="muted">—</span>' : confidencePill(s.confidence_score)}</td>
    <td onclick="if(${s.has_variants}) toggleVariantRows('${s.service_key}')">${s.last_verified ? escapeHtml(s.last_verified) : '<span class="muted">not set</span>'}</td>
    <td>
      <div class="actions-row">
        <button class="btn btn-sm" onclick="openModal('edit', '${s.service_key}')">Edit Parent</button>
        ${s.active
          ? `<button class="btn btn-sm btn-danger" onclick="deactivateService('${s.service_key}')">Deactivate</button>`
          : `<button class="btn btn-sm" onclick="restoreService('${s.service_key}')">Restore</button>`}
      </div>
    </td>
  </tr>
  <tr class="variant-children-slot" id="variantSlot-${escapeHtml(s.service_key)}" style="${isExpanded ? '' : 'display:none'}"></tr>`
}

function toggleVariantRows(serviceKey) {
  let willExpand = !expandedRows.has(serviceKey)
  if (willExpand) {
    expandedRows.add(serviceKey)
  } else {
    expandedRows.delete(serviceKey)
  }

  let parentRow = document.querySelector(`tr[data-service-key="${cssEscape(serviceKey)}"]`)
  if (parentRow) parentRow.classList.toggle("expanded", willExpand)

  let slot = document.getElementById("variantSlot-" + serviceKey)
  if (!slot) return

  if (!willExpand) {
    slot.style.display = "none"
    return
  }

  slot.style.display = ""
  if (variantChildrenCache[serviceKey]) {
    renderVariantChildRows(serviceKey, variantChildrenCache[serviceKey])
    return
  }

  fetchVariantChildren(serviceKey)
}

function renderVariantChildRows(serviceKey, variants) {
  let slot = document.getElementById("variantSlot-" + serviceKey)
  if (!slot) return

  if (!variants.length) {
    slot.innerHTML = `<td colspan="7"><span class="variant-child-empty">No variants yet. Edit parent to add them.</span></td>`
    return
  }

  slot.innerHTML = `<td colspan="7" style="padding:0">
    <table style="width:100%; background: var(--bg-hover);">
      <tbody>
        ${variants.map(v => variantChildRowHtml(serviceKey, v)).join("")}
      </tbody>
    </table>
  </td>`
}

function variantChildRowHtml(serviceKey, v) {
  let inactivePill = v.active ? "" : `<span class="pill pill-inactive">Inactive</span>`
  return `
    <tr class="variant-child-row" style="border-bottom: 1px solid var(--border);">
      <td style="width:34%">
        <span class="variant-child-name" style="padding-left: 20px;">
          <span class="variant-tree-glyph">↳</span>
          ${escapeHtml(v.icon || "📄")} ${escapeHtml(v.label)}
        </span>
      </td>
      <td colspan="3">${inactivePill}</td>
      <td colspan="1"></td>
      <td>
        <div class="actions-row">
          <button class="btn btn-sm btn-accent" onclick="openVariantModal('edit', '${serviceKey}', ${v.id})">Edit Variant Data</button>
          <button class="btn btn-sm btn-danger" onclick="deleteVariantFromTable('${serviceKey}', ${v.id}, '${escapeHtml(v.label).replace(/'/g, "\\'")}')">Delete</button>
        </div>
      </td>
    </tr>`
}

function deleteVariantFromTable(serviceKey, variantId, label) {
  if (!confirm(`Delete variant "${label}"?`)) return
  fetch("/admin/api/variant/" + variantId + "/delete", { method: "POST" })
    .then(r => r.json())
    .then(data => {
      if (data.status === "success") {
        showToast("Variant deleted", "success")
        delete variantChildrenCache[serviceKey]
        toggleVariantRows(serviceKey) 
        toggleVariantRows(serviceKey) 
      } else {
        showToast(data.message || "Couldn't delete variant", "error")
      }
    })
    .catch(() => showToast("Network error deleting variant", "error"))
}

function cssEscape(s) {
  return String(s).replace(/["\\]/g, "\\$&")
}

function renderReviews() {
  let list = document.getElementById("reviewList")
  if (!dueReviews.length) {
    list.innerHTML = `<li class="muted">Nothing due right now.</li>`
    return
  }
  
  list.innerHTML = dueReviews.map(s => `
    <li style="margin-bottom: 10px; padding-bottom: 10px; border-bottom: 1px solid var(--border-soft);">
      <div style="font-weight: 600;">${escapeHtml(s.service_name)}</div>
      <div style="color: var(--muted); font-size: 12px; margin-top: 4px;">
        📍 ${escapeHtml(s.state)} &nbsp;·&nbsp;
        ${s.last_verified ? `Last verified: ${escapeHtml(s.last_verified)}` : `<span style="color: var(--danger)">Never verified</span>`}
      </div>
    </li>`).join("")
}

function loadServices() {
  let q = document.getElementById("filterQ").value.trim()
  let state = document.getElementById("filterState").value
  let params = new URLSearchParams()
  if (q) params.set("q", q)
  if (state) params.set("state", state)

  fetch("/admin/api/services?" + params.toString())
    .then(r => r.json())
    .then(data => {
      if (data.status !== "success") return
      allServices = data.services
      dueReviews = data.due_reviews
      let stillPresent = new Set(allServices.map(s => s.service_key))
      expandedRows.forEach(key => { if (!stillPresent.has(key)) expandedRows.delete(key) })
      renderTable()
      renderReviews()
    })
    .catch(() => showToast("Couldn't refresh the list", "error"))
}

function debouncedLoad() {
  clearTimeout(loadTimer)
  loadTimer = setTimeout(loadServices, 300)
}

function deactivateService(key) {
  if (!confirm("Deactivate this service? It will stop showing in the app.")) return
  fetch("/admin/api/service/" + encodeURIComponent(key) + "/delete", { method: "POST" })
    .then(r => r.json())
    .then(data => {
      if (data.status === "success") { showToast("Service deactivated", "success"); loadServices() }
      else showToast(data.message || "Couldn't deactivate", "error")
    })
}

function restoreService(key) {
  fetch("/admin/api/service/" + encodeURIComponent(key) + "/restore", { method: "POST" })
    .then(r => r.json())
    .then(data => {
      if (data.status === "success") { showToast("Service restored", "success"); loadServices() }
      else showToast(data.message || "Couldn't restore", "error")
    })
}

let toastTimer = null
function showToast(msg, kind) {
  let el = document.getElementById("toast")
  el.textContent = msg
  el.className = "toast show" + (kind ? " " + kind : "")
  clearTimeout(toastTimer)
  toastTimer = setTimeout(() => el.classList.remove("show"), 2500)
}

renderTable()
renderReviews()
