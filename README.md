# Demo of ElasticSearch

This project demo the keyword search and embedding based search of ElasticSearch.

## Environment

- Indexing Data: [MovieLens 25M Dataset](https://grouplens.org/datasets/movielens/25m/)
- [ElasticSearch 8.13.3](https://www.elastic.co/guide/en/elasticsearch/reference/8.13/release-notes-8.13.3.html)
- [Kibana 8.13.3](https://www.elastic.co/downloads/past-releases/kibana-8-13-3)
- This project is coded in:
  - Python 3.11.9
  - Pycharm 2024.1 with [codeium](https://codeium.com) and [Black](https://github.com/psf/black) formatter plugin

## Project Files


- scripts:
  - transformer.py: extract and transformer MovieLens 25M Dataset into one indexable data set in json format
  - indexer.py: load and index indexable data set into elasticsearch keyword index and embedding index
  

- web: demo the elasticsearch results

