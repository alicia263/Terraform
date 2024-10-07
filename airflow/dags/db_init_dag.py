from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python_operator import PythonOperator
from airflow.operators.dummy_operator import DummyOperator

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Disable timezone check for initial setup
os.environ['RUN_TIMEZONE_CHECK'] = '0'

# Import all functions from db.py
from plugins.db_init.db import (
    init_db, check_timezone, get_recent_conversations, get_feedback_stats,
    get_relevance_stats, get_avg_response_time, get_model_usage_stats,
    get_token_usage_stats
)

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2023, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    'database_operations',
    default_args=default_args,
    description='Initialize database and perform various database operations',
    schedule_interval=None,
    catchup=False
)

# Start task
start = DummyOperator(task_id='start', dag=dag)

# Initialize database
init_db_task = PythonOperator(
    task_id='init_db',
    python_callable=init_db,
    dag=dag
)

# Check timezone
check_timezone_task = PythonOperator(
    task_id='check_timezone',
    python_callable=check_timezone,
    dag=dag
)

# Get recent conversations
get_recent_conversations_task = PythonOperator(
    task_id='get_recent_conversations',
    python_callable=get_recent_conversations,
    op_kwargs={'limit': 5},
    dag=dag
)

# Get feedback stats
get_feedback_stats_task = PythonOperator(
    task_id='get_feedback_stats',
    python_callable=get_feedback_stats,
    dag=dag
)

# Get relevance stats
get_relevance_stats_task = PythonOperator(
    task_id='get_relevance_stats',
    python_callable=get_relevance_stats,
    dag=dag
)

# Get average response time
get_avg_response_time_task = PythonOperator(
    task_id='get_avg_response_time',
    python_callable=get_avg_response_time,
    dag=dag
)

# Get model usage stats
get_model_usage_stats_task = PythonOperator(
    task_id='get_model_usage_stats',
    python_callable=get_model_usage_stats,
    dag=dag
)

# Get token usage stats
get_token_usage_stats_task = PythonOperator(
    task_id='get_token_usage_stats',
    python_callable=get_token_usage_stats,
    dag=dag
)

# End task
end = DummyOperator(task_id='end', dag=dag)

# Define the task dependencies
start >> init_db_task >> check_timezone_task

check_timezone_task >> [
    get_recent_conversations_task,
    get_feedback_stats_task,
    get_relevance_stats_task,
    get_avg_response_time_task,
    get_model_usage_stats_task,
    get_token_usage_stats_task
] >> end