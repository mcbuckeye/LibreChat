#!/usr/bin/env python3
"""
Script to process an Excel file with email addresses and add MyGPT last access data.

This script:
1. Reads an input Excel file (.xlsx) containing email addresses
2. Automatically detects the email column or uses user-specified column
3. Matches emails with MyGPT user data and calculates last access dates
4. Outputs a new Excel file with original data plus LastMyGPTAccess column
5. Uses the same activity calculation method as list_users_with_last_activity.py
"""
import os
import logging
import argparse
import re
from datetime import datetime
from pymongo import MongoClient
from dotenv import load_dotenv
from bson.objectid import ObjectId
import pandas as pd
from openpyxl import load_workbook, Workbook
from openpyxl.utils import get_column_letter, column_index_from_string

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

def get_user_last_activity_with_cross_domain_matching(db, email):
    """
    Get the last activity timestamp for a user based on their email address.
    Handles cross-domain matching between @beigene.com and @beonemed.com.
    
    Args:
        db: MongoDB database connection
        email: User email address to find last activity for
    
    Returns:
        tuple: (matched_email, last_activity_datetime) or (None, None) if no match found
    """
    try:
        users_collection = db["users"]
        transactions_collection = db["transactions"]
        
        # Extract username and domain from the input email
        if '@' not in email:
            return None, None
            
        username, domain = email.split('@', 1)
        
        # Define the domains to check
        target_domains = ['beigene.com', 'beonemed.com']
        
        # If the input email is already one of our target domains, check both
        # If it's a different domain, only check the exact email
        if domain.lower() in target_domains:
            emails_to_check = [f"{username}@{d}" for d in target_domains]
        else:
            emails_to_check = [email]
        
        best_match = None
        latest_activity = None
        matched_email = None
        
        # Check each potential email variant
        for check_email in emails_to_check:
            user = users_collection.find_one({"email": check_email})
            if user:
                user_id = user["_id"]
                
                # Find the most recent transaction from this user
                last_transaction = transactions_collection.find({'user': ObjectId(user_id)}).sort('createdAt', -1).limit(1)
                
                for lt in last_transaction:
                    activity_date = lt.get('createdAt')
                    if activity_date and (latest_activity is None or activity_date > latest_activity):
                        latest_activity = activity_date
                        matched_email = check_email
                        break
                
                # If we found a user but no activity, still record the match
                if not matched_email:
                    matched_email = check_email
        
        return matched_email, latest_activity
    
    except Exception as e:
        logger.error(f"Error getting last activity for email {email}: {str(e)}")
        return None, None

def is_email(text):
    """Check if a text string looks like an email address."""
    if not isinstance(text, str):
        return False
    
    # Simple email regex pattern
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(email_pattern, text.strip()) is not None

def detect_email_column(df):
    """
    Automatically detect which column contains email addresses.
    
    Args:
        df: pandas DataFrame
    
    Returns:
        Column name/index that contains emails, or None if not found
    """
    for col in df.columns:
        # Check if column name suggests it contains emails
        col_name_lower = str(col).lower()
        if any(keyword in col_name_lower for keyword in ['email', 'e-mail', 'mail', 'address']):
            # Verify by checking if values look like emails
            sample_values = df[col].dropna().head(10)
            email_count = sum(1 for val in sample_values if is_email(val))
            if email_count > 0:
                logger.info(f"Detected email column by name: {col}")
                return col
    
    # If no column name matches, check content of each column
    for col in df.columns:
        sample_values = df[col].dropna().head(20)
        if len(sample_values) == 0:
            continue
            
        email_count = sum(1 for val in sample_values if is_email(val))
        email_ratio = email_count / len(sample_values)
        
        # If more than 50% of non-null values look like emails, consider it an email column
        if email_ratio > 0.5:
            logger.info(f"Detected email column by content: {col} (ratio: {email_ratio:.2f})")
            return col
    
    return None

