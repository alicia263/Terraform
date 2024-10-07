import json
import pandas as pd
import logging
from sentence_transformers import SentenceTransformer
from elasticsearch import Elasticsearch
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def load_documents(file_path):
    file_path = file_path or os.getenv('DOCUMENTS_PATH')
    logging.info(f"Loading documents from {file_path}")
    with open(file_path, 'r') as f:
        return json.load(f)

def load_ground_truth(file_path):
    file_path = file_path or os.getenv('GROUND_TRUTH_PATH')
    logging.info(f"Loading ground truth from {file_path}")
    df = pd.read_csv(file_path)
    return df.to_dict(orient='records')

def initialize_model(model_name):
    model_name = model_name or os.getenv('MODEL_NAME', 'all-MiniLM-L6-v2')
    logging.info(f"Initializing model: {model_name}")
    return SentenceTransformer(model_name)

def initialize_elasticsearch(host):
    host = host or os.getenv('ELASTIC_URL')
    logging.info(f"Connecting to Elasticsearch at {host}")
    return Elasticsearch(host)

def create_index(es_client, index_name):
    index_name = index_name or os.getenv('INDEX_NAME', 'faq_index')
    logging.info(f"Creating index: {index_name}")
    index_settings = {
        "settings": {
            "number_of_shards": 1,
            "number_of_replicas": 0
        },
        "mappings": {
            "properties": {
                "question": {"type": "text"},
                "answer": {"type": "text"},
                "id": {"type": "text"},
                "question_answer_vector": {
                    "type": "dense_vector",
                    "dims": 384,
                    "index": True,
                    "similarity": "cosine"
                },
            }
        }
    }
    es_client.indices.delete(index=index_name, ignore_unavailable=True)
    es_client.indices.create(index=index_name, body=index_settings)

def ingest_documents(es_client, index_name, documents, model):
    index_name = index_name or os.getenv('INDEX_NAME', 'faq_index')
    logging.info(f"Ingesting documents into index: {index_name}")
    for doc in documents:
        question = doc['Question']
        answer = doc['Answer']
        
        es_doc = {
            "question": question,
            "answer": answer,
            "question_answer_vector": model.encode(question + ' ' + answer).tolist()
        }
        
        es_client.index(index=index_name, document=es_doc)
    logging.info("Document ingestion completed.")