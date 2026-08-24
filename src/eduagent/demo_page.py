"""ĐỢT 3 #2 -- single-file Vanilla HTML/CSS/JS demo page for the Cloud Run
service, so a human opening the deployed URL in a browser sees a working
Student/Teacher UI instead of a bare push-subscriber 404. Kept as one
dependency-free string (no build step, no static file mount) -- matches
this project's "no new infra than necessary" discipline elsewhere.
"""

from __future__ import annotations

DEMO_PAGE_HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>eduagent -- Live Demo</title>
<style>
  :root {
    --bg: #f5f6f8; --panel: #ffffff; --text: #1a1d23; --muted: #5b6472;
    --accent: #3b6fd6; --accent-text: #ffffff; --border: #dde1e7;
    --danger: #b3261e; --ok: #1e7a34;
  }
  @media (prefers-color-scheme: dark) {
    :root { --bg: #14161a; --panel: #1e2127; --text: #eef0f3; --muted: #a2acba;
      --accent: #5b8def; --accent-text: #0c1116; --border: #333844; --danger: #ff6b60; --ok: #58d68d; }
  }
  * { box-sizing: border-box; }
  body { margin: 0; background: var(--bg); color: var(--text); font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; }
  header { padding: 1.25rem 1.5rem; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center; }
  header h1 { font-size: 1.1rem; margin: 0; }
  header .sub { color: var(--muted); font-size: 0.85rem; }
  main { max-width: 860px; margin: 0 auto; padding: 1.5rem; }
  .tabs { display: flex; gap: 0.5rem; margin-bottom: 1rem; }
  .tabs button { padding: 0.5rem 1rem; border-radius: 8px; border: 1px solid var(--border); background: var(--panel); color: var(--text); cursor: pointer; }
  .tabs button.active { background: var(--accent); color: var(--accent-text); border-color: var(--accent); }
  .panel { background: var(--panel); border: 1px solid var(--border); border-radius: 12px; padding: 1.25rem; }
  .panel + .panel { margin-top: 1rem; }
  label { display: block; font-size: 0.8rem; color: var(--muted); margin: 0.75rem 0 0.25rem; }
  input, textarea { width: 100%; padding: 0.55rem 0.7rem; border-radius: 8px; border: 1px solid var(--border); background: var(--bg); color: var(--text); font: inherit; }
  textarea { min-height: 120px; resize: vertical; }
  button.action { margin-top: 1rem; padding: 0.6rem 1.1rem; border-radius: 8px; border: none; background: var(--accent); color: var(--accent-text); font-weight: 600; cursor: pointer; }
  button.action:disabled { opacity: 0.5; cursor: not-allowed; }
  .turn { border-left: 3px solid var(--accent); padding: 0.5rem 0.9rem; margin-top: 1rem; background: var(--bg); border-radius: 0 8px 8px 0; }
  .turn .meta { color: var(--muted); font-size: 0.75rem; margin-bottom: 0.25rem; }
  .error { color: var(--danger); margin-top: 0.75rem; font-size: 0.85rem; }
  .badge { display: inline-block; padding: 0.15rem 0.5rem; border-radius: 999px; font-size: 0.72rem; background: var(--accent); color: var(--accent-text); }
  table { width: 100%; border-collapse: collapse; margin-top: 1rem; font-size: 0.85rem; }
  th, td { text-align: left; padding: 0.5rem 0.6rem; border-bottom: 1px solid var(--border); }
  th { color: var(--muted); font-weight: 600; }
  .hidden { display: none; }
  .ok-text { color: var(--ok); }
</style>
</head>
<body>
<header>
  <h1>eduagent</h1>
  <span class="sub">Socratic Debate Coach -- live demo</span>
</header>
<main>
  <div class="tabs">
    <button id="tab-student" class="active" onclick="showTab('student')">Student</button>
    <button id="tab-teacher" onclick="showTab('teacher')">Teacher</button>
  </div>

  <section id="panel-student" class="panel">
    <div id="student-form">
      <label for="student_id">Student ID</label>
      <input id="student_id" placeholder="stu_demo">
      <label for="name">Name</label>
      <input id="name" placeholder="An">
      <label for="class_id">Class ID</label>
      <input id="class_id" placeholder="c1">
      <label for="essay_text">Essay (type it, or upload a photo of handwriting below instead)</label>
      <textarea id="essay_text" placeholder="Paste or write your essay here..."></textarea>
      <label for="essay_image">Or upload a photo of a handwritten essay</label>
      <input id="essay_image" type="file" accept="image/*">
      <button class="action" id="start-btn" onclick="startDebate()">Start Debate</button>
      <div id="start-error" class="error hidden"></div>
    </div>
    <div id="debate-area" class="hidden">
      <div id="turns"></div>
      <div id="reply-area">
        <label for="student_reply">Your reply</label>
        <textarea id="student_reply"></textarea>
        <button class="action" id="reply-btn" onclick="sendReply()">Send Reply</button>
      </div>
      <div id="turn-error" class="error hidden"></div>
      <div id="complete-msg" class="hidden ok-text" style="margin-top:1rem;">Debate complete -- 3 turns finished.</div>
    </div>
  </section>

  <section id="panel-teacher" class="panel hidden">
    <label for="teacher_class_id">Class ID</label>
    <input id="teacher_class_id" placeholder="c1">
    <div style="display:flex; gap:0.5rem; margin-top:0.75rem;">
      <button class="action" onclick="loadAnalytics()">Load Digests</button>
      <button class="action" onclick="loadRoster()">Load Class Roster</button>
    </div>
    <div id="teacher-error" class="error hidden"></div>
    <div id="teacher-results"></div>
    <div id="roster-error" class="error hidden"></div>
    <div id="roster-results"></div>
  </section>
</main>

<script>
let sessionId = null;

function showTab(name) {
  document.getElementById('panel-student').classList.toggle('hidden', name !== 'student');
  document.getElementById('panel-teacher').classList.toggle('hidden', name !== 'teacher');
  document.getElementById('tab-student').classList.toggle('active', name === 'student');
  document.getElementById('tab-teacher').classList.toggle('active', name === 'teacher');
}

function renderTurn(turnNumber, personaLabel, questionText) {
  const div = document.createElement('div');
  div.className = 'turn';
  div.innerHTML = `<div class="meta">Turn ${turnNumber} <span class="badge">${personaLabel || ''}</span></div><div>${questionText}</div>`;
  document.getElementById('turns').appendChild(div);
}

function fileToBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result.split(',')[1]);
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

