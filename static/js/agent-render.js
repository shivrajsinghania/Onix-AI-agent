// ─── agent-render.js ─────────────────────────────────────
// All rendering functions: research cards, data views, chat session replay.
// Depends on: agent-infra.js (escapeHtml, safeUrl, toArray, humanTime, describeTask, etc.)

// ─── Human-readable task descriptions ────────────────────
function describeTask(task) {
  let a = task.action || ""
  let app = task.app || ""
  let target = task.target || ""
  let url = task.url || ""
  let query = task.query || ""
  let text = task.text || ""
  let element = task.element || ""
  let platformName = capitalize(app)
  let label = ""

  if (a === "open_website") {
    let name = siteName(url) || url
    label = `🌐 Open ${name}`
  } else if (a === "search") {
    let where = platformName ? ` on ${platformName}` : ""
    label = `🔍 Search${where} for "${query}"`
  } else if (a === "send_message") {
    let where = platformName ? ` on ${platformName}` : ""
    label = `📩 Send message to ${target}${where}`
  } else if (a === "observe_website") {
    let name = siteName(url) || url
    label = `👀 Observe ${name}`
  } else if (a === "type_text") {
    label = `⌨️ Type "${text}"`
  } else if (a === "click_element") {
    label = `🖱️ Click ${element}`
  } else if (a === "take_screenshot") {
    label = `📸 Take a screenshot`
  } else if (a === "scroll") {
    label = `📜 Scroll the page`
  } else {
    label = `⚙️ ${a.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase())}`
  }

  return `<div class="task-label">${label}</div>`
}

