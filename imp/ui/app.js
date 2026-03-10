const statusUrl = "/api/status";
const updatedEl = document.getElementById("updated");
const refreshBtn = document.getElementById("refresh");
const procScore = document.getElementById("proc-score");
const procStatus = document.getElementById("proc-status");
const autoStatus = document.getElementById("auto-status");
const spotlightList = document.getElementById("spotlight");
const riskList = document.getElementById("risks");
const leadersList = document.getElementById("leaders");
const nextAction = document.getElementById("next-action");
const autonomySummary = document.getElementById("autonomy-summary");
const groupsTable = document.getElementById("groups-table");
const openLogs = document.getElementById("open-logs");
const toggleMode = document.getElementById("toggle-mode");

const state = {
  focusMode: false,
};

const fmt = (value, fallback = "--") => (value === undefined || value === null ? fallback : value);

function renderList(target, items, emptyLabel) {
  target.innerHTML = "";
  if (!items || items.length === 0) {
    const li = document.createElement("li");
    li.textContent = emptyLabel;
    target.appendChild(li);
    return;
  }
  items.forEach((item) => {
    const li = document.createElement("li");
    li.textContent = item;
    target.appendChild(li);
  });
}

function renderGroups(groups) {
  groupsTable.innerHTML = "";
  const header = document.createElement("div");
  header.className = "row header";
  header.innerHTML = "<span>Group</span><span>Health</span><span>Status</span><span>Backlog</span>";
  groupsTable.appendChild(header);

  Object.entries(groups || {}).forEach(([name, metrics]) => {
    const row = document.createElement("div");
    row.className = "row";
    row.innerHTML = `
      <strong>${name}</strong>
      <span>${fmt(metrics.health_score)}</span>
      <span>${fmt(metrics.health_status)}</span>
      <span>${fmt(metrics.average_backlog)}</span>
    `;
    groupsTable.appendChild(row);
  });
}

function renderAutonomy(last) {
  if (!last) {
    autonomySummary.textContent = "No autonomy cycles recorded yet.";
    autoStatus.textContent = "--";
    return;
  }
  const status = fmt(last.status, "unknown");
  autoStatus.textContent = status;
  const summary = last.summary || {};
  const goals = summary.goal_updates?.count;
  const actions = summary.success_plan?.actions;
  const tests = last.tests?.success;
  const parts = [];
  if (goals !== undefined) parts.push(`Goals updated: ${goals}`);
  if (actions !== undefined) parts.push(`Actions: ${actions}`);
  if (tests !== undefined) parts.push(`Tests: ${tests ? "passed" : "failed"}`);
  autonomySummary.textContent = parts.length ? parts.join(" · ") : "Autonomy cycle recorded.";
}

async function refresh() {
  updatedEl.textContent = "Updating...";
  try {
    const response = await fetch(statusUrl);
    const data = await response.json();
    const processing = data.processing?.snapshot || {};
    const overall = processing.overall_health || {};
    procScore.textContent = fmt(overall.score);
    procStatus.textContent = fmt(overall.status, "unknown");

    renderList(spotlightList, processing.spotlight || [], "No spotlight groups yet.");
    renderList(riskList, processing.risk_groups || [], "No risks flagged.");
    renderList(leadersList, processing.leaders || [], "No leaders yet.");

    const action = (processing.action_plan || [])[0];
    if (action) {
      nextAction.textContent = `[${(action.priority || "info").toUpperCase()}] ${action.group}: ${action.summary}`;
    } else {
      nextAction.textContent = "No action recommendations.";
    }

    renderGroups(processing.groups || {});
    renderAutonomy(data.autonomy?.last);

    updatedEl.textContent = `Updated ${new Date().toLocaleTimeString()}`;
  } catch (err) {
    updatedEl.textContent = "Update failed";
    nextAction.textContent = "Unable to load data.";
  }
}

refreshBtn.addEventListener("click", refresh);
toggleMode.addEventListener("click", () => {
  state.focusMode = !state.focusMode;
  document.body.classList.toggle("focus", state.focusMode);
  toggleMode.textContent = state.focusMode ? "Focus Mode On" : "Focus Mode";
});

openLogs.addEventListener("click", (event) => {
  event.preventDefault();
  alert("Logs live in the imp/logs directory.");
});

refresh();
setInterval(refresh, 10000);
