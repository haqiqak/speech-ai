"""
voice.py — Browser-native Voice-In (STT) and Voice-Out (TTS) for Speech AI.

Design decisions
─────────────────
STT: Web Speech API called directly via st.iframe with
     interimResults=true for live word-by-word display.  The component
     renders its own Start / Stop buttons, shows interim text inside a
     live textarea, then pushes the final transcript back to Streamlit
     via st.query_params (polled with st_autorefresh or a meta-refresh
     shim).  Falls back gracefully on Firefox (no Web Speech API).

     Legacy streamlit-mic-recorder path is kept as a fallback when
     render_voice_input() is called with live_preview=False.

TTS: window.speechSynthesis injected via st.iframe.
     Lets the browser pick from its local neural voices (Chrome/Edge ship
     high-quality ones). User can choose voice + rate.  Zero cost, zero
     server load, no temp files.

Neither component imports torch, transformers, or any heavy library, so
both are safe on Streamlit Community Cloud and Hugging Face Spaces free
tiers.

Public API
──────────
    transcript = render_voice_input(key="...", live_preview=True)
        Shows mic button with live interim transcript; returns final text
        or None.

    render_tts_button(text, key="...", label="🔊 Speak")
        Injects a JS TTS trigger.  No return value.

    render_voice_settings()
        Sidebar widget: TTS rate slider + voice selector (populated by JS).
"""

from __future__ import annotations

import streamlit as st


# ── helpers ──────────────────────────────────────────────────────────────────

def _check_mic_recorder() -> bool:
    """Return True if streamlit-mic-recorder is installed."""
    try:
        import streamlit_mic_recorder  # noqa: F401
        return True
    except ImportError:
        return False


# ── Live-preview STT component ────────────────────────────────────────────────

