// ─── admin-form.js ─────────────────────────────────────────────

let chipState = { documents: [], steps: [], sources: [], eligibility: [] }
let modalMode = "new"
let editingKey = null            
let editingVariantId = null      

function configureModalUI(type, hasVariantsChecked) {
  let toggleWrap = document.getElementById('hasVariantsToggleWrap')
  let variantsManager = document.getElementById('variantsManagerWrapper')
  let dataFields = document.getElementById('dataFieldsWrapper')
  let scopeWrap = document.getElementById('wrap_scope')
  let catWrap = document.getElementById('wrap_category')
  let toggleCheckbox = document.getElementById('f_has_variants')

  if (type === 'variant') {
    toggleWrap.style.display = 'none'
    variantsManager.style.display = 'none'
    dataFields.style.display = 'contents'
    scopeWrap.style.display = 'none'
    catWrap.style.display = 'none'
  } else {
    toggleWrap.style.display = 'block'
    scopeWrap.style.display = 'flex'
    catWrap.style.display = 'flex'
    toggleCheckbox.checked = hasVariantsChecked
    toggleFormMode() 
  }
}

function toggleFormMode() {
  const hasVariants = document.getElementById("f_has_variants").checked
  if (hasVariants) {
    document.getElementById("dataFieldsWrapper").style.display = "none"
    document.getElementById("variantsManagerWrapper").style.display = "block"
  } else {
    document.getElementById("dataFieldsWrapper").style.display = "contents"
    document.getElementById("variantsManagerWrapper").style.display = "none"
  }
}

function renderChips() {
  let docWrap = document.getElementById("documentsChips")
  docWrap.innerHTML = chipState.documents.length
    ? chipState.documents.map((v, i) => `
        <span class="chip"><span>${escapeHtml(v)}</span>
        <button type="button" class="chip-remove" onclick="removeChip('documents', ${i})">✕</button></span>`).join("")
    : `<span class="chip-empty">No documents added yet</span>`

  let srcWrap = document.getElementById("sourcesChips")
  srcWrap.innerHTML = chipState.sources.length
    ? chipState.sources.map((v, i) => `
        <span class="chip"><span>${escapeHtml(v)}</span>
        <button type="button" class="chip-remove" onclick="removeChip('sources', ${i})">✕</button></span>`).join("")
    : `<span class="chip-empty">No sources added yet</span>`

  let stepWrap = document.getElementById("stepsChips")
  stepWrap.innerHTML = chipState.steps.length
    ? chipState.steps.map((v, i) => `
        <div class="step-item"><span class="step-num">${i + 1}</span>
        <span class="step-text">${escapeHtml(v)}</span>
        <button type="button" class="chip-remove" onclick="removeChip('steps', ${i})">✕</button></div>`).join("")
    : `<span class="chip-empty">No steps added yet</span>`

  let eligWrap = document.getElementById("eligibilityChips")
  if (eligWrap) {
    eligWrap.innerHTML = chipState.eligibility.length
      ? chipState.eligibility.map((v, i) => `
          <span class="chip"><span>${escapeHtml(v)}</span>
          <button type="button" class="chip-remove" onclick="removeChip('eligibility', ${i})">✕</button></span>`).join("")
      : `<span class="chip-empty">No eligibility conditions added yet</span>`
  }
}

function addChip(key) {
  let inputId = key === "documents" ? "docInput" : key === "steps" ? "stepInput" : key === "eligibility" ? "eligibilityInput" : "sourceInput"
  let input = document.getElementById(inputId)
  let val = input.value.trim()
  if (!val) return
  chipState[key].push(val)
  input.value = ""
  renderChips()
  input.focus()
}

function removeChip(key, idx) {
  chipState[key].splice(idx, 1)
  renderChips()
}

function onCategoryChange() {
  let v = document.getElementById("f_category").value
  document.getElementById("f_category_other_wrap").style.display = v === "__other__" ? "flex" : "none"
}

function slugify(text) {
  return String(text || "").toLowerCase().trim().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "")
}

function onServiceNameInput() {
  if (modalMode !== "new") return
  let name = document.getElementById("f_service_name").value
  let preview = document.getElementById("serviceKeyPreview")
  preview.textContent = name.trim() ? `Will be saved as: ${slugify(name)}` : ""
}

