#!/usr/bin/env python3
"""
Script to analyze messages and suggest appropriate categories.

This script:
1. Connects to MongoDB and retrieves a sample of messages
2. Uses Ollama to analyze these messages and suggest categories
3. Clusters similar suggestions to come up with a final list of categories
4. Outputs the suggested categories along with example messages for each
"""
import os
import logging
import argparse
import json
import requests
import random
from collections import Counter
from pymongo import MongoClient
from dotenv import load_dotenv
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

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

def get_message_sample(db, sample_size=500):
    """
    Retrieve a random sample of messages from MongoDB.
    
    Args:
        db: MongoDB database connection
        sample_size: Number of messages to sample
    
    Returns:
        List of message texts
    """
    try:
        messages_collection = db["messages"]
        
        # Count total messages
        total_messages = messages_collection.count_documents({"isCreatedByUser": True})
        logger.info(f"Found {total_messages} user messages in the database")
        
        # Adjust sample size if needed
        if sample_size > total_messages:
            sample_size = total_messages
            logger.info(f"Adjusted sample size to {sample_size}")
        
        # Get a random sample of messages
        pipeline = [
            {"$match": {"isCreatedByUser": True}},
            {"$sample": {"size": sample_size}}
        ]
        
        message_sample = list(messages_collection.aggregate(pipeline))
        logger.info(f"Retrieved {len(message_sample)} messages")
        
        # Extract message text
        message_texts = []
        for message in message_sample:
            if "text" in message and message["text"]:
                # Truncate long messages to avoid token limits
                text = message["text"][:1000]
                message_texts.append({
                    "id": str(message["_id"]),
                    "text": text
                })
        
        logger.info(f"Extracted text from {len(message_texts)} messages")
        return message_texts
    
    except Exception as e:
        logger.error(f"Error retrieving message sample: {str(e)}")
        raise

