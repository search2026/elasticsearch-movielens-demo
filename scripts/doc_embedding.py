import os
import logging
import json
from sentence_transformers import SentenceTransformer

logging.basicConfig(level=logging.INFO)


class MovieEmbedder:
    def __init__(self):
        self.model = SentenceTransformer('sentence-transformers/all-distilroberta-v1')

    def embed_strings(self, strings):
        embeddings = self.model.encode(strings)
        return embeddings.tolist()

    def process_csv_files(self, input_folder, output_folder):
        # Create output folder if it doesn't exist
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)

        counter = 0
        # Process each CSV file in the input folder
        for filename in os.listdir(input_folder):
            if filename.endswith(".json"):
                input_path = os.path.join(input_folder, filename)
                output_path = os.path.join(output_folder, filename.replace('.json', '.jsonl'))

                with open(input_path, 'r', encoding='utf-8') as infile, \
                        open(output_path, 'w', encoding='utf-8') as outfile:
                    logging.info(f"Processing {filename}...")
                    for line in infile:
                        movie_data = json.loads(line)
                        counter += 1
                        if counter % 1000 == 0:
                            logging.info(f"{counter} documents processed.")

                        # Extract data
                        movie_id = movie_data['movieId']
                        title = movie_data['title']
                        tmdb_id = movie_data['tmdbId']
                        genres = movie_data['genres']
                        genres_text = ' '.join(genres)
                        title_genres_text = title + ' ' + genres_text

                        title_genres_embedding = self.embed_strings([title_genres_text])[0]

                        # Prepare output JSON object
                        output_data = {
                            'movieId': movie_id,
                            'title': title,
                            'tmdbId': tmdb_id,
                            'title_genres_embedding': title_genres_embedding,
                        }

                        # Write to output file as JSONL
                        outfile.write(json.dumps(output_data) + '\n')

        # Add _SUCCESS file
        with open(os.path.join(output_folder, '_SUCCESS'), 'w'):
            pass


# Example usage:
embedder = MovieEmbedder()
embedder.process_csv_files('movielens_index', 'movielens_embedding')
