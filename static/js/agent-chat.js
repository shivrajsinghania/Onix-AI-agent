// agent-chat.js
// ─── agent-chat.js ───────────────────────────────────────
// Chat mode: sending messages, pending queue, offline retry,
// voice input, data loaders (history/queue/workflows/results),
// opening past chat sessions.
// Depends on: agent-infra.js, agent-render.js

// ─── Pending offline queue ────────────────────────────────
let isSending = false

const PENDING_CHAT_KEY = "onix_pending_chat_v1"
let pendingChatQueue = JSON.parse(localStorage.getItem(PENDING_CHAT_KEY) || "[]")
let pendingChatFlushRunning = false

function savePendingChatQueue() {
  localStorage.setItem(PENDING_CHAT_KEY, JSON.stringify(pendingChatQueue))
}

function escapeHTML(text) {
  return String(text || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;")
}

function renderPlainText(text) {
  return escapeHTML(text).replace(/\n/g, "<br>")
}

function getBubbleForLoadingId(loadingId) {
  const loadingEl = document.getElementById(`loading-${loadingId}`)
  return loadingEl ? loadingEl.parentElement : null
}

function setPendingBubble(loadingId, title, subtitle = "") {
  const el = document.getElementById(`loading-${loadingId}`)
  if (!el) return
  el.parentElement.innerHTML = `
  <div class="processing-wrap">
  <div class="processing-dots">
  <span></span><span></span><span></span>
  </div>
  <div class="processing-label">${title}</div>
  ${subtitle ? `<div style="font-size:11px;color:#64748b;text-align:center">${subtitle}</div>` : ""}
  </div>
  `
}

function queuePendingChat(payload, loadingId) {
  pendingChatQueue.push({
    id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    loadingId,
    attempts: 0,
    payload
  })
  savePendingChatQueue()
  setPendingBubble(
    loadingId,
    "Waiting for connection…",
    "It will send automatically when data returns."
  )
}

async function postChatPayload(payload) {
  const response = await fetch("/chat/ask", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  })
  const contentType = response.headers.get("content-type") || ""
  if (!response.ok) {
    const raw = await response.text()
    throw new Error(`HTTP ${response.status}: ${raw.substring(0, 300)}`)
  }
  if (!contentType.includes("application/json")) {
    const raw = await response.text()
    throw new Error(
      `Server returned non-JSON response.\n\nStatus: ${response.status}\n\n${raw.substring(0, 500)}`
    )
  }
  return await response.json()
}

function setBubbleStaticText(bubble, text, className = "ai-message") {
  bubble.innerHTML = `<div class="${className}">${renderPlainText(text)}</div>`
}

function animateAssistantReply(bubble, text, className = "ai-message") {
  const fullText = String(text || "")
  const content = document.createElement("div")
  content.className = className

  const textSpan = document.createElement("span")
  textSpan.className = "streaming-line"

  const cursor = document.createElement("span")
  cursor.className = "streaming-cursor"
  cursor.textContent = "▍"

  content.appendChild(textSpan)
  content.appendChild(cursor)
  bubble.innerHTML = ""
  bubble.appendChild(content)

  if (!fullText) {
    cursor.remove()
    return Promise.resolve()
  }

  const baseDelay = Math.max(10, Math.min(22, Math.round(1200 / Math.max(fullText.length, 90))))
  const chunkSize = fullText.length > 800 ? 10 : fullText.length > 300 ? 6 : fullText.length > 120 ? 4 : 2

  return new Promise(resolve => {
    let index = 0

    const tick = () => {
      index = Math.min(fullText.length, index + chunkSize)
      textSpan.innerHTML = renderPlainText(fullText.slice(0, index))

      if (index < fullText.length) {
        scrollToBottom()
        setTimeout(tick, baseDelay)
      } else {
        cursor.remove()
        scrollToBottom()
        resolve()
      }
    }

    tick()
  })
}

