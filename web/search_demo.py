import cherrypy
import tmdbsimple as tmdb
from elasticsearch import Elasticsearch
from sentence_transformers import SentenceTransformer


# Function to fetch movie poster URL from TMDB API
def getTmdbImage(tmdb_id):
    try:
        # Replace this variable with your actual TMdb API key
        tmdb.API_KEY = "" #you own key
        # Base URL for TMDB poster images
        IMAGE_URL = 'https://image.tmdb.org/t/p/w500'
        movie_info = tmdb.Movies(tmdb_id).info()
        movie_poster_url = IMAGE_URL + movie_info['poster_path']
        return movie_poster_url
    except Exception:
        # print("Cannot import tmdbsimple, no movie posters will be displayed!")
        return ""


# Sample data for popular movies
mock_popular_data = [
    {"movieId": 3114, "title": "Toy Story 2", "release_year": "1999",
     "genres": ["adventure", "animation", "children", "comedy", "fantasy"], "tmdbId": 863,
     "avg_rating": 3.8114636719927644},
    # Add more movie data as needed
]

# Sample data for search results
mock_search_data = [
    {"movieId": 1, "title": "Toy Story", "release_year": "1995",
     "genres": ["adventure", "animation", "children", "comedy", "fantasy"], "tmdbId": 862,
     "avg_rating": 3.893707794587238},
    # Add more movie data as needed
]


def process_search_results(resp):
    hits = resp["hits"]["total"]["value"]
    print("Got {} hits:".format(resp["hits"]["total"]["value"]))
    res = []

    # if hits > 0:
    #     max_es_score = resp["hits"]["hits"][0]["_score"]
    for hit in resp["hits"]["hits"]:
        # hit["_source"]["normalized_score"] = hit["_score"] / max_es_score
        res.append(hit["_source"])
    print(res)
    return res


class MovieLensDemo:
    def __init__(self):
        self.es_host = "http://localhost:9200"
        self.es = Elasticsearch(self.es_host)
        print(self.es.info(pretty=True))
        self.model = SentenceTransformer('sentence-transformers/all-distilroberta-v1')
        self.keyword_alias_name = "a_movielens_keywords"
        self.embedding_alias_name = "a_movielens_embeddings"

    @staticmethod
    def render_row(data):
        row = ""
        for movie in data:
            image_url = getTmdbImage(movie['tmdbId'])
            if not image_url:
                image_url = "/static/image_not_available.png"  # Placeholder for missing images
            row += """
                <div class="cell" title='%s'>
                    <div class="title">%s</div>
                    <img src='%s' alt='%s' style='width: 100px;'>
                </div>
            """ % (movie, movie['title'], image_url, movie['title'])
        return row

    @cherrypy.expose
    def index(self, query_phrase=None):
        # Check if search query is provided
        if query_phrase:
            # Handle search functionality
            search_results = self.keyword_search(query_phrase)
            # Render row1 with search results
            row1_content = self.render_row(search_results)
            row1_title = "Keyword Search"
            vector_search_results = self.vector_search(query_phrase)
            row2_title = "Vector Search"
            row2_content = self.render_row(vector_search_results)
        else:
            # Render row with popular movies, before we have a search result
            row1_title = "Recent Movies"
            row1_content = self.render_row(self.recent_movies())
            row2_title = "Popular Movies"
            row2_content = self.render_row(self.most_popular_movies())

        return """
            <html>
            <head>
                <title>MovieLens Demo</title>
                <link rel="stylesheet" type="text/css" href="style.css">
                <style>
                    .row { white-space: nowrap; overflow-x: auto; }
                    .cell { display: inline-block; margin: 5px; }
                    .title { font-weight: bold; }
                </style>
                <script>
                    function showMovieDetails(movie) {
                        alert(JSON.stringify(movie, null, 4));
                    }
                </script>
            </head>
            <body>
                <div id="container">
                    <h1>MovieLens Demo</h1>
                    <p>This is a demo of keyword search and vector search on MovieLens data.</p>
                    <form method="get" action="/">
                        <input type="text" name="query_phrase" placeholder="Enter search phrase...">
                        <input type="submit" value="Search">
                    </form>
                    <h2>%s</h2>
                    <div class="row" id="row1">
                        %s
                    </div>
                    <h2>%s</h2>
                    <div class="row" id="row2">
                        %s
                    </div>
                </div>
            </body>
            </html>
        """ % (row1_title, row1_content, row2_title, row2_content)

    def most_popular_movies(self):
        es_query = {
            "query": {
                "match_all": {}
            },
            "sort": [
                {
                    "avg_rating": {
                        "order": "desc"
                    }
                }
            ],
            "size": 20,
            "_source": [
                "movieId",
                "tmdbId",
                "title",
                "release_year",
                "avg_rating",
                "genres"
            ]
        }
        resp = self.es.search(index=self.keyword_alias_name, body=es_query)
        return process_search_results(resp)

    def recent_movies(self):
        es_query = {
            "query": {
                "match_all": {}
            },
            "sort": [
                {
                    "release_year": {
                        "order": "desc"
                    }
                },
                {
                    "avg_rating": {
                        "order": "desc"
                    }
                }
            ],
            "size": 20,
            "_source": [
                "movieId",
                "tmdbId",
                "title",
                "release_year",
                "avg_rating",
                "genres"
            ]
        }
        resp = self.es.search(index=self.keyword_alias_name, body=es_query)
        return process_search_results(resp)

    def keyword_search(self, query_phrase):
        es_query = {
            "query": {
                "function_score": {
                    "query": {
                        "bool": {
                            "must": {
                                "multi_match": {
                                    "query": query_phrase,
                                    "fields": [
                                        "title.exact_phrase^100.0",
                                        "title.exact_word^25.0",
                                        "title.exact_word_stemmed^15.0",
                                        "genres.exact_phrase^100.0",
                                        "genres.exact_word^25.0",
                                        "genres.exact_word_stemmed^15.0",
                                        "tags.exact_phrase^10.0",
                                        "tags.exact_word^2.50",
                                        "tags.exact_word_stemmed^1.5"
                                    ],
                                    "type": "cross_fields",
                                    "operator": "AND",
                                    "slop": 0,
                                    "prefix_length": 0,
                                    "max_expansions": 50,
                                    "zero_terms_query": "NONE",
                                    "auto_generate_synonyms_phrase_query": True,
                                    "fuzzy_transpositions": True,
                                    "boost": 1
                                }
                            }
                        }
                    },
                    "script_score": {
                        "script": {
                            "source": "doc.containsKey('avg_rating') ? doc['avg_rating'].value + 0.01 : 0.01"
                        }
                    }
                }
            },
            "_source": [
                "movieId",
                "tmdbId",
                "title",
                "release_year",
                "avg_rating",
                "genres"
            ],
            "size": 20
        }
        resp = self.es.search(index=self.keyword_alias_name, body=es_query)
        return process_search_results(resp)

    def vector_search(self, query_phrase):
        query_vector = self.model.encode(query_phrase)
        print("Query vector: ", query_vector)
        knn_query = {"field": "title_genres_embedding", "query_vector": query_vector, "k": 5, "num_candidates": 20}
        resp = self.es.search(index=self.embedding_alias_name, knn=knn_query)
        return process_search_results(resp)


if __name__ == "__main__":
    cherrypy.quickstart(MovieLensDemo())
