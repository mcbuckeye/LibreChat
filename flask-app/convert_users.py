#!/usr/bin/env python3
"""
Script to convert user emails from beigene.com to beonemed.com in the LibreChat MongoDB database.

This script:
1. Connects to MongoDB and retrieves users with emails ending in @beigene.com or @beonemed.com
2. Groups users by the local part of their email address
3. For each group:
   - If both beigene.com and beonemed.com accounts exist: deletes the beonemed account and updates the beigene one
   - If only beigene.com account exists: updates it to use beonemed.com
   - If only beonemed.com account exists: does nothing
4. Outputs the changes made to the console
"""
import os
import re
import logging
import argparse
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

def get_users_by_email_domain(db, domain_pattern):
    """
    Retrieve users from MongoDB with emails matching the given domain pattern.
    
    Args:
        db: MongoDB database connection
        domain_pattern: Regex pattern to match email domains
    
    Returns:
        List of user documents
    """
    try:
        users_collection = db["users"]
        
        # Create regex pattern for email domain
        regex_pattern = re.compile(domain_pattern)
        
        # Find users with matching email domains
        users = list(users_collection.find({"email": regex_pattern}))
        logger.info(f"Found {len(users)} users with emails matching {domain_pattern}")
        
        return users
    
    except Exception as e:
        logger.error(f"Error retrieving users: {str(e)}")
        raise

def group_users_by_email_local(users):
    """
    Group users by the local part of their email address.
    
    Args:
        users: List of user documents
    
    Returns:
        Dictionary with local parts as keys and lists of user documents as values
    """
    groups = {}
    
    for user in users:
        if not user.get("email"):
            continue
            
        parts = user["email"].split('@')
        if len(parts) != 2:
            continue
            
        local = parts[0]
        if local not in groups:
            groups[local] = []
            
        groups[local].append(user)
    
    logger.info(f"Grouped users into {len(groups)} email local parts")
    return groups

def process_user_groups(db, groups, dry_run=False):
    """
    Process each group of users according to the conversion rules.
    
    Args:
        db: MongoDB database connection
        groups: Dictionary with local parts as keys and lists of user documents as values
        dry_run: If True, don't make any changes to the database
    """
    users_collection = db["users"]
    stats = {"both_exist": 0, "only_beigene": 0, "only_beonemed": 0}
    
    for local, docs in groups.items():
        has_beigene = False
        has_beonemed = False
        beigene_doc = None
        beonemed_doc = None
        
        for doc in docs:
            if doc["email"].endswith("@beigene.com"):
                has_beigene = True
                beigene_doc = doc
            elif doc["email"].endswith("@beonemed.com"):
                has_beonemed = True
                beonemed_doc = doc
        
        if has_beigene and has_beonemed:
            # Both exist: delete the beonemed account and update the beigene one to be on beonemed.com
            print(f"For {local}: Both accounts exist. Deleting beonemed account and updating beigene account.")
            stats["both_exist"] += 1
            
            if not dry_run:
                # Delete beonemed account
                users_collection.delete_one({"_id": beonemed_doc["_id"]})
                
                # Update beigene account
                users_collection.update_one(
                    {"_id": beigene_doc["_id"]},
                    {"$set": {"email": f"{local}@beonemed.com"}}
                )
        
        elif has_beigene and not has_beonemed:
            # Only beigene exists: update it to use beonemed.com
            print(f"For {local}: Only beigene account exists. Updating email to beonemed.com.")
            stats["only_beigene"] += 1
            
            if not dry_run:
                users_collection.update_one(
                    {"_id": beigene_doc["_id"]},
                    {"$set": {"email": f"{local}@beonemed.com"}}
                )
        
        elif not has_beigene and has_beonemed:
            # Only beonemed exists: do nothing
            print(f"For {local}: Only beonemed account exists. No change made.")
            stats["only_beonemed"] += 1
    
    return stats

def main():
    """Main function to run the user conversion process."""
    parser = argparse.ArgumentParser(description="Convert user emails from beigene.com to beonemed.com")
    parser.add_argument("--dry-run", action="store_true", help="Don't make any changes to the database")
    parser.add_argument("--mongodb-uri", type=str, help="MongoDB connection URI")
    
    args = parser.parse_args()
    
    # Set environment variables if provided
    if args.mongodb_uri:
        os.environ["MONGODB_URI"] = args.mongodb_uri
    
    try:
        # Connect to MongoDB
        db = connect_to_mongodb()
        
        # Get users with beigene.com or beonemed.com emails
        users = get_users_by_email_domain(db, r"@(beigene|beonemed)\.com$")
        
        # Group users by the local part of their email
        groups = group_users_by_email_local(users)
        
        # Process each group
        stats = process_user_groups(db, groups, dry_run=args.dry_run)
        
        # Print summary
        print("\nConversion Summary:")
        print(f"  Users with both accounts: {stats['both_exist']}")
        print(f"  Users with only beigene.com: {stats['only_beigene']}")
        print(f"  Users with only beonemed.com: {stats['only_beonemed']}")
        print(f"  Total users processed: {sum(stats.values())}")
        
        if args.dry_run:
            print("\nThis was a dry run. No changes were made to the database.")
        
    except Exception as e:
        logger.error(f"Error in main function: {str(e)}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())