function resetForm() {
  document.getElementById("f_service_name").value = ""
  document.getElementById("serviceKeyPreview").textContent = ""
  document.getElementById("f_scope").value = "Bihar"
  document.getElementById("f_category").value = ""
  document.getElementById("f_category_other").value = ""
  document.getElementById("f_category_other_wrap").style.display = "none"
  document.getElementById("f_icon").value = ""
  document.getElementById("f_department").value = ""
  document.getElementById("f_portal_name").value = ""
  document.getElementById("f_portal_url").value = ""
  document.getElementById("f_apply_url").value = ""
  document.getElementById("f_fees").value = ""
  document.getElementById("f_timeline").value = ""
  document.getElementById("f_validity").value = ""
  document.getElementById("f_photo_size").value = ""
  document.getElementById("f_signature_size").value = ""
  document.getElementById("f_upload_limits").value = ""
  document.getElementById("f_notes").value = ""
  document.getElementById("f_manual_review_needed").checked = false
  document.getElementById("f_active").checked = true
  document.getElementById("f_has_variants").checked = false
  
  chipState = { documents: [], steps: [], sources: [], eligibility: [] }
  renderChips()
  // reset auto-grow textareas to single line
  document.querySelectorAll(".modal-content .auto-grow").forEach(el => { el.style.height = ""; })
  document.getElementById("modalServiceKeyLine").textContent = ""
  document.getElementById("modalLastVerified").textContent = "Will be set automatically on save"
  document.getElementById("modalConfidence").textContent = "Confidence score: calculated after first save"
}

function populateForm(s) {
  document.getElementById("f_service_name").value = s.service_name || s.label || ""
  document.getElementById("serviceKeyPreview").textContent = ""

  if (s.state) {
    let stateLower = (s.state || "").toLowerCase()
    document.getElementById("f_scope").value = stateLower === "central" ? "Central" : "Bihar"
  }

  let knownCategories = ["certificates","identity","transport","land records","welfare & employment","welfare","travel","health","employment & finance","business"]
  let catLower = (s.category || "").toLowerCase()
  if (s.category && knownCategories.includes(catLower)) {
    document.getElementById("f_category").value = s.category
    document.getElementById("f_category_other_wrap").style.display = "none"
  } else if (s.category) {
    document.getElementById("f_category").value = "__other__"
    document.getElementById("f_category_other").value = s.category
    document.getElementById("f_category_other_wrap").style.display = "flex"
  } else {
    document.getElementById("f_category").value = ""
    document.getElementById("f_category_other_wrap").style.display = "none"
  }

  document.getElementById("f_icon").value = s.icon || ""
  document.getElementById("f_department").value = s.department || ""
  document.getElementById("f_portal_name").value = s.portal_name || ""
  document.getElementById("f_portal_url").value = s.portal_url || ""
  document.getElementById("f_apply_url").value = s.apply_url || ""
  document.getElementById("f_fees").value = s.fees || ""
  document.getElementById("f_timeline").value = s.timeline || ""
  document.getElementById("f_validity").value = s.validity || ""
  document.getElementById("f_photo_size").value = s.photo_size || ""
  document.getElementById("f_signature_size").value = s.signature_size || ""
  document.getElementById("f_upload_limits").value = s.upload_limits || ""
  document.getElementById("f_notes").value = s.notes || ""
  document.getElementById("f_manual_review_needed").checked = !!s.manual_review_needed
  document.getElementById("f_active").checked = s.active !== false

  // eligibility: stored as newline-joined string, show as chips
  let eligibilityItems = []
  if (Array.isArray(s.eligibility)) {
    eligibilityItems = s.eligibility
  } else if (typeof s.eligibility === "string" && s.eligibility.trim()) {
    eligibilityItems = s.eligibility.split("\n").map(l => l.trim()).filter(Boolean)
  }

  chipState = {
    documents: Array.isArray(s.documents) ? s.documents.slice() : [],
    steps: Array.isArray(s.steps) ? s.steps.slice() : [],
    sources: Array.isArray(s.sources) ? s.sources.slice() : [],
    eligibility: eligibilityItems,
  }
  renderChips()

  // trigger auto-grow for all populated textareas
  document.querySelectorAll(".modal-content .auto-grow").forEach(el => autoGrow(el))

  if (modalMode === "variant-new" || modalMode === "variant-edit") {
    document.getElementById("modalServiceKeyLine").textContent = ""
    document.getElementById("modalLastVerified").textContent = ""
    document.getElementById("modalConfidence").textContent = ""
  } else {
    document.getElementById("modalServiceKeyLine").textContent = `Service key: ${s.service_key}`
    document.getElementById("modalLastVerified").textContent = s.last_verified ? `Last verified: ${s.last_verified}` : `Never verified`
    document.getElementById("modalConfidence").textContent = `Confidence score: ${s.confidence_score ?? 0}/100`
  }
}

function setNameFieldLabel(text, placeholder) {
  let label = document.getElementById("f_service_name_label")
  let input = document.getElementById("f_service_name")
  if (label) label.innerHTML = `${text} <span class="req">*</span>`
  if (input) input.placeholder = placeholder
}

