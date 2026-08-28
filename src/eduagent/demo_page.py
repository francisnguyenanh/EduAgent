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
  input:not([type="checkbox"]), textarea { width: 100%; padding: 0.55rem 0.7rem; border-radius: 8px; border: 1px solid var(--border); background: var(--bg); color: var(--text); font: inherit; }
  input[type="checkbox"] { cursor: pointer; }
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
  .reflection-card { margin-top: 1.25rem; padding: 1.1rem; background: var(--panel); border: 2px solid var(--accent); border-radius: 12px; }
  .judge-bar { background: linear-gradient(90deg, #1e3a8a, #3b82f6); color: #fff; padding: 0.5rem 1rem; border-radius: 8px; margin-bottom: 1.25rem; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 0.5rem; font-size: 0.8rem; }
  .judge-bar-title { font-weight: 700; display: flex; align-items: center; gap: 0.4rem; }
  .judge-bar-btns { display: flex; gap: 0.4rem; flex-wrap: wrap; }
  .judge-btn { background: rgba(255, 255, 255, 0.2); border: 1px solid rgba(255, 255, 255, 0.4); color: #fff; border-radius: 6px; padding: 0.3rem 0.6rem; font-size: 0.75rem; cursor: pointer; transition: all 0.15s; }
  .judge-btn:hover { background: #fff; color: #1e3a8a; font-weight: 600; }
  .typing-bubble { display: flex; align-items: center; gap: 0.4rem; padding: 0.6rem 0.9rem; background: var(--bg); border: 1px solid var(--border); border-radius: 14px; width: fit-content; color: var(--muted); font-size: 0.82rem; font-style: italic; }
  .typing-dots { display: inline-flex; gap: 4px; align-items: center; margin-left: 0.3rem; }
  .typing-dot { width: 6px; height: 6px; border-radius: 50%; background: var(--accent); animation: typingBounce 1.4s infinite ease-in-out both; }
  .typing-dot:nth-child(1) { animation-delay: -0.32s; }
  .typing-dot:nth-child(2) { animation-delay: -0.16s; }
  @keyframes typingBounce { 0%, 80%, 100% { transform: scale(0.6); opacity: 0.35; } 40% { transform: scale(1.1); opacity: 1; } }

  @media print {
    body { background: #fff !important; color: #000 !important; }
    header, .judge-bar, .tabs, button, .hint, .who, #student-form, #debate-area, #panel-teacher, #panel-settings, #panel-student { display: none !important; }
    main { max-width: 100% !important; margin: 0 !important; padding: 0 !important; }
    .panel { display: none !important; }
    #panel-priority { display: block !important; border: none !important; box-shadow: none !important; padding: 0 !important; }
    table { width: 100% !important; border: 1px solid #ccc !important; font-size: 10pt !important; }
    th, td { border: 1px solid #ccc !important; padding: 6px !important; color: #000 !important; }
    .print-header { display: block !important; margin-bottom: 1.5rem; }
  }

  .print-header { display: none; }
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

  <!-- Judge 1-Click Showcase Bar (ĐỢT 7) -->
  <div class="judge-bar" id="judge-bar">
    <div class="judge-bar-title">✨ Judge 1-Click Showcase:</div>
    <div class="judge-bar-btns">
      <button class="judge-btn" onclick="presetScenario('stuck')">🎯 1. Stuck Streak (Binh)</button>
      <button class="judge-btn" onclick="presetScenario('ocr')">📷 2. Handwritten Essay (OCR)</button>
      <button class="judge-btn" onclick="presetScenario('gdoc')">🔗 3. Google Doc Ingestion</button>
      <button class="judge-btn" onclick="presetScenario('teacher')">👨‍🏫 4. Teacher Dashboard &amp; Note</button>
    </div>
  </div>

  <div class="print-header">
    <h2 style="margin:0 0 0.25rem 0;">Pedagogical Report &amp; Intervention Priority Matrix</h2>
    <p style="color:#666; font-size:9pt; margin:0 0 1rem 0;">EduAgent Automated Executive Briefing &bull; Class: c1 &bull; Generated: <span id="print-date"></span></p>
  </div>

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
      <label for="login_password">Passcode / Password</label>
      <input id="login_password" type="password" placeholder="eduagent2026">
      <div class="hint" id="login-hint">Demo build: Student passcode: <strong>eduagent2026</strong> | Teacher passcode: <strong>eduagent-teacher-2026</strong></div>
      <button class="action" id="login-btn" onclick="doLogin()">Sign in</button>
      <button class="small" style="margin-top:0.75rem;" onclick="backToRolePick()">Back</button>
      <div id="login-error" class="error hidden"></div>
    </div>
  </section>

  <section id="app" class="hidden">
    <div class="tabs hidden" id="student-tabs">
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
        <div style="display:flex; gap:0.5rem; align-items:center; flex-wrap:wrap;">
          <input id="gdoc_url" style="flex:1; min-width:260px;" placeholder="https://docs.google.com/document/d/1A2B3C.../edit" oninput="updateGDocPreviewBtn()">
          <button type="button" id="btn_extract_gdoc" class="small" style="display:none;" onclick="extractGDoc()">📄 View Essay</button>
          <a id="btn_open_gdoc" href="https://docs.google.com/document/d/11Zm7Y5xBd5hzvSXr5WcfS4QyozCg7kfZGfIT1Me4TBY/edit?usp=sharing" target="_blank" rel="noopener noreferrer" style="text-decoration:none; display:none; align-items:center; gap:0.3rem; padding:0.5rem 0.8rem; background:var(--panel); border:1px solid var(--border); border-radius:8px; color:var(--accent); font-weight:600; font-size:0.8rem;" title="Open in Google Docs">
            ↗
          </a>
        </div>
        <label for="essay_image">Or upload a photo of a handwritten essay</label>
        <input id="essay_image" type="file" accept="image/*" onchange="handleImagePicked(this)">
        
        <div id="ocr_preview_container" class="hidden" style="margin-top:0.6rem; padding:0.6rem; border:1px dashed var(--border); border-radius:8px; background:rgba(0,0,0,0.02);">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.4rem;">
            <span style="font-size:0.78rem; font-weight:600; color:var(--muted);" id="ocr_preview_label">📷 Handwritten Essay Preview:</span>
            <div style="display:flex; gap:0.3rem;">
              <button type="button" class="small" style="padding:0.2rem 0.5rem; font-size:0.72rem; color:var(--accent); border-color:var(--accent);" id="btn_extract_image" onclick="extractImage()">📄 View Essay</button>
              <button type="button" class="small" style="padding:0.2rem 0.5rem; font-size:0.72rem;" onclick="clearOcrPreview()">Remove image</button>
            </div>
          </div>
          <img id="ocr_preview_img" src="" alt="Handwritten Essay Preview" style="max-width:100%; max-height:260px; object-fit:contain; border-radius:6px; border:1px solid var(--border); display:block; margin:0 auto; background:#fff;">
          <div id="ocr_sample_note" class="hint" style="text-align:center; margin-top:0.3rem;">Real handwriting sample with cross-outs and natural paper angle.</div>
        </div>
        
        <!-- Socratic Persona is now set by the Teacher in Settings tab -->

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
          <p class="ok-text" style="margin-top:1rem; font-weight:600;">Debate complete -- 3 turns finished.</p>
          <div id="complete-radar"></div>
          <div id="complete-feedback" class="feedback-box"></div>
          
          <!-- Metacognitive Self-Correction Loop (ĐỢT 7) -->
          <div id="reflection-card" class="reflection-card">
            <h4 style="margin:0 0 0.5rem 0; color:var(--accent);">🧠 Metacognitive Self-Correction (Revised Thesis)</h4>
            <p style="font-size:0.82rem; color:var(--muted); margin:0 0 0.75rem 0;">
              After reflecting on the reasoning gaps and counter-arguments identified by the Socratic persona, please rewrite <strong>1 refined thesis sentence</strong> to address these weaknesses:
            </p>
            <textarea id="revised_claim_input" style="min-height:70px;" placeholder="e.g. While electric vehicles eliminate direct tailpipe emissions, their overall environmental impact depends on grid electricity generation and lifecycle battery recycling..."></textarea>
            <div style="margin-top:0.5rem; display:flex; align-items:center; gap:0.5rem; flex-wrap:wrap;">
              <button class="action" style="margin:0;" id="reflection-btn" onclick="submitReflection()">Submit Revised Claim</button>
              <span id="reflection-status" class="hint"></span>
            </div>
            <div id="reflection-feedback" class="hidden" style="margin-top:0.75rem; padding:0.6rem 0.8rem; background:rgba(34, 197, 94, 0.1); border-left:3px solid var(--ok); border-radius:4px; font-size:0.85rem;"></div>
          </div>
        </div>
      </div>
    </section>

    <section id="panel-priority" class="panel hidden">
      <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:0.5rem;">
        <p class="hint" style="margin:0;">Live Intervention Priority Index -- deterministic ranking (see priority_engine.py), zero LLM.</p>
        <div style="display:flex; gap:0.5rem;">
          <button class="small" onclick="loadPriority()">Refresh</button>
          <button class="small" onclick="printReport()">📄 Export Briefing (Print / PDF)</button>
        </div>
      </div>
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
      <p class="hint">Pedagogical and logging settings for this class.</p>
      <div class="settings-row">
        <input type="checkbox" id="setting_show_radar">
        <label for="setting_show_radar" style="margin:0;">Show cognitive score radar to students</label>
      </div>
      <label for="setting_stuck_threshold">Stuck-streak threshold (essays without improvement)</label>
      <input id="setting_stuck_threshold" type="number" min="1">
      
      <label for="setting_digest_email">Digest recipient &mdash; the <code>To:</code> address on the Gmail draft</label>
      <input id="setting_digest_email" placeholder="parent@example.com or principal@school.edu">
      <p class="hint" style="margin-top:0.35rem;">The agent <strong>composes a draft, it never sends</strong> (ADR-001). This address is who <em>you</em> will be sending to once you review it &mdash; a parent, the principal, a co-teacher. Nobody is emailed automatically; the digest itself is shown to you below the Analytics table.</p>

      <label for="setting_socratic_persona" style="font-weight:600; margin-top:0.75rem; display:block;">Socratic Coach Persona (Class-wide Enforcement)</label>
      <select id="setting_socratic_persona" style="width:100%; padding:0.55rem 0.7rem; border-radius:8px; border:1px solid var(--border); background:var(--bg); color:var(--text); font:inherit; font-size:0.9rem; margin-top:0.25rem;">
        <option value="auto">🎯 Auto-Detect Weakness (AI diagnoses reasoning flaws per student)</option>
        <option value="skeptic">🧐 The Skeptic (Probes evidence, data, citations)</option>
        <option value="devils_advocate">😈 The Devil's Advocate (Presents opposing counter-arguments)</option>
        <option value="nitpicker">🔬 The Nitpicker (Challenges assumptions & logical fallacies)</option>
        <option value="expander">🔭 The Expander (Tests edge cases, generalizations & scope)</option>
      </select>

      <label for="setting_sheet_id">Audit Log Google Sheet (Link or Spreadsheet ID)</label>
      <div style="display:flex; gap:0.5rem; align-items:center; flex-wrap:wrap;">
        <input id="setting_sheet_id" style="flex:1; min-width:280px; margin:0;" placeholder="https://docs.google.com/spreadsheets/d/1pUGTCIz.../edit or ID">
        <button class="small" type="button" id="btn-test-sheets" onclick="testSheetsConnection()">🧪 Test Sheet Connection</button>
      </div>
      <div id="sheets-test-status" class="hint hidden" style="margin-top:0.4rem;"></div>

      <div style="margin-top:1.25rem;">
        <button class="action" onclick="saveSettings()">Save Settings</button>
        <button class="small" style="margin-left:0.5rem;" onclick="loadSettings()">Reload</button>
      </div>
      <div id="settings-error" class="error hidden"></div>
      <div id="settings-ok" class="hidden ok-text" style="margin-top:0.75rem;">Settings saved successfully.</div>
    </section>

  </section>
</main>

<script>
let sessionId = null;
let auth = null; // {role, class_id, user_id, display_name}
let presetImageBase64 = null;

function pickRole(role) {
  auth = {role};
  document.getElementById('role-pick-step').classList.add('hidden');
  document.getElementById('login-step').classList.remove('hidden');
  document.getElementById('login-heading').textContent = role === 'student' ? 'Student sign-in' : 'Teacher sign-in';
  document.getElementById('id-example').textContent = role === 'student' ? 'c1_stu01' : 'c1_teacher';
  const idInput = document.getElementById('login_user_id');
  if (idInput) {
    idInput.value = '';
    idInput.placeholder = role === 'student' ? 'c1_stu01' : 'c1_teacher';
  }
  const passInput = document.getElementById('login_password');
  if (passInput) {
    passInput.value = '';
    passInput.placeholder = role === 'student' ? 'eduagent2026' : 'eduagent-teacher-2026';
  }
  const hintEl = document.getElementById('login-hint');
  if (hintEl) {
    hintEl.innerHTML = role === 'student'
      ? 'Demo build: Student passcode is <strong>eduagent2026</strong>.'
      : 'Demo build: Teacher passcode is <strong>eduagent-teacher-2026</strong> (ADR-025 separated).';
  }
  const errEl = document.getElementById('login-error');
  if (errEl) errEl.classList.add('hidden');
}

function backToRolePick() {
  auth = null;
  document.getElementById('login-step').classList.add('hidden');
  document.getElementById('role-pick-step').classList.remove('hidden');
  const errEl = document.getElementById('login-error');
  if (errEl) errEl.classList.add('hidden');
}

async function autoLogin(userId, role, displayName) {
  try {
    const autoPass = role === 'teacher' ? 'eduagent-teacher-2026' : 'eduagent2026';
    const resp = await fetch('/api/auth/login', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        role: role,
        user_id: userId,
        password: autoPass,
      }),
    });
    if (resp.ok) {
      auth = await resp.json();
      return true;
    }
  } catch (e) {
    console.error('Auto-login error:', e);
  }
  // ĐỢT 12 NHÓM 2: the debate endpoints now require a Bearer token (they used
  // to accept any caller-supplied student_id). A tokenless fallback identity
  // therefore cannot do anything except collect 401s -- so say so plainly
  // instead of leaving the page looking mysteriously broken.
  auth = {role: role, user_id: userId, class_id: userId.split('_')[0] || 'c1', display_name: displayName || userId, token: ''};
  alert('Could not sign in (the server may be unreachable or rate-limited). Debate actions need a valid session token, so please retry in a moment.');
  return false;
}

async function doLogin() {
  const btn = document.getElementById('login-btn');
  const errEl = document.getElementById('login-error');
  errEl.classList.add('hidden');
  btn.disabled = true;
  try {
    const isTeacher = auth && auth.role === 'teacher';
    const defaultId = isTeacher ? 'c1_teacher' : 'c1_stu01';
    const defaultPass = isTeacher ? 'eduagent-teacher-2026' : 'eduagent2026';
    const enteredId = (document.getElementById('login_user_id').value || '').trim() || defaultId;
    const enteredPass = (document.getElementById('login_password').value || '').trim() || defaultPass;
    const resp = await fetch('/api/auth/login', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        role: auth.role,
        user_id: enteredId,
        password: enteredPass,
      }),
    });
    if (!resp.ok) {
      let errDetail = `HTTP ${resp.status}`;
      try {
        const errJson = await resp.json();
        if (errJson.detail) errDetail = errJson.detail;
      } catch (_) {}
      throw new Error(errDetail);
    }
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
  document.getElementById('student-tabs').classList.add('hidden');
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

function esc(str) {
  if (str === null || str === undefined) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function authHeaders(extra = {}) {
  const h = {'Content-Type': 'application/json', ...extra};
  if (auth && auth.token) {
    h['Authorization'] = 'Bearer ' + auth.token;
  }
  return h;
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

  const avatar = document.createElement('div');
  avatar.className = 'avatar';
  avatar.style.background = style.color;
  avatar.textContent = style.emoji;

  const bubble = document.createElement('div');
  bubble.className = 'speech-bubble';

  const meta = document.createElement('div');
  meta.className = 'meta';
  meta.textContent = `Turn ${turnNumber} -- ${style.label}`;

  const text = document.createElement('div');
  text.textContent = questionText;

  bubble.appendChild(meta);
  bubble.appendChild(text);
  row.appendChild(avatar);
  row.appendChild(bubble);
  document.getElementById('turns').appendChild(row);
}

function renderStudentReply(replyText) {
  const row = document.createElement('div');
  row.className = 'bubble-row student';

  const avatar = document.createElement('div');
  avatar.className = 'avatar';
  avatar.style.background = 'var(--muted)';
  avatar.textContent = '🗯️';

  const bubble = document.createElement('div');
  bubble.className = 'speech-bubble';

  const meta = document.createElement('div');
  meta.className = 'meta';
  meta.textContent = 'You';

  const text = document.createElement('div');
  text.textContent = replyText;

  bubble.appendChild(meta);
  bubble.appendChild(text);
  row.appendChild(avatar);
  row.appendChild(bubble);
  document.getElementById('turns').appendChild(row);
}

function showTypingIndicator(personaName = 'Socratic Coach') {
  removeTypingIndicator();
  const row = document.createElement('div');
  row.className = 'bubble-row';
  row.id = 'active-typing-indicator';

  const avatar = document.createElement('div');
  avatar.className = 'avatar';
  avatar.style.background = 'var(--accent)';
  avatar.textContent = '🤔';

  const bubble = document.createElement('div');
  bubble.className = 'typing-bubble';
  bubble.innerHTML = `<span>${esc(personaName)} is evaluating your argument</span><span class="typing-dots"><span class="typing-dot"></span><span class="typing-dot"></span><span class="typing-dot"></span></span>`;

  row.appendChild(avatar);
  row.appendChild(bubble);
  document.getElementById('turns').appendChild(row);
  row.scrollIntoView({behavior: 'smooth', block: 'end'});
}

function removeTypingIndicator() {
  const el = document.getElementById('active-typing-indicator');
  if (el) el.remove();
}

function fileToBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const b64 = reader.result.split(',')[1];
      resolve(b64);
    };
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

function updateGDocPreviewBtn() {
  const val = (document.getElementById('gdoc_url').value || '').trim();
  const btn = document.getElementById('btn_open_gdoc');
  const extractBtn = document.getElementById('btn_extract_gdoc');
  if (btn && extractBtn) {
    if (val.startsWith('http')) {
      btn.href = val;
      btn.style.display = 'inline-flex';
      extractBtn.style.display = 'inline-flex';
    } else {
      btn.style.display = 'none';
      extractBtn.style.display = 'none';
    }
  }
}

async function handleImagePicked(input) {
  if (input.files && input.files[0]) {
    presetImageBase64 = null;
    const file = input.files[0];
    const b64 = await fileToBase64(file);
    document.getElementById('ocr_preview_img').src = 'data:' + (file.type || 'image/jpeg') + ';base64,' + b64;
    document.getElementById('ocr_preview_label').textContent = '📷 Uploaded Photo Preview: ' + file.name;
    document.getElementById('ocr_preview_container').classList.remove('hidden');
    document.getElementById('essay_text').value = '';
    document.getElementById('gdoc_url').value = '';
    updateGDocPreviewBtn();
  }
}

function clearOcrPreview() {
  presetImageBase64 = null;
  const imgInput = document.getElementById('essay_image');
  if (imgInput) imgInput.value = '';
  const previewImg = document.getElementById('ocr_preview_img');
  if (previewImg) previewImg.src = '';
  const container = document.getElementById('ocr_preview_container');
  if (container) container.classList.add('hidden');
}

function loadSampleEssay(type) {
  clearOcrPreview();
  if (type === 'climate') {
    document.getElementById('essay_text').value = "Electric vehicles are completely useless for saving the environment because manufacturing their batteries creates huge amounts of pollution, and electricity comes from burning coal anyway. Therefore, governments should immediately stop all subsidies for electric cars.";
    document.getElementById('gdoc_url').value = '';
    document.getElementById('essay_image').value = '';
  } else if (type === 'ai') {
    document.getElementById('essay_text').value = "Schools should completely ban all AI writing tools like ChatGPT because if students use AI, they will lose their ability to think critically and write on their own, ultimately leading to the total decline of human intelligence.";
    document.getElementById('gdoc_url').value = '';
    document.getElementById('essay_image').value = '';
  }
  updateGDocPreviewBtn();
}

function clearEssayForm() {
  document.getElementById('essay_text').value = '';
  document.getElementById('gdoc_url').value = '';
  document.getElementById('essay_image').value = '';
  clearOcrPreview();
  updateGDocPreviewBtn();
}

async function extractGDoc() {
  const gdocUrl = (document.getElementById('gdoc_url').value || '').trim();
  if (!gdocUrl) return;
  const btn = document.getElementById('btn_extract_gdoc');
  const originalText = btn.textContent;
  btn.textContent = '⏳ Extracting...';
  btn.disabled = true;
  const errEl = document.getElementById('start-error');
  errEl.classList.add('hidden');
  try {
    const resp = await fetch('/api/debate/extract-gdoc', {
      method: 'POST',
      headers: authHeaders(),
      // Identity is REQUIRED: the route runs _verify_student_auth() on it, exactly
      // like /start-with-gdoc. Sending only gdoc_url returns 422 Unprocessable Entity.
      body: JSON.stringify({gdoc_url: gdocUrl, student_id: auth.user_id, name: auth.display_name, class_id: auth.class_id}),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}: ${await resp.text()}`);
    const data = await resp.json();
    document.getElementById('essay_text').value = data.text;
    document.getElementById('gdoc_url').value = '';
    updateGDocPreviewBtn();
  } catch (e) {
    errEl.textContent = e.message;
    errEl.classList.remove('hidden');
  } finally {
    btn.textContent = originalText;
    btn.disabled = false;
  }
}

async function extractImage() {
  const imageFile = document.getElementById('essay_image').files[0];
  if (!imageFile && !presetImageBase64) return;
  const btn = document.getElementById('btn_extract_image');
  const originalText = btn.textContent;
  btn.textContent = '⏳ Extracting OCR...';
  btn.disabled = true;
  const errEl = document.getElementById('start-error');
  errEl.classList.add('hidden');
  try {
    const imageBase64 = imageFile ? await fileToBase64(imageFile) : presetImageBase64;
    const mimeType = imageFile ? (imageFile.type || 'image/jpeg') : 'image/jpeg';
    const resp = await fetch('/api/debate/extract-image', {
      method: 'POST',
      headers: authHeaders(),
      // Identity is REQUIRED here too -- see the note in extractGDoc().
      body: JSON.stringify({
        image_base64: imageBase64,
        image_mime_type: mimeType,
        student_id: auth.user_id, name: auth.display_name, class_id: auth.class_id,
      }),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}: ${await resp.text()}`);
    const data = await resp.json();
    document.getElementById('essay_text').value = data.text;
    // Must cover 'unavailable' and `degraded` too, not just 'low': on a Vertex
    // outage transcribe_essay_image() returns EMPTY text with
    // confidence='unavailable' (ADR-008: never fabricate a transcription). Warning
    // only on 'low' left the student staring at an empty box with no explanation.
    if (data.ocr && (data.ocr.degraded || data.ocr.confidence === 'unavailable')) {
      errEl.textContent = `We could not read that photo right now -- the transcription service is temporarily unavailable. Try again shortly, or type the essay in yourself.`;
      errEl.classList.remove('hidden');
    } else if (data.ocr && data.ocr.confidence === 'low') {
      errEl.textContent = `Heads up: the photo was hard to read (confidence: low). Please review and fix any transcription errors.`;
      errEl.classList.remove('hidden');
    }
    clearOcrPreview();
  } catch (e) {
    errEl.textContent = e.message;
    errEl.classList.remove('hidden');
  } finally {
    btn.textContent = originalText;
    btn.disabled = false;
  }
}

function loadSampleReply() {
  document.getElementById('student_reply').value = "While battery production does create upfront emissions, peer-reviewed life-cycle analyses show that EVs generate 50% to 70% lower net carbon emissions over their full lifespan compared to traditional gasoline vehicles, especially as the electrical grid transitions to renewable energy.";
}

async function startDebate() {
  const btn = document.getElementById('start-btn');
  const errEl = document.getElementById('start-error');
  errEl.classList.add('hidden');
  btn.disabled = true;
  const originalText = btn.textContent;
  btn.textContent = '⏳ Analyzing essay & matching persona...';
  try {
    const imageFile = document.getElementById('essay_image').files[0];
    const gdocUrl = (document.getElementById('gdoc_url').value || '').trim();
    const studentId = auth.user_id;
    let resp;
    if (gdocUrl) {
      resp = await fetch('/api/debate/start-with-gdoc', {
        method: 'POST',
        headers: authHeaders(),
        body: JSON.stringify({gdoc_url: gdocUrl, student_id: studentId, name: auth.display_name, class_id: auth.class_id}),
      });
    } else if (imageFile || presetImageBase64) {
      const imageBase64 = imageFile ? await fileToBase64(imageFile) : presetImageBase64;
      const mimeType = imageFile ? (imageFile.type || 'image/jpeg') : 'image/jpeg';
      resp = await fetch('/api/debate/start-with-image', {
        method: 'POST',
        headers: authHeaders(),
        body: JSON.stringify({
          image_base64: imageBase64,
          image_mime_type: mimeType,
          student_id: studentId, name: auth.display_name, class_id: auth.class_id,
        }),
      });
    } else {
      resp = await fetch('/api/debate/start', {
        method: 'POST',
        headers: authHeaders(),
        body: JSON.stringify({
          essay_text: document.getElementById('essay_text').value,
          student_id: studentId,
          name: auth.display_name,
          class_id: auth.class_id,
        }),
      });
    }

    if (!resp.ok) throw new Error(`HTTP ${resp.status}: ${await resp.text()}`);
    const data = await resp.json();
    sessionId = data.session_id;
    document.getElementById('student-form').classList.add('hidden');
    document.getElementById('debate-area').classList.remove('hidden');
    const turnsEl = document.getElementById('turns');
    turnsEl.innerHTML = '';

    const fallacyText = (data.summary && data.summary.fallacies_draft && data.summary.fallacies_draft[0]) || 'Argument structure analysis';
    const routingBadge = document.createElement('div');
    routingBadge.style.cssText = 'margin-bottom:1rem; padding:0.6rem 0.85rem; background:rgba(37,99,235,0.08); border-left:3px solid var(--accent); border-radius:6px; font-size:0.83rem; color:var(--text);';
    routingBadge.innerHTML = `<strong>🤖 Autonomous Agent Routing:</strong> Diagnosed flaw: <em>"${esc(fallacyText)}"</em> ➔ Socratic Coach: <strong>${esc(data.persona_name || data.persona_id)}</strong>`;
    turnsEl.appendChild(routingBadge);

    if (data.ocr && (data.ocr.confidence === 'low' || data.ocr.confidence === 'unavailable')) {
      const warn = document.createElement('div');
      warn.className = 'error';
      warn.textContent = `Heads up: the photo was hard to read (confidence: ${data.ocr.confidence}) -- the debate below is based on a best-effort transcription.`;
      turnsEl.appendChild(warn);
    }
    renderTurn(1, data.persona_id, data.turn.question);

  } catch (e) {
    errEl.textContent = e.message;
    errEl.classList.remove('hidden');
  } finally {
    btn.disabled = false;
    btn.textContent = originalText;
  }
}

async function sendReply() {
  const btn = document.getElementById('reply-btn');
  const errEl = document.getElementById('turn-error');
  errEl.classList.add('hidden');
  const replyInput = document.getElementById('student_reply');
  const replyText = (replyInput.value || '').trim();
  if (!replyText) return;

  btn.disabled = true;
  const originalText = btn.textContent;
  btn.textContent = '⏳ Submitting argument...';

  // 1. Optimistic UI: Render student reply immediately
  renderStudentReply(replyText);
  replyInput.value = '';

  // 2. Show Animated Socratic Persona Typing Indicator
  showTypingIndicator();

  try {
    const resp = await fetch('/api/debate/turn', {
      method: 'POST',
      headers: authHeaders(),
      body: JSON.stringify({session_id: sessionId, student_reply: replyText}),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}: ${await resp.text()}`);
    const data = await resp.json();

    // 3. Remove typing indicator and render next Socratic question
    removeTypingIndicator();

    if (data.turn && data.turn.question) {
      renderTurn(data.turn_number, data.turn.persona, data.turn.question);
    }
    if (data.completed) {
      document.getElementById('reply-area').classList.add('hidden');
      renderCompleteResult(data.result);
    }
  } catch (e) {
    removeTypingIndicator();
    errEl.textContent = e.message;
    errEl.classList.remove('hidden');
    replyInput.value = replyText;
  } finally {
    btn.disabled = false;
    btn.textContent = originalText;
  }
}

const AXIS_LABELS = {
  logical_coherence: 'Logical coherence',
  evidence_quality: 'Evidence quality',
  counterargument_handling: 'Counterargument handling',
  scope_awareness: 'Scope awareness',
};

function createRadarChartSvg(scores) {
  if (!scores) return '';
  const size = 260, center = size / 2, radius = 80;
  const axes = [
    {key: 'logical_coherence', label: 'Logical Coherence'},
    {key: 'evidence_quality', label: 'Evidence Quality'},
    {key: 'scope_awareness', label: 'Scope Awareness'},
    {key: 'counterargument_handling', label: 'Counterargument Handling'},
  ];
  const angles = [-Math.PI / 2, 0, Math.PI / 2, Math.PI];

  // Concentric polygon grids
  let gridPolys = [2, 4, 6, 8, 10].map(level => {
    const r = radius * (level / 10);
    const pts = angles.map(a => `${(center + r * Math.cos(a)).toFixed(1)},${(center + r * Math.sin(a)).toFixed(1)}`).join(' ');
    return `<polygon points="${pts}" fill="none" stroke="var(--border)" stroke-width="1" stroke-dasharray="${level < 10 ? '2,2' : 'none'}" />`;
  }).join('');

  // Axis lines
  let axisLines = angles.map(a => {
    const x = (center + radius * Math.cos(a)).toFixed(1);
    const y = (center + radius * Math.sin(a)).toFixed(1);
    return `<line x1="${center}" y1="${center}" x2="${x}" y2="${y}" stroke="var(--border)" stroke-width="1" />`;
  }).join('');

  // Data coords
  const dataCoords = axes.map((axis, i) => {
    const val = typeof scores[axis.key] === 'number' ? scores[axis.key] : 5;
    const r = radius * (Math.max(0, Math.min(10, val)) / 10);
    const a = angles[i];
    return [center + r * Math.cos(a), center + r * Math.sin(a)];
  });
  const dataPoints = dataCoords.map(c => `${c[0].toFixed(1)},${c[1].toFixed(1)}`).join(' ');

  const dots = dataCoords.map(([x, y]) =>
    `<circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="4.5" fill="var(--accent)" stroke="#fff" stroke-width="1.5" />`
  ).join('');

  const labelOffsets = [
    {x: center, y: center - radius - 10, align: 'middle'},
    {x: center + radius + 8, y: center + 4, align: 'start'},
    {x: center, y: center + radius + 16, align: 'middle'},
    {x: center - radius - 8, y: center + 4, align: 'end'},
  ];
  const labels = axes.map((axis, i) => {
    const val = typeof scores[axis.key] === 'number' ? scores[axis.key] : '';
    const off = labelOffsets[i];
    return `<text x="${off.x}" y="${off.y}" text-anchor="${off.align}" fill="var(--text)" font-size="10" font-weight="600">${esc(axis.label)}: <tspan fill="var(--accent)">${val}/10</tspan></text>`;
  }).join('');

  return `
    <div style="width:100%; display:flex; justify-content:center; align-items:center; margin:0.75rem 0;">
      <svg viewBox="0 0 ${size} ${size}" style="width:100%; max-width:${size}px; height:auto; overflow:visible;">
        ${gridPolys}
        ${axisLines}
        <polygon points="${dataPoints}" fill="var(--accent)" fill-opacity="0.25" stroke="var(--accent)" stroke-width="2.5" />
        ${dots}
        ${labels}
      </svg>
    </div>
  `;
}

function renderCompleteResult(result) {
  // ĐỢT 5 #1: respects the teacher's show_score_radar_to_students setting
  // (Settings tab) -- api.py already stripped `scores`/`rationale` out of
  // `result` server-side when that flag is off, so the client only ever
  // has to check for their presence, never re-derive the decision itself.
  const radarEl = document.getElementById('complete-radar');
  const feedbackEl = document.getElementById('complete-feedback');
  radarEl.innerHTML = '';
  if (result && result.scores) {
    let html = createRadarChartSvg(result.scores);
    html += Object.entries(result.scores).map(([axis, value]) => `
      <div class="radar-row">
        <div class="radar-label">${esc(AXIS_LABELS[axis] || axis)}</div>
        <div class="radar-track"><div class="radar-fill" style="width:${Math.max(0, Math.min(10, value)) * 10}%;"></div></div>
        <div class="radar-value">${esc(value)}/10</div>
      </div>`).join('');
    radarEl.innerHTML = html;
  }
  feedbackEl.textContent = (result && result.student_feedback) || 'Debate complete -- great effort working through all 3 turns!';
  document.getElementById('complete-result').classList.remove('hidden');
}


async function submitReflection() {
  const inputEl = document.getElementById('revised_claim_input');
  const statusEl = document.getElementById('reflection-status');
  const feedbackEl = document.getElementById('reflection-feedback');
  const btn = document.getElementById('reflection-btn');
  const text = (inputEl.value || '').trim();
  if (!text) {
    statusEl.textContent = 'Please enter your revised thesis claim.';
    return;
  }
  btn.disabled = true;
  statusEl.textContent = 'Evaluating cognitive revision...';
  feedbackEl.classList.add('hidden');
  try {
    // ĐỢT 15 #2: session_id only. The student_id, class_id, original essay and
    // the fallacy being revised all come off the server's session record now --
    // this client used to supply them, which let anyone POST a reflection with
    // no debate behind it and collect the growth bonus.
    const resp = await fetch('/api/debate/reflect', {
      method: 'POST',
      headers: authHeaders(),
      body: JSON.stringify({
        session_id: sessionId,
        revised_claim: text,
      }),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}: ${await resp.text()}`);
    const data = await resp.json();
    // ĐỢT 16 #1: a degraded (unevaluated) submission must not look like a real
    // breakthrough. Before this, a Vertex AI outage rendered the identical
    // green "Cognitive Breakthrough Achieved!" panel, so nobody watching the
    // screen -- including during a demo recording -- could tell the difference.
    if (data.degraded) {
      feedbackEl.innerHTML = `
        <div style="font-weight:600; color:var(--warn); margin-bottom:0.25rem;">
          ⏳ Not evaluated yet
          <span class="badge" style="margin-left:0.4rem;">evaluator unavailable</span>
        </div>
        <div style="margin-bottom:0.75rem;">${esc(data.feedback)}</div>
      `;
      feedbackEl.classList.remove('hidden');
      statusEl.textContent = 'Recorded, but not scored — you can submit again.';
      btn.disabled = false;
      btn.textContent = 'Try Again';
      return;
    }
    feedbackEl.innerHTML = `
      <div style="font-weight:600; color:var(--ok); margin-bottom:0.25rem;">
        🌟 ${data.resolved ? 'Cognitive Breakthrough Achieved!' : 'Growth Effort Acknowledged!'} 
        <span class="badge" style="margin-left:0.4rem; background:var(--ok); color:#fff;">+${esc(data.growth_bonus)} Growth Bonus</span>
      </div>
      <div style="margin-bottom:0.75rem;">${esc(data.feedback)}</div>
      <button class="action" style="margin:0; font-size:0.82rem;" onclick="resetForNewEssay()">🔄 Return to Submit Another Essay</button>
    `;
    feedbackEl.classList.remove('hidden');
    statusEl.textContent = 'Saved to student learning profile.';
    btn.disabled = true;
    btn.textContent = 'Submitted';
  } catch (e) {
    statusEl.textContent = 'Error: ' + e.message;
    btn.disabled = false;
  }
}

function resetForNewEssay() {
  sessionId = null;
  document.getElementById('turns').innerHTML = '';
  document.getElementById('complete-radar').innerHTML = '';
  document.getElementById('complete-feedback').textContent = '';
  document.getElementById('reflection-feedback').innerHTML = '';
  document.getElementById('reflection-feedback').classList.add('hidden');
  document.getElementById('revised_claim_input').value = '';
  document.getElementById('reflection-status').textContent = '';
  document.getElementById('student_reply').value = '';
  document.getElementById('complete-result').classList.add('hidden');
  document.getElementById('reply-area').classList.remove('hidden');
  document.getElementById('debate-area').classList.add('hidden');
  document.getElementById('student-form').classList.remove('hidden');
  
  const refBtn = document.getElementById('reflection-btn');
  if (refBtn) {
    refBtn.disabled = false;
    refBtn.textContent = 'Submit Revised Claim';
  }
  
  clearEssayForm();
  window.scrollTo({top: 0, behavior: 'smooth'});
}


function printReport() {
  const dateEl = document.getElementById('print-date');
  if (dateEl) dateEl.textContent = new Date().toLocaleString();
  window.print();
}


async function presetScenario(scenario) {
  if (scenario === 'stuck') {
    await autoLogin('c1_stu02', 'student', 'Bob (Stuck Streak)');
    enterApp();
    showTab('student');
    clearEssayForm();
    document.getElementById('essay_text').value = 'Electric vehicles completely eliminate environmental pollution because they have zero tailpipe emissions. Therefore, if everyone switches to electric cars immediately, global climate change will be entirely solved.';
  } else if (scenario === 'ocr') {
    await autoLogin('c1_stu01', 'student', 'Alice');
    enterApp();
    showTab('student');
    clearEssayForm();
    try {
      const resp = await fetch('/api/demo/sample-ocr-image');
      if (resp.ok) {
        const data = await resp.json();
        presetImageBase64 = data.image_base64;
        document.getElementById('ocr_preview_img').src = 'data:' + data.mime_type + ';base64,' + data.image_base64;
        document.getElementById('ocr_preview_label').textContent = '📷 Sample Image Loaded: ' + data.filename;
        document.getElementById('ocr_preview_container').classList.remove('hidden');
      }
    } catch (e) {
      console.error('Failed to load sample OCR image:', e);
    }
  } else if (scenario === 'gdoc') {
    await autoLogin('c1_stu01', 'student', 'Alice');
    enterApp();
    showTab('student');
    clearEssayForm();
    const gdocLink = 'https://docs.google.com/document/d/11Zm7Y5xBd5hzvSXr5WcfS4QyozCg7kfZGfIT1Me4TBY/edit?usp=sharing';
    document.getElementById('gdoc_url').value = gdocLink;
    updateGDocPreviewBtn();
  } else if (scenario === 'teacher') {
    pickRole('teacher');
    document.getElementById('login_user_id').value = 'c1_teacher';
    document.getElementById('login_password').value = '';
    document.getElementById('login_password').focus();
  }
}


async function loadPriority() {
  const errEl = document.getElementById('priority-error');
  const resultsEl = document.getElementById('priority-results');
  errEl.classList.add('hidden');
  resultsEl.innerHTML = '';
  try {
    const resp = await fetch(`/api/classes/${encodeURIComponent(auth.class_id)}/priority`, {
      headers: authHeaders(),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}: ${await resp.text()}`);
    const data = await resp.json();
    if (!data.ranking || data.ranking.length === 0) {
      resultsEl.innerHTML = '<p>No students found for this class yet.</p>';
      return;
    }
    let rows = data.ranking.map(r => `
      <tr>
        <td>${esc(r.name || r.student_id)}</td>
        <td>${esc(r.priority)}</td>
        <td>${esc(r.reason.score_trend)}${r.reason.stuck_streak_count ? ', stuck x' + esc(r.reason.stuck_streak_count) : ''}${r.reason.inactivity_days ? ', ' + esc(r.reason.inactivity_days) + 'd inactive' : ''}</td>
        <td><button class="small btn-parent-note" data-student-id="${esc(r.student_id)}">Copy Parent Update Note</button>
            <div class="note-box hidden" id="note-${esc(r.student_id)}"></div></td>
      </tr>`).join('');
    resultsEl.innerHTML = `<table><thead><tr><th>Student</th><th>Priority</th><th>Why</th><th>Parent Co-Pilot</th></tr></thead><tbody>${rows}</tbody></table>`;
  } catch (e) {
    errEl.textContent = e.message;
    errEl.classList.remove('hidden');
  }
}

document.addEventListener('DOMContentLoaded', () => {
  const priorityEl = document.getElementById('priority-results');
  if (priorityEl) {
    priorityEl.addEventListener('click', (e) => {
      const btn = e.target.closest('.btn-parent-note');
      if (btn) {
        const studentId = btn.getAttribute('data-student-id');
        if (studentId) copyParentNote(studentId, btn);
      }
    });
  }
});

async function copyParentNote(studentId, btn) {
  const box = document.getElementById('note-' + studentId);
  btn.disabled = true;
  if (box) {
    box.classList.remove('hidden');
    box.textContent = 'Drafting...';
  }
  try {
    const resp = await fetch('/api/parent-note', {
      method: 'POST',
      headers: authHeaders(),
      body: JSON.stringify({class_id: auth.class_id, student_id: studentId}),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}: ${await resp.text()}`);
    const data = await resp.json();
    if (box) {
      box.textContent = data.note;
      try { await navigator.clipboard.writeText(data.note); box.textContent += '  (copied to clipboard)'; } catch (_) { /* clipboard permission not granted */ }
    }
  } catch (e) {
    if (box) box.textContent = 'Error: ' + e.message;
  } finally {
    btn.disabled = false;
  }
}

function formatShortTimestamp(tsString) {
  if (!tsString) return '';
  try {
    const d = new Date(tsString);
    if (isNaN(d.getTime())) return tsString;
    const yyyy = d.getFullYear();
    const mm = String(d.getMonth() + 1).padStart(2, '0');
    const dd = String(d.getDate()).padStart(2, '0');
    const HH = String(d.getHours()).padStart(2, '0');
    const MM = String(d.getMinutes()).padStart(2, '0');
    return `${yyyy}-${mm}-${dd} ${HH}:${MM}`;
  } catch (e) {
    return tsString;
  }
}

async function loadAnalytics() {
  const errEl = document.getElementById('teacher-error');
  const resultsEl = document.getElementById('teacher-results');
  errEl.classList.add('hidden');
  resultsEl.innerHTML = '';
  try {
    const resp = await fetch(`/api/classes/${encodeURIComponent(auth.class_id)}/analytics`, {
      headers: authHeaders(),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}: ${await resp.text()}`);
    const data = await resp.json();
    if (!data.digests || data.digests.length === 0) {
      resultsEl.innerHTML = '<p>No digests found for this class yet.</p>';
      return;
    }
    let rows = data.digests.map(d => {
      const miniLessonText = d.digest_text?.mini_lesson_suggestion || d.digest_text?.actionable_lesson_plan?.title || 'None';
      return `
      <tr>
        <td>${esc(formatShortTimestamp(d.timestamp))}</td>
        <td>${esc((d.ranked_students || []).map(s => s.name || s.student_id).join(', '))}</td>
        <td>${esc((d.common_fallacies || []).join(', '))}</td>
        <td><span style="font-size:12px;color:var(--accent);font-weight:bold;">${esc(miniLessonText)}</span></td>
      </tr>`;
    }).join('');
    resultsEl.innerHTML = `<table><thead><tr><th>Timestamp</th><th>Priority ranking</th><th>Common fallacies</th><th>Suggested Mini-Lesson</th></tr></thead><tbody>${rows}</tbody></table>`
      + digestDraftPreview(data.digests[0]);
  } catch (e) {
    errEl.textContent = e.message;
    errEl.classList.remove('hidden');
  }
}

// ĐỢT 26 #1.2-#1.4 -- the Gmail draft lives in the SYSTEM account's Drafts
// folder, so before this a judge (or a teacher on a different address) had no
// way to see what the agent had actually composed. `digest_html` is the exact
// body the draft carries, rendered server-side and HTML-escaped at the source
// (class_aggregator._h), so there is no second renderer to drift and no
// unescaped LLM text reaching this origin.
function digestDraftPreview(latest) {
  if (!latest) return '';
  const draftId = latest.gmail_draft_id;
  // Gmail's web UI addresses drafts by the HEX MESSAGE id, not the API draft
  // id -- verified against the live mailbox in Wave 26 (draft id
  // "r328879860172231529" vs message id "1a04055b6640d946"). Digests written
  // before this field existed fall back to opening the Drafts folder, which
  // still gets the teacher there.
  const composeId = latest.gmail_draft_message_id;
  const badge = draftId
    ? '<span style="background:#dcfce7;color:#14532d;padding:3px 10px;border-radius:10px;font-size:12px;font-weight:600;">Draft created &#10003; &mdash; awaiting human Send (ADR-001)</span>'
    : '<span style="background:#e5e7eb;color:#374151;padding:3px 10px;border-radius:10px;font-size:12px;font-weight:600;">No draft for this digest &mdash; no recipient configured</span>';
  const link = draftId
    ? `<a href="https://mail.google.com/mail/u/0/#drafts${composeId ? '?compose=' + encodeURIComponent(composeId) : ''}" target="_blank" rel="noopener noreferrer" class="small" style="text-decoration:none;">${composeId ? 'Open the draft in Gmail &rarr;' : 'Open Gmail Drafts &rarr;'}</a>`
    : '';
  const body = latest.digest_html
    ? `<div style="border:1px solid var(--border);border-radius:8px;padding:1rem;background:#fff;color:#111827;overflow-x:auto;">${latest.digest_html}</div>`
    : '<p class="hint">Preview unavailable for this digest.</p>';
  return `<section style="margin-top:1.5rem;">
    <h3 style="margin-bottom:0.35rem;">Latest teacher digest &mdash; exactly what the Gmail draft contains</h3>
    <div style="display:flex;gap:0.6rem;align-items:center;flex-wrap:wrap;margin-bottom:0.6rem;">${badge}${link}</div>
    ${body}
    <p class="hint" style="margin-top:0.5rem;">The agent stops here on purpose. It composes; a human reviews and presses Send.</p>
  </section>`;
}

const TREND_COLORS = {improving: '#1e7a34', declining: '#b3261e', stagnant: '#b8860b', insufficient_data: '#5b6472'};

function sparklineSvg(essayHistory, trend) {
  const points = (essayHistory || []).map(e => e.avg_score).filter(v => typeof v === 'number');
  if (points.length < 2) return '<span class="hint">not enough essays yet</span>';
  const w = 140, h = 36, pad = 4;
  const maxV = 10, minV = 0;
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
    <title>${esc(titleText)}</title>
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
    const resp = await fetch(`/api/classes/${encodeURIComponent(auth.class_id)}/students`, {
      headers: authHeaders(),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}: ${await resp.text()}`);
    const data = await resp.json();
    if (!data.students || data.students.length === 0) {
      resultsEl.innerHTML = '<p>No students found for this class yet.</p>';
      return;
    }
    let rows = data.students.map(s => `
      <tr>
        <td>${esc(s.name || s.student_id)}</td>
        <td>${sparklineSvg(s.essay_history, s.score_trend)}</td>
        <td>${esc(s.score_trend || '')}</td>
        <td>${s.flags && s.flags.needs_attention ? 'Yes' : 'No'}</td>
        <td>${esc(formatShortTimestamp(s.flags && s.flags.last_updated))}</td>
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
  document.getElementById('sheets-test-status').classList.add('hidden');
  try {
    const resp = await fetch(`/api/classes/${encodeURIComponent(auth.class_id)}/settings`, {
      headers: authHeaders(),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}: ${await resp.text()}`);
    const data = await resp.json();
    document.getElementById('setting_show_radar').checked = !!data.settings.show_score_radar_to_students;
    document.getElementById('setting_stuck_threshold').value = data.settings.stuck_streak_threshold;
    document.getElementById('setting_digest_email').value = data.settings.digest_notify_email || '';
    document.getElementById('setting_sheet_id').value = data.settings.audit_spreadsheet_id || '';
    document.getElementById('setting_socratic_persona').value = data.settings.socratic_persona || 'auto';
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
      headers: authHeaders(),
      body: JSON.stringify({
        show_score_radar_to_students: document.getElementById('setting_show_radar').checked,
        stuck_streak_threshold: parseInt(document.getElementById('setting_stuck_threshold').value, 10),
        digest_notify_email: document.getElementById('setting_digest_email').value.trim(),
        audit_spreadsheet_id: document.getElementById('setting_sheet_id').value.trim(),
        socratic_persona: document.getElementById('setting_socratic_persona').value,
      }),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}: ${await resp.text()}`);
    document.getElementById('settings-ok').classList.remove('hidden');
  } catch (e) {
    errEl.textContent = e.message;
    errEl.classList.remove('hidden');
  }
}

async function testSheetsConnection() {
  const btn = document.getElementById('btn-test-sheets');
  const statusEl = document.getElementById('sheets-test-status');
  const sheetInput = document.getElementById('setting_sheet_id').value.trim();
  btn.disabled = true;
  statusEl.textContent = '⏳ Testing connection to Google Sheets...';
  statusEl.classList.remove('hidden', 'error', 'ok-text');
  try {
    const resp = await fetch(`/api/classes/${encodeURIComponent(auth.class_id)}/test-sheets`, {
      method: 'POST',
      headers: authHeaders(),
      body: JSON.stringify({spreadsheet_id: sheetInput || undefined}),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}: ${await resp.text()}`);
    const data = await resp.json();
    statusEl.textContent = `✅ Successfully wrote test row to sheet (${data.spreadsheet_id}) at ${formatShortTimestamp(data.timestamp)}!`;
    statusEl.classList.add('ok-text');
  } catch (e) {
    statusEl.textContent = `❌ Connection failed: ${e.message}`;
    statusEl.classList.add('error');
  } finally {
    btn.disabled = false;
  }
}

</script>
</body>
</html>
"""