def detect_header_row(file_path):
    """
    Detect if the Excel file has a header row.
    
    Args:
        file_path: Path to the Excel file
    
    Returns:
        Row number to use as header (0 if header exists, None if no header)
    """
    try:
        # Read first few rows to analyze
        df_sample = pd.read_excel(file_path, header=None, nrows=5)
        
        if len(df_sample) < 2:
            return 0  # Default to treating first row as header
        
        # Check if first row looks like headers (contains text, not just data)
        first_row = df_sample.iloc[0]
        second_row = df_sample.iloc[1]
        
        # Count how many cells in first row are strings vs numbers
        first_row_strings = sum(1 for val in first_row if isinstance(val, str) and not is_email(val))
        first_row_emails = sum(1 for val in first_row if isinstance(val, str) and is_email(val))
        
        # Count emails in second row
        second_row_emails = sum(1 for val in second_row if isinstance(val, str) and is_email(val))
        
        # If first row has more non-email strings and second row has emails, likely has header
        if first_row_strings > first_row_emails and second_row_emails > 0:
            logger.info("Detected header row in first row")
            return 0
        
        # If first row has emails, probably no header
        if first_row_emails > 0:
            logger.info("No header row detected (first row contains emails)")
            return None
        
        # Default to assuming header exists
        logger.info("Assuming header row exists (default)")
        return 0
    
    except Exception as e:
        logger.error(f"Error detecting header row: {str(e)}")
        return 0  # Default to header

def format_date(date_obj):
    """Format a date object as a string."""
    if not date_obj:
        return ""
    
    if isinstance(date_obj, str):
        try:
            date_obj = datetime.fromisoformat(date_obj.replace('Z', '+00:00'))
        except ValueError:
            return date_obj
    
    return date_obj.strftime("%Y-%m-%d %H:%M:%S")

def process_excel_file(input_file, output_file, email_column=None, db=None):
    """
    Process the Excel file to add MyGPT last access data.
    
    Args:
        input_file: Path to input Excel file
        output_file: Path to output Excel file
        email_column: Optional column letter/name containing emails
        db: MongoDB database connection
    """
    try:
        logger.info(f"Processing Excel file: {input_file}")
        
        # Detect header row
        header_row = detect_header_row(input_file)
        
        # Read the Excel file
        if header_row is not None:
            df = pd.read_excel(input_file, header=header_row)
        else:
            df = pd.read_excel(input_file, header=None)
            # Create generic column names
            df.columns = [f"Column_{i+1}" for i in range(len(df.columns))]
        
        logger.info(f"Loaded Excel file with {len(df)} rows and {len(df.columns)} columns")
        
        # Determine email column
        if email_column:
            # User specified column
            if email_column.isalpha():
                # Column letter (e.g., 'A', 'B')
                col_index = column_index_from_string(email_column) - 1
                if col_index < len(df.columns):
                    email_col = df.columns[col_index]
                    logger.info(f"Using user-specified email column: {email_column} (index {col_index})")
                else:
                    raise ValueError(f"Column {email_column} does not exist in the spreadsheet")
            else:
                # Column name
                if email_column in df.columns:
                    email_col = email_column
                    logger.info(f"Using user-specified email column: {email_column}")
                else:
                    raise ValueError(f"Column '{email_column}' not found in spreadsheet")
        else:
            # Auto-detect email column
            email_col = detect_email_column(df)
            if not email_col:
                raise ValueError("Could not detect email column. Please specify using --email-column option")
        
        # Add the LastMyGPTAccess and MatchedMyGPTEmail columns
        logger.info("Calculating last access dates for each email...")
        last_access_data = []
        matched_email_data = []
        processed_emails = 0
        
        for index, row in df.iterrows():
            email = row[email_col]
            
            if pd.isna(email) or not is_email(str(email)):
                last_access_data.append("")
                matched_email_data.append("")
            else:
                matched_email, last_activity = get_user_last_activity_with_cross_domain_matching(db, str(email).strip())
                formatted_date = format_date(last_activity)
                last_access_data.append(formatted_date)
                matched_email_data.append(matched_email if matched_email else "")
                processed_emails += 1
                
                if processed_emails % 50 == 0:
                    logger.info(f"Processed {processed_emails} emails...")
        
        # Add the new columns to the DataFrame
        df['MatchedMyGPTEmail'] = matched_email_data
        df['LastMyGPTAccess'] = last_access_data
        
        # Save to new Excel file with auto-sized columns
        logger.info(f"Saving results to: {output_file}")
        
        # Use openpyxl for better formatting control
        with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Sheet1', index=False)
            
            # Auto-size columns
            worksheet = writer.sheets['Sheet1']
            
            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                
                # Check header length
                if column[0].value:
                    max_length = len(str(column[0].value))
                
                # Check all cell values in the column
                for cell in column:
                    if cell.value:
                        cell_length = len(str(cell.value))
                        if cell_length > max_length:
                            max_length = cell_length
                
                # Set column width with reasonable limits
                # Minimum width of 8, maximum width of 50
                adjusted_width = min(max(max_length + 2, 8), 50)
                worksheet.column_dimensions[column_letter].width = adjusted_width
                
        logger.info(f"Applied auto-sizing to all columns (max width: 50 characters)")
        
        # Summary statistics
        matched_users = sum(1 for val in matched_email_data if val != "")
        active_users = sum(1 for val in last_access_data if val != "")
        cross_domain_matches = sum(1 for i, matched in enumerate(matched_email_data) 
                                 if matched != "" and matched != df.iloc[i][email_col])
        
        logger.info(f"Processing complete!")
        logger.info(f"Total rows processed: {len(df)}")
        logger.info(f"Emails found: {processed_emails}")
        logger.info(f"MyGPT users found: {matched_users}")
        logger.info(f"MyGPT users with activity: {active_users}")
        logger.info(f"MyGPT users without activity: {matched_users - active_users}")
        logger.info(f"Cross-domain matches: {cross_domain_matches}")
        
        return {
            "total_rows": len(df),
            "emails_processed": processed_emails,
            "matched_users": matched_users,
            "active_users": active_users,
            "inactive_users": matched_users - active_users,
            "cross_domain_matches": cross_domain_matches
        }
    
    except Exception as e:
        logger.error(f"Error processing Excel file: {str(e)}")
        raise

