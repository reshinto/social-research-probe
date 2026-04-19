"""Static CSS and JavaScript assets for the HTML report.

CSS_STYLES: inline stylesheet for the report page.
TTS_SCRIPT: inline JavaScript that wires up Web Speech API playback controls.
"""

from __future__ import annotations

CSS_STYLES = """
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
:root {
  --bg: #ffffff; --fg: #1a1a2e; --accent: #4f6ef7;
  --surface: #f5f5f8; --border: #e0e0e8; --radius: 6px;
  --font: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
}
@media (prefers-color-scheme: dark) {
  :root { --bg: #0d0f1a; --fg: #e8e8f0; --surface: #1a1c2e; --border: #2a2d45; }
}
body { background: var(--bg); color: var(--fg); font: 16px/1.65 var(--font); }

/* TTS toolbar */
#tts-bar {
  background: var(--surface); border-bottom: 1px solid var(--border);
  padding: 0.55rem 1.5rem; display: flex; align-items: center; gap: 0.65rem;
  font-size: 0.875rem; position: sticky; top: 0; z-index: 20;
}
#tts-bar button {
  padding: 0.28rem 0.7rem; border-radius: var(--radius);
  border: 1px solid var(--border); background: var(--bg); color: var(--fg);
  cursor: pointer; font-size: 0.82rem; transition: background .12s;
}
#tts-bar button:hover:not(:disabled) { background: var(--accent); color: #fff; border-color: var(--accent); }
#tts-bar button:disabled { opacity: 0.4; cursor: default; }
#tts-bar select {
  border-radius: var(--radius); border: 1px solid var(--border);
  background: var(--bg); color: var(--fg); padding: 0.22rem 0.5rem; font-size: 0.82rem;
}
#tts-label { font-size: 0.78rem; opacity: 0.6; margin-left: auto; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 280px; }

/* Page layout */
#layout { display: grid; grid-template-columns: 210px 1fr; max-width: 1180px; margin: 0 auto; min-height: 100vh; }
@media (max-width: 720px) { #layout { grid-template-columns: 1fr; } #toc { display: none; } }

/* Sidebar TOC */
#toc {
  position: sticky; top: 45px; height: calc(100vh - 45px);
  overflow-y: auto; padding: 1.5rem 1rem;
  border-right: 1px solid var(--border); font-size: 0.82rem;
}
#toc h2 { font-size: 0.7rem; text-transform: uppercase; letter-spacing: .08em; opacity: 0.55; margin-bottom: 0.65rem; }
#toc a { display: block; padding: 0.22rem 0; color: var(--fg); text-decoration: none; opacity: 0.7; transition: opacity .12s; }
#toc a:hover, #toc a.active { opacity: 1; color: var(--accent); }

/* Main content */
main { padding: 2rem 2.5rem 4rem; max-width: 880px; }
h1.report-title { font-size: 1.7rem; font-weight: 700; margin-bottom: 0.2rem; }
.report-meta { font-size: 0.82rem; opacity: 0.55; margin-bottom: 2rem; }
section { margin-bottom: 2.5rem; scroll-margin-top: 50px; }
section h2 {
  font-size: 1.15rem; font-weight: 600;
  border-bottom: 2px solid var(--accent); padding-bottom: 0.3rem; margin-bottom: 0.9rem;
}
p { margin-bottom: 0.7rem; }
ul, ol { margin: 0.4rem 0 0.7rem 1.5rem; }
li { margin-bottom: 0.25rem; }

/* Tables */
.table-wrap { overflow-x: auto; margin-bottom: 1rem; }
table { width: 100%; border-collapse: collapse; font-size: 0.87rem; }
th { background: var(--surface); font-weight: 600; text-align: left; white-space: nowrap; }
th, td { padding: 0.45rem 0.7rem; border: 1px solid var(--border); }
tr:nth-child(even) td { background: var(--surface); }

/* Inline elements */
code { background: var(--surface); padding: 0.1em 0.3em; border-radius: 3px; font-size: 0.9em; }
pre { background: var(--surface); padding: 0.75rem; border-radius: var(--radius); overflow-x: auto; font-size: 0.84em; white-space: pre-wrap; margin-bottom: 0.75rem; }
a { color: var(--accent); }
hr { border: none; border-top: 1px solid var(--border); margin: 1.25rem 0; }
strong { font-weight: 600; }

/* Charts */
.chart-block { margin: 1rem 0; }
.chart-block img { max-width: 100%; border-radius: var(--radius); border: 1px solid var(--border); display: block; }
.chart-caption { font-size: 0.78rem; opacity: 0.65; margin-top: 0.3rem; font-style: italic; }
.chart-ascii { background: var(--surface); padding: 0.6rem 0.8rem; border-radius: var(--radius); font-size: 0.8rem; margin: 0.5rem 0; white-space: pre; overflow-x: auto; }

/* Collapsible transcript sections */
details { border: 1px solid var(--border); border-radius: var(--radius); margin-bottom: 0.65rem; }
summary { padding: 0.45rem 0.9rem; cursor: pointer; font-weight: 600; font-size: 0.9rem; }
details > *:not(summary) { padding: 0.5rem 0.9rem 0.75rem; }
details > pre { margin: 0 0.9rem 0.75rem; }

/* Warnings */
.warning-list li { color: #c0392b; }
@media (prefers-color-scheme: dark) { .warning-list li { color: #e74c3c; } }
"""

