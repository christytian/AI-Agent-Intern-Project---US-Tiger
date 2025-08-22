# memory_agent.py - Simple Memory Agent for your existing FAQ system
from typing import Dict, List, Any, Optional
from langchain.memory import ConversationBufferWindowMemory
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, AIMessage
import json
from datetime import datetime
import os

# Import your existing FAQ system
from smarter_faq_rag import SmartFAQSystem

class MemoryEnabledFAQ:
    def __init__(self, memory_window: int = 10):
        """
        Initialize Memory-Enabled FAQ Agent
        
        Args:
            memory_window: Number of previous Q&A pairs to remember (default: 10)
        """
        print("Initializing Memory-Enabled FAQ Agent...")
        
        # Initialize your existing FAQ system
        self.faq_system = SmartFAQSystem()
        
        # Initialize LLM for context enhancement
        self.llm = ChatOpenAI(
            model="gpt-4",
            temperature=0.1,
            openai_api_key=os.getenv('OPENAI_API_KEY')
        )
        
        # Create conversation memory
        self.memory = ConversationBufferWindowMemory(
            memory_key="chat_history",
            return_messages=True,
            k=memory_window  # Remember last N exchanges
        )
        
        # Store session metadata
        self.session_start = datetime.now()
        self.total_questions = 0
        
        print(f"Memory-Enabled FAQ Agent initialized (memory window: {memory_window})")
    
    def _get_conversation_context(self) -> str:
        """Get conversation history as context string"""
        messages = self.memory.chat_memory.messages
        if not messages:
            return ""
        
        context_parts = []
        for i in range(0, len(messages), 2):  # Process in Q&A pairs
            if i + 1 < len(messages):
                human_msg = messages[i]
                ai_msg = messages[i + 1]
                context_parts.append(f"Previous Q: {human_msg.content}")
                context_parts.append(f"Previous A: {ai_msg.content[:200]}...")  # Truncate long answers
        
        if context_parts:
            return "CONVERSATION HISTORY:\n" + "\n".join(context_parts[-6:]) + "\n\nCURRENT QUESTION:\n"
        return ""
    
    def _enhance_query_with_context(self, current_question: str) -> str:
        """Enhance current question with conversation context"""
        context = self._get_conversation_context()
        if not context:
            return current_question
        
        # Create enhanced prompt for better context understanding
        enhanced_prompt = f"""{context}{current_question}

Based on the conversation history above, please answer the current question. If the current question refers to something mentioned earlier (like "that", "it", "the account I mentioned"), use the context to understand what the user is referring to."""

        return enhanced_prompt
    
    def ask_question(self, question: str, user_id: str = None) -> Dict[str, Any]:
        """
        Ask a question with memory context
        
        Args:
            question: User's question
            user_id: Optional user identifier for tracking
            
        Returns:
            Dict with response and memory information
        """
        try:
            print(f"Memory FAQ Question: {question}")
            self.total_questions += 1
            
            # Get conversation context
            conversation_context = self._get_conversation_context()
            has_context = bool(conversation_context.strip())
            
            # Enhance query with context if we have conversation history
            if has_context:
                enhanced_question = self._enhance_query_with_context(question)
                print(f"Enhanced with context: {len(conversation_context)} chars of history")
            else:
                enhanced_question = question
                print("No previous context - first question")
            
            # Get response from your existing FAQ system
            faq_result = self.faq_system.get_smart_response(enhanced_question)
            
            # Store in memory
            self.memory.chat_memory.add_user_message(question)  # Store original question
            self.memory.chat_memory.add_ai_message(faq_result['response'])
            
            # Prepare response
            response_data = {
                'success': True,
                'response': faq_result['response'],
                'original_question': question,
                'enhanced_with_context': has_context,
                'conversation_length': len(self.memory.chat_memory.messages) // 2,
                'session_questions': self.total_questions,
                'memory_info': {
                    'has_conversation_history': has_context,
                    'memory_window_size': self.memory.k,
                    'current_memory_items': len(self.memory.chat_memory.messages),
                    'context_characters': len(conversation_context) if has_context else 0
                },
                # Include original FAQ system data
                'intent': faq_result['intent_analysis'].get('main_intent', 'General inquiry'),
                'sources_count': int(faq_result['num_sources']),
                'categories': faq_result['categories_used'],
                'suggested_questions': faq_result.get('suggested_questions', []),
                'sources': [self._convert_numpy_types(source) for source in faq_result['sources'][:3]]
            }
            
            print(f"Response generated (conversation length: {response_data['conversation_length']})")
            return response_data
            
        except Exception as e:
            print(f"Error in memory FAQ: {e}")
            
            # Fallback to regular FAQ if memory processing fails
            try:
                fallback_result = self.faq_system.get_smart_response(question)
                return {
                    'success': True,
                    'response': fallback_result['response'],
                    'fallback_mode': True,
                    'memory_error': str(e),
                    'conversation_length': 0
                }
            except Exception as fallback_error:
                return {
                    'success': False,
                    'error': f'Memory FAQ error: {str(e)}, Fallback error: {str(fallback_error)}'
                }
    
    def _convert_numpy_types(self, obj):
        """Convert numpy types to Python native types for JSON serialization"""
        import numpy as np
        
        if isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, dict):
            return {key: self._convert_numpy_types(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_numpy_types(item) for item in obj]
        return obj
    
    def get_conversation_history(self) -> List[Dict[str, Any]]:
        """Get formatted conversation history"""
        messages = self.memory.chat_memory.messages
        history = []
        
        for i in range(0, len(messages), 2):
            if i + 1 < len(messages):
                question_msg = messages[i]
                answer_msg = messages[i + 1]
                
                history.append({
                    'question_number': (i // 2) + 1,
                    'question': question_msg.content,
                    'answer': answer_msg.content,
                    'timestamp': datetime.now().isoformat(),  # You could store actual timestamps
                    'answer_length': len(answer_msg.content)
                })
        
        return history
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """Get memory and session statistics"""
        messages = self.memory.chat_memory.messages
        
        return {
            'session_start': self.session_start.isoformat(),
            'session_duration_minutes': (datetime.now() - self.session_start).total_seconds() / 60,
            'total_questions_asked': self.total_questions,
            'conversation_pairs_in_memory': len(messages) // 2,
            'memory_window_size': self.memory.k,
            'memory_utilization': f"{(len(messages) // 2)}/{self.memory.k}",
            'memory_full': (len(messages) // 2) >= self.memory.k,
            'last_question_time': datetime.now().isoformat() if messages else None
        }
    
    def clear_memory(self) -> Dict[str, str]:
        """Clear conversation memory"""
        conversation_count = len(self.memory.chat_memory.messages) // 2
        self.memory.clear()
        
        return {
            'status': 'success',
            'message': f'Cleared {conversation_count} conversation pairs from memory',
            'new_session_start': datetime.now().isoformat()
        }
    
    def set_memory_window(self, new_window_size: int) -> Dict[str, Any]:
        """Change memory window size"""
        old_size = self.memory.k
        self.memory.k = new_window_size
        
        # Trim memory if new window is smaller
        messages = self.memory.chat_memory.messages
        if len(messages) > new_window_size * 2:
            # Keep only the most recent conversations
            recent_messages = messages[-(new_window_size * 2):]
            self.memory.chat_memory.clear()
            for msg in recent_messages:
                if isinstance(msg, HumanMessage):
                    self.memory.chat_memory.add_user_message(msg.content)
                elif isinstance(msg, AIMessage):
                    self.memory.chat_memory.add_ai_message(msg.content)
        
        return {
            'status': 'success',
            'old_window_size': old_size,
            'new_window_size': new_window_size,
            'conversations_retained': len(self.memory.chat_memory.messages) // 2
        }

# Example usage and testing
if __name__ == "__main__":
    # Initialize the memory-enabled FAQ
    memory_faq = MemoryEnabledFAQ(memory_window=5)
    
    # Test conversation with memory
    test_conversation = [
        "How do I open a trading account?",
        "What documents do I need for that?", 
        "How long does the approval process take?",
        "What about margin accounts?",
        "Can I upgrade the account I mentioned earlier to margin?"
    ]
    
    print("Testing Memory-Enabled FAQ with conversation flow...")
    print("=" * 60)
    
    for i, question in enumerate(test_conversation, 1):
        print(f"\nQ{i}: {question}")
        result = memory_faq.ask_question(question)
        
        if result['success']:
            print(f"A{i}: {result['response'][:200]}...")
            print(f"Memory: {result['conversation_length']} pairs, Context: {result['enhanced_with_context']}")
        else:
            print(f"Error: {result['error']}")
    
    print("\n" + "=" * 60)
    print("Final Memory Stats:")
    stats = memory_faq.get_memory_stats()
    for key, value in stats.items():
        print(f"{key}: {value}")
    
    print("\nConversation History:")
    history = memory_faq.get_conversation_history()
    for entry in history:
        print(f"Q{entry['question_number']}: {entry['question']}")
        print(f"A{entry['question_number']}: {entry['answer'][:100]}...")
        print()