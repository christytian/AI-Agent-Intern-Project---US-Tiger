# app.py - TradeUP FAQ App - CLEANED VERSION with Essential Swagger Documentation
from flask import Flask, request, jsonify, session, send_from_directory
from flask_restx import Api, Resource, fields
from flask_cors import CORS
import json
import os
from datetime import datetime, timezone
from dotenv import load_dotenv
import numpy as np
from typing import List, Dict, Any, Optional
import re
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

APP_STARTUP_TIME = datetime.now(timezone.utc)
print(f"🚀 App started at: {APP_STARTUP_TIME.isoformat()}")

# Load environment variables
load_dotenv(dotenv_path="notepad.env")

# Import enhanced systems
from optimized_faq_system import LLMPoweredOptimizedFAQSystem

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# Enable CORS for React frontend
CORS(app, origins=[
    'http://localhost:3000',  # React development server
    'http://localhost:3001',  # Alternative React port
    'https://your-production-domain.com'  # Add your production domain
], supports_credentials=True)

# Import FAQ Market Agent (FIXED IMPORT PATH)
try:
    from faq_market_agent import FAQMarketAgent  # Removed 'backend.' prefix
    faq_market_agent = None
    print("✅ FAQ Market Agent module imported successfully")
except ImportError as e:
    print(f"⚠️ Warning: FAQ Market Agent not available: {e}")
    faq_market_agent = None

try:
    from supabase_memory import OptimalChatbotFAQ, create_chatbot
    supabase_faq_system = None
    print("✅ Supabase memory module imported successfully")
except ImportError as e:
    print(f"⚠️ Warning: Supabase memory system not available: {e}")
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
        print("✅ LLM-Powered FAQ System loaded successfully")
        return True
    except Exception as e:
        print(f"❌ Error loading LLM-Powered FAQ system: {e}")
        return False

def init_faq_market_agent():
    global faq_market_agent
    try:
        print("🔄 Initializing FAQ Market Agent...")
        faq_market_agent = FAQMarketAgent(memory_window=10)
        print("✅ FAQ + Market Data Agent loaded successfully")
        return True
    except Exception as e:
        print(f"❌ Error loading FAQ + Market Data Agent: {e}")
        return False

def init_supabase_faq_system():
    global supabase_faq_system
    try:
        supabase_faq_system = OptimalChatbotFAQ()
        print(f"✅ Supabase FAQ System loaded (memory: {supabase_faq_system.memory_enabled})")
        return True
    except Exception as e:
        print(f"❌ Error loading Supabase FAQ System: {e}")
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
    Returns: (session_id, user_id) tuple
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

def get_conversation_history(session_id):
    """Get conversation history for session"""
    try:
        if supabase_faq_system and supabase_faq_system.memory_enabled and session_id:
            # Get messages from Supabase
            messages = supabase_faq_system.supabase.table('chat_messages').select('*').eq('session_id', session_id).order('created_at', desc=False).execute()
            return messages.data if messages.data else []
        return []
    except Exception as e:
        print(f"Error getting conversation history: {e}")
        return []

def store_message(session_id, content, message_type, user_id=None):
    """Store message in database with proper user_id"""
    try:
        if supabase_faq_system and supabase_faq_system.memory_enabled and session_id:
            # Get user_id from session if not provided
            if not user_id:
                _, user_id = get_or_create_session()
            
            message_data = {
                'session_id': session_id,
                'user_id': user_id,  # FIXED: Always include user_id
                'content': content,
                'message_type': message_type,
                'created_at': datetime.now(timezone.utc).isoformat()
            }
            result = supabase_faq_system.supabase.table('chat_messages').insert(message_data).execute()
            return result.data[0]['id'] if result.data else None
        return None
    except Exception as e:
        print(f"Error storing message: {e}")
        return None

def get_search_suggestions_for_keyword(keyword):
    """Get search suggestions when no results found"""
    keyword_lower = keyword.lower()
    
    # Map keywords to related suggestions
    suggestion_map = {
        'tax': ['tax documents', 'tax forms', '1099', 'statements'],
        'account': ['account opening', 'verification', 'documents', 'approval'],
        'trading': ['trading fees', 'first trade', 'margin', 'options'],
        'deposit': ['fund account', 'ACH transfer', 'wire transfer', 'money'],
        'withdraw': ['withdrawal', 'cash out', 'transfer'],
        'fee': ['trading fees', 'commissions', 'costs'],
        'document': ['verification', 'identity', 'tax forms'],
        'money': ['deposit', 'withdraw', 'funding', 'transfer']
    }
    
    # Find related suggestions
    suggestions = []
    for key, values in suggestion_map.items():
        if key in keyword_lower or keyword_lower in key:
            suggestions.extend(values)
    
    # Add general suggestions if no specific matches
    if not suggestions:
        suggestions = ['account', 'trading', 'fees', 'tax', 'deposit', 'withdraw']
    
    return list(set(suggestions))  # Remove duplicates