TTS_SCRIPT = """
(function () {
  var synth = window.speechSynthesis;
  if (!synth) return;

  var sections = [];
  var playBtn  = document.getElementById('tts-play');
  var pauseBtn = document.getElementById('tts-pause');
  var stopBtn  = document.getElementById('tts-stop');
  var rateEl   = document.getElementById('tts-rate');
  var voiceEl  = document.getElementById('tts-voice');
  var labelEl  = document.getElementById('tts-label');

  function populateVoices() {
    var voices = synth.getVoices();
    if (!voices.length) return;
    voiceEl.options.length = 0;
    voices.forEach(function (v, i) {
      var opt = document.createElement('option');
      opt.value = i;
      opt.textContent = v.name + ' (' + v.lang + ')';
      if (v.default) opt.selected = true;
      voiceEl.appendChild(opt);
    });
  }
  if (synth.onvoiceschanged !== undefined) { synth.onvoiceschanged = populateVoices; }
  populateVoices();

  function buildSections() {
    sections = [];
    document.querySelectorAll('#report-body section').forEach(function (sec) {
      var heading = sec.querySelector('h2');
      var title = heading ? heading.textContent.trim() : '';
      var parts = [];
      sec.querySelectorAll('h2,h3,p,li,td,th,summary').forEach(function (el) {
        if (el.closest('[aria-hidden="true"]')) { return; }
        var t = el.textContent.trim();
        if (t) { parts.push(t); }
      });
      if (parts.length) { sections.push({ title: title, text: parts.join('. ') }); }
    });
  }

  function setLabel(text) { if (labelEl) { labelEl.textContent = text; } }

  function speakSection(i) {
    if (i >= sections.length) { onDone(); return; }
    setLabel('Section ' + (i + 1) + '/' + sections.length + ': ' + sections[i].title);
    var utt = new SpeechSynthesisUtterance(sections[i].text);
    utt.rate = parseFloat(rateEl.value) || 1.0;
    var voices = synth.getVoices();
    var vi = parseInt(voiceEl.value, 10);
    if (!isNaN(vi) && voices[vi]) { utt.voice = voices[vi]; }
    utt.onend = function () { speakSection(i + 1); };
    utt.onerror = function () { speakSection(i + 1); };
    synth.speak(utt);
  }

  function onDone() {
    playBtn.disabled  = false;
    pauseBtn.disabled = true;
    stopBtn.disabled  = true;
    pauseBtn.textContent = '\u23f8 Pause';
    setLabel('');
  }

  playBtn.addEventListener('click', function () {
    buildSections();
    if (!sections.length) { return; }
    synth.cancel();
    playBtn.disabled  = true;
    pauseBtn.disabled = false;
    stopBtn.disabled  = false;
    speakSection(0);
  });

  pauseBtn.addEventListener('click', function () {
    if (synth.speaking && !synth.paused) {
      synth.pause();
      pauseBtn.textContent = '\u25b6 Resume';
    } else {
      synth.resume();
      pauseBtn.textContent = '\u23f8 Pause';
    }
  });

  stopBtn.addEventListener('click', function () {
    synth.cancel();
    onDone();
  });
})();
"""
