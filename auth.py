"""
auth.py — Login / Register screen for Speech AI.

Call  require_auth()  at the very top of app.py (after set_page_config).
It uses st.stop() to halt rendering until the user is authenticated, so
everything that comes after require_auth() is the protected app.

Session state keys set after successful login:
  st.session_state.authenticated  = True
  st.session_state.current_user   = "<username>"
"""

import streamlit as st
from user_store import list_users, register_user, verify_user, load_profile


# ── CSS injected only for the auth screen ─────────────────────────────────────
_AUTH_CSS = """
<style>
/* ── Auth overlay ── */
.auth-root {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    min-height: 78vh;
    padding: 1rem;
}

.auth-card {
    background: #fff;
    border: 1.5px solid #d4e8f8;
    border-radius: 22px;
    padding: 2.4rem 2.6rem 2rem;
    width: 100%;
    max-width: 440px;
    box-shadow: 0 8px 40px rgba(75,145,220,.11);
    position: relative;
}

.auth-logo {
    text-align: center;
    margin-bottom: 1.3rem;
}

.auth-logo h1 {
    font-family: 'DM Serif Display', serif;
    font-size: 2.1rem;
    color: #1a2740;
    margin: 0 0 .15rem;
    letter-spacing: -.4px;
}

.auth-logo h1 span { color: #f57c2b; }

.auth-logo p {
    font-size: .83rem;
    color: #5a7096;
    font-weight: 300;
    margin: 0;
}

.auth-tab-row {
    display: flex;
    gap: .5rem;
    margin-bottom: 1.4rem;
}

.auth-divider {
    height: 1px;
    background: #deeaf7;
    margin: 1.1rem 0;
}

.auth-footer {
    text-align: center;
    font-size: .75rem;
    color: #8aaccb;
    margin-top: .7rem;
}

/* Make Streamlit labels feel native inside the card */
div[data-testid="stSelectbox"] label,
div[data-testid="stTextInput"] label {
    font-size: .78rem !important;
    font-weight: 700 !important;
    color: #3d6ea8 !important;
    letter-spacing: .3px !important;
    text-transform: uppercase !important;
}
</style>
"""


def _inject_fonts() -> None:
    st.markdown(
        '<link href="https://fonts.googleapis.com/css2?family=DM+Serif+Display'
        '&family=DM+Sans:wght@300;400;500;600&display=swap" rel="stylesheet">',
        unsafe_allow_html=True,
    )


def _load_user_into_session(username: str) -> None:
    """Pull the user's phoneme profile into session state after login."""
    profile = load_profile(username)
    prefs = dict(profile["preferences"])
    prefs.setdefault("allowlist_words", [])
    prefs.setdefault("rephrase_enabled", False)
    st.session_state.stutter_patterns    = profile["stutter_patterns"]
    st.session_state.blocked_words       = profile["blocked_words"]
    st.session_state.custom_replacements = profile["custom_replacements"]
    st.session_state.preferences         = prefs
    st.session_state.allowlist_words     = list(prefs.get("allowlist_words", []))
    st.session_state.rephrase_enabled    = bool(prefs.get("rephrase_enabled", False))


# ── public entry point ────────────────────────────────────────────────────────

def require_auth() -> None:
    """
    Render the login/register screen and call st.stop() until auth succeeds.
    After this returns, st.session_state.current_user is set and the caller
    can safely render the protected application.
    """
    _inject_fonts()

    # Already authenticated in this session?
    if st.session_state.get("authenticated"):
        return

    st.markdown(_AUTH_CSS, unsafe_allow_html=True)

    # Centre the card via Streamlit columns
    _, mid, _ = st.columns([1, 2.2, 1])
    with mid:
        st.markdown("""
<div class="auth-logo">
  <h1>Speech <span>AI</span></h1>
  <p>Grammar correction · SBERT semantic firewall · Stutter assistance</p>
</div>
""", unsafe_allow_html=True)

        # ── Tab selector ──────────────────────────────────────────────────────
        tab_choice = st.radio(
            "auth_mode",
            ["🔑  Login", "✚  Register"],
            horizontal=True,
            label_visibility="collapsed",
        )

        st.markdown("<div style='height:.3rem'></div>", unsafe_allow_html=True)

        if tab_choice == "🔑  Login":
            _render_login()
        else:
            _render_register()

        st.markdown("""
<div class="auth-footer">
  Speech AI · Stutter Assistance System · NUST SEECS
</div>""", unsafe_allow_html=True)

    # Block any further rendering until login succeeds
    st.stop()


# ── sub-screens ───────────────────────────────────────────────────────────────

def _render_login() -> None:
    users = list_users()

    if not users:
        st.info("No accounts yet — switch to **Register** to create the first one.", icon="ℹ️")
        return

    with st.container():
        username = st.selectbox(
            "Username",
            options=users,
            help="Select your account from the dropdown.",
        )

        password = st.text_input(
            "Password",
            type="password",
            placeholder="Enter your password",
        )

        col_btn, _ = st.columns([1, 1])
        with col_btn:
            login_clicked = st.button(
                "Login →",
                use_container_width=True,
                type="primary",
            )

    if login_clicked:
        if not password:
            st.error("Please enter your password.")
            return

        ok, msg = verify_user(username, password)
        if ok:
            st.session_state.authenticated = True
            st.session_state.current_user  = username
            _load_user_into_session(username)
            st.success(f"Welcome back, **{username}**! Loading your profile…")
            st.rerun()
        else:
            st.error(f"Login failed: {msg}")


def _render_register() -> None:
    with st.container():
        new_username = st.text_input(
            "Choose a username",
            placeholder="e.g.  alice_s  (letters, numbers, _ -)  ",
        )

        new_pass = st.text_input(
            "Choose a password",
            type="password",
            placeholder="Minimum 4 characters",
        )

        confirm_pass = st.text_input(
            "Confirm password",
            type="password",
            placeholder="Re-enter your password",
        )

        st.markdown(
            '<div style="font-size:.77rem;color:#8aaccb;margin:.25rem 0 .55rem">'
            'You can add your phoneme / stutter profile after logging in.</div>',
            unsafe_allow_html=True,
        )

        col_btn, _ = st.columns([1, 1])
        with col_btn:
            reg_clicked = st.button(
                "Create account →",
                use_container_width=True,
                type="primary",
            )

    if reg_clicked:
        if not new_username.strip():
            st.error("Username cannot be empty.")
            return
        if new_pass != confirm_pass:
            st.error("Passwords do not match.")
            return

        ok, msg = register_user(new_username.strip(), new_pass)
        if ok:
            # Auto-login after registration
            st.session_state.authenticated = True
            st.session_state.current_user  = new_username.strip().lower()
            _load_user_into_session(new_username.strip().lower())
            st.success(f"Account **{new_username.strip().lower()}** created! Logging you in…")
            st.rerun()
        else:
            st.error(f"Registration failed: {msg}")
