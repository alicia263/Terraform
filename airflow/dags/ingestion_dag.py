from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
from plugins.data_ingestion.ingest import initialize_model, initialize_elasticsearch, create_index, ingest_documents
import logging
import json

load_dotenv()

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2024, 10, 2),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    'faq_ingestion',
    default_args=default_args,
    description='A DAG to ingest FAQ data into Elasticsearch',
    schedule_interval=None,
)

def get_env_var(var_name):
    value = os.getenv(var_name)
    if value is None:
        raise ValueError(f"Environment variable {var_name} is not set")
    return value

def initialize_model_task(**kwargs):
    model = initialize_model(get_env_var('MODEL_NAME'))
    return f"Model {get_env_var('MODEL_NAME')} initialized successfully"

def initialize_elasticsearch_task(**kwargs):
    es_client = initialize_elasticsearch(get_env_var('ELASTIC_URL'))
    return f"Connected to Elasticsearch at {get_env_var('ELASTIC_URL')}"

def create_index_task(**kwargs):
    es_client = initialize_elasticsearch(get_env_var('ELASTIC_URL'))
    create_index(es_client, get_env_var('INDEX_NAME'))
    return f"Index {get_env_var('INDEX_NAME')} created successfully"

def ingest_documents_task(**kwargs):
    # Load documents from the local JSON file
    input_file = '/opt/airflow/data/processed_documents.json'
    try:
        with open(input_file, 'r') as f:
            documents = json.load(f)
    except FileNotFoundError:
        error_msg = f"Document file not found: {input_file}. Make sure the 'faq_processing' DAG has run successfully."
        logging.error(error_msg)
        raise FileNotFoundError(error_msg)
    
    logging.info(f"Loaded documents from file: {input_file}")
    
    if not documents:
        error_msg = "No documents found in the input file."
        logging.error(error_msg)
        raise ValueError(error_msg)
    
    es_client = initialize_elasticsearch(get_env_var('ELASTIC_URL'))
    model = initialize_model(get_env_var('MODEL_NAME'))
    
    try:
        ingest_documents(es_client, get_env_var('INDEX_NAME'), documents, model)
        return "Documents ingested successfully"
    except Exception as e:
        error_msg = f"Error ingesting documents: {str(e)}"
        logging.error(error_msg)
        raise

def log_env_vars(**kwargs):
    env_vars = ['MODEL_NAME', 'ELASTIC_URL', 'INDEX_NAME', 'DOCUMENTS_PATH', 'GROUND_TRUTH_PATH']
    for var in env_vars:
        value = os.getenv(var)
        if value:
            logging.info(f"Environment Variable - {var}: {value}")
        else:
            logging.warning(f"Environment Variable {var} is not set")
    return "Environment variables logged"

t0_log_env = PythonOperator(task_id='log_environment_variables', python_callable=log_env_vars, dag=dag)
t1_init_model = PythonOperator(task_id='initialize_model', python_callable=initialize_model_task, dag=dag)
t2_init_es = PythonOperator(task_id='initialize_elasticsearch', python_callable=initialize_elasticsearch_task, dag=dag)
t3_create_index = PythonOperator(task_id='create_index', python_callable=create_index_task, dag=dag)
t4_ingest_docs = PythonOperator(task_id='ingest_documents', python_callable=ingest_documents_task, dag=dag)

t0_log_env >> t1_init_model >> t2_init_es >> t3_create_index >> t4_ingest_docs