// ─── Render research card ─────────────────────────────────
// Used by both chat mode (/ask) and task mode (/research-subtype)
function renderResearchCard(data, bubble, skipHistory) {
  let r = data.research
  let a = r.analysis || {}
  if (data.remember && data.remember.state) userContext.state = data.remember.state

  let serviceName = a.service_name || (r.service || "").replace(/_/g, " ")
  let stateName   = a.state || r.state || ""
  let department  = a.department || ""
  let portalName  = a.portal_name || ""
  let portalUrl   = a.portal_url || r.url || ""
  let applyUrl    = a.apply_url || ""
  let fee         = a.fee || ""
  let timeline    = a.processing_time || ""
  let eligibility = a.eligibility || ""
  let validity    = a.validity || ""
  let uploadLimits= a.upload_limits || ""
  let photoSize   = a.photo_size || ""
  let sigSize     = a.signature_size || ""
  let lastVerified= a.last_verified || ""
  let notes       = a.notes || ""
  let docs        = toArray(a.required_documents)
  let steps       = toArray(a.application_steps)
  let faq         = toArray(a.faq)
  let sources     = toArray(a.sources)
  let pdfSources  = toArray(a.pdf_sources)
  if (sources.length === 0 && portalUrl) sources = [portalUrl]

  // ── helper: only render a row if value is non-empty ──
  function infoRow(icon, label, value, cls) {
    if (!value) return ""
    return `<div class="rc-row${cls ? " " + cls : ""}">
      <span class="rc-label">${icon} ${label}</span>
      <span class="rc-value">${escapeHtml(value)}</span>
    </div>`
  }

  // ── portal links (inline, not buttons) ───────────────
  let portalLinkHtml = portalUrl
    ? `<a class="rc-inline-link" href="${safeUrl(portalUrl)}" target="_blank" rel="noopener noreferrer">${escapeHtml(portalName || portalUrl)} ↗</a>`
    : ""
  let applyLinkHtml = (applyUrl && applyUrl !== portalUrl)
    ? `<a class="rc-inline-link" href="${safeUrl(applyUrl)}" target="_blank" rel="noopener noreferrer">Apply here ↗</a>`
    : ""

  // ── documents ─────────────────────────────────────────
  let docsHtml = ""
  if (docs.length > 0) {
    docs.forEach((doc, i) => {
      let name = typeof doc === "string" ? doc : (doc.name || "Document")
      let size = typeof doc === "object" && doc.size ? `<span class="rc-doc-size">${escapeHtml(doc.size)}</span>` : ""
      docsHtml += `<div class="rc-doc-item"><span class="rc-doc-num">${i + 1}</span><span class="rc-doc-name">${escapeHtml(name)}${size}</span></div>`
    })
  } else {
    docsHtml = `<div class="rc-empty">Not specified</div>`
  }

  // ── steps ─────────────────────────────────────────────
  let stepsHtml = ""
  if (steps.length > 0) {
    steps.forEach((step, i) => {
      stepsHtml += `<div class="rc-step"><span class="rc-step-num">${i + 1}</span><div class="rc-step-text">${escapeHtml(step)}</div></div>`
    })
  } else {
    stepsHtml = `<div class="rc-empty">Not specified</div>`
  }

  // ── sources ───────────────────────────────────────────
  let sourcesHtml = ""
  sources.forEach(src => {
    sourcesHtml += `<a class="rc-source-link" href="${safeUrl(src)}" target="_blank" rel="noopener noreferrer">${escapeHtml(src)}</a>`
  })

  // ── pdf chips ─────────────────────────────────────────
  let pdfHtml = ""
  pdfSources.forEach(src => {
    pdfHtml += `<a class="rc-chip" href="${safeUrl(src)}" target="_blank" rel="noopener noreferrer">📄 PDF</a>`
  })

  // ── faq ──────────────────────────────────────────────
  let faqHtml = faq.map(item => `<div class="rc-doc-item">${escapeHtml(item)}</div>`).join("")

  // ── last verified badge text ──────────────────────────
  let verifiedBadge = lastVerified
    ? `<span class="rc-verified-badge">✓ Verified</span>`
    : ""

  bubble.innerHTML = `
  <div class="research-card">

    <div class="rc-header">
      <div class="rc-header-icon">📋</div>
      <div class="rc-header-text">
        <div class="rc-title">${escapeHtml(serviceName.charAt(0).toUpperCase() + serviceName.slice(1))}</div>
        <div class="rc-header-meta">
          <span class="rc-state-pill">${escapeHtml(stateName)}</span>
          ${verifiedBadge}
        </div>
      </div>
    </div>

    <div class="rc-scroll-body">

      <div class="rc-section">
        <div class="rc-section-label">Service Info</div>
        ${infoRow("🏛️", "Department", department)}
        ${portalLinkHtml ? `<div class="rc-row"><span class="rc-label">🌐 Portal</span><span class="rc-value">${portalLinkHtml}</span></div>` : ""}
        ${applyLinkHtml ? `<div class="rc-row"><span class="rc-label">📝 Apply</span><span class="rc-value">${applyLinkHtml}</span></div>` : ""}
        ${infoRow("💰", "Fee", fee)}
        ${infoRow("⏱️", "Processing Time", timeline)}
        ${infoRow("📅", "Validity", validity)}
        ${eligibility ? (() => {
          let lines = eligibility.split(/\n|(?<=\.)\s+(?=[A-Z•\-])/).map(s => s.replace(/^[-•]\s*/, "").trim()).filter(Boolean)
          if (lines.length <= 1) return infoRow("✅", "Eligibility", eligibility, "rc-row-wrap")
          return `<div class="rc-row rc-row-wrap">
            <span class="rc-label">✅ Eligibility</span>
            <ul class="rc-eligibility-list">${lines.map(l => `<li>${escapeHtml(l)}</li>`).join("")}</ul>
          </div>`
        })() : ""}
        ${infoRow("📦", "Upload Limits", uploadLimits)}
        ${infoRow("📸", "Photo Size", photoSize)}
        ${infoRow("✍️", "Signature Size", sigSize)}
      </div>

      <div class="rc-section">
        <div class="rc-section-label">📎 Required Documents</div>
        <div class="rc-docs">${docsHtml}</div>
      </div>

      <details class="rc-expand" open>
        <summary><span class="rc-expand-label">🗂️ Application Steps</span><span class="rc-expand-count">${steps.length || ""}</span></summary>
        <div class="rc-steps">${stepsHtml}</div>
      </details>

      ${notes ? `<div class="rc-notes-block"><span class="rc-notes-icon">💡</span><div class="rc-notes-text">${escapeHtml(notes)}</div></div>` : ""}

      ${faqHtml ? `<details class="rc-expand"><summary><span class="rc-expand-label">❓ FAQ</span></summary><div class="rc-docs" style="margin-top:8px">${faqHtml}</div></details>` : ""}

      ${(sourcesHtml || pdfHtml) ? `
      <details class="rc-expand">
        <summary><span class="rc-expand-label">🔗 Sources & References</span></summary>
        <div class="rc-source-list">${sourcesHtml}</div>
        ${pdfHtml ? `<div class="rc-chip-row" style="margin-top:8px">${pdfHtml}</div>` : ""}
      </details>` : ""}

      ${a.subtypes_note ? `<div class="rc-notes-block"><span class="rc-notes-icon">ℹ️</span><div class="rc-notes-text">${escapeHtml(a.subtypes_note)}</div></div>` : ""}
      ${a.error ? `<div class="rc-error">⚠️ ${escapeHtml(a.error)}</div>` : ""}

    </div>
  </div>
  `
  if (!skipHistory) { chatHistory.push({role: "assistant", content: `Research completed for ${serviceName} in ${stateName}.`}) }
}

