import streamlit as st
import requests
import pickle
from functools import lru_cache

# TMDb API key
tmdb_api_key = "c876118b555b956c44c7c08153dc12b3"

# Caching setup with LRU Cache
@lru_cache(maxsize=128)
def fetch_genres():
    url = f"https://api.themoviedb.org/3/genre/movie/list?api_key={tmdb_api_key}&language=en-US"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        return {genre['id']: genre['name'] for genre in data['genres']}
    except requests.RequestException as e:
        st.error(f"Error fetching genres: {e}")
        return {}

@lru_cache(maxsize=128)
def fetch_movies_by_category(category):
    url_map = {
        "Popular": "https://api.themoviedb.org/3/movie/popular",
        "Trending": "https://api.themoviedb.org/3/trending/movie/week",
        "Top Rated": "https://api.themoviedb.org/3/movie/top_rated",
        "Upcoming": "https://api.themoviedb.org/3/movie/upcoming"
    }
    url = url_map.get(category, "")
    if not url:
        st.error("Invalid category selected.")
        return []
    try:
        response = requests.get(f"{url}?api_key={tmdb_api_key}&language=en-US")
        response.raise_for_status()
        data = response.json()
        return data['results']
    except requests.RequestException as e:
        st.error(f"Error fetching movies: {e}")
        return []

@lru_cache(maxsize=128)
def fetch_movies_by_genre(genre_id):
    url = f"https://api.themoviedb.org/3/discover/movie?api_key={tmdb_api_key}&with_genres={genre_id}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        return data['results']
    except requests.RequestException as e:
        st.error(f"Error fetching movies: {e}")
        return []

@lru_cache(maxsize=128)
def fetch_poster(movie_id):
    url = f"https://api.themoviedb.org/3/movie/{movie_id}?api_key={tmdb_api_key}&language=en-US"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        poster_path = data.get('poster_path', '')
        if poster_path:
            return f"https://image.tmdb.org/t/p/w500/{poster_path}", data.get('overview', 'No description available.')
        else:
            return None, 'No description available.'
    except requests.RequestException as e:
        st.error(f"Error fetching poster for movie ID {movie_id}: {e}")
        return None, 'No description available.'

@lru_cache(maxsize=128)
def recommend_similar_movies(movie_id):
    url = f"https://api.themoviedb.org/3/movie/{movie_id}/similar?api_key={tmdb_api_key}&language=en-US"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        return data['results']
    except requests.RequestException as e:
        st.error(f"Error fetching similar movies: {e}")
        return []

@lru_cache(maxsize=128)
def fetch_cast(movie_id):
    url = f"https://api.themoviedb.org/3/movie/{movie_id}/credits?api_key={tmdb_api_key}&language=en-US"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        cast = data.get('cast', [])
        crew = data.get('crew', [])
        cast_crew = []
        for person in cast[:5]:
            profile_path = person.get('profile_path', '')
            cast_crew.append({
                'name': person.get('name', 'No Name'),
                'role': person.get('character', 'No Role'),
                'profile_path': profile_path
            })
        for person in crew[:5]:
            profile_path = person.get('profile_path', '')
            cast_crew.append({
                'name': person.get('name', 'No Name'),
                'role': person.get('job', 'No Job'),
                'profile_path': profile_path
            })
        return cast_crew
    except requests.RequestException as e:
        st.error(f"Error fetching cast for movie ID {movie_id}: {e}")
        return []

# Load movie data and similarity matrix
with open("movies_list.pkl", 'rb') as f:
    movies = pickle.load(f)
with open("similarity.pkl", 'rb') as f:
    similarity = pickle.load(f)

# Streamlit app setup
st.set_page_config(layout="wide")
st.markdown("<h1 style='text-align: center;'>Movie Recommender System</h1>", unsafe_allow_html=True)

# Add a search bar at the top of the page
search_query = st.text_input("Search for a movie:", "")

# Sidebar for categories and genres
st.sidebar.header("Categories and Genres")
categories = ["Popular", "Trending", "Top Rated", "Upcoming"]
selected_category = st.sidebar.selectbox("Choose a category", categories)

# Fetch and display genres based on selected category
if selected_category:
    st.sidebar.subheader("Genres")
    genres = fetch_genres()
    genre_names = ["All"] + list(genres.values())
    selected_genre_name = st.sidebar.selectbox("Choose a genre", genre_names)
    selected_genre_id = [key for key, value in genres.items() if value == selected_genre_name]
    selected_genre_id = selected_genre_id[0] if selected_genre_id else None

# Fetch movies for the selected category
if selected_category:
    movies = fetch_movies_by_category(selected_category)
    if selected_genre_id and selected_genre_id != 'All':
        movies = fetch_movies_by_genre(selected_genre_id)
else:
    movies = []

# Apply search filter
if search_query:
    movies = [movie for movie in movies if search_query.lower() in movie['title'].lower()]

# Get query parameters
query_params = st.experimental_get_query_params()
page = query_params.get("page", ["home"])[0]

# Function to find movie by title in the dataset
def find_movie_by_title(title):
    for movie in movies:
        if movie['title'].lower() == title.lower():
            return movie
    return None

# Main content area
if page == "details":
    if "selected_movie" in st.session_state:
        selected_movie = st.session_state.selected_movie
        movie = find_movie_by_title(selected_movie['title'])
        if movie:
            poster_path, overview = fetch_poster(movie['id'])
            st.markdown(f"### {movie['title']}")
            if poster_path:
                st.image(poster_path)
            st.write(overview)

            # Show cast and crew with images
            cast_crew = fetch_cast(movie['id'])
            if cast_crew:
                st.markdown("#### Cast and Crew")
                cols = st.columns(5)
                for index, person in enumerate(cast_crew):
                    if index % 5 == 0:
                        cols = st.columns(5)
                    col = cols[index % 5]
                    with col:
                        st.text(person['name'])
                        st.text(person['role'])
                        if person['profile_path']:
                            st.image(f"https://image.tmdb.org/t/p/w500/{person['profile_path']}", width=100)
                        else:
                            st.image("https://via.placeholder.com/100x150?text=No+Image", width=100)

            # Recommend similar movies
            similar_movies = recommend_similar_movies(movie['id'])
            if similar_movies:
                st.markdown("### Similar Movies")
                cols = st.columns(5)
                for index, movie in enumerate(similar_movies[:5]):
                    if index % 5 == 0:
                        cols = st.columns(5)
                    col = cols[index % 5]
                    with col:
                        st.text(movie['title'])
                        poster_path, _ = fetch_poster(movie['id'])
                        if poster_path:
                            st.image(poster_path)
                        if st.button("View Details", key=movie['id']):
                            st.session_state.selected_movie = movie
                            st.experimental_set_query_params(page='details')
            st.button("Back to Home", on_click=lambda: st.experimental_set_query_params(page='home'))
        else:
            st.write("Movie not found in the dataset.")
    else:
        st.write("No movie selected.")
elif page == "home":
    st.markdown("<h2 style='text-align: center;'>Movies</h2>", unsafe_allow_html=True)
    if movies:
        cols = st.columns(5)
        for index, movie in enumerate(movies):
            if index % 5 == 0:
                cols = st.columns(5)
            col = cols[index % 5]
            with col:
                st.text(movie['title'])
                poster_path, _ = fetch_poster(movie['id'])
                if poster_path:
                    st.image(poster_path)
                    if st.button("View Details", key=movie['id']):
                        st.session_state.selected_movie = movie
                        st.experimental_set_query_params(page='details')
    else:
        st.write("No movies found.")
