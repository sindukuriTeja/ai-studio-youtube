const generateBtn = document.getElementById("generate-btn");
const statusCard = document.getElementById("status-card");
const progressFill = document.getElementById("progress-fill");
const statusMessage = document.getElementById("status-message");
const scriptCard = document.getElementById("script-card");
const filmTitle = document.getElementById("film-title");
const filmLogline = document.getElementById("film-logline");
const scenesList = document.getElementById("scenes-list");
const finalCard = document.getElementById("final-card");
const finalVideo = document.getElementById("final-video");
const downloadLink = document.getElementById("download-link");
const configWarning = document.getElementById("config-warning");
const ragHint = document.getElementById("rag-hint");
const inspirationCard = document.getElementById("inspiration-card");
const refinedLoglineEl = document.getElementById("refined-logline");
const similarList = document.getElementById("similar-list");

let pollTimer = null;

async function checkHealth() {
  try {
    const res = await fetch("/api/health");
    const data = await res.json();
    if (!data.ok) {
      configWarning.textContent =
        "Missing API configuration: " + data.problems.join(", ") + ". Add these to your .env file and restart the server.";
      configWarning.classList.remove("hidden");
      generateBtn.disabled = true;
    }
    if (data.rag_enabled) {
      ragHint.classList.remove("hidden");
    }
  } catch (e) {
    // server not reachable yet, ignore
  }
}

function badgeFor(status) {
  return `<span class="badge ${status}">${status}</span>`;
}

function renderScript(script) {
  if (!script) return;
  scriptCard.classList.remove("hidden");
  filmTitle.textContent = script.title;
  filmLogline.textContent = script.logline;
  scenesList.innerHTML = script.scenes
    .map(
      (s) => `
      <div class="scene-item">
        <div class="scene-info">
          <h4>${s.index + 1}. ${s.title}</h4>
          <p>${s.narration || ""}</p>
        </div>
        ${badgeFor(s.status)}
      </div>`
    )
    .join("");
}

function renderInspiration(job) {
  if (!job.refined_logline) return;
  inspirationCard.classList.remove("hidden");
  refinedLoglineEl.textContent = job.refined_logline;

  const similar = job.inspired_by || [];
  similarList.innerHTML = similar
    .map(
      (s) => `
      <div class="similar-item">
        <span class="badge genre">${s.genre}</span>
        <span class="similar-score">${Math.round((s.score <= 1 ? s.score * 100 : s.score))}% match</span>
        <p>${s.logline}</p>
      </div>`
    )
    .join("");
}

function renderStatus(job) {
  statusCard.classList.remove("hidden");
  progressFill.style.width = `${Math.round((job.progress || 0) * 100)}%`;
  statusMessage.textContent = job.message || job.status;
  renderInspiration(job);
  renderScript(job.script);

  if (job.status === "error") {
    statusMessage.textContent = `Error: ${job.error || "unknown error"}`;
    generateBtn.disabled = false;
    clearInterval(pollTimer);
  }

  if (job.status === "done" && job.final_video_path) {
    finalCard.classList.remove("hidden");
    const videoUrl = `/api/films/${job.job_id}/download`;
    finalVideo.src = videoUrl;
    downloadLink.href = videoUrl;
    generateBtn.disabled = false;
    clearInterval(pollTimer);
  }
}

async function pollJob(jobId) {
  const res = await fetch(`/api/films/${jobId}`);
  if (!res.ok) return;
  const job = await res.json();
  renderStatus(job);
}

async function generateFilm() {
  const idea = document.getElementById("idea").value.trim();
  if (!idea) {
    alert("Please enter a film idea.");
    return;
  }

  generateBtn.disabled = true;
  statusCard.classList.remove("hidden");
  inspirationCard.classList.add("hidden");
  scriptCard.classList.add("hidden");
  finalCard.classList.add("hidden");
  progressFill.style.width = "0%";
  statusMessage.textContent = "Starting...";

  const payload = {
    idea,
    num_scenes: parseInt(document.getElementById("num_scenes").value, 10),
    scene_duration: parseInt(document.getElementById("scene_duration").value, 10),
    aspect_ratio: document.getElementById("aspect_ratio").value,
    style: document.getElementById("style").value.trim() || null,
    genre: document.getElementById("genre").value || null,
    include_narration: document.getElementById("include_narration").checked,
  };

  try {
    const res = await fetch("/api/films", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Failed to start job");
    }

    const job = await res.json();
    renderStatus(job);

    pollTimer = setInterval(() => pollJob(job.job_id), 3000);
  } catch (e) {
    statusMessage.textContent = `Error: ${e.message}`;
    generateBtn.disabled = false;
  }
}

generateBtn.addEventListener("click", generateFilm);
checkHealth();