def _live_stt_html(component_key: str, language: str) -> str:
    """
    Return a self-contained HTML/JS block that:
      • Shows "🎙️ Start speaking" / "⏹ Stop" buttons.
      • Streams interim words into a read-only textarea in real time.
      • On stop (or natural end), writes the final transcript into
        window.parent's URL query-string as  ?<component_key>=<text>
        so Streamlit can read it via st.query_params.
      • Also posts a window.parent.postMessage for any parent listeners.
    """
    return f"""
<style>
  :root {{
    --blue: #2563eb;
    --blue-light: #dbeafe;
    --border: #bfdbfe;
    --text: #1e3a5f;
    --red: #dc2626;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; font-family: 'DM Sans', system-ui, sans-serif; }}
  body {{ background: transparent; padding: 4px 0; }}

  #stt-wrap {{
    display: flex;
    flex-direction: column;
    gap: 8px;
  }}

  .btn-row {{
    display: flex;
    gap: 8px;
  }}

  button {{
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 7px 16px;
    border-radius: 8px;
    border: none;
    font-size: .88rem;
    font-weight: 600;
    cursor: pointer;
    transition: opacity .15s, transform .1s;
  }}
  button:active {{ transform: scale(.97); }}
  button:disabled {{ opacity: .45; cursor: not-allowed; transform: none; }}

  #btn-start {{
    background: var(--blue);
    color: #fff;
  }}
  #btn-stop {{
    background: var(--red);
    color: #fff;
  }}

  #status {{
    font-size: .78rem;
    color: #64748b;
    min-height: 1.1em;
  }}

  #live-box {{
    width: 100%;
    min-height: 72px;
    max-height: 160px;
    padding: .55rem .75rem;
    border: 1.5px solid var(--border);
    border-radius: 10px;
    background: var(--blue-light);
    color: var(--text);
    font-size: .93rem;
    line-height: 1.5;
    resize: vertical;
    overflow-y: auto;
    white-space: pre-wrap;
    word-break: break-word;
    outline: none;
  }}
  #live-box.recording {{
    border-color: var(--red);
    box-shadow: 0 0 0 3px rgba(220,38,38,.15);
  }}
  #live-box.done {{
    border-color: var(--blue);
    background: #eff6ff;
  }}

  .dot-blink {{
    display: inline-block;
    width: 8px; height: 8px;
    border-radius: 50%;
    background: var(--red);
    margin-right: 5px;
    animation: blink 1s infinite;
  }}
  @keyframes blink {{ 0%,100%{{opacity:1}} 50%{{opacity:.2}} }}
</style>

<div id="stt-wrap">
  <div class="btn-row">
    <button id="btn-start">🎙️ Start speaking</button>
    <button id="btn-stop" disabled>⏹ Stop</button>
  </div>
  <div id="status">Ready.</div>
  <div id="live-box" aria-label="Live transcript" tabindex="-1">&nbsp;</div>
</div>

<script>
(function() {{
  var LANG        = "{language}";
  var PARAM_KEY   = "{component_key}";
  var btnStart    = document.getElementById("btn-start");
  var btnStop     = document.getElementById("btn-stop");
  var statusEl    = document.getElementById("status");
  var liveBox     = document.getElementById("live-box");

  var recognition = null;
  var finalText   = "";
  var interimText = "";
  var recording   = false;

  // ── browser support check ──
  var SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRec) {{
    statusEl.textContent = "⚠️ Web Speech API not supported in this browser. Use Chrome or Edge.";
    btnStart.disabled = true;
    return;
  }}

  function updateBox() {{
    liveBox.textContent = finalText + interimText || "";
    if (!finalText && !interimText) liveBox.innerHTML = "&nbsp;";
  }}

  function setRecording(on) {{
    recording = on;
    btnStart.disabled = on;
    btnStop.disabled  = !on;
    liveBox.className = on ? "recording" : "";
    if (on) {{
      statusEl.innerHTML = '<span class="dot-blink"></span>Recording… speak now';
    }}
  }}

  function pushFinal(text) {{
    // Push the final transcript to the parent Streamlit frame via query param.
    // Streamlit polls st.query_params, so a URL update triggers re-evaluation.
    try {{
      var encoded = encodeURIComponent(text);
      var url = new URL(window.parent.location.href);
      url.searchParams.set(PARAM_KEY, encoded);
      window.parent.history.replaceState(null, "", url.toString());
    }} catch(e) {{
      // cross-origin guard — fallback to postMessage only
    }}
    window.parent.postMessage({{
      type:   "stt_final",
      key:    PARAM_KEY,
      text:   text,
    }}, "*");
  }}

  function initRecognition() {{
    recognition = new SpeechRec();
    recognition.lang            = LANG;
    recognition.interimResults  = true;
    recognition.maxAlternatives = 1;
    recognition.continuous      = true;   // keep listening until Stop

    recognition.onstart = function() {{
      setRecording(true);
    }};

    recognition.onresult = function(e) {{
      var interim = "";
      for (var i = e.resultIndex; i < e.results.length; i++) {{
        if (e.results[i].isFinal) {{
          finalText += e.results[i][0].transcript + " ";
        }} else {{
          interim += e.results[i][0].transcript;
        }}
      }}
      interimText = interim;
      updateBox();
    }};

    recognition.onerror = function(e) {{
      statusEl.textContent = "Error: " + e.error;
      setRecording(false);
    }};

    recognition.onend = function() {{
      interimText = "";
      setRecording(false);
      liveBox.className = "done";
      var final = finalText.trim();
      if (final) {{
        statusEl.textContent = "✅ Done — transcript captured.";
        updateBox();
        pushFinal(final);
      }} else {{
        statusEl.textContent = "Nothing recognised. Try again.";
        liveBox.innerHTML = "&nbsp;";
      }}
      finalText = "";
    }};
  }}

  btnStart.addEventListener("click", function() {{
    finalText   = "";
    interimText = "";
    liveBox.className = "";
    liveBox.innerHTML = "&nbsp;";
    initRecognition();
    recognition.start();
  }});

  btnStop.addEventListener("click", function() {{
    if (recognition && recording) {{
      recognition.stop();   // triggers onend → pushFinal
    }}
  }});
}})();
</script>
"""