def get_quick_questions_by_keyword(keyword: str) -> list[str]:
    """
    SIMPLE and RELIABLE search for quick questions
    """
    try:
        print(f"\n🔍 === SIMPLE SEARCH FOR: '{keyword}' ===")
        
        from optimized_faq_system import LLMPoweredOptimizedFAQSystem
        faq_system = LLMPoweredOptimizedFAQSystem()
        
        # Get documents from vectorstore
        docs_with_scores = faq_system.vectorstore.similarity_search_with_score(
            keyword, 
            k=50
        )
        
        print(f"📊 Got {len(docs_with_scores)} documents from vectorstore")
        
        found_questions = []
        seen_questions = set()
        keyword_lower = keyword.lower()
        
        print(f"🔍 Looking for keyword '{keyword_lower}' in documents...")
        
        for i, (doc, score) in enumerate(docs_with_scores):
            question = doc.metadata.get("question", "")
            category = doc.metadata.get("category_name", "")
            
            if not question or question in seen_questions:
                continue
                
            # SIMPLE matching - just check if keyword is anywhere
            question_lower = question.lower()
            category_lower = category.lower() if category else ""
            
            # Check multiple places for the keyword
            keyword_found = (
                keyword_lower in question_lower or
                keyword_lower in category_lower or
                # Special mappings for common searches
                (keyword_lower == "tax" and ("tax" in question_lower or "tax" in category_lower)) or
                (keyword_lower == "account" and ("account" in question_lower or "account" in category_lower)) or
                (keyword_lower == "trading" and ("trading" in question_lower or "fees" in question_lower)) or
                (keyword_lower == "deposit" and ("deposit" in question_lower or "fund" in question_lower))
            )
            
            if keyword_found:
                print(f"   ✅ FOUND: {question}")
                print(f"      Category: {category}")
                print(f"      Match in: {'question' if keyword_lower in question_lower else 'category'}")
                
                found_questions.append(question)
                seen_questions.add(question)
                
                # Stop at 3 results as requested
                if len(found_questions) >= 3:
                    break
        
        print(f"\n✅ FINAL RESULTS: {len(found_questions)} questions found")
        for i, q in enumerate(found_questions, 1):
            print(f"   {i}. {q}")
        
        print("=== END SIMPLE SEARCH ===\n")
        
        return found_questions
        
    except Exception as e:
        print(f"❌ Error in simple search: {e}")
        import traceback
        traceback.print_exc()
        return []

def get_related_terms(keyword: str) -> list[str]:
    """
    Enhanced related terms for better matching
    """
    related_terms = {
        'tax': ['taxes', '1099', 'taxation', 'tax form', 'tax document', 'tax reporting', 
                'irs', 'filing', 'tax year', 'tax return', 'statement', 'turbotax', 
                'consolidated', 'reportable', 'tax event'],
        'account': ['accounts', 'registration', 'sign up', 'open', 'opening', 'statements'],
        'trading': ['trade', 'trades', 'buy', 'sell', 'trading', 'transaction'],
        'deposit': ['deposits', 'fund', 'funding', 'money', 'transfer', 'cash'],
        'withdraw': ['withdrawal', 'withdrawals', 'cash out', 'wire'],
        'margin': ['leverage', 'buying power', 'margin account'],
        'options': ['option', 'call', 'put', 'derivatives'],
        'fee': ['fees', 'commission', 'commissions', 'cost', 'costs', 'pricing'],
        'verify': ['verification', 'identity', 'documents', 'document', 'forms'],
        'statement': ['statements', 'account statement', 'monthly', 'quarterly']
    }
    
    return related_terms.get(keyword, [])

