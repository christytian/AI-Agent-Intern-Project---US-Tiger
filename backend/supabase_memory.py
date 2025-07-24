import os
import json
import re
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from uuid import uuid4
import logging
from dotenv import load_dotenv

from supabase import create_client, Client
from postgrest.exceptions import APIError
from langchain_openai import ChatOpenAI

# Import your UPDATED LLM-powered FAQ system
from optimized_faq_system import LLMPoweredOptimizedFAQSystem

@dataclass
class ChatMessage:
    """Message structure for Supabase"""
    id: str
    session_id: str
    user_id: str
    message_type: str
    content: str
    intent: Optional[str] = None
    sources: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: Optional[str] = None

class ConversationAnalyzer:
    """Uses LLM to analyze conversations instead of hard-coded patterns"""
    
    def __init__(self, openai_api_key: str = None):
        """Initialize the LLM-powered conversation analyzer"""
        self.openai_api_key = openai_api_key or os.getenv('OPENAI_API_KEY')
        
        if not self.openai_api_key:
            raise ValueError("OpenAI API key required for conversation analysis")
        
        # Initialize LLM for conversation analysis
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.1,
            openai_api_key=self.openai_api_key
        )
        
        # Cache for conversation analysis to avoid repeated LLM calls
        self.analysis_cache = {}
    
    def analyze_conversation_intent(self, question: str, conversation_history: List[ChatMessage] = None) -> Dict[str, Any]:
        """
        Use LLM to analyze conversation intent and determine how to handle the question
        FIXED: Better memory question detection and routing
        """
        # Create cache key
        cache_key = f"{question}:{len(conversation_history) if conversation_history else 0}"
        if cache_key in self.analysis_cache:
            return self.analysis_cache[cache_key]
        
        # Build conversation context
        context = ""
        if conversation_history:
            recent_messages = conversation_history[-6:]  # Last 6 messages for context
            context_parts = []
            for msg in recent_messages:
                context_parts.append(f"{msg.message_type.title()}: {msg.content}")
            context = "\n".join(context_parts)
        
        # CRITICAL: Force-check for obvious memory questions first
        question_lower = question.lower()
        memory_indicators = [
            'how many questions', 'how many have i asked', 'question count',
            'what was my first question', 'what was my last question', 
            'what did i just ask', 'what did i ask', 'previous question',
            'first question', 'last question', 'what have we discussed'
        ]
        
        is_obvious_memory_question = any(indicator in question_lower for indicator in memory_indicators)
        
        # Create analysis prompt with BETTER memory question detection
        analysis_prompt = f"""You are an expert conversation analyzer for TradeUP's customer service system.

Analyze this customer message and determine how it should be handled:

Current Message: "{question}"

Conversation History:
{context if context else "No previous conversation"}

CRITICAL ROUTING RULES:
- Questions about "how many questions", "question count", "first question", "last question" → MUST use memory_analysis
- Questions about conversation history, what was discussed → MUST use memory_analysis  
- Questions about TradeUP services, fees, accounts → use faq_system
- Simple greetings → use simple_response

Provide analysis in this exact JSON format:
{{
    "message_type": "greeting" | "faq_question" | "memory_question" | "conversational",
    "handling_strategy": "simple_response" | "faq_system" | "memory_analysis",
    "confidence": 0.0-1.0,
    "reasoning": "Brief explanation of your decision",
    "is_about_conversation": true | false,
    "needs_faq_lookup": true | false,
    "suggested_response_tone": "friendly" | "professional" | "helpful" | "informative",
    "conversation_reference": {{
        "references_previous": true | false,
        "ordinal_reference": null | "first" | "second" | "last" | "previous",
        "asks_for_summary": true | false,
        "asks_about_count": true | false
    }}
}}

MANDATORY ROUTING:
- "How many questions did I ask?" → memory_question + memory_analysis
- "What was my first question?" → memory_question + memory_analysis  
- "What did I just ask?" → memory_question + memory_analysis
- "What have we discussed?" → memory_question + memory_analysis"""

        try:
            # Use the LLM to analyze
            response = self.llm.invoke([
                {"role": "system", "content": "You are an expert conversation analyzer. Always respond with valid JSON only. Route memory questions to memory_analysis."},
                {"role": "user", "content": analysis_prompt}
            ])
            
            # Parse the response
            analysis_text = response.content.strip()
            if analysis_text.startswith('```json'):
                analysis_text = analysis_text.replace('```json', '').replace('```', '')
            
            analysis = json.loads(analysis_text)
            
            # FORCE CORRECTION for obvious memory questions - OVERRIDE LLM if wrong
            if is_obvious_memory_question:
                print(f"🔧 FORCE CORRECTING: Detected memory question: '{question_lower}'")
                analysis['message_type'] = 'memory_question'
                analysis['handling_strategy'] = 'memory_analysis'
                analysis['is_about_conversation'] = True
                analysis['reasoning'] = f"Force-corrected: Contains memory indicator in '{question_lower}'"
                
                # Set specific conversation reference based on question
                if 'how many' in question_lower or 'question count' in question_lower:
                    analysis['conversation_reference']['asks_about_count'] = True
                elif 'first question' in question_lower:
                    analysis['conversation_reference']['ordinal_reference'] = 'first'
                elif 'last question' in question_lower or 'just ask' in question_lower:
                    analysis['conversation_reference']['ordinal_reference'] = 'last'
            
            # Double-check: if it's identified as memory_question but not routed to memory_analysis, fix it
            if analysis.get('message_type') == 'memory_question' and analysis.get('handling_strategy') != 'memory_analysis':
                print(f"🔧 FIXING ROUTING: memory_question should use memory_analysis, not {analysis.get('handling_strategy')}")
                analysis['handling_strategy'] = 'memory_analysis'
            
            # Cache the result
            self.analysis_cache[cache_key] = analysis
            
            # Limit cache size
            if len(self.analysis_cache) > 500:
                keys_to_remove = list(self.analysis_cache.keys())[:100]
                for key in keys_to_remove:
                    del self.analysis_cache[key]
            
            return analysis
            
        except Exception as e:
            logging.warning(f"LLM conversation analysis failed: {e}, using fallback")
            
            # Enhanced fallback for memory questions
            if is_obvious_memory_question:
                return {
                    'message_type': 'memory_question',
                    'handling_strategy': 'memory_analysis',
                    'confidence': 0.8,
                    'reasoning': f'Fallback detected memory question: {question}',
                    'is_about_conversation': True,
                    'conversation_reference': {
                        'asks_about_count': 'how many' in question_lower,
                        'ordinal_reference': 'first' if 'first' in question_lower else 'last' if 'last' in question_lower or 'just ask' in question_lower else None
                    }
                }
            
            return self._fallback_analysis(question, conversation_history)
    
    def _fallback_analysis(self, question: str, conversation_history: List[ChatMessage] = None) -> Dict[str, Any]:
        """Fallback analysis if LLM fails"""
        question_lower = question.lower().strip()
        
        # Simple pattern matching as fallback
        if question_lower in ['hi', 'hello', 'hey', 'good morning', 'good afternoon']:
            return {
                "message_type": "greeting",
                "handling_strategy": "simple_response",
                "confidence": 0.9,
                "reasoning": "Simple greeting detected",
                "is_about_conversation": False,
                "needs_faq_lookup": False,
                "suggested_response_tone": "friendly",
                "conversation_reference": {
                    "references_previous": False,
                    "ordinal_reference": None,
                    "asks_for_summary": False,
                    "asks_about_count": False
                }
            }
        
        # Check for conversation references
        memory_keywords = ['previous', 'earlier', 'first', 'second', 'last', 'conversation', 'asked', 'discussed']
        if any(keyword in question_lower for keyword in memory_keywords):
            return {
                "message_type": "memory_question",
                "handling_strategy": "memory_analysis",
                "confidence": 0.7,
                "reasoning": "Contains conversation reference keywords",
                "is_about_conversation": True,
                "needs_faq_lookup": False,
                "suggested_response_tone": "helpful",
                "conversation_reference": {
                    "references_previous": True,
                    "ordinal_reference": "previous" if "previous" in question_lower else None,
                    "asks_for_summary": "discuss" in question_lower or "summary" in question_lower,
                    "asks_about_count": "how many" in question_lower
                }
            }
        
        # Default to FAQ question
        return {
            "message_type": "faq_question",
            "handling_strategy": "faq_system",
            "confidence": 0.6,
            "reasoning": "Default to FAQ processing",
            "is_about_conversation": False,
            "needs_faq_lookup": True,
            "suggested_response_tone": "informative",
            "conversation_reference": {
                "references_previous": False,
                "ordinal_reference": None,
                "asks_for_summary": False,
                "asks_about_count": False
            }
        }
    
    def generate_simple_response(self, question: str, analysis: Dict[str, Any]) -> str:
        """Generate simple responses for greetings and conversational elements"""
        tone = analysis.get('suggested_response_tone', 'friendly')
        
        response_prompt = f"""Generate a brief, {tone} response to this customer message: "{question}"

This is a {analysis.get('message_type', 'conversational')} message that needs a simple response.

Requirements:
- Be warm and welcoming for greetings
- Keep it brief (1-2 sentences)
- Mention TradeUP naturally
- End with offering help or asking what they need

Response:"""

        try:
            response = self.llm.invoke([
                {"role": "system", "content": f"You are TradeUP's {tone} customer service assistant. Be brief and helpful."},
                {"role": "user", "content": response_prompt}
            ])
            
            return response.content.strip()
            
        except Exception as e:
            logging.warning(f"Simple response generation failed: {e}")
            return self._fallback_simple_response(question, analysis)
    
    def _fallback_simple_response(self, question: str, analysis: Dict[str, Any]) -> str:
        """Fallback simple responses"""
        question_lower = question.lower().strip()
        
        if question_lower in ['hi', 'hello', 'hey']:
            return "Hello! How can I help you with your TradeUP questions today?"
        
        if 'good morning' in question_lower:
            return "Good morning! What can I help you with regarding TradeUP?"
        
        if question_lower in ['thanks', 'thank you']:
            return "You're welcome! Feel free to ask if you have any other TradeUP questions."
        
        if question_lower in ['ok', 'okay', 'cool', 'great']:
            return "Great! Is there anything else about TradeUP I can help you with?"
        
        return "I'm here to help with your TradeUP questions! What would you like to know?"

