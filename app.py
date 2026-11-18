
import streamlit as st
import sqlite3
import os
import uuid
from pathlib import Path


try:
    from streamlit_mic_recorder import speech_to_text
    VOICE_AVAILABLE = True
except ImportError:
    VOICE_AVAILABLE = False

# =====================================
# CONFIGURATION
# =====================================

st.set_page_config(
    page_title="BREVINFLIX",
    page_icon="B",
    layout="wide"
)

BASE_DIR = Path(__file__).parent
MEDIA_DIR = BASE_DIR / "media"
MEDIA_DIR.mkdir(exist_ok=True)
VIDEO_DIR = MEDIA_DIR / "videos"
VIDEO_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = BASE_DIR / "brevinflix_new.db"

try:
    ADMIN_PASSWORD = st.secrets.get("ADMIN_PASSWORD", "")
except Exception:
    ADMIN_PASSWORD = ""

# =====================================
# CINEMATIC STREAMING DESIGN
# =====================================

st.markdown("""
<style>
:root {
    --navy: #071426;
    --navy-light: #102541;
    --gold: #d8b76a;
    --white: #f7f8fb;
    --muted: #b7c2d0;
}
.stApp {
    background: radial-gradient(ellipse at top, #173456 0%, #09182c 42%, #050d19 100%);
    color: var(--white);
}
header[data-testid="stHeader"] { background: rgba(5,13,25,.92); }
[data-testid="stSidebar"] {
    background: #071426;
    border-right: 1px solid rgba(216,183,106,.22);
}
[data-testid="stSidebar"] * { color: var(--white) !important; }
h1, h2, h3, h4 {
    color: var(--white) !important;
    font-weight: 750 !important;
    letter-spacing: .2px;
}
p, label, [data-testid="stMarkdownContainer"] { color: #dce4ef; }
.stButton button, .stFormSubmitButton button, .stLinkButton a {
    background: var(--gold);
    color: #101b2a !important;
    border: 1px solid var(--gold);
    border-radius: 22px;
    font-weight: 700;
    min-height: 40px;
    padding: 0 18px;
}
.stButton button:hover, .stFormSubmitButton button:hover, .stLinkButton a:hover {
    background: #f0d48d;
    border-color: #f0d48d;
    color: #101b2a !important;
}
input, textarea, [data-baseweb="select"] > div {
    border-radius: 10px !important;
}
[data-testid="stImage"] img {
    border-radius: 12px;
    box-shadow: 0 8px 24px rgba(0,0,0,.32);
}
hr { border-color: rgba(216,183,106,.22); }
div[data-testid="stMetric"] {
    background: #102541;
    padding: 14px;
    border-radius: 12px;
    border: 1px solid rgba(216,183,106,.2);
}
[data-testid="stVerticalBlock"] > div:has(> [data-testid="stImage"]) {
    border-radius: 14px;
}
</style>
""", unsafe_allow_html=True)

# =====================================
# DATABASE
# =====================================

def connect():
    return sqlite3.connect(DB_PATH)

def setup_database():
    with connect() as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS movies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            category TEXT NOT NULL,
            genre TEXT,
            year TEXT,
            description TEXT,
            poster TEXT,
            trailer TEXT,
            video_url TEXT DEFAULT '',
            is_premium INTEGER DEFAULT 0
        )
        """)

        columns = [
            row[1] for row in
            conn.execute("PRAGMA table_info(movies)").fetchall()
        ]

        if "video_url" not in columns:
            conn.execute(
                "ALTER TABLE movies ADD COLUMN video_url TEXT DEFAULT ''"
            )

        if "is_premium" not in columns:
            conn.execute(
                "ALTER TABLE movies ADD COLUMN is_premium INTEGER DEFAULT 0"
            )

setup_database()

# =====================================
# MOVIE FUNCTIONS
# =====================================

def get_movies(category=None):
    with connect() as conn:
        if category:
            rows = conn.execute(
                """SELECT * FROM movies
                WHERE category=?
                ORDER BY id DESC""",
                (category,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM movies ORDER BY id DESC"
            ).fetchall()

    return [
        {
            "id": r[0],
            "title": r[1],
            "category": r[2],
            "genre": r[3],
            "year": r[4],
            "description": r[5],
            "poster": r[6],
            "trailer": r[7],
            "video_url": r[8],
            "is_premium": r[9]
        }
        for r in rows
    ]

def add_movie(
    title, category, genre, year,
    description, poster, trailer,
    video_url, is_premium
):
    with connect() as conn:
        conn.execute("""
        INSERT INTO movies
        (title, category, genre, year, description,
         poster, trailer, video_url, is_premium)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            title, category, genre, year,
            description, poster, trailer,
            video_url, is_premium
        ))