def should_use_market_agent(query: str) -> bool:
    """
    ENHANCED: Better detection for market overview and real-time queries
    """
    query_lower = query.lower().strip()
    
    # HIGH PRIORITY: Real-time market queries (THESE SHOULD ALWAYS USE MARKET AGENT)
    high_priority_market_keywords = [
        # Market overview queries
        'current market overview', 'market overview', 'today\'s market', 'market today',
        'market status', 'market summary', 'market update', 'market report',
        'how is the market', 'what\'s the market doing', 'market performance today',
        
        # Real-time data requests  
        'current price', 'stock price', 'share price', 'latest price', 'live price',
        'real time price', 'today\'s price', 'price today', 'current quote',
        
        # Market indices
        'dow jones', 's&p 500', 'sp500', 'nasdaq', 'russell 2000', 'market indices',
        'how are the indices', 'index performance', 'market index',
        
        # Trending/current market analysis
        'market trends', 'market analysis today', 'stock market trends',
        'what\'s trending', 'market direction', 'bull market', 'bear market'
    ]
    
    # Company-specific stock queries
    company_stock_keywords = [
        'stock information', 'stock info', 'stock data', 'stock performance',
        'stock analysis', 'stock overview', 'share information', 'share price',
        'company stock', 'stock quote', 'ticker', 'market cap'
    ]
    
    # News and events that affect markets
    market_news_keywords = [
        'stock news', 'market news', 'financial news', 'earnings',
        'analyst rating', 'price target', 'market movers', 'gainers', 'losers'
    ]
    
    # Company names (expanded list)
    major_companies = [
        'apple', 'microsoft', 'google', 'alphabet', 'amazon', 'tesla', 
        'nvidia', 'meta', 'facebook', 'netflix', 'adobe', 'oracle',
        'salesforce', 'intel', 'amd', 'uber', 'lyft', 'airbnb',
        'zoom', 'spotify', 'twitter', 'snapchat', 'walmart', 'target',
        'coca cola', 'pepsi', 'starbucks', 'nike', 'boeing'
    ]
    
    # Stock ticker patterns (2-5 uppercase letters)
    import re
    ticker_pattern = r'\b[A-Z]{2,5}\b'
    
    print(f"🔍 MARKET AGENT ROUTING CHECK: '{query}'")
    
    # PRIORITY 1: High priority market keywords (most important)
    for keyword in high_priority_market_keywords:
        if keyword in query_lower:
            print(f"✅ HIGH PRIORITY MATCH: '{keyword}' → MARKET AGENT")
            return True
    
    # PRIORITY 2: Company + stock context
    for company in major_companies:
        if company in query_lower:
            # Check for stock-related context
            stock_context = ['stock', 'price', 'share', 'quote', 'trading', 'market', 'information', 'info', 'data']
            for context in stock_context:
                if context in query_lower:
                    print(f"✅ COMPANY + CONTEXT: '{company}' + '{context}' → MARKET AGENT")
                    return True
            
            # Check for question phrases about companies
            question_phrases = ['what about', 'tell me about', 'how is', 'what\'s', 'give me info', 'information about']
            for phrase in question_phrases:
                if phrase in query_lower:
                    print(f"✅ COMPANY + QUESTION: '{company}' + '{phrase}' → MARKET AGENT")
                    return True
    
    # PRIORITY 3: Stock-specific keywords
    for keyword in company_stock_keywords:
        if keyword in query_lower:
            print(f"✅ STOCK KEYWORD: '{keyword}' → MARKET AGENT")
            return True
    
    # PRIORITY 4: Market news keywords
    for keyword in market_news_keywords:
        if keyword in query_lower:
            print(f"✅ MARKET NEWS: '{keyword}' → MARKET AGENT")
            return True
    
    # PRIORITY 5: Ticker symbol pattern
    if re.search(ticker_pattern, query):
        print(f"✅ TICKER PATTERN FOUND → MARKET AGENT")
        return True
    
    # PRIORITY 6: Investment/financial keywords
    financial_keywords = [
        'invest in', 'investment', 'portfolio', 'buy stock', 'sell stock',
        'financial analysis', 'valuation', 'pe ratio', 'dividend', 'earnings'
    ]
    
    for keyword in financial_keywords:
        if keyword in query_lower:
            print(f"✅ FINANCIAL KEYWORD: '{keyword}' → MARKET AGENT")
            return True
    
    print(f"❌ NO MARKET INDICATORS → FAQ SYSTEM")
    return False

# ============================================================================
# CORE ROUTES - ESSENTIAL FOR FUNCTIONALITY
# ============================================================================

@app.route('/')
def home():
    """API status endpoint (no template serving)"""
    return jsonify({
        'message': 'Tiger Securities Enhanced LLM-Powered FAQ API',
        'status': 'active',
        'version': '4.1',
        'frontend': 'React (separate application)',
        'backend': 'Flask API',
        'endpoints': {
            'main_faq': '/api/ask',
            'quick_questions': '/api/quick-questions',
            'stats': '/api/stats',
            'health': '/health',
            'docs': '/docs/'
        }
    })

# Serve static files (like logo) for React frontend
@app.route('/static/<path:filename>')
def serve_static(filename):
    """Serve static files for React frontend"""
    return send_from_directory('static', filename)

