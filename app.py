# app.py - TradeUP FAQ App - CLEANED VERSION with Essential Swagger Documentation
from flask import Flask, render_template, request, jsonify, session
from flask_restx import Api, Resource, fields
import json
import os
from datetime import datetime, timezone
from dotenv import load_dotenv
import numpy as np

APP_STARTUP_TIME = datetime.now(timezone.utc)
print(f"🚀 App started at: {APP_STARTUP_TIME.isoformat()}")

# Load environment variables
load_dotenv(dotenv_path="notepad.env")

# Import enhanced systems
from optimized_faq_system import LLMPoweredOptimizedFAQSystem

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

try:
    from faq_market_agent import FAQMarketAgent
    faq_market_agent = None
except ImportError:
    print("Warning: FAQ Market Agent not available")
    faq_market_agent = None

try:
    from supabase_memory import OptimalChatbotFAQ, create_chatbot
    supabase_faq_system = None
    print("Supabase memory module imported successfully")
except ImportError:
    print("Warning: Supabase memory system not available")
    supabase_faq_system = None

# Initialize systems
llm_powered_faq_system = None
processing_stats = {
    "total_questions": 0,
    "faq_questions": 0,
    "market_questions": 0,
    "avg_response_time": 0.0,
    "cache_hits": 0,
    "llm_analysis_calls": 0
}

def init_llm_powered_faq_system():
    global llm_powered_faq_system
    try:
        llm_powered_faq_system = LLMPoweredOptimizedFAQSystem()
        print("LLM-Powered FAQ System loaded successfully")
        return True
    except Exception as e:
        print(f"Error loading LLM-Powered FAQ system: {e}")
        return False

def init_faq_market_agent():
    global faq_market_agent
    try:
        faq_market_agent = FAQMarketAgent(memory_window=10)
        print("FAQ + Market Data Agent loaded successfully")
        return True
    except Exception as e:
        print(f"Error loading FAQ + Market Data Agent: {e}")
        return False

def init_supabase_faq_system():
    global supabase_faq_system
    try:
        supabase_faq_system = OptimalChatbotFAQ()
        print(f"Supabase FAQ System loaded (memory: {supabase_faq_system.memory_enabled})")
        return True
    except Exception as e:
        print(f"Error loading Supabase FAQ System: {e}")
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

def get_or_create_session(force_new_session=False):
    """
    Simplified session management that works reliably
    """
    global APP_STARTUP_TIME
    
    # Generate user_id if not exists
    if 'user_id' not in session:
        session['user_id'] = f"user_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    user_id = session['user_id']
    current_session_id = session.get('session_id')
    
    # Simple approach: Create new session if forced or no session exists
    should_create_new = force_new_session or not current_session_id
    
    # Add session tracking to Flask session for app restart detection
    app_session_marker = session.get('app_session_marker')
    current_app_marker = APP_STARTUP_TIME.isoformat()
    
    # If the app restarted, the session marker will be different
    if app_session_marker != current_app_marker:
        print(f"🔄 App restarted - creating fresh session")
        should_create_new = True
        session['app_session_marker'] = current_app_marker
    
    # Create new session if needed
    if should_create_new:
        if supabase_faq_system and supabase_faq_system.memory_enabled:
            session_id = supabase_faq_system.create_new_session_for_user(user_id, {
                'source': 'flask_app', 
                'started_at': datetime.now(timezone.utc).isoformat(),
                'app_startup_time': APP_STARTUP_TIME.isoformat(),
                'app_session_marker': current_app_marker
            })
            if session_id:
                session['session_id'] = session_id
                print(f"🆕 Created fresh session: {session_id}")
            else:
                session['session_id'] = None
        else:
            session['session_id'] = None
    else:
        print(f"✅ Using existing session {current_session_id}")
    
    return session.get('session_id'), user_id

def cleanup_old_sessions_on_startup():
    """Clean up old sessions when app starts"""
    if not supabase_faq_system or not supabase_faq_system.memory_enabled:
        return
    
    try:
        print("🧹 Cleaning up sessions from previous app instances...")
        app_startup_iso = APP_STARTUP_TIME.isoformat()
        
        old_sessions = supabase_faq_system.supabase.table('chat_sessions').select('id', 'created_at').eq('status', 'active').lt('created_at', app_startup_iso).execute()
        
        if old_sessions.data:
            for old_session in old_sessions.data:
                supabase_faq_system.supabase.table('chat_sessions').update({
                    'status': 'ended',
                    'updated_at': datetime.now(timezone.utc).isoformat(),
                    'metadata': {'ended_reason': 'app_restart'}
                }).eq('id', old_session['id']).execute()
            
            print(f"✅ Marked {len(old_sessions.data)} old sessions as ended")
        else:
            print("✅ No old sessions to clean up")
            
    except Exception as e:
        print(f"Warning: Could not clean up old sessions: {e}")

# ============================================================================
# CORE ROUTES - ESSENTIAL FOR FUNCTIONALITY
# ============================================================================

@app.route('/')
def home():
    """Serve the main chat interface"""
    try:
        return render_template('index.html')
    except Exception as e:
        print(f"Template error: {e}")
        return jsonify({
            'message': 'TradeUP Enhanced LLM-Powered FAQ API is running',
            'status': 'active',
            'version': '4.1',
            'endpoints': {
                'main_faq': '/api/ask',
                'quick_questions': '/api/quick-questions',
                'stats': '/api/stats',
                'health': '/health'
            }
        })