def delete_movie(movie_id):
    with connect() as conn:
        conn.execute(
            "DELETE FROM movies WHERE id=?",
            (movie_id,)
        )

# =====================================
# SESSION SETTINGS
# =====================================

if "favourites" not in st.session_state:
    st.session_state.favourites = []

if "selected_movie" not in st.session_state:
    st.session_state.selected_movie = None

if "membership" not in st.session_state:
    st.session_state.membership = "Free"

if "search_query" not in st.session_state:
    st.session_state.search_query = ""

if "last_voice" not in st.session_state:
    st.session_state.last_voice = ""

# =====================================
# HEADER
# =====================================

st.markdown("""
<div style="padding: 10px 0 18px 0;">
  <div style="font-size:13px;letter-spacing:5px;color:#d8b76a;font-weight:700;">YOUR ENTERTAINMENT DESTINATION</div>
  <div style="font-size:42px;line-height:1.15;font-weight:850;color:#ffffff;letter-spacing:1px;">BREVINFLIX</div>
  <div style="font-size:16px;color:#b7c2d0;margin-top:7px;">Stories worth staying in for.</div>
</div>
<div style="height:1px;background:linear-gradient(90deg,rgba(216,183,106,.75),rgba(216,183,106,0));margin-bottom:22px;"></div>
""", unsafe_allow_html=True)

# =====================================
# NAVIGATION
# =====================================

page = st.sidebar.radio(
    "MENU",
    [
        "Home",
        "Movies",
        "TV Shows",
        "Favourites",
        "Membership",
        "Admin"
    ]
)

st.sidebar.markdown("---")
st.sidebar.markdown("### YOUR ACCOUNT")
st.sidebar.write("Plan:", st.session_state.membership)

# =====================================
# VOICE SEARCH
# =====================================

st.subheader("Find your next movie")

if VOICE_AVAILABLE:
    voice_text = speech_to_text(
        language="en",
        start_prompt="Start voice search",
        stop_prompt="Stop recording",
        just_once=True,
        key="voice_search"
    )

    if voice_text and voice_text != st.session_state.last_voice:
        st.session_state.search_query = voice_text
        st.session_state.last_voice = voice_text
else:
    st.caption("Voice search is unavailable. Install streamlit-mic-recorder.")

search = st.text_input(
    "Search movies, genres or descriptions",
    placeholder="Try Moana, action, comedy...",
    key="search_query"
)

# =====================================
# SEARCH RESULTS
# =====================================

all_movies = get_movies()

if search:
    all_movies = [
        m for m in all_movies
        if search.lower() in m["title"].lower()
        or search.lower() in (m["genre"] or "").lower()
        or search.lower() in (m["description"] or "").lower()
    ]

# =====================================
# MOVIE DISPLAY
# =====================================

def show_movies(movie_list):

    if not movie_list:
        st.info("No movies found. Try another search.")
        return

    columns = st.columns(4)

    for index, movie in enumerate(movie_list):

        with columns[index % 4]:

            poster = movie["poster"]

            if poster and os.path.isfile(poster):
                st.image(
                    poster,
                    use_container_width=True
                )
            else:
                st.markdown(
                    "**Poster unavailable**"
                )

            st.markdown("**" + movie["title"] + "**")

            st.caption(
                str(movie["year"] or "") +
                "  |  " +
                str(movie["genre"] or "")
            )

            if movie["is_premium"]:
                st.caption("PREMIUM")

            if st.button(
                "View details",
                key=f"view_{movie['id']}"
            ):
                st.session_state.selected_movie = movie

            fav_label = (
                "Remove favourite"
                if movie["id"] in st.session_state.favourites
                else "Add to favourites"
            )

            if st.button(
                fav_label,
                key=f"fav_{movie['id']}"
            ):
                if movie["id"] in st.session_state.favourites:
                    st.session_state.favourites.remove(movie["id"])
                else:
                    st.session_state.favourites.append(movie["id"])

                st.rerun()

