import os
import sys
import logging
import re
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends, Form, Request
from fastapi.security import APIKeyHeader
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from typing import Dict, Optional
from dotenv import load_dotenv
from starlette.middleware.sessions import SessionMiddleware
from twilio.twiml.messaging_response import MessagingResponse
from rag import rag, submit_feedback
from plugins.db_init.db import get_db_connection, save_feedback



load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Context manager to handle the lifespan of the FastAPI app.
    
    During startup, it checks the database connection, and during shutdown,
    it logs the shutdown message..
    
    Args:
        app (FastAPI): FastAPI application instance.
    """
    # Startup
    logging.info("Checking database connection...")
    conn = get_db_connection()
    if conn is None:
        logging.error("Failed to connect to the database. Please check your database configuration.")
    else:
        conn.close()
        logging.info("Successfully connected to the database.")
    yield
    # Shutdown
    logging.info("Shutting down...")

app = FastAPI(lifespan=lifespan)
app.add_middleware(SessionMiddleware, secret_key=os.getenv("SESSION_SECRET_KEY", "your-secret-key"))
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
conversation_history = {}

def get_api_key(api_key: Optional[str] = Depends(api_key_header)) -> Optional[str]:
    """
    Get and validate API key from the request header.

    Args:
        api_key (Optional[str]): API key from the request header.

    Returns:
        Optional[str]: The API key if valid, otherwise raises an HTTPException.
    """
    if api_key is None or api_key == os.getenv("API_KEY", "your-api-key"):
        return api_key
    raise HTTPException(status_code=401, detail="Invalid API Key")

def get_conversation_history(conversation_id: str) -> list:
    """
    Retrieve conversation history for a given user ID.

    Args:
        conversation_id (str): Unique identifier for the conversation (user ID).

    Returns:
        list: List of conversation history entries.
    """
    return conversation_history.get(conversation_id, [])

def add_to_conversation_history(conversation_id: str, role: str, content: str):
    """
    Add a message to the conversation history.

    Args:
        conversation_id (str): Unique identifier for the conversation (user ID).
        role (str): The role of the message sender (e.g., 'user', 'assistant').
        content (str): The message content.
    """
    if conversation_id not in conversation_history:
        conversation_history[conversation_id] = []
    conversation_history[conversation_id].append({"role": role, "content": content})

def format_question_with_history(question: str, history: list) -> str:
    """
    Format the user's question by appending the previous conversation history.

    Args:
        question (str): The user's question.
        history (list): The conversation history.

    Returns:
        str: Formatted question with history.
    """
    formatted_history = "\n".join([f"{'User' if item['role'] == 'user' else 'Assistant'}: {item['content']}" for item in history[-5:]])
    return f"Previous conversation:\n{formatted_history}\n\nNew question: {question}"

def is_end_of_conversation(message: str) -> bool:
    """
    Determine if the message indicates the end of the conversation.

    Args:
        message (str): The user's message.

    Returns:
        bool: True if the message signifies the end, False otherwise.
    """
    end_phrases = [
        r'\b(no|nope|that\'s all|nothing else|i\'m good|i\'m done|that\'s it|bye|goodbye|thanks|thank you)\b',
        r'\b(that\'s all for now|no more questions|all set|that\'s everything)\b'
    ]
    return any(re.search(phrase, message, re.IGNORECASE) for phrase in end_phrases)

@app.post("/whatsapp")
async def whatsapp(request: Request, Body: str = Form(...), From: str = Form(...)):
    """
    Endpoint to handle incoming WhatsApp messages and interact with the RAG model.

    Args:
        request (Request): FastAPI request object.
        Body (str): The content of the user's message.
        From (str): The user ID (e.g., phone number).

    Returns:
        PlainTextResponse: The response containing the assistant's reply.
    """
    try:
        incoming_msg = Body.strip()
        user_id = From
        logging.info(f"Received WhatsApp message from {user_id}: {incoming_msg}")
        
        if incoming_msg in ['👍', '👎', '🤔']:
            return await process_whatsapp_feedback(request, incoming_msg, user_id)
        
        if is_end_of_conversation(incoming_msg):
            bot_resp = MessagingResponse()
            msg = bot_resp.message()
            msg.body("Alright! It was a pleasure assisting you. If you need help in the future, feel free to message again. Take care!")
            return PlainTextResponse(content=str(bot_resp), media_type="application/xml")
        
        history = get_conversation_history(user_id)
        formatted_question = format_question_with_history(incoming_msg, history)
        
        answer_data = rag(formatted_question)
        answer = answer_data['answer']
        conversation_id = answer_data['id']
        
        add_to_conversation_history(user_id, "user", incoming_msg)
        add_to_conversation_history(user_id, "assistant", answer)
        
        logging.info(f"Generated answer for WhatsApp user {user_id}: {answer}")
        
        bot_resp = MessagingResponse()
        msg = bot_resp.message()
        msg.body(answer)
        msg.body("\n\nWas this answer helpful? React with:\n👍 - Yes\n👎 - No\n🤔 - Partly")
        
        request.session['last_conversation_id'] = conversation_id
        
        return PlainTextResponse(content=str(bot_resp), media_type="application/xml")
    except Exception as e:
        logging.error(f"Error processing WhatsApp message: {str(e)}")
        raise HTTPException(status_code=500, detail="Error processing your message")

async def process_whatsapp_feedback(request: Request, feedback: str, user_id: str):
    """
    Process user feedback based on a WhatsApp message.

    Args:
        request (Request): FastAPI request object.
        feedback (str): Feedback message from the user.
        user_id (str): User identifier (e.g., phone number).

    Returns:
        PlainTextResponse: The response after feedback is processed.
    """
    try:
        logging.info(f"Processing WhatsApp feedback from {user_id}: {feedback}")
        
        conversation_id = request.session.get('last_conversation_id')
        if not conversation_id:
            raise ValueError("No active conversation found. Please ask a question first.")
        
        feedback_value = {
            '👍': 1,   
            '👎': -1,  
            '🤔': 0    
        }[feedback]
        
        result = submit_feedback(conversation_id, feedback_value)
        
        bot_resp = MessagingResponse()
        msg = bot_resp.message()
        if result['status'] == 'success':
            msg.body("Thank you for your feedback! If you have any more questions, feel free to ask.")
        else:
            msg.body("There was an issue saving your feedback. How can I assist you further?")
        
        return PlainTextResponse(content=str(bot_resp), media_type="application/xml")
    except ValueError as ve:
        bot_resp = MessagingResponse()
        msg = bot_resp.message()
        msg.body(str(ve))
        return PlainTextResponse(content=str(bot_resp), media_type="application/xml")
    except Exception as e:
        logging.error(f"Error processing WhatsApp feedback: {str(e)}")
        raise HTTPException(status_code=500, detail="Error processing your feedback")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
