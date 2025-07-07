# TradeUP Smart FAQ Assistant

An intelligent FAQ system powered by AI that provides natural language responses to customer questions by searching and synthesizing information from your knowledge base.

## Features

- **Intelligent Question Understanding**: Uses advanced NLP to comprehend questions regardless of phrasing
- **Multi-Source Synthesis**: Combines information from multiple FAQ entries to provide comprehensive answers
- **Intent Analysis**: Analyzes user intent to provide relevant and contextual responses
- **Smart Suggestions**: Recommends follow-up questions based on the current conversation
- **Beautiful Web Interface**: Modern, responsive chat interface for seamless user experience
- **Real-time Statistics**: Dashboard showing system performance and knowledge base metrics
- **Category Organization**: Automatically organizes FAQs by category for better navigation
- **Source Attribution**: Shows which FAQ sources were used to generate responses

## Prerequisites

- Python 3.11 or higher
- OpenAI API key
- 4GB RAM minimum (8GB recommended)
- Modern web browser

## Installation

### 1. Clone or Download the Project

Create a project directory and organize your files:

```
TradeUP-FAQ-System/
├── data/
├── templates/
├── app.py
├── indexing.py
├── smarter_faq_rag.py
├── requirements.txt
├── notepad.env
└── README.md
```

### 2. Set Up Python Environment

```bash
# Create virtual environment
python3 -m venv myenv

# Activate virtual environment
# On macOS/Linux:
source myenv/bin/activate

# On Windows:
myenv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a `notepad.env` file in the root directory:

```
OPENAI_API_KEY=your_openai_api_key_here
SECRET_KEY=your_flask_secret_key_here
```

## Data Preparation

### Automated FAQ Scraping

This system uses automated web scraping to collect FAQ data from the TradeUP website. The scraper targets specific FAQ categories and extracts question-answer pairs automatically.

### Running the Web Scraper

```bash
python comprehensive_scraper.py
```

The scraper will prompt you to enter a category ID:
- **22**: New Accounts
- **23**: Funding/Withdrawal  
- **24**: Stock Trading - General
- **25**: Stock Trading - Order Types
- **30**: Option Trading
- **And more...**

### What the Scraper Does

1. **Launches a browser** and navigates to the TradeUP FAQ page
2. **Finds collapsed FAQs** (those with + icons) 
3. **Clicks to expand** each FAQ automatically
4. **Extracts** the question and answer content
5. **Saves** the data as properly formatted JSON files in the `data/` folder

### Generated JSON Format

Each category creates a JSON file like:
```json
{
  "category_id": 22,
  "category_name": "New Accounts",
  "extraction_method": "icon_click_targeting", 
  "scraped_at": "2025-07-05T16:18:32.994289",
  "qa_pairs": [
    {
      "id": 1,
      "question": "What do I need to open an account?",
      "answer": "We offer individual brokerage accounts...",
      "answer_length": 1084
    }
  ]
}
```

### Scraping Multiple Categories

To collect FAQs from all categories:
1. Run `python comprehensive_scraper.py`
2. Enter a category ID (e.g., 22)
3. Wait for scraping to complete
4. Repeat for other category IDs
5. All JSON files will be saved in the `data/` folder

## Usage

### 1. Index Your FAQ Data

Before starting the application, you need to create the vector database:

```bash
python indexing.py
```

Expected output:
```
Starting RAG indexing pipeline...
Loading documents from data/
Loaded 142 Q&A pairs from 8 JSON files
Created 172 chunks from 142 documents
Creating vectorstore with 172 chunks
Vectorstore created successfully
```

### 2. Start the Web Application

```bash
python app.py
```

The application will be available at `http://localhost:8000`

### 3. Using the Chat Interface

1. Open your web browser and navigate to `http://localhost:8000`
2. Type your question in the chat input field
3. Press Enter or click the send button
4. View the AI-generated response with source attribution
5. Click on suggested follow-up questions for related information

## API Endpoints

### POST /api/ask
Submit a question to the FAQ system.

**Request Body:**
```json
{
  "question": "How do I open an account?"
}
```

**Response:**
```json
{
  "success": true,
  "response": "To open an account...",
  "intent": "Account Opening",
  "sources_count": 3,
  "categories": ["New Accounts", "Verification"],
  "suggested_questions": ["What documents do I need?", "How long does approval take?"],
  "sources": [...]
}
```

### GET /api/stats
Retrieve system statistics.

**Response:**
```json
{
  "total_faqs": 142,
  "total_categories": 8,
  "categories": ["Trading", "Accounts", "Funding"],
  "system_status": "active",
  "embedding_model": "text-embedding-3-small"
}
```