# =====================================
# MOVIE DETAILS
# =====================================

if st.session_state.selected_movie:

    movie = st.session_state.selected_movie

    st.markdown("---")
    st.header(movie["title"])

    if movie["poster"] and os.path.isfile(movie["poster"]):
        st.image(movie["poster"], width=250)

    st.write("**Category:**", movie["category"])
    st.write("**Genre:**", movie["genre"])
    st.write("**Year:**", movie["year"])

    st.write(movie["description"])

    can_watch = (
        not movie["is_premium"]
        or st.session_state.membership in ["Premium", "VIP"]
    )

    if movie["is_premium"] and not can_watch:
        st.warning("This title is available on the Premium or VIP demo plan.")
        st.info("Visit Membership to explore the available plans.")

    elif movie["video_url"]:
        video_value = movie["video_url"]
        if isinstance(video_value, str) and os.path.isfile(video_value):
            st.video(video_value)
        elif isinstance(video_value, str) and video_value.startswith(("https://", "http://")):
            st.video(video_value)
        else:
            st.warning(
                "This uploaded video file is not available on the server. "
                "On Streamlit Cloud, files saved to the app's local disk can "
                "disappear after a restart or redeployment. Re-upload the video "
                "or use a permanent licensed video URL."
            )

    if movie["trailer"]:
        st.link_button(
            "Watch official trailer",
            movie["trailer"]
        )

    if st.button("Close details"):
        st.session_state.selected_movie = None
        st.rerun()

# =====================================
# HOME
# =====================================

if page == "Home":

    st.markdown("""
    <div style="background:linear-gradient(115deg,#173456 0%,#0b1a30 62%,#071426 100%);padding:38px 32px;border-radius:18px;border:1px solid rgba(216,183,106,.35);box-shadow:0 14px 35px rgba(0,0,0,.28);">
      <div style="font-size:12px;letter-spacing:4px;color:#d8b76a;font-weight:700;">FEATURED COLLECTION</div>
      <h2 style="color:#ffffff;margin:12px 0 8px;font-size:32px;">Welcome to BREVINFLIX</h2>
      <p style="color:#d5dfeb;margin:0;font-size:16px;">Discover great movies and TV shows, all in one place.</p>
    </div>
    """, unsafe_allow_html=True)

    st.subheader("Latest additions")
    show_movies(all_movies[:8])

    st.subheader("Explore")
    st.write(
        "Discover movies, browse TV shows and explore membership options."
    )

# =====================================
# MOVIES
# =====================================

elif page == "Movies":

    st.header("Movies")

    results = [
        m for m in all_movies
        if m["category"] == "Movie"
    ]

    show_movies(results)

# =====================================
# TV SHOWS
# =====================================

elif page == "TV Shows":

    st.header("TV Shows")

    results = [
        m for m in all_movies
        if m["category"] == "TV Show"
    ]

    show_movies(results)

# =====================================
# FAVOURITES
# =====================================

elif page == "Favourites":

    st.header("My Favourites")

    results = [
        m for m in get_movies()
        if m["id"] in st.session_state.favourites
    ]

    show_movies(results)

# =====================================
# MEMBERSHIP
# =====================================

elif page == "Membership":

    st.header("Membership")
    st.write("Choose a demo viewing plan. No payments are collected in this app.")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.subheader("Free")
        st.markdown("### KSh 0")
        st.write("Browse the catalogue")
        st.write("Search and save favourites")
        if st.button("Choose Free", key="free"):
            st.session_state.membership = "Free"
            st.success("Free plan selected.")
            st.rerun()

    with col2:
        st.subheader("Premium")
        st.markdown("### Demo plan")
        st.write("Access premium-marked titles")
        if st.button("Choose Premium", key="premium"):
            st.session_state.membership = "Premium"
            st.success("Premium demo plan selected.")
            st.rerun()

    with col3:
        st.subheader("VIP")
        st.markdown("### Demo plan")
        st.write("Access premium-marked titles")
        st.write("VIP demo label")
        if st.button("Choose VIP", key="vip"):
            st.session_state.membership = "VIP"
            st.success("VIP demo plan selected.")
            st.rerun()

    st.caption("Membership choices are for demonstration only. There is no checkout or payment connection.")


# =====================================
# ADMIN
# =====================================

