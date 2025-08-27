#!/usr/bin/env python3
"""
Script to list users from the LibreChat MongoDB database with their last activity.

This script:
1. Connects to MongoDB and retrieves users from the users collection
2. Calculates each user's last activity based on their most recent message
3. Outputs user details with calculated last login/activity to the console
4. Provides filtering and sorting options via command-line arguments
"""
import os
import logging
import argparse
import json
from datetime import datetime
from pymongo import MongoClient
from dotenv import load_dotenv
from tabulate import tabulate
from bson.objectid import ObjectId

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

def get_user_last_activity(db, user_id):
    """
    Get the last activity timestamp for a user based on their most recent transaction.
    This follows the same approach as the dashboard in app.py.
    
    Args:
        db: MongoDB database connection
        user_id: User ID to find last activity for
    
    Returns:
        datetime object of last activity or None if no activity found
    """
    try:
        transactions_collection = db["transactions"]
        
        # Find the most recent transaction from this user
        # This is the same approach used in app.py generate_report function
        last_transaction = transactions_collection.find({'user': ObjectId(user_id)}).sort('createdAt', -1).limit(1)
        
        for lt in last_transaction:
            return lt.get('createdAt')
        
        return None
    
    except Exception as e:
        logger.error(f"Error getting last activity for user {user_id}: {str(e)}")
        return None

def get_users_with_activity(db, limit=None, filter_query=None, sort_by="last_activity", sort_order=-1):
    """
    Retrieve users from MongoDB with their calculated last activity.
    
    Args:
        db: MongoDB database connection
        limit: Maximum number of users to retrieve
        filter_query: MongoDB query to filter users
        sort_by: Field to sort by (supports 'last_activity', 'createdAt', etc.)
        sort_order: Sort order (1 for ascending, -1 for descending)
    
    Returns:
        List of user documents with last_activity field added
    """
    try:
        users_collection = db["users"]
        
        # Count total users
        total_users = users_collection.count_documents(filter_query or {})
        logger.info(f"Found {total_users} users in the database")
        
        # Get users (we'll sort after adding activity data)
        cursor = users_collection.find(filter_query or {})
        users = list(cursor)
        
        logger.info(f"Processing {len(users)} users to find last activity...")
        
        # Add last activity data to each user
        users_with_activity = []
        processed_count = 0
        
        for user in users:
            user_id = str(user["_id"])
            last_activity = get_user_last_activity(db, user_id)
            
            # Add the calculated last activity to user data
            user["last_activity"] = last_activity
            users_with_activity.append(user)
            
            processed_count += 1
            if processed_count % 100 == 0:
                logger.info(f"Processed {processed_count}/{len(users)} users...")
        
        logger.info(f"Completed processing all {len(users_with_activity)} users")
        
        # Sort the results
        if sort_by == "last_activity":
            # Sort by last activity, handling None values
            users_with_activity.sort(
                key=lambda x: x["last_activity"] or datetime.min,
                reverse=(sort_order == -1)
            )
        else:
            # Sort by other fields
            users_with_activity.sort(
                key=lambda x: x.get(sort_by, ""),
                reverse=(sort_order == -1)
            )
        
        # Apply limit if specified
        if limit:
            users_with_activity = users_with_activity[:limit]
        
        logger.info(f"Returning {len(users_with_activity)} users")
        return users_with_activity
    
    except Exception as e:
        logger.error(f"Error retrieving users with activity: {str(e)}")
        raise

def format_date(date_obj):
    """Format a date object as a string."""
    if not date_obj:
        return "Never"
    
    if isinstance(date_obj, str):
        try:
            date_obj = datetime.fromisoformat(date_obj.replace('Z', '+00:00'))
        except ValueError:
            return date_obj
    
    return date_obj.strftime("%Y-%m-%d %H:%M:%S")

def display_users_with_activity(users, output_format="table", fields=None):
    """
    Display user information with last activity in the specified format.
    
    Args:
        users: List of user documents with last_activity field
        output_format: Format to display users (table, json, csv)
        fields: List of fields to include in the output
    """
    if not users:
        print("No users found.")
        return
    
    # Default fields to display
    default_fields = [
        "_id", "name", "email", "username", "createdAt", "last_activity", 
        "provider", "role", "tier", "active"
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
                if field in ["createdAt", "last_activity"] and value:
                    value = format_date(value)
                elif field == "last_activity" and not value:
                    value = "Never"
                
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

def get_activity_statistics(users):
    """
    Get statistics about user activity.
    
    Args:
        users: List of user documents with last_activity field
    
    Returns:
        Dictionary with activity statistics
    """
    total_users = len(users)
    active_users = sum(1 for user in users if user.get("last_activity"))
    inactive_users = total_users - active_users
    
    # Calculate activity within different time periods
    now = datetime.now()
    active_last_day = 0
    active_last_week = 0
    active_last_month = 0
    
    for user in users:
        last_activity = user.get("last_activity")
        if last_activity:
            days_since_activity = (now - last_activity).days
            if days_since_activity <= 1:
                active_last_day += 1
            if days_since_activity <= 7:
                active_last_week += 1
            if days_since_activity <= 30:
                active_last_month += 1
    
    return {
        "total_users": total_users,
        "active_users": active_users,
        "inactive_users": inactive_users,
        "active_last_day": active_last_day,
        "active_last_week": active_last_week,
        "active_last_month": active_last_month
    }

def main():
    """Main function to run the user listing process with activity data."""
    parser = argparse.ArgumentParser(description="List LibreChat users with their last activity")
    parser.add_argument("--limit", type=int, help="Limit the number of users to display")
    parser.add_argument("--format", choices=["table", "json", "csv"], default="table",
                        help="Output format (default: table)")
    parser.add_argument("--fields", nargs="+", help="Specific fields to display")
    parser.add_argument("--sort-by", default="last_activity",
                        help="Field to sort by (default: last_activity)")
    parser.add_argument("--sort-order", choices=["asc", "desc"], default="desc",
                        help="Sort order (default: desc)")
    parser.add_argument("--stats", action="store_true",
                        help="Show activity statistics")
    parser.add_argument("--active-only", action="store_true",
                        help="Show only users with activity")
    parser.add_argument("--inactive-only", action="store_true",
                        help="Show only users without activity")
    
    args = parser.parse_args()
    
    try:
        # Connect to MongoDB
        db = connect_to_mongodb()
        
        # Build filter query
        filter_query = {}
        
        # Get users with activity data
        sort_order = 1 if args.sort_order == "asc" else -1
        users = get_users_with_activity(
            db, 
            limit=args.limit,
            filter_query=filter_query,
            sort_by=args.sort_by,
            sort_order=sort_order
        )
        
        # Apply activity filters
        if args.active_only:
            users = [user for user in users if user.get("last_activity")]
        elif args.inactive_only:
            users = [user for user in users if not user.get("last_activity")]
        
        # Show statistics if requested
        if args.stats:
            stats = get_activity_statistics(users)
            print("\n=== USER ACTIVITY STATISTICS ===")
            print(f"Total Users: {stats['total_users']}")
            print(f"Users with Activity: {stats['active_users']}")
            print(f"Users without Activity: {stats['inactive_users']}")
            print(f"Active in Last Day: {stats['active_last_day']}")
            print(f"Active in Last Week: {stats['active_last_week']}")
            print(f"Active in Last Month: {stats['active_last_month']}")
            print("=" * 35)
            print()
        
        # Display users
        display_users_with_activity(users, args.format, args.fields)
        
        return 0
    
    except Exception as e:
        logger.error(f"Error in main function: {str(e)}")
        return 1

if __name__ == "__main__":
    exit(main())
