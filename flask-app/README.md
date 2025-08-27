# Message Categorization System

This system examines the first message in each conversation from LibreChat and uses a local Ollama model to categorize it into different types of questions. The results are stored in a SQLite database for analysis.

## Requirements

- Python 3.9+
- MongoDB (with LibreChat data)
- Ollama running locally with models like llama3
- Dependencies listed in `requirements.txt`

## Setup

1. Install the required dependencies:

```bash
pip install -r requirements.txt
```

2. Make sure Ollama is running locally with your preferred model (default is llama3):

```bash
# Start Ollama service if not already running
ollama serve

# Pull the model if you haven't already
ollama pull llama3
```

3. Ensure MongoDB is accessible at the configured URL (default: `mongodb://mongodb:27017/`).

## Usage

### Categorizing Messages

To run the categorization process:

```bash
# Basic usage
python run_categorization.py

# Limit the number of conversations to process
python run_categorization.py --limit 100

# Use a different Ollama model
python run_categorization.py --model llama3:8b

# Specify a custom SQLite database path
python run_categorization.py --db-path /path/to/custom_categories.db

# Specify a custom Ollama API URL (useful when running in Docker)
python run_categorization.py --ollama-url http://host.docker.internal:11434

# Specify a custom MongoDB URI
python run_categorization.py --mongodb-uri mongodb://localhost:27017/

# Force reprocessing of all messages, even if already processed
python run_categorization.py --force
```

By default, the script will only process new messages that haven't been categorized yet. This makes it efficient to run the script periodically to categorize new conversations without duplicating work. If you want to reprocess all messages (for example, if you've changed the categorization model or logic), use the `--force` option.

## Running in Docker Environment

When running the script inside the Docker container, you need to use special configuration to access services running on the host machine:

```bash
# Run the categorization script inside the Docker container
docker-compose exec flask-app python run_categorization.py --ollama-url http://host.docker.internal:11434 --model llama3.2:latest

# View statistics from the command line
docker-compose exec flask-app python view_categories.py stats

# View recent categorizations
docker-compose exec flask-app python view_categories.py recent --limit 10

# View examples of a specific category
docker-compose exec flask-app python view_categories.py examples how_to --limit 5
```

The web dashboard is accessible at http://localhost:8082/categories with the appropriate authentication credentials.

### Viewing Categorization Results

#### Command Line

To view the categorization results in the terminal:

```bash
# View category statistics
python view_categories.py stats

# View recent categorizations
python view_categories.py recent --limit 20

# View examples for a specific category
python view_categories.py examples technical_support --limit 5
```

#### Web Dashboard

The Flask app includes a web dashboard to view the categorization results:

1. Start the Flask server:

```bash
python app.py
```

2. Access the categories dashboard at: http://localhost:8082/categories

## Category Types

The system categorizes messages into the following types:

- `general_information_request`: General inquiries seeking factual information or explanations
- `technical_inquiry`: Questions about technical concepts, systems, or processes
- `programming_request`: Requests for code, programming help, or software development
- `medical_inquiry`: Questions about medical conditions, treatments, or healthcare
- `business_analysis`: Requests for business information, market analysis, or company details
- `document_creation`: Requests to create documents, reports, or presentations
- `content_editing`: Requests to edit, proofread, or improve existing content
- `translation_request`: Requests to translate text between languages
- `data_analysis`: Requests to analyze, interpret, or visualize data
- `technical_support`: Requests for help with technical issues or troubleshooting
- `summarization`: Requests to summarize documents, articles, or other content
- `creative_writing`: Requests for creative content like stories, poems, or marketing copy
- `research_request`: Requests for in-depth research on specific topics
- `comparison`: Requests to compare different options, products, or approaches
- `process_guidance`: Requests for step-by-step instructions or workflows
- `feedback_request`: Requests for opinions, evaluations, or assessments
- `email_drafting`: Requests to draft or help with email content
- `legal_regulatory_inquiry`: Questions about laws, regulations, or compliance
- `educational_content`: Requests for learning materials or educational content
- `brainstorming`: Requests for ideas, suggestions, or creative solutions
- `other`: Messages that don't fit any of the above categories

These categories were determined through analysis of 500 sample messages using the `suggest_categories.py` script, which uses machine learning to cluster similar message types and identify the most representative categories.

## Database Schema

The categorization results are stored in a SQLite database with the following schema:

```sql
CREATE TABLE message_categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id TEXT NOT NULL,
    message_id TEXT NOT NULL,
    message_text TEXT NOT NULL,
    category TEXT NOT NULL,
    confidence REAL,
    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(message_id)
)
```

## Integration with Flask Dashboard

The categorization data is integrated into the Flask dashboard, allowing you to:

- View category distribution statistics
- See recent categorized messages
- Analyze trends in question types
