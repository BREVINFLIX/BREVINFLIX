import streamlit as st
st.markdown(
    '<meta name="google-site-verification" content="Z41xRLdLVq0nCp4U4ldVdDXPD8xfep6HaInWZylIVa8" />',
    unsafe_allow_html=True
)
import streamlit as st
import sqlite3
import uuid
from pathlib import Path

# =====================================
# BREVINFLIX CONFIGURATION
# =====================================

BASE_DIR = Path(__file__).resolve().parent
MEDIA_DIR = BASE_DIR / "media"
MOVIE_DIR = MEDIA_DIR / "Movies"
POSTER_DIR = MEDIA_DIR / "Posters"
DB_PATH = BASE_DIR / "movies.db"

ADMIN_PASSWORD = st.secrets["ADMIN_PASSWORD"]

for folder in [MOVIE_DIR, POSTER_DIR]:
    folder.mkdir(parents=True, exist_ok=True)

st.set_page_config(
    page_title="BREVINFLIX",
    page_icon="🎬",
    layout="wide"
)

# =====================================
# DATABASE
# =====================================

def initialize_database():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS movies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                genre TEXT,
                year INTEGER,
                description TEXT,
                content_type TEXT,
                poster TEXT,
                video TEXT
            )
        """)

def get_movies(content_type=None):
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row

        if content_type:
            rows = conn.execute(
                "SELECT * FROM movies WHERE content_type=? ORDER BY id DESC",
                (content_type,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM movies ORDER BY id DESC"
            ).fetchall()

        return [dict(row) for row in rows]

def save_movie(title, genre, year, description,
               content_type, poster, video):

    poster_name = f"{uuid.uuid4().hex}{Path(poster.name).suffix.lower()}"
    video_name = f"{uuid.uuid4().hex}{Path(video.name).suffix.lower()}"

    (POSTER_DIR / poster_name).write_bytes(poster.getvalue())
    (MOVIE_DIR / video_name).write_bytes(video.getvalue())

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            INSERT INTO movies
            (title, genre, year, description,
             content_type, poster, video)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            title, genre, year, description,
            content_type, poster_name, video_name
        ))

def delete_movie(movie_id):
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row

        movie = conn.execute(
            "SELECT * FROM movies WHERE id=?",
            (movie_id,)
        ).fetchone()

        if movie:
            for folder, filename in [
                (POSTER_DIR, movie["poster"]),
                (MOVIE_DIR, movie["video"])
            ]:
                if filename:
                    path = folder / filename
                    if path.exists():
                        path.unlink()

            conn.execute(
                "DELETE FROM movies WHERE id=?",
                (movie_id,)
            )

initialize_database()

# =====================================
# SESSION
# =====================================

if "favourites" not in st.session_state:
    st.session_state.favourites = []

if "selected_movie" not in st.session_state:
    st.session_state.selected_movie = None

if "admin_authenticated" not in st.session_state:
    st.session_state.admin_authenticated = False

# =====================================
# DESIGN
# =====================================

st.markdown("""
<style>
.stApp {
    background: #050b18;
    color: white;
}

[data-testid="stSidebar"] {
    background: #071329;
}

h1 {
    color: #48a9ff !important;
    font-weight: 900;
}

h2, h3, p, label {
    color: white;
}