def render_voice_input(
    key: str = "voice_input",
    language: str = "en-US",
    placeholder: str = "Click the mic and speak…",
    live_preview: bool = True,
    height: int = 220,
) -> str | None:
    """
    Render a mic button with live interim transcript.

    Parameters
    ----------
    key          : unique Streamlit key (also used as URL query-param name).
    language     : BCP-47 language tag passed to SpeechRecognition.
    live_preview : if True (default) use the built-in live-preview widget.
                   Set False to fall back to streamlit-mic-recorder behaviour.
    height       : pixel height of the embedded component iframe.

    Returns
    -------
    The final transcript string, or None if nothing was captured yet.
    """
    # ── legacy fallback ──────────────────────────────────────────────────────
    if not live_preview:
        return _render_legacy_voice_input(key=key, language=language)

    # ── live-preview path ────────────────────────────────────────────────────
    # 1. Render the self-contained HTML widget
    st.iframe(
        _live_stt_html(component_key=key, language=language),
        height=height,
    )

    # 2. Read back the final transcript that the JS wrote into query params
    #    (the JS does window.parent.history.replaceState with ?key=encoded_text)
    params = st.query_params
    raw = params.get(key)          # returns str | None in Streamlit ≥ 1.30

    if raw:
        from urllib.parse import unquote
        transcript = unquote(raw).strip()
    else:
        transcript = None

    # 3. Persist in session state so the value survives across reruns even
    #    after the query-param is cleared.
    if transcript:
        st.session_state[f"{key}_last"] = transcript

    last = st.session_state.get(f"{key}_last")

    # 4. Clear button
    if last:
        col1, col2 = st.columns([5, 1])
        with col2:
            if st.button("✕ Clear", key=f"{key}_clear", use_container_width=True):
                st.session_state[f"{key}_last"] = None
                # Also remove from query params
                try:
                    params_dict = dict(st.query_params)
                    params_dict.pop(key, None)
                    st.query_params.update(params_dict)
                except Exception:
                    pass
                st.rerun()

    return last or None


# ── legacy path (streamlit-mic-recorder) ─────────────────────────────────────

def _render_legacy_voice_input(
    key: str = "voice_input",
    language: str = "en-US",
) -> str | None:
    if not _check_mic_recorder():
        st.info(
            "🎙️ Voice input requires **streamlit-mic-recorder**. "
            "Add it to `requirements.txt` and redeploy.",
            icon="ℹ️",
        )
        return None

    from streamlit_mic_recorder import speech_to_text  # type: ignore[import]

    transcript = speech_to_text(
        language=language,
        start_prompt="🎙️ Start speaking",
        stop_prompt="⏹ Stop",
        just_once=True,
        use_container_width=True,
        callback=None,
        key=key,
    )

    if transcript:
        st.session_state[f"{key}_last"] = transcript

    last = st.session_state.get(f"{key}_last")
    if last:
        st.markdown(
            f'<div style="background:#eef6ff;border:1.5px solid #b8d9f5;border-radius:12px;'
            f'padding:.55rem 1rem;font-size:.95rem;color:#1a2740;margin-top:.3rem">'
            f'🎙️ <em>{last}</em></div>',
            unsafe_allow_html=True,
        )
        col1, col2 = st.columns([3, 1])
        with col2:
            if st.button("✕ Clear", key=f"{key}_clear", use_container_width=True):
                st.session_state[f"{key}_last"] = None
                st.rerun()

    return last or None


# ── TTS ──────────────────────────────────────────────────────────────────────

def _tts_html(text: str, rate: float, voice_index: int, component_key: str) -> str:
    """
    Return self-contained HTML/JS that speaks *text* immediately on render.

    voice_index: 0 = browser default; positive int = nth voice from
                 window.speechSynthesis.getVoices() sorted by name.
    rate:        0.5 (slow) – 1.5 (fast). 0.85 is comfortable for fluency work.
    """
    safe = (
        text
        .replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", " ")
        .replace("\r", "")
    )
    return f"""
<script>
(function() {{
  var KEY = "tts_{component_key}";
  if (window[KEY]) return;
  window[KEY] = true;

  function speak(voices) {{
    var utt = new SpeechSynthesisUtterance("{safe}");
    utt.rate  = {rate};
    utt.pitch = 1.0;
    if (voices && voices.length > {voice_index}) {{
      utt.voice = voices[{voice_index}];
    }}
    window.speechSynthesis.cancel();
    window.speechSynthesis.speak(utt);
  }}

  var voices = window.speechSynthesis.getVoices();
  if (voices.length > 0) {{
    speak(voices);
  }} else {{
    window.speechSynthesis.addEventListener("voiceschanged", function() {{
      speak(window.speechSynthesis.getVoices());
    }}, {{ once: true }});
  }}
}})();
</script>
<div style="height:0;overflow:hidden"></div>
"""


