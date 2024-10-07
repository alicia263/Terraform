import os
import time
import uuid
from typing import Dict, Any, Tuple
import logging
import json
from sentence_transformers import SentenceTransformer
from elasticsearch import Elasticsearch
from groq import Groq
from db import save_conversation, save_feedback
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
load_dotenv()

model_name = os.getenv('MODEL_NAME', 'multi-qa-MiniLM-L6-cos-v1')
es_url = os.getenv('ELASTICSEARCH_URL', 'http://elasticsearch:9200')
groq_api_key = os.getenv('GROQ_API_KEY')

model = SentenceTransformer(model_name)
es_client = Elasticsearch(es_url)

def elastic_search_knn(field: str, vector: list, index_name: str = "customer_support") -> list:
    """Performs a K-Nearest Neighbors (KNN) search on Elasticsearch.

    Args:
        field (str): The field in the index that contains the vector to search against.
        vector (list): The query vector to perform the search with.
        index_name (str): The name of the Elasticsearch index. Defaults to "customer-support".

    Returns:
        list: A list of search results containing questions and answers.
    """
    knn = {
        "field": field,
        "query_vector": vector,
        "k": 5,
        "num_candidates": 10000
    }
    search_query = {
        "knn": knn,
        "_source": ["question", "answer"]
    }
    es_results = es_client.search(
        index=index_name,
        body=search_query
    )
    return [hit['_source'] for hit in es_results['hits']['hits']]

def question_answer_vector_knn(question: str) -> list:
    """Encodes the question and performs a KNN search on Elasticsearch.

    Args:
        question (str): The input question to encode and search.

    Returns:
        list: A list of relevant question-answer pairs from Elasticsearch.
    """
    v_q = model.encode(question)
    return elastic_search_knn('question_answer_vector', v_q)

def build_prompt(query: str, search_results: list) -> str:
    """Builds a prompt for a customer support assistant based on search results.

    Args:
        query (str): The original query from the customer.
        search_results (list): The search results containing relevant questions and answers.

    Returns:
        str: A formatted prompt string ready for language model consumption.
    """
    prompt_template = """
    You are a highly knowledgeable, friendly, and empathetic customer support assistant for a telecommunications company...
    (continued)
    """
    context = "\n\n".join([f"question: {doc['question']}\nanswer: {doc['answer']}" for doc in search_results])
    return prompt_template.format(question=query, context=context).strip()

def llm(prompt: str, model: str = 'llama-3.1-70b-versatile') -> Tuple[str, Dict[str, Any], float]:
    """Generates a response using a large language model (LLM) based on a given prompt.

    Args:
        prompt (str): The prompt to send to the LLM.
        model (str): The LLM model to use. Defaults to 'llama-3.1-70b-versatile'.

    Returns:
        Tuple[str, Dict[str, Any], float]: The generated answer, token usage, and response time.
    """
    client = Groq()
    start_time = time.time()
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}]
    )
    end_time = time.time()

    return response.choices[0].message.content, response.usage.to_dict(), end_time - start_time

def calculate_openai_cost(tokens: int, model: str) -> float:
    """Calculates the cost of OpenAI API usage based on token count.

    Args:
        tokens (int): The total number of tokens used.
        model (str): The name of the model used.

    Returns:
        float: The estimated cost in USD.
    """
    return tokens * 0.00002  # Placeholder for actual pricing

def evaluate_relevance(question: str, answer: str) -> Tuple[str, str, Dict[str, int]]:
    """Evaluates the relevance of the generated answer to the given question.

    Args:
        question (str): The input question.
        answer (str): The generated answer to evaluate.

    Returns:
        Tuple[str, str, Dict[str, int]]: The relevance rating, explanation, and token usage.
    """
    logging.info("Evaluating relevance of generated answer...")
    prompt_template = """
    You are an expert evaluator for a Retrieval-Augmented Generation (RAG) system...
    (continued)
    """
    prompt = prompt_template.format(question=question, answer=answer)
    evaluation, tokens, _ = llm(prompt)

    try:
        json_eval = json.loads(evaluation)
        logging.info(f"Evaluation result: {json_eval}")
        return json_eval['Relevance'], json_eval['Explanation'], tokens
    except json.JSONDecodeError:
        logging.error("Failed to parse evaluation JSON.")
        return "UNKNOWN", "Failed to parse evaluation", tokens

def rag(query: str, model: str = 'llama-3.1-70b-versatile') -> Dict[str, Any]:
    """Executes the Retrieval-Augmented Generation (RAG) process for a query.

    Args:
        query (str): The input query string.
        model (str): The LLM model to use. Defaults to 'llama-3.1-70b-versatile'.

    Returns:
        Dict[str, Any]: A dictionary containing the RAG results, including the question, answer, relevance, and cost.
    """
    conversation_id = str(uuid.uuid4())
    question = query
    search_results = question_answer_vector_knn(question)
    prompt = build_prompt(question, search_results)
    answer, tokens, response_time = llm(prompt, model=model)
    relevance, relevance_explanation, eval_tokens = evaluate_relevance(question, answer)
    openai_cost = calculate_openai_cost(tokens['total_tokens'] + eval_tokens['total_tokens'], model)

    conversation_data = {
        "id": conversation_id,
        "question": question,
        "answer": answer,
        "model_used": model,
        "response_time": response_time,
        "relevance": relevance,
        "relevance_explanation": relevance_explanation,
        "prompt_tokens": tokens['prompt_tokens'],
        "completion_tokens": tokens['completion_tokens'],
        "total_tokens": tokens['total_tokens'],
        "eval_prompt_tokens": eval_tokens['prompt_tokens'],
        "eval_completion_tokens": eval_tokens['completion_tokens'],
        "eval_total_tokens": eval_tokens['total_tokens'],
        "openai_cost": openai_cost
    }

    save_conversation(conversation_id, question, conversation_data)
    return conversation_data

def submit_feedback(conversation_id: str, feedback: int) -> Dict[str, Any]:
    """Submits user feedback for a given conversation.

    Args:
        conversation_id (str): The ID of the conversation.
        feedback (int): The user feedback score (1 for positive, -1 for negative).

    Returns:
        Dict[str, Any]: The status and message of the feedback submission.
    """
    try:
        save_feedback(conversation_id, feedback)
        return {"status": "success", "message": "Feedback saved successfully"}
    except Exception as e:
        logging.error(f"Error saving feedback: {str(e)}")
        return {"status": "error", "message": f"Failed to save feedback: {str(e)}"}

def get_answer_for_question(question: str) -> Dict[str, Any]:
    """Gets an answer for a given question using the RAG pipeline.

    Args:
        question (str): The question to answer.

    Returns:
        Dict[str, Any]: The generated answer and related metadata.
    """
    return rag(question)

if __name__ == "__main__":
    custom_question = input("Enter your question: ")
    answer_data = get_answer_for_question(custom_question)
    print(f"\nQuestion: {custom_question}")
    print(f"Answer: {answer_data['answer']}")
    print(f"\nRelevance: {answer_data['relevance']}")
    print(f"Explanation: {answer_data['relevance_explanation']}")
    print(f"\nResponse Time: {answer_data['response_time']:.2f} seconds")
    print(f"Total Tokens: {answer_data['total_tokens']}")
    print(f"Estimated Cost: ${answer_data['openai_cost']:.6f}")

    feedback = input("Was this answer helpful? (1 for yes, -1 for no): ")
    feedback_result = submit_feedback(answer_data['id'], int(feedback))
    print(feedback_result['message'])
