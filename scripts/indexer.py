import json
import logging
import os

from elasticsearch import Elasticsearch, helpers
from datetime import datetime

logging.basicConfig(level=logging.INFO)


class EsIndexer:
    """
    Initialize the ElasticsearchOperations object with default values.
    """

    def __init__(self):
        self.hosts = ['localhost:9200']
        self.host = "http://localhost:9200"
        self.es = Elasticsearch(self.host)
        logging.info(self.es.info(pretty=True))

    # create index
    def create_index(self, index_name_prefix, index_schema_file):
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        index_name = f"{index_name_prefix}{timestamp}"
        logging.info(f"creating index: {index_name}")

        with open(index_schema_file) as schema_file:
            schema = schema_file.read()

        self.es.indices.create(index=index_name, body=schema)
        return index_name

    # index documents from json files
    def indexer(self, index_name, directory):
        batch_size = 500
        actions = []

        counter = 0
        for filename in os.listdir(directory):
            if filename.endswith(".json") or filename.endswith(".jsonl"):
                filepath = os.path.join(directory, filename)
                with open(filepath) as json_file:
                    for line in json_file:
                        actions.append({
                            "_index": index_name,
                            "_source": json.loads(line)
                        })
                        if len(actions) == batch_size:
                            try:
                                # logging.info(f"first action: {actions[0]}")
                                helpers.bulk(client=self.es, index=index_name, actions=actions)
                            except Exception as e:
                                logging.info(e)
                            actions = []
                        counter += 1
                        if counter % 1000 == 0:
                            logging.info(f"{counter} documents indexed.")

        if actions:
            try:
                # logging.info(f"first action: {actions[0]}")
                helpers.bulk(client=self.es, index=index_name, actions=actions)
            except Exception as e:
                logging.info(e)

        self.es.indices.forcemerge(index=index_name, max_num_segments=1, request_timeout=30)
        self.es.indices.refresh(index=index_name)
        logging.info(f"indexing is done. total {counter} documents.")

    # Move the specified index to the specified alias
    def move_alias(self, index_name, alias_name):
        self.es.indices.refresh(index=index_name)

        old_index_name = None
        try:
            alias_index_list = list(self.es.indices.get_alias(name=alias_name).keys())
            if len(alias_index_list) > 0:
                old_index_name = alias_index_list[0]
                logging.info(f"{alias_name} was pointing to: {old_index_name}")
        except Exception as e:
            logging.error(e)

        if old_index_name is None:
            actions = {"actions": [
                {"add": {"index": index_name, "alias": alias_name}}]
            }
        else:
            actions = {"actions": [
                {"remove": {"index": old_index_name, "alias": alias_name}},
                {"add": {"index": index_name, "alias": alias_name}}]
            }

        logging.info(f"actions: {json.dumps(actions, indent=2)}")

        try:
            self.es.indices.update_aliases(body=actions)
        except Exception as e:
            logging.error(e)
            logging.error(f"{alias_name} is not moved")
            return False

        try:
            self.es.indices.refresh(index=index_name)
            alias_index_list = list(self.es.indices.get_alias(name=alias_name).keys())
            if len(alias_index_list) > 0:
                new_index_name = alias_index_list[0]
                logging.info(f"{alias_name} is pointing to: {new_index_name}")
        except Exception as e:
            logging.error(e)
            logging.error(f"{alias_name} is not pointing to any index")
            return False

        return True

    # Keep two most recently created indices with the specified prefix
    def remove_index(self, prefix, num_to_keep=2):
        all_indices = self.es.indices.get(index=prefix + "*").keys()
        prefixed_indices = [index for index in all_indices if index.startswith(prefix)]

        sorted_indices = sorted(prefixed_indices)
        logging.info(f"list of indices: {sorted_indices}")
        indices_to_keep = sorted_indices[-num_to_keep:]
        logging.info(f"indices to keep: {indices_to_keep}")

        for index in prefixed_indices:
            if index not in indices_to_keep:
                logging.info(f"removing index: {index}")
                try:
                    self.es.indices.refresh(index=index)
                    self.es.indices.delete(index=index)
                    logging.info(f"{index} is removed.")
                except Exception as e:
                    logging.error(e)
                    logging.error(f"{index} is not removed.")

    # Get the count of documents in the specified index
    def index_count(self, index_name):
        # Get the count of documents in the specified index
        count = self.es.count(index=index_name)['count']
        return count

    # Get random 5 documents from the specified index
    def sample_query(self, index_name):
        query = {
            "size": 5,
            "query": {
                "function_score": {
                    "query": {"match_all": {}},
                    "random_score": {}  # Get random documents
                }
            }
        }
        # Execute the query
        result = self.es.search(index=index_name, body=query)
        # Extract and return the documents
        return [hit['_source'] for hit in result['hits']['hits']]


indexing_names = {
    "keyword": {
        "index_prefix": "index_movielens_keyword_",
        "alias_name": "a_movielens_keywords",
        "data_directory": "movielens_index",
        "index_schema": "scripts/keywords_schema.json"
    },
    "embedding": {
        "index_prefix": "index_movielens_embedding_",
        "alias_name": "a_movielens_embeddings",
        "data_directory": "movielens_embedding",
        "index_schema": "scripts/keywords_schema.json"
    }
}


def main():
    es = EsIndexer()
    index_type = "embedding"  # "keyword" or "embedding"
    index_prefix = indexing_names[index_type]["index_prefix"]
    alias_name = indexing_names[index_type]["alias_name"]
    data_directory = indexing_names[index_type]["data_directory"]
    index_schema_file = indexing_names[index_type]["index_schema"]
    index_name = es.create_index(index_prefix, index_schema_file)
    es.indexer(index_name, data_directory)
    index_count = es.index_count(index_name)
    logging.info(f"{index_name} document count: {index_count}")
    logging.info(f"{index_name} sample documents: {es.sample_query(index_name)}")
    if index_count > 40000:
        if es.move_alias(index_name, alias_name=alias_name):
            es.remove_index(index_prefix)


if __name__ == "__main__":
    main()