class OptimalChatbotFAQ:
    """Enhanced LLM-powered chatbot with intelligent conversation analysis"""
    
    def __init__(self, memory_window: int = 10):
        # Load environment
        env_path = "/Users/a16463/Desktop/Tiger_Securities/AI-Agent-Intern-Project---US-Tiger/notepad.env"
        if os.path.exists(env_path):
            load_dotenv(dotenv_path=env_path)
        
        # Initialize Supabase
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_ANON_KEY')
        
        if supabase_url and supabase_key:
            self.supabase = create_client(supabase_url, supabase_key)
            self.memory_enabled = True
            print("Supabase memory enabled")
        else:
            self.supabase = None
            self.memory_enabled = False
            print("Supabase memory disabled (no credentials)")
        
        # Initialize enhanced FAQ system
        try:
            self.faq_system = LLMPoweredOptimizedFAQSystem()
            print("Enhanced LLM FAQ system initialized")
        except Exception as e:
            print(f"Error initializing Enhanced LLM FAQ system: {e}")
            self.faq_system = None
        
        # Initialize enhanced conversation analyzer
        try:
            self.conversation_analyzer = ConversationAnalyzer()
            print("Enhanced conversation analyzer initialized")
        except Exception as e:
            print(f"Error initializing Enhanced conversation analyzer: {e}")
            self.conversation_analyzer = None
        
        self.memory_window = memory_window
        self.logger = logging.getLogger(__name__)
    
    def create_session(self, user_id: str, metadata: Dict[str, Any] = None) -> Optional[str]:
        """Create a new chat session"""
        if not self.memory_enabled:
            return None
        
        try:
            session_data = {
                'user_id': user_id,
                'status': 'active',
                'metadata': metadata or {}
            }
            
            result = self.supabase.table('chat_sessions').insert(session_data).execute()
            
            if result.data:
                session_id = result.data[0]['id']
                self.logger.info(f"Created session {session_id}")
                return session_id
        except Exception as e:
            self.logger.error(f"Error creating session: {e}")
        
        return None
    
    def store_message(self, session_id: str, user_id: str, message_type: str, 
                     content: str, intent: str = None, sources: List[str] = None) -> Optional[str]:
        """Store a message in Supabase"""
        if not self.memory_enabled or not session_id:
            return None
        
        try:
            message_data = {
                'session_id': session_id,
                'user_id': user_id,
                'message_type': message_type,
                'content': content,
                'intent': intent,
                'sources': sources,
                'metadata': {}
            }
            
            result = self.supabase.table('chat_messages').insert(message_data).execute()
            
            if result.data:
                return result.data[0]['id']
        except Exception as e:
            self.logger.error(f"Error storing message: {e}")
        
        return None
    
    def get_session_history(self, session_id: str, limit: int = None) -> List[ChatMessage]:
        """Get conversation history"""
        if not self.memory_enabled or not session_id:
            return []
        
        try:
            query = self.supabase.table('chat_messages').select('*').eq('session_id', session_id).order('created_at')
            
            if limit:
                query = query.limit(limit)
            
            result = query.execute()
            
            messages = []
            for row in result.data:
                messages.append(ChatMessage(
                    id=row['id'],
                    session_id=row['session_id'],
                    user_id=row['user_id'],
                    message_type=row['message_type'],
                    content=row['content'],
                    intent=row['intent'],
                    sources=row['sources'],
                    metadata=row['metadata'],
                    created_at=row['created_at']
                ))
            
            return messages
        except Exception as e:
            self.logger.error(f"Error getting history: {e}")
            return []
    
    def ask_question(self, question: str, user_id: str = None, session_id: str = None) -> Dict[str, Any]:
        """Enhanced question processing with categorized memory handling"""
        try:
            print(f"Processing with Enhanced LLM system: {question}")
            
            # DEBUG: Show what's in the database BEFORE processing
            if session_id:
                debug_info = self.debug_session_data(session_id, user_id)
                print(f"🔍 PRE-PROCESSING DEBUG: {debug_info}")
            
            # Get conversation history FIRST (before storing current question)
            conversation_history = []
            if self.memory_enabled and session_id:
                conversation_history = self.get_session_history(session_id)
                print(f"📜 Retrieved {len(conversation_history)} messages from history")
            
            # Step 1: Intelligent conversation analysis using LLM
            if self.conversation_analyzer:
                analysis = self.conversation_analyzer.analyze_conversation_intent(question, conversation_history)
            else:
                analysis = {
                    "message_type": "faq_question",
                    "handling_strategy": "faq_system",
                    "confidence": 0.5,
                    "reasoning": "Conversation analyzer not available",
                    "is_about_conversation": False,
                    "needs_faq_lookup": True,
                    "suggested_response_tone": "helpful"
                }
            
            print(f"Analysis: {analysis['message_type']} -> {analysis['handling_strategy']} (confidence: {analysis['confidence']:.1f})")
            
            # Step 2: Store current question FIRST
            current_question_id = None
            if self.memory_enabled and session_id and user_id:
                current_question_id = self.store_message(session_id, user_id, 'human', question)
                print(f"✅ Stored current question with ID: {current_question_id}")
            
            # Step 3: Handle MEMORY QUESTIONS with enhanced categorization
            if analysis['handling_strategy'] == 'memory_analysis':
                return self.process_memory_question(question, session_id, user_id, conversation_history)
            
            # Step 4: Handle simple responses
            elif analysis['handling_strategy'] == 'simple_response':
                print("Generating simple conversational response")
                
                if self.conversation_analyzer:
                    response = self.conversation_analyzer.generate_simple_response(question, analysis)
                else:
                    response = "Hello! How can I help you with TradeUP today?"
                
                # Store response
                if self.memory_enabled and session_id and user_id:
                    self.store_message(session_id, user_id, 'ai', response, 
                                    intent=analysis['message_type'], sources=['simple_conversation'])
                
                return {
                    'success': True,
                    'response': response,
                    'session_id': session_id,
                    'enhanced_with_context': False,
                    'conversation_history_used': len(conversation_history) > 0,
                    'memory_enabled': self.memory_enabled,
                    'intent': analysis['message_type'],
                    'sources_count': 0,
                    'categories': ['simple_conversation'],
                    'suggested_questions': [
                        "How do I open a TradeUP account?",
                        "What are the trading fees?",
                        "What documents do I need?"
                    ],
                    'analysis': analysis,
                    'enhanced_llm': True
                }
            
            # Step 5: Process as FAQ question
            else:
                print("Processing as FAQ question with enhanced LLM system")
                
                if not self.faq_system:
                    return {
                        'success': False,
                        'error': 'Enhanced FAQ system not available',
                        'session_id': session_id,
                        'analysis': analysis
                    }
                
                # Get updated conversation history including current question
                updated_conversation_history = conversation_history.copy()
                if current_question_id and self.memory_enabled and session_id:
                    from datetime import datetime
                    current_msg = ChatMessage(
                        id=current_question_id,
                        session_id=session_id,
                        user_id=user_id,
                        message_type='human',
                        content=question,
                        created_at=datetime.now().isoformat()
                    )
                    updated_conversation_history.append(current_msg)
                
                # Get enhanced FAQ response
                faq_result = self.faq_system.get_smart_response(question, updated_conversation_history)
                
                # Store FAQ response
                if self.memory_enabled and session_id and user_id:
                    self.store_message(session_id, user_id, 'ai', faq_result['response'],
                                    intent=faq_result.get('analysis', {}).get('likely_intent', 'general'),
                                    sources=faq_result['categories_used'])
                
                return {
                    'success': True,
                    'response': faq_result['response'],
                    'session_id': session_id,
                    'enhanced_with_context': len(updated_conversation_history) > 1,
                    'conversation_history_used': len(updated_conversation_history) > 1,
                    'memory_enabled': self.memory_enabled,
                    'intent': faq_result.get('analysis', {}).get('likely_intent', 'general'),
                    'sources_count': faq_result['num_sources'],
                    'categories': faq_result['categories_used'],
                    'suggested_questions': faq_result.get('suggested_questions', []),
                    'analysis': analysis,
                    'faq_analysis': faq_result.get('analysis', {}),
                    'enhanced_llm': True,
                    'from_cache': faq_result.get('from_cache', False),
                    'processing_time': faq_result.get('processing_time', 0)
                }
            
        except Exception as e:
            self.logger.error(f"Error in enhanced ask_question: {e}")
            return {
                'success': False,
                'error': str(e),
                'session_id': session_id,
                'enhanced_llm': False
            }

    # NEW ENHANCED MEMORY PROCESSING METHODS
    def process_memory_question(self, question: str, session_id: str, user_id: str, conversation_history: List[ChatMessage]) -> Dict[str, Any]:
        """Process memory-related questions with enhanced content analysis"""
        question_lower = question.lower()
        
        # Categorize the type of memory question
        if any(indicator in question_lower for indicator in ['how many', 'question count', 'count', 'number of questions']):
            return self._handle_count_question(question, session_id, user_id, conversation_history)
        elif any(indicator in question_lower for indicator in ['what have we discussed', 'what did we discuss', 'conversation summary', 'what have we talked about', 'what topics', 'summary of our conversation']):
            return self._handle_content_summary(question, session_id, user_id, conversation_history)
        elif any(indicator in question_lower for indicator in ['first question', 'last question', 'previous question', 'what did i just ask', 'what was my', 'recent question']):
            return self._handle_specific_recall(question, session_id, user_id, conversation_history)
        else:
            return self._handle_content_summary(question, session_id, user_id, conversation_history)

    def _handle_count_question(self, question: str, session_id: str, user_id: str, conversation_history: List[ChatMessage]) -> Dict[str, Any]:
        """Handle questions about question counts"""
        try:
            current_count = self.get_user_question_count_current_session(session_id)
            print(f"🔢 EXACT DATABASE COUNT: {current_count}")
            print(f"✅ BYPASSED LLM - Used exact database count: {current_count}")
            
            return {
                'success': True,
                'response': f"In this conversation session, you've asked exactly {current_count} questions.",
                'memory_enabled': True,
                'session_id': session_id,
                'intent': 'memory_count',
                'sources_count': 0,
                'categories': ['memory_analysis'],
                'suggested_questions': [
                    "What was my first question?",
                    "What have we discussed?",
                    "How do I open a TradeUP account?"
                ],
                'enhanced_with_context': True,
                'conversation_history_used': False,
                'analysis': {
                    'message_type': 'memory_question',
                    'handling_strategy': 'memory_analysis',
                    'memory_type': 'count',
                    'confidence': 1.0
                }
            }
        except Exception as e:
            logging.error(f"Error handling count question: {e}")
            return self._fallback_memory_response(question, session_id)

    def _handle_content_summary(self, question: str, session_id: str, user_id: str, conversation_history: List[ChatMessage]) -> Dict[str, Any]:
        """Handle questions about conversation content/summary"""
        try:
            print(f"🧠 GENERATING CONTENT SUMMARY for session {session_id}")
            
            # Extract user questions (not AI responses) for summary
            user_questions = []
            if conversation_history:
                for msg in conversation_history:
                    if msg.message_type == 'human' and msg.content.strip():
                        content_lower = msg.content.lower()
                        if not any(skip in content_lower for skip in ['how many questions', 'what did i ask', 'what was my']):
                            user_questions.append(msg.content.strip())
            
            if not user_questions:
                response = "This is the beginning of our conversation! You haven't asked any substantive questions yet that I can summarize. Feel free to ask me about TradeUP services, account opening, trading, or any other topics!"
            else:
                # Create intelligent summary
                if len(user_questions) == 1:
                    response = f"In our conversation, we've discussed: {user_questions[0]}. Is there anything else about this topic you'd like to know?"
                else:
                    # Extract key topics from questions
                    topics = []
                    for q in user_questions:
                        if "account" in q.lower():
                            topics.append("account opening")
                        elif "fee" in q.lower() or "cost" in q.lower():
                            topics.append("trading fees")
                        elif "trade" in q.lower():
                            topics.append("trading")
                        elif "document" in q.lower():
                            topics.append("required documents")
                    
                    if topics:
                        unique_topics = list(dict.fromkeys(topics))
                        topics_text = ", ".join(unique_topics[:-1]) + f" and {unique_topics[-1]}" if len(unique_topics) > 1 else unique_topics[0]
                        response = f"In our conversation, we've discussed {topics_text}. Is there anything specific about these topics you'd like me to explain further?"
                    else:
                        response = f"In our conversation, we've covered {len(user_questions)} different topics about TradeUP. Would you like me to elaborate on any of them?"
            
            # Store the response
            if self.memory_enabled and session_id and user_id:
                self.store_message(session_id, user_id, 'ai', response, 
                                intent='conversation_summary', sources=['conversation_history'])
            
            return {
                'success': True,
                'response': response,
                'memory_enabled': True,
                'session_id': session_id,
                'intent': 'memory_summary',
                'sources_count': len(user_questions),
                'categories': ['memory_analysis', 'conversation_summary'],
                'enhanced_with_context': True,
                'conversation_history_used': True,
                'analysis': {
                    'message_type': 'memory_question',
                    'handling_strategy': 'memory_analysis',
                    'memory_type': 'content_summary',
                    'topics_analyzed': len(user_questions),
                    'confidence': 0.9
                }
            }
            
        except Exception as e:
            logging.error(f"Error generating content summary: {e}")
            return self._fallback_memory_response(question, session_id)

    def _handle_specific_recall(self, question: str, session_id: str, user_id: str, conversation_history: List[ChatMessage]) -> Dict[str, Any]:
        """Handle questions about specific previous questions/messages"""
        try:
            question_lower = question.lower()
            user_messages = [msg for msg in conversation_history if msg.message_type == 'human']
            
            if not user_messages:
                response_text = "You haven't asked any previous questions in this session yet."
            else:
                if 'first question' in question_lower:
                    target_message = user_messages[0].content
                    response_text = f'Your first question in this session was: "{target_message}"'
                elif 'last question' in question_lower or 'previous question' in question_lower or 'just ask' in question_lower:
                    if len(user_messages) >= 2:
                        target_message = user_messages[-2].content
                        response_text = f'Your previous question was: "{target_message}"'
                    else:
                        response_text = f'Your only previous question was: "{user_messages[0].content}"'
                else:
                    target_message = user_messages[0].content
                    response_text = f'Your first question in this session was: "{target_message}"'
            
            # Store the response
            if self.memory_enabled and session_id and user_id:
                self.store_message(session_id, user_id, 'ai', response_text, 
                                intent='specific_recall', sources=['conversation_history'])
            
            return {
                'success': True,
                'response': response_text,
                'memory_enabled': True,
                'session_id': session_id,
                'intent': 'memory_recall',
                'sources_count': 1,
                'categories': ['memory_analysis'],
                'enhanced_with_context': True,
                'conversation_history_used': True,
                'analysis': {
                    'message_type': 'memory_question',
                    'handling_strategy': 'memory_analysis',
                    'memory_type': 'specific_recall',
                    'confidence': 1.0
                }
            }
            
        except Exception as e:
            logging.error(f"Error handling specific recall: {e}")
            return self._fallback_memory_response(question, session_id)

    def _fallback_memory_response(self, question: str, session_id: str) -> Dict[str, Any]:
        """Fallback response for memory questions when processing fails"""
        return {
            'success': True,
            'response': "I'm having trouble accessing our conversation history right now. Could you rephrase your question?",
            'memory_enabled': True,
            'session_id': session_id,
            'intent': 'memory_fallback',
            'analysis': {'memory_type': 'fallback'}
        }

    # ESSENTIAL UTILITY METHODS
    def create_new_session_for_user(self, user_id: str, metadata: Dict[str, Any] = None) -> Optional[str]:
        """Create a brand new session for a user"""
        if not self.memory_enabled:
            return None
        
        try:
            session_data = {
                'user_id': user_id,
                'status': 'active',
                'metadata': metadata or {},
                'created_at': datetime.now().isoformat()
            }
            
            result = self.supabase.table('chat_sessions').insert(session_data).execute()
            
            if result.data:
                session_id = result.data[0]['id']
                self.logger.info(f"Created NEW session {session_id} for user {user_id}")
                return session_id
                
        except Exception as e:
            self.logger.error(f"Error creating new session: {e}")
        
        return None

    def get_user_question_count_current_session(self, session_id: str) -> int:
        """Get count of questions in CURRENT session only"""
        if not self.memory_enabled or not session_id:
            return 0
        
        try:
            result = self.supabase.table('chat_messages').select('id').eq('session_id', session_id).eq('message_type', 'human').execute()
            return len(result.data)
        except Exception as e:
            self.logger.error(f"Error getting question count: {e}")
            return 0

    def get_user_question_count_all_sessions(self, user_id: str) -> int:
        """Get count of questions across ALL user sessions"""
        if not self.memory_enabled or not user_id:
            return 0
        
        try:
            result = self.supabase.table('chat_messages').select('id').eq('user_id', user_id).eq('message_type', 'human').execute()
            return len(result.data)
        except Exception as e:
            self.logger.error(f"Error getting total question count: {e}")
            return 0

    def debug_session_data(self, session_id: str, user_id: str = None):
        """Debug what's actually in the database for this session"""
        if not self.memory_enabled or not session_id:
            return None
        
        try:
            print(f"🔍 DEBUG SESSION: {session_id}")
            
            # Get session info
            session_result = self.supabase.table('chat_sessions').select('*').eq('id', session_id).execute()
            if session_result.data:
                session_data = session_result.data[0]
                print(f"📊 Session Status: {session_data['status']}")
                print(f"📅 Created: {session_data['created_at']}")
                print(f"👤 User ID: {session_data['user_id']}")
            
            # Get ALL messages for this session
            messages_result = self.supabase.table('chat_messages').select('*').eq('session_id', session_id).order('created_at').execute()
            
            human_count = 0
            ai_count = 0
            
            print(f"📝 Messages in session {session_id}:")
            for i, msg in enumerate(messages_result.data, 1):
                msg_type = msg['message_type']
                content = msg['content'][:50] + "..." if len(msg['content']) > 50 else msg['content']
                created = msg['created_at']
                
                if msg_type == 'human':
                    human_count += 1
                    print(f"  {i}. 👤 USER: {content} ({created})")
                else:
                    ai_count += 1
                    print(f"  {i}. 🤖 AI: {content} ({created})")
            
            print(f"📊 TOTALS: {human_count} user questions, {ai_count} AI responses")
            
            # Compare with our counting method
            db_count = self.get_user_question_count_current_session(session_id)
            print(f"🔢 Method count: {db_count}")
            
            if user_id:
                total_count = self.get_user_question_count_all_sessions(user_id)
                print(f"🌍 Total across all sessions: {total_count}")
            
            return {
                'session_human_count': human_count,
                'session_ai_count': ai_count,
                'method_count': db_count,
                'total_messages': len(messages_result.data)
            }
            
        except Exception as e:
            print(f"Debug error: {e}")
            return None

    def get_system_info(self) -> Dict[str, Any]:
        """Get information about the enhanced systems"""
        info = {
            'system_type': 'OptimalChatbotFAQ',
            'enhanced_llm': True,
            'memory_enabled': self.memory_enabled,
            'features': [
                'Enhanced LLM-powered intelligent responses',
                'LLM-based conversation analysis',
                'Intelligent question routing',
                'Multi-strategy search',
                'Supabase persistent memory',
                'Advanced response generation'
            ]
        }
        
        if self.faq_system:
            try:
                cache_stats = self.faq_system.get_cache_stats()
                info['faq_system'] = {
                    'type': 'LLMPoweredOptimizedFAQSystem',
                    'cache_stats': cache_stats,
                    'available': True
                }
            except Exception as e:
                info['faq_system'] = {
                    'type': 'LLMPoweredOptimizedFAQSystem',
                    'available': True,
                    'cache_error': str(e)
                }
        else:
            info['faq_system'] = {'available': False}
        
        info['conversation_analyzer'] = {
            'available': self.conversation_analyzer is not None,
            'type': 'ConversationAnalyzer',
            'features': ['LLM-based intent analysis', 'Intelligent conversation handling']
        }
        
        return info

    def submit_feedback(self, session_id: str, user_id: str, question: str, 
                   feedback_type: str, answer_preview: str = None, 
                   system_used: str = None, categories: List[str] = None,
                   sources_count: int = 0, user_ip: str = None, 
                   user_agent: str = None) -> Optional[str]:
        """Submit user feedback to Supabase"""
        if not self.memory_enabled:
            self.logger.warning("Memory not enabled, cannot store feedback")
            return None
        
        if feedback_type not in ['up', 'down']:
            self.logger.error(f"Invalid feedback type: {feedback_type}")
            return None
        
        try:
            feedback_data = {
                'session_id': session_id,
                'user_id': user_id,
                'question': question.strip(),
                'answer_preview': answer_preview[:500] if answer_preview else None,  # Limit length
                'feedback_type': feedback_type,
                'system_used': system_used,
                'categories': categories if categories else [],
                'sources_count': sources_count,
                'user_ip': user_ip,
                'user_agent': user_agent,
                'metadata': {
                    'submitted_at': datetime.now().isoformat(),
                    'question_length': len(question)
                }
            }
            
            result = self.supabase.table('user_feedback').insert(feedback_data).execute()
            
            if result.data:
                feedback_id = result.data[0]['id']
                self.logger.info(f"✅ Feedback submitted: {feedback_id} (type: {feedback_type})")
                return feedback_id
            else:
                self.logger.error("No data returned from feedback insert")
                return None
                
        except Exception as e:
            self.logger.error(f"❌ Error submitting feedback: {e}")
            return None

    def get_feedback_stats(self) -> Dict[str, Any]:
        """Get comprehensive feedback statistics from Supabase"""
        if not self.memory_enabled:
            return {'error': 'Memory not enabled'}
        
        try:
            # Get all feedback
            all_feedback = self.supabase.table('user_feedback').select('feedback_type').execute()
            
            total_feedback = len(all_feedback.data)
            thumbs_up = sum(1 for f in all_feedback.data if f['feedback_type'] == 'up')
            thumbs_down = sum(1 for f in all_feedback.data if f['feedback_type'] == 'down')
            
            # Calculate satisfaction rate
            satisfaction_rate = round((thumbs_up / max(total_feedback, 1)) * 100, 1)
            
            return {
                'success': True,
                'stats': {
                    'total_feedback': total_feedback,
                    'thumbs_up': thumbs_up,
                    'thumbs_down': thumbs_down,
                    'satisfaction_rate': satisfaction_rate,
                    'database_type': 'supabase'
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error getting feedback stats: {e}")
            return {
                'success': False,
                'error': str(e),
                'database_type': 'supabase'
            }
        
    def get_user_feedback_history(self, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get feedback history for a specific user"""
        if not self.memory_enabled:
            self.logger.warning("Memory not enabled, cannot get user feedback history")
            return []
        
        try:
            result = self.supabase.table('user_feedback')\
                .select('*')\
                .eq('user_id', user_id)\
                .order('created_at', desc=True)\
                .limit(limit)\
                .execute()
            
            if result.data:
                self.logger.info(f"Retrieved {len(result.data)} feedback entries for user {user_id}")
                return result.data
            else:
                self.logger.info(f"No feedback found for user {user_id}")
                return []
            
        except Exception as e:
            self.logger.error(f"Error getting user feedback history for {user_id}: {e}")
            return []

    def get_session_feedback(self, session_id: str) -> List[Dict[str, Any]]:
        """Get all feedback for a specific session"""
        if not self.memory_enabled:
            self.logger.warning("Memory not enabled, cannot get session feedback")
            return []
        
        try:
            result = self.supabase.table('user_feedback')\
                .select('*')\
                .eq('session_id', session_id)\
                .order('created_at')\
                .execute()
            
            if result.data:
                self.logger.info(f"Retrieved {len(result.data)} feedback entries for session {session_id}")
                return result.data
            else:
                self.logger.info(f"No feedback found for session {session_id}")
                return []
            
        except Exception as e:
            self.logger.error(f"Error getting session feedback for {session_id}: {e}")
            return []

    def get_user_sessions_with_feedback(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all sessions for a user that have feedback"""
        if not self.memory_enabled:
            return []
        
        try:
            # Get sessions with feedback count
            result = self.supabase.rpc('get_user_sessions_with_feedback_count', {
                'p_user_id': user_id
            }).execute()
            
            return result.data if result.data else []
            
        except Exception as e:
            self.logger.error(f"Error getting user sessions with feedback: {e}")
            # Fallback: get sessions and feedback separately
            try:
                sessions = self.supabase.table('chat_sessions')\
                    .select('id, created_at, status')\
                    .eq('user_id', user_id)\
                    .order('created_at', desc=True)\
                    .execute()
                
                sessions_with_feedback = []
                for session in sessions.data:
                    feedback = self.get_session_feedback(session['id'])
                    if feedback:
                        sessions_with_feedback.append({
                            'session_id': session['id'],
                            'created_at': session['created_at'],
                            'status': session['status'],
                            'feedback_count': len(feedback)
                        })
                
                return sessions_with_feedback
                
            except Exception as fallback_error:
                self.logger.error(f"Fallback method also failed: {fallback_error}")
                return []

    def get_feedback_summary_for_session(self, session_id: str) -> Dict[str, Any]:
        """Get feedback summary for a specific session"""
        if not self.memory_enabled:
            return {'error': 'Memory not enabled'}
        
        try:
            feedback_data = self.get_session_feedback(session_id)
            
            if not feedback_data:
                return {
                    'session_id': session_id,
                    'total_feedback': 0,
                    'thumbs_up': 0,
                    'thumbs_down': 0,
                    'satisfaction_rate': 0.0,
                    'feedback_entries': []
                }
            
            thumbs_up = sum(1 for f in feedback_data if f.get('feedback_type') == 'up')
            thumbs_down = sum(1 for f in feedback_data if f.get('feedback_type') == 'down')
            total = len(feedback_data)
            satisfaction_rate = round((thumbs_up / max(total, 1)) * 100, 1)
            
            return {
                'session_id': session_id,
                'total_feedback': total,
                'thumbs_up': thumbs_up,
                'thumbs_down': thumbs_down,
                'satisfaction_rate': satisfaction_rate,
                'feedback_entries': feedback_data
            }
            
        except Exception as e:
            self.logger.error(f"Error getting feedback summary for session {session_id}: {e}")
            return {'error': str(e)}
    

# SIMPLIFIED HELPER FUNCTIONS
def create_chatbot(memory_window: int = 10, user_id: str = None, new_session: bool = True) -> Tuple[OptimalChatbotFAQ, Optional[str]]:
    """Create an enhanced LLM-powered chatbot instance"""
    chatbot = OptimalChatbotFAQ(memory_window)
    
    if user_id and new_session and chatbot.memory_enabled:
        session_id = chatbot.create_new_session_for_user(user_id, {
            'started_at': datetime.now().isoformat(),
            'restart_type': 'new_session'
        })
        return chatbot, session_id
    
    return chatbot, None