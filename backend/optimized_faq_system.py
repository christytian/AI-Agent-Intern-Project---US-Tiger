import os
import logging
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import pickle
import json
import time
from functools import lru_cache
from datetime import datetime, timedelta
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor
import re

# Core libraries
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import OpenAIEmbeddings
from langchain_core.documents import Document

# OpenAI for chat completion
import openai
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LLMPoweredOptimizedFAQSystem:
    """
    Ultra Fast FAQ system: 3-5 second responses while maintaining accuracy
    Aggressively optimized for speed with minimal quality trade-offs
    """
    
    def __init__(self, 
                 vectorstore_path: str = "/Users/a16463/Desktop/Tiger_Securities/AI-Agent-Intern-Project---US-Tiger/vectorstore",
                 openai_api_key: Optional[str] = None,
                 embedding_model: str = "text-embedding-3-small",
                 chat_model: str = "gpt-4o-mini",
                 top_k: int = 8,
                 similarity_threshold: float = 0.05):
        """
        Initialize the Optimized FAQ system
        """
        self.vectorstore_path = Path(vectorstore_path)
        self.chat_model = chat_model
        self.top_k = top_k
        self.similarity_threshold = similarity_threshold
        
        # Load environment variables
        env_path = "/Users/a16463/Desktop/Tiger_Securities/AI-Agent-Intern-Project---US-Tiger/notepad.env"
        if os.path.exists(env_path):
            load_dotenv(dotenv_path=env_path)
        else:
            load_dotenv()
        
        # Set OpenAI API key
        if openai_api_key:
            os.environ["OPENAI_API_KEY"] = openai_api_key
        elif not os.environ.get("OPENAI_API_KEY"):
            raise ValueError("OpenAI API key must be provided")
        
        # Initialize OpenAI client
        self.client = openai.OpenAI(api_key=os.environ["OPENAI_API_KEY"], timeout=15.0)
        
        # Initialize embeddings
        self.embeddings = OpenAIEmbeddings(model=embedding_model)
        
        # Load vectorstore and metadata
        self.vectorstore = self._load_vectorstore()
        self.metadata = self._load_metadata()
        
        # Enhanced caching
        self.response_cache = {}
        self.search_cache = {}
        
        # Thread pool for parallel operations
        self.executor = ThreadPoolExecutor(max_workers=2)
        
        # Pre-computed category mappings for faster routing
        self.category_keywords = self._build_category_mappings()
        
        logger.info("LLMPoweredOptimizedFAQSystem initialized - ultra fast optimizations")
    
    def _load_vectorstore(self) -> FAISS:
        """Load the saved FAISS vectorstore"""
        if not self.vectorstore_path.exists():
            raise FileNotFoundError(f"Vectorstore not found at {self.vectorstore_path}")
        
        vectorstore = FAISS.load_local(
            str(self.vectorstore_path), 
            self.embeddings,
            allow_dangerous_deserialization=True
        )
        logger.info(f"Loaded vectorstore from {self.vectorstore_path}")
        return vectorstore
    
    def _load_metadata(self) -> Dict[str, Any]:
        """Load metadata about the indexed documents"""
        metadata_path = self.vectorstore_path / "metadata.pkl"
        if metadata_path.exists():
            try:
                with open(metadata_path, "rb") as f:
                    return pickle.load(f)
            except Exception:
                pass
        return {}
    
    def _build_category_mappings(self) -> Dict[str, List[str]]:
        """Pre-build category keyword mappings for faster routing"""
        return {
            'account': ['account', 'open', 'new', 'registration', 'sign up', 'documents', 'verify', 'identity'],
            'funding': ['deposit', 'withdraw', 'fund', 'money', 'transfer', 'ach', 'wire'],
            'trading': ['trade', 'trading', 'buy', 'sell', 'stock', 'equity'],
            'orders': ['order', 'limit', 'market', 'stop'],
            'fractional': ['fractional', 'partial', 'share'],
            'hours': ['extended', 'after hours', 'pre market', 'hours'],
            'cash': ['cash', 'cash account'],
            'margin': ['margin', 'leverage', 'buying power'],
            'day_trading': ['day trading', 'pdt', 'pattern'],
            'otc': ['otc', 'over counter', 'pink sheet'],
            'options': ['option', 'options', 'call', 'put', 'derivative'],
            'security': ['authenticator', '2fa', 'security'],
            'lending': ['lending', 'securities lending', 'borrow'],
            'tax': ['tax', 'taxes', '1099', 'statement'],
            'ira': ['ira', 'retirement', 'roth', 'traditional'],
            'market_data': ['current price', 'stock price', 'market price', 'quote', 'real-time', 'today price']
        }
    
    @lru_cache(maxsize=2000)
    def _get_question_hash(self, query: str) -> str:
        """Create a hash for caching responses"""
        return hashlib.md5(query.lower().strip().encode()).hexdigest()
    
    def smart_question_analysis(self, query: str, conversation_history: List = None) -> Dict[str, Any]:
        """
        HYBRID analysis: Fast keyword-based + selective LLM analysis for complex cases
        """
        query_lower = query.lower()
        
        # Fast routing for obvious cases
        if any(keyword in query_lower for keyword in self.category_keywords['market_data']):
            return {
                "question_type": "market_data",
                "routing_decision": "market_agent", 
                "confidence": 0.9,
                "category_hint": "market_data",
                "analysis_method": "fast_keyword"
            }
        
        if query_lower.strip() in ['hi', 'hello', 'hey', 'good morning', 'good afternoon']:
            return {
                "question_type": "greeting",
                "routing_decision": "simple_response",
                "confidence": 0.9,
                "category_hint": "greeting",
                "analysis_method": "fast_keyword"
            }
        
        # Memory queries
        memory_keywords = ['how many questions', 'what did i ask', 'previous', 'conversation', 'discussed']
        if any(keyword in query_lower for keyword in memory_keywords):
            return {
                "question_type": "memory_query",
                "routing_decision": "simple_response",
                "confidence": 0.8,
                "category_hint": "memory",
                "analysis_method": "fast_keyword"
            }
        
        # Find best matching FAQ category
        best_category = None
        max_matches = 0
        
        for category, keywords in self.category_keywords.items():
            if category == 'market_data':  # Already checked
                continue
            matches = sum(1 for keyword in keywords if keyword in query_lower)
            if matches > max_matches:
                max_matches = matches
                best_category = category
        
        # For complex queries, use LLM analysis
        if max_matches == 0 or len(query.split()) > 10:
            return self._llm_analysis(query, conversation_history, best_category)
        
        # Fast analysis for clear FAQ queries
        return {
            "question_type": "faq_query",
            "routing_decision": "faq_system",
            "confidence": 0.8 if max_matches > 0 else 0.6,
            "category_hint": best_category or "general",
            "analysis_method": "fast_keyword",
            "likely_intent": f"Get information about {best_category or 'Tiger Securities services'}"
        }
    
    def _llm_analysis(self, query: str, conversation_history: List, category_hint: str) -> Dict[str, Any]:
        """
        Use LLM analysis only for complex/ambiguous queries
        """
        # Build minimal conversation context
        conversation_context = ""
        if conversation_history:
            recent_messages = conversation_history[-2:]
            context_parts = []
            for msg in recent_messages:
                if hasattr(msg, 'content') and hasattr(msg, 'message_type'):
                    role = "User" if msg.message_type == 'human' else "Assistant"
                    context_parts.append(f"{role}: {msg.content[:100]}...")
            conversation_context = "\n".join(context_parts)
        
        analysis_prompt = f"""Analyze this Tiger Securities customer question:

Question: "{query}"
Context: {conversation_context or "None"}
Suggested category: {category_hint or "unknown"}

Respond with JSON only:
{{
    "question_type": "faq_query" | "market_data" | "greeting" | "conversational" | "memory_query",
    "routing_decision": "faq_system" | "market_agent" | "simple_response",
    "confidence": 0.0-1.0,
    "likely_intent": "Brief intent description",
    "category_hint": "Best matching FAQ category"
}}

Guidelines:
- "market_data" = Real-time prices, current market info
- "faq_query" = Tiger Securities policies, procedures, account questions  
- Use "faq_system" for most trading/account questions"""

        try:
            response = self.client.chat.completions.create(
                model=self.chat_model,
                messages=[
                    {"role": "system", "content": "Analyze the question and respond with JSON only."},
                    {"role": "user", "content": analysis_prompt}
                ],
                temperature=0.0,
                max_tokens=200,
                timeout=8
            )
            
            analysis_text = response.choices[0].message.content.strip()
            if analysis_text.startswith('```json'):
                analysis_text = analysis_text.replace('```json', '').replace('```', '')
            
            analysis = json.loads(analysis_text)
            analysis["analysis_method"] = "llm_detailed"
            return analysis
            
        except Exception as e:
            logger.warning(f"LLM analysis failed: {e}, using fallback")
            return {
                "question_type": "faq_query",
                "routing_decision": "faq_system",
                "confidence": 0.7,
                "category_hint": category_hint or "general",
                "analysis_method": "fallback",
                "likely_intent": "Get Tiger Securities information"
            }
    
    def ultra_fast_search(self, query: str, analysis: Dict[str, Any]) -> List[Document]:
        """
        Ultra fast search with single strategy
        """
        start_time = time.time()
        
        # Check search cache
        search_key = f"{query}_{analysis.get('category_hint', 'general')}"
        search_hash = hashlib.md5(search_key.encode()).hexdigest()
        
        if search_hash in self.search_cache:
            print(f"⚡ Search cache hit - ultra fast return")
            return self.search_cache[search_hash]
        
        print(f"🚀 Ultra fast search for: '{query}'")
        
        try:
            docs_with_scores = self.vectorstore.similarity_search_with_score(query, k=self.top_k)
            print(f"  📝 Direct search: {len(docs_with_scores)} docs")
            
            final_docs = []
            for doc, score in docs_with_scores:
                similarity = 1 - score
                if similarity >= self.similarity_threshold:
                    doc.metadata['retrieval_score'] = similarity
                    doc.metadata['retrieval_method'] = 'direct_search'
                    final_docs.append(doc)
            
            # Cache immediately
            self.search_cache[search_hash] = final_docs
            
            search_time = time.time() - start_time
            print(f"🚀 Ultra fast search completed: {len(final_docs)} docs in {search_time:.2f}s")
            
            return final_docs
            
        except Exception as e:
            logger.error(f"Ultra fast search failed: {e}")
            return []
    
    def generate_ultra_fast_response(self, query: str, faq_documents: List[Document], 
                                   analysis: Dict[str, Any]) -> str:
        """
        Ultra fast response generation - handles both FAQ sources and zero sources
        """
        print(f"🔍 generate_ultra_fast_response: Got {len(faq_documents)} documents")
        
        # Handle zero documents case
        if not faq_documents:
            print(f"⚠️ No FAQ documents found - using structured LLM knowledge")
            return self._generate_zero_documents_response(query)
        
        # Handle FAQ documents case
        return self._generate_faq_response(query, faq_documents)
    
    def _generate_faq_response(self, query: str, faq_documents: List[Document]) -> str:
        """
        Generate CONCISE, well-structured response using FAQ documents
        """
        print(f"📚 Generating CONCISE FAQ response with {len(faq_documents)} sources")
        
        # Use top 3 documents for focused response
        top_docs = faq_documents[:3]
        
        # Build focused context
        faq_context = "=== FAQ KNOWLEDGE ===\n"
        for i, doc in enumerate(top_docs, 1):
            category = doc.metadata.get("category_name", "General")
            question = doc.metadata.get("question", "")
            # Use shorter content for more focused responses
            content = doc.page_content[:300] + "..." if len(doc.page_content) > 300 else doc.page_content
            
            faq_context += f"""
    {i}. CATEGORY: {category}
    QUESTION: {question}
    CONTENT: {content}
    ---"""

        system_prompt = f"""You are Tiger Securities' AI assistant. Create a CONCISE, well-structured response using the FAQ information.

    {faq_context}

    RESPONSE REQUIREMENTS:
    - Keep response under 200 words
    - Use clear, short paragraphs (2-3 sentences each)
    - Start with a direct answer
    - Use bullet points for lists (• not -)
    - Include key details but avoid repetition
    - End with EXACTLY: "**Source: Tiger Securities FAQ Database**"
    - NO trailing text after the source line

    FORMATTING RULES:
    - Use paragraphs separated by blank lines
    - Bold important terms: **Form 1099**, **Account**, etc.
    - Keep paragraphs short and scannable
    - Use simple, clear language
    - Focus on the most important information"""

        user_prompt = f"""User Question: "{query}"

    Create a concise, well-formatted response that directly answers the question. Keep it under 200 words with clear paragraphs and bullet points where helpful."""

        try:
            response = self.client.chat.completions.create(
                model=self.chat_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,
                max_tokens=300,  # Reduced for shorter responses
                timeout=15
            )
            
            generated_response = response.choices[0].message.content
            print(f"🔍 RAW CONCISE FAQ RESPONSE: {repr(generated_response[-50:])}")
            
            cleaned_response = self._universal_response_cleaner(generated_response, "faq")
            print(f"🧹 CLEANED CONCISE RESPONSE: {repr(cleaned_response[-50:])}")
            
            return cleaned_response
            
        except Exception as e:
            logger.error(f"Concise FAQ response generation failed: {e}")
            return self._generate_simple_fallback_response(query, top_docs, "faq")

    
    def _generate_zero_documents_response(self, query: str) -> str:
        """
        Generate CONCISE LLM response when no FAQ documents are found
        """
        print(f"🤖 Generating CONCISE LLM knowledge response: {query}")
        
        system_prompt = """You are Tiger Securities' AI assistant. Provide a CONCISE, helpful response using your general knowledge.

    RESPONSE REQUIREMENTS:
    - Keep response under 150 words
    - Use clear, short paragraphs
    - Start with a direct answer
    - Use bullet points for lists (• not -)
    - Be practical and actionable
    - End with EXACTLY: "**Source: AI Assistant Knowledge**"
    - NO trailing text after the source line

    FORMATTING RULES:
    - Use paragraphs separated by blank lines
    - Bold important terms
    - Keep it concise and scannable
    - Suggest contacting Tiger Securities for specifics"""

        user_prompt = f"""User Question: "{query}"

    This wasn't found in our FAQ database. Provide a concise, helpful response using general financial knowledge. Keep it under 150 words with clear formatting."""

        try:
            response = self.client.chat.completions.create(
                model=self.chat_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,
                max_tokens=250,  # Reduced for shorter responses
                timeout=15
            )
            
            generated_response = response.choices[0].message.content
            print(f"🔍 RAW CONCISE AI RESPONSE: {repr(generated_response[-50:])}")
            
            cleaned_response = self._universal_response_cleaner(generated_response, "ai")
            print(f"🧹 CLEANED CONCISE RESPONSE: {repr(cleaned_response[-50:])}")
            
            return cleaned_response
            
        except Exception as e:
            logger.error(f"Concise AI response generation failed: {e}")
            return self._generate_fallback_response(query, [], "ai")

    def _generate_simple_fallback_response(self, query: str, docs: List[Document], source_type: str) -> str:
        """Generate a simple fallback response when LLM fails"""
        if docs and len(docs) > 0:
            # Use the first document's content directly
            content = docs[0].page_content[:200] + "..." if len(docs[0].page_content) > 200 else docs[0].page_content
            source = "**Source: Tiger Securities FAQ Database**" if source_type == "faq" else "**Source: AI Assistant Knowledge**"
            return f"{content}\n\n{source}"
        else:
            return f"I found information about your question, but I'm having trouble formatting the response right now. Please try asking again or contact Tiger Securities support.\n\n**Source: AI Assistant Knowledge**"
        
    def _universal_response_cleaner(self, response: str, source_type: str) -> str:
        """
        Enhanced response cleaner for concise, well-formatted responses
        """
        if not response:
            return response
        
        print(f"🧹 Enhanced cleaning for {source_type} response")
        
        # Step 1: Initial cleaning
        cleaned = response.strip()
        
        # Step 2: Remove all trailing junk aggressively
        patterns_to_remove = [
            r'[\s*\d]+$',           # Numbers and asterisks at end
            r'\*+\s*$',             # Asterisks at end
            r'[*\d\s]+$',           # Mixed symbols/numbers
            r'\s*\d+\s*$',          # Numbers with spaces
            r'\d+$',                # Just numbers
        ]
        
        for pattern in patterns_to_remove:
            cleaned = re.sub(pattern, '', cleaned)
        
        # Step 3: Set expected source
        expected_source = "**Source: Tiger Securities FAQ Database**" if source_type == "faq" else "**Source: AI Assistant Knowledge**"
        
        # Step 4: Remove any existing malformed source lines
        source_patterns = [
            r'\*+\s*Source:.*?\*+.*$',
            r'\*+Source:.*$', 
            r'\*\*Source:.*\*\*.*$',
        ]
        
        for pattern in source_patterns:
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE | re.MULTILINE)
        
        # Step 5: Format content for better readability
        lines = cleaned.split('\n')
        formatted_lines = []
        
        for line in lines:
            line = line.strip()
            
            # Skip empty lines or lines with just symbols
            if not line or re.match(r'^[*\s\d]+$', line):
                continue
            
            # Clean up formatting
            line = re.sub(r'\s+', ' ', line)  # Multiple spaces to single space
            line = re.sub(r'^[*\s\d]+', '', line)  # Remove leading junk
            line = re.sub(r'[*\s\d]+$', '', line)  # Remove trailing junk
            
            if line and len(line) > 5:  # Only meaningful lines
                formatted_lines.append(line)
        
        # Step 6: Structure the content with proper paragraphs
        if formatted_lines:
            # Group lines into paragraphs
            paragraphs = []
            current_paragraph = []
            
            for line in formatted_lines:
                if line.startswith('•') or line.startswith('-') or line.startswith('*'):
                    # Bullet point - start new paragraph if needed
                    if current_paragraph:
                        paragraphs.append(' '.join(current_paragraph))
                        current_paragraph = []
                    paragraphs.append(line)
                elif line.startswith('#') or line.isupper() or len(line) < 50:
                    # Heading or short line - separate paragraph
                    if current_paragraph:
                        paragraphs.append(' '.join(current_paragraph))
                        current_paragraph = []
                    paragraphs.append(line)
                else:
                    # Regular text - add to current paragraph
                    current_paragraph.append(line)
            
            # Add any remaining paragraph
            if current_paragraph:
                paragraphs.append(' '.join(current_paragraph))
            
            # Join paragraphs with double newlines for better spacing
            content = '\n\n'.join(paragraphs)
            
            # Ensure it's not too long (max 200 words roughly)
            words = content.split()
            if len(words) > 200:
                content = ' '.join(words[:200]) + '...'
            
            final_response = f"{content}\n\n{expected_source}"
        else:
            final_response = f"I have information about your question. Please contact Tiger Securities for specific details.\n\n{expected_source}"
        
        # Step 7: Final cleanup - ensure no trailing junk after source
        source_index = final_response.rfind(expected_source)
        if source_index != -1:
            final_response = final_response[:source_index + len(expected_source)]
        
        # Step 8: Ensure proper paragraph breaks
        final_response = re.sub(r'\n{3,}', '\n\n', final_response)  # Max 2 newlines
        final_response = final_response.strip()
        
        print(f"🧹 Cleaned response length: {len(final_response)} chars, {len(final_response.split())} words")
        
        return final_response
    
    
    def _generate_fallback_response(self, query: str, documents: List[Document], source_type: str) -> str:
        """
        Generate clean fallback response when LLM calls fail
        """
        expected_source = "**Source: Tiger Securities FAQ Database**" if source_type == "faq" else "**Source: AI Assistant Knowledge**"
        
        if documents and source_type == "faq":
            doc = documents[0]
            content = doc.page_content[:300]
            # Clean the content
            content = re.sub(r'[\s*\d]+$', '', content)
            return f"{content}\n\n{expected_source}"
        else:
            return f"""I understand you're asking about "{query}".

While this specific question isn't covered in our Tiger Securities FAQ database, I recommend:

• Search online for detailed information about this topic
• Visit the official Tiger Securities website for specific policies  
• Contact Tiger Securities customer support directly for personalized assistance

Our support team can provide you with the most accurate and up-to-date information for your specific needs.

{expected_source}"""
    
    def generate_ultra_fast_suggestions(self, query: str, category_hint: str, faq_documents: List[Document]) -> List[str]:
        """
        Generate relevant suggestions based on the actual query and found documents
        """
        print(f"🔍 Generating suggestions for query: '{query}' with category: {category_hint}")
        
        # If we have FAQ documents, generate suggestions based on similar content
        if faq_documents:
            return self._generate_contextual_suggestions(query, faq_documents, category_hint)
        else:
            # For zero sources, generate suggestions based on query keywords
            return self._generate_keyword_based_suggestions(query, category_hint)
    
    def _generate_contextual_suggestions(self, query: str, faq_documents: List[Document], category_hint: str) -> List[str]:
        """
        Generate suggestions based on found FAQ documents
        """
        suggestions = []
        categories_found = set()
        
        # Extract categories and related questions from found documents
        for doc in faq_documents[:6]:  # Use more docs for suggestions
            category = doc.metadata.get("category_name", "")
            question = doc.metadata.get("question", "")
            
            if category and category not in categories_found:
                categories_found.add(category)
                if question and question not in suggestions and len(question) < 100:
                    suggestions.append(question)
        
        # If we don't have enough, supplement with category-based suggestions
        if len(suggestions) < 4:
            category_suggestions = self._get_category_suggestions(category_hint)
            for suggestion in category_suggestions:
                if suggestion not in suggestions:
                    suggestions.append(suggestion)
                if len(suggestions) >= 4:
                    break
        
        return suggestions[:4]
    
    def _generate_keyword_based_suggestions(self, query: str, category_hint: str) -> List[str]:
        """
        Generate suggestions based on query keywords when no FAQ docs found
        """
        query_lower = query.lower()
        
        # Keyword-based suggestions
        if any(word in query_lower for word in ['document', 'documents', 'need', 'required', 'verification']):
            return [
                "What documents do I need to open an account?",
                "How do I verify my identity?",
                "What is the account approval process?",
                "How long does identity verification take?"
            ]
        
        if any(word in query_lower for word in ['deposit', 'fund', 'money', 'transfer']):
            return [
                "How do I deposit money into my account?",
                "What are the funding options available?",
                "How long do deposits take to clear?",
                "Are there any deposit fees?"
            ]
        
        if any(word in query_lower for word in ['trade', 'trading', 'buy', 'sell']):
            return [
                "How do I place my first trade?",
                "What are the trading fees?",
                "What order types are available?",
                "What are the trading hours?"
            ]
        
        # Default suggestions based on category
        return self._get_category_suggestions(category_hint)
    
    def _get_category_suggestions(self, category_hint: str) -> List[str]:
        """
        Get default suggestions based on category
        """
        category_suggestions = {
            'account': [
                "How do I open a Tiger Securities account?",
                "What documents are required for account opening?",
                "How long does account approval take?",
                "What types of accounts are available?"
            ],
            'funding': [
                "How do I deposit money into my account?",
                "What are the available funding methods?",
                "How long do deposits take?",
                "Are there withdrawal fees?"
            ],
            'trading': [
                "What are the trading fees and commissions?",
                "How do I place my first trade?", 
                "What are the trading hours?",
                "What order types are supported?"
            ],
            'margin': [
                "What are margin requirements?",
                "How do I enable margin trading?",
                "What is buying power?",
                "What are margin interest rates?"
            ],
            'options': [
                "How do I get approved for options trading?",
                "What are the options trading levels?",
                "What are options trading fees?",
                "What are the risks of options trading?"
            ]
        }
        
        if category_hint in category_suggestions:
            return category_suggestions[category_hint]
        
        # Default general suggestions
        return [
            "How do I open a Tiger Securities account?",
            "What are the trading fees and commissions?",
            "How do I fund my trading account?",
            "What documents do I need to get started?"
        ]
    
    def get_smart_response(self, query: str, conversation_history: List = None) -> Dict[str, Any]:
        """
        Main response pipeline with proper source attribution
        """
        start_time = time.time()
        logger.info(f"Processing query: {query}")
        
        # Check cache first
        query_hash = self._get_question_hash(query)
        if query_hash in self.response_cache:
            cached_result = self.response_cache[query_hash].copy()
            cached_result['from_cache'] = True
            cached_result['processing_time'] = time.time() - start_time
            print(f"⚡ Cache hit - response available instantly!")
            return cached_result
        
        # Step 1: Smart analysis
        analysis = self.smart_question_analysis(query, conversation_history)
        analysis_method = analysis.get('analysis_method', 'unknown')
        print(f"🧠 Analysis ({analysis_method}): {analysis['question_type']} -> {analysis['routing_decision']}")
        
        # Step 2: Handle simple routing cases
        if analysis['routing_decision'] == 'market_agent':
            result = {
                "query": query,
                "response": f"This question requires real-time market data. Routing reason: {analysis.get('likely_intent', 'Market data request')}. Please use the market agent for current financial information.",
                "use_market_agent": True,
                "analysis": analysis,
                "num_sources": 0,
                "sources": [],
                "suggested_questions": self._get_category_suggestions("trading"),
                "processing_time": time.time() - start_time,
                "from_cache": False,
                "source_attribution": "Market Agent Routing"
            }
            return result
        
        elif analysis['routing_decision'] == 'simple_response':
            if analysis['question_type'] == 'greeting':
                simple_response = "Hello! I'm here to help you with your Tiger Securities questions. I have access to our comprehensive FAQ database covering all service categories. What would you like to know?"
            elif analysis['question_type'] == 'memory_query':
                simple_response = "I don't have access to our previous conversation history in this session. However, I'm here to help with any Tiger Securities questions about trading, accounts, or our services. What would you like to know?"
            else:
                simple_response = "I'm here to help with your Tiger Securities questions. What would you like to know about our trading services, accounts, or platform features?"
            
            result = {
                "query": query,
                "response": simple_response,
                "use_market_agent": False,
                "analysis": analysis,
                "num_sources": 0,
                "sources": [],
                "suggested_questions": self._get_category_suggestions("account"),
                "processing_time": time.time() - start_time,
                "from_cache": False,
                "source_attribution": "AI Assistant"
            }
            return result
        
        # Step 3: FAQ search and response
        print(f"🚀 Starting FAQ search...")
        faq_documents = self.ultra_fast_search(query, analysis)
        
        print(f"⚡ Generating response...")
        response = self.generate_ultra_fast_response(query, faq_documents, analysis)
        
        # Generate contextual suggestions
        suggested_questions = self.generate_ultra_fast_suggestions(
            query, analysis.get('category_hint', 'general'), faq_documents
        )
        
        # Compile results
        sources = []
        for doc in faq_documents:
            sources.append({
                "source_type": "faq_database",
                "category": doc.metadata.get("category_name", "Unknown"),
                "question": doc.metadata.get("question", ""),
                "relevance_score": round(doc.metadata.get("retrieval_score", 0), 3),
                "retrieval_method": doc.metadata.get("retrieval_method", "unknown")
            })
        
        # Source attribution
        if faq_documents:
            categories_used = list(set(doc.metadata.get("category_name", "Unknown") for doc in faq_documents))
            if len(categories_used) == 1:
                source_attribution = f"Tiger Securities FAQ Database: {categories_used[0]}"
            else:
                source_attribution = f"Tiger Securities FAQ Database: {', '.join(categories_used[:3])}"
        else:
            source_attribution = "AI Assistant Knowledge + Online Search Suggested"
            categories_used = []
        
        result = {
            "query": query,
            "response": response,
            "use_market_agent": False,
            "analysis": analysis,
            "num_sources": len(sources),
            "sources": sources,
            "categories_used": categories_used,
            "suggested_questions": suggested_questions,
            "processing_time": time.time() - start_time,
            "from_cache": False,
            "source_attribution": source_attribution,
            "faq_sources_count": len(faq_documents),
            "search_strategies_used": list(set(doc.metadata.get("retrieval_method", "unknown") for doc in faq_documents)),
            "has_faq_sources": len(faq_documents) > 0
        }
        
        # Cache the response
        self.response_cache[query_hash] = result.copy()
        
        # Limit cache size
        if len(self.response_cache) > 800:
            keys_to_remove = list(self.response_cache.keys())[:150]
            for key in keys_to_remove:
                del self.response_cache[key]
        
        print(f"✅ RESPONSE COMPLETED:")
        print(f"   📊 FAQ sources: {len(faq_documents)}")
        print(f"   📝 Source attribution: {source_attribution}")
        print(f"   ⏱️  Total time: {result['processing_time']:.2f}s")
        print(f"   🤖 LLM knowledge used: {len(faq_documents) == 0}")
        
        return result
    
    def clear_cache(self):
        """Clear all caches"""
        self.response_cache.clear()
        self.search_cache.clear()
        logger.info("All caches cleared")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return {
            "response_cache_size": len(self.response_cache),
            "search_cache_size": len(self.search_cache),
            "total_cached_queries": len(self.response_cache) + len(self.search_cache)
        }
    
    def get_system_info(self) -> Dict[str, Any]:
        """Get system information"""
        info = {
            'system_type': 'LLMPoweredOptimizedFAQSystem',
            'optimization_level': 'Ultra Fast: 3-5 second target',
            'target_response_time': '3-5 seconds',
            'features': {
                'comprehensive_faq_search': True,
                'smart_hybrid_analysis': True,
                'quality_preservation': True,
                'enhanced_caching': True,
                'selective_llm_usage': True,
                'source_attribution': True,
                'contextual_suggestions': True,
                'universal_response_cleaning': True
            },
            'cache_stats': self.get_cache_stats()
        }
        
        if self.metadata:
            info['faq_database'] = {
                'total_qa_pairs': self.metadata.get('total_qa_pairs', 0),
                'total_categories': self.metadata.get('total_categories', 0),
                'categories': self.metadata.get('categories', []),
                'indexed_at': self.metadata.get('indexed_at', 'unknown')
            }
        
        return info
    
    def interactive_chat(self):
        """Interactive chat interface"""
        print("\n" + "="*80)
        print("🐅 TIGER SECURITIES ULTRA FAST FAQ ASSISTANT")
        print("⚡ Ultra Fast (3-5s) + 🎯 Accurate + 📚 FAQ-Based")
        print("="*80)
        print("🚀 Features:")
        print("   ⚡ Single search strategy for speed")
        print("   🎯 Contextual suggestions based on your questions")
        print("   🧹 Universal response cleaning (no trailing characters)")
        print("   💾 Enhanced caching for instant repeats")
        print("   ⏱️  Target: 3-5 second responses")
        
        info = self.get_system_info()
        if info.get('faq_database'):
            faq_info = info['faq_database']
            print(f"   📚 FAQ database: {faq_info['total_qa_pairs']} Q&A pairs across {faq_info['total_categories']} categories")
        
        print("="*80 + "\n")
        
        question_count = 0
        total_time = 0
        cached_responses = 0
        
        while True:
            try:
                user_input = input("🤔 You: ").strip()
                
                if user_input.lower() in ['quit', 'exit', 'bye']:
                    avg_time = total_time / max(1, question_count)
                    cache_rate = (cached_responses / max(1, question_count)) * 100
                    print(f"\n📊 Session Summary:")
                    print(f"   Questions: {question_count}")
                    print(f"   Average response time: {avg_time:.2f}s")
                    print(f"   Cache hit rate: {cache_rate:.1f}%")
                    print("\n⚡ Thank you for using Tiger Securities FAQ Assistant!")
                    break
                
                if user_input.lower() == 'stats':
                    stats = self.get_cache_stats()
                    avg_time = total_time / max(1, question_count) if question_count > 0 else 0
                    cache_rate = (cached_responses / max(1, question_count)) * 100 if question_count > 0 else 0
                    print(f"\n📊 Performance Statistics:")
                    print(f"   Questions answered: {question_count}")
                    print(f"   Average response time: {avg_time:.2f}s")
                    print(f"   Cache hit rate: {cache_rate:.1f}%")
                    print(f"   Total cached entries: {stats['total_cached_queries']}")
                    continue
                
                if user_input.lower() == 'clear cache':
                    self.clear_cache()
                    print("\n🧹 All caches cleared!")
                    continue
                
                if not user_input:
                    continue
                
                question_count += 1
                print(f"\n🚀 Processing...")
                
                result = self.get_smart_response(user_input)
                total_time += result['processing_time']
                
                if result.get('from_cache'):
                    cached_responses += 1
                
                # Display response
                if result.get('use_market_agent'):
                    print(f"\n🔀 {result['response']}")
                else:
                    print(f"\n🐅 Tiger Securities Response:")
                    print(f"{result['response']}")
                
                # Performance metrics
                time_taken = result['processing_time']
                speed_indicator = "⚡" if time_taken < 4 else "🚀" if time_taken < 6 else "✅"
                cache_indicator = "💾" if result.get('from_cache') else "🆕"
                
                print(f"\n📊 {speed_indicator} {cache_indicator} Response time: {time_taken:.2f}s")
                print(f"   📚 FAQ sources: {result.get('faq_sources_count', 0)}")
                print(f"   🎯 Categories: {', '.join(result.get('categories_used', [])[:3])}")
                
                # Suggestions
                if result.get('suggested_questions'):
                    print(f"\n💡 Related questions:")
                    for i, suggestion in enumerate(result['suggested_questions'][:3], 1):
                        print(f"   {i}. {suggestion}")
                
                print("\n" + "-"*60 + "\n")
                
            except KeyboardInterrupt:
                print("\n\n⚡ Chat interrupted. Goodbye!")
                break
            except Exception as e:
                print(f"\n❌ Error: {str(e)}")
                print("Please try again.\n")

def main():
    """Main function"""
    try:
        print("⚖️  Initializing Tiger Securities FAQ Assistant...")
        print("🎯 Target: Fast + Accurate responses")
        
        faq_system = LLMPoweredOptimizedFAQSystem()
        
        print("✅ FAQ Assistant ready!")
        faq_system.interactive_chat()
        
    except Exception as e:
        logger.error(f"FAQ system failed: {str(e)}")
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    main()