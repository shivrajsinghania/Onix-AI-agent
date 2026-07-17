// ─── agent-task.js ───────────────────────────────────────
// Task mode: mode switching, running research via dropdowns,
// subtype picker for task mode.
// Depends on: agent-infra.js, agent-render.js

const TASK_STATE_OPTIONS = [
  { value: "Bihar",   label: "Bihar",   icon: "📍", sub: "State government services" },
  { value: "Central", label: "Central", icon: "🇮🇳", sub: "All-India / Union services" },
]

const TASK_SERVICE_CATALOG_FALLBACK = {
  Bihar: [
    { group: "Certificates", items: [
      { value: "birth certificate", label: "Birth Certificate", icon: "👶" },
      { value: "income certificate", label: "Income Certificate", icon: "💰" },
    ]},
  ],
  Central: [
    { group: "Identity", items: [
      { value: "aadhar card", label: "Aadhar Card", icon: "🆔" },
      { value: "pan card", label: "PAN Card", icon: "💳" },
    ]},
  ],
}

let TASK_SERVICE_CATALOG_LIVE = null

async function loadServiceCatalog() {
  try {
    let [biharRes, centralRes] = await Promise.all([
      fetch("/api/services?state=Bihar"),
      fetch("/api/services?state=Central"),
    ])
    let [biharData, centralData] = await Promise.all([biharRes.json(), centralRes.json()])

    if (biharData.status !== "success" || centralData.status !== "success") {
      throw new Error("Non-success response from /api/services")
    }

    TASK_SERVICE_CATALOG_LIVE = {
      Bihar: biharData.groups || [],
      Central: centralData.groups || [],
    }
  } catch (err) {
    console.warn("Could not load live service catalog, using fallback:", err)
    TASK_SERVICE_CATALOG_LIVE = null
  }
  renderServiceOptions()
}

function getActiveCatalog() {
  if (TASK_SERVICE_CATALOG_LIVE && TASK_SERVICE_CATALOG_LIVE[currentTaskState] && TASK_SERVICE_CATALOG_LIVE[currentTaskState].length) {
    return TASK_SERVICE_CATALOG_LIVE
  }
  return TASK_SERVICE_CATALOG_FALLBACK
}

let currentTaskState = "Bihar"

function closeAllTaskDropdowns() {
  document.querySelectorAll(".onix-dd.open").forEach(el => el.classList.remove("open"))
  let backdrop = document.getElementById("serviceDDBackdrop")
  if (backdrop) backdrop.classList.remove("show")
}

document.addEventListener("click", (e) => {
  if (!e.target.closest(".onix-dd")) closeAllTaskDropdowns()
})
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") closeAllTaskDropdowns()
})

function toggleTaskDropdown(id) {
  let el = document.getElementById(id)
  if (!el) return
  let willOpen = !el.classList.contains("open")
  closeAllTaskDropdowns()
  el.classList.toggle("open", willOpen)

  let backdrop = document.getElementById("serviceDDBackdrop")
  if (backdrop) backdrop.classList.toggle("show", willOpen && id === "serviceDD")

  if (willOpen) {
    let search = el.querySelector(".onix-dd-search")
    let searchWrap = el.querySelector(".onix-dd-search-wrap")

    if (id === "serviceDD" && inDrillMode()) {
      if (searchWrap) searchWrap.style.display = "none"
      loadDrillLevel()
      return
    }

    if (searchWrap) searchWrap.style.display = ""
    if (search) {
      search.value = ""
      filterServiceOptions("")
    }
  }
}

function renderStateOptions() {
  let list = document.getElementById("stateDDList")
  if (!list) return
  list.innerHTML = TASK_STATE_OPTIONS.map(opt => `
    <button type="button" class="onix-dd-option ${opt.value === currentTaskState ? "selected" : ""}"
      onclick="selectTaskState('${opt.value}')">
      <span class="onix-dd-option-icon">${opt.icon}</span>
      <span class="onix-dd-option-text">
        <span class="onix-dd-option-title">${opt.label}</span>
        <span class="onix-dd-option-sub">${opt.sub}</span>
      </span>
      <span class="onix-dd-check">✓</span>
    </button>`).join("")
}

