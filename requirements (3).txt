import streamlit as st
import requests
from st_keyup import st_keyup

BACKEND_URL = "https://flask-backend-797757706991.europe-west6.run.app"

# list of languages
LANGUAGE_MAP = {
    "All": "", "English": "en", "French": "fr", "Italian": "it", "Spanish": "es",
    "German": "de", "Japanese": "ja", "Albanian": "sq", "Amharic": "am", "Arabic": "ar",
    "Armenian": "hy", "Aymara": "ay", "Bambara": "bm", "Basque": "eu", "Bengali": "bn",
    "Bosnian": "bs", "Bulgarian": "bg", "Catalan": "ca", "Chinese (Simplified)": "zh",
    "Chinese (Traditional)": "cn", "Croatian": "hr", "Czech": "cs", "Danish": "da",
    "Dutch": "nl", "Dzongkha": "dz", "Esperanto": "eo", "Estonian": "et", "Finnish": "fi",
    "Fulah": "ff", "Galician": "gl", "Georgian": "ka", "Greek": "el", "Hebrew": "he",
    "Hindi": "hi", "Hungarian": "hu", "Icelandic": "is", "Indonesian": "id", "Inuktitut": "iu",
    "Javanese": "jv", "Kazakh": "kk", "Kinyarwanda": "rw", "Korean": "ko", "Kurdish": "ku",
    "Lao": "lo", "Latin": "la", "Latvian": "lv", "Lingala": "ln", "Lithuanian": "lt",
    "Macedonian": "mk", "Malay": "ms", "Malayalam": "ml", "Marathi": "mr", "Mongolian": "mn",
    "Nepali": "ne", "Northern Sami": "se", "Norwegian": "no", "Norwegian Bokmål": "nb",
    "Pashto": "ps", "Persian": "fa", "Polish": "pl", "Portuguese": "pt", "Quechua": "qu",
    "Romanian": "ro", "Russian": "ru", "Sardinian": "sc", "Serbian": "sr", "Serbo-Croatian": "sh",
    "Slovak": "sk", "Slovenian": "sl", "Swedish": "sv", "Tagalog": "tl", "Tajik": "tg",
    "Tamil": "ta", "Telugu": "te", "Thai": "th", "Tibetan": "bo", "Tswana": "tn",
    "Turkish": "tr", "Ukrainian": "uk", "Urdu": "ur", "Uzbek": "uz", "Vietnamese": "vi",
    "Welsh": "cy", "Western Frisian": "fy", "Wolof": "wo", "Zulu": "zu"
}
REVERSE_MAP = {v: k for k, v in LANGUAGE_MAP.items() if v != ""}

# sliders
def sync_slider_to_inputs():
    st.session_state.min_year_input = st.session_state.year_range[0]
    st.session_state.max_year_input = st.session_state.year_range[1]

def sync_inputs_to_slider():
    min_y = st.session_state.min_year_input
    max_y = st.session_state.max_year_input
    if min_y > max_y: min_y = max_y
    st.session_state.year_range = (min_y, max_y)

def search_by_filters():
    payload = {
        "search_term": "", 
        "language": LANGUAGE_MAP[st.session_state.lang_input],
        "genre": st.session_state.genre_input,
        "min_year": st.session_state.min_year_input,
        "max_year": st.session_state.max_year_input,
        "min_rating": st.session_state.min_rating_input,
        "max_rating": st.session_state.max_rating_input,
        "min_votes": st.session_state.min_votes_input
    }
    res = requests.post(f"{BACKEND_URL}/explore", json=payload)
    if res.status_code == 200:
        st.session_state.explore_results = res.json()
        st.session_state.recommendations = None
        st.session_state.search_key_counter += 1

