from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
import json
from plugins.scraping import ecosure_scraper, ecocash_scraper, econet_scraper, merge_data
from plugins.data_ingestion.ingest import load_documents, load_ground_truth
from config.scraper_config import SCRAPER_CONFIG, CSV_COMBINER_CONFIG, BASE_OUTPUT_DIR

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
    'faq_processing',
    default_args=default_args,
    description='A DAG to scrape FAQs, combine results, and prepare for ingestion',
    schedule_interval=timedelta(days=1),
)

def scrape_ecosure():
    ecosure_scraper.main(SCRAPER_CONFIG['ecosure'])

def scrape_ecocash():
    ecocash_scraper.main(SCRAPER_CONFIG['ecocash'])

def scrape_econet():
    econet_scraper.main(SCRAPER_CONFIG['econet'])

def merge_dataset():
    merge_data.merge_csv_files(CSV_COMBINER_CONFIG)

def load_documents_task(**kwargs):
    documents = load_documents(CSV_COMBINER_CONFIG['output_file'])
    
    # Save documents to a local JSON file
    output_file = os.path.join(BASE_OUTPUT_DIR, 'processed_documents.json')
    with open(output_file, 'w') as f:
        json.dump(documents, f)
    
    return f"Documents loaded and saved to {output_file}"

def load_ground_truth_task(**kwargs):
    ground_truth = load_ground_truth(os.getenv('GROUND_TRUTH_PATH'))
    
    # Save ground truth to a local JSON file
    output_file = os.path.join(BASE_OUTPUT_DIR, 'ground_truth.json')
    with open(output_file, 'w') as f:
        json.dump(ground_truth, f)
    
    return f"Ground truth loaded and saved to {output_file}"

# Define tasks
t1_ecosure = PythonOperator(task_id='scrape_ecosure', python_callable=scrape_ecosure, dag=dag)
t2_ecocash = PythonOperator(task_id='scrape_ecocash', python_callable=scrape_ecocash, dag=dag)
t3_econet = PythonOperator(task_id='scrape_econet', python_callable=scrape_econet, dag=dag)
t4_merge = PythonOperator(task_id='merge_datasets', python_callable=merge_dataset, dag=dag)
t5_load_docs = PythonOperator(task_id='load_documents', python_callable=load_documents_task, dag=dag)
t6_load_ground_truth = PythonOperator(task_id='load_ground_truth', python_callable=load_ground_truth_task, dag=dag)

# Set task dependencies
[t1_ecosure, t2_ecocash, t3_econet] >> t4_merge >> t5_load_docs
t4_merge >> t6_load_ground_truth