from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.trigger_dagrun import TriggerDagRunOperator
from datetime import timedelta
from common.constants import DEFAULT_ARGS
from common.utils import load_env_vars
from plugins.scraping import ecosure_scraper, ecocash_scraper, econet_scraper, merge_data

load_env_vars()

dag = DAG(
    'faq_scraping',
    default_args=DEFAULT_ARGS,
    description='A DAG to scrape FAQs and combine results',
    schedule_interval=timedelta(days=1),
)

def scrape_ecosure():
    ecosure_scraper.main()

def scrape_ecocash():
    ecocash_scraper.main()

def scrape_econet():
    econet_scraper.main()

def merge_dataset():
    merge_data.merge_csv_files()

t1_ecosure = PythonOperator(task_id='scrape_ecosure', python_callable=scrape_ecosure, dag=dag)
t2_ecocash = PythonOperator(task_id='scrape_ecocash', python_callable=scrape_ecocash, dag=dag)
t3_econet = PythonOperator(task_id='scrape_econet', python_callable=scrape_econet, dag=dag)
t4_merge = PythonOperator(task_id='merge_datasets', python_callable=merge_dataset, dag=dag)
t5_trigger_processing = TriggerDagRunOperator(
    task_id='trigger_processing_dag',
    trigger_dag_id='faq_processing',
    dag=dag,
)

[t1_ecosure, t2_ecocash, t3_econet] >> t4_merge >> t5_trigger_processing