async function startDebate() {
  const btn = document.getElementById('start-btn');
  const errEl = document.getElementById('start-error');
  errEl.classList.add('hidden');
  btn.disabled = true;
  try {
    const imageFile = document.getElementById('essay_image').files[0];
    const studentId = document.getElementById('student_id').value || 'stu_demo';
    let resp;
    if (imageFile) {
      const imageBase64 = await fileToBase64(imageFile);
      resp = await fetch('/api/debate/start-with-image', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
          image_base64: imageBase64,
          image_mime_type: imageFile.type || 'image/jpeg',
          student_id: studentId,
          name: document.getElementById('name').value,
          class_id: document.getElementById('class_id').value,
        }),
      });
    } else {
      resp = await fetch('/api/debate/start', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
          essay_text: document.getElementById('essay_text').value,
          student_id: studentId,
          name: document.getElementById('name').value,
          class_id: document.getElementById('class_id').value,
        }),
      });
    }
    if (!resp.ok) throw new Error(`HTTP ${resp.status}: ${await resp.text()}`);
    const data = await resp.json();
    sessionId = data.session_id;
    document.getElementById('student-form').classList.add('hidden');
    document.getElementById('debate-area').classList.remove('hidden');
    if (data.ocr && (data.ocr.confidence === 'low' || data.ocr.confidence === 'unavailable')) {
      const warn = document.createElement('div');
      warn.className = 'error';
      warn.textContent = `Heads up: the photo was hard to read (confidence: ${data.ocr.confidence}) -- the debate below is based on a best-effort transcription.`;
      document.getElementById('turns').appendChild(warn);
    }
    renderTurn(1, data.persona_name, data.turn.question);
  } catch (e) {
    errEl.textContent = e.message;
    errEl.classList.remove('hidden');
  } finally {
    btn.disabled = false;
  }
}