// ─── Render assistant content (for replaying saved sessions) ──
function renderAssistantContent(content) {
  if (content && content.startsWith("json:")) {
    try {
      let data = JSON.parse(content.slice(5))
      let tmp = document.createElement("div")
      tmp.className = "ai-bubble"
      if (data.status === "success" && data.tasks) {
        let taskHtml = ""
        data.tasks.forEach(task => {
          taskHtml += `<div class="task-item">${describeTask(task)}</div>`
        })
        tmp.innerHTML = `
          <h3 class="workflow-title">Workflow Created</h3>
          ${taskHtml}
          <details style="margin-top:8px">
            <summary style="color:#64748b;font-size:12px;cursor:pointer">Raw JSON</summary>
            <pre style="font-size:11px;overflow-x:auto">${JSON.stringify(data, null, 2)}</pre>
          </details>`
      } else if (data.status === "research") {
        let fakeDiv = document.createElement("div")
        fakeDiv.className = "ai-bubble"
        document.getElementById("chat-messages").appendChild(fakeDiv)
        renderResearchCard(data, fakeDiv)
        return fakeDiv.outerHTML
      } else if (data.status === "need_clarification") {
        tmp.innerHTML = `<div class="ai-clarification">🤔 ${data.question}</div>`
      } else if (data.status === "needs_subtype") {
        let subtypeBtns = (data.subtypes || []).map(s => `
          <button class="subtype-btn" onclick="pickSubtype('${data.service}','${data.state}','${s.id}','${s.label}',this.closest('.subtype-card'))">
            <span class="subtype-label">${s.label}</span>
            <span class="subtype-desc">${s.description || ""}</span>
          </button>`).join("")
        tmp.innerHTML = `
          <div class="subtype-card">
            <div class="rc-header">
              <span class="rc-icon">🗂️</span>
              <div>
                <div class="rc-title">${data.service_name || ""}</div>
                <div class="rc-subtitle">Which type do you need?</div>
              </div>
            </div>
            <div class="subtype-list">${subtypeBtns}</div>
          </div>`
      } else if (data.status === "conversation" && data.message) {
        tmp.innerHTML = `<div class="ai-message">${(data.message || "").replace(/\n/g, "<br>")}</div>`
      } else {
        tmp.innerHTML = `<pre style="font-size:11px;overflow-x:auto">${JSON.stringify(data, null, 2)}</pre>`
      }
      return tmp.outerHTML
    } catch(e) {
      // JSON parse failed — fall through to plain text
    }
  }
  return `<div class="ai-bubble"><div class="ai-message">${(content || "").replace(/\n/g, "<br>")}</div></div>`
}

