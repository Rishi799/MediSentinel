"""Session state and role-based access management for MediSentinel Streamlit app."""

from html import escape

import psycopg
import streamlit as st

from medisentinel import db

# Keys used in st.session_state
SESSION_CONN = "db_conn"
SESSION_ROLE = "user_role"
SESSION_USERNAME = "username"


def init_session() -> None:
    """Initialize session state keys if they are not already present."""
    if SESSION_CONN not in st.session_state:
        st.session_state[SESSION_CONN] = None
    if SESSION_ROLE not in st.session_state:
        st.session_state[SESSION_ROLE] = None
    if SESSION_USERNAME not in st.session_state:
        st.session_state[SESSION_USERNAME] = None


def is_logged_in() -> bool:
    """Return True if an active, open database connection exists in session state."""
    init_session()
    conn = st.session_state.get(SESSION_CONN)
    if conn is None:
        return False
    if getattr(conn, "closed", False):
        st.session_state[SESSION_CONN] = None
        st.session_state[SESSION_ROLE] = None
        st.session_state[SESSION_USERNAME] = None
        return False
    return True


def get_connection():
    """Return the active psycopg connection or None if not logged in."""
    if not is_logged_in():
        return None
    return st.session_state.get(SESSION_CONN)


def get_role() -> str | None:
    """Return the normalized role string ('doctor', 'pharmacist', 'admin') or None."""
    if not is_logged_in():
        return None
    return st.session_state.get(SESSION_ROLE)


def get_username() -> str | None:
    """Return the logged-in username (e.g. 'ms_doctor') or None."""
    if not is_logged_in():
        return None
    return st.session_state.get(SESSION_USERNAME)


def can_write() -> bool:
    """Return True if the current user role is authorized to perform write operations.

    Doctors and admins have write access; pharmacists have read-only access.
    """
    return get_role() in ("doctor", "admin")


def login(username: str, password: str) -> tuple[bool, str | None]:
    """Attempt login via medisentinel.db.connect.

    Returns:
        (True, None) on success.
        (False, error_message) on failure.
    Never exposes internal system or database error details on bad credentials.
    """
    init_session()
    # Close any existing active connection
    logout(rerun=False)

    clean_user = username.strip().lower() if username else ""
    if clean_user in ("doctor", "pharmacist", "admin"):
        clean_user = "ms_" + clean_user  # short form of the role login
    password = password.strip() if password else ""  # copied passwords often carry a space or newline
    if not clean_user or not password:
        return False, "Please enter both username and password."

    try:
        conn = db.connect(clean_user, password)
        role = db.role_of(conn)
        st.session_state[SESSION_CONN] = conn
        st.session_state[SESSION_ROLE] = role
        st.session_state[SESSION_USERNAME] = clean_user
        return True, None
    except psycopg.OperationalError:
        return False, "Invalid username or password"
    except Exception:
        return False, "Database connection failed. Please ensure PostgreSQL is running."


def logout(rerun: bool = True) -> None:
    """Close the active database connection and reset the session state."""
    init_session()
    conn = st.session_state.get(SESSION_CONN)
    if conn is not None and not getattr(conn, "closed", False):
        try:
            conn.close()
        except Exception:
            pass
    st.session_state[SESSION_CONN] = None
    st.session_state[SESSION_ROLE] = None
    st.session_state[SESSION_USERNAME] = None
    if rerun:
        st.rerun()


def require_login():
    """Guard function: stops page execution with an alert if the user is not authenticated.

    Returns the active database connection when logged in.
    """
    if not is_logged_in():
        st.warning("Sign in to view this page.", icon=":material/lock:")
        st.stop()
    return st.session_state[SESSION_CONN]


def require_role(*roles: str):
    """Guard function: stops page execution if the logged-in role is not in the allowed list."""
    conn = require_login()
    role = get_role()
    if role not in roles:
        st.error("⛔ **Access Denied**: Your current role does not have permission to view or use this page.")
        st.caption(f"Logged in as: **{role}** · Required role: {', '.join(roles)}")
        st.stop()
    return conn


def render_sidebar_status() -> None:
    """Render consistent session info and a logout button in the Streamlit sidebar."""
    if not is_logged_in():
        return
    role = get_role()
    user = get_username()
    title = {"doctor": "Doctor", "pharmacist": "Pharmacist", "admin": "Administrator"}.get(role or "", "User")
    access = "Read-only" if role == "pharmacist" else "Read & write"
    with st.sidebar:
        st.markdown(
            f'<div class="ms-account"><div class="ms-avatar">{escape(title[:2].upper())}</div>'
            f'<div><div class="ms-account-name">{escape(title)}</div>'
            f'<div class="ms-account-meta">{escape(user or "")} · {access}</div></div></div>',
            unsafe_allow_html=True)
        if st.button("Sign out", key="sidebar_logout_button", icon=":material/logout:", width="stretch"):
            logout()
        pg_ok = not getattr(get_connection(), "closed", True)
        mongo_ok = _mongo_reachable()
        rows = [("PostgreSQL", pg_ok, "Connected" if pg_ok else "Offline"),
                ("MongoDB", mongo_ok, "Connected" if mongo_ok else "Offline")]
        status = "".join(
            f'<div class="ms-status-row"><span class="ms-status-dot" style="background:{"#17B26A" if ok else "#F04438"}">'
            f'</span>{name}<span class="ms-status-val">{text}</span></div>' for name, ok, text in rows)
        st.markdown(f'<div class="ms-status"><div class="ms-status-title">System status</div>{status}'
                    f'<div class="ms-status-note">Every prescription is checked by the database trigger; '
                    f'permissions are enforced by PostgreSQL.</div></div>', unsafe_allow_html=True)


@st.cache_data(ttl=30, show_spinner=False)
def _mongo_reachable() -> bool:
    """Quick MongoDB ping for the status panel (cached for 30 s)."""
    from pymongo import MongoClient
    from medisentinel import config
    try:
        client = MongoClient(config.MONGO_URI, serverSelectionTimeoutMS=800)
        client.admin.command("ping")
        client.close()
        return True
    except Exception:
        return False
