from airflow import DAG
from airflow.operators.python_operator import PythonOperator
from datetime import datetime, timedelta
from plugins.rag.rag import get_answer_for_question, evaluate_relevance, save_conversation, save_feedback

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2024, 10, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    'customer_support_rag',
    default_args=default_args,
    description='Customer Support RAG Pipeline',
    schedule_interval=timedelta(days=1),
)

def process_question(**kwargs):
    ti = kwargs['ti']
    question = kwargs['dag_run'].conf.get('question', 'What are your available internet plans?')
    result = get_answer_for_question(question)
    ti.xcom_push(key='rag_result', value=result)
    return result

def evaluate_answer(**kwargs):
    ti = kwargs['ti']
    rag_result = ti.xcom_pull(key='rag_result', task_ids='get_answer')
    relevance, explanation, _ = evaluate_relevance(rag_result['question'], rag_result['answer'])
    ti.xcom_push(key='evaluation', value={'relevance': relevance, 'explanation': explanation})
    return {'relevance': relevance, 'explanation': explanation}

def save_result(**kwargs):
    ti = kwargs['ti']
    rag_result = ti.xcom_pull(key='rag_result', task_ids='get_answer')
    evaluation = ti.xcom_push(key='evaluation', task_ids='evaluate_answer')
    save_conversation(rag_result['id'], rag_result['question'], rag_result)
    return "Result saved successfully"

def process_feedback(**kwargs):
    ti = kwargs['ti']
    rag_result = ti.xcom_pull(key='rag_result', task_ids='get_answer')
    feedback = kwargs['dag_run'].conf.get('feedback', 0)
    result = save_feedback(rag_result['id'], feedback)
    return result['message']

get_answer = PythonOperator(
    task_id='get_answer',
    python_callable=process_question,
    dag=dag,
)

evaluate_answer = PythonOperator(
    task_id='evaluate_answer',
    python_callable=evaluate_answer,
    dag=dag,
)

save_result = PythonOperator(
    task_id='save_result',
    python_callable=save_result,
    dag=dag,
)

process_feedback = PythonOperator(
    task_id='process_feedback',
    python_callable=process_feedback,
    dag=dag,
)

get_answer >> evaluate_answer >> save_result >> process_feedback