#!/usr/bin/env python3
"""
Script to run the message categorization process.
"""
import os
import logging
import argparse
from categorize_messages import main as categorize_main

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Main function to run the categorization process."""
    parser = argparse.ArgumentParser(description="Run message categorization process")
    parser.add_argument("--limit", type=int, help="Limit the number of conversations to process")
    parser.add_argument("--model", type=str, default="llama3", help="Ollama model to use (default: llama3)")
    parser.add_argument("--db-path", type=str, help="Path to SQLite database")
    parser.add_argument("--ollama-url", type=str, help="URL for Ollama API (default: http://localhost:11434)")
    parser.add_argument("--mongodb-uri", type=str, help="MongoDB connection URI")
    parser.add_argument("--force", action="store_true", help="Force reprocessing of all messages, even if already processed")
    
    args = parser.parse_args()
    
    # Set environment variables if provided
    if args.model:
        os.environ["OLLAMA_MODEL"] = args.model
    
    if args.db_path:
        os.environ["SQLITE_DB_PATH"] = args.db_path
        
    if args.ollama_url:
        os.environ["OLLAMA_BASE_URL"] = args.ollama_url
        
    if args.mongodb_uri:
        os.environ["MONGODB_URI"] = args.mongodb_uri
    
    # Run the categorization process
    try:
        logger.info("Starting message categorization process")
        categorize_main(limit=args.limit, force_reprocess=args.force)
        logger.info("Message categorization process completed successfully")
    except Exception as e:
        logger.error(f"Error running message categorization: {str(e)}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
