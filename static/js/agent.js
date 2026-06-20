// ─── State ─────────────────────────────────────────────
      let sidebarOpen = false
      let currentView = "chat" // "chat" | "data"
      let chatHistory = []
      let currentChatSessionId = null   // DB id of the active conversation, null = not yet created
      let lastSavedMsgIndex = 0          // how many chatHistory entries have been persisted so far
      // Remembered facts about the user — sent with every request so AI never asks twice
      let userContext = {
        state: null,
        name: null
      }

      // Extract and remember key facts from any message
      function learnFromMessage(text) {
        if (!text) return
        const lower = text.toLowerCase()

        // Full state names
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

        // Cities and districts → their state
        const cityToState = {
          // Bihar cities/districts
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
          // UP cities
          "lucknow": "Uttar Pradesh", "kanpur": "Uttar Pradesh",
          "agra": "Uttar Pradesh", "varanasi": "Uttar Pradesh",
          "allahabad": "Uttar Pradesh", "prayagraj": "Uttar Pradesh",
          "meerut": "Uttar Pradesh", "noida": "Uttar Pradesh",
          "ghaziabad": "Uttar Pradesh", "mathura": "Uttar Pradesh",
          "gorakhpur": "Uttar Pradesh", "aligarh": "Uttar Pradesh",
          // Delhi areas
          "rohini": "Delhi", "dwarka": "Delhi", "janakpuri": "Delhi",
          "saket": "Delhi", "pitampura": "Delhi", "lajpat": "Delhi",
          "connaught": "Delhi", "karol bagh": "Delhi",
          // Maharashtra cities
          "mumbai": "Maharashtra", "pune": "Maharashtra",
          "nagpur": "Maharashtra", "nashik": "Maharashtra",
          "thane": "Maharashtra", "aurangabad mh": "Maharashtra",
          // Rajasthan
          "jaipur": "Rajasthan", "jodhpur": "Rajasthan",
          "udaipur": "Rajasthan", "kota": "Rajasthan",
          "ajmer": "Rajasthan", "bikaner": "Rajasthan",
          // Gujarat
          "ahmedabad": "Gujarat", "surat": "Gujarat",
          "vadodara": "Gujarat", "rajkot": "Gujarat",
          // West Bengal
          "kolkata": "West Bengal", "howrah": "West Bengal",
          "siliguri": "West Bengal", "asansol": "West Bengal",
          // Tamil Nadu
          "chennai": "Tamil Nadu", "coimbatore": "Tamil Nadu",
          "madurai": "Tamil Nadu", "salem": "Tamil Nadu",
          // Karnataka
          "bangalore": "Karnataka", "bengaluru": "Karnataka",
          "mysore": "Karnataka", "hubli": "Karnataka",
          // Jharkhand
          "ranchi": "Jharkhand", "jamshedpur": "Jharkhand",
          "dhanbad": "Jharkhand", "bokaro": "Jharkhand",
          // Others
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

        // Check state names first (longest match wins)
        const sortedStates = Object.keys(stateMap).sort((a,b) => b.length - a.length)
        for (let s of sortedStates) {
          if (lower.includes(s)) {
            userContext.state = stateMap[s]
            console.log("[context] Learned state:", userContext.state, "from:", s)
            return
          }
        }

        // Then check city/district names
        for (let [city, state] of Object.entries(cityToState)) {
          if (lower.includes(city)) {
            userContext.state = state
            console.log("[context] Learned state:", state, "from city:", city)
            return
          }
        }
      }
      
      // ─── Input bar visibility ──────────────────────────────
      function showInputBar() {
        document.getElementById("inputBar").style.display = "block"
      }
      function hideInputBar() {
        document.getElementById("inputBar").style.display = "none"
      }

      // ─── Auto-scroll ────────────────────────────────────────
      function scrollToBottom() {
        let mainArea = document.getElementById("mainArea")
        if (mainArea) mainArea.scrollTop = mainArea.scrollHeight
      }

      function syncChatHistory() {
        return;
      }

      // ─── Sidebar ───────────────────────────────────────────
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

      // ─── Sidebar history loader ────────────────────────────
      async function loadSidebarHistory() {
        let content = document.getElementById("sidebarContent")
        content.innerHTML = "<p class='sidebar-empty'>Loading...</p>"
        try {
          let response = await fetch("/history")
          let data = await response.json()
          if (!data.length) {
            content.innerHTML = "<p class='sidebar-empty'>No history yet.</p>"
            return
          }
          let html = ""
          // show latest 10 only in sidebar
          data.slice(0, 10).forEach(item => {
            let task = item.task || item.workflow || item
            if (typeof task === "string") { try { task = JSON.parse(task) } catch(e){} }
            let label = "⚙️ Task"
            if (Array.isArray(task)) label = `🧠 Workflow (${task.length} steps)`
            else if (task && task.action === "search") label = `🔎 ${task.query}`
            else if (task && task.action === "send_message") label = `📩 → ${task.target}`
            else if (task && task.action === "open_website") label = `🌐 ${task.url}`
            else if (task && task.action) label = `⚙️ ${task.action}`
            let statusColor = item.status === "completed" ? "#22c55e"
              : item.status === "failed" || item.status === "permanently_failed" ? "#ef4444"
              : item.status === "running" ? "#eab308" : "#64748b"
            html += `<div class="sidebar-item">
              <div class="sidebar-item-label">${label}</div>
              <span class="sidebar-item-status" style="background:${statusColor}">${item.status || "stored"}</span>
            </div>`
          })
          content.innerHTML = html
        } catch(e) {
          content.innerHTML = "<p class='sidebar-empty'>Could not load history.</p>"
        }
      }

      // ─── Settings modal ────────────────────────────────────
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

      // ─── History choice popup ──────────────────────────────
      function openHistoryPopup() {
        let popup = document.getElementById("historyPopup")
        let btn = document.getElementById("viewAllHistoryBtn")
        let rect = btn.getBoundingClientRect()
        // Position the popup just above the button, aligned to its left edge
        popup.style.left = rect.left + "px"
        popup.style.width = rect.width + "px"
        popup.style.bottom = (window.innerHeight - rect.top + 8) + "px"
        popup.style.top = "auto"
        popup.classList.add("open")
        // close on outside click
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
        // trigger transition on next frame
        requestAnimationFrame(() => requestAnimationFrame(() => screen.classList.add("visible")))
        setTimeout(() => { window.location.replace("/logout") }, 1200)
      }
      
      // ─── View switching ────────────────────────────────────
      function showChatView() {
        currentView = "chat"
        document.getElementById("chat-view").style.display = "block"
        document.getElementById("data-view").style.display = "none"
        document.getElementById("topbarTitle").innerText = "Onix"
        showInputBar()
      }

      function showDataView(title) {
        currentView = "data"
        document.getElementById("chat-view").style.display = "none"
        document.getElementById("data-view").style.display = "block"
        document.getElementById("topbarTitle").innerText = title
        hideInputBar()
      }

      function hideEmptyState() {
        let empty = document.getElementById("output")
        if (empty) empty.style.display = "none"
      }

      function newChat() {
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

      function addUserMessage(text){
        let container = document.getElementById("chat-messages")
        container.innerHTML += `
        <div class="user-bubble">
        ${text}
        </div>
        `
      }
      
      function addOnixMessage(html){
        let container = document.getElementById("chat-messages")
        container.innerHTML += `
        <div class="ai-bubble">
        ${html}
        </div>
        `
      }
      
      // ─── Human-readable task descriptions ─────────────────
      function siteName(url) {
        if (!url) return ""
        try {
          let host = new URL(url).hostname.replace(/^www\./, "")
          let parts = host.split(".")
          let name = parts[parts.length - 2] || host
          return name.charAt(0).toUpperCase() + name.slice(1)
        } catch(e) { return url }
      }

      function capitalize(str) {
        if (!str) return ""
        return str.charAt(0).toUpperCase() + str.slice(1)
      }


      // ─── Render research card (shared by /ask and /research-subtype) ──────
      function renderResearchCard(data, bubble) {
        let r = data.research
        let a = r.analysis || {}
        if (data.remember && data.remember.state) userContext.state = data.remember.state

        let serviceName = a.service_name || (r.service || "").replace(/_/g, " ")
        let stateName = a.state || r.state || ""
        let fee = a.fee || "Not mentioned"
        let timeline = a.processing_time || "Not mentioned"

        let docsHtml = ""
        let docs = a.required_documents || []
        if (docs.length > 0) {
          docs.forEach((doc, i) => {
            let label = String.fromCharCode(65 + i)
            let sizeNote = doc.size ? ` <span style="color:#94a3b8;font-size:12px">(${doc.size})</span>` : ""
            docsHtml += `<div class="rc-doc-item">(<b>${label}</b>) ${doc.name}${sizeNote}</div>`
          })
        } else {
          docsHtml = `<div style="color:#94a3b8;font-size:13px">No documents listed on this page.</div>`
        }

        let stepsHtml = ""
        let steps = a.application_steps || []
        if (steps.length > 0) {
          steps.forEach((step, i) => {
            stepsHtml += `<div class="rc-step"><span class="rc-step-num">${i+1}</span>${step}</div>`
          })
        }

        let specsHtml = ""
        if (a.photo_requirements) specsHtml += `<div class="rc-row"><span class="rc-label">📸 Photo</span><span class="rc-value">${a.photo_requirements}</span></div>`
        if (a.signature_requirements) specsHtml += `<div class="rc-row"><span class="rc-label">✍️ Signature</span><span class="rc-value">${a.signature_requirements}</span></div>`

        bubble.innerHTML = `
        <div class="research-card">
          <div class="rc-header">
            <span class="rc-icon">📄</span>
            <div>
              <div class="rc-title">${serviceName.charAt(0).toUpperCase() + serviceName.slice(1)}</div>
              <div class="rc-subtitle">Research Result${a.source === 'training_knowledge' ? ' · <span style="color:#f59e0b">From Training Knowledge</span>' : ' · <span style="color:#22c55e">Live Data</span>'}</div>
            </div>
          </div>
          <div class="rc-row"><span class="rc-label">🏛️ Service Type</span><span class="rc-value">${serviceName}</span></div>
          <div class="rc-row"><span class="rc-label">📍 State</span><span class="rc-value">${stateName.charAt(0).toUpperCase() + stateName.slice(1)}</span></div>
          <div class="rc-row"><span class="rc-label">💰 Fee</span><span class="rc-value">${fee}</span></div>
          <div class="rc-row"><span class="rc-label">⏱️ Timeline</span><span class="rc-value">${timeline}</span></div>
          ${a.eligibility ? `<div class="rc-row"><span class="rc-label">✅ Eligibility</span><span class="rc-value">${a.eligibility}</span></div>` : ""}
          ${a.validity ? `<div class="rc-row"><span class="rc-label">📅 Validity</span><span class="rc-value">${a.validity}</span></div>` : ""}
          ${specsHtml}
          <div class="rc-section-title">📎 Required Documents</div>
          <div class="rc-docs">${docsHtml}</div>
          ${stepsHtml ? `<div class="rc-section-title">📋 Application Steps</div><div class="rc-steps">${stepsHtml}</div>` : ""}
          ${a.subtypes_note ? `<div class="rc-section-title">ℹ️ Note</div><div class="rc-notes">${a.subtypes_note}</div>` : ""}
          ${a.notes ? `<div class="rc-section-title">📝 Notes</div><div class="rc-notes">${a.notes}</div>` : ""}
          ${a.error ? `<div style="color:#f87171;font-size:12px;margin-top:8px">⚠️ ${a.error}</div>` : ""}
          <div class="rc-source">🔗 Source: <a href="${r.url}" target="_blank" style="color:#60a5fa">${r.url}</a></div>
        </div>
        `
        chatHistory.push({role: "assistant", content: `Research completed for ${serviceName} in ${stateName}. User is applying in ${stateName}.`})
      }

      // ─── Subtype picker handler ────────────────────────────────────────────
      async function pickSubtype(service, state, subtypeId, subtypeLabel, cardEl) {
        // Replace the card with a loading state
        cardEl.innerHTML = `
        <div class="processing-wrap">
          <div class="processing-dots"><span></span><span></span><span></span></div>
          <div class="processing-label">Researching ${subtypeLabel}…</div>
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
            cardEl.innerHTML = `<div style="color:#f87171">❌ ${data.message || "Research failed"}</div>`
          }
        } catch(e) {
          cardEl.innerHTML = `<div style="color:#f87171">❌ Network error: ${e.message}</div>`
        }
        scrollToBottom()
      }

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
          // Fallback: prettify snake_case
          label = `⚙️ ${a.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase())}`
        }

        return `<div class="task-label">${label}</div>`
      }

      // ─── Chat ──────────────────────────────────────────────
      let isSending = false
      
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
        learnFromMessage(message)  // remember state/facts from user input
        chatHistory.push({role: "user", content: message})
        addOnixMessage(`
        <div id="loading-${loadingId}" class="processing-wrap">
        <div class="processing-dots">
        <span></span><span></span><span></span>
        </div>
        <div class="processing-label">Processing…</div>
        </div>
        `)
        scrollToBottom()
        try {
          let response = await fetch("/ask", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({
              message: message,
              history: chatHistory,
              user_context: userContext,   // send remembered facts
              session_id: currentChatSessionId
            })
          })
          const contentType = response.headers.get("content-type") || ""
          if (!contentType.includes("application/json")) {
            const raw = await response.text()
            throw new Error(
              `Server returned non-JSON response.\n\nStatus: ${response.status}\n\n${raw.substring(0,500)}`
            )
          }
          const data = await response.json()
          if (data.session_id) currentChatSessionId = data.session_id

          // If backend tells us to remember something, store it
          if (data.remember) {
            if (data.remember.state) userContext.state = data.remember.state
          }

          let bubble = document.getElementById(`loading-${loadingId}`).parentElement
          // AI needs more info
          if (data.status === "conversation") {
            // Normal chat message — display as plain text
            let msg = data.message || ""
            // Convert \n to <br> for display
            msg = msg.replace(/\n/g, "<br>")
            bubble.innerHTML = `<div class="ai-message">${msg}</div>`
            chatHistory.push({role: "assistant", content: data.message || ""})

          } else if (data.status === "need_clarification") {
            bubble.innerHTML = `
            <div class="ai-clarification">
            🤔 ${data.question}
            </div>
            <details style="margin-top:6px">
            <summary style="color:#64748b;font-size:11px;cursor:pointer">Raw JSON</summary>
            <pre style="font-size:11px">${JSON.stringify(data, null, 2)}</pre>
            </details>
            `
            chatHistory.push({role: "assistant", content: data.question})

          } else if (data.status === "unsupported") {
            bubble.innerHTML = `
            <div class="ai-unsupported">
            ⚠️ ${data.message}
            </div>
            `
            chatHistory.push({role: "assistant", content: data.message || ""})

          } else if (data.status === "error") {
            bubble.innerHTML = `
            <div style="color:#f87171">
            ❌ Error: ${data.message}
            </div>
            <details>
            <summary style="color:#64748b;font-size:12px">Raw response</summary>
            <pre>${data.raw_response || ""}</pre>
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
            <pre style="font-size:11px;overflow-x:auto">${JSON.stringify(data, null, 2)}</pre>
            </details>
            `
            chatHistory.push({role: "assistant", content: "workflow created successfully"})

          } else if (data.status === "needs_subtype") {
            // User must pick a subtype before SerpAPI credit is spent
            let subtypeBtns = data.subtypes.map(s => `
              <button class="subtype-btn" onclick="pickSubtype('${data.service}','${data.state}','${s.id}','${s.label}',this.closest('.subtype-card'))">
                <span class="subtype-label">${s.label}</span>
                <span class="subtype-desc">${s.description || ""}</span>
              </button>
            `).join("")
            bubble.innerHTML = `
            <div class="subtype-card">
              <div class="rc-header">
                <span class="rc-icon">🗂️</span>
                <div>
                  <div class="rc-title">${data.service_name}</div>
                  <div class="rc-subtitle">Which type do you need?</div>
                </div>
              </div>
              <div class="subtype-list">${subtypeBtns}</div>
            </div>
            `
            chatHistory.push({role: "assistant", content: `What type of ${data.service_name} do you need? Options: ${data.subtypes.map(s=>s.label).join(", ")}`})

          } else if (data.status === "search") {
            let s = data.search || {}
            bubble.innerHTML = `
            <div class="ai-message">
              🔎 Search complete. <a href="${s.url}" target="_blank" style="color:#60a5fa">${s.title || s.url}</a>
              ${s.snippet ? `<div style="color:#94a3b8;font-size:12px;margin-top:4px">${s.snippet}</div>` : ""}
            </div>
            `
            chatHistory.push({role: "assistant", content: `Search result: ${s.title || s.url}`})

          } else {
            bubble.innerHTML = `
            <div style="color:#f87171">
            ❌ Unexpected response from server.
            </div>
            <details>
            <summary style="color:#64748b;font-size:12px">Raw</summary>
            <pre>${JSON.stringify(data, null, 2)}</pre>
            </details>
            `
          }

        } catch(e) {
          console.error("ASK ERROR:", e)
          let loadingEl = document.getElementById(`loading-${loadingId}`)
          if (loadingEl) {
            loadingEl.parentElement.innerHTML = `
            <div style="color:#f87171">
            ❌ ${e.message}
            </div>
            `
          }
        } finally {
          scrollToBottom()
          isSending = false
        }
      }
        
      function handleKey(e) {
        if (e.key === "Enter" && !e.shiftKey) {
          e.preventDefault()
          sendMessage()
        }
      }

      function autoResize(el) {
        el.style.height = "auto"
        el.style.height = Math.min(el.scrollHeight, 140) + "px"
      }
      document.getElementById("message").addEventListener("input", function() {
        autoResize(this)
      })

      // ─── Data loaders ──────────────────────────────────────
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

      function humanTime(dateStr) {
        if (!dateStr) return ""
        // SQLite returns UTC timestamps without "Z" — add it so JS parses correctly
        let normalized = dateStr.trim().replace(" ", "T")
        if (!normalized.endsWith("Z") && !normalized.includes("+")) normalized += "Z"
        let d = new Date(normalized)
        if (isNaN(d)) return dateStr
        let now = new Date()
        let diff = Math.floor((now - d) / 1000) // seconds
        if (diff < 60) return "just now"
        if (diff < 3600) return Math.floor(diff / 60) + "m ago"
        if (diff < 86400) return Math.floor(diff / 3600) + "h ago"
        if (diff < 172800) return "yesterday"
        if (diff < 604800) return Math.floor(diff / 86400) + "d ago"
        return d.toLocaleDateString(undefined, { month: "short", day: "numeric" })
      }

      function renderChatSessions(data) {
        let html = `<div class="title-row">
          <button class="back-btn" onclick="backToChat()">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
              <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
          </button>
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

      function renderAssistantContent(content) {
        // Backend saves structured responses as "json:{...}"
        if (content && content.startsWith("json:")) {
          try {
            let data = JSON.parse(content.slice(5))
            let tmp = document.createElement("div")
            tmp.className = "ai-bubble"
            // Re-use the exact same rendering logic as live chat
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
              // Unknown structured type — show as formatted JSON
              tmp.innerHTML = `<pre style="font-size:11px;overflow-x:auto">${JSON.stringify(data, null, 2)}</pre>`
            }
            return tmp.outerHTML
          } catch(e) {
            // JSON parse failed — fall through to plain text
          }
        }
        // Plain text message
        return `<div class="ai-bubble"><div class="ai-message">${(content || "").replace(/\n/g, "<br>")}</div></div>`
      }

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
            html += `<div class="user-bubble">${m.content}</div>`
          } else {
            html += renderAssistantContent(m.content)
          }
        })

        document.getElementById("chat-messages").innerHTML = html
        showChatView()
        setTimeout(scrollToBottom, 0)
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

      function backToChat() {
        showChatView()
      }

      function renderData(data, title) {
        let type = title === "History" ? "history"
          : title === "Queue" ? "queue"
          : title === "Workflows" ? "workflow" : ""

        let html = `<div class="title-row">
          <button class="back-btn" onclick="backToChat()">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
              <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
          </button>
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

      function renderResults(data) {
        let html = `<div class="title-row">
          <button class="back-btn" onclick="backToChat()">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
              <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
          </button>
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

      // ─── Voice input ───────────────────────────────────────
      // Fix: use SpeechRecognition || webkitSpeechRecognition, fix boolean strings
      let recognition = null

      function startVoiceInput() {
        const micButton = document.getElementById("micButton")
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition
        if (!SpeechRecognition) {
          alert("Speech recognition is not supported on this browser.")
          return
        }

        // If already listening, stop
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
