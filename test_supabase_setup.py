# test_supabase_setup.py
import os
from dotenv import load_dotenv
from supabase_memory import OptimalChatbotFAQ  # Import your new class

load_dotenv()

def test_chatbot():
    chatbot = OptimalChatbotFAQ(
        supabase_url=os.getenv('SUPABASE_URL'),
        supabase_key=os.getenv('SUPABASE_ANON_KEY')
    )
    
    # Test conversation
    session_id = chatbot.start_conversation("test_user")
    print(f" Session created: {session_id}")
    
    result = chatbot.ask_question("How do I open an account?")
    if result['success']:
        print(f" Question answered: {result['response'][:100]}...")
    else:
        print(f" Error: {result['error']}")
    
    chatbot.end_conversation()
    print(" Test completed!")

if __name__ == "__main__":
    test_chatbot()