// ─── Render chat sessions list ────────────────────────────
function renderChatSessions(data) {
  const backIcon = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>`
  let html = `<div class="title-row">
    <button class="back-btn" onclick="backToChat()">${backIcon}</button>
    <h2>Chat History</h2>
  </div>`

  if (!data.length) {
    html += `<p style="color:#64748b;text-align:center;margin-top:40px">No past conversations yet.</p>`
  }

  data.forEach(item => {
    html += `<div class="card" style="cursor:pointer" onclick="openChatSession(${item.id})">
      <div class="human-header" style="padding-right:0">💬 ${item.title}</div>
      <div style="color:#64748b;font-size:12px">${humanTime(item.updated_at)}</div>
    </div>`
  })
  document.getElementById("data-view").innerHTML = html
}

// ─── Render data view (history / queue / workflows) ───────
function renderData(data, title) {
  const backIcon = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>`
  let type = title === "History" ? "history"
    : title === "Queue" ? "queue"
    : title === "Workflows" ? "workflow" : ""

  let html = `<div class="title-row">
    <button class="back-btn" onclick="backToChat()">${backIcon}</button>
    <h2>${title}</h2>
    <button class="clear-btn" onclick="clearAll('${type}')">Clear All</button>
  </div>`

  if (!data.length) {
    html += `<p style="color:#64748b;text-align:center;margin-top:40px">Nothing here yet.</p>`
  }

  data.forEach(item => {
    let humanText = ""
    let task = item.task || item.workflow || item
    if (typeof task === "string") { try { task = JSON.parse(task) } catch(e){} }

    if (Array.isArray(task)) humanText = `🧠 Workflow with ${task.length} steps`
    else if (task) {
      if (task.action === "search") humanText = `🔎 Searched "${task.query}" on ${task.app}`
      else if (task.action === "send_message") humanText = `📩 Sent message to ${task.target}`
      else if (task.action === "open_website") humanText = `🌐 Opened ${task.url}`
      else if (task.action === "observe_website") humanText = `👀 Observed ${task.url}`
      else if (task.action === "type_text") humanText = `⌨️ Typed "${task.text}"`
      else if (task.action === "click_element") humanText = `🖱️ Clicked ${task.element}`
      else humanText = `⚙️ ${task.action}`
    }

    let statusColor = item.status === "completed" ? "#22c55e"
      : item.status === "failed" ? "#ef4444"
      : item.status === "running" ? "#eab308"
      : item.status === "pending" ? "#64748b"
      : item.status === "permanently_failed" ? "#dc2626" : "#94a3b8"

    html += `<div class="card">
      <div class="human-header">${humanText}</div>
      <div class="status-badge" style="background:${statusColor}">${item.status || "stored"}</div>
      <details>
        <summary>Raw JSON</summary>
        <pre>${JSON.stringify(item, null, 2)}</pre>
        <button class="delete-btn" onclick="deleteItem(${item.id}, '${type}')">🗑</button>
      </details>
    </div>`
  })
  document.getElementById("data-view").innerHTML = html
}

// ─── Render results view ──────────────────────────────────
function renderResults(data) {
  const backIcon = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>`
  let html = `<div class="title-row">
    <button class="back-btn" onclick="backToChat()">${backIcon}</button>
    <h2>Results</h2>
    <button class="clear-btn" onclick="clearAll('results')">Clear All</button>
  </div>`

  if (!data.length) {
    html += `<p style="color:#64748b;text-align:center;margin-top:40px">Nothing here yet.</p>`
  }

  data.forEach(item => {
    html += `<div class="card">
      <button class="delete-btn" onclick="deleteItem(${item.id}, 'results')">🗑</button>
      <div class="human-header">👀 ${item.action}</div>
      <div class="status-badge">Stored</div>
      <pre>${JSON.stringify(item.result, null, 2)}</pre>
    </div>`
  })
  document.getElementById("data-view").innerHTML = html
}
