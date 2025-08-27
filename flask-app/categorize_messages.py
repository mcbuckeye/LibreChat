#!/usr/bin/env python3
import os
import logging
import sqlite3
import json
import requests
from datetime import datetime
from pymongo import MongoClient
from bson.objectid import ObjectId
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Configuration
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://mongodb:27017/")
SQLITE_DB_PATH = os.getenv("SQLITE_DB_PATH", "message_categories.db")

# Category definitions
CATEGORIES = [
    "general_information_request",
    "technical_inquiry",
    "programming_request",
    "medical_inquiry",
    "business_analysis",
    "document_creation",
    "content_editing",
    "translation_request",
    "data_analysis",
    "technical_support",
    "summarization",
    "creative_writing",
    "research_request",
    "comparison",
    "process_guidance",
    "feedback_request",
    "email_drafting",
    "legal_regulatory_inquiry",
    "educational_content",
    "brainstorming",
    "other"
]

def connect_to_mongodb():
    """Connect to MongoDB and return the database client."""
    try:
        client = MongoClient(MONGODB_URI)
        db = client["LibreChat"]
        logger.info("Successfully connected to MongoDB")
        return db
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {str(e)}")
        raise

def setup_sqlite_db():
    """Set up the SQLite database with the necessary tables."""
    try:
        conn = sqlite3.connect(SQLITE_DB_PATH)
        cursor = conn.cursor()
        
        # Create tables if they don't exist
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS message_categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id TEXT NOT NULL,
            message_id TEXT NOT NULL,
            message_text TEXT NOT NULL,
            category TEXT NOT NULL,
            confidence REAL,
            processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(message_id)
        )
        ''')
        
        # Create an index on conversation_id for faster lookups
        cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_conversation_id 
        ON message_categories(conversation_id)
        ''')
        
        conn.commit()
        logger.info("SQLite database setup complete")
        return conn
    except Exception as e:
        logger.error(f"Failed to set up SQLite database: {str(e)}")
        raise

def get_first_messages_from_conversations(db, limit=None):
    """
    Retrieve the first message from each conversation in MongoDB.
    
    Args:
        db: MongoDB database connection
        limit: Optional limit on the number of conversations to process
    
    Returns:
        List of dictionaries containing conversation_id and first message
    """
    try:
        conversations_collection = db["conversations"]
        messages_collection = db["messages"]
        
        # Get all conversation IDs
        conversation_query = {}
        if limit:
            conversations = list(conversations_collection.find(conversation_query).limit(limit))
        else:
            conversations = list(conversations_collection.find(conversation_query))
        
        logger.info(f"Found {len(conversations)} conversations")
        
        # Log a sample conversation to understand its structure
        if conversations:
            sample_conversation = conversations[0]
            logger.info(f"Sample conversation structure: {sample_conversation.keys()}")
        
        # Get a sample message to understand its structure
        sample_message = messages_collection.find_one()
        if sample_message:
            logger.info(f"Sample message structure: {sample_message.keys()}")
            logger.info(f"Sample message conversationId field: {sample_message.get('conversationId')}")
        else:
            logger.warning("No messages found in the messages collection")
        
        first_messages = []
        for conversation in conversations:
            # Try to get the conversationId field first, then fall back to _id
            if "conversationId" in conversation:
                conversation_id = str(conversation.get("conversationId"))
                logger.info(f"Using conversationId field: {conversation_id}")
            else:
                conversation_id = str(conversation.get("_id"))
                logger.info(f"Using _id field: {conversation_id}")
            
            # Find the first message in this conversation
            query = {"conversationId": conversation_id}
            count = messages_collection.count_documents(query)
            
            if count > 0:
                logger.info(f"Found {count} messages with conversationId={conversation_id}")
            else:
                logger.warning(f"No messages found for conversation {conversation_id}")
                continue
            
            # Sort by createdAt to ensure we get the first message
            first_message = messages_collection.find_one(
                query,
                sort=[("createdAt", 1)]
            )
            
            if first_message:
                # Extract the content from the message
                message_content = ""
                
                # Try different field names for the message content
                content_field = None
                for field in ["content", "text", "message", "body"]:
                    if field in first_message:
                        content_field = field
                        break
                
                if content_field:
                    content = first_message[content_field]
                    if isinstance(content, list):
                        # Handle content as a list of parts
                        for part in content:
                            if isinstance(part, dict) and "text" in part:
                                message_content += part["text"] + " "
                            elif isinstance(part, str):
                                message_content += part + " "
                    elif isinstance(content, str):
                        # Handle content as a string
                        message_content = content
                    elif isinstance(content, dict) and "text" in content:
                        # Handle content as a dict with text field
                        message_content = content["text"]
                
                if message_content.strip():
                    first_messages.append({
                        "conversation_id": conversation_id,
                        "message_id": str(first_message.get("_id")),
                        "message_text": message_content.strip()
                    })
        
        logger.info(f"Retrieved {len(first_messages)} first messages")
        return first_messages
    
    except Exception as e:
        logger.error(f"Error retrieving first messages: {str(e)}")
        raise

