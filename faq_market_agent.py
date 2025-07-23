# faq_market_agent.py - AI Agent for FAQ + Market Data (Updated)
import os
from typing import Dict, List, Any, Optional
from langchain.agents import create_openai_functions_agent, AgentExecutor
from langchain.tools import Tool
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.memory import ConversationBufferWindowMemory
import yfinance as yf
import requests
import json
from datetime import datetime, timedelta
import pandas as pd

# Import your UPDATED LLM-powered FAQ system
from optimized_faq_system import LLMPoweredOptimizedFAQSystem

class FAQMarketAgent:
    def __init__(self, memory_window: int = 10):
        """
        Initialize FAQ + Market Data AI Agent with LLM-powered FAQ system
        
        Args:
            memory_window: Number of previous conversations to remember
        """
        print("Initializing FAQ + Market Data AI Agent with LLM-powered FAQ system...")
        
        # Initialize your LLM-powered FAQ system
        self.faq_system = LLMPoweredOptimizedFAQSystem()
        
        # Initialize LLM
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",  # Using faster model for cost efficiency
            temperature=0.1,
            openai_api_key=os.getenv('OPENAI_API_KEY')
        )
        
        # Create conversation memory
        self.memory = ConversationBufferWindowMemory(
            memory_key="chat_history",
            return_messages=True,
            k=memory_window
        )
        
        # Create tools
        self.tools = self._create_tools()
        
        # Create agent prompt
        self.prompt = self._create_agent_prompt()
        
        # Create the agent
        self.agent = create_openai_functions_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=self.prompt
        )
        
        # Create agent executor
        self.agent_executor = AgentExecutor(
            agent=self.agent,
            tools=self.tools,
            memory=self.memory,
            verbose=True,
            max_iterations=3,
            early_stopping_method="generate"
        )
        
        print("FAQ + Market Data AI Agent initialized successfully with LLM-powered FAQ system!")
    
    def _create_tools(self) -> List[Tool]:
        """Create tools for the agent"""
        return [
            Tool(
                name="faq_search",
                description="Search TradeUP FAQ database for answers about trading policies, procedures, account types, fees, and general trading information. Use this for any questions about TradeUP services. Returns intelligent, comprehensive responses.",
                func=self._faq_search_tool
            ),
            Tool(
                name="get_stock_quote",
                description="Get current stock price, daily change, and basic information for any stock symbol (e.g., AAPL, TSLA, GOOGL). Use this when users ask about specific stock prices.",
                func=self._get_stock_quote_tool
            ),
            Tool(
                name="get_market_overview",
                description="Get overall market status and major indices (S&P 500, NASDAQ, Dow Jones). Use this for general market questions.",
                func=self._get_market_overview_tool
            ),
            Tool(
                name="get_stock_news",
                description="Get recent news and information about a specific stock. Use this when users want news about a particular company.",
                func=self._get_stock_news_tool
            ),
            Tool(
                name="search_stock_symbol",
                description="Search for stock symbols by company name. Use this when users mention a company name but not the ticker symbol.",
                func=self._search_stock_symbol_tool
            )
        ]
    
    def _create_agent_prompt(self) -> ChatPromptTemplate:
        """Create the agent prompt template"""
        system_message = """You are a helpful TradeUP assistant that combines LLM-powered FAQ knowledge with real-time market data.

Your capabilities:
1. Answer questions about TradeUP services using the LLM-powered FAQ database (intelligent, comprehensive responses)
2. Provide real-time stock prices and market data
3. Get stock news and company information
4. Help with both trading questions and market information

Guidelines:
- For questions about TradeUP policies, fees, account types, procedures: Use FAQ search (powered by LLM for intelligent responses)
- For stock prices, market data, company info: Use market data tools
- For questions combining both (e.g., "Can I trade Apple stock and what's the price?"): Use both tools
- The FAQ system now provides intelligent, comprehensive responses using LLM technology
- Always be accurate and helpful
- If you can't find information, clearly explain what you can help with
- Provide context and explanations, not just raw data
- Remember the conversation history to provide better responses

When providing market data:
- Always include the timestamp of the data
- Explain any significant movements if relevant
- Provide context for the numbers when helpful

When providing FAQ information:
- The FAQ system now uses LLM intelligence to provide comprehensive answers
- It can synthesize information from multiple FAQ sources
- It provides smart suggestions for related questions
- Be accurate and refer to official TradeUP policies
- If something requires account-specific information, direct them to contact support"""

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_message),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad")
        ])
        
        return prompt
    
    def _faq_search_tool(self, query: str) -> str:
        """Tool wrapper for your LLM-powered FAQ system"""
        try:
            print(f"FAQ Search (LLM-powered): {query}")
            result = self.faq_system.get_smart_response(query)
            
            # Check if this should actually use market agent
            if result.get('use_market_agent', False):
                return f"FAQ System Routing: This question should use market data tools. Reason: {result.get('routing_reason', 'Market data required')}"
            
            # Format the LLM-powered response for the agent
            response = f"LLM-Powered FAQ Response: {result['response']}\n"
            
            # Add metadata about the intelligent response
            if result.get('categories_used'):
                response += f"Categories covered: {', '.join(result['categories_used'])}\n"
            if result.get('sources_count', 0) > 0:
                response += f"FAQ sources synthesized: {result['sources_count']}\n"
            if result.get('from_cache'):
                response += f"Response served from cache (instant)\n"
            else:
                response += f"Generated using LLM intelligence\n"
            
            # Add suggested follow-up questions
            if result.get('suggested_questions'):
                response += f"Related questions users often ask: {', '.join(result['suggested_questions'][:3])}"
            
            return response
        except Exception as e:
            return f"Error in LLM-powered FAQ search: {str(e)}"
    
    def _get_stock_quote_tool(self, symbol: str) -> str:
        """Get real-time stock quote"""
        try:
            print(f"Getting stock quote for: {symbol}")
            symbol = symbol.upper().strip()
            
            # Use yfinance to get stock data
            stock = yf.Ticker(symbol)
            
            # Get current info
            info = stock.info
            
            # Get recent price data
            hist = stock.history(period="1d", interval="1m")
            if hist.empty:
                hist = stock.history(period="5d")
            
            if hist.empty:
                return f"Could not retrieve data for {symbol}. Please check the symbol."
            
            current_price = hist['Close'].iloc[-1]
            prev_close = info.get('previousClose', hist['Close'].iloc[0])
            change = current_price - prev_close
            change_percent = (change / prev_close) * 100
            
            # Format response
            response = f"""{symbol} Stock Quote:
Company: {info.get('longName', symbol)}
Current Price: ${current_price:.2f}
Change: ${change:+.2f} ({change_percent:+.2f}%)
Previous Close: ${prev_close:.2f}
Day Range: ${info.get('dayLow', 'N/A')} - ${info.get('dayHigh', 'N/A')}
Volume: {info.get('volume', 'N/A'):,}
Market Cap: {self._format_market_cap(info.get('marketCap'))}
Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ET"""

            return response
            
        except Exception as e:
            return f"Error retrieving stock quote for {symbol}: {str(e)}"
    
    def _get_market_overview_tool(self, query: str = "") -> str:
        """Get market overview and major indices"""
        try:
            print("Getting market overview...")
            
            # Major indices
            indices = {
                '^GSPC': 'S&P 500',
                '^IXIC': 'NASDAQ',
                '^DJI': 'Dow Jones'
            }
            
            market_data = []
            for symbol, name in indices.items():
                try:
                    ticker = yf.Ticker(symbol)
                    hist = ticker.history(period="2d")
                    if not hist.empty:
                        current = hist['Close'].iloc[-1]
                        prev = hist['Close'].iloc[-2] if len(hist) > 1 else hist['Close'].iloc[0]
                        change = current - prev
                        change_pct = (change / prev) * 100
                        
                        market_data.append(f"{name}: {current:.2f} ({change:+.2f}, {change_pct:+.2f}%)")
                except:
                    market_data.append(f"{name}: Data unavailable")
            
            # Check if market is open
            now = datetime.now()
            is_weekday = now.weekday() < 5
            market_hours = 9 <= now.hour < 16
            market_status = "Open" if is_weekday and market_hours else "Closed"
            
            response = f"""Market Overview ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ET):
Market Status: {market_status}

Major Indices:
{chr(10).join(market_data)}

Trading Hours: 9:30 AM - 4:00 PM ET (Monday-Friday)
Pre-Market: 4:00 AM - 9:30 AM ET
After-Hours: 4:00 PM - 8:00 PM ET"""

            return response
            
        except Exception as e:
            return f"Error retrieving market overview: {str(e)}"
    
    def _get_stock_news_tool(self, symbol: str) -> str:
        """Get recent news for a stock"""
        try:
            print(f"Getting news for: {symbol}")
            symbol = symbol.upper().strip()
            
            stock = yf.Ticker(symbol)
            news = stock.news
            
            if not news:
                return f"No recent news found for {symbol}"
            
            # Format top 3 news items
            news_items = []
            for i, item in enumerate(news[:3], 1):
                title = item.get('title', 'No title')
                published = datetime.fromtimestamp(item.get('providerPublishTime', 0))
                source = item.get('publisher', 'Unknown source')
                
                news_items.append(f"{i}. {title}")
                news_items.append(f"   Source: {source}")
                news_items.append(f"   Published: {published.strftime('%Y-%m-%d %H:%M')}")
                news_items.append("")
            
            response = f"Recent News for {symbol}:\n\n" + "\n".join(news_items)
            return response
            
        except Exception as e:
            return f"Error retrieving news for {symbol}: {str(e)}"
    
    def _search_stock_symbol_tool(self, company_name: str) -> str:
        """Search for stock symbol by company name"""
        try:
            print(f"Searching symbol for: {company_name}")
            
            # Enhanced company name to symbol mappings
            common_symbols = {
                'apple': 'AAPL', 'microsoft': 'MSFT', 'google': 'GOOGL', 'alphabet': 'GOOGL',
                'amazon': 'AMZN', 'tesla': 'TSLA', 'nvidia': 'NVDA', 'meta': 'META',
                'facebook': 'META', 'netflix': 'NFLX', 'adobe': 'ADBE', 'salesforce': 'CRM',
                'oracle': 'ORCL', 'intel': 'INTC', 'amd': 'AMD', 'uber': 'UBER',
                'lyft': 'LYFT', 'airbnb': 'ABNB', 'zoom': 'ZM', 'slack': 'WORK',
                'twitter': 'TWTR', 'snapchat': 'SNAP', 'pinterest': 'PINS',
                'square': 'SQ', 'paypal': 'PYPL', 'visa': 'V', 'mastercard': 'MA',
                'jpmorgan': 'JPM', 'goldman': 'GS', 'morgan stanley': 'MS',
                'bank of america': 'BAC', 'wells fargo': 'WFC', 'coca cola': 'KO',
                'pepsi': 'PEP', 'walmart': 'WMT', 'target': 'TGT', 'costco': 'COST',
                'home depot': 'HD', 'lowes': 'LOW', 'disney': 'DIS', 'boeing': 'BA',
                'caterpillar': 'CAT', 'ge': 'GE', 'general electric': 'GE'
            }
            
            company_lower = company_name.lower().strip()
            
            # Direct match
            if company_lower in common_symbols:
                symbol = common_symbols[company_lower]
                return f"Found symbol for {company_name}: {symbol}"
            
            # Partial match
            for name, symbol in common_symbols.items():
                if name in company_lower or company_lower in name:
                    return f"Found possible match for {company_name}: {symbol} ({name.title()})"
            
            return f"Could not find symbol for '{company_name}'. Please provide the stock ticker symbol directly (e.g., AAPL for Apple)."
            
        except Exception as e:
            return f"Error searching for symbol: {str(e)}"
    
    def _format_market_cap(self, market_cap):
        """Format market cap in readable form"""
        if not market_cap:
            return "N/A"
        
        if market_cap >= 1e12:
            return f"${market_cap/1e12:.2f}T"
        elif market_cap >= 1e9:
            return f"${market_cap/1e9:.2f}B"
        elif market_cap >= 1e6:
            return f"${market_cap/1e6:.2f}M"
        else:
            return f"${market_cap:,.0f}"
    
    def ask_question(self, question: str, user_context: Dict = None) -> Dict[str, Any]:
        """Process user question through the agent"""
        try:
            print(f"Processing question with LLM-powered FAQ backend: {question}")
            
            # Add user context if provided
            if user_context:
                context_str = f"User context: {json.dumps(user_context)}\n\nUser question: {question}"
            else:
                context_str = question
            
            # Execute the agent
            response = self.agent_executor.invoke({
                "input": context_str
            })
            
            # Extract the response
            agent_response = response.get('output', 'I apologize, but I encountered an error processing your request.')
            
            # Get memory for conversation history
            chat_history = self.memory.chat_memory.messages
            
            return {
                'success': True,
                'response': agent_response,
                'agent_type': 'faq_market_agent_llm_powered',
                'tools_available': [tool.name for tool in self.tools],
                'conversation_length': len(chat_history),
                'capabilities': [
                    'LLM-powered TradeUP FAQ search and intelligent responses',
                    'Real-time stock quotes and prices',
                    'Market overview and indices',
                    'Stock news and company information',
                    'Company name to symbol lookup',
                    'Conversation memory and context',
                    'Smart synthesis of multiple FAQ sources',
                    'Intelligent follow-up question suggestions'
                ]
            }
            
        except Exception as e:
            print(f"Error processing request: {e}")
            return {
                'success': False,
                'error': f'Agent processing error: {str(e)}',
                'fallback_response': 'I apologize for the technical difficulty. Please try rephrasing your question.'
            }
    
    def get_conversation_history(self) -> List[Dict]:
        """Get the conversation history"""
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
                    'timestamp': datetime.now().isoformat(),
                    'answer_length': len(answer_msg.content)
                })
        
        return history
    
    def clear_memory(self):
        """Clear conversation memory"""
        self.memory.clear()
        print("Conversation memory cleared")
    
    def get_faq_system_stats(self) -> Dict[str, Any]:
        """Get statistics from the underlying LLM-powered FAQ system"""
        try:
            return {
                'faq_system_type': 'LLMPoweredOptimizedFAQSystem',
                'cache_stats': self.faq_system.get_cache_stats(),
                'llm_powered': True,
                'features': [
                    'LLM intelligence for comprehensive responses',
                    'Response caching for speed',
                    'Smart routing between FAQ and market',
                    'Conversation context',
                    'Multi-source FAQ synthesis'
                ]
            }
        except Exception as e:
            return {'error': f'Could not get FAQ system stats: {str(e)}'}

