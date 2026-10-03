// Pi Stop-Motion Workshop frontend
const $ = (id) => document.getElementById(id);
let projectId = null;
let frames = [];       // [{file, url}]
let playing = false, playTimer = null;

async function api(path, opts = {}) {
  const r = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...opts,
  });
  if (!r.ok) {
    const e = await r.json().catch(() => ({}));
    throw new Error(e.error || r.statusText);
  }
  return r.json();
}

async function refreshProjects(selectId) {
  const list = await api("/api/projects");
  const sel = $("projectSelect");
  sel.innerHTML = "";
  for (const p of list) {
    const o = document.createElement("option");
    o.value = p.id;
    o.textContent = `${p.name} (${p.frames})`;
    sel.appendChild(o);
  }
  if (selectId && [...sel.options].some((o) => o.value === selectId)) {
    sel.value = selectId;
  }
  projectId = sel.value || null;
  if (!projectId && list.length === 0) {
    // first run: create a starter project
    const created = await api("/api/projects", {
      method: "POST",
      body: JSON.stringify({ name: "My first animation" }),
    });
    await refreshProjects(created.id);
    return;
  }
  await refreshFrames();
}

async function refreshFrames() {
  if (!projectId) return;
  frames = await api(`/api/projects/${projectId}/frames`);
  $("frameCount").textContent = `(${frames.length})`;
  const tl = $("timeline");
  tl.innerHTML = "";
  frames.forEach((f, i) => {
    const d = document.createElement("div");
    d.className = "thumb";
    d.innerHTML = `<img src="${f.url}" alt="frame ${i + 1}">
      <button title="Delete frame">✕</button>`;
    d.querySelector("button").onclick = async (e) => {
      e.stopPropagation();
      if (!confirm(`Delete frame ${i + 1}?`)) return;
      await api(`/api/projects/${projectId}/frames/${f.file}`,
        { method: "DELETE" });
      await refreshFrames();
      await refreshProjects(projectId);
    };
    tl.appendChild(d);
  });
  tl.scrollLeft = tl.scrollWidth;
  updateOnion();
}

function updateOnion() {
  const on = $("onionToggle").checked && frames.length > 0;
  const img = $("onion");
  if (on) {
    img.src = frames[frames.length - 1].url + `?t=${Date.now()}`;
    img.style.opacity = $("onionOpacity").value / 100;
    img.style.display = "block";
  } else {
    img.style.display = "none";
  }
  $("onionVal").textContent = $("onionOpacity").value + "%";
}

async function capture() {
  if (!projectId) return;
  const btn = $("captureBtn");
  btn.disabled = true;
  try {
    // cache-bust the MJPEG so the captured pose is fresh
    await api(`/api/projects/${projectId}/capture`, { method: "POST" });
    $("captureFlash").classList.add("on");
    setTimeout(() => $("captureFlash").classList.remove("on"), 120);
    await refreshFrames();
    const sel = $("projectSelect");
    await refreshProjects(projectId); // update counts
    sel.value = projectId;
  } catch (e) {
    alert("Capture failed: " + e.message);
  } finally {
    btn.disabled = false;
  }
}

function stopPlayback() {
  playing = false;
  clearInterval(playTimer);
  $("playBtn").textContent = "▶ Play";
  $("playerWrap").hidden = true;
}

function togglePlay() {
  if (playing) { stopPlayback(); return; }
  if (!frames.length) { alert("Capture some frames first!"); return; }
  playing = true;
  $("playBtn").textContent = "⏸ Stop";
  $("playerWrap").hidden = false;
  const fps = Math.max(1, Math.min(60, +$("fps").value || 12));
  let i = 0;
  const tick = () => {
    $("player").src = frames[i % frames.length].url;
    i++;
  };
  tick();
  playTimer = setInterval(tick, 1000 / fps);
}

async function exportVideo() {
  if (!frames.length) { alert("Capture some frames first!"); return; }
  const fps = Math.max(1, Math.min(60, +$("fps").value || 12));
  $("exportBtn").disabled = true;
  $("exportBtn").textContent = "⏳ Exporting…";
  try {
    const r = await api(`/api/projects/${projectId}/export`, {
      method: "POST",
      body: JSON.stringify({ fps }),
    });
    $("exportLink").innerHTML =
      `Done — <a href="${r.video_url}" download>⬇ Download MP4</a>
       (${r.frames} frames @ ${r.fps}fps)`;
    $("playerWrap").hidden = false;
  } catch (e) {
    alert("Export failed: " + e.message);
  } finally {
    $("exportBtn").disabled = false;
    $("exportBtn").textContent = "🎞 Export MP4";
  }
}

// ---- wiring ----
$("captureBtn").onclick = capture;
$("playBtn").onclick = togglePlay;
$("exportBtn").onclick = exportVideo;
$("onionOpacity").oninput = updateOnion;
$("onionToggle").onchange = updateOnion;
$("projectSelect").onchange = (e) => {
  projectId = e.target.value;
  stopPlayback();
  refreshFrames();
};
$("newProjectBtn").onclick = async () => {
  const name = prompt("Project name:", "New animation");
  if (!name) return;
  const p = await api("/api/projects", {
    method: "POST", body: JSON.stringify({ name }),
  });
  await refreshProjects(p.id);
};
$("deleteProjectBtn").onclick = async () => {
  if (!projectId || !confirm("Delete this project and all its frames?")) return;
  await api(`/api/projects/${projectId}`, { method: "DELETE" });
  stopPlayback();
  await refreshProjects();
};
document.addEventListener("keydown", (e) => {
  if (e.code === "Space" && !/INPUT|SELECT|TEXTAREA/.test(
      document.activeElement.tagName)) {
    e.preventDefault();
    capture();
  }
});

refreshProjects();
