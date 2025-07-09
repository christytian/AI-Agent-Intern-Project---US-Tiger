# app.py - Enhanced TradeUP FAQ App with Working Routes
from flask import Flask, render_template, request, jsonify
from flask_restx import Api, Resource, fields
import json
import os
from datetime import datetime
from dotenv import load_dotenv
import numpy as np

# Load environment variables from notepad.env
load_dotenv(dotenv_path="notepad.env")

# Import your Smart FAQ system 
from smarter_faq_rag import SmartFAQSystem

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# Import enhanced systems
try:
    from faq_market_agent import FAQMarketAgent
    faq_market_agent = None
except ImportError:
    print("Warning: FAQ Market Agent not available")
    faq_market_agent = None

try:
    from memory_agent import MemoryEnabledFAQ
    memory_faq_system = None
except ImportError:
    print("Warning: Memory FAQ system not available")
    memory_faq_system = None

# Initialize systems
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

def init_faq_market_agent():
    """Initialize the FAQ + Market Data Agent"""
    global faq_market_agent
    try:
        faq_market_agent = FAQMarketAgent(memory_window=10)
        print("FAQ + Market Data Agent loaded successfully")
        return True
    except Exception as e:
        print(f"Error loading FAQ + Market Data Agent: {e}")
        return False

def init_memory_faq_system():
    """Initialize the Memory-Enabled FAQ system"""
    global memory_faq_system
    try:
        memory_faq_system = MemoryEnabledFAQ(memory_window=10)
        print("Memory-Enabled FAQ System loaded successfully")
        return True
    except Exception as e:
        print(f"Error loading Memory FAQ System: {e}")
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

# ============================================================================
# REGULAR FLASK ROUTES (MUST BE DEFINED BEFORE FLASK-RESTX)
# ============================================================================