@app.route('/health')
def health_check():
    """Health check with system status"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'message': 'Tiger Securities Enhanced FAQ App is running',
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
    """
    COMPLETE: Enhanced ask endpoint with Market Agent, Memory System, and FAQ System
    """
    try:
        data = request.get_json()
        if not data or 'question' not in data:
            return jsonify({'error': 'No question provided'}), 400
        
        user_question = data['question'].strip()
        if not user_question:
            return jsonify({'error': 'Empty question'}), 400
        
        print(f"\n🔍 === PROCESSING QUESTION ===")
        print(f"📝 Question: '{user_question}'")

        # STEP 1: Check if question should use market agent (HIGHEST PRIORITY)
        use_market_agent_flag = should_use_market_agent(user_question)
        print(f"🎯 Market agent routing: {use_market_agent_flag}")
        
        if use_market_agent_flag and faq_market_agent:
            print(f"✅ ROUTING TO: FAQ Market Agent")
            print(f"🚀 === MARKET AGENT PROCESSING ===")
            
            try:
                # Use the market agent
                market_result = faq_market_agent.ask_question(user_question)
                print(f"📤 Market agent response: {market_result.get('success', False)}")
                
                if market_result['success']:
                    print(f"✅ Market agent SUCCESS - storing messages")
                    
                    # Store the conversation in your database
                    session_id, user_id = get_or_create_session()
                    
                    # Store user question
                    store_message(session_id, user_question, 'human')
                    
                    # Store agent response
                    store_message(session_id, market_result['response'], 'ai')
                    
                    # Enhanced source attribution for market agent
                    sources = []
                    tools_used = market_result.get('tools_available', [])
                    response_text = str(market_result.get('response', ''))
                    
                    print(f"🔧 Tools available: {tools_used}")
                    print(f"📝 Response preview: {response_text[:100]}...")
                    
                    # Determine sources based on response content and tools
                    if any(tool in str(tools_used) for tool in ['get_stock_quote', 'stock']):
                        sources.append('Yahoo Finance (Real-time Stock Data)')
                        print(f"📈 Added Yahoo Finance source")
                    
                    if any(tool in str(tools_used) for tool in ['search_web', 'web']):
                        sources.append('Web Search Results')
                        print(f"🌐 Added Web Search source")
                    
                    if any(tool in str(tools_used) for tool in ['get_market_overview', 'market']):
                        sources.append('Market Data Provider')
                        print(f"📊 Added Market Data Provider source")
                    
                    if any(tool in str(tools_used) for tool in ['faq_search', 'faq']):
                        sources.append('Tiger Securities FAQ Database')
                        print(f"📋 Added FAQ Database source")
                    
                    # Always include market agent as a source if no specific tools detected
                    if not sources:
                        sources.append('LLM Market Intelligence')
                        print(f"🤖 Added LLM Market Intelligence source")
                        
                    # Add market data disclaimer
                    sources.append('⚠️ Market data may be delayed')
                    
                    print(f"📚 Final sources: {sources}")
                    
                    response_data = {
                        'success': True,
                        'response': market_result['response'],
                        'system_used': 'faq_market_agent',
                        'capabilities': market_result.get('capabilities', 'Market Data & FAQ Analysis'),
                        'sources': sources,
                        'sources_count': len(sources),
                        'tools_used': tools_used,
                        'conversation_length': market_result.get('conversation_length', 0),
                        'session_id': session_id,
                        'processing_time': market_result.get('processing_time', 0),
                        'categories': ['market_data', 'real_time'],
                        'suggested_questions': [
                            "What's the current market overview?",
                            "How do I place a stock trade?", 
                            "What are trading fees?",
                            "Can I get real-time quotes?",
                            "Show me other stock prices"
                        ]
                    }
                    
                    print(f"✅ MARKET AGENT SUCCESS - Response ready")
                    print(f"📊 Response data keys: {list(response_data.keys())}")
                    return jsonify(response_data)
                    
                else:
                    print(f"❌ Market agent FAILED: {market_result.get('error', 'Unknown error')}")
                    print(f"🔄 Falling back to FAQ system")
                    use_market_agent_flag = False
                    
            except Exception as market_error:
                print(f"💥 MARKET AGENT ERROR: {market_error}")
                print(f"🔄 Falling back to FAQ system")
                use_market_agent_flag = False
        
        elif use_market_agent_flag and not faq_market_agent:
            print(f"⚠️ Market agent routing triggered but faq_market_agent is None")
            print(f"🔄 Falling back to FAQ system")
            use_market_agent_flag = False
        
        # STEP 2: Check if it's a memory question (SECOND PRIORITY)
        if not use_market_agent_flag:
            print(f"🧠 === MEMORY & FAQ SYSTEM ROUTING ===")
            
            # Get session info first
            session_id, user_id = get_or_create_session()
            print(f"💾 Session: {session_id}, User: {user_id}")
            
            # CRITICAL: Detect memory questions
            memory_indicators = [
                'what did i just ask', 'what did i ask', 'what was my question',
                'how many questions', 'question count', 'how many have i asked',
                'what was my first question', 'what was my last question',
                'previous question', 'last question', 'first question',
                'what have we discussed', 'what did we discuss', 'conversation summary',
                'what have we talked about', 'what topics have we covered',
                'summarize our conversation', 'what was my previous question'
            ]
            
            question_lower = user_question.lower().strip()
            is_memory_question = any(indicator in question_lower for indicator in memory_indicators)
            
            print(f"🧠 Memory question detection: {is_memory_question}")
            if is_memory_question:
                print(f"✅ DETECTED MEMORY QUESTION: '{user_question}'")
                for indicator in memory_indicators:
                    if indicator in question_lower:
                        print(f"   🎯 Matched indicator: '{indicator}'")
                        break
            
            # STEP 3: Route to Memory System (supabase_faq_system)
            if is_memory_question and supabase_faq_system:
                print(f"🧠 === SUPABASE MEMORY SYSTEM PROCESSING ===")
                print(f"🔧 Using OptimalChatbotFAQ with memory analysis")
                
                try:
                    # Use the Supabase memory system (OptimalChatbotFAQ)
                    memory_result = supabase_faq_system.ask_question(
                        question=user_question,
                        user_id=user_id,
                        session_id=session_id
                    )
                    
                    print(f"📤 Memory system result: {memory_result.get('success', False)}")
                    print(f"🧠 Intent: {memory_result.get('intent', 'unknown')}")
                    print(f"📝 Response preview: {str(memory_result.get('response', ''))[:100]}...")
                    
                    if memory_result['success']:
                        # Enhanced response for memory questions
                        response_data = {
                            'success': True,
                            'response': memory_result['response'],
                            'system_used': 'supabase_memory_system',  # Clear identification
                            'capabilities': 'Memory Analysis & Conversation History',
                            'sources': ['Conversation History', 'Session Memory'],
                            'sources_count': 2,
                            'suggested_questions': memory_result.get('suggested_questions', [
                                "What was my first question?",
                                "How many questions have I asked?",
                                "What have we discussed?",
                                "What was my previous question?"
                            ]),
                            'processing_time': memory_result.get('processing_time', 0),
                            'session_id': session_id,
                            'categories': ['memory_analysis', 'conversation_history'],
                            'memory_enabled': True,
                            'intent': memory_result.get('intent', 'memory_question'),
                            'conversation_history_used': memory_result.get('conversation_history_used', True),
                            'enhanced_with_context': memory_result.get('enhanced_with_context', True)
                        }
                        
                        print(f"✅ MEMORY SYSTEM SUCCESS - Response ready")
                        print(f"📊 Memory response data keys: {list(response_data.keys())}")
                        return jsonify(response_data)
                    else:
                        print(f"❌ Memory system failed: {memory_result.get('error', 'Unknown error')}")
                        print(f"🔄 Falling back to regular FAQ system")
                        
                except Exception as memory_error:
                    print(f"💥 MEMORY SYSTEM ERROR: {memory_error}")
                    import traceback
                    traceback.print_exc()
                    print(f"🔄 Falling back to regular FAQ system")
            
            elif is_memory_question and not supabase_faq_system:
                print(f"⚠️ Memory question detected but supabase_faq_system is None")
                print(f"🔄 Processing as regular FAQ")
            
            # STEP 4: Regular FAQ System Processing (LOWEST PRIORITY)
            print(f"📋 === REGULAR FAQ SYSTEM PROCESSING ===")
            
            # Get conversation history for context
            conversation_history = get_conversation_history(session_id)
            print(f"📚 Conversation history: {len(conversation_history)} messages")
            
            # Use your existing FAQ system logic
            print(f"🔍 Processing with enhanced LLM system")
            result = llm_powered_faq_system.get_smart_response(user_question, conversation_history)
            
            print(f"📤 FAQ system response received")
            print(f"📝 Response preview: {str(result.get('response', ''))[:100]}...")
            
            # Store messages
            store_message(session_id, user_question, 'human', user_id)
            store_message(session_id, result['response'], 'ai', user_id)
            
            # Enhanced source attribution for FAQ system
            sources = result.get('sources', [])
            
            # Add appropriate sources based on system used
            if result.get('llm_knowledge_used'):
                if not any('AI Assistant' in str(s) for s in sources):
                    sources.append('AI Assistant Knowledge')
                    print(f"🤖 Added AI Assistant source")
            
            if result.get('num_sources', 0) > 0:
                if not any('FAQ' in str(s) for s in sources):
                    sources.append('Tiger Securities FAQ Database')
                    print(f"📋 Added FAQ Database source")
            
            # Ensure we always have some source attribution
            if not sources:
                sources = ['Tiger Securities Knowledge Base']
                print(f"📖 Added default Knowledge Base source")
            
            print(f"📚 Final FAQ sources: {sources}")
            
            # Prepare response data
            response_data = {
                'success': True,
                'response': result['response'],
                'system_used': 'enhanced_llm_faq_system',
                'capabilities': 'FAQ Search & LLM Intelligence',
                'sources': sources,
                'sources_count': len(sources),
                'num_sources': result.get('num_sources', 0),
                'suggested_questions': result.get('suggested_questions', []),
                'processing_time': result.get('processing_time', 0),
                'session_id': session_id,
                'source_attribution': result.get('source_attribution', 'AI Assistant'),
                'categories': result.get('categories_used', ['general']),
                'llm_knowledge_used': result.get('llm_knowledge_used', False)
            }
        
            # Convert numpy types to JSON-serializable types
            response_data = convert_numpy_types(response_data)
            
            print(f"✅ FAQ SYSTEM SUCCESS - Response ready")
            print(f"📊 Response data keys: {list(response_data.keys())}")
            return jsonify(response_data)
            
    except Exception as e:
        print(f"💥 CRITICAL ERROR in /api/ask: {str(e)}")
        import traceback
        traceback.print_exc()
        
        logger.error(f"Error processing question: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Processing error: {str(e)}',
            'sources': ['Error Handler'],
            'sources_count': 1,
            'fallback_response': 'I apologize for the technical difficulty. Please try rephrasing your question.'
        }), 500
    
@app.route('/api/test-market-agent', methods=['POST'])
def test_market_agent():
    """
    Test endpoint specifically for market agent
    """
    try:
        if not faq_market_agent:  # FIXED: was 'market_agent'
            return jsonify({
                'success': False,
                'error': 'Market agent not available'
            }), 503
        
        data = request.get_json()
        question = data.get('question', '').strip()
        
        if not question:
            return jsonify({'error': 'No question provided'}), 400
        
        result = faq_market_agent.ask_question(question)  # FIXED: was 'market_agent'
        
        return jsonify({
            'success': result['success'],
            'response': result.get('response', ''),
            'agent_type': result.get('agent_type', ''),
            'error': result.get('error', ''),
            'capabilities': result.get('capabilities', [])
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/market-agent-stats', methods=['GET'])
def get_market_agent_stats():
    """
    Get market agent statistics and capabilities
    """
    try:
        if faq_market_agent: 
            stats = faq_market_agent.get_faq_system_stats()
            return jsonify({
                'success': True,
                'market_agent_available': True,
                'stats': stats,
                'capabilities': [
                    'Tiger Securities FAQ search with LLM intelligence',
                    'Real-time stock quotes and prices', 
                    'Market overview and major indices',
                    'Stock news and company information',
                    'Company name to ticker symbol lookup',
                    'Conversation memory and context'
                ]
            })
        else:
            return jsonify({
                'success': False,
                'market_agent_available': False,
                'error': 'Market agent not initialized'
            })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    
@app.route('/api/market-agent-status')
def check_market_agent_status():
    """Quick check of market agent availability and functionality"""
    
    status = {
        'faq_market_agent_available': faq_market_agent is not None,
        'can_process_questions': False,
        'last_test_result': None,
        'error': None
    }
    
    if faq_market_agent:
        try:
            # Quick test
            test_result = faq_market_agent.ask_question("Test market agent")
            status['can_process_questions'] = test_result.get('success', False)
            status['last_test_result'] = test_result.get('success', False)
        except Exception as e:
            status['error'] = str(e)
    
    return jsonify(status)

@app.route('/api/debug-routing')
def debug_routing():
    """Enhanced debug endpoint to test specific queries"""
    
    test_queries = [
        "What's the current market overview?",
        "current market overview", 
        "How is the market today?",
        "Apple stock information",
        "Tell me about Tesla",
        "What about Microsoft stock?",
        "How do I open an account?",  # Should be FAQ
        "AAPL price",
        "market status",
        "S&P 500 performance"
    ]
    
    results = []
    
    for query in test_queries:
        should_use_market = should_use_market_agent(query)
        results.append({
            'query': query,
            'should_use_market_agent': should_use_market,
            'expected_agent': 'market_agent' if should_use_market else 'faq_system'
        })
    
    return jsonify({
        'test_results': results,
        'summary': f"Tested {len(test_queries)} queries",
        'market_queries': sum(1 for r in results if r['should_use_market_agent']),
        'faq_queries': sum(1 for r in results if not r['should_use_market_agent'])
    })

@app.route('/api/test-specific-query')
def test_specific_query():
    """Test the exact query the user asked about"""
    
    query = "What's the current market overview?"
    
    should_use_market = should_use_market_agent(query)
    
    return jsonify({
        'query': query,
        'should_use_market_agent': should_use_market,
        'expected_response': 'Real-time market data from Market Agent' if should_use_market else 'Generic info from FAQ System',
        'debug_info': {
            'query_lowercase': query.lower(),
            'contains_market_overview': 'market overview' in query.lower(),
            'contains_current': 'current' in query.lower(),
            'routing_decision': 'MARKET AGENT' if should_use_market else 'FAQ SYSTEM'
        }
    })

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

@app.route('/api/quick-questions', methods=['GET'])
def get_quick_questions():
    """
    Get quick questions - sample questions by default, database search with keyword
    """
    try:
        keyword = request.args.get('keyword', '').strip()
        
        if keyword:
            print(f"🔍 Database search for: '{keyword}'")
            # Search the database for relevant questions
            questions = get_quick_questions_by_keyword(keyword)
            
            if questions:
                return jsonify({
                    'success': True,
                    'questions': questions,
                    'keyword': keyword,
                    'count': len(questions),
                    'message': f"Found {len(questions)} relevant questions"
                })
            else:
                return jsonify({
                    'success': True,
                    'questions': [],
                    'keyword': keyword,
                    'count': 0,
                    'message': f"No questions found for '{keyword}'. Try: tax, account, trading, fees"
                })
        else:
            # Return sample questions (not from database)
            sample_questions = [
                "How do I open a Tiger Securities account?",
                "What documents do I need to verify my identity?",
                "What are the trading fees and commissions?",
                "How do I deposit money into my account?",
                "What are the different account types available?",
                "How long does account approval take?"
            ]
            
            return jsonify({
                'success': True,
                'questions': sample_questions,
                'keyword': None,
                'count': len(sample_questions),
                'message': "Sample quick questions"
            })
            
    except Exception as e:
        print(f"❌ Error in get_quick_questions: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'questions': [],
            'message': "Error retrieving quick questions"
        }), 500

@app.route('/api/debug-vectorstore', methods=['GET'])
def debug_vectorstore():
    """Debug endpoint to check what's in the vectorstore"""
    try:
        from optimized_faq_system import LLMPoweredOptimizedFAQSystem
        faq_system = LLMPoweredOptimizedFAQSystem()
        
        # Get some sample documents
        sample_docs = faq_system.vectorstore.similarity_search("tax", k=20)
        
        result = {
            'total_docs_found': len(sample_docs),
            'sample_docs': []
        }
        
        for i, doc in enumerate(sample_docs[:10]):
            result['sample_docs'].append({
                'index': i,
                'question': doc.metadata.get("question", "No question"),
                'category': doc.metadata.get("category_name", "No category"),
                'content_preview': doc.page_content[:100] + "..."
            })
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'message': 'Failed to debug vectorstore'
        }), 500

