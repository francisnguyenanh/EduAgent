"""ĐỢT 3 #2 / ĐỢT 4 -- single-file Vanilla HTML/CSS/JS demo page for the
Cloud Run service, so a human opening the deployed URL in a browser sees a
working Student/Teacher UI instead of a bare push-subscriber 404. Kept as
one dependency-free string (no build step, no static file mount) -- matches
this project's "no new infra than necessary" discipline elsewhere.

ĐỢT 4 adds a mock role-based login gate (see auth.py) in front of the same
Student/Teacher panels ĐỢT 3 already built, plus a Teacher "Priority" tab
(live Intervention Priority Index + Parent Update Note co-pilot) and a
Settings tab -- all against endpoints server.py exposes.
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
    --danger: #b3261e; --ok: #1e7a34; --warn: #b8860b;
  }
  @media (prefers-color-scheme: dark) {
    :root { --bg: #14161a; --panel: #1e2127; --text: #eef0f3; --muted: #a2acba;
      --accent: #5b8def; --accent-text: #0c1116; --border: #333844; --danger: #ff6b60; --ok: #58d68d; --warn: #e0b23d; }
  }
  * { box-sizing: border-box; }
  body { margin: 0; background: var(--bg); color: var(--text); font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; }
  header { padding: 1.25rem 1.5rem; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center; }
  header h1 { font-size: 1.1rem; margin: 0; }
  header .sub { color: var(--muted); font-size: 0.85rem; }
  header .who { font-size: 0.8rem; color: var(--muted); display: flex; align-items: center; gap: 0.6rem; }
  header .who button { background: none; border: 1px solid var(--border); color: var(--text); border-radius: 6px; padding: 0.25rem 0.6rem; cursor: pointer; }
  main { max-width: 900px; margin: 0 auto; padding: 1.5rem; }
  .tabs { display: flex; gap: 0.5rem; margin-bottom: 1rem; flex-wrap: wrap; }
  .tabs button { padding: 0.5rem 1rem; border-radius: 8px; border: 1px solid var(--border); background: var(--panel); color: var(--text); cursor: pointer; }
  .tabs button.active { background: var(--accent); color: var(--accent-text); border-color: var(--accent); }
  .panel { background: var(--panel); border: 1px solid var(--border); border-radius: 12px; padding: 1.25rem; }
  .panel + .panel { margin-top: 1rem; }
  label { display: block; font-size: 0.8rem; color: var(--muted); margin: 0.75rem 0 0.25rem; }
  input, textarea { width: 100%; padding: 0.55rem 0.7rem; border-radius: 8px; border: 1px solid var(--border); background: var(--bg); color: var(--text); font: inherit; }
  textarea { min-height: 120px; resize: vertical; }
  button.action { margin-top: 1rem; padding: 0.6rem 1.1rem; border-radius: 8px; border: none; background: var(--accent); color: var(--accent-text); font-weight: 600; cursor: pointer; }
  button.action:disabled { opacity: 0.5; cursor: not-allowed; }
  button.small { margin-top: 0; padding: 0.35rem 0.7rem; font-size: 0.78rem; border-radius: 6px; border: 1px solid var(--border); background: var(--bg); color: var(--text); cursor: pointer; }
  .turn { border-left: 3px solid var(--accent); padding: 0.5rem 0.9rem; margin-top: 1rem; background: var(--bg); border-radius: 0 8px 8px 0; }
  .turn .meta { color: var(--muted); font-size: 0.75rem; margin-bottom: 0.25rem; }
  .error { color: var(--danger); margin-top: 0.75rem; font-size: 0.85rem; }
  .badge { display: inline-block; padding: 0.15rem 0.5rem; border-radius: 999px; font-size: 0.72rem; background: var(--accent); color: var(--accent-text); }
  .badge.warn { background: var(--warn); color: #1a1d23; }
  table { width: 100%; border-collapse: collapse; margin-top: 1rem; font-size: 0.85rem; }
  th, td { text-align: left; padding: 0.5rem 0.6rem; border-bottom: 1px solid var(--border); vertical-align: top; }
  th { color: var(--muted); font-weight: 600; }
  .hidden { display: none; }
  .ok-text { color: var(--ok); }
  .role-pick { display: flex; gap: 1rem; margin-top: 1rem; }
  .role-pick button { flex: 1; padding: 1.5rem 1rem; font-size: 1rem; border-radius: 12px; border: 1px solid var(--border); background: var(--panel); cursor: pointer; color: var(--text); }
  .role-pick button:hover { border-color: var(--accent); }
  .note-box { margin-top: 0.5rem; padding: 0.7rem 0.9rem; background: var(--bg); border-radius: 8px; border: 1px solid var(--border); font-size: 0.85rem; }
  .settings-row { display: flex; align-items: center; gap: 0.6rem; margin-top: 0.75rem; }
  .settings-row label { margin: 0; }
  .hint { color: var(--muted); font-size: 0.75rem; margin-top: 0.25rem; }
  .bubble-row { display: flex; align-items: flex-start; gap: 0.6rem; margin-top: 1rem; }
  .bubble-row.student { flex-direction: row-reverse; }
  .avatar { flex: none; width: 2.1rem; height: 2.1rem; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 1.1rem; color: #fff; }
  .speech-bubble { max-width: 80%; border-radius: 14px; padding: 0.6rem 0.9rem; background: var(--bg); border: 1px solid var(--border); }
  .bubble-row.student .speech-bubble { background: var(--accent); color: var(--accent-text); border-color: var(--accent); }
  .speech-bubble .meta { font-weight: 600; font-size: 0.75rem; margin-bottom: 0.2rem; opacity: 0.85; }
  .radar-row { display: flex; align-items: center; gap: 0.6rem; margin-top: 0.5rem; }
  .radar-label { flex: none; width: 11rem; font-size: 0.8rem; color: var(--muted); }
  .radar-track { flex: 1; height: 0.6rem; background: var(--bg); border: 1px solid var(--border); border-radius: 999px; overflow: hidden; }
  .radar-fill { height: 100%; background: var(--accent); }
  .radar-value { flex: none; width: 2rem; text-align: right; font-size: 0.8rem; color: var(--muted); }
  .feedback-box { margin-top: 1rem; padding: 0.9rem 1rem; background: var(--bg); border-radius: 8px; border: 1px solid var(--border); }
</style>
</head>
<body>
<header>
  <div>
    <h1>eduagent</h1>
    <span class="sub">Socratic Debate Coach -- live demo</span>
  </div>
  <div class="who hidden" id="who-box">
    <span id="who-label"></span>
    <button onclick="logout()">Log out</button>
  </div>
</header>
<main>

  <section id="gate" class="panel">
    <div id="role-pick-step">
      <p>Who's signing in?</p>
      <div class="role-pick">
        <button onclick="pickRole('student')">Student Portal</button>
        <button onclick="pickRole('teacher')">Teacher Portal</button>
      </div>
    </div>
    <div id="login-step" class="hidden">
      <p id="login-heading"></p>
      <label for="login_user_id">ID (e.g. <span id="id-example">c1_stu01</span>)</label>
      <input id="login_user_id" placeholder="c1_stu01">
      <label for="login_password">Password</label>
      <input id="login_password" type="password" placeholder="demo password">
      <div class="hint">Demo build: mock login only, shared demo password -- not a real auth system.</div>
      <button class="action" id="login-btn" onclick="doLogin()">Sign in</button>
      <button class="small" style="margin-top:0.75rem;" onclick="backToRolePick()">Back</button>
      <div id="login-error" class="error hidden"></div>
    </div>
  </section>

  <section id="app" class="hidden">
    <div class="tabs" id="student-tabs">
      <button id="tab-student" class="active" onclick="showTab('student')">Submit &amp; Debate</button>
    </div>
    <div class="tabs hidden" id="teacher-tabs">
      <button id="tab-priority" class="active" onclick="showTab('priority')">Priority</button>
      <button id="tab-teacher" onclick="showTab('teacher')">Digests</button>
      <button id="tab-roster" onclick="showTab('roster')">Roster</button>
      <button id="tab-settings" onclick="showTab('settings')">Settings</button>
    </div>

    <section id="panel-student" class="panel">
      <div id="student-form">
        <div style="display:flex; gap:0.5rem; margin-bottom:0.5rem; flex-wrap:wrap; align-items:center;">
          <span style="font-size:0.75rem; color:var(--muted); font-weight:600;">Presets for Testing:</span>
          <button type="button" class="small" onclick="loadSampleEssay('climate')">📝 Sample: Electric Vehicles</button>
          <button type="button" class="small" onclick="loadSampleEssay('ai')">📝 Sample: AI in Education</button>
          <button type="button" class="small" onclick="clearEssayForm()">Clear</button>
        </div>
        <label for="essay_text">Essay (type it, or upload a photo, or paste a Google Doc link)</label>
        <textarea id="essay_text" placeholder="Paste or write your essay here..."></textarea>
        <label for="gdoc_url">Or Google Doc share link (Anyone with link can view)</label>
        <input id="gdoc_url" placeholder="https://docs.google.com/document/d/1A2B3C.../edit">
        <label for="essay_image">Or upload a photo of a handwritten essay</label>
        <input id="essay_image" type="file" accept="image/*">
        <button class="action" id="start-btn" onclick="startDebate()">Start Debate</button>
        <div id="start-error" class="error hidden"></div>
      </div>
      <div id="debate-area" class="hidden">
        <div id="turns"></div>
        <div id="reply-area">
          <label for="student_reply">Your reply</label>
          <textarea id="student_reply" placeholder="Defend your position against the persona's challenge..."></textarea>
          <div style="display:flex; align-items:center; gap:0.5rem; margin-top:0.75rem;">
            <button class="action" style="margin-top:0;" id="reply-btn" onclick="sendReply()">Send Reply</button>
            <button type="button" class="small" onclick="loadSampleReply()">💡 Fill Sample Argument</button>
          </div>
        </div>
        <div id="turn-error" class="error hidden"></div>
        <div id="complete-result" class="hidden">
          <p class="ok-text" style="margin-top:1rem;">Debate complete -- 3 turns finished.</p>
          <div id="complete-radar"></div>
          <div id="complete-feedback" class="feedback-box"></div>
        </div>
      </div>
    </section>

    <section id="panel-priority" class="panel hidden">
      <p class="hint">Live Intervention Priority Index -- deterministic ranking (see priority_engine.py), zero LLM. Highest priority first.</p>
      <button class="action" onclick="loadPriority()">Refresh Priority Ranking</button>
      <div id="priority-error" class="error hidden"></div>
      <div id="priority-results"></div>
    </section>

    <section id="panel-teacher" class="panel hidden">
      <button class="action" onclick="loadAnalytics()">Load Digests</button>
      <div id="teacher-error" class="error hidden"></div>
      <div id="teacher-results"></div>
    </section>

    <section id="panel-roster" class="panel hidden">
      <button class="action" onclick="loadRoster()">Load Class Roster</button>
      <div id="roster-error" class="error hidden"></div>
      <div id="roster-results"></div>
    </section>

    <section id="panel-settings" class="panel hidden">
      <p class="hint">Pedagogical settings for this class.</p>
      <div class="settings-row">
        <input type="checkbox" id="setting_show_radar">
        <label for="setting_show_radar" style="margin:0;">Show score radar to students</label>
      </div>
      <label for="setting_stuck_threshold">Stuck-streak threshold (essays without improvement)</label>
      <input id="setting_stuck_threshold" type="number" min="1">
      <label for="setting_digest_email">Digest notification email</label>
      <input id="setting_digest_email" placeholder="teacher@school.edu">
      <button class="action" onclick="saveSettings()">Save Settings</button>
      <button class="small" style="margin-left:0.5rem;" onclick="loadSettings()">Reload</button>
      <div id="settings-error" class="error hidden"></div>
      <div id="settings-ok" class="hidden ok-text" style="margin-top:0.75rem;">Saved.</div>
    </section>
  </section>
</main>

<script>
let sessionId = null;
let auth = null; // {role, class_id, user_id, display_name}

function pickRole(role) {
  auth = {role};
  document.getElementById('role-pick-step').classList.add('hidden');
  document.getElementById('login-step').classList.remove('hidden');
  document.getElementById('login-heading').textContent = role === 'student' ? 'Student sign-in' : 'Teacher sign-in';
  document.getElementById('id-example').textContent = role === 'student' ? 'c1_stu01' : 'c1_teacher';
}

function backToRolePick() {
  auth = null;
  document.getElementById('login-step').classList.add('hidden');
  document.getElementById('role-pick-step').classList.remove('hidden');
}

async function doLogin() {
  const btn = document.getElementById('login-btn');
  const errEl = document.getElementById('login-error');
  errEl.classList.add('hidden');
  btn.disabled = true;
  try {
    const resp = await fetch('/api/auth/login', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        role: auth.role,
        user_id: document.getElementById('login_user_id').value,
        password: document.getElementById('login_password').value,
      }),
    });
    if (!resp.ok) throw new Error((await resp.json()).detail || `HTTP ${resp.status}`);
    auth = await resp.json();
    enterApp();
  } catch (e) {
    errEl.textContent = e.message;
    errEl.classList.remove('hidden');
  } finally {
    btn.disabled = false;
  }
}

function logout() {
  auth = null;
  sessionId = null;
  document.getElementById('gate').classList.remove('hidden');
  document.getElementById('app').classList.add('hidden');
  document.getElementById('who-box').classList.add('hidden');
  document.getElementById('role-pick-step').classList.remove('hidden');
  document.getElementById('login-step').classList.add('hidden');
  document.getElementById('login_user_id').value = '';
  document.getElementById('login_password').value = '';
}

function enterApp() {
  document.getElementById('gate').classList.add('hidden');
  document.getElementById('app').classList.remove('hidden');
  document.getElementById('who-box').classList.remove('hidden');
  document.getElementById('who-label').textContent = `${auth.display_name} -- class ${auth.class_id} (${auth.role})`;
  const isTeacher = auth.role === 'teacher';
  document.getElementById('student-tabs').classList.toggle('hidden', isTeacher);
  document.getElementById('teacher-tabs').classList.toggle('hidden', !isTeacher);
  showTab(isTeacher ? 'priority' : 'student');
  if (isTeacher) loadPriority();
}

function showTab(name) {
  ['student', 'priority', 'teacher', 'roster', 'settings'].forEach(n => {
    document.getElementById('panel-' + n).classList.toggle('hidden', n !== name);
  });
  ['tab-student', 'tab-priority', 'tab-teacher', 'tab-roster', 'tab-settings'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.classList.toggle('active', id === 'tab-' + name);
  });
  if (name === 'settings') loadSettings();
}

// ĐỢT 5 #2: one avatar/color per Socratic persona so the 4 debate
// personalities read as distinct characters in the chat, not interchangeable
// grey boxes -- matches PERSONAS in skills/personas.py by persona_id.
const PERSONA_STYLE = {
  skeptic: {emoji: '🧐', color: '#1e3a8a', label: 'The Skeptic'},
  devils_advocate: {emoji: '😈', color: '#c2410c', label: "The Devil's Advocate"},
  nitpicker: {emoji: '🔍', color: '#7e22ce', label: 'The Nitpicker'},
  expander: {emoji: '🌌', color: '#047857', label: 'The Expander'},
};

function personaStyle(personaId) {
  return PERSONA_STYLE[personaId] || {emoji: '🤖', color: '#5b6472', label: personaId || 'Persona'};
}

function renderTurn(turnNumber, personaId, questionText) {
  const style = personaStyle(personaId);
  const row = document.createElement('div');
  row.className = 'bubble-row';
  row.innerHTML = `
    <div class="avatar" style="background:${style.color};">${style.emoji}</div>
    <div class="speech-bubble">
      <div class="meta">Turn ${turnNumber} -- ${style.label}</div>
      <div>${questionText}</div>
    </div>`;
  document.getElementById('turns').appendChild(row);
}

function renderStudentReply(replyText) {
  const row = document.createElement('div');
  row.className = 'bubble-row student';
  row.innerHTML = `
    <div class="avatar" style="background:var(--muted);">🗯️</div>
    <div class="speech-bubble"><div class="meta">You</div><div>${replyText}</div></div>`;
  document.getElementById('turns').appendChild(row);
}

function fileToBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result.split(',')[1]);
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

function loadSampleEssay(type) {
  if (type === 'climate') {
    document.getElementById('essay_text').value = "Electric vehicles are completely useless for saving the environment because manufacturing their batteries creates huge amounts of pollution, and electricity comes from burning coal anyway. Therefore, governments should immediately stop all subsidies for electric cars.";
    document.getElementById('gdoc_url').value = '';
    document.getElementById('essay_image').value = '';
  } else if (type === 'ai') {
    document.getElementById('essay_text').value = "Schools should completely ban all AI writing tools like ChatGPT because if students use AI, they will lose their ability to think critically and write on their own, ultimately leading to the total decline of human intelligence.";
    document.getElementById('gdoc_url').value = '';
    document.getElementById('essay_image').value = '';
  }
}

function clearEssayForm() {
  document.getElementById('essay_text').value = '';
  document.getElementById('gdoc_url').value = '';
  document.getElementById('essay_image').value = '';
}

function loadSampleReply() {
  document.getElementById('student_reply').value = "While battery production does create upfront emissions, peer-reviewed life-cycle analyses show that EVs generate 50% to 70% lower net carbon emissions over their full lifespan compared to traditional gasoline vehicles, especially as the electrical grid transitions to renewable energy.";
}

async function startDebate() {
  const btn = document.getElementById('start-btn');
  const errEl = document.getElementById('start-error');
  errEl.classList.add('hidden');
  btn.disabled = true;
  try {
    const imageFile = document.getElementById('essay_image').files[0];
    const gdocUrl = (document.getElementById('gdoc_url').value || '').trim();
    const studentId = auth.user_id;
    let resp;
    if (gdocUrl) {
      resp = await fetch('/api/debate/start-with-gdoc', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({gdoc_url: gdocUrl, student_id: studentId, name: auth.display_name, class_id: auth.class_id}),
      });
    } else if (imageFile) {
      const imageBase64 = await fileToBase64(imageFile);
      resp = await fetch('/api/debate/start-with-image', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
          image_base64: imageBase64,
          image_mime_type: imageFile.type || 'image/jpeg',
          student_id: studentId, name: auth.display_name, class_id: auth.class_id,
        }),
      });
    } else {
      resp = await fetch('/api/debate/start', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({essay_text: document.getElementById('essay_text').value, student_id: studentId, name: auth.display_name, class_id: auth.class_id}),
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
    renderTurn(1, data.persona_id, data.turn.question);
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
    renderStudentReply(replyText);
    renderTurn(data.turn_number, data.turn.persona, data.turn.question);
    document.getElementById('student_reply').value = '';
    if (data.completed) {
      document.getElementById('reply-area').classList.add('hidden');
      renderCompleteResult(data.result);
    }
  } catch (e) {
    errEl.textContent = e.message;
    errEl.classList.remove('hidden');
  } finally {
    btn.disabled = false;
  }
}

const AXIS_LABELS = {
  logical_coherence: 'Logical coherence',
  evidence_quality: 'Evidence quality',
  counterargument_handling: 'Counterargument handling',
  scope_awareness: 'Scope awareness',
};

function renderCompleteResult(result) {
  // ĐỢT 5 #1: respects the teacher's show_score_radar_to_students setting
  // (Settings tab) -- api.py already stripped `scores`/`rationale` out of
  // `result` server-side when that flag is off, so the client only ever
  // has to check for their presence, never re-derive the decision itself.
  const radarEl = document.getElementById('complete-radar');
  const feedbackEl = document.getElementById('complete-feedback');
  radarEl.innerHTML = '';
  if (result && result.scores) {
    radarEl.innerHTML = Object.entries(result.scores).map(([axis, value]) => `
      <div class="radar-row">
        <div class="radar-label">${AXIS_LABELS[axis] || axis}</div>
        <div class="radar-track"><div class="radar-fill" style="width:${Math.max(0, Math.min(10, value)) * 10}%;"></div></div>
        <div class="radar-value">${value}/10</div>
      </div>`).join('');
  }
  feedbackEl.textContent = (result && result.student_feedback) || 'Debate complete -- great effort working through all 3 turns!';
  document.getElementById('complete-result').classList.remove('hidden');
}

async function loadPriority() {
  const errEl = document.getElementById('priority-error');
  const resultsEl = document.getElementById('priority-results');
  errEl.classList.add('hidden');
  resultsEl.innerHTML = '';
  try {
    const resp = await fetch(`/api/classes/${encodeURIComponent(auth.class_id)}/priority`);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}: ${await resp.text()}`);
    const data = await resp.json();
    if (!data.ranking || data.ranking.length === 0) {
      resultsEl.innerHTML = '<p>No students found for this class yet.</p>';
      return;
    }
    let rows = data.ranking.map(r => `
      <tr>
        <td>${r.name || r.student_id}</td>
        <td>${r.priority}</td>
        <td>${r.reason.score_trend}${r.reason.stuck_streak_count ? ', stuck x' + r.reason.stuck_streak_count : ''}${r.reason.inactivity_days ? ', ' + r.reason.inactivity_days + 'd inactive' : ''}</td>
        <td><button class="small" onclick="copyParentNote('${r.student_id}', this)">Copy Parent Update Note</button>
            <div class="note-box hidden" id="note-${r.student_id}"></div></td>
      </tr>`).join('');
    resultsEl.innerHTML = `<table><thead><tr><th>Student</th><th>Priority</th><th>Why</th><th>Parent Co-Pilot</th></tr></thead><tbody>${rows}</tbody></table>`;
  } catch (e) {
    errEl.textContent = e.message;
    errEl.classList.remove('hidden');
  }
}

async function copyParentNote(studentId, btn) {
  const box = document.getElementById('note-' + studentId);
  btn.disabled = true;
  box.classList.remove('hidden');
  box.textContent = 'Drafting...';
  try {
    const resp = await fetch('/api/parent-note', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({class_id: auth.class_id, student_id: studentId}),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}: ${await resp.text()}`);
    const data = await resp.json();
    box.textContent = data.note;
    try { await navigator.clipboard.writeText(data.note); box.textContent += '  (copied to clipboard)'; } catch (_) { /* clipboard permission not granted -- note is still shown to copy by hand */ }
  } catch (e) {
    box.textContent = 'Error: ' + e.message;
  } finally {
    btn.disabled = false;
  }
}

async function loadAnalytics() {
  const errEl = document.getElementById('teacher-error');
  const resultsEl = document.getElementById('teacher-results');
  errEl.classList.add('hidden');
  resultsEl.innerHTML = '';
  try {
    const resp = await fetch(`/api/classes/${encodeURIComponent(auth.class_id)}/analytics`);
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

const TREND_COLORS = {improving: '#1e7a34', declining: '#b3261e', stagnant: '#b8860b', insufficient_data: '#5b6472'};

function sparklineSvg(essayHistory, trend) {
  // ĐỢT 4 storage/retrieval visual: a per-student avg_score-over-time
  // sparkline, drawn from essay_history (already returned in full by
  // list_students_by_class -- no new endpoint/query needed). Inline SVG,
  // no charting library, consistent with this project's zero-new-dependency
  // discipline (demo_page.py's own module docstring).
  const points = (essayHistory || []).map(e => e.avg_score).filter(v => typeof v === 'number');
  if (points.length < 2) return '<span class="hint">not enough essays yet</span>';
  const w = 140, h = 36, pad = 4;
  const maxV = 10, minV = 0; // rubric axes are fixed 0-10 (scorer.py) -- a fixed scale keeps sparklines comparable across students
  const stepX = (w - 2 * pad) / (points.length - 1);
  const coords = points.map((v, i) => {
    const x = pad + i * stepX;
    const y = pad + (h - 2 * pad) * (1 - (v - minV) / (maxV - minV));
    return [x, y];
  });
  const path = coords.map(([x, y]) => `${x.toFixed(1)},${y.toFixed(1)}`).join(' ');
  const color = TREND_COLORS[trend] || TREND_COLORS.insufficient_data;
  const lastPoint = coords[coords.length - 1];
  const titleText = points.map(v => v.toFixed(1)).join(' -> ');
  return `<svg width="${w}" height="${h}" viewBox="0 0 ${w} ${h}" role="img">
    <title>${titleText}</title>
    <polyline points="${path}" fill="none" stroke="${color}" stroke-width="2" stroke-linejoin="round" stroke-linecap="round" />
    <circle cx="${lastPoint[0].toFixed(1)}" cy="${lastPoint[1].toFixed(1)}" r="2.5" fill="${color}" />
  </svg>`;
}

async function loadRoster() {
  const errEl = document.getElementById('roster-error');
  const resultsEl = document.getElementById('roster-results');
  errEl.classList.add('hidden');
  resultsEl.innerHTML = '';
  try {
    const resp = await fetch(`/api/classes/${encodeURIComponent(auth.class_id)}/students`);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}: ${await resp.text()}`);
    const data = await resp.json();
    if (!data.students || data.students.length === 0) {
      resultsEl.innerHTML = '<p>No students found for this class yet.</p>';
      return;
    }
    let rows = data.students.map(s => `
      <tr>
        <td>${s.name || s.student_id}</td>
        <td>${sparklineSvg(s.essay_history, s.score_trend)}</td>
        <td>${s.score_trend || ''}</td>
        <td>${s.flags && s.flags.needs_attention ? 'Yes' : 'No'}</td>
        <td>${(s.flags && s.flags.last_updated) || ''}</td>
      </tr>`).join('');
    resultsEl.innerHTML = `<h3 style="margin-top:1.5rem;">Class Roster</h3><table><thead><tr><th>Student</th><th>Score trend chart</th><th>Trend</th><th>Needs attention</th><th>Last updated</th></tr></thead><tbody>${rows}</tbody></table>`;
  } catch (e) {
    errEl.textContent = e.message;
    errEl.classList.remove('hidden');
  }
}

async function loadSettings() {
  const errEl = document.getElementById('settings-error');
  errEl.classList.add('hidden');
  document.getElementById('settings-ok').classList.add('hidden');
  try {
    const resp = await fetch(`/api/classes/${encodeURIComponent(auth.class_id)}/settings`);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}: ${await resp.text()}`);
    const data = await resp.json();
    document.getElementById('setting_show_radar').checked = !!data.settings.show_score_radar_to_students;
    document.getElementById('setting_stuck_threshold').value = data.settings.stuck_streak_threshold;
    document.getElementById('setting_digest_email').value = data.settings.digest_notify_email || '';
  } catch (e) {
    errEl.textContent = e.message;
    errEl.classList.remove('hidden');
  }
}

async function saveSettings() {
  const errEl = document.getElementById('settings-error');
  errEl.classList.add('hidden');
  document.getElementById('settings-ok').classList.add('hidden');
  try {
    const resp = await fetch(`/api/classes/${encodeURIComponent(auth.class_id)}/settings`, {
      method: 'PUT',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        show_score_radar_to_students: document.getElementById('setting_show_radar').checked,
        stuck_streak_threshold: parseInt(document.getElementById('setting_stuck_threshold').value, 10),
        digest_notify_email: document.getElementById('setting_digest_email').value,
      }),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}: ${await resp.text()}`);
    document.getElementById('settings-ok').classList.remove('hidden');
  } catch (e) {
    errEl.textContent = e.message;
    errEl.classList.remove('hidden');
  }
}
</script>
</body>
</html>
"""