def main():
    """Main function to run the Excel processing."""
    parser = argparse.ArgumentParser(description="Process Excel file to add MyGPT last access data")
    parser.add_argument("input_file", help="Input Excel file path (.xlsx)")
    parser.add_argument("--email-column", help="Column letter (A, B, C...) or name containing email addresses")
    parser.add_argument("--output-file", help="Output Excel file path (optional, auto-generated if not specified)")
    
    args = parser.parse_args()
    
    # Validate input file
    if not os.path.exists(args.input_file):
        logger.error(f"Input file does not exist: {args.input_file}")
        return 1
    
    if not args.input_file.lower().endswith('.xlsx'):
        logger.error("Input file must be an Excel file (.xlsx)")
        return 1
    
    # Generate output filename if not specified
    if args.output_file:
        output_file = args.output_file
    else:
        # Extract base name without extension
        base_name = os.path.splitext(os.path.basename(args.input_file))[0]
        output_dir = os.path.dirname(args.input_file)
        output_file = os.path.join(output_dir, f"{base_name}_MyGPT_Usage.xlsx")
    
    try:
        # Connect to MongoDB
        db = connect_to_mongodb()
        
        # Process the Excel file
        stats = process_excel_file(args.input_file, output_file, args.email_column, db)
        
        print(f"\n=== PROCESSING SUMMARY ===")
        print(f"Input File: {args.input_file}")
        print(f"Output File: {output_file}")
        print(f"Total Rows: {stats['total_rows']}")
        print(f"Emails Processed: {stats['emails_processed']}")
        print(f"MyGPT Users Found: {stats['matched_users']}")
        print(f"Active MyGPT Users: {stats['active_users']}")
        print(f"Inactive MyGPT Users: {stats['inactive_users']}")
        print(f"Cross-Domain Matches: {stats['cross_domain_matches']}")
        print(f"========================")
        
        return 0
    
    except Exception as e:
        logger.error(f"Error in main function: {str(e)}")
        return 1

if __name__ == "__main__":
    exit(main())