@app.route('/api/test-search/<keyword>')
def test_search(keyword):
    """Test the search function directly"""
    try:
        print(f"🧪 Testing search for: {keyword}")
        results = get_quick_questions_by_keyword(keyword)
        
        return jsonify({
            'success': True,
            'keyword': keyword,
            'results': results,
            'count': len(results),
            'message': f"Direct search test for '{keyword}'"
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'keyword': keyword,
            'error': str(e),
            'results': []
        }), 500
    
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
            {"question": "How do I open a Tiger Securities account?", "category": "Account", "keywords": ["account", "open", "new", "start"], "answer": "To open a Tiger Securities account, visit our website and click 'Sign Up'. You'll need to provide personal information and verify your identity."},
            {"question": "What documents do I need to get started?", "category": "Account", "keywords": ["documents", "required", "verification", "id"], "answer": "You need a government-issued ID, Social Security number, and proof of address to get started."},
            {"question": "What are the trading fees and commissions?", "category": "Fees", "keywords": ["fees", "commission", "cost", "price"], "answer": "Tiger Securities offers commission-free stock trading. Some premium features may have fees."},
            {"question": "How do I fund my trading account?", "category": "Funding", "keywords": ["fund", "deposit", "money", "transfer"], "answer": "You can fund your account via ACH transfer, wire transfer, or mobile check deposit."},
            {"question": "How do I withdraw money from my account?", "category": "Funding", "keywords": ["withdraw", "withdrawal", "money", "cash"], "answer": "Withdrawals can be made through ACH transfer to your linked bank account, usually taking 1-3 business days."},
            {"question": "How do I place my first trade?", "category": "Trading", "keywords": ["trade", "first", "buy", "sell"], "answer": "To place your first trade, search for a stock, select the number of shares, choose your order type, and confirm the trade."},
            {"question": "What are the margin requirements?", "category": "Trading", "keywords": ["margin", "requirements", "leverage"], "answer": "Margin trading requires a minimum account balance of $2,000 and approval for margin privileges."},
            {"question": "Can I trade during extended hours?", "category": "Trading", "keywords": ["extended", "hours", "after", "pre"], "answer": "Yes, Tiger Securities offers extended hours trading from 4:00 AM to 8:00 PM ET."},
            {"question": "What is a cash account?", "category": "Account", "keywords": ["cash", "account", "type"], "answer": "A cash account requires you to pay for securities purchases in full and doesn't allow borrowing."},
            {"question": "What is a margin account?", "category": "Account", "keywords": ["margin", "account", "borrowing"], "answer": "A margin account allows you to borrow money from Tiger Securities to purchase securities."},
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

