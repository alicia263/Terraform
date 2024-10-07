# dags/combined_faq_scraper_dag.py
from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
from plugins.scraping import ecosure_scraper, ecocash_scraper, econet_scraper, merge_data
from plugins.data_ingestion.ingest import (
    load_documents, load_ground_truth, initialize_model,
    initialize_elasticsearch, create_index, ingest_documents
)

# Load environment variables
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
    'combined_faq_scraper_and_ingestion',
    default_args=default_args,
    description='A DAG to scrape FAQs, combine results, and ingest into Elasticsearch',
    schedule_interval=timedelta(days=1),
)

# Scraping tasks
def scrape_ecosure():
    ecosure_scraper.main()

def scrape_ecocash():
    ecocash_scraper.main()

def scrape_econet():
    econet_scraper.main()

def merge_dataset():
    merge_data.merge_csv_files()

def load_documents_task(**kwargs):
    documents = load_documents(os.getenv('DOCUMENTS_PATH'))
    kwargs['ti'].xcom_push(key='documents', value=documents)
    return "Documents loaded successfully"

def load_ground_truth_task(**kwargs):
    ground_truth = load_ground_truth(os.getenv('GROUND_TRUTH_PATH'))
    kwargs['ti'].xcom_push(key='ground_truth', value=ground_truth)
    return "Ground truth loaded successfully"

def initialize_model_task(**kwargs):
    model = initialize_model(os.getenv('MODEL_NAME'))
    return f"Model {os.getenv('MODEL_NAME')} initialized successfully"

def initialize_elasticsearch_task(**kwargs):
    es_client = initialize_elasticsearch(os.getenv('ELASTIC_URL'))
    return f"Connected to Elasticsearch at {os.getenv('ELASTIC_URL')}"

def create_index_task(**kwargs):
    es_client = initialize_elasticsearch(os.getenv('ELASTIC_URL'))
    create_index(es_client, os.getenv('INDEX_NAME'))
    return f"Index {os.getenv('INDEX_NAME')} created successfully"

def ingest_documents_task(**kwargs):
    ti = kwargs['ti']
    documents = ti.xcom_pull(key='documents', task_ids='load_documents')
    es_client = initialize_elasticsearch(os.getenv('ELASTIC_URL'))
    model = initialize_model(os.getenv('MODEL_NAME'))
    ingest_documents(es_client, os.getenv('INDEX_NAME'), documents, model)
    return "Documents ingested successfully"

# Define tasks
t1_ecosure = PythonOperator(
    task_id='scrape_ecosure',
    python_callable=scrape_ecosure,
    dag=dag,
)

t2_ecocash = PythonOperator(
    task_id='scrape_ecocash',
    python_callable=scrape_ecocash,
    dag=dag,
)

t3_econet = PythonOperator(
    task_id='scrape_econet',
    python_callable=scrape_econet,
    dag=dag,
)

t4_merge = PythonOperator(
    task_id='merge_datasets',
    python_callable=merge_dataset,
    dag=dag,
)



t5_load_docs = PythonOperator(
    task_id='load_documents',
    python_callable=load_documents_task,
    dag=dag,
)

t6_load_ground_truth = PythonOperator(
    task_id='load_ground_truth',
    python_callable=load_ground_truth_task,
    dag=dag,
)

t7_init_model = PythonOperator(
    task_id='initialize_model',
    python_callable=initialize_model_task,
    dag=dag,
)

t8_init_es = PythonOperator(
    task_id='initialize_elasticsearch',
    python_callable=initialize_elasticsearch_task,
    dag=dag,
)

t9_create_index = PythonOperator(
    task_id='create_index',
    python_callable=create_index_task,
    dag=dag,
)

t10_ingest_docs = PythonOperator(
    task_id='ingest_documents',
    python_callable=ingest_documents_task,
    dag=dag,
)


# Set task dependencies
[t1_ecosure, t2_ecocash, t3_econet] >> t4_merge >> t5_load_docs
[t5_load_docs, t6_load_ground_truth, t7_init_model] >> t8_init_es >> t9_create_index >> t10_ingest_docs