async function flushPendingChatQueue() {
  if (pendingChatFlushRunning || !navigator.onLine || !pendingChatQueue.length) return
  pendingChatFlushRunning = true
  try {
    while (pendingChatQueue.length && navigator.onLine) {
      const item = pendingChatQueue[0]
      setPendingBubble(item.loadingId, "Sending…", "Retrying automatically")
      try {
        const data = await postChatPayload(item.payload)
        if (data.session_id) currentChatSessionId = data.session_id
        if (data.remember && data.remember.state) userContext.state = data.remember.state
        const bubble = getBubbleForLoadingId(item.loadingId)
        if (!bubble) {
          pendingChatQueue.shift()
          savePendingChatQueue()
          continue
        }
        if (data.status === "conversation") {
          await animateAssistantReply(bubble, data.message || "", "ai-message")
          chatHistory.push({ role: "assistant", content: data.message || "" })
        } else if (data.status === "need_clarification") {
          await animateAssistantReply(bubble, `🤔 ${data.question || ""}`, "ai-clarification")
          chatHistory.push({ role: "assistant", content: data.question || "" })
        } else if (data.status === "unsupported") {
          await animateAssistantReply(bubble, `⚠️ ${data.message || ""}`, "ai-unsupported")
          chatHistory.push({ role: "assistant", content: data.message || "" })
        } else if (data.status === "offline") {
          setPendingBubble(item.loadingId, "Waiting for connection…", "Still offline, will retry automatically.")
          break
        } else if (data.status === "research") {
          renderResearchCard(data, bubble, false)
        } else if (data.status === "error") {
          throw new Error(data.message || "Server error")
        }
        pendingChatQueue.shift()
        savePendingChatQueue()
      } catch (e) {
        item.attempts = (item.attempts || 0) + 1
        savePendingChatQueue()
        if (!navigator.onLine || item.attempts >= 5) {
          setPendingBubble(item.loadingId, "Waiting for connection…", "It will retry automatically.")
          break
        }
        await new Promise(r => setTimeout(r, 1500))
      }
    }
  } finally {
    pendingChatFlushRunning = false
  }
}

window.addEventListener("online", flushPendingChatQueue)
setTimeout(flushPendingChatQueue, 1500)