### GET /api/quick-questions
Get predefined quick questions for the interface.

### GET /api/categories
Retrieve all available FAQ categories.

## Configuration

### Customizing Chunk Settings

Modify the indexing parameters in `indexing.py`:

```python
indexer = RAGIndexer(
    data_path=DATA_PATH,
    chunk_size=1000,      # Adjust chunk size
    chunk_overlap=200     # Adjust chunk overlap
)
```

### Adjusting AI Model Settings

Configure the AI model in `smarter_faq_rag.py`:

```python
faq_system = SmartFAQSystem(
    embedding_model="text-embedding-3-small",  # Change embedding model
    chat_model="gpt-4o",                       # Change chat model
    top_k=8,                                   # Number of sources to retrieve
    similarity_threshold=0.2                   # Similarity threshold
)
```

### Interface Customization

Edit `templates/index.html` to customize:
- Colors and styling
- Logo and branding
- Quick questions
- Layout and messaging

## System Architecture

```
User Question → Intent Analysis → Enhanced Queries → Vector Search 
                                                         ↓
Response Generation ← Source Verification ← Multi-Source Retrieval
```

### Components

- **QAJSONLoader**: Custom loader for FAQ JSON files
- **RAGIndexer**: Creates and manages the vector database
- **SmartFAQSystem**: Core AI system for question processing
- **Flask App**: Web interface and API endpoints

## Maintenance

### Updating FAQ Data

1. Add or modify JSON files in the `data/` directory
2. Re-run the indexing process: `python indexing.py`
3. Restart the Flask application: `python app.py`

### Monitoring Performance

- Check OpenAI API usage in your OpenAI dashboard
- Monitor response times and accuracy
- Review user questions for gaps in knowledge base
- Update FAQ content based on common queries

### Backup Procedures

Regularly backup:
- `data/` directory (your FAQ source files)
- `vectorstore/` directory (processed vector database)
- `notepad.env` file (securely store API keys)

## Troubleshooting

### Common Issues

**ImportError: No module named 'faiss'**
```bash
pip install faiss-cpu
```

**OpenAI API key not found**
- Verify `notepad.env` file exists and contains valid API key
- Ensure no extra spaces around the API key
- Restart the Flask application

**No documents loaded**
- Check that JSON files exist in `data/` directory
- Verify JSON format matches the required structure
- Check file permissions

**Stats showing 0 FAQs**
- Re-run indexing: `python indexing.py`
- Check console output for errors
- Verify vectorstore was created successfully

**JSON serialization errors**
- Ensure numpy is installed: `pip install numpy`
- Update Flask app with latest code that includes type conversion
- Restart the application

### Debug Mode

Enable debug output by setting environment variable:
```bash
export FLASK_DEBUG=1
python app.py
```

## Performance Optimization

### For Large FAQ Databases

- Increase `top_k` parameter for more comprehensive searches
- Adjust `chunk_size` based on average FAQ length
- Consider using GPU-accelerated FAISS: `pip install faiss-gpu`

### Memory Usage

- Monitor RAM usage with large document sets
- Adjust batch sizes in indexing process
- Consider document pruning for outdated FAQs

## Security Considerations

- Keep `notepad.env` file secure and never commit to version control
- Use strong, unique API keys
- Implement rate limiting for production deployments
- Regular security updates for dependencies
- Consider API key rotation policies

## Development

### Project Structure

```
├── app.py                 # Flask web application
├── indexing.py           # Vector database creation
├── smarter_faq_rag.py    # Core AI system
├── templates/
│   └── index.html        # Web interface
├── data/                 # FAQ source files
├── vectorstore/          # Generated vector database
├── requirements.txt      # Python dependencies
└── notepad.env          # Environment variables
```

### Adding New Features

1. Core AI improvements: Modify `smarter_faq_rag.py`
2. Web interface changes: Edit `templates/index.html`
3. API modifications: Update routes in `app.py`
4. Data processing: Enhance `indexing.py`

## Contributing

1. Ensure all FAQ data follows the specified JSON format
2. Test changes with the full indexing and application pipeline
3. Update documentation for any configuration changes
4. Verify all dependencies are listed in `requirements.txt`

## License

This project is proprietary software for TradeUP internal use.

## Support

For technical issues:
1. Check the troubleshooting section above
2. Review console output for specific error messages
3. Verify all prerequisites are met
4. Ensure FAQ data format compliance

---

**Version**: 1.0.0  
**Last Updated**: July 2025  
**Minimum Python Version**: 3.11