def categorize_message_with_ollama(message_text):
    """
    Use Ollama to categorize the message.
    
    Args:
        message_text: The text of the message to categorize
    
    Returns:
        Dictionary with category and confidence
    """
    try:
        # Log the Ollama URL and model being used
        ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        ollama_model = os.getenv("OLLAMA_MODEL", "llama3")
        logger.info(f"Using Ollama URL: {ollama_url} with model: {ollama_model}")
        
        prompt = f"""
        Analyze the following message and categorize it into exactly one of these categories:
        {', '.join(CATEGORIES)}
        
        Message: "{message_text}"
        
        Respond with a JSON object containing:
        1. "category": The single most appropriate category from the list
        2. "confidence": A number between 0 and 1 indicating your confidence
        3. "reasoning": A brief explanation of why you chose this category
        
        JSON response only:
        """
        
        response = requests.post(
            f"{ollama_url}/api/generate",
            json={
                "model": ollama_model,
                "prompt": prompt,
                "stream": False
            }
        )
        
        if response.status_code != 200:
            logger.error(f"Ollama API error: {response.text}")
            return {"category": "other", "confidence": 0.0}
        
        # Extract the JSON from the response
        response_text = response.json().get("response", "")
        
        # Find JSON in the response (it might be embedded in text)
        try:
            # Try to find JSON object in the response
            json_start = response_text.find("{")
            json_end = response_text.rfind("}") + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = response_text[json_start:json_end]
                result = json.loads(json_str)
                
                # Validate the result
                if "category" in result and result["category"] in CATEGORIES:
                    return {
                        "category": result["category"],
                        "confidence": float(result.get("confidence", 0.7))
                    }
            
            # If we couldn't parse JSON or it's invalid, try to extract category directly
            for category in CATEGORIES:
                if category.lower() in response_text.lower():
                    return {"category": category, "confidence": 0.5}
            
            # Default fallback
            return {"category": "other", "confidence": 0.3}
            
        except json.JSONDecodeError:
            logger.warning(f"Could not parse JSON from Ollama response: {response_text}")
            # Try to extract category directly from text
            for category in CATEGORIES:
                if category.lower() in response_text.lower():
                    return {"category": category, "confidence": 0.5}
            return {"category": "other", "confidence": 0.3}
    
    except Exception as e:
        logger.error(f"Error categorizing message with Ollama: {str(e)}")
        return {"category": "other", "confidence": 0.0}