def main():
    st.set_page_config(page_title="Movie Explorer", layout="wide")

    # memory initialization
    if 'liked_movies' not in st.session_state: st.session_state.liked_movies = []
    if 'explore_results' not in st.session_state: st.session_state.explore_results = None
    if 'recommendations' not in st.session_state: st.session_state.recommendations = None
    if 'search_key_counter' not in st.session_state: st.session_state.search_key_counter = 0

    if "year_range" not in st.session_state: st.session_state.year_range = (1980, 2026)
    if "min_year_input" not in st.session_state: st.session_state.min_year_input = 1980
    if "max_year_input" not in st.session_state: st.session_state.max_year_input = 2026

    if 'welcome_movies' not in st.session_state:
        welcome_payload = {
            "search_term": "", "language": "", "genre": "All",
            "min_year": 1990, "max_year": 2026, "min_rating": 4.0, "max_rating": 5.0, "min_votes": 500 
        }
        try:
            res = requests.post(f"{BACKEND_URL}/explore", json=welcome_payload)
            if res.status_code == 200:
                st.session_state.welcome_movies = res.json()
            else:
                st.session_state.welcome_movies = []
        except:
            st.session_state.welcome_movies = []

    # slidebar
    st.sidebar.header("Search Filters")
    st.sidebar.selectbox("Language:", list(LANGUAGE_MAP.keys()), key="lang_input")
    st.sidebar.selectbox("Genre:", ["All", "Action", "Adventure", "Comedy", "Drama", "Documentary", "Horror", "Western", "Romance", "War", "Fantasy", "Mystery", "Sci-Fi", "Thriller"], key="genre_input")

    st.sidebar.write("### Release Year Range")
    st.sidebar.slider("Use slider:", 1800, 2026, key="year_range", on_change=sync_slider_to_inputs, label_visibility="collapsed")
    
    col1, col2 = st.sidebar.columns(2)
    col1.number_input("Min Year", 1800, 2026, key="min_year_input", on_change=sync_inputs_to_slider)
    col2.number_input("Max Year", 1800, 2026, key="max_year_input", on_change=sync_inputs_to_slider)

    st.sidebar.markdown("---")
    min_rating, max_rating = st.sidebar.slider("Average rating range:", 0.0, 5.0, (3.0, 5.0), step=0.1)
    st.session_state.min_rating_input = min_rating
    st.session_state.max_rating_input = max_rating
    st.sidebar.number_input("Minimum number of votes:", 1, 10000, 100, key="min_votes_input")
    
    st.sidebar.button("Search Movies", on_click=search_by_filters, type="primary", use_container_width=True)

    # layout
    st.title("🍿 Movie Explorer & Recommender")
    col_main, col_cart = st.columns([3, 1])

    with col_cart:
        # viewer profile
        st.header("👤 Your Profile")
        if not st.session_state.liked_movies:
            st.info("No movies in your profile. Add some using ➕.")
        else:
            for m in st.session_state.liked_movies:
                c_title, c_btn = st.columns([4, 1])
                c_title.write(f"🎬 {m['title']}")
                if c_btn.button("➖", key=f"del_{m['movieId']}"):
                    st.session_state.liked_movies.remove(m)
                    st.session_state.recommendations = None
                    st.rerun()
            st.markdown("---")
            if st.button("Discover Recommendations", type="primary", use_container_width=True):
                movie_ids = [m['movieId'] for m in st.session_state.liked_movies]
                with st.spinner("Analyzing your choices..."):
                    res = requests.post(f"{BACKEND_URL}/recommend", json={"movie_ids": movie_ids})
                    if res.status_code == 200:
                        st.session_state.recommendations = res.json()
                        st.session_state.explore_results = None 
                        st.session_state.search_key_counter += 1 # Resets live search!
                        st.rerun()
                    else:
                        st.error("Error generating recommendations.")

    with col_main:
        # life search
        live_search = st_keyup("Search by title:", key=f"live_search_{st.session_state.search_key_counter}", debounce=500)
        
        if live_search:
            payload = {
                "search_term": live_search, "language": "", "genre": "All",
                "min_year": 1800, "max_year": 2026, "min_rating": 0.0, "max_rating": 5.0, "min_votes": 1 
            }
            res = requests.post(f"{BACKEND_URL}/explore", json=payload)
            if res.status_code == 200:
                st.session_state.explore_results = res.json()
                st.session_state.recommendations = None

        st.markdown("---")
        
        if st.session_state.explore_results is None and st.session_state.recommendations is None and not live_search:
            st.subheader("🔥 Welcome! Popular picks to start:")
            if st.session_state.welcome_movies:
                cols = st.columns(5)
                for i, row in enumerate(st.session_state.welcome_movies[:10]):
                    with cols[i % 5]:
                        if row.get('poster_url'): st.image(row['poster_url'], use_container_width=True)
                        st.markdown(f"<div style='height: 45px; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;'><b>{row['title']}</b></div>", unsafe_allow_html=True)
                        st.caption(f"⭐ {row['avg_rating']} ({row['rating_count']} votes)")
                        
                        with st.popover("ℹ️ Details"):
                            st.write(f"**Overview:** {row.get('overview')}")
                            if st.button("➕ Add to profile", key=f"welcome_add_{row['movieId']}", use_container_width=True):
                                movie_to_add = {"movieId": row['movieId'], "title": row['title']}
                                if movie_to_add not in st.session_state.liked_movies:
                                    st.session_state.liked_movies.append(movie_to_add)
                                    st.rerun()

        # search results
        if st.session_state.explore_results is not None:
            st.subheader("Database search results:")
            for row in st.session_state.explore_results:
                c_exp, c_btn = st.columns([12, 1], vertical_alignment="center")
                
                with c_btn:
                    if st.button("➕", key=f"quick_add_{row['movieId']}", help="Add movie to profile", use_container_width=True):
                        movie_to_add = {"movieId": row['movieId'], "title": row['title']}
                        if movie_to_add not in st.session_state.liked_movies:
                            st.session_state.liked_movies.append(movie_to_add)
                            st.session_state.recommendations = None
                            st.rerun()

                with c_exp:
                    with st.expander(f"⭐ {row['avg_rating']} ({row['rating_count']} votes) | {row['title']} - {row['genres']}"):
                        c1, c2 = st.columns([1, 3])
                        with c1:
                            if row.get('poster_url'): st.image(row['poster_url'], use_container_width=True)
                            else: st.write("No poster")
                        with c2:
                            st.write(f"**Original Language:** {REVERSE_MAP.get(row.get('language'), row.get('language'))}")
                            st.write("**Overview:**")
                            st.write(row.get('overview', 'No overview available.'))

        # recommendations
        if st.session_state.recommendations is not None:
            st.subheader("Best recommends:")
            recs = st.session_state.recommendations
            if not recs:
                st.warning("No recommendations. Add more popular movies to your profile.")
            else:
                cols = st.columns(5)
                for i, rec in enumerate(recs):
                    with cols[i % 5]:
                        if rec.get('poster_url'): st.image(rec['poster_url'], use_container_width=True)
                        st.markdown(f"<div style='height: 45px; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;'><b>{rec['title']}</b></div>", unsafe_allow_html=True)
                        st.caption(f"Match: ⭐ {rec['score']}")
                        
                        with st.popover("Details"):
                            st.write(f"**Overview:** {rec.get('overview')}")
                            if st.button("➕ Add to profile", key=f"rec_add_{rec['movieId']}", use_container_width=True):
                                movie_to_add = {"movieId": rec['movieId'], "title": rec['title']}
                                if movie_to_add not in st.session_state.liked_movies:
                                    st.session_state.liked_movies.append(movie_to_add)
                                    st.rerun()

if __name__ == '__main__':
    main()