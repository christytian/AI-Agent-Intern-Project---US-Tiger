import os
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
import pickle
import json

# Core libraries
from langchain_community.vectorstores import FAISS
from langchain.embeddings import OpenAIEmbeddings
from langchain_core.documents import Document

# OpenAI for chat completion
import openai
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SmartFAQSystem:
    """
    An intelligent FAQ system that:
    1. Uses FAQ database as the foundation
    2. Infers user intent and provides comprehensive answers
    3. Combines multiple FAQ sources intelligently
    4. Applies logical reasoning while staying grounded in FAQ content
    5. Anticipates follow-up questions and provides proactive suggestions
    """
    
    def __init__(self, 
                 vectorstore_path: str = "/Users/a16463/Desktop/Tiger_Securities/AI-Agent-Intern-Project---US-Tiger/vectorstore",
                 openai_api_key: Optional[str] = None,
                 embedding_model: str = "text-embedding-3-small",
                 chat_model: str = "gpt-4o",
                 top_k: int = 8,  # More sources for better synthesis
                 similarity_threshold: float = 0.2):  # Much lower threshold for better recall
        """
        Initialize the Smart FAQ system
        """
        self.vectorstore_path = Path(vectorstore_path)
        self.chat_model = chat_model
        self.top_k = top_k
        self.similarity_threshold = similarity_threshold
        
        # Load environment variables
        env_path = "/Users/a16463/Desktop/Tiger_Securities/AI-Agent-Intern-Project---US-Tiger/notepad.env"
        load_dotenv(dotenv_path=env_path)
        
        # Set OpenAI API key
        if openai_api_key:
            os.environ["OPENAI_API_KEY"] = openai_api_key
        elif not os.environ.get("OPENAI_API_KEY"):
            raise ValueError("OpenAI API key must be provided")
        
        # Initialize OpenAI client
        self.client = openai.OpenAI(api_key=os.environ["OPENAI_API_KEY"])
        
        # Initialize embeddings with fallback
        self._initialize_embeddings(embedding_model)
        
        # Load vectorstore and metadata
        self.vectorstore = self._load_vectorstore()
        self.metadata = self._load_metadata()
        
        # Conversation context for better inference
        self.conversation_context = []
        
        # Track current suggested questions for interactive selection
        self.current_suggestions = []
        
        logger.info("Smart FAQ System initialized - intelligent synthesis with FAQ grounding")
    
    def _initialize_embeddings(self, embedding_model: str):
        """Initialize embeddings with fallback"""
        try:
            self.embeddings = OpenAIEmbeddings(model=embedding_model)
            logger.info("Using OpenAI embeddings")
        except Exception as e:
            logger.warning(f"OpenAI embeddings failed: {e}")
            from langchain_community.embeddings import HuggingFaceEmbeddings
            self.embeddings = HuggingFaceEmbeddings(
                model_name="sentence-transformers/all-MiniLM-L6-v2"
            )
    
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
    
    def analyze_user_intent(self, query: str) -> Dict[str, Any]:
        """
        Analyze what the user really wants to know and infer related topics
        """
        # Use conversation context to better understand intent
        context_info = ""
        if self.conversation_context:
            recent_context = self.conversation_context[-2:]  # Last 2 exchanges
            context_info = f"Recent conversation context: {recent_context}"
        
        intent_prompt = f"""Analyze this TradeUP customer question and infer what they really want to know:

{context_info}

Current question: "{query}"

Provide a JSON response with:
1. "main_intent": What they're primarily asking about
2. "related_concerns": What they might also be worried about or need to know
3. "likely_follow_ups": Questions they'll probably ask next
4. "user_situation": Infer their likely situation (new customer, existing trader, etc.)
5. "comprehensive_topics": All FAQ topics that might be relevant to fully address their needs

Return only valid JSON."""

        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": intent_prompt}],
                temperature=0.3,
                max_tokens=400
            )
            
            intent_analysis = json.loads(response.choices[0].message.content)
            logger.info(f"Intent analysis: {intent_analysis.get('main_intent', 'unknown')}")
            return intent_analysis
            
        except Exception as e:
            logger.warning(f"Intent analysis failed: {e}")
            return {
                "main_intent": query,
                "related_concerns": [],
                "likely_follow_ups": [],
                "user_situation": "customer",
                "comprehensive_topics": []
            }
    
    def generate_enhanced_queries(self, query: str, intent_analysis: Dict[str, Any]) -> List[str]:
        """
        Generate search queries that match actual FAQ content more closely
        """
        # Start with the original query
        queries = [query]
        
        # Add common FAQ patterns for better matching
        lower_query = query.lower()
        
        # Add more specific FAQ-matching queries for common intents
        if any(word in lower_query for word in ['start', 'begin', 'invest', 'new']):
            queries.extend([
                "what do I need to open an account",  # Exact FAQ match
                "account opening requirements",
                "open account",
                "account requirements", 
                "new account",
                "account types",
                "funding account",
                "deposit money"
            ])
        
        if any(word in lower_query for word in ['account', 'open']):
            queries.extend([
                "what do I need to open an account",
                "account opening requirements",
                "how long does approval take",
                "account types available",
                "documents needed"
            ])
        
        if any(word in lower_query for word in ['trade', 'trading']):
            queries.extend([
                "trading features",
                "account types",
                "cash account",
                "margin account",
                "trading permissions"
            ])
        
        if any(word in lower_query for word in ['option', 'options']):
            queries.extend([
                "option trading",
                "trading options",
                "options permissions",
                "margin account"
            ])
        
        if any(word in lower_query for word in ['fund', 'deposit', 'money']):
            queries.extend([
                "funding",
                "deposit",
                "withdrawal",
                "transfer money"
            ])
        
        # Remove duplicates while preserving order
        unique_queries = []
        seen = set()
        for q in queries:
            if q.lower() not in seen:
                unique_queries.append(q)
                seen.add(q.lower())
        
        logger.info(f"Generated {len(unique_queries)} search queries: {unique_queries[:5]}...")
        return unique_queries[:8]  # Limit to 8 queries
    
    def retrieve_comprehensive_faq_content(self, queries: List[str]) -> List[Document]:
        """
        Retrieve comprehensive FAQ content using multiple search strategies with detailed logging
        """
        all_docs = []
        seen_content = set()
        
        logger.info(f"Searching with {len(queries)} queries: {queries}")
        
        # Search with each enhanced query
        for i, query in enumerate(queries):
            try:
                docs_with_scores = self.vectorstore.similarity_search_with_score(query, k=self.top_k)
                
                logger.info(f"Query {i+1} '{query}': found {len(docs_with_scores)} potential matches")
                
                for doc, score in docs_with_scores:
                    similarity = 1 - score
                    category = doc.metadata.get('category_name', 'Unknown')
                    question = doc.metadata.get('question', 'No question')
                    
                    logger.debug(f"  Score: {similarity:.3f} | {category} | {question[:50]}...")
                    
                    if similarity >= self.similarity_threshold:
                        content_hash = hash(doc.page_content)
                        if content_hash not in seen_content:
                            doc.metadata['retrieval_score'] = similarity
                            doc.metadata['retrieval_query'] = query
                            all_docs.append(doc)
                            seen_content.add(content_hash)
                            logger.info(f"  ✓ Added: {similarity:.3f} | {category} | {question[:50]}...")
                
            except Exception as e:
                logger.warning(f"Retrieval failed for query '{query}': {e}")
        
        # Sort by relevance
        all_docs.sort(key=lambda x: x.metadata.get('retrieval_score', 0), reverse=True)
        
        # Remove duplicates while preserving order
        unique_docs = []
        seen_questions = set()
        
        for doc in all_docs:
            question = doc.metadata.get('question', '')
            if question and question not in seen_questions:
                unique_docs.append(doc)
                seen_questions.add(question)
            elif not question:  # Keep docs without questions (shouldn't happen but safety)
                unique_docs.append(doc)
        
        # Filter out obviously irrelevant results for investment/account opening queries
        filtered_docs = []
        lower_query = ' '.join(queries).lower()
        is_investment_query = any(word in lower_query for word in ['invest', 'start', 'begin', 'new', 'open'])
        
        for doc in unique_docs:
            question = doc.metadata.get('question', '').lower()
            category = doc.metadata.get('category_name', '').lower()
            
            # Filter out cancellation/closure topics for investment queries
            if is_investment_query and any(word in question for word in ['cancel', 'close', 'delete', 'remove']):
                logger.info(f"Filtered out irrelevant: {doc.metadata.get('question', '')}")
                continue
            
            filtered_docs.append(doc)
        
        # Take top results after filtering
        if len(filtered_docs) >= 3:
            selected_docs = filtered_docs[:self.top_k]
        elif len(filtered_docs) >= 1:
            selected_docs = filtered_docs
        else:
            # Fallback to unfiltered if filtering removed everything
            selected_docs = unique_docs[:self.top_k]
        
        categories_found = set(doc.metadata.get('category_name', 'Unknown') for doc in selected_docs)
        logger.info(f"Final result: {len(selected_docs)} documents from {len(categories_found)} categories: {list(categories_found)}")
        
        return selected_docs
    
    def verify_response_accuracy(self, response: str, documents: List[Document]) -> str:
        """
        Verify response accuracy - remove external info but KEEP helpful FAQ details
        """
        # Extract all FAQ content for verification
        faq_content = "\n".join([doc.page_content for doc in documents])
        
        verification_prompt = f"""You are a balanced fact-checker. Your job is to ensure the response only uses information from the FAQ sources, but KEEP all helpful details that ARE actually in the FAQs.

RESPONSE TO CHECK:
{response}

FAQ SOURCES:
{faq_content}

CRITICAL BALANCE:
 KEEP information that IS in the FAQ sources:
- Specific numbers, percentages, dollar amounts that appear in FAQs
- Step-by-step instructions that are explicitly provided in FAQs
- UI navigation paths that are mentioned in FAQs
- Specific features, programs, or procedures described in FAQs
- Exact timeframes, requirements, or processes stated in FAQs

 REMOVE information that is NOT in the FAQ sources:
- External knowledge not mentioned in FAQs
- Made-up steps or processes not in FAQs
- Assumptions about features not explicitly described
- Links or URLs not provided in FAQs
- Details that contradict FAQ information

 GUIDELINES:
1. If FAQ says "go to Profile > Deposit > ACH" → KEEP this exact instruction
2. If FAQ says "up to 4x leverage" → KEEP this specific number
3. If FAQ says "$2,000 minimum" → KEEP this specific amount
4. If FAQ gives step-by-step process → KEEP the actual steps
5. Only say "contact customer service" if FAQ truly lacks the information
6. Don't make responses less helpful by removing FAQ details that exist

TASK: If the response removes helpful information that IS actually in the FAQ sources, provide a corrected version that includes the FAQ details. If the response correctly uses only FAQ information (including helpful specifics), return "RESPONSE_ACCURATE".

RESULT:"""

        try:
            verification = self.client.chat.completions.create(
                model="gpt-4o",  # Use best model for verification
                messages=[{"role": "user", "content": verification_prompt}],
                temperature=0.0,  # Zero temperature for maximum accuracy
                max_tokens=1200
            )
            
            result = verification.choices[0].message.content.strip()
            
            if result == "RESPONSE_ACCURATE":
                logger.info("Response verified as appropriately using FAQ information")
                return response
            else:
                logger.info("Response was overly conservative, restored helpful FAQ details")
                return result
                
        except Exception as e:
            logger.warning(f"Response verification failed: {e}")
            # Fallback: return original response since we want to be less conservative
            return response
    
    def _create_conservative_fallback(self, documents: List[Document]) -> str:
        """
        Create an ultra-conservative response using only FAQ content
        """
        if not documents:
            return "I don't have specific FAQ information to answer your question. Please contact TradeUP customer service for detailed assistance."
        
        conservative_response = "Based on our FAQ information:\n\n"
        
        # Just summarize what's in the FAQs very conservatively
        categories = set()
        for doc in documents:
            category = doc.metadata.get('category_name', 'General')
            categories.add(category)
        
        conservative_response += f"I found information in our FAQ database covering: {', '.join(categories)}.\n\n"
        conservative_response += "However, to ensure accuracy and provide you with the most current specific details, requirements, and procedures, I recommend contacting TradeUP customer service directly.\n\n"
        conservative_response += "They can provide:\n"
        conservative_response += "• Specific account requirements and procedures\n"
        conservative_response += "• Current fees and features\n" 
        conservative_response += "• Step-by-step guidance for your situation\n"
        conservative_response += "• Access to the most up-to-date information"
        
        return conservative_response
    
    def generate_intelligent_faq_response(self, query: str, documents: List[Document], intent_analysis: Dict[str, Any]) -> str:
        """
        Generate an intelligent response that synthesizes FAQ content with smart reasoning
        """
        if not documents:
            return self._generate_no_faq_response(query, intent_analysis)
        
        # Format comprehensive FAQ context
        context_parts = []
        categories_covered = set()
        
        for i, doc in enumerate(documents, 1):
            category = doc.metadata.get("category_name", "General")
            question = doc.metadata.get("question", "")
            score = doc.metadata.get("retrieval_score", 0)
            
            categories_covered.add(category)
            
            context_entry = f"""
FAQ Source {i} - Category: {category} (Relevance: {score:.2f})
FAQ Question: {question}
FAQ Content: {doc.page_content}
"""
            context_parts.append(context_entry.strip())
        
        context = "\n\n" + "="*50 + "\n\n".join(context_parts)
        
        # Create intelligent but conservative system prompt
        system_prompt = f"""You are a TradeUP customer service assistant. You must follow these STRICT RULES:

**CRITICAL**: Every specific detail (numbers, percentages, dollar amounts, UI instructions, feature names) must come directly from the FAQ sources. If a detail is not explicitly stated in the provided FAQs, do not include it. When in doubt, use general language like "leverage options are available" instead of specific ratios.

INTELLIGENCE GUIDELINES:
- **Synthesize Multiple FAQs**: Combine information from the provided FAQ sources into a comprehensive answer
- **Organize Clearly**: Structure your response with headers and clear sections
- **Stay Grounded**: Every fact must come from the FAQ sources provided - no external information
- **Be Helpful**: Anticipate related questions but only using FAQ information available
- **Admit Limitations**: If FAQ information is incomplete, say so and refer to customer service

RESPONSE STRUCTURE:
1. **Direct Answer**: Address their main question using FAQ information
2. **Related FAQ Information**: Include other relevant FAQ details that help answer their broader needs
3. **Process Steps**: If multiple FAQs show a process, organize it step-by-step
4. **Limitations**: If FAQ information is incomplete, acknowledge it and suggest contacting customer service

**CRITICAL**: Do not mention specific fees, URLs, platform features, or services unless they are explicitly stated in the FAQ sources provided. Do not assume or add details not in the FAQs.

CUSTOMER CONTEXT:
- Main Intent: {intent_analysis.get('main_intent', 'general inquiry')}
- Likely Situation: {intent_analysis.get('user_situation', 'customer')}"""

        user_prompt = f"""Customer Question: {query}

TradeUP FAQ Information Available:
{context}

Categories Covered: {', '.join(categories_covered)}

Please provide an intelligent, comprehensive response that:
1. Directly answers their question using FAQ information
2. Synthesizes information from multiple FAQ sources when relevant
3. Anticipates related concerns and questions they might have
4. Provides clear, actionable guidance
5. Organizes complex information in an easy-to-follow way

Response:"""

        try:
            response = self.client.chat.completions.create(
                model=self.chat_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.2,  # Very low temperature for consistency and accuracy
                max_tokens=1000   # Shorter responses to encourage conciseness
            )
            
            initial_response = response.choices[0].message.content
            
            # Verify response accuracy against FAQ sources
            verified_response = self.verify_response_accuracy(initial_response, documents)
            
            return verified_response
            
        except Exception as e:
            logger.error(f"Response generation failed: {str(e)}")
            return "I apologize, but I'm experiencing technical difficulties. Please contact TradeUP customer service for assistance."
    
    def _generate_no_faq_response(self, query: str, intent_analysis: Dict[str, Any]) -> str:
        """
        Generate an intelligent response when no relevant FAQ information is found
        """
        suggested_topics = intent_analysis.get('comprehensive_topics', [])
        related_concerns = intent_analysis.get('related_concerns', [])
        
        response = f"""I understand you're asking about "{query}". While I don't have specific FAQ information that directly addresses this topic, I can help guide you to the right resources.

**For immediate assistance with this specific question:**
📞 **Contact TradeUP Customer Service** - They have access to the most current information and can provide personalized guidance for your situation.

**Related topics you might find helpful:**"""

        if suggested_topics:
            response += "\n" + "\n".join([f"• {topic}" for topic in suggested_topics[:5]])
        
        if related_concerns:
            response += f"\n\n**You might also be interested in:**\n"
            response += "\n".join([f"• {concern}" for concern in related_concerns[:3]])
        
        response += f"\n\n**Available FAQ categories:**\n"
        if self.metadata and 'categories' in self.metadata:
            categories = self.metadata['categories'][:8]  # Show first 8
            response += "\n".join([f"• {cat}" for cat in categories])
            if len(self.metadata['categories']) > 8:
                response += f"\n• And {len(self.metadata['categories']) - 8} more categories..."
        
        response += "\n\nFeel free to ask about any of these topics, and I'll provide detailed information from our FAQ database!"
        
        return response
    
    def generate_suggested_questions(self, query: str, documents: List[Document], intent_analysis: Dict[str, Any]) -> List[str]:
        """
        Generate intelligent follow-up questions based on the current query and FAQ content
        """
        # Get categories from retrieved documents
        categories_found = set(doc.metadata.get('category_name', '') for doc in documents)
        
        # Base suggestions on intent and categories
        suggestions = []
        
        # Intent-based suggestions
        main_intent = intent_analysis.get('main_intent', '').lower()
        
        if any(word in main_intent for word in ['account', 'open', 'start', 'begin']):
            suggestions.extend([
                "How long does account approval take?",
                "What documents do I need to provide?",
                "What are the different account types?",
                "How do I fund my account?",
                "Are there any account fees?"
            ])
        
        if any(word in main_intent for word in ['trading', 'trade', 'buy', 'sell']):
            suggestions.extend([
                "What are the different order types?",
                "Can I trade during extended hours?",
                "What is the difference between cash and margin accounts?",
                "How do I place my first trade?",
                "What are the trading fees?"
            ])
        
        if any(word in main_intent for word in ['option', 'options']):
            suggestions.extend([
                "What are the requirements to trade options?",
                "How do I upgrade my options trading level?",
                "What happens to options on expiration day?",
                "Can I use margin to buy options?"
            ])
        
        if any(word in main_intent for word in ['fund', 'deposit', 'money']):
            suggestions.extend([
                "How long does it take for funds to be available?",
                "What are the deposit methods?",
                "Why are my funds not available to withdraw?",
                "How do I withdraw money?"
            ])
        
        if any(word in main_intent for word in ['margin', 'leverage']):
            suggestions.extend([
                "What are the benefits and risks of margin?",
                "How do I upgrade to a margin account?",
                "What is a margin call?",
                "Can I day trade with a margin account?"
            ])
        
        if any(word in main_intent for word in ['day trade', 'day trading']):
            suggestions.extend([
                "What is a Pattern Day Trader (PDT)?",
                "How many day trades can I make?",
                "What happens if I exceed day trading limits?",
                "What account balance do I need for day trading?"
            ])
        
        # Category-based suggestions
        for category in categories_found:
            if 'New Accounts' in category:
                suggestions.extend([
                    "How do I update my account information?",
                    "What is a Trusted Contact Person?",
                    "Where can I see account agreements?"
                ])
            
            elif 'Funding' in category:
                suggestions.extend([
                    "How do I transfer assets from another broker?",
                    "What is an ACH reversal?",
                    "How do I check my deposit history?"
                ])
            
            elif 'Margin' in category:
                suggestions.extend([
                    "What is the maintenance margin requirement?",
                    "How do I cover a margin call?",
                    "Why can't I sell short?"
                ])
            
            elif 'Option' in category:
                suggestions.extend([
                    "When will my options trade settle?",
                    "What are call and put options?",
                    "How do I place a multi-leg options order?"
                ])
        
        # Remove duplicates and limit to 5 suggestions
        unique_suggestions = []
        seen = set()
        for suggestion in suggestions:
            if suggestion.lower() not in seen and suggestion.lower() != query.lower():
                unique_suggestions.append(suggestion)
                seen.add(suggestion.lower())
                if len(unique_suggestions) >= 5:
                    break
        
        # If we don't have enough suggestions, add some general ones
        if len(unique_suggestions) < 3:
            general_suggestions = [
                "What account types are available?",
                "How do I contact customer service?",
                "What are the trading hours?",
                "How do I place my first order?",
                "What fees does TradeUP charge?"
            ]
            
            for suggestion in general_suggestions:
                if suggestion not in unique_suggestions and len(unique_suggestions) < 5:
                    unique_suggestions.append(suggestion)
        
        logger.info(f"Generated {len(unique_suggestions)} suggested questions")
        return unique_suggestions[:5]  # Maximum 5 suggestions
    
    def get_smart_response(self, query: str) -> Dict[str, Any]:
        """
        Complete smart FAQ pipeline with intent analysis and intelligent synthesis
        """
        logger.info(f"Processing smart FAQ query: {query}")
        
        # Step 1: Analyze user intent and infer comprehensive needs
        intent_analysis = self.analyze_user_intent(query)
        
        # Step 2: Generate enhanced search queries based on intent
        enhanced_queries = self.generate_enhanced_queries(query, intent_analysis)
        
        # Step 3: Retrieve comprehensive FAQ content
        documents = self.retrieve_comprehensive_faq_content(enhanced_queries)
        
        # Step 4: Generate intelligent response with FAQ synthesis
        response = self.generate_intelligent_faq_response(query, documents, intent_analysis)
        
        # Step 5: Generate intelligent suggested questions
        suggested_questions = self.generate_suggested_questions(query, documents, intent_analysis)
        
        # Step 6: Update conversation context for better future inference
        self.conversation_context.append({
            "query": query,
            "intent": intent_analysis,
            "response_preview": response[:200] + "..." if len(response) > 200 else response
        })
        
        # Keep only last 5 conversations for context
        if len(self.conversation_context) > 5:
            self.conversation_context = self.conversation_context[-5:]
        
        return {
            "query": query,
            "response": response,
            "intent_analysis": intent_analysis,
            "enhanced_queries": enhanced_queries,
            "num_sources": len(documents),
            "sources": [
                {
                    "category": doc.metadata.get("category_name", "Unknown"),
                    "question": doc.metadata.get("question", ""),
                    "relevance_score": round(doc.metadata.get("retrieval_score", 0), 3),
                    "preview": doc.page_content[:150] + "..." if len(doc.page_content) > 150 else doc.page_content
                }
                for doc in documents
            ],
            "has_faq_content": len(documents) > 0,
            "categories_used": list(set(doc.metadata.get("category_name", "Unknown") for doc in documents)),
            "suggested_questions": suggested_questions
        }
    
    def debug_search_process(self, query: str):
        """
        Debug the entire search process to identify issues
        """
        print(f"\n DEBUG: Full search process for '{query}'")
        print("="*60)
        
        # Step 1: Intent analysis
        print("1. INTENT ANALYSIS:")
        intent_analysis = self.analyze_user_intent(query)
        for key, value in intent_analysis.items():
            print(f"   {key}: {value}")
        
        # Step 2: Query enhancement  
        print("\n2. QUERY ENHANCEMENT:")
        enhanced_queries = self.generate_enhanced_queries(query, intent_analysis)
        for i, eq in enumerate(enhanced_queries, 1):
            print(f"   {i}. '{eq}'")
        
        # Step 3: Test each query with different thresholds
        print("\n3. RETRIEVAL TESTING:")
        thresholds = [0.1, 0.2, 0.3, 0.4, 0.5]
        
        for threshold in thresholds:
            total_matches = 0
            print(f"\n   Threshold {threshold}:")
            
            for eq in enhanced_queries[:3]:  # Test first 3 queries
                try:
                    docs_with_scores = self.vectorstore.similarity_search_with_score(eq, k=5)
                    matches = [(doc, score) for doc, score in docs_with_scores if (1-score) >= threshold]
                    total_matches += len(matches)
                    
                    if matches:
                        print(f"     '{eq}': {len(matches)} matches")
                        for doc, score in matches[:2]:  # Show top 2
                            similarity = 1 - score
                            category = doc.metadata.get('category_name', 'Unknown')
                            question = doc.metadata.get('question', 'No question')
                            print(f"       {similarity:.3f} | {category} | {question[:60]}...")
                except Exception as e:
                    print(f"       Error with '{eq}': {e}")
            
            print(f"     TOTAL: {total_matches} matches at threshold {threshold}")
        
        # Step 4: Show what would be returned
        print(f"\n4. ACTUAL RETRIEVAL (threshold {self.similarity_threshold}):")
        documents = self.retrieve_comprehensive_faq_content(enhanced_queries)
        print(f"   Found {len(documents)} documents:")
        for i, doc in enumerate(documents, 1):
            category = doc.metadata.get('category_name', 'Unknown')
            question = doc.metadata.get('question', 'No question')
            score = doc.metadata.get('retrieval_score', 0)
            print(f"   {i}. {score:.3f} | {category} | {question}")
        
        print("="*60)
        return documents
    
    def interactive_smart_chat(self):
        """Smart FAQ interactive chat with intelligent inference"""
        print("\n" + "="*70)
        print(" TradeUP Smart FAQ Assistant")
        print("="*70)
        print("I'm your intelligent FAQ assistant! I can:")
        print("   Understand what you really want to know")
        print("   Find comprehensive information from our FAQ database")
        print("   Combine multiple FAQ sources intelligently")
        print("   Anticipate your related questions and concerns")
        print("   Provide structured, actionable guidance")
        print("\nCommands:")
        print("  • 'quit/exit/bye' - End conversation")
        print("  • 'stats' - System information")
        print("  • 'topics' - Available FAQ categories")
        print("  • 'context' - Show conversation context")
        print("  • 'debug [question]' - Debug search process")
        print("  • Just type a number (1-5) to ask a suggested question")
        print("="*70 + "\n")
        
        # Track suggested questions for easy access
        self.current_suggestions = []
        
        while True:
            try:
                user_input = input("You: ").strip()
                
                if user_input.lower() in ['quit', 'exit', 'bye', 'q']:
                    print("\n Thank you for using TradeUP Smart FAQ Assistant!")
                    print("Your intelligent assistant for comprehensive TradeUP guidance! 📚✨")
                    break
                
                if user_input.lower() == 'stats':
                    self._print_smart_stats()
                    continue
                
                if user_input.lower() == 'topics':
                    self._print_faq_topics()
                    continue
                
                if user_input.lower() == 'context':
                    self._print_conversation_context()
                    continue
                
                if user_input.lower().startswith('debug '):
                    debug_query = user_input[6:].strip()
                    if debug_query:
                        self.debug_search_process(debug_query)
                    else:
                        print("Usage: debug [your question]")
                    continue
                
                # Check if user selected a suggested question by number
                if user_input.isdigit() and self.current_suggestions:
                    try:
                        suggestion_index = int(user_input) - 1
                        if 0 <= suggestion_index < len(self.current_suggestions):
                            user_input = self.current_suggestions[suggestion_index]
                            print(f" You selected: {user_input}")
                        else:
                            print(f"Please enter a number between 1 and {len(self.current_suggestions)}")
                            continue
                    except ValueError:
                        pass
                
                if not user_input:
                    continue
                
                print("\n Smart Assistant: Analyzing your needs and searching comprehensively...")
                result = self.get_smart_response(user_input)
                
                print(f"\n TradeUP Smart Assistant:")
                print(f"{result['response']}")
                
                # Show intelligent analysis info
                intent = result['intent_analysis']
                print(f"\n Smart Analysis:")
                print(f"    Main Intent: {intent.get('main_intent', 'General inquiry')}")
                print(f"    Sources Used: {result['num_sources']} FAQ entries from {len(result['categories_used'])} categories")
                if result['categories_used']:
                    print(f"    Categories: {', '.join(result['categories_used'])}")
                
                # Show suggested follow-up questions
                if result['suggested_questions']:
                    print(f"\n You might also want to ask:")
                    self.current_suggestions = result['suggested_questions']
                    for i, suggestion in enumerate(result['suggested_questions'], 1):
                        print(f"   {i}. {suggestion}")
                    print(f"\n    Tip: Type a number (1-{len(result['suggested_questions'])}) to ask that question!")
                else:
                    self.current_suggestions = []
                
                print("\n" + "-"*70 + "\n")
                
            except KeyboardInterrupt:
                print("\n\n Chat interrupted. Goodbye!")
                break
            except Exception as e:
                print(f"\n Error: {str(e)}")
                print("Please try again.\n")
    
    def _print_smart_stats(self):
        """Print smart system statistics"""
        print("\n Smart FAQ System Statistics:")
        print("="*50)
        
        if self.metadata:
            for key, value in self.metadata.items():
                print(f"{key}: {value}")
        
        print(f"\nSmart Features:")
        print(f"   Intent Analysis:  Active")
        print(f"   Comprehensive Search:  Active")
        print(f"   Multi-source Synthesis:  Active")
        print(f"   Proactive Suggestions:  Active")
        print(f"   Suggested Questions:  Active")
        print(f"   Conversation Context: {len(self.conversation_context)} exchanges")
        print(f"   Similarity Threshold: {self.similarity_threshold}")
        print(f"   AI Model: {self.chat_model}")
        print("="*50 + "\n")
    
    def _print_faq_topics(self):
        """Print available FAQ categories"""
        if self.metadata and 'categories' in self.metadata:
            print("\n📚 Available FAQ Categories:")
            print("="*40)
            for i, category in enumerate(self.metadata['categories'], 1):
                print(f"  {i:2d}. {category}")
            print("\nI can intelligently combine information from multiple categories")
            print("to give you comprehensive answers!")
            print("="*40 + "\n")
        else:
            print("\n📚 FAQ categories information not available.\n")
    
    def _print_conversation_context(self):
        """Print conversation context for debugging"""
        if not self.conversation_context:
            print("\n📝 No conversation context yet.\n")
            return
        
        print(f"\n Conversation Context ({len(self.conversation_context)} exchanges):")
        print("="*50)
        for i, ctx in enumerate(self.conversation_context, 1):
            print(f"{i}. Q: {ctx['query']}")
            print(f"   Intent: {ctx['intent'].get('main_intent', 'unknown')}")
            print(f"   Response: {ctx['response_preview']}")
            print()
        print("="*50 + "\n")


def main():
    """Main function to run the Smart FAQ system"""
    
    try:
        print("🚀 Initializing TradeUP Smart FAQ Assistant...")
        
        # Initialize Smart FAQ system
        smart_faq = SmartFAQSystem()
        
        print(" Smart FAQ Assistant ready!")
        print(" Enhanced with intelligent inference and comprehensive synthesis")
        print(" Now featuring intelligent suggested questions!")
        print(" Improved retrieval and conservative FAQ-based responses")
        print(" Use 'debug [question]' to troubleshoot search issues")
        print(" Type numbers (1-5) to quickly ask suggested questions")
        
        # Start smart interactive chat
        smart_faq.interactive_smart_chat()
        
    except Exception as e:
        logger.error(f"Smart FAQ system failed: {str(e)}")
        print(f" Error: {str(e)}")


if __name__ == "__main__":
    main()