function selectTaskState(value) {
  currentTaskState = value
  document.getElementById("taskState").value = value

  let opt = TASK_STATE_OPTIONS.find(o => o.value === value)
  document.getElementById("stateDDLabel").textContent = `${opt.icon} ${opt.label}`
  document.getElementById("stateDD").classList.remove("open")
  renderStateOptions()

  document.getElementById("taskService").value = ""
  let variantInput = document.getElementById("taskVariantId")
  if (variantInput) variantInput.value = ""
  taskDrillStack = []
  let serviceLabel = document.getElementById("serviceDDLabel")
  serviceLabel.textContent = "Select a government service…"
  serviceLabel.classList.add("placeholder")
  renderServiceOptions()
}

let taskDrillStack = []
let taskDrillLoading = false

function inDrillMode() {
  return taskDrillStack.length > 0
}

function renderServiceOptions(filterText) {
  if (inDrillMode()) return

  filterText = (filterText || "").trim().toLowerCase()
  let groups = getActiveCatalog()[currentTaskState] || []
  let currentValue = document.getElementById("taskService").value
  let html = ""
  let totalShown = 0

  groups.forEach(group => {
    let items = group.items.filter(it => !filterText || it.label.toLowerCase().includes(filterText))
    if (!items.length) return
    totalShown += items.length
    html += `<div class="onix-dd-group-label">${group.group}</div>`
    html += items.map(it => `
      <button type="button" class="onix-dd-option ${it.value === currentValue ? "selected" : ""}"
        onclick="handleServiceOptionClick(event, '${it.value}', '${it.label.replace(/'/g, "\\'")}', '${it.icon}', ${!!it.has_variants})">
        <span class="onix-dd-option-icon">${it.icon}</span>
        <span class="onix-dd-option-text">
          <span class="onix-dd-option-title">${it.label}</span>
        </span>
        ${it.has_variants
          ? `<span class="onix-dd-drill-arrow">›</span>`
          : `<span class="onix-dd-check">✓</span>`}
      </button>`).join("")
  })

  let list = document.getElementById("serviceDDList")
  if (!list) return
  list.innerHTML = totalShown
    ? html
    : `<div class="onix-dd-empty">No services match "${filterText}"</div>`

  renderDrillHeader()
}

function filterServiceOptions(text) {
  renderServiceOptions(text)
}

function handleServiceOptionClick(e, value, label, icon, hasVariants) {
  if (e) e.stopPropagation() // Prevents document click handler from closing dropdown
  
  if (!hasVariants) {
    selectTaskService(value, label, icon, null, null)
    return
  }
  taskDrillStack = [{ type: "service", key: value, label, icon }]
  let searchWrap = document.querySelector("#serviceDD .onix-dd-search-wrap")
  if (searchWrap) searchWrap.style.display = "none"
  loadDrillLevel()
}

function handleVariantOptionClick(e, variantId, variantLabel) {
  if (e) e.stopPropagation() // Prevents document click handler from closing dropdown

  let root = taskDrillStack[0]
  let combinedLabel = `${root.label} - ${variantLabel}`
  selectTaskService(root.key, combinedLabel, root.icon, variantId, variantLabel)
}

function loadDrillLevel() {
  let root = taskDrillStack[0]

  let list = document.getElementById("serviceDDList")
  if (list) list.innerHTML = `<div class="onix-dd-empty">Loading…</div>`
  renderDrillHeader()
  taskDrillLoading = true

  let url = "/api/service-variants?service=" + encodeURIComponent(root.key)

  fetch(url)
    .then(r => r.json())
    .then(data => {
      taskDrillLoading = false
      if (data.status !== "success") {
        if (list) list.innerHTML = `<div class="onix-dd-empty">Couldn't load options</div>`
        return
      }
      renderDrillOptions(data.variants || [])
    })
    .catch(() => {
      taskDrillLoading = false
      if (list) list.innerHTML = `<div class="onix-dd-empty">Network error — try again</div>`
    })
}

function renderDrillOptions(variants) {
  let list = document.getElementById("serviceDDList")
  if (!list) return

  if (!variants.length) {
    list.innerHTML = `<div class="onix-dd-empty">No options here</div>`
    return
  }

  list.innerHTML = variants.map(v => `
    <button type="button" class="onix-dd-option"
      onclick="handleVariantOptionClick(event, ${v.id}, '${v.label.replace(/'/g, "\\'")}')">
      <span class="onix-dd-option-icon">${v.icon || "📄"}</span>
      <span class="onix-dd-option-text">
        <span class="onix-dd-option-title">${v.label}</span>
      </span>
      <span class="onix-dd-check">✓</span>
    </button>`).join("")
}

