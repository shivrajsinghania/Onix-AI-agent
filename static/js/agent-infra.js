// ─── agent-infra.js ─────────────────────────────────────
// Shared state, utilities, sidebar, settings, logout, view switching.
// Must be loaded FIRST — all other files depend on these.

// ─── State ──────────────────────────────────────────────
let sidebarOpen = false
let currentView = "chat" // "chat" | "data"
let chatHistory = []
let currentChatSessionId = null   // DB id of the active conversation, null = not yet created
let lastSavedMsgIndex = 0          // how many chatHistory entries have been persisted so far
let currentMode = "task"           // "chat" | "task" — Task is default

// Remembered facts about the user — sent with every request so AI never asks twice
let userContext = {
  state: null,
  name: null
}

// ─── Context learning ────────────────────────────────────
// Extract and remember key facts from any message
function learnFromMessage(text) {
  if (!text) return
  const lower = text.toLowerCase()

  const stateMap = {
    "bihar": "Bihar", "delhi": "Delhi", "maharashtra": "Maharashtra",
    "uttar pradesh": "Uttar Pradesh", " up ": "Uttar Pradesh",
    "rajasthan": "Rajasthan", "gujarat": "Gujarat",
    "west bengal": "West Bengal", "bengal": "West Bengal",
    "tamil nadu": "Tamil Nadu", "karnataka": "Karnataka",
    "kerala": "Kerala", "madhya pradesh": "Madhya Pradesh",
    "andhra pradesh": "Andhra Pradesh", "telangana": "Telangana",
    "punjab": "Punjab", "haryana": "Haryana", "odisha": "Odisha",
    "jharkhand": "Jharkhand", "chhattisgarh": "Chhattisgarh",
    "assam": "Assam", "uttarakhand": "Uttarakhand",
    "himachal pradesh": "Himachal Pradesh", "goa": "Goa",
    "manipur": "Manipur", "meghalaya": "Meghalaya",
    "tripura": "Tripura", "nagaland": "Nagaland",
    "mizoram": "Mizoram", "sikkim": "Sikkim",
    "arunachal pradesh": "Arunachal Pradesh",
    "jammu": "Jammu & Kashmir", "kashmir": "Jammu & Kashmir",
    "ladakh": "Ladakh"
  }

  const cityToState = {
    "patna": "Bihar", "gaya": "Bihar", "muzaffarpur": "Bihar",
    "bhagalpur": "Bihar", "darbhanga": "Bihar", "purnia": "Bihar",
    "arrah": "Bihar", "begusarai": "Bihar", "katihar": "Bihar",
    "munger": "Bihar", "chapra": "Bihar", "samastipur": "Bihar",
    "hajipur": "Bihar", "jehanabad": "Bihar", "nawada": "Bihar",
    "nalanda": "Bihar", "sitamarhi": "Bihar", "vaishali": "Bihar",
    "siwan": "Bihar", "saran": "Bihar", "buxar": "Bihar",
    "rohtas": "Bihar", "aurangabad": "Bihar", "jamui": "Bihar",
    "lakhisarai": "Bihar", "sheikhpura": "Bihar", "supaul": "Bihar",
    "madhepura": "Bihar", "saharsa": "Bihar", "khagaria": "Bihar",
    "madhubani": "Bihar", "east champaran": "Bihar",
    "west champaran": "Bihar", "motihari": "Bihar",
    "bettiah": "Bihar", "gopalganj": "Bihar",
    "lucknow": "Uttar Pradesh", "kanpur": "Uttar Pradesh",
    "agra": "Uttar Pradesh", "varanasi": "Uttar Pradesh",
    "allahabad": "Uttar Pradesh", "prayagraj": "Uttar Pradesh",
    "meerut": "Uttar Pradesh", "noida": "Uttar Pradesh",
    "ghaziabad": "Uttar Pradesh", "mathura": "Uttar Pradesh",
    "gorakhpur": "Uttar Pradesh", "aligarh": "Uttar Pradesh",
    "rohini": "Delhi", "dwarka": "Delhi", "janakpuri": "Delhi",
    "saket": "Delhi", "pitampura": "Delhi", "lajpat": "Delhi",
    "connaught": "Delhi", "karol bagh": "Delhi",
    "mumbai": "Maharashtra", "pune": "Maharashtra",
    "nagpur": "Maharashtra", "nashik": "Maharashtra",
    "thane": "Maharashtra", "aurangabad mh": "Maharashtra",
    "jaipur": "Rajasthan", "jodhpur": "Rajasthan",
    "udaipur": "Rajasthan", "kota": "Rajasthan",
    "ajmer": "Rajasthan", "bikaner": "Rajasthan",
    "ahmedabad": "Gujarat", "surat": "Gujarat",
    "vadodara": "Gujarat", "rajkot": "Gujarat",
    "kolkata": "West Bengal", "howrah": "West Bengal",
    "siliguri": "West Bengal", "asansol": "West Bengal",
    "chennai": "Tamil Nadu", "coimbatore": "Tamil Nadu",
    "madurai": "Tamil Nadu", "salem": "Tamil Nadu",
    "bangalore": "Karnataka", "bengaluru": "Karnataka",
    "mysore": "Karnataka", "hubli": "Karnataka",
    "ranchi": "Jharkhand", "jamshedpur": "Jharkhand",
    "dhanbad": "Jharkhand", "bokaro": "Jharkhand",
    "bhopal": "Madhya Pradesh", "indore": "Madhya Pradesh",
    "raipur": "Chhattisgarh", "hyderabad": "Telangana",
    "chandigarh": "Punjab", "amritsar": "Punjab",
    "ludhiana": "Punjab", "guwahati": "Assam",
    "dehradun": "Uttarakhand", "shimla": "Himachal Pradesh",
    "bhubaneswar": "Odisha", "cuttack": "Odisha",
    "thiruvananthapuram": "Kerala", "kochi": "Kerala",
    "kozhikode": "Kerala", "visakhapatnam": "Andhra Pradesh",
    "vijayawada": "Andhra Pradesh"
  }

  const sortedStates = Object.keys(stateMap).sort((a, b) => b.length - a.length)
  for (let s of sortedStates) {
    if (lower.includes(s)) {
      userContext.state = stateMap[s]
      console.log("[context] Learned state:", userContext.state, "from:", s)
      return
    }
  }

  for (let [city, state] of Object.entries(cityToState)) {
    if (lower.includes(city)) {
      userContext.state = state
      console.log("[context] Learned state:", state, "from city:", city)
      return
    }
  }
}