def render_tts_button(
    text: str,
    key: str = "tts",
    label: str = "🔊 Speak",
    help_text: str = "Read the rebuilt sentence aloud using your browser's voice engine.",
) -> None:
    """
    Render a 'Speak' button. When clicked, injects JS to speak *text* via
    window.speechSynthesis. Uses rate + voice index from session state
    (populated by render_voice_settings()).
    """
    if not text or not text.strip():
        return

    rate        = float(st.session_state.get("tts_rate", 0.90))
    voice_index = int(st.session_state.get("tts_voice_index", 0))

    ctr_key = f"{key}_ctr"
    if ctr_key not in st.session_state:
        st.session_state[ctr_key] = 0

    if st.button(label, key=f"{key}_btn", help=help_text, use_container_width=False):
        st.session_state[ctr_key] += 1

    if st.session_state[ctr_key] > 0:
        component_key = f"{key}_{st.session_state[ctr_key]}"
        st.iframe(
            _tts_html(text, rate, voice_index, component_key),
            height=0,
        )


def render_stop_button(key: str = "tts_stop") -> None:
    """Inject a JS snippet to stop any ongoing speech."""
    if st.button("⏹ Stop", key=key, help="Stop speaking"):
        st.iframe(
            "<script>window.speechSynthesis && window.speechSynthesis.cancel();</script>"
            '<div style="height:0"></div>',
            height=0,
        )


# ── Voice settings (sidebar) ─────────────────────────────────────────────────

_VOICE_LOADER_HTML = """
<div id="vl-status" style="font-size:.78rem;color:#5a7096;font-family:'DM Sans',sans-serif">
  Loading available voices…
</div>
<select id="vl-select"
  style="width:100%;margin-top:.35rem;padding:.32rem .6rem;
         border:1.5px solid #c3daf7;border-radius:8px;
         font-family:'DM Sans',sans-serif;font-size:.85rem;
         background:#fff;color:#1a2740">
</select>
<script>
(function() {
  function populate() {
    var voices = window.speechSynthesis.getVoices();
    var sel = document.getElementById("vl-select");
    var status = document.getElementById("vl-status");
    if (!voices.length) { return; }
    sel.innerHTML = "";
    voices.forEach(function(v, i) {
      var opt = document.createElement("option");
      opt.value = i;
      opt.textContent = v.name + " (" + v.lang + ")";
      sel.appendChild(opt);
    });
    status.textContent = voices.length + " voice(s) available on this device.";
    sel.addEventListener("change", function() {
      window.parent.postMessage({type:"stts_voice",index:parseInt(sel.value)}, "*");
    });
  }
  if (window.speechSynthesis.getVoices().length) { populate(); }
  else { window.speechSynthesis.addEventListener("voiceschanged", populate, {once:true}); }
})();
</script>
"""


def render_voice_settings(location=None) -> None:
    """
    Render TTS settings (rate slider + voice picker) in *location* (defaults
    to st.sidebar). Voice picker is a passthrough info widget — the index is
    manually entered via a number input because Streamlit can't receive
    postMessage from components without a custom component.
    """
    target = location or st.sidebar

    with target:
        st.markdown("#### 🔊 Voice Settings")

        st.session_state.tts_rate = st.slider(
            "Speaking rate",
            min_value=0.5,
            max_value=1.5,
            value=float(st.session_state.get("tts_rate", 0.90)),
            step=0.05,
            help="1.0 = normal speed. Try 0.85 for clearer output.",
            key="_tts_rate_slider",
        )

        st.caption("Available voices on your device:")
        st.iframe(_VOICE_LOADER_HTML, height=80)

        st.session_state.tts_voice_index = st.number_input(
            "Voice index (from list above)",
            min_value=0,
            max_value=99,
            value=int(st.session_state.get("tts_voice_index", 0)),
            step=1,
            help="Enter the number next to your preferred voice (0 = browser default).",
            key="_tts_voice_num",
        )
