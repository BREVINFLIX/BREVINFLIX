
import streamlit as st
import sqlite3
import os
import uuid
import base64
from datetime import datetime
from pathlib import Path

import requests

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
    page_icon="­ƒÄ¼",
    layout="wide"
)

BASE_DIR = Path(__file__).parent
MEDIA_DIR = BASE_DIR / "media"
MEDIA_DIR.mkdir(exist_ok=True)

DB_PATH = BASE_DIR / "brevinflix_new.db"

try:
    ADMIN_PASSWORD = st.secrets.get("ADMIN_PASSWORD", "")
except Exception:
    ADMIN_PASSWORD = ""

# =====================================
# COLOURFUL DESIGN
# =====================================

st.markdown("""
<style>
.stApp {
    background: linear-gradient(
        135deg, #090018, #16052e, #071b38, #090018
    );
    color: white;
}

header[data-testid="stHeader"] {
    background: transparent;
}

h1 {
    color: #ff4fd8 !important;
    font-weight: 900 !important;
    text-shadow: 0 0 18px #a020f0;
}

h2 {
    color: #00e5ff !important;
    font-weight: 800 !important;
}

h3 {
    color: #ffd166 !important;
}

p, label {
    color: #f5f5ff;
}

[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #210044, #101d4b);
}

.stButton button {
    background: linear-gradient(
        90deg, #ff1744, #a020f0, #007bff
    );
    color: white;
    border: none;
    border-radius: 12px;
    font-weight: bold;
    min-height: 40px;
}

.stButton button:hover {
    background: linear-gradient(90deg, #ffd166, #ff4fd8);
    color: #090018;
}

input, textarea {
    background: #20143b !important;
    color: white !important;
    border: 1px solid #a020f0 !important;
    border-radius: 10px !important;
}

[data-testid="stImage"] {
    border-radius: 14px;
}

hr {
    border-color: #a020f0;
}

div[data-testid="stMetric"] {
    background: #21123c;
    padding: 15px;
    border-radius: 12px;
    border: 1px solid #a020f0;
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
# M-PESA DARAJA SANDBOX HELPERS
# =====================================

def get_mpesa_config():
    """Read sandbox credentials from Streamlit Secrets; never hard-code them."""
    try:
        return {
            "consumer_key": st.secrets.get("MPESA_CONSUMER_KEY", ""),
            "consumer_secret": st.secrets.get("MPESA_CONSUMER_SECRET", ""),
            "shortcode": st.secrets.get("MPESA_SHORTCODE", ""),
            "passkey": st.secrets.get("MPESA_PASSKEY", ""),
            "callback_url": st.secrets.get("MPESA_CALLBACK_URL", ""),
        }
    except Exception:
        return {
            "consumer_key": "", "consumer_secret": "",
            "shortcode": "", "passkey": "", "callback_url": ""
        }


def mpesa_access_token(config):
    response = requests.get(
        "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials",
        auth=(config["consumer_key"], config["consumer_secret"]),
        timeout=30,
    )
    response.raise_for_status()
    return response.json()["access_token"]


def normalize_kenyan_phone(phone):
    digits = "".join(ch for ch in phone if ch.isdigit())
    if digits.startswith("0") and len(digits) == 10:
        return "254" + digits[1:]
    if digits.startswith("254") and len(digits) == 12:
        return digits
    if digits.startswith("7") and len(digits) == 9:
        return "254" + digits
    raise ValueError("Enter a valid Kenyan number, e.g. 0712345678.")


def send_mpesa_stk(phone, amount, plan, config):
    if not config["callback_url"].startswith("https://"):
        raise ValueError(
            "A public HTTPS callback URL is required. The callback receiver "
            "must be deployed before STK Push can be tested."
        )

    token = mpesa_access_token(config)
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    password_raw = config["shortcode"] + config["passkey"] + timestamp
    password = base64.b64encode(password_raw.encode("utf-8")).decode("utf-8")
    payload = {
        "BusinessShortCode": config["shortcode"],
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": int(amount),
        "PartyA": phone,
        "PartyB": config["shortcode"],
        "PhoneNumber": phone,
        "CallBackURL": config["callback_url"],
        "AccountReference": "BREVINFLIX",
        "TransactionDesc": plan,
    }
    response = requests.post(
        "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def query_mpesa_stk(checkout_request_id, config):
    token = mpesa_access_token(config)
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    password_raw = config["shortcode"] + config["passkey"] + timestamp
    password = base64.b64encode(password_raw.encode("utf-8")).decode("utf-8")
    payload = {
        "BusinessShortCode": config["shortcode"],
        "Password": password,
        "Timestamp": timestamp,
        "CheckoutRequestID": checkout_request_id,
    }
    response = requests.post(
        "https://sandbox.safaricom.co.ke/mpesa/stkpushquery/v1/query",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


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

st.title("­ƒÄ¼ BREVINFLIX")

st.markdown(
    "### Your entertainment destination"
)

st.markdown("""
<div style="
background:linear-gradient(90deg,#e50914,#a020f0,#007bff);
padding:3px;
border-radius:20px;
"></div>
""", unsafe_allow_html=True)

# =====================================
# NAVIGATION
# =====================================

page = st.sidebar.radio(
    "­ƒîƒ NAVIGATION",
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
st.sidebar.markdown("### ­ƒæñ YOUR ACCOUNT")
st.sidebar.write("Plan:", st.session_state.membership)

# =====================================
# VOICE SEARCH
# =====================================

st.subheader("­ƒöÄ Find your next movie")

if VOICE_AVAILABLE:
    voice_text = speech_to_text(
        language="en",
        start_prompt="­ƒÄÖ´©Å Speak your movie title",
        stop_prompt="ÔÅ╣´©Å Stop recording",
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
                    "­ƒÄ¼ **Poster unavailable**"
                )

            st.markdown("**" + movie["title"] + "**")

            st.caption(
                str(movie["year"] or "") +
                " ÔÇó " +
                str(movie["genre"] or "")
            )

            if movie["is_premium"]:
                st.caption("­ƒöÆ PREMIUM")

            if st.button(
                "View details",
                key=f"view_{movie['id']}"
            ):
                st.session_state.selected_movie = movie

            fav_label = (
                "ÔÖÑ Remove favourite"
                if movie["id"] in st.session_state.favourites
                else "ÔÖí Add favourite"
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
    st.header("­ƒÄÑ " + movie["title"])

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
        st.warning("­ƒöÆ This title is reserved for Premium members.")
        st.info("Visit Membership to explore the available plans.")

    elif movie["video_url"]:
        st.video(movie["video_url"])

    if movie["trailer"]:
        st.link_button(
            "ÔûÂ Watch official trailer",
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
    <div style="
    background:linear-gradient(120deg,#e50914,#6a00f4,#007bff);
    padding:35px;
    border-radius:18px;
    ">
    <h1 style="color:white!important;">
    WELCOME TO BREVINFLIX
    </h1>
    <h3 style="color:white!important;">
    Discover movies and amazing entertainment.
    </h3>
    <p>­ƒÄ¼ MOVIES ÔÇó ­ƒô║ TV SHOWS ÔÇó Ô¡É ENTERTAINMENT</p>
    </div>
    """, unsafe_allow_html=True)

    st.subheader("­ƒöÑ Latest additions")
    show_movies(all_movies[:8])

    st.subheader("Ô¡É Explore more")
    st.write(
        "Discover movies, browse TV shows and explore membership options."
    )

# =====================================
# MOVIES
# =====================================

elif page == "Movies":

    st.header("­ƒÄ¼ Movies")

    results = [
        m for m in all_movies
        if m["category"] == "Movie"
    ]

    show_movies(results)

# =====================================
# TV SHOWS
# =====================================

elif page == "TV Shows":

    st.header("­ƒô║ TV Shows")

    results = [
        m for m in all_movies
        if m["category"] == "TV Show"
    ]

    show_movies(results)

# =====================================
# FAVOURITES
# =====================================

elif page == "Favourites":

    st.header("ÔØñ´©Å My Favourites")

    results = [
        m for m in get_movies()
        if m["id"] in st.session_state.favourites
    ]

    show_movies(results)

# =====================================
# MEMBERSHIP
# =====================================

elif page == "Membership":

    st.header("BREVINFLIX MEMBERSHIPS")
    st.write("Choose the entertainment experience you want.")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("## FREE")
        st.markdown("### KSh 0")
        st.write("Browse the catalogue")
        st.write("Search movies")
        st.write("Save favourites")
        if st.button("Choose Free", key="free"):
            st.session_state.membership = "Free"
            st.success("Free plan selected.")
            st.rerun()

    with col2:
        st.markdown("## PREMIUM")
        st.markdown("### KSh 299/month")
        st.write("Premium catalogue")
        st.write("Premium member features")
        st.write("Licensed content where available")
        if st.button("Select Premium", key="premium"):
            st.session_state.mpesa_plan = "Premium"
            st.session_state.mpesa_amount = 299

    with col3:
        st.markdown("## VIP")
        st.markdown("### KSh 499/month")
        st.write("Premium features")
        st.write("VIP member badge")
        st.write("Priority support")
        if st.button("Select VIP", key="vip"):
            st.session_state.mpesa_plan = "VIP"
            st.session_state.mpesa_amount = 499

    st.markdown("---")
    st.subheader("M-Pesa sandbox checkout")
    st.warning(
        "TEST MODE ONLY. This connects to Safaricom's Daraja sandbox, "
        "not live customer payments. Do not enter your M-Pesa PIN here."
    )

    config = get_mpesa_config()
    if not all(config.values()):
        st.info(
            "Sandbox credentials and a publicly reachable HTTPS callback "
            "URL have not been configured. Keep these values private in "
            "Streamlit Secrets; never paste them into this chat or source code."
        )
    else:
        selected_plan = st.session_state.get("mpesa_plan", "")
        selected_amount = st.session_state.get("mpesa_amount", 0)
        if selected_plan:
            st.write(f"Selected plan: **{selected_plan} — KSh {selected_amount}**")
            phone_input = st.text_input(
                "Safaricom test phone number",
                placeholder="0712345678",
                key="mpesa_phone",
            )
            if st.button("Send sandbox STK Push", key="send_mpesa_stk"):
                try:
                    phone = normalize_kenyan_phone(phone_input)
                    result = send_mpesa_stk(
                        phone, selected_amount, selected_plan, config
                    )
                    if result.get("ResponseCode") == "0":
                        st.session_state.mpesa_checkout_request_id = result.get(
                            "CheckoutRequestID", ""
                        )
                        st.success(
                            "Sandbox STK request submitted. Check the Daraja "
                            "sandbox response and use the status check below."
                        )
                        st.caption(result.get("CustomerMessage", "Request submitted."))
                    else:
                        st.error(result.get("errorMessage", str(result)))
                except Exception as exc:
                    st.error(f"Sandbox request could not be sent: {exc}")

        checkout_id = st.session_state.get("mpesa_checkout_request_id", "")
        if checkout_id:
            st.caption("A sandbox request is pending. Membership is not active yet.")
            if st.button("Check sandbox payment status", key="check_mpesa_status"):
                try:
                    result = query_mpesa_stk(checkout_id, config)
                    result_code = str(result.get("ResultCode", ""))
                    if result_code == "0":
                        st.session_state.membership = st.session_state.get(
                            "mpesa_plan", "Free"
                        )
                        st.success(
                            "Daraja sandbox reports success for this test request. "
                            "This temporary session membership is for testing only."
                        )
                        st.rerun()
                    elif result_code:
                        st.warning(
                            "Daraja returned a non-success result: "
                            + str(result.get("ResultDesc", result))
                        )
                    else:
                        st.info(
                            "No final result yet. Wait a little and check again."
                        )
                except Exception as exc:
                    st.error(f"Could not check sandbox status: {exc}")

    st.markdown("---")
    st.subheader("Current demo membership")
    st.success(st.session_state.membership)
    st.caption(
        "This app does not include a deployed callback receiver or permanent "
        "payment ledger. Do not use it to collect real customer payments. "
        "Production payments need a secure HTTPS backend, verified callbacks, "
        "persistent subscription records, and an eligible merchant account."
    )


# =====================================
# ADMIN
# =====================================

elif page == "Admin":

    st.header("­ƒöÉ ADMIN DASHBOARD")

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

            st.subheader("Ô×ò Add a movie or TV show")

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
                    type=["jpg", "jpeg", "png", "webp"]
                )

                trailer = st.text_input(
                    "Official trailer link"
                )

                video_url = st.text_input(
                    "Licensed video URL (optional)"
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

                        extension = Path(
                            poster.name
                        ).suffix.lower()

                        filename = (
                            str(uuid.uuid4()) + extension
                        )

                        poster_path = MEDIA_DIR / filename

                        with open(poster_path, "wb") as file:
                            file.write(poster.getbuffer())

                        add_movie(
                            title.strip(),
                            category,
                            genre,
                            year,
                            description,
                            str(poster_path),
                            trailer,
                            video_url,
                            int(is_premium)
                        )

                        st.success(
                            title + " added successfully!"
                        )

                        st.rerun()

            st.markdown("---")

            st.subheader("­ƒùæ´©Å Manage movies")

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

                        st.rerun()

        elif password:
            st.error("Incorrect admin password.")

# =====================================
# FOOTER
# =====================================

st.markdown("---")

st.markdown("""
<div style="text-align:center;padding:15px;">
<h3>­ƒÄ¼ BREVINFLIX</h3>
<p>Movies ÔÇó TV Shows ÔÇó Entertainment</p>
<p>┬® BREVINFLIX</p>
</div>
""", unsafe_allow_html=True)