function openModal(mode, serviceKey) {
  modalMode = mode
  editingKey = serviceKey || null
  editingVariantId = null
  resetForm()
  setNameFieldLabel("Service name", "e.g. Income Certificate")
  document.getElementById("modalSubtitle").textContent = ""

  let unsavedNote = document.getElementById("variantsUnsavedNote")
  let addRow = document.getElementById("variantAddRowBtn")

  if (mode === "edit" && serviceKey) {
    document.getElementById("modalTitle").textContent = "Edit Parent Service"
    if (unsavedNote) unsavedNote.style.display = "none"
    if (addRow) addRow.style.display = "flex"
    
    fetch("/admin/api/service/" + encodeURIComponent(serviceKey))
      .then(r => r.json())
      .then(data => {
        if (data.status === "success") {
          populateForm(data.service)
          configureModalUI('service', !!data.service.has_variants)
        }
      })
    loadServiceVariantsFlat(serviceKey)
  } else {
    document.getElementById("modalTitle").textContent = "Add Service"
    if (unsavedNote) unsavedNote.style.display = "block"
    if (addRow) addRow.style.display = "none"
    document.getElementById("variantsTree").innerHTML = ""
    configureModalUI('service', false)
  }

  document.getElementById("modalBg").classList.add("open")
}

function openVariantModal(mode, serviceKey, variantId) {
  modalMode = mode === "edit" ? "variant-edit" : "variant-new"
  editingKey = serviceKey
  editingVariantId = mode === "edit" ? variantId : null
  resetForm()
  setNameFieldLabel("Variant name (e.g. Update Address)", "e.g. Update Address")

  document.getElementById("modalSubtitle").textContent = `Data for Variant under: ${serviceKey}`
  configureModalUI('variant', false)

  if (modalMode === "variant-edit") {
    document.getElementById("modalTitle").textContent = "Edit Variant Data"
    fetch("/admin/api/service/" + encodeURIComponent(serviceKey) + "/variant/" + variantId)
      .then(r => r.json())
      .then(data => {
        if (data.status === "success") populateForm(data.variant)
      })
  } else {
    document.getElementById("modalTitle").textContent = "Add Variant Data"
  }

  document.getElementById("modalBg").classList.add("open")
}

function closeModal() {
  document.getElementById("modalBg").classList.remove("open")
}

document.addEventListener("keydown", (e) => { if (e.key === "Escape") closeModal() })

function collectPayload() {
  let scope = document.getElementById("f_scope").value
  let state = scope
  let jurisdiction_type = scope === "Central" ? "central" : "state"
  let category = document.getElementById("f_category").value
  if (category === "__other__") category = document.getElementById("f_category_other").value.trim()

  let hasVariantsCheckbox = document.getElementById("f_has_variants");

  return {
    mode: modalMode,
    service_key: editingKey,
    service_name: document.getElementById("f_service_name").value.trim(),
    state: state,
    jurisdiction_type: jurisdiction_type,
    category: category,
    icon: document.getElementById("f_icon").value.trim(),
    department: document.getElementById("f_department").value.trim(),
    portal_name: document.getElementById("f_portal_name").value.trim(),
    portal_url: document.getElementById("f_portal_url").value.trim(),
    apply_url: document.getElementById("f_apply_url").value.trim(),
    fees: document.getElementById("f_fees").value.trim(),
    timeline: document.getElementById("f_timeline").value.trim(),
    validity: document.getElementById("f_validity").value.trim(),
    eligibility: chipState.eligibility.join("\n"),
    photo_size: document.getElementById("f_photo_size").value.trim(),
    signature_size: document.getElementById("f_signature_size").value.trim(),
    upload_limits: document.getElementById("f_upload_limits").value.trim(),
    notes: document.getElementById("f_notes").value.trim(),
    manual_review_needed: document.getElementById("f_manual_review_needed").checked,
    active: document.getElementById("f_active").checked,
    has_variants: hasVariantsCheckbox ? hasVariantsCheckbox.checked : false,
    documents: chipState.documents,
    steps: chipState.steps,
    sources: chipState.sources,
  }
}

function saveService() {
  if (modalMode === "variant-new" || modalMode === "variant-edit") {
    saveVariant()
    return
  }

  let payload = collectPayload()
  if (!payload.service_name) { showToast("Service name is required", "error"); return }
  if (!payload.state) { showToast("Please choose or type a state", "error"); return }

  let btn = document.getElementById("saveBtn")
  btn.disabled = true
  btn.textContent = "Saving…"

  fetch("/admin/api/service/save", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  })
    .then(r => r.json())
    .then(data => {
      if (data.status === "success") {
        showToast("Service saved", "success")
        closeModal()
        loadServices() 
      } else {
        showToast(data.message || "Couldn't save service", "error")
      }
    })
    .catch(() => showToast("Network error while saving", "error"))
    .finally(() => {
      btn.disabled = false
      btn.textContent = "Save service"
    })
}