// ─── Send message ─────────────────────────────────────────
async function sendMessage() {
  if (isSending) return
  let messageEl = document.getElementById("message")
  let message = messageEl.value.trim()
  if (!message) return
  isSending = true
  messageEl.value = ""
  autoResize(messageEl)
  showChatView()
  hideEmptyState()
  let loadingId = Date.now()
  addUserMessage(message)
  learnFromMessage(message)
  chatHistory.push({ role: "user", content: message })
  addOnixMessage(`
  <div id="loading-${loadingId}" class="processing-wrap">
  <div class="processing-dots">
  <span></span><span></span><span></span>
  </div>
  <div class="processing-label">Processing…</div>
  </div>
  `)
  scrollToBottom()
  const payload = {
    message: message,
    history: JSON.parse(JSON.stringify(chatHistory)),
    user_context: JSON.parse(JSON.stringify(userContext)),
    session_id: currentChatSessionId
  }
  try {
    if (!navigator.onLine) {
      queuePendingChat(payload, loadingId)
      return
    }
    const data = await postChatPayload(payload)
    if (data.session_id) currentChatSessionId = data.session_id
    if (data.remember && data.remember.state) userContext.state = data.remember.state
    let bubble = getBubbleForLoadingId(loadingId)
    if (!bubble) {
      return
    }
    if (data.status === "offline") {
      queuePendingChat(payload, loadingId)
      return
    }
    if (data.status === "conversation") {
      await animateAssistantReply(bubble, data.message || "", "ai-message")
      chatHistory.push({ role: "assistant", content: data.message || "" })
    } else if (data.status === "need_clarification") {
      await animateAssistantReply(bubble, `🤔 ${data.question || ""}`, "ai-clarification")
      chatHistory.push({ role: "assistant", content: data.question || "" })
    } else if (data.status === "unsupported") {
      await animateAssistantReply(bubble, `⚠️ ${data.message || ""}`, "ai-unsupported")
      chatHistory.push({ role: "assistant", content: data.message || "" })
    } else if (data.status === "error") {
      bubble.innerHTML = `
      <div style="color:#f87171">
      ❌ Error: ${escapeHTML(data.message || "Unknown error")}
      </div>
      <details>
      <summary style="color:#64748b;font-size:12px">Raw response</summary>
      <pre>${escapeHTML(data.raw_response || "")}</pre>
      </details>
      `
    } else if (data.status === "research") {
      renderResearchCard(data, bubble)
    } else if (data.status === "success") {
      let taskHtml = ""
      data.tasks.forEach(task => {
        taskHtml += `<div class="task-item">${describeTask(task)}</div>`
      })
      bubble.innerHTML = `
      <h3 class="workflow-title">Workflow Created</h3>
      ${taskHtml}
      <details style="margin-top:8px">
      <summary style="color:#64748b;font-size:12px;cursor:pointer">Raw JSON</summary>
      <pre style="font-size:11px;overflow-x:auto">${escapeHTML(JSON.stringify(data, null, 2))}</pre>
      </details>
      `
      chatHistory.push({ role: "assistant", content: "workflow created successfully" })
    } else if (data.status === "needs_subtype") {
      let subtypeBtns = data.subtypes.map(s => `
      <button class="subtype-btn" onclick="pickSubtype('${data.service}','${data.state}','${s.id}','${s.label}',this.closest('.subtype-card'))">
      <span class="subtype-label">${escapeHTML(s.label)}</span>
      <span class="subtype-desc">${escapeHTML(s.description || "")}</span>
      </button>
      `).join("")
      bubble.innerHTML = `
      <div class="subtype-card">
      <div class="rc-header">
      <span class="rc-icon">🗂️</span>
      <div>
      <div class="rc-title">${escapeHTML(data.service_name || "")}</div>
      <div class="rc-subtitle">Which type do you need?</div>
      </div>
      </div>
      <div class="subtype-list">${subtypeBtns}</div>
      </div>
      `
      chatHistory.push({
        role: "assistant",
        content: `What type of ${data.service_name} do you need? Options: ${data.subtypes.map(s => s.label).join(", ")}`
      })
    } else if (data.status === "search") {
      let s = data.search || {}
      bubble.innerHTML = `
      <div class="ai-message">
      🔎 Search complete. <a href="${escapeHTML(s.url || "#")}" target="_blank" style="color:#60a5fa">${escapeHTML(s.title || s.url || "")}</a>
      ${s.snippet ? `<div style="color:#94a3b8;font-size:12px;margin-top:4px">${escapeHTML(s.snippet)}</div>` : ""}
      </div>
      `
      chatHistory.push({ role: "assistant", content: `Search result: ${s.title || s.url}` })
    } else {
      bubble.innerHTML = `
      <div style="color:#f87171">
      ❌ Unexpected response from server.
      </div>
      <details>
      <summary style="color:#64748b;font-size:12px">Raw</summary>
      <pre>${escapeHTML(JSON.stringify(data, null, 2))}</pre>
      </details>
      `
    }
  } catch(e) {
    console.error("ASK ERROR:", e)
    if (!navigator.onLine || /Failed to fetch|NetworkError|Load failed/i.test(String(e.message || ""))) {
      queuePendingChat(payload, loadingId)
    } else {
      let loadingEl = document.getElementById(`loading-${loadingId}`)
      if (loadingEl) {
        loadingEl.parentElement.innerHTML = `<div style="color:#f87171">❌ ${escapeHTML(e.message || "Error")}</div>`
      }
    }
  } finally {
    scrollToBottom()
    isSending = false
  }
}

// ─── Subtype picker (chat mode) ───────────────────────────
async function pickSubtype(service, state, subtypeId, subtypeLabel, cardEl) {
  cardEl.innerHTML = `
  <div class="processing-wrap">
    <div class="processing-dots"><span></span><span></span><span></span></div>
    <div class="processing-label">Researching ${escapeHTML(subtypeLabel)}…</div>
  </div>`

  chatHistory.push({role: "user", content: subtypeLabel})
  if (state) userContext.state = state

  try {
    let response = await fetch("/research-subtype", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({
        service, state, subtype: subtypeId,
        subtype_label: subtypeLabel,
        session_id: currentChatSessionId
      })
    })
    let data = await response.json()
    if (data.status === "research") {
      renderResearchCard(data, cardEl)
    } else {
      cardEl.innerHTML = `<div style="color:#f87171">❌ ${escapeHTML(data.message || "Research failed")}</div>`
    }
  } catch(e) {
    cardEl.innerHTML = `<div style="color:#f87171">❌ Network error: ${escapeHTML(e.message || "")}</div>`
  }
  scrollToBottom()
}

