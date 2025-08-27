#!/usr/bin/env python3
"""
Script to validate and analyze the effectiveness of message categorization.

This script analyzes the categorization results stored in the SQLite database
and provides insights into category usage, confidence levels, and recommendations
for improvements.
"""
import os
import sqlite3
import logging
from categorize_messages import validate_category_distribution, SQLITE_DB_PATH

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Main function to run category validation."""
    try:
        # Connect to SQLite database
        db_path = os.getenv("SQLITE_DB_PATH", SQLITE_DB_PATH)
        
        if not os.path.exists(db_path):
            logger.error(f"Database file not found: {db_path}")
            logger.error("Please run the categorization process first to generate data.")
            return 1
        
        conn = sqlite3.connect(db_path)
        
        # Check if we have any data
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM message_categories")
        total_messages = cursor.fetchone()[0]
        
        if total_messages == 0:
            logger.error("No categorized messages found in database.")
            logger.error("Please run the categorization process first to generate data.")
            return 1
        
        logger.info(f"Analyzing {total_messages} categorized messages...")
        
        # Run validation
        validation_report = validate_category_distribution(conn)
        
        # Save report to file
        report_file = "category_validation_report.txt"
        with open(report_file, 'w') as f:
            f.write("CATEGORY VALIDATION REPORT\n")
            f.write("=" * 50 + "\n\n")
            f.write(f"Total messages analyzed: {validation_report['total_messages']}\n")
            f.write(f"Total categories used: {validation_report['total_categories']}\n\n")
            
            f.write("CATEGORY STATISTICS:\n")
            f.write("-" * 30 + "\n")
            for stat in validation_report['category_stats']:
                f.write(f"{stat['category']:25} | {stat['count']:6d} ({stat['percentage']:5.1f}%) | ")
                f.write(f"Conf: {stat['avg_confidence']:.3f} ({stat['min_confidence']:.2f}-{stat['max_confidence']:.2f})\n")
            
            if validation_report['recommendations']:
                f.write(f"\nRECOMMENDATIONS:\n")
                f.write("-" * 20 + "\n")
                for i, rec in enumerate(validation_report['recommendations'], 1):
                    f.write(f"{i}. {rec}\n")
            else:
                f.write(f"\nNo specific recommendations - categories appear well-balanced!\n")
        
        logger.info(f"Validation report saved to: {report_file}")
        
        conn.close()
        return 0
        
    except Exception as e:
        logger.error(f"Error running validation: {str(e)}")
        return 1

if __name__ == "__main__":
    exit(main())