function renderDrillHeader() {
  let header = document.getElementById("serviceDDDrillHeader")
  if (!header) return

  if (!inDrillMode()) {
    header.innerHTML = ""
    header.style.display = "none"
    return
  }

  header.style.display = "flex"
  let crumbs = taskDrillStack.map(node => node.label).join(" › ")
  header.innerHTML = `
    <button type="button" class="onix-dd-drill-back" onclick="drillBack()">← Back</button>
    <span class="onix-dd-drill-crumb">${crumbs}</span>`
}

function drillBack() {
  taskDrillStack.pop()
  if (taskDrillStack.length === 0) {
    let searchWrap = document.querySelector("#serviceDD .onix-dd-search-wrap")
    if (searchWrap) searchWrap.style.display = ""
    renderServiceOptions()
  } else {
    loadDrillLevel()
  }
}

function selectTaskService(value, label, icon, variantId, variantLabel) {
  document.getElementById("taskService").value = value
  document.getElementById("taskVariantId").value = variantId || ""
  let labelEl = document.getElementById("serviceDDLabel")
  labelEl.textContent = `${icon} ${label}`
  labelEl.classList.remove("placeholder")
  document.getElementById("serviceDD").classList.remove("open")
  let backdrop = document.getElementById("serviceDDBackdrop")
  if (backdrop) backdrop.classList.remove("show")
  taskDrillStack = []
  let searchWrap = document.querySelector("#serviceDD .onix-dd-search-wrap")
  if (searchWrap) searchWrap.style.display = ""
  renderServiceOptions()
}

function initTaskDropdowns() {
  document.getElementById("taskService").value = ""
  let variantInput = document.getElementById("taskVariantId")
  if (variantInput) variantInput.value = ""
  let labelEl = document.getElementById("serviceDDLabel")
  if (labelEl) {
    labelEl.textContent = "Select a government service…"
    labelEl.classList.add("placeholder")
  }
  taskDrillStack = []
  renderStateOptions()
  renderServiceOptions()
  loadServiceCatalog()
}
initTaskDropdowns()

function switchMode(mode) {
  if (currentMode === mode) return
  currentMode = mode

  document.getElementById("modeChatBtn").classList.toggle("active", mode === "chat")
  document.getElementById("modeTaskBtn").classList.toggle("active", mode === "task")

  if (mode === "chat") {
    document.getElementById("task-view").style.display = "none"
    document.getElementById("data-view").style.display = "none"
    document.getElementById("chat-view").style.display = "block"
    showInputBar()
  } else {
    document.getElementById("chat-view").style.display = "none"
    document.getElementById("data-view").style.display = "none"
    document.getElementById("task-view").style.display = "block"
    hideInputBar()
  }
}

let isTaskRunning = false

async function runTaskResearch() {
  if (isTaskRunning) return

  let state = document.getElementById("taskState").value
  let service = document.getElementById("taskService").value
  let variantEl = document.getElementById("taskVariantId")
  let variantId = variantEl && variantEl.value ? variantEl.value : null

  if (!service) {
    alert("Please select a service first.")
    return
  }

  isTaskRunning = true
  let btn = document.getElementById("taskResearchBtn")
  let btnText = document.getElementById("taskResearchBtnText")
  btn.disabled = true
  btnText.textContent = "Researching…"

  let resultEl = document.getElementById("task-result")
  resultEl.innerHTML = `
    <div class="processing-wrap">
      <div class="processing-dots"><span></span><span></span><span></span></div>
      <div class="processing-label">Researching ${service} in ${state}…</div>
    </div>`

  let message = `I need information about ${service} in ${state}`
  let taskContext = { state: state, name: null }

  try {
    let response = await fetch("/task/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message: message,
        service: service,
        state: state,
        variant_id: variantId,
        history: [],
        user_context: taskContext,
        task_mode: true,
        session_id: null
      })
    })

    const contentType = response.headers.get("content-type") || ""
    if (!contentType.includes("application/json")) {
      const raw = await response.text()
      throw new Error(`Server error: ${response.status}\n${raw.substring(0, 300)}`)
    }

    const data = await response.json()

    if (data.status === "research") {
      let bubble = document.createElement("div")
      bubble.className = "ai-bubble"
      renderResearchCard(data, bubble, true)
      showResearchOverlay(bubble, data.research && data.research.analysis && data.research.analysis.service_name || service)

    } else if (data.status === "needs_subtype") {
      let subtypeBtns = (data.subtypes || []).map(s => `
        <button class="subtype-btn" onclick="taskPickSubtype('${data.service}','${state}','${s.id}','${s.label}')">
          <span class="subtype-label">${s.label}</span>
          <span class="subtype-desc">${s.description || ""}</span>
        </button>`).join("")
      resultEl.innerHTML = `
        <div class="subtype-card">
          <div class="rc-header">
            <span class="rc-icon">🗂️</span>
            <div>
              <div class="rc-title">${data.service_name || service}</div>
              <div class="rc-subtitle">Which type do you need?</div>
            </div>
          </div>
          <div class="subtype-list">${subtypeBtns}</div>
        </div>`

    } else if (data.status === "missing") {
      resultEl.innerHTML = `<div class="ai-bubble task-missing-msg">The service is not in system's database</div>`

    } else if (data.status === "conversation" || data.status === "need_clarification") {
      let msg = (data.message || data.question || "").replace(/\n/g, "<br>")
      resultEl.innerHTML = `<div class="ai-bubble"><div class="ai-message">${msg}</div></div>`

    } else if (data.status === "error") {
      resultEl.innerHTML = `<div class="ai-bubble" style="color:#f87171">❌ ${data.message}</div>`

    } else {
      resultEl.innerHTML = `<div class="ai-bubble" style="color:#f87171">❌ Unexpected response from server.</div>`
    }

  } catch(e) {
    resultEl.innerHTML = `<div class="ai-bubble" style="color:#f87171">❌ ${e.message}</div>`
  } finally {
    btn.disabled = false
    btnText.textContent = "🔍 Research"
    isTaskRunning = false
  }
}

