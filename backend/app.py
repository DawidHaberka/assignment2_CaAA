from flask import Flask, request, jsonify
from flask_cors import CORS
from elasticsearch import Elasticsearch
from google.cloud import bigquery
import requests

app = Flask(__name__)
CORS(app) 

# config
PROJECT_ID = "dh-assignment1"
DATASET_ID = "recommender_db"
OLD_DATASET_ID = "movie_db" 
ES_URL = "https://a9eaf2c33a5146eca828297b74d0b9a7.europe-west3.gcp.cloud.es.io:443"
ES_USER = "elastic"
ES_PASS = "fzoZOq3P2pupBx7dduqdumD0"
TMDB_API_KEY = "dee031756bbb4499f30c60fc595ce12b"

es = Elasticsearch(ES_URL, basic_auth=(ES_USER, ES_PASS))
bq_client = bigquery.Client(project=PROJECT_ID)

def fetch_tmdb_details_full(tmdb_id):
    if not tmdb_id: return {"poster_url": None, "overview": "No overview available."}
    url = f"https://api.themoviedb.org/3/movie/{tmdb_id}?api_key={TMDB_API_KEY}"
    try:
        res = requests.get(url, timeout=3).json()
        poster_url = f"https://image.tmdb.org/t/p/w500{res.get('poster_path')}" if res.get('poster_path') else None
        overview = res.get('overview', 'No overview available.')
        return {"poster_url": poster_url, "overview": overview}
    except:
        return {"poster_url": None, "overview": "No overview available."}

@app.route('/autocomplete', methods=['GET'])
def autocomplete():
    query_text = request.args.get('q', '')
    if not query_text: return jsonify([])
    res = es.search(index="movies_autocomplete", body={
        "query": {"multi_match": {"query": query_text, "type": "bool_prefix", "fields": ["title", "title._2gram"]}}, "size": 10
    })
    return jsonify([{"movieId": h["_source"]["movieId"], "title": h["_source"]["title"]} for h in res["hits"]["hits"]])

