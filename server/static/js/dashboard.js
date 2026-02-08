/* Team Monitor - Dashboard Client */
(function () {
  "use strict";

  // --- State ---
  let eventSource = null;
  let lastEventId = 0;
  let totalEvents = 0;
  let newEventCount = 0;
  let recentTimestamps = []; // timestamps of events in last 60s for rate calc
  let currentFilters = { category: "", agent: "", tool: "" };
  let feedScrolledToTop = true;
  const AGENT_COLORS = ["#58a6ff","#3fb950","#d29922","#f85149","#bc8cff","#79c0ff"];

  // --- DOM refs (set on DOMContentLoaded) ---
  let elStatusDot, elStatusText, elHeaderCount;
  let elAgentsRow, elEventFeed, elNewIndicator;
  let elFilterCategory, elFilterAgent, elFilterTool, elBtnClear;
  let elStatTotal, elStatRate, elStatMostActive, elCategoryBars;

  // --- Utility ---

  function formatTimestamp(iso) {
    if (!iso) return "";
    var d = new Date(iso);
    var diff = (Date.now() - d.getTime()) / 1000;
    if (diff < 5) return "now";
    if (diff < 60) return Math.floor(diff) + "s ago";
    if (diff < 3600) return Math.floor(diff / 60) + "m ago";
    if (diff < 86400) return Math.floor(diff / 3600) + "h ago";
    return d.toLocaleDateString() + " " + d.toLocaleTimeString();
  }

  function getCategoryColor(cat) {
    var map = {
      communication: "#1f6feb",
      task_management: "#238636",
      tool_use: "#9e6a03",
      lifecycle: "#484f58"
    };
    return map[cat] || "#484f58";
  }

  function getAgentColor(name) {
    if (!name) return AGENT_COLORS[0];
    var hash = 0;
    for (var i = 0; i < name.length; i++) {
      hash = name.charCodeAt(i) + ((hash << 5) - hash);
    }
    return AGENT_COLORS[Math.abs(hash) % AGENT_COLORS.length];
  }

  function truncateText(text, maxLen) {
    if (!text) return "";
    return text.length > maxLen ? text.slice(0, maxLen) + "..." : text;
  }

  function highlightJSON(jsonStr) {
    return jsonStr
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/("(?:\\.|[^"\\])*")\s*:/g, '<span class="json-key">$1</span>:')
      .replace(/:\s*("(?:\\.|[^"\\])*")/g, ': <span class="json-string">$1</span>')
      .replace(/:\s*(\d+\.?\d*)/g, ': <span class="json-number">$1</span>')
      .replace(/:\s*(true|false)/g, ': <span class="json-boolean">$1</span>')
      .replace(/:\s*(null)/g, ': <span class="json-null">$1</span>');
  }

  function trackEventTimestamp() {
    var now = Date.now();
    recentTimestamps.push(now);
    // Prune older than 60s
    var cutoff = now - 60000;
    while (recentTimestamps.length > 0 && recentTimestamps[0] < cutoff) {
      recentTimestamps.shift();
    }
  }

  function calcEventsPerMinute() {
    var now = Date.now();
    var cutoff = now - 60000;
    while (recentTimestamps.length > 0 && recentTimestamps[0] < cutoff) {
      recentTimestamps.shift();
    }
    return recentTimestamps.length;
  }

  // --- API ---

  function apiFetch(path) {
    return fetch(path).then(function (r) {
      if (!r.ok) throw new Error("HTTP " + r.status);
      return r.json();
    });
  }

  function fetchEvents() {
    var params = new URLSearchParams();
    if (currentFilters.category) params.set("category", currentFilters.category);
    if (currentFilters.agent) params.set("agent", currentFilters.agent);
    if (currentFilters.tool) params.set("tool", currentFilters.tool);
    params.set("per_page", "100");
    return apiFetch("/api/events?" + params.toString());
  }

  function fetchAgents() {
    return apiFetch("/api/agents");
  }

  function fetchStats() {
    return apiFetch("/api/stats");
  }

  // --- Rendering ---

  function renderAgentCards(agents) {
    if (!agents || agents.length === 0) {
      elAgentsRow.innerHTML = '<div class="agents-empty">No agents detected yet</div>';
      return;
    }
    elAgentsRow.innerHTML = "";
    agents.forEach(function (agent) {
      var card = document.createElement("div");
      card.className = "agent-card";
      card.style.borderLeftColor = getAgentColor(agent.agent_name || agent.name);
      card.innerHTML =
        '<div class="agent-name">' + escapeHTML(agent.agent_name || agent.name || "unknown") + "</div>" +
        '<div class="agent-team">' + escapeHTML(agent.team_name || "") + "</div>" +
        '<div class="agent-meta">' +
          '<span>' + formatTimestamp(agent.last_seen || agent.last_activity) + "</span>" +
          '<span class="agent-count">' + (agent.event_count || 0) + "</span>" +
        "</div>";
      elAgentsRow.appendChild(card);
    });
  }

  function escapeHTML(s) {
    var div = document.createElement("div");
    div.textContent = s;
    return div.innerHTML;
  }

  function createEventRow(ev) {
    var row = document.createElement("div");
    row.className = "event-row";
    row.dataset.eventId = ev.id || "";
    row.dataset.category = ev.category || ev.event_category || "";
    row.dataset.agent = ev.agent_name || "";
    row.dataset.tool = ev.tool_name || "";

    var cat = ev.category || ev.event_category || "lifecycle";
    var agentColor = getAgentColor(ev.agent_name);

    row.innerHTML =
      '<div class="event-row-header">' +
        '<span class="event-timestamp">' + formatTimestamp(ev.timestamp || ev.created_at) + "</span>" +
        '<span class="event-agent-badge" style="border-color:' + agentColor + ";color:" + agentColor + '">' +
          escapeHTML(ev.agent_name || "system") +
        "</span>" +
        '<span class="event-category-badge ' + escapeHTML(cat) + '">' + escapeHTML(cat) + "</span>" +
        '<span class="event-summary">' + escapeHTML(truncateText(ev.summary || ev.event_type || "", 120)) + "</span>" +
      "</div>" +
      '<div class="event-detail"><pre></pre></div>';

    row.addEventListener("click", function () {
      row.classList.toggle("expanded");
      if (row.classList.contains("expanded")) {
        var payload = ev.payload || ev.payload_json;
        var jsonStr;
        if (typeof payload === "string") {
          try { jsonStr = JSON.stringify(JSON.parse(payload), null, 2); }
          catch (e) { jsonStr = payload; }
        } else if (payload && typeof payload === "object") {
          jsonStr = JSON.stringify(payload, null, 2);
        } else {
          jsonStr = JSON.stringify(ev, null, 2);
        }
        row.querySelector("pre").innerHTML = highlightJSON(jsonStr);
      }
    });

    return row;
  }

  function renderEventFeed(events) {
    elEventFeed.innerHTML = "";
    if (!events || events.length === 0) {
      elEventFeed.innerHTML = '<div class="feed-empty">No events yet. Waiting for activity...</div>';
      return;
    }
    events.forEach(function (ev) {
      elEventFeed.appendChild(createEventRow(ev));
      if (ev.id && ev.id > lastEventId) lastEventId = ev.id;
    });
  }

  function addEventToFeed(ev) {
    // Remove empty state if present
    var empty = elEventFeed.querySelector(".feed-empty");
    if (empty) empty.remove();

    var row = createEventRow(ev);
    row.classList.add("new");
    elEventFeed.insertBefore(row, elEventFeed.firstChild);

    // Track for rate calc
    trackEventTimestamp();

    // Update total
    totalEvents++;
    elHeaderCount.textContent = totalEvents + " events";

    // Update rate display
    elStatRate.textContent = calcEventsPerMinute();

    if (ev.id && ev.id > lastEventId) lastEventId = ev.id;

    if (!feedScrolledToTop) {
      newEventCount++;
      elNewIndicator.textContent = newEventCount + " new event" + (newEventCount > 1 ? "s" : "") + " - click to scroll up";
      elNewIndicator.classList.add("visible");
    }

    // Remove animation class after it plays
    setTimeout(function () { row.classList.remove("new"); }, 350);
  }

  function matchesFilters(ev) {
    if (currentFilters.category && (ev.category || ev.event_category || "") !== currentFilters.category) return false;
    if (currentFilters.agent && (ev.agent_name || "") !== currentFilters.agent) return false;
    if (currentFilters.tool && (ev.tool_name || "") !== currentFilters.tool) return false;
    return true;
  }

  function renderStats(stats) {
    if (!stats) return;
    elStatTotal.textContent = stats.total_events || 0;
    totalEvents = stats.total_events || 0;
    elHeaderCount.textContent = totalEvents + " events";
    elStatRate.textContent = stats.events_last_minute || stats.events_per_minute || 0;

    var mostActive = stats.most_active_agent;
    if (mostActive && typeof mostActive === "object") {
      elStatMostActive.textContent = (mostActive.agent_name || "-") + " (" + (mostActive.event_count || 0) + ")";
    } else {
      elStatMostActive.textContent = mostActive || "-";
    }

    var byCat = stats.by_category || {};
    var maxCount = 1;
    Object.keys(byCat).forEach(function (k) {
      if (byCat[k] > maxCount) maxCount = byCat[k];
    });

    var categories = ["communication", "task_management", "tool_use", "lifecycle"];
    elCategoryBars.innerHTML = "";
    categories.forEach(function (cat) {
      var count = byCat[cat] || 0;
      var pct = maxCount > 0 ? Math.round((count / maxCount) * 100) : 0;
      var item = document.createElement("div");
      item.className = "category-bar-item";
      item.innerHTML =
        '<span class="category-bar-label">' + cat.replace("_", " ") + "</span>" +
        '<div class="category-bar-track"><div class="category-bar-fill ' + cat + '" style="width:' + pct + '%"></div></div>' +
        '<span class="category-bar-count">' + count + "</span>";
      elCategoryBars.appendChild(item);
    });
  }

  function populateFilterDropdowns(agents) {
    // Populate agent dropdown
    if (elFilterAgent.options.length <= 1 && agents && agents.length > 0) {
      agents.forEach(function (a) {
        var name = a.agent_name || a.name;
        if (name) {
          var opt = document.createElement("option");
          opt.value = name;
          opt.textContent = name;
          elFilterAgent.appendChild(opt);
        }
      });
    }
  }

  // --- SSE ---

  function connectSSE() {
    if (eventSource) {
      eventSource.close();
    }
    eventSource = new EventSource("/api/stream");

    eventSource.onopen = function () {
      elStatusDot.classList.add("connected");
      elStatusText.textContent = "Connected";
    };

    eventSource.onmessage = function (e) {
      if (!e.data || e.data.trim() === "") return;
      var ev;
      try { ev = JSON.parse(e.data); } catch (err) { return; }
      if (!ev || !ev.id) return;

      // Only add if matches filter
      if (matchesFilters(ev)) {
        addEventToFeed(ev);
      }

      // Refresh agents and stats periodically on new events
      fetchAgents().then(function (data) {
        renderAgentCards(data.agents || data);
        populateFilterDropdowns(data.agents || data);
      }).catch(function () {});

      fetchStats().then(function (data) {
        renderStats(data);
      }).catch(function () {});
    };

    eventSource.onerror = function () {
      elStatusDot.classList.remove("connected");
      elStatusText.textContent = "Disconnected";
      eventSource.close();
      // Reconnect after 3 seconds
      setTimeout(connectSSE, 3000);
    };
  }

  // --- Filter handlers ---

  function onFilterChange() {
    currentFilters.category = elFilterCategory.value;
    currentFilters.agent = elFilterAgent.value;
    currentFilters.tool = elFilterTool.value;
    fetchEvents().then(function (data) {
      renderEventFeed(data.events || []);
    }).catch(function () {});
  }

  function onClearFilters() {
    elFilterCategory.value = "";
    elFilterAgent.value = "";
    elFilterTool.value = "";
    currentFilters = { category: "", agent: "", tool: "" };
    fetchEvents().then(function (data) {
      renderEventFeed(data.events || []);
    }).catch(function () {});
  }

  // --- Init ---

  document.addEventListener("DOMContentLoaded", function () {
    // Cache DOM references
    elStatusDot = document.getElementById("status-dot");
    elStatusText = document.getElementById("status-text");
    elHeaderCount = document.getElementById("header-count");
    elAgentsRow = document.getElementById("agents-row");
    elEventFeed = document.getElementById("event-feed");
    elNewIndicator = document.getElementById("new-events-indicator");
    elFilterCategory = document.getElementById("filter-category");
    elFilterAgent = document.getElementById("filter-agent");
    elFilterTool = document.getElementById("filter-tool");
    elBtnClear = document.getElementById("btn-clear-filters");
    elStatTotal = document.getElementById("stat-total");
    elStatRate = document.getElementById("stat-rate");
    elStatMostActive = document.getElementById("stat-most-active");
    elCategoryBars = document.getElementById("category-bars");

    // Scroll detection for event feed
    elEventFeed.addEventListener("scroll", function () {
      feedScrolledToTop = elEventFeed.scrollTop < 10;
      if (feedScrolledToTop) {
        newEventCount = 0;
        elNewIndicator.classList.remove("visible");
      }
    });

    // New events indicator click
    elNewIndicator.addEventListener("click", function () {
      elEventFeed.scrollTop = 0;
      newEventCount = 0;
      elNewIndicator.classList.remove("visible");
    });

    // Filter listeners
    elFilterCategory.addEventListener("change", onFilterChange);
    elFilterAgent.addEventListener("change", onFilterChange);
    elFilterTool.addEventListener("change", onFilterChange);
    elBtnClear.addEventListener("click", onClearFilters);

    // Initial data load - fetch all in parallel
    Promise.all([
      fetchEvents().catch(function () { return { events: [] }; }),
      fetchAgents().catch(function () { return { agents: [] }; }),
      fetchStats().catch(function () { return {}; })
    ]).then(function (results) {
      var eventsData = results[0];
      var agentsData = results[1];
      var statsData = results[2];

      renderEventFeed(eventsData.events || []);
      renderAgentCards(agentsData.agents || agentsData || []);
      populateFilterDropdowns(agentsData.agents || agentsData || []);
      renderStats(statsData);
    });

    // Connect SSE
    connectSSE();
  });
})();
