import os
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
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

class FAQOnlyRAGSystem:
    """
    A strict RAG system that ONLY uses information from the FAQ database.
    If no relevant FAQ information is found, it politely declines to answer.
    """
    
    def __init__(self, 
                 vectorstore_path: str = "vectorstore",
                 openai_api_key: Optional[str] = None,
                 embedding_model: str = "text-embedding-3-small",
                 chat_model: str = "gpt-4o",
                 top_k: int = 5,
                 similarity_threshold: float = 0.4,  # Lowered for better matching
                 min_sources_required: int = 1):
        """
        Initialize the FAQ-only RAG system
        """
        self.vectorstore_path = Path(vectorstore_path)
        self.chat_model = chat_model
        self.top_k = top_k
        self.similarity_threshold = similarity_threshold
        self.min_sources_required = min_sources_required
        
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
        
        logger.info("FAQ-Only RAG System initialized - responses limited to FAQ database content")
    
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
    
    def enhance_query_for_faq_search(self, query: str) -> List[str]:
        """
        Generate alternative search queries to better match FAQ content
        """
        enhancement_prompt = f"""Given this user question about TradeUP brokerage services, generate 2-3 alternative search phrases that might match FAQ entries. Focus on:
1. The original question
2. Key terms and synonyms that might appear in FAQ titles
3. More formal/technical phrasing that might be in official documentation

Original question: "{query}"

Return only the search phrases, one per line, without explanations."""

        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": enhancement_prompt}],
                temperature=0.2,
                max_tokens=150
            )
            
            enhanced_queries = [q.strip() for q in response.choices[0].message.content.split('\n') if q.strip()]
            return enhanced_queries[:3]  # Limit to 3 queries
            
        except Exception as e:
            logger.warning(f"Query enhancement failed: {e}")
            return [query]
    
    def retrieve_faq_documents(self, queries: List[str]) -> List[Document]:
        """
        Retrieve documents from FAQ database with strict relevance filtering
        """
        all_docs = []
        seen_content = set()
        
        for query in queries:
            try:
                docs_with_scores = self.vectorstore.similarity_search_with_score(query, k=self.top_k)
                
                for doc, score in docs_with_scores:
                    similarity = 1 - score
                    # Strict threshold - only include highly relevant matches
                    if similarity >= self.similarity_threshold:
                        content_hash = hash(doc.page_content)
                        if content_hash not in seen_content:
                            doc.metadata['retrieval_score'] = similarity
                            doc.metadata['retrieval_query'] = query
                            all_docs.append(doc)
                            seen_content.add(content_hash)
                
            except Exception as e:
                logger.warning(f"Retrieval failed for query '{query}': {e}")
        
        # Sort by relevance and return
        all_docs.sort(key=lambda x: x.metadata.get('retrieval_score', 0), reverse=True)
        final_docs = all_docs[:self.top_k]
        
        logger.info(f"Retrieved {len(final_docs)} relevant FAQ documents")
        return final_docs
    
    def check_sufficient_information(self, documents: List[Document], query: str) -> bool:
        """
        Check if the retrieved FAQ documents contain sufficient information to answer the query
        """
        if len(documents) < self.min_sources_required:
            return False
        
        # Check if the best match meets quality threshold
        if documents:
            best_score = documents[0].metadata.get('retrieval_score', 0)
            if best_score < self.similarity_threshold:
                return False
        
        return True
    
    def generate_faq_based_response(self, query: str, documents: List[Document]) -> str:
        """
        Generate response using ONLY the information from FAQ documents
        """
        # Format FAQ context
        context_parts = []
        for i, doc in enumerate(documents, 1):
            category = doc.metadata.get("category_name", "General")
            question = doc.metadata.get("question", "")
            score = doc.metadata.get("retrieval_score", 0)
            
            context_entry = f"""
FAQ Source {i} - Category: {category} (Relevance: {score:.2f})
FAQ Question: {question}
FAQ Answer: {doc.page_content}
"""
            context_parts.append(context_entry.strip())
        
        context = "\n\n" + "="*50 + "\n\n".join(context_parts)
        
        # Strict system prompt - only use FAQ information
        system_prompt = """You are a customer service representative for TradeUP. You can ONLY answer questions using the information provided from TradeUP's official FAQ database.

STRICT RULES:
1. Use ONLY the information from the FAQ sources provided
2. Do NOT add any information not explicitly stated in the FAQ content
3. Do NOT use general financial knowledge or outside information
4. If the FAQ information doesn't fully answer the question, say so and direct them to customer service
5. Be helpful and professional, but stay strictly within the FAQ content
6. You can synthesize and combine information from multiple FAQ sources if they're all provided
7. Always maintain TradeUP's professional tone

If you cannot fully answer the question with the provided FAQ information, politely explain this limitation."""

        user_prompt = f"""Based ONLY on the following TradeUP FAQ information, please answer this customer question:

Customer Question: {query}

TradeUP FAQ Information:
{context}

Important: Use ONLY the information provided above. If the FAQ content doesn't contain enough information to fully answer the question, please say so and suggest they contact TradeUP customer service.

Response:"""

        try:
            response = self.client.chat.completions.create(
                model=self.chat_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.2,  # Low temperature for consistency
                max_tokens=800
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Response generation failed: {str(e)}")
            return "I apologize, but I'm experiencing technical difficulties. Please contact TradeUP customer service for assistance."
    
    def generate_no_info_response(self, query: str) -> str:
        """
        Generate a polite response when no relevant FAQ information is found
        """
        return f"""I apologize, but I don't have specific information about "{query}" in our FAQ database. 

For accurate and up-to-date information about this topic, I recommend:

📞 **Contact TradeUP Customer Service:**
- They can provide detailed, personalized assistance
- Access to the most current policies and procedures
- Able to address your specific situation

🔍 **You might also want to ask about:**
- Account opening and requirements
- Trading features and fees
- Funding and withdrawal options
- Account types and their differences

Is there anything else from our FAQ topics that I can help you with?"""
    
    def get_faq_response(self, query: str) -> Dict[str, Any]:
        """
        Complete FAQ-only pipeline
        """
        logger.info(f"Processing FAQ-only query: {query}")
        
        # Step 1: Enhance query for better FAQ matching
        enhanced_queries = self.enhance_query_for_faq_search(query)
        
        # Step 2: Retrieve FAQ documents
        documents = self.retrieve_faq_documents(enhanced_queries)
        
        # Step 3: Check if we have sufficient information
        has_sufficient_info = self.check_sufficient_information(documents, query)
        
        if has_sufficient_info:
            # Step 4a: Generate response from FAQ content
            response = self.generate_faq_based_response(query, documents)
            response_type = "faq_based"
            
            sources = [
                {
                    "category": doc.metadata.get("category_name", "Unknown"),
                    "question": doc.metadata.get("question", ""),
                    "relevance_score": round(doc.metadata.get("retrieval_score", 0), 3),
                    "preview": doc.page_content[:150] + "..." if len(doc.page_content) > 150 else doc.page_content
                }
                for doc in documents
            ]
        else:
            # Step 4b: Politely decline and suggest alternatives
            response = self.generate_no_info_response(query)
            response_type = "no_faq_info"
            sources = []
        
        return {
            "query": query,
            "response": response,
            "response_type": response_type,
            "enhanced_queries": enhanced_queries,
            "num_sources": len(documents),
            "sources": sources,
            "has_relevant_faq": has_sufficient_info
        }
    
    def interactive_faq_chat(self):
        """FAQ-only interactive chat"""
        print("\n" + "="*70)
        print("📚 TradeUP FAQ Assistant")
        print("="*70)
        print("I can help you with questions covered in TradeUP's FAQ database.")
        print("For topics not in our FAQ, I'll direct you to our customer service team.")
        print("\nCommands:")
        print("  • 'quit/exit/bye' - End conversation")
        print("  • 'stats' - System information")
        print("  • 'topics' - Show available FAQ categories")
        print("  • 'debug [question]' - Debug search process")
        print("="*70 + "\n")
        
        while True:
            try:
                user_input = input("You: ").strip()
                
                if user_input.lower() in ['quit', 'exit', 'bye', 'q']:
                    print("\n📚 Thank you for using TradeUP FAQ Assistant!")
                    print("For further assistance, please contact our customer service team.")
                    break
                
                if user_input.lower() == 'stats':
                    self._print_faq_stats()
                    continue
                
                if user_input.lower() == 'topics':
                    self._print_faq_topics()
                    continue
                
                if user_input.lower().startswith('debug '):
                    debug_query = user_input[6:].strip()
                    if debug_query:
                        self.debug_search(debug_query)
                    else:
                        print("Usage: debug [your question]")
                    continue
                
                if not user_input:
                    continue
                
                print("\n📚 FAQ Assistant: Searching our database...")
                result = self.get_faq_response(user_input)
                
                print(f"\n📚 TradeUP FAQ Assistant:")
                print(f"{result['response']}")
                
                if result['response_type'] == 'faq_based' and result['sources']:
                    print(f"\n📋 Based on {result['num_sources']} FAQ source(s):")
                    for i, source in enumerate(result['sources'], 1):
                        print(f"   {i}. {source['category']}: {source['question']} (Score: {source['relevance_score']})")
                
                print("\n" + "-"*70 + "\n")
                
            except KeyboardInterrupt:
                print("\n\n📚 Chat interrupted. Goodbye!")
                break
            except Exception as e:
                print(f"\n❌ Error: {str(e)}")
                print("Please try again or contact customer service.\n")
    
    def _print_faq_stats(self):
        """Print FAQ system statistics"""
        print("\n📊 FAQ Assistant Statistics:")
        print("="*50)
        
        if self.metadata:
            for key, value in self.metadata.items():
                print(f"{key}: {value}")
        
        print(f"\nSettings:")
        print(f"  - Similarity threshold: {self.similarity_threshold}")
        print(f"  - Minimum sources required: {self.min_sources_required}")
        print(f"  - Response mode: FAQ-only (no external knowledge)")
        print(f"  - Chat model: {self.chat_model}")
        print("="*50 + "\n")
    
    def debug_search(self, query: str) -> Dict[str, Any]:
        """Debug the search process to see what's happening"""
        print(f"\n🔍 DEBUG: Searching for '{query}'")
        
        # Test different similarity thresholds
        thresholds = [0.3, 0.4, 0.5, 0.6, 0.7]
        
        enhanced_queries = self.enhance_query_for_faq_search(query)
        print(f"Enhanced queries: {enhanced_queries}")
        
        for threshold in thresholds:
            total_docs = 0
            for eq in enhanced_queries:
                docs_with_scores = self.vectorstore.similarity_search_with_score(eq, k=10)
                matching_docs = [(doc, score) for doc, score in docs_with_scores if (1-score) >= threshold]
                total_docs += len(matching_docs)
                
                if matching_docs:
                    print(f"\nThreshold {threshold} - Query: '{eq}'")
                    for doc, score in matching_docs[:3]:
                        similarity = 1 - score
                        question = doc.metadata.get('question', 'No question')
                        print(f"  Score: {similarity:.3f} - {question}")
            
            print(f"Threshold {threshold}: {total_docs} total matches")
        
        return {"enhanced_queries": enhanced_queries}
    
    def _print_faq_topics(self):
        """Print available FAQ categories"""
        if self.metadata and 'categories' in self.metadata:
            print("\n📋 Available FAQ Topics:")
            print("="*40)
            for i, category in enumerate(self.metadata['categories'], 1):
                print(f"  {i}. {category}")
            print("\nTry asking questions related to these topics!")
            print("="*40 + "\n")
        else:
            print("\n📋 FAQ topics information not available.\n")


def main():
    """Main function to run the FAQ-only RAG system"""
    
    # Your specific vectorstore path
    VECTORSTORE_PATH = "/Users/a16463/Desktop/Tiger_Securities/AI-Agent-Intern-Project---US-Tiger/vectorstore"
    
    try:
        print("🚀 Initializing TradeUP FAQ-Only Assistant...")
        
        # Initialize with strict FAQ-only settings and your vectorstore path
        faq_system = FAQOnlyRAGSystem(
            vectorstore_path=VECTORSTORE_PATH,
            chat_model="gpt-4o",
            top_k=5,
            similarity_threshold=0.4,  # Balanced threshold for good matching
            min_sources_required=1
        )
        
        print("✅ FAQ-Only Assistant ready!")
        print("📚 Responses limited to TradeUP FAQ database content only")
        
        # Start FAQ-only interactive chat
        faq_system.interactive_faq_chat()
        
    except Exception as e:
        logger.error(f"FAQ-only RAG system failed: {str(e)}")
        print(f"❌ Error: {str(e)}")
        print(f"Make sure the vectorstore exists at: {VECTORSTORE_PATH}")


if __name__ == "__main__":
    main()