function saveVariant() {
  let payload = collectPayload()
  let label = payload.service_name 
  if (!label) { showToast("Variant name is required", "error"); return }

  let body = {
    id: editingVariantId,
    label: label,
    icon: payload.icon,
    department: payload.department,
    portal_name: payload.portal_name,
    portal_url: payload.portal_url,
    apply_url: payload.apply_url,
    fees: payload.fees,
    timeline: payload.timeline,
    validity: payload.validity,
    eligibility: payload.eligibility,
    photo_size: payload.photo_size,
    signature_size: payload.signature_size,
    upload_limits: payload.upload_limits,
    notes: payload.notes,
    active: payload.active,
    manual_review_needed: payload.manual_review_needed,
    documents: payload.documents,
    steps: payload.steps,
    sources: payload.sources,
  }

  let btn = document.getElementById("saveBtn")
  btn.disabled = true
  btn.textContent = "Saving…"

  fetch("/admin/api/service/" + encodeURIComponent(editingKey) + "/variant/save", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body)
  })
    .then(r => r.json())
    .then(data => {
      if (data.status === "success") {
        showToast("Variant saved", "success")
        closeModal()
        delete variantChildrenCache[editingKey]
        loadServices() 
      } else {
        showToast(data.message || "Couldn't save variant", "error")
      }
    })
    .catch(() => showToast("Network error while saving", "error"))
    .finally(() => {
      btn.disabled = false
      btn.textContent = "Save Variant Data"
    })
}

function loadServiceVariantsFlat(serviceKey) {
  let treeEl = document.getElementById("variantsTree")
  if (!editingKey) return 

  treeEl.innerHTML = `<div class="variants-empty">Loading…</div>`
  fetch("/admin/api/service/" + encodeURIComponent(serviceKey) + "/variants")
    .then(r => r.json())
    .then(data => {
      if (data.status !== "success") {
        treeEl.innerHTML = `<div class="variants-empty">Couldn't load variants</div>`
        return
      }
      renderVariantsTree(data.variants)
    })
    .catch(() => { treeEl.innerHTML = `<div class="variants-empty">Couldn't load variants</div>` })
}

function renderVariantsTree(variants) {
  let treeEl = document.getElementById("variantsTree")
  if (!variants.length) {
    treeEl.innerHTML = `<div class="variants-empty">No variants at this level yet.</div>`
    return
  }
  treeEl.innerHTML = variants.map(v => `
    <div class="variant-row" style="display: flex; justify-content: space-between; padding: 10px; background: var(--bg); border: 1px solid var(--border); border-radius: 4px; margin-bottom: 5px;">
      <span class="variant-row-label">
        ${escapeHtml(v.icon || "📄")} ${escapeHtml(v.label)}
      </span>
      <div class="variant-row-actions">
        <button type="button" class="btn btn-sm btn-accent" title="Edit Data" onclick="openVariantModal('edit', '${editingKey}', ${v.id})">✎ Edit Data</button>
        <button type="button" class="btn btn-sm btn-danger" title="Delete" onclick="deleteVariant(${v.id}, '${escapeHtml(v.label).replace(/'/g, "\\'")}')">🗑</button>
      </div>
    </div>`).join("")
}

function addVariantAtCurrentLevel() {
  if (!editingKey) {
    showToast("Save the service first, then add variants", "error")
    return
  }
  openVariantModal("new", editingKey, null)
}

function deleteVariant(id, label) {
  if (!confirm(`Delete variant "${label}"?`)) return

  fetch("/admin/api/variant/" + id + "/delete", { method: "POST" })
    .then(r => r.json())
    .then(data => {
      if (data.status === "success") {
        loadServiceVariantsFlat(editingKey)
        delete variantChildrenCache[editingKey]
        loadServices() 
      } else {
        showToast(data.message || "Couldn't delete variant", "error")
      }
    })
    .catch(() => showToast("Network error deleting variant", "error"))
}

// ─── Auto-grow textareas ────────────────────────────────────
function autoGrow(el) {
  el.style.height = "auto"
  el.style.height = el.scrollHeight + "px"
}

document.addEventListener("DOMContentLoaded", function() {
  document.addEventListener("input", function(e) {
    if (e.target.classList.contains("auto-grow")) autoGrow(e.target)
  })
})
