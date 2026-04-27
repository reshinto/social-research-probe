"""Static CSS and JavaScript assets for the HTML report.

CSS_STYLES: inline stylesheet for the report page.
TTS_SCRIPT: inline JavaScript that prefers Voicebox playback and falls back
to browser system voices when Voicebox is unavailable.
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
#tts-audio { display: none; }

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

TTS_SCRIPT = r"""
(function () {
  var toolbar = document.getElementById('tts-bar');
  var preparedAudioMapEl = document.getElementById('tts-prepared-audio-map');
  var playBtn  = document.getElementById('tts-play');
  var pauseBtn = document.getElementById('tts-pause');
  var stopBtn  = document.getElementById('tts-stop');
  var rateEl   = document.getElementById('tts-rate');
  var voiceEl  = document.getElementById('tts-voice');
  var refreshBtn = document.getElementById('tts-refresh');
  var labelEl  = document.getElementById('tts-label');
  var audioEl  = document.getElementById('tts-audio');
  var speechApi = window.speechSynthesis || null;
  var API_BASE = toolbar ? (toolbar.getAttribute('data-api-base') || 'http://127.0.0.1:17493') : 'http://127.0.0.1:17493';
  var PREPARED_AUDIO_SRC = toolbar ? (toolbar.getAttribute('data-prepared-audio-src') || '') : '';
  var PREPARED_PROFILE_NAME = toolbar ? (toolbar.getAttribute('data-prepared-profile-name') || '') : '';
  var PREPARED_AUDIO_MAP = {};
  var DEFAULT_PROFILE_NAME = voiceEl ? (voiceEl.getAttribute('data-default-profile-name') || '') : '';
  var VOICE_CHOICE_STORAGE_KEY = 'srp.tts.voice_choice';
  var SEGMENT_MAX_CHARS = 180;
  var STREAM_TIMEOUT_MS = 120000;
  var currentGenerationId = null;
  var currentObjectUrl = null;
  var currentRequestController = null;
  var currentSpeechUtterance = null;
  var currentVoiceboxProfiles = [];
  var currentSystemVoices = [];
  var narrationSegments = [];
  var currentSegmentIndex = -1;
  var isPlaybackActive = false;
  var playbackBackend = '';
  if (!toolbar || !playBtn || !pauseBtn || !stopBtn || !rateEl || !voiceEl || !refreshBtn || !audioEl) { return; }

  if (preparedAudioMapEl) {
    try {
      PREPARED_AUDIO_MAP = JSON.parse(preparedAudioMapEl.textContent || '{}') || {};
    } catch (err) {
      PREPARED_AUDIO_MAP = {};
    }
  }
  if (PREPARED_AUDIO_SRC && PREPARED_PROFILE_NAME && !PREPARED_AUDIO_MAP[PREPARED_PROFILE_NAME]) {
    PREPARED_AUDIO_MAP[PREPARED_PROFILE_NAME] = PREPARED_AUDIO_SRC;
  }

  function setLabel(text) {
    if (labelEl) { labelEl.textContent = text || ''; }
  }

  function setControls(isPlaying) {
    playBtn.disabled = !!isPlaying;
    pauseBtn.disabled = !isPlaying;
    stopBtn.disabled = !isPlaying;
  }

  function revokeObjectUrl() {
    if (currentObjectUrl) {
      URL.revokeObjectURL(currentObjectUrl);
      currentObjectUrl = null;
    }
  }

  function clearAudioElement() {
    audioEl.pause();
    audioEl.currentTime = 0;
    revokeObjectUrl();
    audioEl.removeAttribute('src');
    audioEl.load();
    pauseBtn.textContent = '\\u23f8 Pause';
  }

  function cancelSystemSpeech() {
    if (speechApi) {
      speechApi.cancel();
    }
    currentSpeechUtterance = null;
  }

  function abortPendingRequest() {
    if (currentRequestController) {
      currentRequestController.abort();
      currentRequestController = null;
    }
  }

  function resetPlaybackState() {
    isPlaybackActive = false;
    playbackBackend = '';
    abortPendingRequest();
    cancelSystemSpeech();
    clearAudioElement();
    currentGenerationId = null;
    narrationSegments = [];
    currentSegmentIndex = -1;
    pauseBtn.textContent = '\\u23f8 Pause';
    setControls(false);
  }

  function applyPlaybackRate() {
    var rate = parseFloat(rateEl.value || '1');
    var safeRate = Number.isNaN(rate) ? 1 : rate;
    audioEl.playbackRate = safeRate;
    if (currentSpeechUtterance) {
      currentSpeechUtterance.rate = safeRate;
    }
  }

  function cleanNarrationText(text) {
    var cleaned = String(text || '')
      .replace(/https?:\/\/\S+/gi, '')
      .replace(/www\.\S+/gi, '')
      .replace(/\s+/g, ' ')
      .replace(/\s+([,.;!?])/g, '$1')
      .trim();
    if (
      cleaned.indexOf('LLM synthesis unavailable') >= 0 ||
      cleaned.indexOf('LLM summary unavailable') >= 0
    ) {
      return '';
    }
    if (!cleaned) { return ''; }
    if (!/[.!?]$/.test(cleaned)) {
      cleaned += '.';
    }
    return cleaned;
  }

  function getNarrationPieces() {
    var parts = [];
    document.querySelectorAll(
      '#compiled-synthesis h2, #compiled-synthesis p, #compiled-synthesis li, #compiled-synthesis summary, ' +
      '#opportunity-analysis h2, #opportunity-analysis p, #opportunity-analysis li, #opportunity-analysis summary, ' +
      '#final-summary h2, #final-summary p, #final-summary li, #final-summary summary'
    ).forEach(function (el) {
      if (el.closest('[aria-hidden="true"]')) { return; }
      var text = cleanNarrationText(el.textContent || '');
      if (text) { parts.push(text); }
    });
    return parts;
  }

  function splitLongText(text, maxChars) {
    if (text.length <= maxChars) {
      return [text];
    }
    var chunks = [];
    var sentences = text.split(/(?<=[.!?])\s+/);
    var current = '';
    function pushCurrent() {
      if (current) {
        chunks.push(current);
        current = '';
      }
    }
    sentences.forEach(function (sentence) {
      if (!sentence) { return; }
      if (sentence.length > maxChars) {
        pushCurrent();
        var words = sentence.split(/\s+/);
        var longCurrent = '';
        words.forEach(function (word) {
          var candidate = longCurrent ? (longCurrent + ' ' + word) : word;
          if (candidate.length > maxChars && longCurrent) {
            chunks.push(longCurrent);
            longCurrent = word;
          } else if (candidate.length > maxChars) {
            chunks.push(candidate.slice(0, maxChars));
            longCurrent = candidate.slice(maxChars).trim();
          } else {
            longCurrent = candidate;
          }
        });
        if (longCurrent) {
          chunks.push(longCurrent);
        }
        return;
      }
      var next = current ? (current + ' ' + sentence) : sentence;
      if (next.length > maxChars && current) {
        pushCurrent();
        current = sentence;
      } else {
        current = next;
      }
    });
    pushCurrent();
    return chunks;
  }

  function buildNarrationSegments() {
    var segments = [];
    var current = '';
    getNarrationPieces().forEach(function (piece) {
      splitLongText(piece, SEGMENT_MAX_CHARS).forEach(function (chunk) {
        if (!chunk) { return; }
        var candidate = current ? (current + ' ' + chunk) : chunk;
        if (candidate.length > SEGMENT_MAX_CHARS && current) {
          segments.push(current);
          current = chunk;
        } else {
          current = candidate;
        }
      });
    });
    if (current) {
      segments.push(current);
    }
    return segments;
  }

  function safeStorageGet(key) {
    try {
      return window.localStorage.getItem(key) || '';
    } catch (err) {
      return '';
    }
  }

  function safeStorageSet(key, value) {
    try {
      window.localStorage.setItem(key, value);
    } catch (err) {
      return;
    }
  }

  function buildVoiceChoiceValue(source, voiceId) {
    if (!source || !voiceId) { return ''; }
    return source + '::' + voiceId;
  }

  function parseVoiceChoiceValue(value) {
    var raw = String(value || '');
    var separatorIndex = raw.indexOf('::');
    if (separatorIndex < 0) {
      return { source: '', id: raw };
    }
    return {
      source: raw.slice(0, separatorIndex),
      id: raw.slice(separatorIndex + 2)
    };
  }

  function currentVoiceOption() {
    return voiceEl.options[voiceEl.selectedIndex] || null;
  }

  function optionSource(option) {
    if (!option) { return ''; }
    return option.getAttribute('data-source') || parseVoiceChoiceValue(option.value).source || '';
  }

  function optionId(option) {
    if (!option) { return ''; }
    return option.getAttribute('data-voice-id') || parseVoiceChoiceValue(option.value).id || '';
  }

  function currentVoiceSource() {
    return optionSource(currentVoiceOption());
  }

  function currentVoiceId() {
    return optionId(currentVoiceOption());
  }

  function currentVoiceboxProfileId() {
    if (currentVoiceSource() !== 'voicebox') { return ''; }
    var selectedName = currentVoiceId();
    if (!selectedName) { return ''; }
    for (var i = 0; i < currentVoiceboxProfiles.length; i += 1) {
      var profile = currentVoiceboxProfiles[i];
      if (profile.name === selectedName && profile.id) {
        return profile.id;
      }
    }
    return '';
  }

  function usableVoiceOptions() {
    return Array.from(voiceEl.querySelectorAll('option')).filter(function (option) {
      return !!optionId(option);
    });
  }

  function hasUsableVoices() {
    return usableVoiceOptions().length > 0;
  }

  function hasSystemVoiceSupport() {
    return !!(speechApi && typeof window.SpeechSynthesisUtterance !== 'undefined');
  }

  function systemVoiceById(voiceId) {
    if (!hasSystemVoiceSupport() || !voiceId) { return null; }
    var voices = speechApi.getVoices() || [];
    for (var i = 0; i < voices.length; i += 1) {
      var voice = voices[i];
      if ((voice.voiceURI || voice.name) === voiceId) {
        return voice;
      }
    }
    return null;
  }

  function rememberSelectedVoice() {
    var option = currentVoiceOption();
    var source = optionSource(option);
    var voiceId = optionId(option);
    if (!source || !voiceId) { return; }
    safeStorageSet(VOICE_CHOICE_STORAGE_KEY, buildVoiceChoiceValue(source, voiceId));
  }

  function selectPreferredVoice() {
    var candidates = [];
    var storedChoice = safeStorageGet(VOICE_CHOICE_STORAGE_KEY);
    if (storedChoice) {
      candidates.push(storedChoice);
    }
    if (DEFAULT_PROFILE_NAME) {
      candidates.push(buildVoiceChoiceValue('voicebox', DEFAULT_PROFILE_NAME));
    }
    if (voiceEl.value) {
      candidates.push(voiceEl.value);
    }
    for (var i = 0; i < candidates.length; i += 1) {
      var preferred = candidates[i];
      var exists = usableVoiceOptions().some(function (option) {
        return option.value === preferred;
      });
      if (exists) {
        voiceEl.value = preferred;
        rememberSelectedVoice();
        return;
      }
    }
    var options = usableVoiceOptions();
    if (options.length) {
      voiceEl.value = options[0].value;
      rememberSelectedVoice();
    }
  }

  function readRenderedVoiceboxProfiles() {
    var seen = {};
    return Array.from(voiceEl.querySelectorAll('option')).map(function (option) {
      var source = optionSource(option);
      var profileName = option.getAttribute('data-voice-name') || option.textContent || optionId(option);
      if (source !== 'voicebox' || !profileName || seen[profileName]) {
        return null;
      }
      seen[profileName] = true;
      return {
        id: '',
        name: profileName
      };
    }).filter(Boolean);
  }

  function collectSystemVoices() {
    if (!hasSystemVoiceSupport()) {
      return [];
    }
    var seen = {};
    return (speechApi.getVoices() || [])
      .map(function (voice) {
        var voiceId = voice.voiceURI || voice.name || '';
        if (!voiceId || seen[voiceId]) {
          return null;
        }
        seen[voiceId] = true;
        return {
          id: voiceId,
          name: voice.name || voiceId,
          lang: voice.lang || '',
          isDefault: !!voice.default
        };
      })
      .filter(Boolean)
      .sort(function (left, right) {
        if (left.isDefault !== right.isDefault) {
          return left.isDefault ? -1 : 1;
        }
        return left.name.localeCompare(right.name);
      });
  }

  function renderVoiceChoices() {
    var previousChoice = voiceEl.value;
    voiceEl.innerHTML = '';
    if (currentVoiceboxProfiles.length) {
      var voiceboxGroup = document.createElement('optgroup');
      voiceboxGroup.label = 'Voicebox';
      currentVoiceboxProfiles.forEach(function (profile) {
        var option = document.createElement('option');
        option.value = buildVoiceChoiceValue('voicebox', profile.name);
        option.setAttribute('data-source', 'voicebox');
        option.setAttribute('data-voice-name', profile.name);
        option.textContent = profile.name;
        voiceboxGroup.appendChild(option);
      });
      voiceEl.appendChild(voiceboxGroup);
    }
    if (currentSystemVoices.length) {
      var systemGroup = document.createElement('optgroup');
      systemGroup.label = 'System';
      currentSystemVoices.forEach(function (voice) {
        var option = document.createElement('option');
        option.value = buildVoiceChoiceValue('system', voice.id);
        option.setAttribute('data-source', 'system');
        option.setAttribute('data-voice-id', voice.id);
        option.textContent = voice.isDefault ? (voice.name + ' (Default)') : voice.name;
        systemGroup.appendChild(option);
      });
      voiceEl.appendChild(systemGroup);
    }
    if (!currentVoiceboxProfiles.length && !currentSystemVoices.length) {
      var placeholder = document.createElement('option');
      placeholder.value = '';
      placeholder.textContent = 'No voices available';
      voiceEl.appendChild(placeholder);
    } else if (previousChoice) {
      voiceEl.value = previousChoice;
    }
    selectPreferredVoice();
  }

  function firstSystemVoiceChoice() {
    for (var i = 0; i < voiceEl.options.length; i += 1) {
      if (optionSource(voiceEl.options[i]) === 'system') {
        return voiceEl.options[i].value;
      }
    }
    return '';
  }

  function maybeSelectSystemVoice() {
    var systemChoice = firstSystemVoiceChoice();
    if (!systemChoice) {
      return false;
    }
    voiceEl.value = systemChoice;
    rememberSelectedVoice();
    return true;
  }

  function isNetworkFetchError(err) {
    var message = String((err && err.message) || '');
    return err instanceof TypeError || message === 'Failed to fetch' || message.indexOf('Load failed') >= 0;
  }

  function makeHttpError(prefix, status, detail) {
    var message = prefix + ': ' + status;
    if (detail) {
      message += ' ' + detail;
    }
    var err = new Error(message);
    err.httpStatus = status;
    err.httpDetail = detail || '';
    return err;
  }

  function describeOperationalFailure(err, fallbackMessage) {
    if (isNetworkFetchError(err)) {
      return describeVoiceboxReachabilityFailure();
    }
    if (err && err.httpStatus === 502 && err.httpDetail) {
      return err.httpDetail;
    }
    if (err && err.httpDetail) {
      return err.httpDetail;
    }
    if (err && err.message) {
      return err.message;
    }
    return fallbackMessage;
  }

  function describeVoiceboxReachabilityFailure() {
    if (window.location.protocol === 'file:') {
      return 'Voicebox blocked from file:// page. Use srp serve-report --report PATH or allow CORS for file:// on Voicebox.';
    }
    return 'Voicebox not reachable at ' + API_BASE;
  }

  function sleep(ms) {
    return new Promise(function (resolve) {
      window.setTimeout(resolve, ms);
    });
  }

  function makeCanceledError() {
    var err = new Error('Voicebox generation canceled');
    err.canceled = true;
    return err;
  }

  function isCanceledError(err) {
    return !!(err && err.canceled);
  }

  function makeTimedOutError() {
    var err = new Error('Voicebox stream stalled. Restart Voicebox and try again.');
    err.timedOut = true;
    return err;
  }

  function isTimedOutError(err) {
    return !!(err && err.timedOut);
  }

  function isPlayableAudioType(contentType) {
    if (!contentType) { return true; }
    return contentType.indexOf('audio/') === 0 || contentType === 'application/octet-stream';
  }

  function activateBlobAudio(blob, generationId) {
    revokeObjectUrl();
    currentObjectUrl = URL.createObjectURL(blob);
    audioEl.src = currentObjectUrl;
    currentGenerationId = generationId || 'stream';
  }

  function preparedAudioSrcForSelectedVoice() {
    if (currentVoiceSource() !== 'voicebox') {
      return '';
    }
    var profileName = currentVoiceId();
    if (profileName && PREPARED_AUDIO_MAP[profileName]) {
      return PREPARED_AUDIO_MAP[profileName];
    }
    if (PREPARED_AUDIO_SRC) {
      if (!PREPARED_PROFILE_NAME || !profileName || profileName === PREPARED_PROFILE_NAME) {
        return PREPARED_AUDIO_SRC;
      }
    }
    return '';
  }

  function hasPreparedAudioForSelectedVoice() {
    return !!preparedAudioSrcForSelectedVoice();
  }

  async function playPreparedAudio() {
    var preparedSrc = preparedAudioSrcForSelectedVoice();
    if (!preparedSrc) {
      throw new Error('Prepared narration unavailable for the selected voice');
    }
    resetPlaybackState();
    isPlaybackActive = true;
    playbackBackend = 'prepared-audio';
    currentSegmentIndex = 0;
    currentGenerationId = 'prepared';
    audioEl.src = preparedSrc;
    playBtn.disabled = true;
    pauseBtn.disabled = true;
    stopBtn.disabled = false;
    applyPlaybackRate();
    setLabel('Playing prepared report narration');
    await audioEl.play();
    setControls(true);
  }

  function generationPayload(profileId, text) {
    return {
      profile_id: profileId,
      text: text,
      language: 'en',
      max_chunk_chars: 400,
      crossfade_ms: 50
    };
  }

  async function fetchStreamedAudio(profileId, text) {
    var controller = new AbortController();
    var didTimeout = false;
    var timeoutId = window.setTimeout(function () {
      didTimeout = true;
      controller.abort();
    }, STREAM_TIMEOUT_MS);
    currentRequestController = controller;
    try {
      var res = await fetch(API_BASE + '/generate/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(generationPayload(profileId, text)),
        signal: controller.signal
      });
      if (!res.ok) {
        var detail = await res.text().catch(function () { return ''; });
        var err = new Error(detail || ('Voicebox stream failed: ' + res.status));
        if (res.status === 404 || res.status === 405 || res.status === 501) {
          err.fallbackToAsync = true;
        }
        throw err;
      }
      var contentType = ((res.headers.get('Content-Type') || '').split(';')[0] || '').trim().toLowerCase();
      if (!isPlayableAudioType(contentType)) {
        var streamDetail = await res.text().catch(function () { return ''; });
        throw new Error(streamDetail || 'Voicebox stream did not return audio');
      }
      var blob = await res.blob();
      if (!blob.size) {
        throw new Error('Voicebox returned empty audio');
      }
      return blob;
    } catch (err) {
      if (err && err.name === 'AbortError') {
        if (didTimeout) {
          throw makeTimedOutError();
        }
        throw makeCanceledError();
      }
      throw err;
    } finally {
      window.clearTimeout(timeoutId);
      if (currentRequestController === controller) {
        currentRequestController = null;
      }
    }
  }

  async function fetchPlayableAudio(generationId) {
    var audioUrl = API_BASE + '/audio/' + encodeURIComponent(generationId);
    var lastDetail = '';
    for (var attempt = 0; attempt < 60; attempt += 1) {
      var res = await fetch(audioUrl, { cache: 'no-store' });
      var contentType = ((res.headers.get('Content-Type') || '').split(';')[0] || '').trim().toLowerCase();
      if (res.ok) {
        if (isPlayableAudioType(contentType)) {
          var blob = await res.blob();
          if (blob.size > 0) {
            return blob;
          }
          lastDetail = 'Voicebox returned empty audio';
        } else {
          lastDetail = await res.text().catch(function () { return ''; });
          if (!lastDetail) {
            lastDetail = 'Voicebox audio is still preparing';
          }
        }
      } else if (
        res.status === 404 ||
        res.status === 409 ||
        res.status === 425 ||
        res.status === 500 ||
        res.status === 502 ||
        res.status === 503 ||
        res.status === 504
      ) {
        lastDetail = await res.text().catch(function () { return ''; });
        if (!lastDetail) {
          lastDetail = 'Voicebox audio is still preparing';
        }
      } else {
        var detail = await res.text().catch(function () { return ''; });
        throw new Error(detail || ('Voicebox audio fetch failed: ' + res.status));
      }
      await sleep(500);
    }
    throw new Error(lastDetail || 'Voicebox audio was not ready in time');
  }

  async function generateAudioViaAsync(profileId, text) {
    var res = await fetch(API_BASE + '/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(generationPayload(profileId, text))
    });
    if (!res.ok) {
      throw new Error('Generation failed: ' + res.status + ' ' + await res.text());
    }
    var result = await res.json();
    var generationId = result.id || result.generation_id;
    if (!generationId) {
      throw new Error('Generation response missing id');
    }
    currentGenerationId = generationId;
    return fetchPlayableAudio(generationId);
  }

  function finishPlayback() {
    resetPlaybackState();
    setLabel('');
  }

  function systemVoiceLabel() {
    var systemVoice = systemVoiceById(currentVoiceId());
    return systemVoice && systemVoice.name ? systemVoice.name : 'system voice';
  }

  function playSystemSpeechSegment(index) {
    if (!isPlaybackActive || playbackBackend !== 'system-speech') {
      return;
    }
    if (index >= narrationSegments.length) {
      finishPlayback();
      return;
    }
    currentSegmentIndex = index;
    var utterance = new SpeechSynthesisUtterance(narrationSegments[index]);
    currentSpeechUtterance = utterance;
    utterance.rate = parseFloat(rateEl.value || '1') || 1;
    var systemVoice = systemVoiceById(currentVoiceId());
    if (systemVoice) {
      utterance.voice = systemVoice;
    }
    utterance.onend = function () {
      if (!isPlaybackActive || playbackBackend !== 'system-speech') {
        return;
      }
      playSystemSpeechSegment(index + 1);
    };
    utterance.onerror = function (event) {
      if (!isPlaybackActive || playbackBackend !== 'system-speech') {
        return;
      }
      if (event && (event.error === 'interrupted' || event.error === 'canceled')) {
        return;
      }
      resetPlaybackState();
      playBtn.disabled = false;
      setLabel('System voice playback failed');
    };
    playBtn.disabled = true;
    pauseBtn.disabled = false;
    stopBtn.disabled = false;
    setLabel('Speaking with ' + systemVoiceLabel() + ' ' + (index + 1) + '/' + narrationSegments.length);
    speechApi.cancel();
    speechApi.speak(utterance);
    setControls(true);
  }

  async function playVoiceboxSegment(profileId, index) {
    if (!isPlaybackActive || playbackBackend !== 'voicebox-audio') { return; }
    if (index >= narrationSegments.length) {
      finishPlayback();
      return;
    }
    currentSegmentIndex = index;
    playBtn.disabled = true;
    pauseBtn.disabled = true;
    stopBtn.disabled = false;
    setLabel('Preparing report narration ' + (index + 1) + '/' + narrationSegments.length + '…');
    try {
      clearAudioElement();
      try {
        activateBlobAudio(await fetchStreamedAudio(profileId, narrationSegments[index]), 'stream-' + index);
      } catch (err) {
        if (!err || !err.fallbackToAsync) {
          throw err;
        }
        activateBlobAudio(await generateAudioViaAsync(profileId, narrationSegments[index]), currentGenerationId);
      }
      applyPlaybackRate();
      await audioEl.play();
      setControls(true);
      setLabel('Playing report narration ' + (index + 1) + '/' + narrationSegments.length);
    } catch (err) {
      console.error(err);
      if (isCanceledError(err)) {
        return;
      }
      if (isNetworkFetchError(err) && hasSystemVoiceSupport() && maybeSelectSystemVoice()) {
        setLabel('Voicebox unavailable; using system voice');
        resetPlaybackState();
        narrationSegments = buildNarrationSegments();
        isPlaybackActive = true;
        playbackBackend = 'system-speech';
        playSystemSpeechSegment(0);
        return;
      }
      resetPlaybackState();
      playBtn.disabled = false;
      if (isTimedOutError(err)) {
        setLabel(err.message);
      } else if (isNetworkFetchError(err)) {
        setLabel(describeVoiceboxReachabilityFailure());
      } else {
        setLabel(err.message || 'Voicebox generation failed');
      }
    }
  }

  function normalizeVoiceboxProfiles(payload) {
    var rawProfiles = Array.isArray(payload) ? payload : (payload.profiles || []);
    var seen = {};
    var seenNames = {};
    function normalizedName(value) {
      return String(value || '').replace(/\s+/g, ' ').trim().toLowerCase();
    }
    function uniqueName(rawName) {
      var baseName = String(rawName || '').trim() || 'Voicebox Profile';
      var candidate = baseName;
      var suffix = 2;
      while (seenNames[normalizedName(candidate)]) {
        candidate = baseName + ' (' + suffix + ')';
        suffix += 1;
      }
      seenNames[normalizedName(candidate)] = true;
      return candidate;
    }
    return rawProfiles.map(function (profile) {
      if (!profile || typeof profile !== 'object') {
        return null;
      }
      var profileId = String(profile.id || '').trim();
      if (!profileId || seen[profileId]) {
        return null;
      }
      seen[profileId] = true;
      return {
        id: profileId,
        name: uniqueName(profile.name)
      };
    }).filter(Boolean);
  }

  function refreshVoiceLabel(err) {
    if (Object.keys(PREPARED_AUDIO_MAP).length || PREPARED_AUDIO_SRC) {
      setLabel('Prepared report narration ready');
      return;
    }
    if (currentVoiceboxProfiles.length) {
      setLabel('');
      return;
    }
    if (currentSystemVoices.length) {
      maybeSelectSystemVoice();
      setLabel(err ? 'Voicebox unavailable; using system voice' : 'Using system voice');
      return;
    }
    if (err) {
      setLabel(describeOperationalFailure(err, 'Failed to load Voicebox profiles'));
      return;
    }
    setLabel('No voices available');
  }

  async function loadVoiceboxProfiles(showStatus) {
    if (showStatus) { setLabel('Loading voices…'); }
    try {
      var res = await fetch(API_BASE + '/profiles');
      if (!res.ok) {
        throw makeHttpError(
          'Failed to load Voicebox profiles',
          res.status,
          await res.text().catch(function () { return ''; })
        );
      }
      currentVoiceboxProfiles = normalizeVoiceboxProfiles(await res.json());
      renderVoiceChoices();
      refreshVoiceLabel(null);
    } catch (err) {
      console.error(err);
      if (!showStatus && hasUsableVoices()) {
        return;
      }
      renderVoiceChoices();
      refreshVoiceLabel(err);
    }
  }

  async function startNarration() {
    if (!hasUsableVoices() && !hasPreparedAudioForSelectedVoice()) {
      setLabel('No voices available');
      return;
    }
    rememberSelectedVoice();
    if (hasPreparedAudioForSelectedVoice()) {
      try {
        await playPreparedAudio();
      } catch (err) {
        console.error(err);
        resetPlaybackState();
        playBtn.disabled = false;
        setLabel(err.message || 'Prepared narration playback failed');
      }
      return;
    }
    narrationSegments = buildNarrationSegments();
    if (!narrationSegments.length) {
      setLabel('No report text found');
      return;
    }
    if (currentVoiceSource() === 'system') {
      if (!hasSystemVoiceSupport()) {
        setLabel('System voice playback is not available in this browser');
        return;
      }
      resetPlaybackState();
      narrationSegments = buildNarrationSegments();
      isPlaybackActive = true;
      playbackBackend = 'system-speech';
      playSystemSpeechSegment(0);
      return;
    }
    if (currentVoiceSource() !== 'voicebox' || !currentVoiceId()) {
      if (maybeSelectSystemVoice()) {
        resetPlaybackState();
        narrationSegments = buildNarrationSegments();
        isPlaybackActive = true;
        playbackBackend = 'system-speech';
        playSystemSpeechSegment(0);
        return;
      }
      setLabel('Choose a voice first');
      return;
    }
    var profileId = currentVoiceboxProfileId();
    if (!profileId) {
      if (maybeSelectSystemVoice()) {
        resetPlaybackState();
        narrationSegments = buildNarrationSegments();
        isPlaybackActive = true;
        playbackBackend = 'system-speech';
        playSystemSpeechSegment(0);
        return;
      }
      setLabel('Voicebox profiles are unavailable; refresh voices or use a system voice');
      return;
    }
    resetPlaybackState();
    narrationSegments = buildNarrationSegments();
    isPlaybackActive = true;
    playbackBackend = 'voicebox-audio';
    playBtn.disabled = true;
    pauseBtn.disabled = true;
    stopBtn.disabled = false;
    pauseBtn.textContent = '\\u23f8 Pause';
    setLabel('Generating report narration…');
    await playVoiceboxSegment(profileId, 0);
  }

  playBtn.addEventListener('click', startNarration);
  refreshBtn.addEventListener('click', function () {
    currentSystemVoices = collectSystemVoices();
    renderVoiceChoices();
    loadVoiceboxProfiles(true);
  });

  pauseBtn.addEventListener('click', function () {
    if (playbackBackend === 'system-speech') {
      if (!speechApi) { return; }
      if (speechApi.paused) {
        speechApi.resume();
        pauseBtn.textContent = '\\u23f8 Pause';
        setLabel('Speaking with ' + systemVoiceLabel());
      } else {
        speechApi.pause();
        pauseBtn.textContent = '\\u25b6 Resume';
        setLabel('Paused');
      }
      return;
    }
    if (!audioEl.src) { return; }
    if (audioEl.paused) {
      audioEl.play();
      pauseBtn.textContent = '\\u23f8 Pause';
      setLabel(
        currentGenerationId === 'prepared' ? 'Playing prepared report narration' : 'Playing report narration'
      );
    } else {
      audioEl.pause();
      pauseBtn.textContent = '\\u25b6 Resume';
      setLabel('Paused');
    }
  });

  stopBtn.addEventListener('click', function () {
    resetPlaybackState();
    setLabel('');
  });

  rateEl.addEventListener('change', function () {
    applyPlaybackRate();
  });

  voiceEl.addEventListener('change', function () {
    rememberSelectedVoice();
  });

  audioEl.addEventListener('ended', function () {
    if (playbackBackend === 'voicebox-audio' && isPlaybackActive && currentSegmentIndex + 1 < narrationSegments.length) {
      var nextProfileId = currentVoiceboxProfileId();
      if (!nextProfileId) {
        finishPlayback();
        setLabel('Voicebox profiles are unavailable; refresh voices to continue');
        return;
      }
      playVoiceboxSegment(nextProfileId, currentSegmentIndex + 1);
      return;
    }
    finishPlayback();
  });

  audioEl.addEventListener('pause', function () {
    if (playbackBackend === 'system-speech') { return; }
    if (audioEl.src && audioEl.currentTime < audioEl.duration) {
      pauseBtn.textContent = '\\u25b6 Resume';
    }
  });

  audioEl.addEventListener('play', function () {
    if (playbackBackend === 'system-speech' || !audioEl.src) { return; }
    pauseBtn.textContent = '\\u23f8 Pause';
    setControls(true);
  });

  currentVoiceboxProfiles = readRenderedVoiceboxProfiles();
  currentSystemVoices = collectSystemVoices();
  renderVoiceChoices();
  applyPlaybackRate();
  refreshVoiceLabel(null);

  if (speechApi && typeof speechApi.addEventListener === 'function') {
    speechApi.addEventListener('voiceschanged', function () {
      currentSystemVoices = collectSystemVoices();
      if (!isPlaybackActive) {
        renderVoiceChoices();
        refreshVoiceLabel(null);
      }
    });
  }

  loadVoiceboxProfiles(!currentVoiceboxProfiles.length);
})();
"""
