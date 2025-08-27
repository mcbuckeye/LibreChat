#!/usr/bin/env python3
import os
import sqlite3
import argparse
from dotenv import load_dotenv
from tabulate import tabulate

# Load environment variables
load_dotenv()

# Configuration
SQLITE_DB_PATH = os.getenv("SQLITE_DB_PATH", "message_categories.db")

def view_category_statistics():
    """Display statistics about message categories."""
    try:
        # Connect to SQLite database
        conn = sqlite3.connect(SQLITE_DB_PATH)
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
        
        category_counts = cursor.fetchall()
        
        # Get total count
        cursor.execute("SELECT COUNT(*) FROM message_categories")
        total_count = cursor.fetchone()[0]
        
        # Display statistics
        print(f"\nMessage Category Statistics (Total: {total_count})\n")
        
        table_data = []
        for category, count in category_counts:
            percentage = (count / total_count) * 100 if total_count > 0 else 0
            table_data.append([category, count, f"{percentage:.2f}%"])
        
        print(tabulate(
            table_data,
            headers=["Category", "Count", "Percentage"],
            tablefmt="grid"
        ))
        
    except Exception as e:
        print(f"Error viewing category statistics: {str(e)}")

def view_recent_categorizations(limit=10):
    """Display the most recent message categorizations."""
    try:
        # Connect to SQLite database
        conn = sqlite3.connect(SQLITE_DB_PATH)
        cursor = conn.cursor()
        
        # Get recent categorizations
        cursor.execute(
            """
            SELECT message_id, category, confidence, 
                   substr(message_text, 1, 50) || '...' as message_preview, 
                   processed_at
            FROM message_categories
            ORDER BY processed_at DESC
            LIMIT ?
            """,
            (limit,)
        )
        
        recent_categorizations = cursor.fetchall()
        
        # Display recent categorizations
        print(f"\nRecent Message Categorizations (Limit: {limit})\n")
        
        table_data = []
        for message_id, category, confidence, message_preview, processed_at in recent_categorizations:
            table_data.append([
                message_id[:8] + "...",
                category,
                f"{confidence:.2f}",
                message_preview,
                processed_at
            ])
        
        print(tabulate(
            table_data,
            headers=["Message ID", "Category", "Confidence", "Message Preview", "Processed At"],
            tablefmt="grid"
        ))
        
    except Exception as e:
        print(f"Error viewing recent categorizations: {str(e)}")

def view_category_examples(category, limit=5):
    """Display examples of messages in a specific category."""
    try:
        # Connect to SQLite database
        conn = sqlite3.connect(SQLITE_DB_PATH)
        cursor = conn.cursor()
        
        # Get examples for the category
        cursor.execute(
            """
            SELECT message_id, confidence, message_text, processed_at
            FROM message_categories
            WHERE category = ?
            ORDER BY confidence DESC
            LIMIT ?
            """,
            (category, limit)
        )
        
        category_examples = cursor.fetchall()
        
        # Display category examples
        print(f"\nExamples for Category: {category} (Limit: {limit})\n")
        
        if not category_examples:
            print(f"No examples found for category: {category}")
            return
        
        for i, (message_id, confidence, message_text, processed_at) in enumerate(category_examples):
            print(f"Example {i+1}:")
            print(f"  Message ID: {message_id[:8]}...")
            print(f"  Confidence: {confidence:.2f}")
            print(f"  Processed: {processed_at}")
            print(f"  Message: {message_text[:100]}..." if len(message_text) > 100 else f"  Message: {message_text}")
            print()
        
    except Exception as e:
        print(f"Error viewing category examples: {str(e)}")

def main():
    """Main function to run the view script."""
    parser = argparse.ArgumentParser(description="View message categorization results")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Stats command
    stats_parser = subparsers.add_parser("stats", help="View category statistics")
    
    # Recent command
    recent_parser = subparsers.add_parser("recent", help="View recent categorizations")
    recent_parser.add_argument("--limit", type=int, default=10, help="Number of recent categorizations to show")
    
    # Examples command
    examples_parser = subparsers.add_parser("examples", help="View examples for a specific category")
    examples_parser.add_argument("category", type=str, help="Category to show examples for")
    examples_parser.add_argument("--limit", type=int, default=5, help="Number of examples to show")
    
    args = parser.parse_args()
    
    if args.command == "stats":
        view_category_statistics()
    elif args.command == "recent":
        view_recent_categorizations(limit=args.limit)
    elif args.command == "examples":
        view_category_examples(args.category, limit=args.limit)
    else:
        # Default to showing stats if no command is provided
        view_category_statistics()

if __name__ == "__main__":
    main()