async function taskPickSubtype(service, state, subtypeId, subtypeLabel) {
  let resultEl = document.getElementById("task-result")
  resultEl.innerHTML = `
    <div class="processing-wrap">
      <div class="processing-dots"><span></span><span></span><span></span></div>
      <div class="processing-label">Researching ${subtypeLabel}…</div>
    </div>`

  try {
    let response = await fetch("/research-subtype", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        service, state, subtype: subtypeId,
        subtype_label: subtypeLabel,
        task_mode: true,
        session_id: null
      })
    })
    let data = await response.json()
    if (data.status === "research") {
      let bubble = document.createElement("div")
      bubble.className = "ai-bubble"
      renderResearchCard(data, bubble, true)
      showResearchOverlay(bubble, data.research && data.research.analysis && data.research.analysis.service_name || subtypeLabel)

    } else if (data.status === "missing") {
      resultEl.innerHTML = `<div class="ai-bubble task-missing-msg">The service is not in system's database</div>`

    } else {
      resultEl.innerHTML = `<div class="ai-bubble" style="color:#f87171">❌ ${data.message || "Research failed"}</div>`
    }
  } catch(e) {
    resultEl.innerHTML = `<div class="ai-bubble" style="color:#f87171">❌ Network error: ${e.message}</div>`
  }
}

let researchOverlayOpen = false

function showResearchOverlay(bubble, titleText) {
  let overlay = document.getElementById("researchOverlay")
  let titleEl = document.getElementById("researchOverlayTitle")
  let bodyEl = document.getElementById("researchOverlayBody")
  let resultEl = document.getElementById("task-result")
  if (!overlay || !bodyEl || !resultEl) return

  if (titleEl) titleEl.textContent = titleText || "Research"
  bodyEl.innerHTML = ""
  bodyEl.appendChild(bubble)

  resultEl.innerHTML = `
    <button type="button" class="task-result-placeholder" onclick="reopenResearchOverlay()">
      📋 View research result
    </button>`

  overlay.classList.add("show")
  researchOverlayOpen = true
  history.pushState({ onixOverlay: "research" }, "")
}

function reopenResearchOverlay() {
  let overlay = document.getElementById("researchOverlay")
  if (!overlay) return
  overlay.classList.add("show")
  researchOverlayOpen = true
  history.pushState({ onixOverlay: "research" }, "")
}

function closeResearchOverlay(fromPopState) {
  let overlay = document.getElementById("researchOverlay")
  if (!overlay || !researchOverlayOpen) return
  overlay.classList.remove("show")
  researchOverlayOpen = false
  if (!fromPopState && history.state && history.state.onixOverlay === "research") {
    history.back()
  }
}

window.addEventListener("popstate", () => {
  if (researchOverlayOpen) closeResearchOverlay(true)
})