@app.route('/')
def home():
    """Serve the main chat interface"""
    print("Home route called!")
    try:
        return render_template('index.html')
    except Exception as e:
        print(f"Template error: {e}")
        # Fallback HTML
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>TradeUP FAQ App</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; }}
                .container {{ max-width: 800px; margin: 0 auto; }}
                .endpoint {{ background: #f5f5f5; padding: 10px; margin: 10px 0; border-radius: 5px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>TradeUP FAQ App is Running!</h1>
                <p><strong>All systems loaded successfully!</strong></p>
                
                <h2>Available Endpoints:</h2>
                <div class="endpoint"><a href="/docs/">API Documentation (Swagger)</a></div>
                <div class="endpoint"><a href="/health">Health Check</a></div>
                <div class="endpoint"><a href="/version">Version Info</a></div>
                <div class="endpoint"><a href="/test">Test Route</a></div>
                <div class="endpoint"><a href="/api/system-status">System Status</a></div>
                <div class="endpoint"><a href="/api/stats">FAQ Statistics</a></div>
                <div class="endpoint"><a href="/api/quick-questions">Quick Questions</a></div>
                
                <h2>FAQ System Status:</h2>
                <div class="endpoint">
                    <strong>Enhanced Agent:</strong> {'Active' if globals().get('faq_market_agent') else 'Inactive'}<br>
                    <strong>Memory System:</strong> {'Active' if globals().get('memory_faq_system') else 'Inactive'}<br>
                    <strong>Basic FAQ:</strong> {'Active' if globals().get('faq_system') else 'Inactive'}
                </div>
                
                <p><em>Note: Using fallback HTML (template error: {str(e)})</em></p>
            </div>
        </body>
        </html>
        """

@app.route('/health')
def health_check():
    """Simple health check endpoint"""
    print("Health route called!")
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'message': 'TradeUP FAQ App is running'
    })

@app.route('/version')
def version():
    """Get application version info"""
    print("Version route called!")
    return jsonify({
        'app_name': 'TradeUP Enhanced FAQ App',
        'version': '2.0',
        'flask_version': '2.x',
        'description': 'Smart FAQ System with Market Data and Memory'
    })

@app.route('/test')
def test_route():
    """Simple test route to verify Flask is working"""
    print("Test route called!")
    return jsonify({
        'message': 'Flask routes are working correctly!',
        'timestamp': datetime.now().isoformat(),
        'available_routes': [
            '/ - Home page',
            '/health - Health check',
            '/version - Version info',
            '/test - This test route',
            '/docs/ - Swagger API documentation',
            '/api/ask - Main FAQ endpoint',
            '/api/system-status - System status',
            '/api/quick-questions - Quick questions',
            '/api/stats - FAQ statistics'
        ]
    })

@app.route('/debug-routes')
def debug_routes():
    """Debug route to see all registered routes"""
    print("Debug routes called!")
    routes = []
    for rule in app.url_map.iter_rules():
        routes.append({
            'endpoint': rule.endpoint,
            'methods': list(rule.methods),
            'rule': str(rule)
        })
    return jsonify({
        'total_routes': len(routes),
        'routes': routes,
        'systems_status': {
            'faq_system': faq_system is not None,
            'memory_faq_system': memory_faq_system is not None, 
            'faq_market_agent': faq_market_agent is not None
        }
    })

@app.route('/api/quick-questions')
def get_quick_questions():
    """Get predefined quick questions for TradeUP"""
    print("Quick questions route called!")
    try:
        quick_questions = [
            "How do I open a TradeUP account?",
            "What are the trading fees and commissions?",
            "Can I trade options and futures?",
            "How do I fund my trading account?",
            "What is day trading and PDT rules?",
            "How long does account approval take?",
            "What documents do I need to get started?",
            "What are the different account types?",
            "How do I place my first trade?",
            "What trading platforms do you offer?",
            "How do I withdraw money from my account?",
            "What are the margin requirements?"
        ]
        print(f"DEBUG: Returning {len(quick_questions)} quick questions")
        return jsonify(quick_questions)
    except Exception as e:
        print(f"Error in /api/quick-questions: {e}")
        return jsonify([])

@app.route('/api/stats')
def get_stats():
    """Get FAQ system statistics with JSON serialization fix"""
    print("Stats route called!")
    try:
        if not faq_system:
            print("DEBUG: FAQ system not available")
            return jsonify({
                'total_faqs': 0,
                'total_categories': 0,
                'categories': [],
                'system_status': 'inactive',
                'error': 'FAQ system not available'
            }), 200
        
        metadata = getattr(faq_system, 'metadata', {})
        print(f"DEBUG: Available metadata keys: {list(metadata.keys())}")
        
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
            print(f"DEBUG: Using rich metadata: {total_faqs} FAQs, {total_categories} categories")
        else:
            # Fallback to basic metadata
            total_faqs = metadata.get('num_documents', 0)
            categories = []
            total_categories = 0
            print(f"DEBUG: Using basic metadata: {total_faqs} documents")
        
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
        
        print(f"DEBUG: Returning stats: {response_data}")
        return jsonify(response_data)
        
    except Exception as e:
        print(f"Error in /api/stats: {e}")
        return jsonify({
            'total_faqs': 0,
            'total_categories': 0,
            'categories': [],
            'error': str(e),
            'system_status': 'error'
        }), 200

# ============================================================================
# INITIALIZE SWAGGER API AFTER REGULAR ROUTES
# ============================================================================

# Initialize API with Swagger documentation
api = Api(app, 
    doc='/docs/', 
    title='TradeUP Enhanced FAQ API', 
    description='Smart FAQ System with Market Data and Memory',
    version='2.0'
)

# Define API models for Swagger documentation
ask_model = api.model('Question', {
    'question': fields.String(required=True, description='The FAQ question to ask', example='How do I open an account?')
})

# ============================================================================
# SWAGGER API ROUTES (These don't interfere with regular routes above)
# ============================================================================

@api.route('/api/ask')
class EnhancedMainAsk(Resource):
    @api.expect(ask_model)
    @api.doc('ask_enhanced', description='Main FAQ endpoint with auto-fallback: tries enhanced agent first, falls back to regular FAQ')
    def post(self):
        """Enhanced main FAQ endpoint - automatically uses best available system"""
        try:
            data = request.get_json()
            question = data.get('question', '').strip()
            
            print(f"Main App Request: {question}")
            
            if not question:
                return {'error': 'No question provided'}, 400
            
            # Strategy 1: Try FAQ + Market Data Agent first (best experience)
            if faq_market_agent:
                try:
                    print("Using FAQ + Market Data Agent (enhanced mode)")
                    result = faq_market_agent.ask_question(question)
                    
                    if result['success']:
                        return {
                            'success': True,
                            'response': result['response'],
                            'system_used': 'enhanced_agent',
                            'capabilities': 'FAQ + Market Data + Memory',
                            'enhanced_features': True,
                            'conversation_length': result['conversation_length'],
                            'tools_available': result['tools_available']
                        }
                    else:
                        print("Enhanced agent failed, trying fallback...")
                except Exception as e:
                    print(f"Enhanced agent error: {e}, trying fallback...")
            
            # Strategy 2: Try Memory FAQ (memory only, no market data)
            elif memory_faq_system:
                try:
                    print("Using Memory FAQ System (memory mode)")
                    result = memory_faq_system.ask_question(question)
                    
                    if result['success']:
                        return {
                            'success': True,
                            'response': result['response'],
                            'system_used': 'memory_faq',
                            'capabilities': 'FAQ + Memory',
                            'enhanced_features': True,
                            'conversation_length': result['conversation_length'],
                            'enhanced_with_context': result['enhanced_with_context']
                        }
                    else:
                        print("Memory FAQ failed, trying basic fallback...")
                except Exception as e:
                    print(f"Memory FAQ error: {e}, trying basic fallback...")
            
            # Strategy 3: Fallback to regular FAQ system
            if not faq_system:
                return {'error': 'No FAQ systems available'}, 500
            
            print("Using basic FAQ system (fallback mode)")
            
            # Get response from regular FAQ system
            result = faq_system.get_smart_response(question)
            
            # Convert numpy types and prepare response
            response_data = {
                'success': True,
                'response': result['response'],
                'system_used': 'basic_faq',
                'capabilities': 'FAQ Only',
                'enhanced_features': False,
                'intent': result['intent_analysis'].get('main_intent', 'General inquiry'),
                'sources_count': int(result['num_sources']),
                'categories': result['categories_used'],
                'suggested_questions': result.get('suggested_questions', []),
                'sources': [],
                'note': 'Enhanced features (market data, memory) not available'
            }
            
            # Process sources
            if 'sources' in result and result['sources']:
                for source in result['sources'][:3]:
                    source_data = convert_numpy_types(source)
                    response_data['sources'].append(source_data)
            
            return response_data
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"Error in main app endpoint:")
            print(error_details)
            
            return {
                'success': False,
                'error': f'Error processing question: {str(e)}',
                'system_used': 'error'
            }, 500

@api.route('/api/system-status')
class SystemStatus(Resource):
    @api.doc('system_status', description='Check which systems are active and main app capabilities')
    def get(self):
        """Get system status and active capabilities"""
        status = {
            'timestamp': datetime.now().isoformat(),
            'main_app_endpoint': '/api/ask',
            'systems': {},
            'main_app_capabilities': [],
            'fallback_strategy': []
        }
        
        # Check FAQ + Market Data Agent
        if faq_market_agent:
            status['systems']['faq_market_agent'] = {
                'status': 'active',
                'priority': 1,
                'description': 'Enhanced agent with FAQ + Market Data + Memory'
            }
            status['main_app_capabilities'].extend([
                'FAQ Search and Answers',
                'Real-time Stock Quotes',
                'Market Overview and Indices', 
                'Stock News and Information',
                'Company Symbol Lookup',
                'Conversation Memory and Context'
            ])
            status['fallback_strategy'].append('1. FAQ + Market Data Agent (enhanced)')
        else:
            status['systems']['faq_market_agent'] = {'status': 'inactive'}
        
        # Check Memory FAQ System
        if memory_faq_system:
            status['systems']['memory_faq_system'] = {
                'status': 'active',
                'priority': 2,
                'description': 'FAQ system with conversation memory'
            }
            if not faq_market_agent:  # Only add if not already covered
                status['main_app_capabilities'].extend([
                    'FAQ Search and Answers',
                    'Conversation Memory and Context'
                ])
            status['fallback_strategy'].append('2. Memory FAQ System (memory only)')
        else:
            status['systems']['memory_faq_system'] = {'status': 'inactive'}
        
        # Check regular FAQ system
        if faq_system:
            status['systems']['basic_faq_system'] = {
                'status': 'active',
                'priority': 3,
                'description': 'Original TradeUP FAQ system'
            }
            if not faq_market_agent and not memory_faq_system:  # Only add if not covered
                status['main_app_capabilities'].append('FAQ Search and Answers')
            status['fallback_strategy'].append('3. Basic FAQ System (fallback)')
        else:
            status['systems']['basic_faq_system'] = {'status': 'inactive'}
        
        # Determine main app mode
        if faq_market_agent:
            status['main_app_mode'] = 'enhanced'
            status['primary_system'] = 'FAQ + Market Data + Memory'
        elif memory_faq_system:
            status['main_app_mode'] = 'memory_enabled'
            status['primary_system'] = 'FAQ + Memory'
        elif faq_system:
            status['main_app_mode'] = 'basic'
            status['primary_system'] = 'FAQ Only'
        else:
            status['main_app_mode'] = 'error'
            status['primary_system'] = 'No systems available'
        
        return status

@api.route('/api/conversation-history')
class ConversationHistory(Resource):
    @api.doc('conversation_history', description='Get/clear conversation history from active enhanced system')
    def get(self):
        """Get conversation history from the active enhanced system"""
        # Try to get history from the best available system
        if faq_market_agent:
            try:
                history = faq_market_agent.get_conversation_history()
                return {
                    'conversation_history': history,
                    'total_conversations': len(history),
                    'system_source': 'faq_market_agent'
                }
            except Exception as e:
                return {'error': f'Error retrieving agent history: {str(e)}'}, 500
        
        elif memory_faq_system:
            try:
                history = memory_faq_system.get_conversation_history()
                return {
                    'conversation_history': history,
                    'total_conversations': len(history),
                    'system_source': 'memory_faq_system'
                }
            except Exception as e:
                return {'error': f'Error retrieving memory history: {str(e)}'}, 500
        
        else:
            return {
                'conversation_history': [],
                'total_conversations': 0,
                'system_source': 'none',
                'message': 'No enhanced systems with memory available'
            }
    
    def delete(self):
        """Clear conversation memory from active enhanced system"""
        cleared_systems = []
        errors = []
        
        # Clear from all available enhanced systems
        if faq_market_agent:
            try:
                faq_market_agent.clear_memory()
                cleared_systems.append('faq_market_agent')
            except Exception as e:
                errors.append(f'Agent clear error: {str(e)}')
        
        if memory_faq_system:
            try:
                memory_faq_system.clear_memory()
                cleared_systems.append('memory_faq_system')
            except Exception as e:
                errors.append(f'Memory clear error: {str(e)}')
        
        if cleared_systems:
            return {
                'success': True,
                'message': f'Conversation memory cleared from: {", ".join(cleared_systems)}',
                'cleared_systems': cleared_systems,
                'errors': errors if errors else None
            }
        else:
            return {
                'success': False,
                'message': 'No enhanced systems with memory available to clear'
            }

@api.route('/api/categories')
class GetCategories(Resource):
    @api.doc('categories', description='Get all FAQ categories')
    def get(self):
        """Get all FAQ categories"""
        if not faq_system or not hasattr(faq_system, 'metadata'):
            return {'error': 'Categories not available'}, 500
        
        categories = faq_system.metadata.get('categories', [])
        return categories

@api.route('/api/reindex')
class TriggerReindex(Resource):
    @api.doc('reindex', description='Trigger re-indexing (development only)')
    def post(self):
        """Trigger re-indexing of FAQ database"""
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
            
            return {
                'success': True,
                'message': 'Re-indexing completed with rich metadata',
                'stats': stats
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }, 500

# ============================================================================
# APPLICATION STARTUP
# ============================================================================

if __name__ == '__main__':
    print("Starting TradeUP Enhanced FAQ App...")
    print(f"Working directory: {os.getcwd()}")
    
    # Initialize systems in order of preference
    faq_loaded = init_faq_system()
    memory_loaded = init_memory_faq_system()
    faq_market_loaded = init_faq_market_agent()
    
    if faq_loaded or memory_loaded or faq_market_loaded:
        print("\nFlask server starting...")
        
        # Debug: Print all registered routes
        print("\nRegistered routes:")
        for rule in app.url_map.iter_rules():
            print(f"  {rule.methods} {rule}")
        
        print("\nAvailable endpoints:")
        print("   Main App: http://localhost:8000/")
        print("   API Docs: http://localhost:8000/docs/")
        print("   Health Check: http://localhost:8000/health")
        print("   Version Info: http://localhost:8000/version")
        print("   Debug Routes: http://localhost:8000/debug-routes")
        print("   Test Route: http://localhost:8000/test")
        print("   Quick Questions: http://localhost:8000/api/quick-questions")
        print("   Stats: http://localhost:8000/api/stats")
        print("\nMain App Features:")
        
        if faq_market_loaded:
            print("   PRIMARY: FAQ + Market Data + Memory (enhanced agent)")
        elif memory_loaded:
            print("   PRIMARY: FAQ + Memory (memory system)")
        elif faq_loaded:
            print("   PRIMARY: FAQ Only (basic system)")
        
        print(f"   Automatic fallback strategy active")
        print(f"   Stock questions: {'Yes' if faq_market_loaded else 'No'}")
        print(f"   Conversation memory: {'Yes' if (faq_market_loaded or memory_loaded) else 'No'}")
        print(f"   Market data: {'Yes' if faq_market_loaded else 'No'}")
        
        app.run(debug=True, host='0.0.0.0', port=8000)
    else:
        print("Failed to start: No systems available")
        print("Make sure required dependencies are installed")