async function sendReply() {
  const btn = document.getElementById('reply-btn');
  const errEl = document.getElementById('turn-error');
  errEl.classList.add('hidden');
  btn.disabled = true;
  try {
    const replyText = document.getElementById('student_reply').value;
    const resp = await fetch('/api/debate/turn', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({session_id: sessionId, student_reply: replyText}),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}: ${await resp.text()}`);
    const data = await resp.json();
    renderTurn(data.turn_number, data.turn.persona, data.turn.question);
    document.getElementById('student_reply').value = '';
    if (data.completed) {
      document.getElementById('reply-area').classList.add('hidden');
      document.getElementById('complete-msg').classList.remove('hidden');
    }
  } catch (e) {
    errEl.textContent = e.message;
    errEl.classList.remove('hidden');
  } finally {
    btn.disabled = false;
  }
}

async function loadAnalytics() {
  const errEl = document.getElementById('teacher-error');
  const resultsEl = document.getElementById('teacher-results');
  errEl.classList.add('hidden');
  resultsEl.innerHTML = '';
  const classId = document.getElementById('teacher_class_id').value || 'c1';
  try {
    const resp = await fetch(`/api/classes/${encodeURIComponent(classId)}/analytics`);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}: ${await resp.text()}`);
    const data = await resp.json();
    if (!data.digests || data.digests.length === 0) {
      resultsEl.innerHTML = '<p>No digests found for this class yet.</p>';
      return;
    }
    let rows = data.digests.map(d => `
      <tr>
        <td>${d.timestamp || ''}</td>
        <td>${(d.ranked_students || []).map(s => s.name || s.student_id).join(', ')}</td>
        <td>${(d.common_fallacies || []).join(', ')}</td>
      </tr>`).join('');
    resultsEl.innerHTML = `<table><thead><tr><th>Timestamp</th><th>Priority ranking</th><th>Common fallacies</th></tr></thead><tbody>${rows}</tbody></table>`;
  } catch (e) {
    errEl.textContent = e.message;
    errEl.classList.remove('hidden');
  }
}

async function loadRoster() {
  const errEl = document.getElementById('roster-error');
  const resultsEl = document.getElementById('roster-results');
  errEl.classList.add('hidden');
  resultsEl.innerHTML = '';
  const classId = document.getElementById('teacher_class_id').value || 'c1';
  try {
    const resp = await fetch(`/api/classes/${encodeURIComponent(classId)}/students`);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}: ${await resp.text()}`);
    const data = await resp.json();
    if (!data.students || data.students.length === 0) {
      resultsEl.innerHTML = '<p>No students found for this class yet.</p>';
      return;
    }
    let rows = data.students.map(s => `
      <tr>
        <td>${s.name || s.student_id}</td>
        <td>${s.score_trend || ''}</td>
        <td>${s.flags && s.flags.needs_attention ? 'Yes' : 'No'}</td>
        <td>${(s.flags && s.flags.last_updated) || ''}</td>
      </tr>`).join('');
    resultsEl.innerHTML = `<h3 style="margin-top:1.5rem;">Class Roster</h3><table><thead><tr><th>Student</th><th>Score trend</th><th>Needs attention</th><th>Last updated</th></tr></thead><tbody>${rows}</tbody></table>`;
  } catch (e) {
    errEl.textContent = e.message;
    errEl.classList.remove('hidden');
  }
}
</script>
</body>
</html>
"""
