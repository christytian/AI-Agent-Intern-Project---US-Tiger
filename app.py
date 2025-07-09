# app.py - Your original working code + separate Swagger API
from flask import Flask, render_template, request, jsonify
from flask_restx import Api, Resource, fields
import json
import os
from dotenv import load_dotenv
import numpy as np

# Load environment variables from notepad.env
load_dotenv(dotenv_path="notepad.env")

# Import your Smart FAQ system (same folder - much cleaner!)
from smarter_faq_rag import SmartFAQSystem

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# Initialize FAQ system
faq_system = None

def init_faq_system():
    global faq_system
    try:
        faq_system = SmartFAQSystem()
        print("Smart FAQ System loaded successfully")
        return True
    except Exception as e:
        print(f"Error loading FAQ system: {e}")
        return False

def convert_numpy_types(obj):
    """Convert numpy types to Python native types for JSON serialization"""
    if isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {key: convert_numpy_types(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_types(item) for item in obj]
    return obj

# KEEP YOUR ORIGINAL WORKING ROUTES EXACTLY AS THEY ARE
@app.route('/')
def home():
    """Serve the main chat interface"""
    return render_template('index.html')

@app.route('/api/ask', methods=['POST'])
def ask_question():
    """Handle FAQ questions via API with JSON serialization fix"""
    try:
        data = request.get_json()
        question = data.get('question', '').strip()
        
        print(f"DEBUG: Received question: '{question}'")
        
        if not question:
            print("DEBUG: No question provided")
            return jsonify({'error': 'No question provided'}), 400
        
        if not faq_system:
            print("DEBUG: FAQ system not available")
            return jsonify({'error': 'FAQ system not available'}), 500
        
        print(f"DEBUG: FAQ system loaded, processing question...")
        
        # Get response from Smart FAQ system
        result = faq_system.get_smart_response(question)
        
        print(f"DEBUG: Got response, preparing JSON...")
        
        # Convert all numpy types to Python native types
        response_data = {
            'success': True,
            'response': result['response'],
            'intent': result['intent_analysis'].get('main_intent', 'General inquiry'),
            'sources_count': int(result['num_sources']),  # Ensure it's Python int
            'categories': result['categories_used'],
            'suggested_questions': result.get('suggested_questions', []),
            'sources': []
        }
        
        # Safely process sources and convert numpy types
        if 'sources' in result and result['sources']:
            for source in result['sources'][:3]:  # Limit to top 3
                source_data = convert_numpy_types(source)
                response_data['sources'].append(source_data)
        
        print(f"DEBUG: JSON prepared, returning to client")
        
        return jsonify(response_data)
        
    except Exception as e:
        # Print full error details
        import traceback
        error_details = traceback.format_exc()
        print(f"DEBUG: Error in ask_question:")
        print(error_details)
        
        return jsonify({
            'success': False,
            'error': f'Error processing question: {str(e)}'
        }), 500
    
@app.route('/api/stats')
def get_stats():
    """Get system statistics with JSON serialization fix"""
    if not faq_system:
        return jsonify({'error': 'FAQ system not available'}), 500
    
    try:
        metadata = getattr(faq_system, 'metadata', {})
        print(f"Available metadata keys: {list(metadata.keys())}")
        
        # Check if we have rich metadata
        has_rich_metadata = 'total_qa_pairs' in metadata or 'total_faqs' in metadata
        
        if has_rich_metadata:
            total_faqs = (
                metadata.get('total_qa_pairs', 0) or 
                metadata.get('total_faqs', 0) or
                metadata.get('total_questions', 0)
            )
            
            categories = (
                metadata.get('categories', []) or 
                metadata.get('category_names', []) or
                metadata.get('category_list', [])
            )
            
            total_categories = metadata.get('total_categories', len(categories))
            
            print(f"Using rich metadata: {total_faqs} FAQs, {total_categories} categories")
        else:
            # Fallback to basic metadata
            total_faqs = metadata.get('num_documents', 0)
            categories = []
            total_categories = 0
        
        embedding_model = metadata.get('embedding_model', 'unknown')
        
        # Convert all values to ensure JSON serialization
        response_data = {
            'total_faqs': int(total_faqs) if total_faqs else 0,
            'total_categories': int(total_categories) if total_categories else 0,
            'categories': list(categories)[:15] if categories else [],
            'system_status': 'active',
            'has_rich_metadata': bool(has_rich_metadata),
            'embedding_model': str(embedding_model),
            'indexed_at': str(metadata.get('indexed_at', 'unknown'))
        }
        
        return jsonify(response_data)
        
    except Exception as e:
        print(f"Stats error: {e}")
        return jsonify({
            'total_faqs': 0,
            'total_categories': 0,
            'categories': [],
            'error': str(e),
            'system_status': 'error'
        }), 200
    
@app.route('/api/quick-questions')
def get_quick_questions():
    """Get predefined quick questions"""
    quick_questions = [
        "How do I open an account?",
        "What are the trading fees?",
        "Can I trade options?",
        "How do I fund my account?",
        "What is day trading?",
        "How long does account approval take?",
        "What documents do I need?",
        "What are the different account types?"
    ]
    return jsonify(quick_questions)

@app.route('/api/categories')
def get_categories():
    """Get all FAQ categories with sample questions"""
    if not faq_system or not hasattr(faq_system, 'metadata'):
        return jsonify({'error': 'Categories not available'}), 500
    
    categories = faq_system.metadata.get('categories', [])
    return jsonify(categories)

@app.route('/api/reindex', methods=['POST'])
def trigger_reindex():
    """Trigger re-indexing to create rich metadata (development only)"""
    try:
        from indexing import RAGIndexer
        import os
        
        # Configuration
        data_path = "/Users/a16463/Desktop/Tiger_Securities/AI-Agent-Intern-Project---US-Tiger/data"
        vectorstore_path = "/Users/a16463/Desktop/Tiger_Securities/AI-Agent-Intern-Project---US-Tiger/vectorstore"
        
        # Re-run indexing with enhanced metadata
        indexer = RAGIndexer(data_path=data_path)
        vectorstore = indexer.run_indexing_pipeline(vectorstore_path)
        
        # Reload the FAQ system
        global faq_system
        faq_system = SmartFAQSystem()
        
        stats = indexer.get_statistics()
        
        return jsonify({
            'success': True,
            'message': 'Re-indexing completed with rich metadata',
            'stats': stats
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ADD SWAGGER API DOCUMENTATION (separate from your working routes)
# This creates the /docs/ interface without interfering with your existing routes
api = Api(app, doc='/docs/', title='TradeUP FAQ API', description='API Testing Interface')

# Define models for Swagger
ask_model = api.model('Question', {
    'question': fields.String(required=True, example='How do I open an account?')
})

# Swagger-only routes (these create the /docs/ interface)
@api.route('/swagger/ask')
class SwaggerAsk(Resource):
    @api.expect(ask_model)
    def post(self):
        """Swagger documentation for /api/ask endpoint"""
        # This just redirects to your working endpoint
        return ask_question()

@api.route('/swagger/stats')
class SwaggerStats(Resource):
    def get(self):
        """Swagger documentation for /api/stats endpoint"""
        return get_stats()

@api.route('/swagger/quick-questions')
class SwaggerQuickQuestions(Resource):
    def get(self):
        """Swagger documentation for /api/quick-questions endpoint"""
        return get_quick_questions()

@api.route('/swagger/categories')
class SwaggerCategories(Resource):
    def get(self):
        """Swagger documentation for /api/categories endpoint"""
        return get_categories()

# Simple test page that works with your existing endpoints
@app.route('/test')
def test_page():
    """Simple test interface that uses your working API endpoints"""
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>TradeUP FAQ API Tester</title>
        <style>
            body { font-family: Arial; max-width: 800px; margin: 50px auto; padding: 20px; }
            .endpoint { background: #f5f5f5; padding: 15px; margin: 10px 0; border-radius: 5px; }
            button { background: #007bff; color: white; padding: 10px 20px; border: none; border-radius: 3px; cursor: pointer; }
            input { width: 60%; padding: 8px; margin: 5px; }
            .response { background: #e9f7ef; padding: 10px; margin: 10px 0; border-radius: 3px; max-height: 300px; overflow-y: auto; }
            pre { white-space: pre-wrap; font-size: 12px; }
        </style>
    </head>
    <body>
        <h1>TradeUP FAQ API Tester</h1>
        <p><a href="/docs/">Swagger Documentation</a> | <a href="/">Main App</a></p>
        
        <div class="endpoint">
            <h3>POST /api/ask</h3>
            <input type="text" id="question" placeholder="Enter your question" value="How do I open an account?">
            <button onclick="askQuestion()">Ask Question</button>
            <div id="askResponse" class="response" style="display:none;"></div>
        </div>
        
        <div class="endpoint">
            <h3>GET /api/stats</h3>
            <button onclick="getStats()">Get Statistics</button>
            <div id="statsResponse" class="response" style="display:none;"></div>
        </div>
        
        <div class="endpoint">
            <h3>GET /api/quick-questions</h3>
            <button onclick="getQuickQuestions()">Get Quick Questions</button>
            <div id="quickResponse" class="response" style="display:none;"></div>
        </div>

        <script>
            async function askQuestion() {
                const question = document.getElementById('question').value;
                const responseDiv = document.getElementById('askResponse');
                responseDiv.style.display = 'block';
                responseDiv.innerHTML = '<p>Processing...</p>';
                
                try {
                    const response = await fetch('/api/ask', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({question: question})
                    });
                    const data = await response.json();
                    responseDiv.innerHTML = '<pre>' + JSON.stringify(data, null, 2) + '</pre>';
                } catch (error) {
                    responseDiv.innerHTML = '<p>Error: ' + error + '</p>';
                }
            }
            
            async function getStats() {
                const responseDiv = document.getElementById('statsResponse');
                responseDiv.style.display = 'block';
                responseDiv.innerHTML = '<p>Loading...</p>';
                
                try {
                    const response = await fetch('/api/stats');
                    const data = await response.json();
                    responseDiv.innerHTML = '<pre>' + JSON.stringify(data, null, 2) + '</pre>';
                } catch (error) {
                    responseDiv.innerHTML = '<p>Error: ' + error + '</p>';
                }
            }
            
            async function getQuickQuestions() {
                const responseDiv = document.getElementById('quickResponse');
                responseDiv.style.display = 'block';
                responseDiv.innerHTML = '<p>Loading...</p>';
                
                try {
                    const response = await fetch('/api/quick-questions');
                    const data = await response.json();
                    responseDiv.innerHTML = '<pre>' + JSON.stringify(data, null, 2) + '</pre>';
                } catch (error) {
                    responseDiv.innerHTML = '<p>Error: ' + error + '</p>';
                }
            }
        </script>
    </body>
    </html>
    '''

if __name__ == '__main__':
    print("Starting TradeUP Smart FAQ Flask App...")
    print(f"Working directory: {os.getcwd()}")
    
    # Initialize FAQ system
    if init_faq_system():
        print("Starting Flask server...")
        print("Open your browser to:")
        print("   Main App: http://localhost:8000/")
        print("   API Test: http://localhost:8000/test")
        print("   API Docs: http://localhost:8000/docs/")
        app.run(debug=True, host='0.0.0.0', port=8000)
    else:
        print("Failed to start: FAQ system not available")
        print("Make sure smart_faq.py and vectorstore/ are in the same folder")