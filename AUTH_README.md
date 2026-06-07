# Speech AI — Multi-User Auth

## New files

| File | Purpose |
|------|---------|
| `user_store.py` | All user CRUD (file-based). Swap internals for SQLite/Postgres later without touching the rest. |
| `auth.py` | Login / Register Streamlit screen. Call `require_auth()` at the top of `app.py`. |
| `users/` | One JSON per user. Never committed to version control (add to `.gitignore`). |
| `users/default.json` | Auto-generated migration of the old `user_prefs.json`. Password: **speech** |

## User JSON schema

```json
{
  "username": "alice",
  "password_hash": "<sha256 hex>",
  "phoneme_profile": {
    "stutter_patterns": ["str", "pr"],
    "blocked_words": ["present"]
  },
  "custom_replacements": {},
  "preferences": {}
}
```

## How it works

1. `app.py` calls `migrate_legacy_prefs()` at startup → copies `user_prefs.json`
   into `users/default.json` (no-op if already done).
2. `require_auth()` renders the Login/Register card and calls `st.stop()`.
   Nothing else in `app.py` runs until login succeeds.
3. After login, `stutter_patterns` and `blocked_words` are loaded into
   `st.session_state` from the user's JSON.
4. Any phoneme profile edits call `save_profile()` which writes back to
   **only that user's** JSON file.
5. Logout clears all session state and re-triggers `require_auth()`.

## Upgrading password hashing

`user_store.py` uses SHA-256 for simplicity.  To switch to bcrypt:

```python
# pip install bcrypt
import bcrypt

def _hash_password(p):   return bcrypt.hashpw(p.encode(), bcrypt.gensalt()).decode()
def _check_password(p, h): return bcrypt.checkpw(p.encode(), h.encode())
```

Replace those two functions in `user_store.py` — nothing else changes.

## Upgrading to a database

Replace `_read()`, `_write()`, `list_users()` in `user_store.py` with
SQL queries.  The public API (`register_user`, `verify_user`, `load_profile`,
`save_profile`) stays identical, so `auth.py` and `app.py` need zero changes.

## .gitignore

```
users/
user_prefs.json
.cache/
```