// ─── Utility helpers ─────────────────────────────────────
function escapeHtml(text) {
  return String(text ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;")
}

function safeUrl(url) {
  try {
    const u = new URL(url)
    return (u.protocol === "http:" || u.protocol === "https:") ? u.href : "#"
  } catch {
    return "#"
  }
}

function toArray(value) {
  if (Array.isArray(value)) return value
  if (value == null || value === "") return []
  return [value]
}

function capitalize(str) {
  if (!str) return ""
  return str.charAt(0).toUpperCase() + str.slice(1)
}

function siteName(url) {
  if (!url) return ""
  try {
    let host = new URL(url).hostname.replace(/^www\./, "")
    let parts = host.split(".")
    let name = parts[parts.length - 2] || host
    return name.charAt(0).toUpperCase() + name.slice(1)
  } catch(e) { return url }
}

function humanTime(dateStr) {
  if (!dateStr) return ""
  let normalized = dateStr.trim().replace(" ", "T")
  if (!normalized.endsWith("Z") && !normalized.includes("+")) normalized += "Z"
  let d = new Date(normalized)
  if (isNaN(d)) return dateStr
  let now = new Date()
  let diff = Math.floor((now - d) / 1000)
  if (diff < 60) return "just now"
  if (diff < 3600) return Math.floor(diff / 60) + "m ago"
  if (diff < 86400) return Math.floor(diff / 3600) + "h ago"
  if (diff < 172800) return "yesterday"
  if (diff < 604800) return Math.floor(diff / 86400) + "d ago"
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric" })
}

// ─── Input bar visibility ────────────────────────────────
function showInputBar() {
  document.getElementById("inputBar").style.display = "block"
  document.getElementById("mainArea").classList.remove("no-inputbar")
}
function hideInputBar() {
  document.getElementById("inputBar").style.display = "none"
  document.getElementById("mainArea").classList.add("no-inputbar")
}

// ─── Auto-scroll ─────────────────────────────────────────
function scrollToBottom() {
  let mainArea = document.getElementById("mainArea")
  if (mainArea) mainArea.scrollTop = mainArea.scrollHeight
}

function syncChatHistory() {
  return;
}

// ─── Sidebar ─────────────────────────────────────────────
function openSidebar() {
  sidebarOpen = true
  document.getElementById("sidebar").classList.add("open")
  document.getElementById("sidebarOverlay").classList.add("show")
  loadSidebarHistory()
  history.pushState({ sidebar: true }, "")
}

function closeSidebar() {
  if (!sidebarOpen) return
  sidebarOpen = false
  document.getElementById("sidebar").classList.remove("open")
  document.getElementById("sidebarOverlay").classList.remove("show")
  closeSettings()
}

window.addEventListener("popstate", function(e) {
  if (sidebarOpen) closeSidebar()
})

// Swipe left to close sidebar
let touchStartX = 0, touchStartY = 0
document.getElementById("sidebar").addEventListener("touchstart", function(e) {
  touchStartX = e.touches[0].clientX
  touchStartY = e.touches[0].clientY
}, { passive: true })
document.getElementById("sidebar").addEventListener("touchend", function(e) {
  let dx = e.changedTouches[0].clientX - touchStartX
  let dy = Math.abs(e.changedTouches[0].clientY - touchStartY)
  if (dx < -60 && dy < 80) {
    closeSidebar()
    history.back()
  }
}, { passive: true })

// ─── Sidebar history loader ───────────────────────────────
async function loadSidebarHistory() {
  let content = document.getElementById("sidebarContent")
  content.innerHTML = "<p class='sidebar-empty'>Loading...</p>"
  try {
    let response = await fetch("/chat-sessions")
    let data = await response.json()
    if (!data.length) {
      content.innerHTML = "<p class='sidebar-empty'>No conversations yet.</p>"
      return
    }
    let html = ""
    data.slice(0, 10).forEach(item => {
      let title = item.title || "Conversation"
      let time = humanTime(item.updated_at)
      html += `<div class="sidebar-item sidebar-item-clickable" onclick="closeSidebar(); openChatSession(${item.id})">
        <div class="sidebar-item-label">💬 ${title}</div>
        <span class="sidebar-item-time">${time}</span>
      </div>`
    })
    content.innerHTML = html
  } catch(e) {
    content.innerHTML = "<p class='sidebar-empty'>Could not load history.</p>"
  }
}

// ─── Settings modal ───────────────────────────────────────
function openSettings() {
  document.getElementById("settingsModal").classList.add("open")
  document.getElementById("modalOverlay").classList.add("show")
}
function closeSettings() {
  document.getElementById("settingsModal").classList.remove("open")
  document.getElementById("modalOverlay").classList.remove("show")
}

function openSection(section) {
  closeSettings()
  closeSidebar()
  if (history.state && history.state.sidebar) history.back()
  if (section === "history") loadHistory()
  else if (section === "queue") loadQueue()
  else if (section === "workflows") loadWorkflows()
  else if (section === "results") loadResults()
}

// ─── History choice popup ─────────────────────────────────
function openHistoryPopup() {
  let popup = document.getElementById("historyPopup")
  let btn = document.getElementById("viewAllHistoryBtn")
  let rect = btn.getBoundingClientRect()
  popup.style.left = rect.left + "px"
  popup.style.width = rect.width + "px"
  popup.style.bottom = (window.innerHeight - rect.top + 8) + "px"
  popup.style.top = "auto"
  popup.classList.add("open")
  setTimeout(() => document.addEventListener("click", closeHistoryPopupOutside), 0)
}
function closeHistoryPopup() {
  document.getElementById("historyPopup").classList.remove("open")
  document.removeEventListener("click", closeHistoryPopupOutside)
}
function closeHistoryPopupOutside(e) {
  let popup = document.getElementById("historyPopup")
  let btn = document.getElementById("viewAllHistoryBtn")
  if (!popup.contains(e.target) && !btn.contains(e.target)) closeHistoryPopup()
}

// ─── Logout ───────────────────────────────────────────────
function sessionLogout() {
  showLogoutModal()
}

function showLogoutModal() {
  document.getElementById("logoutModal").classList.add("open")
}

function hideLogoutModal() {
  document.getElementById("logoutModal").classList.remove("open")
}

function confirmLogout() {
  hideLogoutModal()
  let screen = document.getElementById("logoutScreen")
  screen.classList.add("active")
  requestAnimationFrame(() => requestAnimationFrame(() => screen.classList.add("visible")))
  setTimeout(() => { window.location.replace("/logout") }, 1200)
}

// ─── View switching ───────────────────────────────────────
function showChatView() {
  currentView = "chat"
  document.getElementById("chat-view").style.display = "block"
  document.getElementById("data-view").style.display = "none"
  document.getElementById("task-view").style.display = "none"
  document.getElementById("modeChatBtn").classList.add("active")
  document.getElementById("modeTaskBtn").classList.remove("active")
  currentMode = "chat"
  showInputBar()
}

function showDataView(title) {
  currentView = "data"
  document.getElementById("chat-view").style.display = "none"
  document.getElementById("data-view").style.display = "block"
  document.getElementById("task-view").style.display = "none"
  hideInputBar()
}

function hideEmptyState() {
  let empty = document.getElementById("output")
  if (empty) empty.style.display = "none"
}

function newChat() {
  if (currentMode === "task") {
    document.getElementById("taskService").value = ""
    let labelEl = document.getElementById("serviceDDLabel")
    if (labelEl) {
      labelEl.textContent = "Select a government service…"
      labelEl.classList.add("placeholder")
    }
    document.getElementById("task-result").innerHTML = ""
    return
  }
  chatHistory = []
  currentChatSessionId = null
  lastSavedMsgIndex = 0
  userContext = { state: null, name: null }
  let container = document.getElementById("chat-messages")
  container.innerHTML = `
    <div id="output" class="output-empty">
      <div class="empty-icon">
        <img src="/static/icon-192.png" alt="Onix">
      </div>
      <div class="empty-title">What can I do for you?</div>
      <div class="empty-sub">Type a command below to get started.</div>
    </div>
  `
  showChatView()
  document.getElementById("message").focus()
}

function addUserMessage(text) {
  let container = document.getElementById("chat-messages")
  let div = document.createElement("div")
  div.className = "bubble-wrapper user-side"
  div.innerHTML = `<div class="user-bubble">${text}</div>`
  container.appendChild(div)
  return div
}

function addOnixMessage(html) {
  let container = document.getElementById("chat-messages")
  let div = document.createElement("div")
  div.className = "bubble-wrapper ai-side"
  let bubble = document.createElement("div")
  bubble.className = "ai-bubble"
  bubble.innerHTML = html
  div.appendChild(bubble)
  container.appendChild(div)
  return bubble
}

function backToChat() {
  showChatView()
}