# Example usage and testing
if __name__ == "__main__":
    # Initialize the agent with LLM-powered FAQ system
    agent = FAQMarketAgent()
    
    # Test questions that combine FAQ and market data
    test_questions = [
        "What are TradeUP's trading fees?",  # Should use LLM-powered FAQ
        "What's the current price of Apple stock?",  # Should use market tools
        "Can I trade options on TradeUP and what's Tesla's stock price?",  # Should use both
        "How do I open an account and what's the market doing today?",  # Should use both
        "What's the news on Microsoft stock?",  # Should use market tools
        "What symbol does Netflix use?",  # Should use market tools
        "How do I fund my account?",  # Should use LLM-powered FAQ
        "What are the margin requirements?"  # Should use LLM-powered FAQ
    ]
    
    print("Testing FAQ + Market Data Agent with LLM-powered FAQ system...")
    print("=" * 70)
    
    for question in test_questions:
        print(f"\nQ: {question}")
        result = agent.ask_question(question)
        if result['success']:
            print(f"A: {result['response']}")
            print(f"System: {result['agent_type']}")
        else:
            print(f"Error: {result['error']}")
        print("-" * 50)
    
    # Show FAQ system stats
    print(f"\nFAQ System Statistics:")
    faq_stats = agent.get_faq_system_stats()
    for key, value in faq_stats.items():
        print(f"  {key}: {value}")