def analyze_message_with_ollama(message_text):
    """
    Use Ollama to analyze a message and suggest a category.
    
    Args:
        message_text: The text of the message to analyze
    
    Returns:
        Dictionary with suggested category and explanation
    """
    try:
        # Log the Ollama URL and model being used
        ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        ollama_model = os.getenv("OLLAMA_MODEL", "llama3")
        
        prompt = f"""
        Analyze the following message and suggest an appropriate category for it.
        
        Message: "{message_text}"
        
        Think about what type of request or question this is. Is it asking for information, 
        requesting help with a task, asking for an explanation, etc.?
        
        Respond with a JSON object containing:
        1. "category": A single word or short phrase (2-3 words max) that best categorizes this message
        2. "explanation": A brief explanation of why you chose this category
        
        The category should be general enough to apply to similar messages but specific enough to be meaningful.
        
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
            return {"category": "unknown", "explanation": "Error analyzing message"}
        
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
                if "category" in result:
                    return {
                        "category": result["category"].lower().strip(),
                        "explanation": result.get("explanation", "")
                    }
            
            # If we couldn't parse JSON, extract category directly
            return {"category": "unknown", "explanation": "Could not parse category from response"}
            
        except json.JSONDecodeError:
            logger.warning(f"Could not parse JSON from Ollama response: {response_text}")
            return {"category": "unknown", "explanation": "Could not parse category from response"}
    
    except Exception as e:
        logger.error(f"Error analyzing message with Ollama: {str(e)}")
        return {"category": "unknown", "explanation": f"Error: {str(e)}"}

def cluster_categories(category_data, num_clusters=20):
    """
    Cluster similar categories to reduce the total number.
    
    Args:
        category_data: List of dictionaries with category, explanation, and message
        num_clusters: Number of clusters to create
    
    Returns:
        List of cluster representatives with example messages
    """
    try:
        # Extract categories and explanations
        categories = [item["category"] for item in category_data]
        explanations = [item["explanation"] for item in category_data]
        
        # Combine categories and explanations for better clustering
        texts = [f"{cat} {exp}" for cat, exp in zip(categories, explanations)]
        
        # Create TF-IDF vectors
        vectorizer = TfidfVectorizer(stop_words='english')
        X = vectorizer.fit_transform(texts)
        
        # Adjust number of clusters if we have fewer samples than requested clusters
        n_samples = len(category_data)
        if n_samples < num_clusters:
            logger.warning(f"Reducing number of clusters from {num_clusters} to {n_samples} because we have fewer samples")
            num_clusters = max(2, n_samples // 2)  # At least 2 clusters, but no more than half the samples
        
        # Find optimal number of clusters (between 2 and min(30, n_samples//2))
        min_k = max(2, min(num_clusters - 5, n_samples // 4))
        max_k = min(num_clusters + 5, n_samples // 2, 30)
        
        if min_k >= max_k:
            best_k = min_k
            logger.info(f"Using {best_k} clusters (no optimization possible)")
        else:
            best_score = -1
            best_k = num_clusters
            
            for k in range(min_k, max_k + 1):
                if k >= n_samples:
                    continue
                    
                kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
                cluster_labels = kmeans.fit_predict(X)
                
                # Skip if we have clusters with only one sample (can't compute silhouette)
                cluster_sizes = Counter(cluster_labels)
                if min(cluster_sizes.values()) < 2:
                    continue
                    
                score = silhouette_score(X, cluster_labels)
                logger.info(f"Silhouette score for k={k}: {score}")
                
                if score > best_score:
                    best_score = score
                    best_k = k
            
            logger.info(f"Using {best_k} clusters based on silhouette score")
        
        # Perform K-means clustering with the optimal k
        kmeans = KMeans(n_clusters=best_k, random_state=42, n_init=10)
        cluster_labels = kmeans.fit_predict(X)
        
        # Group data by cluster
        clusters = {}
        for i, label in enumerate(cluster_labels):
            if label not in clusters:
                clusters[label] = []
            clusters[label].append(category_data[i])
        
        # Find the most common category in each cluster
        cluster_representatives = []
        for label, items in clusters.items():
            category_counter = Counter([item["category"] for item in items])
            most_common_category = category_counter.most_common(1)[0][0]
            
            # Find items with this category
            examples = [item for item in items if item["category"] == most_common_category]
            
            # Select a representative explanation
            explanation = max([item["explanation"] for item in examples], key=len)
            
            # Select a few example messages
            example_messages = random.sample(examples, min(3, len(examples)))
            
            cluster_representatives.append({
                "category": most_common_category,
                "explanation": explanation,
                "count": len(items),
                "examples": example_messages
            })
        
        # Sort by count (descending)
        cluster_representatives.sort(key=lambda x: x["count"], reverse=True)
        
        return cluster_representatives
    
    except Exception as e:
        logger.error(f"Error clustering categories: {str(e)}")
        raise

def main():
    """Main function to run the category suggestion process."""
    parser = argparse.ArgumentParser(description="Analyze messages and suggest appropriate categories")
    parser.add_argument("--sample-size", type=int, default=500, help="Number of messages to sample (default: 500)")
    parser.add_argument("--num-clusters", type=int, default=20, help="Number of category clusters to create (default: 20)")
    parser.add_argument("--ollama-url", type=str, help="URL for Ollama API (default: http://localhost:11434)")
    parser.add_argument("--model", type=str, help="Ollama model to use (default: llama3)")
    parser.add_argument("--mongodb-uri", type=str, help="MongoDB connection URI")
    parser.add_argument("--output", type=str, help="Output file path (default: suggested_categories.json)")
    
    args = parser.parse_args()
    
    # Set environment variables if provided
    if args.ollama_url:
        os.environ["OLLAMA_BASE_URL"] = args.ollama_url
    
    if args.model:
        os.environ["OLLAMA_MODEL"] = args.model
    
    if args.mongodb_uri:
        os.environ["MONGODB_URI"] = args.mongodb_uri
    
    output_file = args.output or "suggested_categories.json"
    
    try:
        # Connect to MongoDB
        db = connect_to_mongodb()
        
        # Get a sample of messages
        message_sample = get_message_sample(db, args.sample_size)
        
        # Analyze each message
        logger.info("Analyzing messages with Ollama...")
        category_data = []
        
        for i, message in enumerate(message_sample):
            logger.info(f"Analyzing message {i+1}/{len(message_sample)}")
            
            analysis = analyze_message_with_ollama(message["text"])
            
            category_data.append({
                "message_id": message["id"],
                "message_text": message["text"],
                "category": analysis["category"],
                "explanation": analysis["explanation"]
            })
        
        # Cluster similar categories
        logger.info("Clustering categories...")
        cluster_representatives = cluster_categories(category_data, args.num_clusters)
        
        # Save results to file
        with open(output_file, 'w') as f:
            json.dump({
                "suggested_categories": [rep["category"] for rep in cluster_representatives],
                "cluster_details": cluster_representatives
            }, f, indent=2)
        
        logger.info(f"Results saved to {output_file}")
        
        # Print suggested categories
        print("\nSuggested Categories:")
        for i, rep in enumerate(cluster_representatives):
            print(f"{i+1}. {rep['category']} ({rep['count']} messages)")
            print(f"   Explanation: {rep['explanation']}")
            print()
        
    except Exception as e:
        logger.error(f"Error in main function: {str(e)}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