.hero {
    background: linear-gradient(100deg,#071329,#123b70,#071329);
    padding: 40px;
    border-radius: 18px;
    margin-bottom: 25px;
}

div.stButton > button {
    background: #0878d1;
    color: white;
    border: none;
    border-radius: 8px;
    width: 100%;
}

div.stButton > button:hover {
    background: #159aff;
    color: white;
}
</style>
""", unsafe_allow_html=True)

# =====================================
# SIDEBAR
# =====================================

st.sidebar.markdown("# 🔵 BREVINFLIX")
st.sidebar.caption("YOUR WORLD OF ENTERTAINMENT")

page = st.sidebar.radio(
    "NAVIGATION",
    [
        "Home",
        "Movies",
        "TV Shows",
        "My List",
        "Search",
        "Admin Dashboard",
        "About"
    ]
)

# =====================================
# HEADER
# =====================================

st.title("BREVINFLIX")
st.caption("STREAM YOUR WORLD.")

# =====================================
# MOVIE DISPLAY
# =====================================

def show_movies(movie_list):

    if not movie_list:
        st.info("No movies available yet.")
        return

    cols = st.columns(3)

    for i, movie in enumerate(movie_list):

        with cols[i % 3]:

            poster = movie.get("poster")

            if poster and (POSTER_DIR / poster).exists():
                st.image(
                    str(POSTER_DIR / poster),
                    use_container_width=True
                )
            else:
                st.markdown("🎬 Poster unavailable")

            st.subheader(movie["title"])

            st.caption(
                f'{movie.get("genre")} • {movie.get("year")}'
            )

            if st.button(
                "▶ WATCH NOW",
                key=f"watch_{page}_{movie['id']}"
            ):
                st.session_state.selected_movie = movie

            if st.button(
                "♡ ADD TO MY LIST",
                key=f"fav_{page}_{movie['id']}"
            ):
                if movie["id"] not in [
                    m["id"] for m in st.session_state.favourites
                ]:
                    st.session_state.favourites.append(movie)
                    st.success("Added to favourites!")
                else:
                    st.info("Already added.")

# =====================================
# HOME
# =====================================

if page == "Home":

    st.markdown("""
    <div class="hero">
        <h2>WELCOME TO BREVINFLIX</h2>
        <p>Discover movies and amazing entertainment.</p>
        <p>🎬 MOVIES • 📺 TV SHOWS • ⭐ ENTERTAINMENT</p>
    </div>
    """, unsafe_allow_html=True)

    st.header("🔥 Recently Added")

    show_movies(get_movies()[:6])

# =====================================
# MOVIES
# =====================================

elif page == "Movies":

    st.header("🎬 MOVIE LIBRARY")
    show_movies(get_movies("Movie"))

# =====================================
# TV SHOWS
# =====================================

elif page == "TV Shows":

    st.header("📺 TV SHOWS")
    show_movies(get_movies("TV Show"))

# =====================================
# MY LIST
# =====================================

elif page == "My List":

    st.header("❤️ MY FAVOURITES")
    show_movies(st.session_state.favourites)

# =====================================
# SEARCH
# =====================================

elif page == "Search":

    st.header("🔍 SEARCH BREVINFLIX")

    search = st.text_input("Search movies or genres")

    if search:
        results = [
            m for m in get_movies()
            if search.lower() in m["title"].lower()
            or search.lower() in (m["genre"] or "").lower()
        ]

        show_movies(results)
    else:
        st.info("Enter a movie title or genre.")

# =====================================
# ADMIN DASHBOARD
# =====================================

elif page == "Admin Dashboard":

    st.header("🔐 ADMIN DASHBOARD")

    if not st.session_state.admin_authenticated:

        password = st.text_input(
            "Admin Password",
            type="password"
        )

        if st.button("LOGIN"):

            if password == ADMIN_PASSWORD:
                st.session_state.admin_authenticated = True
                st.rerun()
            else:
                st.error("Incorrect password!")

    else:

        if st.button("LOG OUT"):
            st.session_state.admin_authenticated = False
            st.rerun()

        st.success("Administrator access granted!")

        content = get_movies()

        col1, col2, col3 = st.columns(3)
        col1.metric("Total Content", len(content))
        col2.metric("Movies", len([
            m for m in content if m["content_type"] == "Movie"
        ]))
        col3.metric("TV Shows", len([
            m for m in content if m["content_type"] == "TV Show"
        ]))

        st.divider()
        st.subheader("➕ ADD NEW MOVIE OR SHOW")

        with st.form("upload_form"):

            title = st.text_input("Title")

            content_type = st.selectbox(
                "Content Type",
                ["Movie", "TV Show"]
            )

            genre = st.selectbox(
                "Genre",
                [
                    "Action",
                    "Adventure",
                    "Animation",
                    "Comedy",
                    "Drama",
                    "Documentary",
                    "Fantasy",
                    "Horror",
                    "Romance",
                    "Science Fiction",
                    "Other"
                ]
            )

            year = st.number_input(
                "Release Year",
                min_value=1900,
                max_value=2100,
                value=2026
            )

            description = st.text_area("Description")

            poster = st.file_uploader(
                "Upload Movie Poster",
                type=["jpg", "jpeg", "png", "webp"]
            )

            video = st.file_uploader(
                "Upload Movie Video",
                type=["mp4", "mov", "m4v", "webm"]
            )

            submit = st.form_submit_button("SAVE TO BREVINFLIX")

            if submit:

                if not title.strip():
                    st.error("Please enter a title.")

                elif not poster:
                    st.error("Please upload a poster.")

                elif not video:
                    st.error("Please upload a video.")

                else:
                    try:
                        save_movie(
                            title.strip(),
                            genre,
                            int(year),
                            description,
                            content_type,
                            poster,
                            video
                        )

                        st.success("Movie uploaded successfully!")
                        st.rerun()

                    except Exception as error:
                        st.error(f"Upload failed: {error}")

        st.divider()
        st.subheader("🗂 MANAGE YOUR CONTENT")

        for movie in get_movies():

            with st.expander(movie["title"]):

                st.write(movie["description"])

                if st.button(
                    f"DELETE {movie['title']}",
                    key=f"delete_{movie['id']}"
                ):
                    delete_movie(movie["id"])

                    st.session_state.favourites = [
                        m for m in st.session_state.favourites
                        if m["id"] != movie["id"]
                    ]

                    if (
                        st.session_state.selected_movie
                        and st.session_state.selected_movie["id"]
                        == movie["id"]
                    ):
                        st.session_state.selected_movie = None

                    st.success("Deleted successfully!")
                    st.rerun()

# =====================================
# ABOUT
# =====================================

elif page == "About":

    st.header("ABOUT BREVINFLIX")

    st.write("""
    BREVINFLIX is your personal entertainment platform.

    Built with Python and Streamlit.

    Your local movie library is stored on your computer.
    """)

# =====================================
# VIDEO PLAYER
# =====================================

if st.session_state.selected_movie:

    movie = st.session_state.selected_movie

    st.divider()
    st.header("▶ NOW PLAYING")
    st.subheader(movie["title"])

    st.write(movie["description"])

    video = movie.get("video")

    if video and (MOVIE_DIR / video).exists():
        st.video(str(MOVIE_DIR / video))
    else:
        st.warning("Video unavailable.")

    if st.button("✖ CLOSE PLAYER"):
        st.session_state.selected_movie = None
        st.rerun()

# =====================================
# FOOTER
# =====================================

st.divider()
st.caption("BREVINFLIX © 2026 | YOUR WORLD OF ENTERTAINMENT")