def save_categorization_to_sqlite(conn, message_data, categorization):
    """
    Save the message categorization to SQLite.
    
    Args:
        conn: SQLite connection
        message_data: Dictionary with message information
        categorization: Dictionary with category and confidence
    """
    try:
        cursor = conn.cursor()
        
        # Check if this message has already been processed
        cursor.execute(
            "SELECT id FROM message_categories WHERE message_id = ?",
            (message_data["message_id"],)
        )
        
        if cursor.fetchone():
            # Update existing record
            cursor.execute(
                """
                UPDATE message_categories 
                SET category = ?, confidence = ?, processed_at = CURRENT_TIMESTAMP
                WHERE message_id = ?
                """,
                (
                    categorization["category"],
                    categorization["confidence"],
                    message_data["message_id"]
                )
            )
        else:
            # Insert new record
            cursor.execute(
                """
                INSERT INTO message_categories 
                (conversation_id, message_id, message_text, category, confidence)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    message_data["conversation_id"],
                    message_data["message_id"],
                    message_data["message_text"],
                    categorization["category"],
                    categorization["confidence"]
                )
            )
        
        conn.commit()
    
    except Exception as e:
        logger.error(f"Error saving categorization to SQLite: {str(e)}")
        conn.rollback()
        raise

def get_category_statistics(conn):
    """
    Get statistics on message categories.
    
    Args:
        conn: SQLite connection
    
    Returns:
        Dictionary with category statistics
    """
    try:
        cursor = conn.cursor()
        
        # Get counts by category
        cursor.execute(
            """
            SELECT category, COUNT(*) as count
            FROM message_categories
            GROUP BY category
            ORDER BY count DESC
            """
        )
        
        category_counts = {}
        for row in cursor.fetchall():
            category_counts[row[0]] = row[1]
        
        # Get total count
        cursor.execute("SELECT COUNT(*) FROM message_categories")
        total_count = cursor.fetchone()[0]
        
        return {
            "total_messages": total_count,
            "category_counts": category_counts
        }
    
    except Exception as e:
        logger.error(f"Error getting category statistics: {str(e)}")
        raise

def get_processed_message_ids(conn):
    """
    Get the IDs of messages that have already been processed.
    
    Args:
        conn: SQLite connection
    
    Returns:
        Set of message IDs that have already been processed
    """
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT message_id FROM message_categories")
        return set(row[0] for row in cursor.fetchall())
    except Exception as e:
        logger.error(f"Error getting processed message IDs: {str(e)}")
        return set()

def main(limit=None, force_reprocess=False):
    """
    Main function to run the categorization process.
    
    Args:
        limit: Optional limit on the number of conversations to process
        force_reprocess: If True, reprocess all messages even if they've been processed before
    """
    try:
        # Connect to MongoDB
        db = connect_to_mongodb()
        
        # Set up SQLite database
        sqlite_conn = setup_sqlite_db()
        
        # Get first messages from conversations
        first_messages = get_first_messages_from_conversations(db, limit)
        
        # Get already processed message IDs
        if force_reprocess:
            logger.info("Force reprocessing enabled, ignoring previously processed messages")
            processed_message_ids = set()
        else:
            processed_message_ids = get_processed_message_ids(sqlite_conn)
            logger.info(f"Found {len(processed_message_ids)} already processed messages")
        
        # Filter out already processed messages
        new_messages = [msg for msg in first_messages if msg["message_id"] not in processed_message_ids]
        logger.info(f"Found {len(new_messages)} new messages to process")
        
        if not new_messages and not force_reprocess:
            logger.info("No new messages to process")
            
            # Get and display statistics
            stats = get_category_statistics(sqlite_conn)
            logger.info(f"Current statistics: {stats}")
            
            # Close connections
            sqlite_conn.close()
            return
        
        # Process each message
        messages_to_process = first_messages if force_reprocess else new_messages
        logger.info(f"Processing {len(messages_to_process)} messages")
        
        for i, message_data in enumerate(messages_to_process):
            logger.info(f"Processing message {i+1}/{len(messages_to_process)}")
            
            # Categorize the message
            categorization = categorize_message_with_ollama(message_data["message_text"])
            
            # Save the categorization
            save_categorization_to_sqlite(sqlite_conn, message_data, categorization)
            
            logger.info(f"Categorized as: {categorization['category']} (confidence: {categorization['confidence']})")
        
        # Get and display statistics
        stats = get_category_statistics(sqlite_conn)
        logger.info(f"Categorization complete. Statistics: {stats}")
        
        # Close connections
        sqlite_conn.close()
        
    except Exception as e:
        logger.error(f"Error in main function: {str(e)}")
        raise

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Categorize first messages in conversations using Ollama")
    parser.add_argument("--limit", type=int, help="Limit the number of conversations to process")
    parser.add_argument("--model", type=str, help="Ollama model to use (default: llama3)")
    
    args = parser.parse_args()
    
    if args.model:
        OLLAMA_MODEL = args.model
    
    main(limit=args.limit)
