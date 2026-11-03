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

    clean_user = username.strip() if username else ""
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
        st.warning("You must be signed in to view this page.", icon=":material/lock:")
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
    role_icon = {"doctor": "🩺", "pharmacist": "💊", "admin": "⚙️"}.get(role or "", "👤")
    access = "Read-only access" if role == "pharmacist" else "Read & write access"
    with st.sidebar:
        st.markdown(
            f'<div style="background:#13304D;border:1px solid #1E3A5F;border-radius:12px;'
            f'padding:0.75rem 0.9rem;margin:0.4rem 0 0.6rem 0">'
            f'<div style="font-size:0.72rem;color:#94A3B8;text-transform:uppercase;letter-spacing:0.05em">'
            f'Signed in</div>'
            f'<div style="font-weight:700;color:#F8FAFC;margin-top:0.15rem">{role_icon} '
            f'{escape((role or "user").capitalize())}</div>'
            f'<div style="font-size:0.82rem;color:#CBD5E1">{escape(user or "")} · {access}</div></div>',
            unsafe_allow_html=True)
        if st.button("Log out", key="sidebar_logout_button", icon=":material/logout:", width="stretch"):
            logout()