@app.route('/api/test-memory-routing', methods=['POST'])
def test_memory_routing():
    """Test memory question routing specifically"""
    try:
        data = request.get_json()
        question = data.get('question', 'What did I just ask?')
        
        # Test memory detection
        memory_indicators = [
            'what did i just ask', 'what did i ask', 'what was my question',
            'how many questions', 'question count', 'how many have i asked',
            'what was my first question', 'what was my last question',
            'previous question', 'last question', 'first question',
            'what have we discussed', 'what did we discuss', 'conversation summary'
        ]
        
        question_lower = question.lower().strip()
        is_memory_question = any(indicator in question_lower for indicator in memory_indicators)
        
        matched_indicators = [indicator for indicator in memory_indicators if indicator in question_lower]
        
        return jsonify({
            'success': True,
            'question': question,
            'question_lower': question_lower,
            'is_memory_question': is_memory_question,
            'matched_indicators': matched_indicators,
            'supabase_faq_system_available': supabase_faq_system is not None,
            'memory_enabled': supabase_faq_system.memory_enabled if supabase_faq_system else False,
            'routing_decision': 'memory_system' if is_memory_question and supabase_faq_system else 'faq_system'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/system-status')
def system_status():
    """Get status of all available systems"""
    return jsonify({
        'market_agent': {
            'available': faq_market_agent is not None,
            'type': 'FAQMarketAgent'
        },
        'memory_system': {
            'available': supabase_faq_system is not None,
            'memory_enabled': supabase_faq_system.memory_enabled if supabase_faq_system else False,
            'type': 'OptimalChatbotFAQ'
        },
        'faq_system': {
            'available': llm_powered_faq_system is not None,
            'type': 'LLMPoweredOptimizedFAQSystem'
        }
    })

@app.route('/ws')
def websocket_endpoint():
    """Handle React development server WebSocket requests properly"""
    # Check if it's a WebSocket upgrade request
    if request.headers.get('Upgrade', '').lower() == 'websocket':
        # This is a WebSocket upgrade request - we can't handle it properly
        # Return a 501 Not Implemented instead of 400
        return jsonify({
            'error': 'WebSocket not implemented',
            'message': 'This endpoint does not support WebSocket connections'
        }), 501
    
    # Regular HTTP request to /ws
    return jsonify({
        'message': 'WebSocket endpoint - React development feature',
        'status': 'http_only',
        'note': 'WebSocket upgrades not supported'
    }), 200


# Add this logging filter to completely hide WebSocket noise
import logging

class CleanLoggingFilter(logging.Filter):
    def filter(self, record):
        message = record.getMessage()
        # Filter out WebSocket and other development noise
        if any(pattern in message for pattern in ['/ws', 'WebSocket', 'websocket']):
            return False
        return True

# Apply clean logging
werkzeug_logger = logging.getLogger('werkzeug')
werkzeug_logger.addFilter(CleanLoggingFilter())
werkzeug_logger.setLevel(logging.WARNING)  # Only show warnings and errors


# ============================================================================
# SWAGGER API DOCUMENTATION
# ============================================================================

api = Api(app, doc='/docs/', title='Tiger Securities Enhanced LLM FAQ API', 
         description='''
## Tiger Securities Enhanced FAQ System with Advanced LLM Intelligence

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
    'question': fields.String(required=True, description='Customer question', example='How do I open a Tiger Securities account?'),
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
    'answer_preview': fields.String(description='Preview of the answer provided', example='To open a Tiger Securities account...'),
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
        <title>Tiger Securities FAQ API Tester</title>
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
        <h1>Tiger Securities FAQ API Tester</h1>
        <div class="nav">
            <a href="/docs/">📚 API Documentation</a> | 
            <a href="/">🏠 Main App</a> | 
            <a href="/health">💓 Health Check</a>
        </div>
        
        <div class="endpoint">
            <h3>🤖 POST /api/ask - Enhanced LLM FAQ</h3>
            <p>Ask questions with advanced LLM intelligence and conversation memory.</p>
            <input type="text" id="question" placeholder="Enter your question" value="What's Apple stock price?">
            <button onclick="askQuestion()">Ask Question</button>
            <div id="askResponse" class="response" style="display:none;"></div>
        </div>
        
        <div class="endpoint">
            <h3>📈 POST /api/test-market-agent - Test Market Agent</h3>
            <p>Test the market agent specifically for stock questions.</p>
            <input type="text" id="marketQuestion" placeholder="Enter market question" value="What's Tesla stock price?">
            <button onclick="testMarketAgent()">Test Market Agent</button>
            <div id="marketResponse" class="response" style="display:none;"></div>
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
            
            async function testMarketAgent() {
                const question = document.getElementById('marketQuestion').value;
                const responseDiv = document.getElementById('marketResponse');
                responseDiv.style.display = 'block';
                responseDiv.innerHTML = '<p>📈 Testing market agent...</p>';
                
                try {
                    const response = await fetch('/api/test-market-agent', {
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
    print("Starting Tiger Securities Enhanced LLM-Powered FAQ App...")
    
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
        
        print(f"\n📡 API endpoints available at:")
        print(f"   💓 Health: http://localhost:8000/health")
        print(f"   📚 API Documentation: http://localhost:8000/docs/")
        print(f"   🤖 FAQ API: http://localhost:8000/api/ask")
        print(f"   📈 Market Agent Test: http://localhost:8000/api/test-market-agent")
        print(f"   📊 Stats: http://localhost:8000/api/stats")
        print(f"   👍 Feedback: http://localhost:8000/api/feedback")
        print(f"   🧪 Test Page: http://localhost:8000/test")
        
        print(f"\n🎨 React Frontend should run on: http://localhost:3000")
        print(f"   (Start with: cd frontend && npm start)")
        
        # Show system status
        print(f"\n🔧 System Status:")
        print(f"   ✅ LLM FAQ System: {'Loaded' if enhanced_llm_loaded else 'Not available'}")
        print(f"   📈 Market Agent: {'Loaded' if market_loaded else 'Not available'}")
        print(f"   💾 Supabase Memory: {'Loaded' if supabase_loaded else 'Not available'}")
        
        app.run(debug=True, host='0.0.0.0', port=8000)
    else:
        print("❌ Failed to start: No systems available")