@app.route('/explore', methods=['POST'])
def explore():
    data = request.json
    search_term = data.get('search_term', '')
    genre = data.get('genre', 'All')
    language = data.get('language', '')
    min_year = data.get('min_year', 1980)
    max_year = data.get('max_year', 2026)
    min_rating = data.get('min_rating', 3.0)
    max_rating = data.get('max_rating', 5.0)
    min_votes = data.get('min_votes', 100)
    
    query = f"""
        SELECT 
            new_m.movieId, new_m.title, m.genres, m.tmdbId, m.language, m.release_year,
            ROUND(AVG(r.rating), 2) as avg_rating, COUNT(r.rating) as rating_count
        FROM `{PROJECT_ID}.{OLD_DATASET_ID}.movies` m
        JOIN `{PROJECT_ID}.{OLD_DATASET_ID}.ratings` r ON m.movieId = r.movieId
        INNER JOIN `{PROJECT_ID}.{DATASET_ID}.movies` new_m ON m.movieId = new_m.movieId
        WHERE m.release_year BETWEEN {min_year} AND {max_year}
    """
    if search_term:
        safe_term = search_term.replace("'", "\\'")
        query += f" AND LOWER(new_m.title) LIKE LOWER('%{safe_term}%')"
    if language:
        query += f" AND m.language = '{language}'"
    if genre != "All":
        query += f" AND m.genres LIKE '%{genre}%'"
        
    query += f"""
        GROUP BY new_m.movieId, new_m.title, m.genres, m.tmdbId, m.language, m.release_year
        HAVING avg_rating BETWEEN {min_rating} AND {max_rating} AND rating_count >= {min_votes}
        ORDER BY avg_rating DESC, rating_count DESC LIMIT 20
    """

    print("\n" + "="*50)
    print("EXECUTING EXPLORE SQL QUERY:")
    print(query)
    print("="*50 + "\n")
    
    try:
        results = []
        for row in bq_client.query(query):
            tmdb_data = fetch_tmdb_details_full(row.tmdbId)
            results.append({
                "movieId": row.movieId, "title": row.title, "genres": row.genres,
                "language": row.language, "release_year": row.release_year,
                "avg_rating": row.avg_rating, "rating_count": row.rating_count,
                "poster_url": tmdb_data['poster_url'], "overview": tmdb_data['overview']
            })
        print(f"SUCCESS: Returned {len(results)} movies from database.\n")
        return jsonify(results)
    except Exception as e:
        print(f"ERROR: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/recommend', methods=['POST'])
def recommend():
    try:
        data = request.json
        selected_movie_ids = data.get('movie_ids', [])
        if not selected_movie_ids: return jsonify({"error": "Empty profile"}), 400

        query = f"""
            WITH SimilarUsers AS (
                SELECT userId FROM `{PROJECT_ID}.{DATASET_ID}.ratings`
                WHERE movieId IN UNNEST(@liked_movies) AND rating_im >= 0.8
                GROUP BY userId ORDER BY COUNT(movieId) DESC LIMIT 50
            ),
            Predictions AS (
                SELECT movieId, AVG(predicted_rating_im) as expected_rating
                FROM ML.RECOMMEND(MODEL `{PROJECT_ID}.{DATASET_ID}.movie_model`, (SELECT userId FROM SimilarUsers))
                GROUP BY movieId
            ),
            MovieStats AS (
                SELECT movieId, COUNT(rating_im) as num_ratings FROM `{PROJECT_ID}.{DATASET_ID}.ratings` GROUP BY movieId
            )
            SELECT p.movieId, new_m.title, old_m.genres, old_m.language, old_m.release_year, l.tmdbId, p.expected_rating
            FROM Predictions p
            JOIN `{PROJECT_ID}.{DATASET_ID}.movies` new_m ON p.movieId = new_m.movieId
            LEFT JOIN `{PROJECT_ID}.{OLD_DATASET_ID}.movies` old_m ON p.movieId = old_m.movieId
            LEFT JOIN `{PROJECT_ID}.{DATASET_ID}.links` l ON p.movieId = l.movieId
            JOIN MovieStats s ON p.movieId = s.movieId
            WHERE p.movieId NOT IN UNNEST(@liked_movies) AND s.num_ratings > 30 
            ORDER BY p.expected_rating DESC LIMIT 10
        """
        job_config = bigquery.QueryJobConfig(query_parameters=[bigquery.ArrayQueryParameter("liked_movies", "INT64", selected_movie_ids)])
        
        print("\n" + "="*50)
        print(f"EXECUTING ML RECOMMENDATION QUERY FOR MOVIES: {selected_movie_ids}")
        print(query)
        print("="*50 + "\n")
        
        fetched_rows = [dict(row) for row in bq_client.query(query, job_config=job_config)]
        results = []
        
        if fetched_rows:
            max_raw_score = max([float(row.get("expected_rating", 0.0)) for row in fetched_rows])
            
            for row_dict in fetched_rows:
                raw_score = float(row_dict.get("expected_rating", 0.0))
                
                # dynamic normalisation
                if max_raw_score > 0:
                    display_score = (raw_score / max_raw_score) * 5.0
                else:
                    display_score = 0.0
                    
                tmdb_data = fetch_tmdb_details_full(row_dict.get("tmdbId"))
                results.append({
                    "movieId": row_dict["movieId"], "title": row_dict["title"], "score": round(display_score, 2), 
                    "poster_url": tmdb_data['poster_url'], "overview": tmdb_data['overview'],
                    "release_year": row_dict.get("release_year"), "language": row_dict.get("language")
                })
        print(f"SUCCESS: Generated {len(results)} recommendations using BigQuery ML.\n")
        return jsonify(results)
    except Exception as e:
        print(f"ERROR: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)