elif page == "Admin":

    st.header("Admin dashboard")

    if not ADMIN_PASSWORD:
        st.error(
            "Admin password is not configured. "
            "Set ADMIN_PASSWORD in Streamlit Secrets."
        )

    else:

        password = st.text_input(
            "Admin password",
            type="password"
        )

        if password == ADMIN_PASSWORD:

            st.success("Admin access granted!")

            st.subheader("Add a movie or TV show")

            with st.form("add_movie_form"):

                title = st.text_input("Movie title")

                category = st.selectbox(
                    "Category",
                    ["Movie", "TV Show"]
                )

                genre = st.text_input("Genre")
                year = st.text_input("Release year")

                description = st.text_area(
                    "Movie description"
                )

                poster = st.file_uploader(
                    "Upload movie poster",
                    type=["jpg", "jpeg", "png", "webp"],
                    help="Choose a JPG, PNG or WEBP poster from your phone or computer."
                )

                uploaded_video = st.file_uploader(
                    "Upload movie video from your phone or computer (optional)",
                    type=["mp4", "mov", "m4v", "webm", "mkv"],
                    help=(
                        "The app is configured for uploads up to 2 GB. "
                        "Large uploads may still fail because Streamlit Cloud "
                        "has platform, memory and temporary-storage limits. "
                        "Only upload videos you own or have permission to distribute."
                    )
                )

                trailer = st.text_input(
                    "Official trailer link"
                )

                video_url = st.text_input(
                    "Licensed video URL (optional; used if no video file is uploaded)"
                )

                is_premium = st.checkbox(
                    "Mark as Premium content"
                )

                submitted = st.form_submit_button(
                    "Add to BREVINFLIX"
                )

                if submitted:

                    if not title.strip():
                        st.error("Enter a movie title.")

                    elif not poster:
                        st.error("Upload a poster.")

                    else:
                        # Save the poster.
                        poster_extension = Path(poster.name).suffix.lower()
                        poster_filename = str(uuid.uuid4()) + poster_extension
                        poster_path = MEDIA_DIR / poster_filename

                        with open(poster_path, "wb") as poster_file:
                            poster_file.write(poster.getbuffer())

                        # Save an uploaded video locally, or keep the supplied URL.
                        # Local files on Streamlit Cloud are temporary and are not
                        # a permanent video-storage solution.
                        saved_video_value = video_url.strip()

                        if uploaded_video is not None:
                            video_extension = Path(uploaded_video.name).suffix.lower()
                            video_filename = str(uuid.uuid4()) + video_extension
                            video_path = VIDEO_DIR / video_filename

                            uploaded_video.seek(0)
                            with open(video_path, "wb") as video_file:
                                video_file.write(uploaded_video.getbuffer())

                            saved_video_value = str(video_path)

                        add_movie(
                            title.strip(),
                            category,
                            genre,
                            year,
                            description,
                            str(poster_path),
                            trailer.strip(),
                            saved_video_value,
                            int(is_premium)
                        )

                        st.success(
                            title + " added successfully!"
                        )

                        st.rerun()

            st.markdown("---")

            st.subheader("Manage movies")

            for movie in get_movies():

                col1, col2 = st.columns([4, 1])

                with col1:
                    st.write(
                        movie["title"] +
                        " (" + movie["category"] + ")"
                    )

                with col2:

                    if st.button(
                        "Delete",
                        key=f"delete_{movie['id']}"
                    ):

                        delete_movie(movie["id"])

                        if (
                            movie["poster"]
                            and os.path.isfile(movie["poster"])
                        ):
                            os.remove(movie["poster"])

                        video_value = movie.get("video_url") or ""
                        if video_value and os.path.isfile(video_value):
                            try:
                                video_real = os.path.realpath(video_value)
                                video_root = os.path.realpath(VIDEO_DIR)
                                if os.path.commonpath([video_real, video_root]) == video_root:
                                    os.remove(video_real)
                            except (OSError, ValueError):
                                pass

                        st.rerun()

        elif password:
            st.error("Incorrect admin password.")

# =====================================
# FOOTER
# =====================================

st.markdown("---")

st.markdown("""
<div style="text-align:center;padding:22px;color:#b7c2d0;">
<div style="font-size:18px;letter-spacing:3px;color:#d8b76a;font-weight:800;">BREVINFLIX</div>
<div style="margin-top:7px;font-size:13px;">Movies. TV Shows. Great stories.</div>
</div>
""", unsafe_allow_html=True)
