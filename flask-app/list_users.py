#!/usr/bin/env python3
"""
Script to list users from the LibreChat MongoDB database.

This script:
1. Connects to MongoDB and retrieves users from the users collection
2. Outputs user details to the console in a readable format
3. Provides filtering options via command-line arguments
"""
import os
import logging
import argparse
import json
from datetime import datetime
from pymongo import MongoClient
from dotenv import load_dotenv
from tabulate import tabulate

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Configuration
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

def get_users(db, limit=None, filter_query=None, sort_by="createdAt", sort_order=-1):
    """
    Retrieve users from MongoDB.
    
    Args:
        db: MongoDB database connection
        limit: Maximum number of users to retrieve
        filter_query: MongoDB query to filter users
        sort_by: Field to sort by
        sort_order: Sort order (1 for ascending, -1 for descending)
    
    Returns:
        List of user documents
    """
    try:
        users_collection = db["users"]
        
        # Count total users
        total_users = users_collection.count_documents(filter_query or {})
        logger.info(f"Found {total_users} users in the database")
        
        # Adjust limit if needed
        if limit and limit > total_users:
            limit = total_users
            logger.info(f"Adjusted limit to {limit}")
        
        # Create cursor with sorting
        cursor = users_collection.find(filter_query or {})
        cursor = cursor.sort(sort_by, sort_order)
        
        # Apply limit if specified
        if limit:
            cursor = cursor.limit(limit)
        
        # Convert cursor to list
        users = list(cursor)
        logger.info(f"Retrieved {len(users)} users")
        
        return users
    
    except Exception as e:
        logger.error(f"Error retrieving users: {str(e)}")
        raise

def format_date(date_obj):
    """Format a date object as a string."""
    if not date_obj:
        return "N/A"
    
    if isinstance(date_obj, str):
        try:
            date_obj = datetime.fromisoformat(date_obj.replace('Z', '+00:00'))
        except ValueError:
            return date_obj
    
    return date_obj.strftime("%Y-%m-%d %H:%M:%S")

def display_users(users, output_format="table", fields=None):
    """
    Display user information in the specified format.
    
    Args:
        users: List of user documents
        output_format: Format to display users (table, json, csv)
        fields: List of fields to include in the output
    """
    if not users:
        print("No users found.")
        return
    
    # Default fields to display
    default_fields = [
        "_id", "name", "email", "username", "createdAt", "lastLogin", 
        "provider", "role", "tier", "active", "openidId"
    ]
    
    # Use specified fields or default fields
    display_fields = fields if fields else default_fields
    
    # Prepare data for display
    formatted_users = []
    for user in users:
        user_data = {}
        for field in display_fields:
            if field in user:
                value = user[field]
                
                # Format date fields
                if field in ["createdAt", "lastLogin"] and value:
                    value = format_date(value)
                
                # Convert ObjectId to string
                if field == "_id":
                    value = str(value)
                
                user_data[field] = value
            else:
                user_data[field] = "N/A"
        
        formatted_users.append(user_data)
    
    # Display in the specified format
    if output_format == "json":
        print(json.dumps(formatted_users, indent=2, default=str))
    
    elif output_format == "csv":
        # Print header
        print(",".join(f'"{field}"' for field in display_fields))
        
        # Print rows
        for user in formatted_users:
            print(",".join(f'"{user[field]}"' for field in display_fields))
    
    else:  # table format
        # Prepare data for tabulate
        headers = display_fields
        table_data = [[user.get(field, "N/A") for field in headers] for user in formatted_users]
        
        # Print table
        print(tabulate(table_data, headers=headers, tablefmt="grid"))

def main():
    """Main function to run the user listing process."""
    parser = argparse.ArgumentParser(description="List users from the LibreChat MongoDB database")
    parser.add_argument("--limit", type=int, help="Maximum number of users to retrieve")
    parser.add_argument("--sort-by", type=str, default="createdAt", help="Field to sort by (default: createdAt)")
    parser.add_argument("--sort-order", type=str, choices=["asc", "desc"], default="desc", 
                        help="Sort order (asc or desc, default: desc)")
    parser.add_argument("--format", type=str, choices=["table", "json", "csv"], default="table",
                        help="Output format (table, json, or csv, default: table)")
    parser.add_argument("--fields", type=str, help="Comma-separated list of fields to include in the output")
    parser.add_argument("--filter", type=str, help="JSON filter query to apply (MongoDB query format)")
    parser.add_argument("--mongodb-uri", type=str, help="MongoDB connection URI")
    parser.add_argument("--active-only", action="store_true", help="Show only active users")
    parser.add_argument("--provider", type=str, help="Filter by authentication provider")
    parser.add_argument("--role", type=str, help="Filter by user role")
    
    args = parser.parse_args()
    
    # Set environment variables if provided
    if args.mongodb_uri:
        os.environ["MONGODB_URI"] = args.mongodb_uri
    
    # Parse fields if provided
    fields = None
    if args.fields:
        fields = [field.strip() for field in args.fields.split(",")]
    
    # Build filter query
    filter_query = {}
    
    if args.filter:
        try:
            filter_query.update(json.loads(args.filter))
        except json.JSONDecodeError:
            logger.error("Invalid JSON filter query")
            return 1
    
    if args.active_only:
        filter_query["active"] = True
    
    if args.provider:
        filter_query["provider"] = args.provider
    
    if args.role:
        filter_query["role"] = args.role
    
    # Convert sort order to integer
    sort_order = -1 if args.sort_order == "desc" else 1
    
    try:
        # Connect to MongoDB
        db = connect_to_mongodb()
        
        # Get users
        users = get_users(
            db, 
            limit=args.limit, 
            filter_query=filter_query, 
            sort_by=args.sort_by, 
            sort_order=sort_order
        )
        
        # Display users
        display_users(users, output_format=args.format, fields=fields)
        
    except Exception as e:
        logger.error(f"Error in main function: {str(e)}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())