// ─── Key handler & auto-resize ────────────────────────────
function handleKey(e) {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault()
    sendMessage()
  }
}

function autoResize(el) {
  el.style.height = "auto"
  el.style.height = Math.min(el.scrollHeight, 160) + "px"
}
document.getElementById("message").addEventListener("input", function() {
  autoResize(this)
})

// ─── Voice input ──────────────────────────────────────────
let recognition = null

function startVoiceInput() {
  const micButton = document.getElementById("micButton")
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition
  if (!SpeechRecognition) {
    alert("Speech recognition is not supported on this browser.")
    return
  }

  if (recognition) {
    recognition.stop()
    recognition = null
    micButton.classList.remove("mic-active", "mic-processing")
    return
  }

  recognition = new SpeechRecognition()
  recognition.lang = "en-US"
  recognition.continuous = false
  recognition.interimResults = false

  micButton.classList.add("mic-active")

  recognition.onresult = function(event) {
    micButton.classList.remove("mic-active")
    micButton.classList.add("mic-processing")
    const text = event.results[0][0].transcript
    document.getElementById("message").value = text
    autoResize(document.getElementById("message"))
  }

  recognition.onend = function() {
    micButton.classList.remove("mic-active", "mic-processing")
    recognition = null
  }

  recognition.onerror = function(event) {
    console.error("Voice error:", event.error)
    micButton.classList.remove("mic-active", "mic-processing")
    recognition = null
  }

  recognition.start()
}

// ─── Data loaders ─────────────────────────────────────────
async function loadHistory() {
  showDataView("History")
  let response = await fetch("/history")
  let data = await response.json()
  renderData(data, "History")
}

async function loadChatSessions() {
  showDataView("Chat History")
  let response = await fetch("/chat-sessions")
  let data = await response.json()
  renderChatSessions(data)
}

async function loadQueue() {
  showDataView("Queue")
  let response = await fetch("/queue")
  let data = await response.json()
  renderData(data, "Queue")
}

async function loadWorkflows() {
  showDataView("Workflows")
  let response = await fetch("/workflows")
  let data = await response.json()
  renderData(data, "Workflows")
}

async function loadResults() {
  showDataView("Results")
  let response = await fetch("/results")
  let data = await response.json()
  renderResults(data)
}

// ─── Open past chat session ───────────────────────────────
async function openChatSession(id) {
  let response = await fetch(`/chat-session/${id}/messages`)
  let messages = await response.json()

  currentChatSessionId = id
  chatHistory = messages.map(m => ({ role: m.role, content: m.content }))
  lastSavedMsgIndex = chatHistory.length

  let html = `<div class="history-banner">
    <span>📜 Viewing past conversation</span>
    <button onclick="newChat()" title="Close">✕</button>
  </div>`

  messages.forEach(m => {
    if (m.role === "user") {
      html += `<div class="user-bubble">${escapeHTML(m.content)}</div>`
    } else {
      html += (typeof renderAssistantContent === "function") ? renderAssistantContent(m.content) : `<div class="ai-bubble">${renderPlainText(m.content)}</div>`
    }
  })

  document.getElementById("chat-messages").innerHTML = html
  showChatView()
  setTimeout(scrollToBottom, 0)
}

// ─── Delete / clear data ──────────────────────────────────
async function deleteItem(id, type) {
  if (!confirm("Delete this item?")) return
  await fetch(`/delete/${type}/${id}`, { method: "DELETE" })
  if (type === "history") loadHistory()
  else if (type === "queue") loadQueue()
  else if (type === "workflow") loadWorkflows()
  else if (type === "results") loadResults()
}

async function clearAll(type) {
  if (!confirm("Delete this entire table?")) return
  await fetch(`/clear/${type}`, { method: "DELETE" })
  if (type === "history") loadHistory()
  else if (type === "queue") loadQueue()
  else if (type === "workflow") loadWorkflows()
  else if (type === "results") loadResults()
}