@app.route('/health')
def health_check():
    """Health check with system status"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'message': 'TradeUP Enhanced FAQ App is running',
        'version': '4.1',
        'systems': {
            'enhanced_llm_faq_system': {
                'available': llm_powered_faq_system is not None
            },
            'faq_market_agent': {
                'available': faq_market_agent is not None
            },
            'supabase_memory': {
                'available': supabase_faq_system is not None,
                'memory_enabled': supabase_faq_system.memory_enabled if supabase_faq_system else False
            }
        },
        'performance': processing_stats
    })

@app.route('/api/ask', methods=['POST'])
def ask_question():
    """Main FAQ endpoint - handles all questions with LLM intelligence"""
    try:
        start_time = datetime.now()
        data = request.get_json()
        question = data.get('question', '').strip()
        force_new_session = data.get('new_session', False)
        
        if not question:
            return jsonify({'success': False, 'error': 'No question provided'}), 400
        
        global processing_stats
        processing_stats["total_questions"] += 1
        
        # Primary: Supabase system with conversation memory
        if supabase_faq_system:
            try:
                session_id, user_id = get_or_create_session(force_new_session=force_new_session)
                conversation_history = []
                if session_id:
                    conversation_history = supabase_faq_system.get_session_history(session_id)
                
                result = supabase_faq_system.ask_question(question, user_id, session_id)
                
                if result['success']:
                    processing_stats["faq_questions"] += 1
                    analysis_data = convert_numpy_types(result.get('analysis', {}))
                    
                    session_debug = {}
                    if session_id:
                        current_question_count = supabase_faq_system.get_user_question_count_current_session(session_id)
                        total_question_count = supabase_faq_system.get_user_question_count_all_sessions(user_id)
                        session_debug = {
                            'current_session_questions': current_question_count,
                            'total_all_sessions': total_question_count,
                            'conversation_history_length': len(conversation_history)
                        }
                    
                    return jsonify({
                        'success': True,
                        'response': result['response'],
                        'system_used': 'supabase_with_memory',
                        'enhanced_llm': True,
                        'memory_enabled': result['memory_enabled'],
                        'session_id': result['session_id'],
                        'intent': result.get('intent', 'general'),
                        'sources_count': result.get('sources_count', 0),
                        'categories': result.get('categories', []),
                        'suggested_questions': result.get('suggested_questions', []),
                        'analysis': analysis_data,
                        'session_debug': session_debug,
                        'processing_time': (datetime.now() - start_time).total_seconds()
                    })
                    
            except Exception as e:
                print(f"Supabase system error: {e}")
        
        # Fallback: Enhanced LLM FAQ System
        if llm_powered_faq_system:
            try:
                result = llm_powered_faq_system.get_smart_response(question, conversation_history=[])
                processing_stats["llm_analysis_calls"] += 1
                
                if result.get('use_market_agent', False):
                    processing_stats["market_questions"] += 1
                    return jsonify({
                        'success': True,
                        'response': f"This question requires real-time market data. {result.get('analysis', {}).get('reasoning', '')}",
                        'system_used': 'routing_fallback',
                        'enhanced_llm': True,
                        'processing_time': (datetime.now() - start_time).total_seconds()
                    })
                
                processing_stats["faq_questions"] += 1
                if result.get('from_cache'):
                    processing_stats["cache_hits"] += 1
                
                return jsonify({
                    'success': True,
                    'response': result['response'],
                    'system_used': 'enhanced_llm_faq_fallback',
                    'enhanced_llm': True,
                    'memory_enabled': False,
                    'analysis': convert_numpy_types(result.get('analysis', {})),
                    'processing_time': result['processing_time'],
                    'sources_count': int(result['num_sources']),
                    'categories': result['categories_used'],
                    'suggested_questions': result['suggested_questions']
                })
                
            except Exception as e:
                print(f"Enhanced LLM FAQ system error: {e}")
        
        return jsonify({
            'success': False,
            'error': 'No FAQ systems available'
        }), 500
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Error processing question: {str(e)}'
        }), 500

@app.route('/api/stats')
def get_stats():
    """Get system statistics and performance metrics"""
    try:
        stats = {
            'total_faqs': 0,
            'total_categories': 0,
            'system_status': 'error',
            'system_performance': processing_stats,
            'version': '4.1'
        }
        
        if llm_powered_faq_system:
            try:
                cache_stats = llm_powered_faq_system.get_cache_stats()
                stats['cache_performance'] = cache_stats
                
                if llm_powered_faq_system.metadata:
                    stats['total_faqs'] = int(llm_powered_faq_system.metadata.get('total_qa_pairs', 0))
                    categories = llm_powered_faq_system.metadata.get('categories', [])
                    stats['total_categories'] = len(categories) if categories else 0
                    stats['categories'] = categories[:10] if categories else []
                
                stats['system_status'] = 'active'
                stats['system_type'] = 'enhanced_llm_powered'
                
            except Exception as e:
                stats['error'] = str(e)
        
        elif supabase_faq_system:
            try:
                stats['system_status'] = 'active'
                stats['system_type'] = 'supabase_llm_powered'
            except Exception as e:
                stats['error'] = str(e)
        
        return jsonify(stats)
        
    except Exception as e:
        return jsonify({
            'total_faqs': 0,
            'total_categories': 0,
            'system_status': 'error',
            'error': str(e)
        }), 500

@app.route('/api/quick-questions')
def get_quick_questions():
    """Get predefined quick questions for UI"""
    quick_questions = [
        "How do I open a TradeUP account?",
        "What are the trading fees and commissions?",
        "How do I fund my trading account?",
        "What documents do I need to get started?",
        "How do I place my first trade?",
        "What are the margin requirements?",
        "Can I trade during extended hours?",
        "How do I withdraw money from my account?"
    ]
    return jsonify(quick_questions)

@app.route('/api/search-faqs', methods=['POST'])
def search_faqs():
    """Search through FAQ database using keywords"""
    try:
        data = request.get_json()
        query = data.get('query', '').strip()
        limit = data.get('limit', 8)
        
        if not query or len(query) < 2:
            return jsonify({'success': False, 'error': 'Query too short (minimum 2 characters)'}), 400
        
        # Your existing FAQ database search logic here
        faq_database = [
            {"question": "How do I open a TradeUP account?", "category": "Account", "keywords": ["account", "open", "new", "start"], "answer": "To open a TradeUP account, visit our website and click 'Sign Up'. You'll need to provide personal information and verify your identity."},
            {"question": "What documents do I need to get started?", "category": "Account", "keywords": ["documents", "required", "verification", "id"], "answer": "You need a government-issued ID, Social Security number, and proof of address to get started."},
            {"question": "What are the trading fees and commissions?", "category": "Fees", "keywords": ["fees", "commission", "cost", "price"], "answer": "TradeUP offers commission-free stock trading. Some premium features may have fees."},
            {"question": "How do I fund my trading account?", "category": "Funding", "keywords": ["fund", "deposit", "money", "transfer"], "answer": "You can fund your account via ACH transfer, wire transfer, or mobile check deposit."},
            {"question": "How do I withdraw money from my account?", "category": "Funding", "keywords": ["withdraw", "withdrawal", "money", "cash"], "answer": "Withdrawals can be made through ACH transfer to your linked bank account, usually taking 1-3 business days."},
            {"question": "How do I place my first trade?", "category": "Trading", "keywords": ["trade", "first", "buy", "sell"], "answer": "To place your first trade, search for a stock, select the number of shares, choose your order type, and confirm the trade."},
            {"question": "What are the margin requirements?", "category": "Trading", "keywords": ["margin", "requirements", "leverage"], "answer": "Margin trading requires a minimum account balance of $2,000 and approval for margin privileges."},
            {"question": "Can I trade during extended hours?", "category": "Trading", "keywords": ["extended", "hours", "after", "pre"], "answer": "Yes, TradeUP offers extended hours trading from 4:00 AM to 8:00 PM ET."},
            {"question": "What is a cash account?", "category": "Account", "keywords": ["cash", "account", "type"], "answer": "A cash account requires you to pay for securities purchases in full and doesn't allow borrowing."},
            {"question": "What is a margin account?", "category": "Account", "keywords": ["margin", "account", "borrowing"], "answer": "A margin account allows you to borrow money from TradeUP to purchase securities."},
            {"question": "How do I set up two-factor authentication?", "category": "Security", "keywords": ["2fa", "security", "authentication"], "answer": "Enable 2FA in your account settings for enhanced security."},
            {"question": "What are fractional shares?", "category": "Trading", "keywords": ["fractional", "partial", "shares"], "answer": "Fractional shares allow you to buy portions of expensive stocks with smaller amounts of money."},
        ]
        
        query_lower = query.lower()
        results = []
        
        # Search algorithm
        for faq in faq_database:
            score = 0
            
            # Check question text
            if query_lower in faq["question"].lower():
                score += 0.8
            
            # Check keywords
            for keyword in faq["keywords"]:
                if query_lower in keyword or keyword in query_lower:
                    score += 0.6
                if query_lower == keyword:
                    score += 0.9
            
            if score > 0:
                results.append({
                    "question": faq["question"],
                    "answer_preview": faq["answer"][:100] + "..." if len(faq["answer"]) > 100 else faq["answer"],
                    "category": faq["category"],
                    "relevance_score": round(min(score, 1.0), 2),
                    "full_answer": faq["answer"]
                })
        
        # Sort by relevance
        results.sort(key=lambda x: x["relevance_score"], reverse=True)
        
        return jsonify({
            'success': True,
            'query': query,
            'results': results[:limit],
            'total_found': len(results),
            'showing': min(len(results), limit)
        })
        
    except Exception as e:
        print(f"Search error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/search-suggestions')
def get_search_suggestions():
    """Get search suggestions based on FAQ categories"""
    suggestions = [
        # Account related
        "account opening", "new account", "verification", "documents needed",
        # Trading related  
        "trading fees", "commissions", "margin requirements", "first trade",
        # Funding related
        "deposit money", "fund account", "withdraw funds", "ACH transfer",
        # Features
        "extended hours", "after hours", "fractional shares", "options trading",
        # Account types
        "cash account", "margin account", "day trading", "IRA account",
        # Security
        "two factor authentication", "2FA", "security", "password reset"
    ]
    
    return jsonify({
        'success': True,
        'suggestions': suggestions
    })

@app.route('/api/feedback', methods=['GET', 'POST'])
def submit_feedback():
    """Submit user feedback using Supabase"""
    
    if request.method == 'GET':
        return jsonify({
            'message': 'Feedback system information',
            'note': 'Use POST to submit feedback',
            'required_fields': ['question', 'feedback_type', 'session_id'],
            'test_page': 'Visit /test for interactive testing'
        })
    
    try:
        data = request.get_json()
        
        # Validate required fields
        question = data.get('question', '').strip()
        feedback_type = data.get('feedback_type', '').strip().lower()
        session_id = data.get('session_id', '').strip()
        user_id = data.get('user_id', 'anonymous')
        
        if not question:
            return jsonify({'success': False, 'error': 'Question is required'}), 400
            
        if feedback_type not in ['up', 'down']:
            return jsonify({'success': False, 'error': 'Invalid feedback type'}), 400
        
        if not session_id:
            return jsonify({'success': False, 'error': 'Session ID is required'}), 400
        
        # NEW: Check if session exists, create if it doesn't
        if supabase_faq_system and supabase_faq_system.memory_enabled:
            try:
                # Try to get the session
                session_check = supabase_faq_system.supabase.table('chat_sessions').select('id').eq('id', session_id).execute()
                
                if not session_check.data:
                    # Session doesn't exist, create it
                    print(f"🔧 Creating missing session: {session_id}")
                    session_data = {
                        'id': session_id,
                        'user_id': user_id,
                        'status': 'active',
                        'metadata': {
                            'created_for': 'feedback_submission',
                            'auto_created': True
                        }
                    }
                    supabase_faq_system.supabase.table('chat_sessions').insert(session_data).execute()
                    print(f"✅ Auto-created session {session_id} for feedback")
                    
            except Exception as session_error:
                print(f"⚠️ Session creation error: {session_error}")
                return jsonify({
                    'success': False, 
                    'error': f'Invalid session ID: {session_id}',
                    'details': 'Session does not exist and could not be created'
                }), 400
        
        # Optional fields
        answer_preview = data.get('answer_preview', '')
        system_used = data.get('system_used', '')
        categories = data.get('categories', [])
        sources_count = data.get('sources_count', 0)
        
        # Get user info
        user_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.environ.get('REMOTE_ADDR', ''))
        user_agent = request.headers.get('User-Agent', '')[:500]
        
        # Submit feedback using Supabase
        feedback_id = supabase_faq_system.submit_feedback(
            session_id=session_id,
            user_id=user_id,
            question=question,
            feedback_type=feedback_type,
            answer_preview=answer_preview,
            system_used=system_used,
            categories=categories,
            sources_count=sources_count,
            user_ip=user_ip,
            user_agent=user_agent
        )
        
        if feedback_id:
            return jsonify({
                'success': True,
                'message': 'Feedback submitted successfully',
                'feedback_id': feedback_id,
                'feedback_type': feedback_type,
                'session_id': session_id,
                'database': 'supabase'
            })
        else:
            return jsonify({
                'success': False, 
                'error': 'Failed to store feedback'
            }), 500
        
    except Exception as e:
        print(f"Feedback submission error: {e}")
        return jsonify({
            'success': False, 
            'error': 'Internal server error',
            'details': str(e)
        }), 500

@app.route('/api/feedback/stats')
def get_feedback_stats():
    """Get feedback statistics from Supabase"""
    try:
        stats = supabase_faq_system.get_feedback_stats()
        return jsonify(stats)
        
    except Exception as e:
        print(f"Feedback stats error: {e}")
        return jsonify({
            'success': False, 
            'error': 'Failed to get feedback stats'
        }), 500

@app.route('/api/feedback/user/<user_id>')
def get_user_feedback(user_id):
    """Get feedback history for a specific user"""
    try:
        limit = request.args.get('limit', 50, type=int)
        feedback_history = supabase_faq_system.get_user_feedback_history(user_id, limit)
        
        return jsonify({
            'success': True,
            'user_id': user_id,
            'feedback_history': feedback_history,
            'count': len(feedback_history)
        })
        
    except Exception as e:
        print(f"User feedback history error: {e}")
        return jsonify({
            'success': False, 
            'error': 'Failed to get user feedback'
        }), 500

@app.route('/api/feedback/session/<session_id>')
def get_session_feedback(session_id):
    """Get feedback for a specific session"""
    try:
        session_feedback = supabase_faq_system.get_session_feedback(session_id)
        
        return jsonify({
            'success': True,
            'session_id': session_id,
            'feedback': session_feedback,
            'count': len(session_feedback)
        })
        
    except Exception as e:
        print(f"Session feedback error: {e}")
        return jsonify({
            'success': False, 
            'error': 'Failed to get session feedback'
        }), 500

@app.route('/api/feedback/user/<user_id>/sessions')
def get_user_sessions_with_feedback(user_id):
    """Get user sessions that have feedback"""
    try:
        sessions = supabase_faq_system.get_user_sessions_with_feedback(user_id)
        
        return jsonify({
            'success': True,
            'user_id': user_id,
            'sessions_with_feedback': sessions,
            'count': len(sessions)
        })
        
    except Exception as e:
        print(f"User sessions with feedback error: {e}")
        return jsonify({
            'success': False, 
            'error': 'Failed to get user sessions with feedback'
        }), 500

@app.route('/api/feedback/session/<session_id>/summary')
def get_session_feedback_summary(session_id):
    """Get feedback summary for a specific session"""
    try:
        summary = supabase_faq_system.get_feedback_summary_for_session(session_id)
        
        if 'error' in summary:
            return jsonify({
                'success': False,
                'error': summary['error']
            }), 500
        
        return jsonify({
            'success': True,
            **summary
        })
        
    except Exception as e:
        print(f"Session feedback summary error: {e}")
        return jsonify({
            'success': False, 
            'error': 'Failed to get session feedback summary'
        }), 500
    
# ============================================================================
# SWAGGER API DOCUMENTATION
# ========@====================================================================

api = Api(app, doc='/docs/', title='TradeUP Enhanced LLM FAQ API', 
         description='''
## TradeUP Enhanced FAQ System with Advanced LLM Intelligence

This API provides intelligent customer service responses using advanced LLM technology.

### Core Features
- **Enhanced LLM Intelligence**: Advanced question analysis and response generation
- **Smart Conversation Analysis**: LLM-based conversation understanding  
- **Multi-Strategy Search**: Enhanced vector search with multiple fallback strategies
- **Intelligent Routing**: LLM-powered routing between FAQ and market data
- **Persistent Memory**: Supabase-powered conversation history and analytics
- **Response Optimization**: Caching and performance optimization
- **User Feedback System**: Thumbs up/down feedback with analytics

### Key Endpoints
- **POST /api/ask**: Main FAQ endpoint with LLM intelligence
- **GET /api/stats**: System statistics and performance metrics
- **GET /api/quick-questions**: Predefined common questions
- **POST /api/feedback**: Submit user feedback (thumbs up/down)
- **GET /api/feedback/stats**: Get feedback analytics
- **GET /health**: Health check and system status
         ''', version='4.1')

# Define models for Swagger documentation
ask_model = api.model('Question', {
    'question': fields.String(required=True, description='Customer question', example='How do I open a TradeUP account?'),
    'new_session': fields.Boolean(required=False, description='Force create new session', example=False)
})

response_model = api.model('FAQResponse', {
    'success': fields.Boolean(description='Request success status'),
    'response': fields.String(description='LLM-generated intelligent response'),
    'system_used': fields.String(description='System that handled the request'),
    'enhanced_llm': fields.Boolean(description='Whether enhanced LLM was used'),
    'memory_enabled': fields.Boolean(description='Whether conversation memory is enabled'),
    'session_id': fields.String(description='Current session identifier'),
    'processing_time': fields.Float(description='Processing time in seconds'),
    'sources_count': fields.Integer(description='Number of FAQ sources used'),
    'categories': fields.List(fields.String, description='FAQ categories used'),
    'suggested_questions': fields.List(fields.String, description='Follow-up questions'),
    'session_debug': fields.Raw(description='Session debugging information')
})

stats_model = api.model('Stats', {
    'total_faqs': fields.Integer(description='Total FAQ entries'),
    'total_categories': fields.Integer(description='Number of categories'),
    'system_status': fields.String(description='System status'),
    'system_performance': fields.Raw(description='Performance metrics'),
    'cache_performance': fields.Raw(description='Cache statistics'),
    'version': fields.String(description='API version')
})

health_model = api.model('Health', {
    'status': fields.String(description='Health status'),
    'timestamp': fields.String(description='Check timestamp'),
    'message': fields.String(description='Status message'),
    'version': fields.String(description='API version'),
    'systems': fields.Raw(description='Available systems status'),
    'performance': fields.Raw(description='Performance statistics')
})

search_request_model = api.model('SearchRequest', {
    'query': fields.String(required=True, description='Search query', example='account opening'),
    'limit': fields.Integer(required=False, description='Maximum results to return', example=8, default=8)
})

search_result_model = api.model('SearchResult', {
    'question': fields.String(description='FAQ question'),
    'answer_preview': fields.String(description='Preview of the answer'),
    'category': fields.String(description='FAQ category'),
    'relevance_score': fields.Float(description='Relevance score (0-1)'),
    'full_answer': fields.String(description='Complete answer text')
})

search_response_model = api.model('SearchResponse', {
    'success': fields.Boolean(description='Request success status'),
    'query': fields.String(description='Original search query'),
    'results': fields.List(fields.Nested(search_result_model), description='Search results'),
    'total_found': fields.Integer(description='Total number of results found'),
    'showing': fields.Integer(description='Number of results returned'),
    'message': fields.String(description='Optional message')
})

search_suggestions_model = api.model('SearchSuggestions', {
    'suggestions': fields.List(fields.String, description='List of search suggestions')
})

# FEEDBACK MODELS
feedback_request_model = api.model('FeedbackRequest', {
    'question': fields.String(required=True, description='The original question', example='How do I open an account?'),
    'feedback_type': fields.String(required=True, description='Feedback type', enum=['up', 'down'], example='up'),
    'session_id': fields.String(required=True, description='Session identifier', example='123e4567-e89b-12d3-a456-426614174000'),
    'user_id': fields.String(required=False, description='User identifier', example='user_20250723_142830'),
    'answer_preview': fields.String(description='Preview of the answer provided', example='To open a TradeUP account...'),
    'system_used': fields.String(description='Which system provided the answer', example='supabase_with_memory'),
    'categories': fields.List(fields.String, description='FAQ categories involved', example=['account', 'opening']),
    'sources_count': fields.Integer(description='Number of sources used', example=3)
})

feedback_response_model = api.model('FeedbackResponse', {
    'success': fields.Boolean(description='Success status'),
    'message': fields.String(description='Response message'),
    'feedback_id': fields.String(description='Unique feedback ID'),
    'feedback_type': fields.String(description='Type of feedback submitted'),
    'database': fields.String(description='Database used (supabase)')
})

feedback_stats_model = api.model('FeedbackStats', {
    'success': fields.Boolean(description='Success status'),
    'stats': fields.Raw(description='Feedback statistics object', example={
        'total_feedback': 150,
        'thumbs_up': 120,
        'thumbs_down': 30,
        'satisfaction_rate': 80.0,
        'database_type': 'supabase'
    })
})

user_feedback_response_model = api.model('UserFeedbackResponse', {
    'success': fields.Boolean(description='Success status'),
    'user_id': fields.String(description='User identifier'),
    'feedback_history': fields.List(fields.Raw, description='List of feedback entries'),
    'count': fields.Integer(description='Number of feedback entries')
})

session_feedback_response_model = api.model('SessionFeedbackResponse', {
    'success': fields.Boolean(description='Success status'),
    'session_id': fields.String(description='Session identifier'),
    'feedback': fields.List(fields.Raw, description='List of feedback entries for session'),
    'count': fields.Integer(description='Number of feedback entries')
})

# Swagger documentation routes
@api.route('/swagger/ask')
class SwaggerAsk(Resource):
    @api.expect(ask_model)
    @api.marshal_with(response_model)
    @api.doc(description='''
    **Enhanced LLM-Powered FAQ Endpoint**
    
    This endpoint uses advanced LLM intelligence to:
    - Analyze question intent and complexity
    - Route to appropriate system (FAQ vs Market data)
    - Generate comprehensive, contextual responses
    - Maintain conversation memory across sessions
    - Provide intelligent follow-up suggestions
    
    **Features:**
    - Multi-strategy search for better accuracy
    - LLM-powered question analysis
    - Smart routing between systems
    - Response caching for performance
    - Session-based conversation memory
    ''')
    def post(self):
        """Main FAQ endpoint with enhanced LLM intelligence"""
        pass  # Documentation only - actual implementation is in ask_question()

@api.route('/swagger/stats')
class SwaggerStats(Resource):
    @api.marshal_with(stats_model)
    @api.doc(description='''
    **System Statistics and Performance**
    
    Returns comprehensive information about:
    - FAQ database size and categories
    - System performance metrics
    - Cache performance statistics
    - Available system features
    ''')
    def get(self):
        """System statistics and performance metrics"""
        pass  # Documentation only

@api.route('/swagger/quick-questions')
class SwaggerQuickQuestions(Resource):
    @api.marshal_with(fields.List(fields.String))
    @api.doc(description='''
    **Predefined Quick Questions**
    
    Returns a curated list of commonly asked questions for:
    - UI quick-select buttons
    - New user suggestions
    - Common topic discovery
    ''')
    def get(self):
        """Predefined common questions"""
        pass  # Documentation only

@api.route('/swagger/health')
class SwaggerHealth(Resource):
    @api.marshal_with(health_model)
    @api.doc(description='''
    **Health Check and System Status**
    
    Returns current system health including:
    - Overall system status
    - Individual component availability
    - Performance statistics
    - Version information
    ''')
    def get(self):
        """Health check and system status"""
        pass  # Documentation only

@api.route('/swagger/search-faqs')
class SwaggerSearchFAQs(Resource):
    @api.expect(search_request_model)
    @api.marshal_with(search_response_model)
    @api.doc(description='''
    **FAQ Database Search**
    
    Search through the entire FAQ database using keywords or phrases.
    
    **Features:**
    - Searches through 128+ FAQ entries across 16 categories
    - Keyword matching with relevance scoring
    - Returns ranked results with answer previews
    - Supports partial matches and synonyms
    
    **Search Tips:**
    - Use keywords like: account, fees, trading, margin, deposit
    - Minimum 2 characters required
    - Results sorted by relevance score
    ''')
    def post(self):
        """Search FAQ database with keywords"""
        pass  # Documentation only

@api.route('/swagger/search-suggestions')
class SwaggerSearchSuggestions(Resource):
    @api.marshal_with(search_suggestions_model)
    @api.doc(description='''
    **Search Suggestions**
    
    Get suggested search terms based on popular FAQ categories and topics.
    
    **Use Cases:**
    - Autocomplete functionality
    - Search guidance for users
    - Popular topic discovery
    ''')
    def get(self):
        """Get search suggestions for FAQ topics"""
        pass  # Documentation only

# FEEDBACK SWAGGER DOCUMENTATION
@api.route('/swagger/feedback')
class SwaggerFeedback(Resource):
    @api.expect(feedback_request_model)
    @api.marshal_with(feedback_response_model)
    @api.doc(description='''
    **Submit User Feedback**
    
    Allows users to submit thumbs up/down feedback for FAQ responses.
    
    **Features:**
    - Tracks user satisfaction with answers
    - Links feedback to original questions and sessions
    - Stores system performance metrics
    - Captures user context (IP, user agent)
    - Provides data for admin analytics
    
    **Usage:**
    - Called automatically when users click 👍 or 👎 buttons
    - Helps improve FAQ system accuracy
    - Provides insights into problematic questions
    
    **Required Fields:**
    - question: The original question asked
    - feedback_type: Either "up" or "down"
    - session_id: Current user session ID
    ''')
    def post(self):
        """Submit thumbs up/down feedback for FAQ responses"""
        pass

@api.route('/swagger/feedback-stats')
class SwaggerFeedbackStats(Resource):
    @api.marshal_with(feedback_stats_model)
    @api.doc(description='''
    **Feedback Analytics Dashboard**
    
    Provides comprehensive feedback statistics for admin monitoring.
    
    **Metrics Include:**
    - Overall satisfaction rates (thumbs up vs down)
    - Total feedback count
    - System performance insights
    - Database type information
    
    **Use Cases:**
    - Monitor user satisfaction trends
    - Identify areas for improvement
    - Track system performance over time
    - Generate reports for stakeholders
    ''')
    def get(self):
        """Get detailed feedback statistics and analytics"""
        pass

@api.route('/swagger/feedback-user')
class SwaggerUserFeedback(Resource):
    @api.marshal_with(user_feedback_response_model)
    @api.doc(description='''
    **User Feedback History**
    
    Get feedback history for a specific user across all sessions.
    
    **Features:**
    - Complete feedback timeline for user
    - Includes questions, answers, and feedback types
    - Useful for user behavior analysis
    - Supports pagination with limit parameter
    
    **Parameters:**
    - user_id (path): The user identifier
    - limit (query): Maximum number of entries to return (default: 50)
    ''')
    def get(self):
        """Get feedback history for a specific user"""
        pass

@api.route('/swagger/feedback-session')
class SwaggerSessionFeedback(Resource):
    @api.marshal_with(session_feedback_response_model)
    @api.doc(description='''
    **Session Feedback Analysis**
    
    Get all feedback for a specific conversation session.
    
    **Features:**
    - Complete feedback for one session
    - Tracks satisfaction throughout conversation
    - Useful for session quality analysis
    - Links to conversation history
    
    **Use Cases:**
    - Analyze conversation quality
    - Debug problematic sessions
    - Understand user satisfaction patterns
    ''')
    def get(self):
        """Get feedback for a specific session"""
        pass

# Simple test page for API testing
@app.route('/test')
def test_page():
    """Simple test interface for API endpoints"""
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>TradeUP FAQ API Tester</title>
        <style>
            body { font-family: Arial; max-width: 900px; margin: 40px auto; padding: 20px; }
            .endpoint { background: #f8f9fa; padding: 20px; margin: 15px 0; border-radius: 8px; border-left: 4px solid #007bff; }
            button { background: #007bff; color: white; padding: 12px 24px; border: none; border-radius: 5px; cursor: pointer; margin: 5px; }
            button:hover { background: #0056b3; }
            input, select, textarea { width: 70%; padding: 10px; margin: 8px; border: 1px solid #ddd; border-radius: 4px; }
            .response { background: #e8f5e8; padding: 15px; margin: 10px 0; border-radius: 5px; max-height: 400px; overflow-y: auto; border: 1px solid #c3e6c3; }
            pre { white-space: pre-wrap; font-size: 13px; line-height: 1.4; }
            h1 { color: #333; }
            h2 { color: #28a745; margin-top: 30px; }
            h3 { color: #007bff; margin-bottom: 10px; }
            .nav { margin-bottom: 30px; }
            .nav a { color: #007bff; text-decoration: none; margin-right: 20px; }
            .feedback-section { border-top: 3px solid #28a745; background: #f0fff0; }
        </style>
    </head>
    <body>
        <h1>TradeUP FAQ API Tester</h1>
        <div class="nav">
            <a href="/docs/">📚 API Documentation</a> | 
            <a href="/">🏠 Main App</a> | 
            <a href="/health">💓 Health Check</a>
        </div>
        
        <div class="endpoint">
            <h3>🤖 POST /api/ask - Enhanced LLM FAQ</h3>
            <p>Ask questions with advanced LLM intelligence and conversation memory.</p>
            <input type="text" id="question" placeholder="Enter your question" value="How do I open a TradeUP account?">
            <button onclick="askQuestion()">Ask Question</button>
            <div id="askResponse" class="response" style="display:none;"></div>
        </div>
        
        <div class="endpoint">
            <h3>📊 GET /api/stats - System Statistics</h3>
            <p>View system performance and FAQ database information.</p>
            <button onclick="getStats()">Get Statistics</button>
            <div id="statsResponse" class="response" style="display:none;"></div>
        </div>
        
        <div class="endpoint">
            <h3>⚡ GET /api/quick-questions - Quick Questions</h3>
            <p>Get predefined common questions for testing.</p>
            <button onclick="getQuickQuestions()">Get Quick Questions</button>
            <div id="quickResponse" class="response" style="display:none;"></div>
        </div>

        <div class="endpoint">
            <h3>🔍 POST /api/search-faqs - FAQ Database Search</h3>
            <p>Search through the entire FAQ database using keywords.</p>
            <input type="text" id="searchQuery" placeholder="Enter search query" value="account">
            <input type="number" id="searchLimit" placeholder="Limit" value="5" style="width: 80px;">
            <button onclick="searchFAQs()">Search FAQs</button>
            <div id="searchResponse" class="response" style="display:none;"></div>
        </div>

        <div class="endpoint">
            <h3>💡 GET /api/search-suggestions - Search Suggestions</h3>
            <p>Get suggested search terms for FAQ topics.</p>
            <button onclick="getSearchSuggestions()">Get Suggestions</button>
            <div id="suggestionsResponse" class="response" style="display:none;"></div>
        </div>

        <h2>👍👎 Feedback System Testing</h2>

        <div class="endpoint feedback-section">
            <h3>👍 POST /api/feedback - Submit User Feedback</h3>
            <p>Submit thumbs up/down feedback for FAQ responses.</p>
            <textarea id="feedbackQuestion" placeholder="Enter question" rows="2">How do I open an account?</textarea><br>
            <input type="text" id="feedbackSessionId" placeholder="Session ID (will auto-fill)" value="" style="width: 45%;"><br>
            <input type="text" id="feedbackUserId" placeholder="User ID (will auto-fill)" value="" style="width: 45%;"><br>
            <select id="feedbackType" style="width: 30%;">
                <option value="up">👍 Thumbs Up</option>
                <option value="down">👎 Thumbs Down</option>
            </select>
            <input type="text" id="feedbackSystem" placeholder="System Used" value="supabase_with_memory" style="width: 35%;"><br>
            <button onclick="loadSessionInfoAndSubmit()">Get Session Info & Submit Feedback</button>
            <div id="feedbackTestResponse" class="response" style="display:none;"></div>
        </div>

        <div class="endpoint feedback-section">
            <h3>📊 GET /api/feedback/stats - Feedback Statistics</h3>
            <p>Get comprehensive feedback analytics and satisfaction rates.</p>
            <button onclick="getFeedbackStats()">Get Feedback Stats</button>
            <div id="feedbackStatsResponse" class="response" style="display:none;"></div>
        </div>

        <div class="endpoint feedback-section">
            <h3>👤 GET /api/feedback/user/{user_id} - User Feedback History</h3>
            <p>Get feedback history for a specific user.</p>
            <input type="text" id="userFeedbackId" placeholder="User ID" value="test_user_123" style="width: 60%;">
            <input type="number" id="userFeedbackLimit" placeholder="Limit" value="10" style="width: 15%;">
            <button onclick="getUserFeedback()">Get User Feedback</button>
            <div id="userFeedbackResponse" class="response" style="display:none;"></div>
        </div>

        <div class="endpoint feedback-section">
            <h3>🔗 GET /api/feedback/session/{session_id} - Session Feedback</h3>
            <p>Get all feedback for a specific conversation session.</p>
            <input type="text" id="sessionFeedbackId" placeholder="Session ID" value="123e4567-e89b-12d3-a456-426614174000">
            <button onclick="getSessionFeedback()">Get Session Feedback</button>
            <div id="sessionFeedbackResponse" class="response" style="display:none;"></div>
        </div>

        <script>
            async function askQuestion() {
                const question = document.getElementById('question').value;
                const responseDiv = document.getElementById('askResponse');
                responseDiv.style.display = 'block';
                responseDiv.innerHTML = '<p>🤖 Processing with enhanced LLM intelligence...</p>';
                
                try {
                    const response = await fetch('/api/ask', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({question: question})
                    });
                    const data = await response.json();
                    responseDiv.innerHTML = '<pre>' + JSON.stringify(data, null, 2) + '</pre>';
                } catch (error) {
                    responseDiv.innerHTML = '<p>❌ Error: ' + error + '</p>';
                }
            }
            
            async function getStats() {
                const responseDiv = document.getElementById('statsResponse');
                responseDiv.style.display = 'block';
                responseDiv.innerHTML = '<p>📊 Loading statistics...</p>';
                
                try {
                    const response = await fetch('/api/stats');
                    const data = await response.json();
                    responseDiv.innerHTML = '<pre>' + JSON.stringify(data, null, 2) + '</pre>';
                } catch (error) {
                    responseDiv.innerHTML = '<p>❌ Error: ' + error + '</p>';
                }
            }
            
            async function getQuickQuestions() {
                const responseDiv = document.getElementById('quickResponse');
                responseDiv.style.display = 'block';
                responseDiv.innerHTML = '<p>⚡ Loading quick questions...</p>';
                
                try {
                    const response = await fetch('/api/quick-questions');
                    const data = await response.json();
                    responseDiv.innerHTML = '<pre>' + JSON.stringify(data, null, 2) + '</pre>';
                } catch (error) {
                    responseDiv.innerHTML = '<p>❌ Error: ' + error + '</p>';
                }
            }

            async function searchFAQs() {
                const query = document.getElementById('searchQuery').value;
                const limit = parseInt(document.getElementById('searchLimit').value) || 5;
                const responseDiv = document.getElementById('searchResponse');
                responseDiv.style.display = 'block';
                responseDiv.innerHTML = '<p>🔍 Searching FAQ database...</p>';
                
                try {
                    const response = await fetch('/api/search-faqs', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({query: query, limit: limit})
                    });
                    const data = await response.json();
                    responseDiv.innerHTML = '<pre>' + JSON.stringify(data, null, 2) + '</pre>';
                } catch (error) {
                    responseDiv.innerHTML = '<p>❌ Error: ' + error + '</p>';
                }
            }

            async function getSearchSuggestions() {
                const responseDiv = document.getElementById('suggestionsResponse');
                responseDiv.style.display = 'block';
                responseDiv.innerHTML = '<p>💡 Loading suggestions...</p>';
                
                try {
                    const response = await fetch('/api/search-suggestions');
                    const data = await response.json();
                    responseDiv.innerHTML = '<pre>' + JSON.stringify(data, null, 2) + '</pre>';
                } catch (error) {
                    responseDiv.innerHTML = '<p>❌ Error: ' + error + '</p>';
                }
            }

            // FEEDBACK TESTING FUNCTIONS
            async function submitTestFeedback() {
                const question = document.getElementById('feedbackQuestion').value;
                const sessionId = document.getElementById('feedbackSessionId').value;
                const userId = document.getElementById('feedbackUserId').value;
                const feedbackType = document.getElementById('feedbackType').value;
                const systemUsed = document.getElementById('feedbackSystem').value;
                const responseDiv = document.getElementById('feedbackTestResponse');
                
                responseDiv.style.display = 'block';
                responseDiv.innerHTML = '<p>👍 Submitting feedback...</p>';
                
                try {
                    const response = await fetch('/api/feedback', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({
                            question: question,
                            feedback_type: feedbackType,
                            session_id: sessionId,
                            user_id: userId,
                            answer_preview: "Test answer preview for feedback submission",
                            system_used: systemUsed,
                            categories: ['account', 'testing'],
                            sources_count: 2
                        })
                    });
                    const data = await response.json();
                    responseDiv.innerHTML = '<pre>' + JSON.stringify(data, null, 2) + '</pre>';
                } catch (error) {
                    responseDiv.innerHTML = '<p>❌ Error: ' + error + '</p>';
                }
            }

            async function getFeedbackStats() {
                const responseDiv = document.getElementById('feedbackStatsResponse');
                responseDiv.style.display = 'block';
                responseDiv.innerHTML = '<p>📊 Loading feedback statistics...</p>';
                
                try {
                    const response = await fetch('/api/feedback/stats');
                    const data = await response.json();
                    responseDiv.innerHTML = '<pre>' + JSON.stringify(data, null, 2) + '</pre>';
                } catch (error) {
                    responseDiv.innerHTML = '<p>❌ Error: ' + error + '</p>';
                }
            }

            async function getUserFeedback() {
                const userId = document.getElementById('userFeedbackId').value;
                const limit = document.getElementById('userFeedbackLimit').value;
                const responseDiv = document.getElementById('userFeedbackResponse');
                
                responseDiv.style.display = 'block';
                responseDiv.innerHTML = '<p>👤 Loading user feedback history...</p>';
                
                try {
                    const response = await fetch(`/api/feedback/user/${userId}?limit=${limit}`);
                    const data = await response.json();
                    responseDiv.innerHTML = '<pre>' + JSON.stringify(data, null, 2) + '</pre>';
                } catch (error) {
                    responseDiv.innerHTML = '<p>❌ Error: ' + error + '</p>';
                }
            }

            async function getSessionFeedback() {
                const sessionId = document.getElementById('sessionFeedbackId').value;
                const responseDiv = document.getElementById('sessionFeedbackResponse');
                
                responseDiv.style.display = 'block';
                responseDiv.innerHTML = '<p>🔗 Loading session feedback...</p>';
                
                try {
                    const response = await fetch(`/api/feedback/session/${sessionId}`);
                    const data = await response.json();
                    responseDiv.innerHTML = '<pre>' + JSON.stringify(data, null, 2) + '</pre>';
                } catch (error) {
                    responseDiv.innerHTML = '<p>❌ Error: ' + error + '</p>';
                }
            }

            async function loadSessionInfoAndSubmit() {
                const responseDiv = document.getElementById('feedbackTestResponse');
                responseDiv.style.display = 'block';
                responseDiv.innerHTML = '<p>🔄 Getting current session info...</p>';
                
                try {
                    // First, get current session info
                    const sessionResponse = await fetch('/api/session-info');
                    const sessionData = await sessionResponse.json();
                    
                    // Fill in the form with real session data
                    document.getElementById('feedbackSessionId').value = sessionData.session_id || 'no-session';
                    document.getElementById('feedbackUserId').value = sessionData.user_id || 'anonymous';
                    
                    responseDiv.innerHTML = '<p>✅ Session info loaded. Now submitting feedback...</p>';
                    
                    // Now submit the feedback
                    setTimeout(() => {
                        submitTestFeedback();
                    }, 500);
                    
                } catch (error) {
                    responseDiv.innerHTML = '<p>❌ Error getting session info: ' + error + '</p>';
                }
            }

            // Keep the existing submitTestFeedback function unchanged
        </script>
    </body>
    </html>
    '''

# ============================================================================
# OPTIONAL ROUTES - FOR DEVELOPMENT/DEBUGGING (can be removed for production)
# ============================================================================

@app.route('/api/new-session', methods=['POST'])
def create_new_session():
    """Force create a new conversation session"""
    try:
        session_id, user_id = get_or_create_session(force_new_session=True)
        return jsonify({
            'success': True,
            'message': 'New conversation session created',
            'session_id': session_id,
            'user_id': user_id
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/session-info')
def get_session_info():
    """Get current session information"""
    try:
        session_id, user_id = get_or_create_session()
        
        session_info = {
            'session_id': session_id,
            'user_id': user_id,
            'app_startup_time': APP_STARTUP_TIME.isoformat(),
            'memory_enabled': supabase_faq_system.memory_enabled if supabase_faq_system else False
        }
        
        if session_id and supabase_faq_system and supabase_faq_system.memory_enabled:
            question_count = supabase_faq_system.get_user_question_count_current_session(session_id)
            session_info['current_session_questions'] = question_count
        
        return jsonify(session_info)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/clear-cache')
def clear_cache():
    """Clear the response cache"""
    if not llm_powered_faq_system:
        return jsonify({'error': 'LLM FAQ system not available'}), 500
    
    llm_powered_faq_system.clear_cache()
    return jsonify({
        'success': True,
        'message': 'Response cache cleared'
    })

# ============================================================================
# APPLICATION STARTUP
# ============================================================================

if __name__ == '__main__':
    print("Starting TradeUP Enhanced LLM-Powered FAQ App...")
    
    # Initialize systems
    enhanced_llm_loaded = init_llm_powered_faq_system()
    market_loaded = init_faq_market_agent()
    supabase_loaded = init_supabase_faq_system()

    # Clean up old sessions
    if supabase_loaded:
        cleanup_old_sessions_on_startup()

    if enhanced_llm_loaded or supabase_loaded:
        print(f"\n🚀 Flask server starting...")
        print(f"🕐 App startup: {APP_STARTUP_TIME.isoformat()}")
        print(f"✅ Auto-fresh sessions enabled")
        
        print(f"\n📡 Available endpoints:")
        print(f"   🏠 Main App: http://localhost:8000/")
        print(f"   📚 API Documentation: http://localhost:8000/docs/")
        print(f"   🧪 API Tester: http://localhost:8000/test")
        print(f"   💓 Health: http://localhost:8000/health")
        print(f"   🤖 FAQ API: http://localhost:8000/api/ask")
        print(f"   📊 Stats: http://localhost:8000/api/stats")
        print(f"   ⚡ Quick Questions: http://localhost:8000/api/quick-questions")
        print(f"   👍 Feedback API: http://localhost:8000/api/feedback")
        print(f"   📈 Feedback Stats: http://localhost:8000/api/feedback/stats")
        
        print(f"\n🎛️ Optional (dev/debug):")
        print(f"   🆕 New Session: http://localhost:8000/api/new-session") 
        print(f"   📋 Session Info: http://localhost:8000/api/session-info")
        print(f"   🧹 Clear Cache: http://localhost:8000/api/clear-cache")
        
        app.run(debug=True, host='0.0.0.0', port=8000)
    else:
        print("❌ Failed to start: No systems available")