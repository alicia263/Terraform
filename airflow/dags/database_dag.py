from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime
import os
from dotenv import load_dotenv
from plugins.db_init.db import init_db

# Define a function to encapsulate the logic
def initialize_database():
    # Set environment variable to disable timezone check
    os.environ['RUN_TIMEZONE_CHECK'] = '0'

    # Load environment variables from .env file
    load_dotenv()

    # Initialize the database
    print("Initializing database...")
    init_db()
    print("Database initialization complete.")

# Define default arguments for the DAG
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'retries': 1,
}

# Create the DAG
with DAG(
    'initialize_db_dag1',
    default_args=default_args,
    description='A DAG to initialize the database',
    schedule_interval=None,  # Set to None to run manually
    start_date=datetime(2024, 10, 1),
    catchup=False,
) as dag:

    # Define the Python task using PythonOperator
    initialize_db_task = PythonOperator(
        task_id='initialize_database_task',
        python_callable=initialize_database,  # This points to the function that will be called
    )

    # Set task dependencies (if you have multiple tasks, you can chain them)
    initialize_db_task
