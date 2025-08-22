# TradeUP Enhanced FAQ System

A sophisticated AI-powered customer service FAQ system built with advanced Large Language Model (LLM) technology, providing intelligent responses with conversation memory and comprehensive analytics.

## Overview

The TradeUP Enhanced FAQ System is a production-ready customer service solution that combines multiple AI technologies to deliver contextual, intelligent responses to customer inquiries. The system features persistent conversation memory, user feedback collection, and comprehensive analytics through a modern web interface.

## Key Features

### Core Intelligence
- **Enhanced LLM-Powered Responses**: Advanced question analysis and response generation using GPT-4
- **Smart Conversation Analysis**: LLM-based intent detection and conversation routing
- **Multi-Strategy Search**: Vector search with multiple fallback strategies for optimal accuracy
- **Intelligent Routing**: Automatic routing between FAQ and market data systems
- **Response Optimization**: Intelligent caching and performance optimization

### Memory & Analytics
- **Persistent Conversation Memory**: Full conversation history using Supabase database
- **Session Management**: Automatic session creation and management across app restarts
- **User Feedback System**: Thumbs up/down feedback collection with comprehensive analytics
- **Performance Monitoring**: Real-time system performance and usage statistics

### User Interface
- **Modern Web Interface**: Responsive design with dark/light mode support
- **Interactive API Documentation**: Complete Swagger/OpenAPI documentation
- **Comprehensive Testing Interface**: Built-in API testing tools
- **Real-time Search**: FAQ database search with relevance scoring

## Architecture

### System Components
- **Flask Web Application**: Main application server with RESTful API
- **Supabase Database**: PostgreSQL database for conversation memory and feedback
- **OpenAI Integration**: GPT-4 for conversation analysis and response generation
- **Vector Search Engine**: FAISS-based semantic search for FAQ matching
- **Caching Layer**: Response caching for improved performance

### Technology Stack
- **Backend**: Python 3.8+, Flask, Flask-RESTX
- **Database**: Supabase (PostgreSQL)
- **AI/ML**: OpenAI GPT-4, FAISS, LangChain
- **Frontend**: HTML5, CSS3, JavaScript (ES6)
- **Documentation**: Swagger/OpenAPI 3.0

## Frontend vs Backend Overview

### Backend (Server-Side)

**Core Application Server:**
- `app.py` - Main Flask web server with all API endpoints
- `supabase_memory.py` - Database integration and conversation memory management
- `optimized_faq_system.py` - Core FAQ processing and AI logic

**Database Layer:**
- **Supabase (PostgreSQL)** - Stores conversations, sessions, and user feedback
- Tables: `chat_sessions`, `chat_messages`, `user_feedback`

**AI/ML Processing:**
- **OpenAI GPT-4 API** - For conversation analysis and response generation
- **FAISS Vector Search** - For semantic FAQ matching
- **LangChain** - For LLM orchestration and processing

**API Layer:**
- RESTful endpoints (`/api/ask`, `/api/feedback`, etc.)
- Swagger/OpenAPI documentation
- JSON request/response handling

**Business Logic:**
- Question analysis and intent detection
- Conversation routing and memory management
- Response caching and optimization
- User feedback processing and analytics

### Frontend (Client-Side)

**Web Interface:**
- `templates/index.html` - Single-page application with embedded CSS and JavaScript
- Modern chat interface with sidebar, message bubbles, and controls

**User Interface Components:**
- Chat message area with conversation history
- Input form for asking questions
- Sidebar with quick questions and system stats
- Feedback buttons (thumbs up/down)
- Dark/light mode toggle
- Search functionality

**Static Assets:**
- `static/logo-tradeup.png` - TradeUP logo
- CSS styling (embedded in HTML)
- JavaScript functionality (embedded in HTML)

**Client-Side Features:**
- Real-time chat interface
- Session management (localStorage)
- AJAX requests to backend APIs
- Interactive feedback collection
- Responsive design for mobile/desktop

### Architecture Flow

```
Frontend (Browser)
    ↓ HTTP Requests
Backend (Flask Server)
    ↓ Database Queries
Supabase Database
    ↓ AI Processing
OpenAI API + Vector Search
    ↓ Response
Backend Processing
    ↓ JSON Response
Frontend Display
```

### Component Responsibilities

**Backend Responsibilities:**
- Process and analyze user questions
- Manage conversation memory and sessions
- Handle AI/ML processing and vector search
- Store and retrieve data from database
- Provide API endpoints for frontend consumption
- Handle business logic and data validation

**Frontend Responsibilities:**
- Display chat interface and user interactions
- Send user input to backend APIs
- Render responses and conversation history
- Manage user interface state and preferences
- Handle client-side interactions (clicks, typing)
- Provide visual feedback and loading states

**Technology Summary:**
- **Backend**: Python + Flask + Supabase + OpenAI + AI/ML libraries
- **Frontend**: HTML + CSS + JavaScript (vanilla, no frameworks like React/Vue)

This is a traditional **server-rendered web application** with a **single-page interface** that communicates with a **RESTful API backend**.

## Installation

### Prerequisites
- Python 3.8 or higher
- Supabase account and project
- OpenAI API key

### Environment Setup

1. **Clone the repository**
```bash
git clone <repository-url>
cd tradeup-faq-system
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Configure environment variables**
Create a `notepad.env` file in the project root:
```env
# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key

# Supabase Configuration
SUPABASE_URL=your_supabase_project_url
SUPABASE_ANON_KEY=your_supabase_anon_key

# Flask Configuration
SECRET_KEY=your_secret_key_for_sessions
```

### Database Setup

1. **Create tables in Supabase**
Execute the following SQL in your Supabase SQL Editor:

```sql
-- Chat sessions table
CREATE TABLE chat_sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id TEXT NOT NULL,
  status TEXT DEFAULT 'active' CHECK (status IN ('active', 'ended')),
  message_count INTEGER DEFAULT 0,
  metadata JSONB DEFAULT '{}',
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Chat messages table
CREATE TABLE chat_messages (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID REFERENCES chat_sessions(id) ON DELETE CASCADE,
  user_id TEXT NOT NULL,
  message_type TEXT NOT NULL CHECK (message_type IN ('human', 'ai')),
  content TEXT NOT NULL,
  intent TEXT,
  sources JSONB,
  metadata JSONB DEFAULT '{}',
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- User feedback table
CREATE TABLE user_feedback (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID REFERENCES chat_sessions(id) ON DELETE CASCADE,
  user_id TEXT NOT NULL,
  question TEXT NOT NULL,
  answer_preview TEXT,
  feedback_type TEXT NOT NULL CHECK (feedback_type IN ('up', 'down')),
  system_used TEXT,
  categories JSONB DEFAULT '[]',
  sources_count INTEGER DEFAULT 0,
  metadata JSONB DEFAULT '{}',
  user_ip TEXT,
  user_agent TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes
CREATE INDEX idx_messages_session ON chat_messages(session_id, created_at);
CREATE INDEX idx_messages_user ON chat_messages(user_id, created_at DESC);
CREATE INDEX idx_sessions_user ON chat_sessions(user_id, created_at DESC);
CREATE INDEX idx_feedback_session ON user_feedback(session_id, created_at);
CREATE INDEX idx_feedback_user ON user_feedback(user_id, created_at DESC);
CREATE INDEX idx_feedback_type ON user_feedback(feedback_type);

-- Enable Row Level Security
ALTER TABLE chat_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE chat_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_feedback ENABLE ROW LEVEL SECURITY;

-- Create policies (adjust for your security requirements)
CREATE POLICY "Allow anonymous access to sessions" ON chat_sessions FOR ALL USING (true);
CREATE POLICY "Allow anonymous access to messages" ON chat_messages FOR ALL USING (true);
CREATE POLICY "Allow anonymous access to feedback" ON user_feedback FOR ALL USING (true);
```

2. **Place logo file**
Create a `static` folder and place your `logo-tradeup.png` file there:
```
project_root/
├── static/
│   └── logo-tradeup.png
└── templates/
    └── index.html
```

## Usage

### Starting the Application

```bash
python app.py
```

The application will be available at:
- **Main Interface**: http://localhost:8000/
- **API Documentation**: http://localhost:8000/docs/
- **API Testing Interface**: http://localhost:8000/test
- **Health Check**: http://localhost:8000/health

### Core Endpoints

#### FAQ Operations
- `POST /api/ask` - Submit questions for intelligent responses
- `GET /api/quick-questions` - Get predefined common questions
- `POST /api/search-faqs` - Search FAQ database with keywords
- `GET /api/search-suggestions` - Get search term suggestions

#### Feedback System
- `POST /api/feedback` - Submit user feedback (thumbs up/down)
- `GET /api/feedback/stats` - Get feedback analytics
- `GET /api/feedback/user/{user_id}` - Get user feedback history
- `GET /api/feedback/session/{session_id}` - Get session feedback

#### System Management
- `GET /api/stats` - System performance metrics
- `GET /api/session-info` - Current session information
- `POST /api/new-session` - Create new conversation session

## API Documentation

Complete API documentation is available through the integrated Swagger UI at `/docs/`. The documentation includes:

- Interactive endpoint testing
- Request/response schemas
- Authentication requirements
- Example requests and responses
- Error handling information

## Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `OPENAI_API_KEY` | OpenAI API key for LLM functionality | Yes |
| `SUPABASE_URL` | Supabase project URL | Yes |
| `SUPABASE_ANON_KEY` | Supabase anonymous key | Yes |
| `SECRET_KEY` | Flask session secret key | Yes |

### System Configuration

Key configuration options can be modified in `app.py`:

```python
# Memory window for conversation context
memory_window = 10

# Processing statistics tracking
processing_stats = {
    "total_questions": 0,
    "faq_questions": 0,
    "market_questions": 0,
    "avg_response_time": 0.0,
    "cache_hits": 0,
    "llm_analysis_calls": 0
}
```

## Development

### Project Structure

```
tradeup-faq-system/
├── app.py                     # Main Flask application
├── supabase_memory.py         # Supabase integration and memory management
├── optimized_faq_system.py    # Core FAQ processing logic
├── templates/
│   └── index.html            # Web interface template
├── static/
│   └── logo-tradeup.png      # Static assets
├── notepad.env               # Environment configuration
├── requirements.txt          # Python dependencies
└── README.md                 # This file
```

### Key Classes

- **`OptimalChatbotFAQ`**: Main chatbot class with conversation memory
- **`ConversationAnalyzer`**: LLM-powered conversation analysis
- **`LLMPoweredOptimizedFAQSystem`**: Core FAQ processing engine

### Adding New Features

1. **New API Endpoints**: Add routes to `app.py` with proper documentation
2. **Enhanced Analysis**: Modify conversation analysis logic in `supabase_memory.py`
3. **Frontend Updates**: Modify `templates/index.html` for UI changes
4. **Database Changes**: Update Supabase schema and corresponding methods

### Testing

The system includes comprehensive testing tools:

1. **Interactive API Tester**: Available at `/test`
2. **Swagger UI**: Available at `/docs/`
3. **Health Monitoring**: Available at `/health`

## Performance Considerations

### Optimization Features
- **Response Caching**: Frequently asked questions are cached for faster responses
- **Session Management**: Efficient session creation and cleanup
- **Database Indexing**: Optimized database queries with proper indexing
- **Connection Pooling**: Supabase connection optimization

### Monitoring
- Real-time performance metrics available through `/api/stats`
- Conversation analytics through feedback system
- System health monitoring through `/health` endpoint

## Security

### Data Protection
- Row Level Security (RLS) enabled on all Supabase tables
- Input validation on all API endpoints
- Session-based user tracking
- IP address and user agent logging for audit trails

### Authentication
Currently configured for anonymous access. For production deployment:
1. Implement Supabase authentication
2. Update RLS policies for authenticated access
3. Add JWT token validation
4. Configure proper CORS settings

## Troubleshooting

### Common Issues

**Database Connection Errors**
- Verify Supabase credentials in environment file
- Check network connectivity to Supabase
- Ensure database tables are created correctly

**OpenAI API Errors**
- Verify API key is valid and has sufficient credits
- Check rate limiting and quota restrictions
- Monitor API usage through OpenAI dashboard

**Session Management Issues**
- Clear browser storage if sessions become corrupted
- Check database connectivity for session persistence
- Verify session table structure and permissions

### Debug Mode

Enable detailed logging by setting Flask debug mode:
```python
app.run(debug=True, host='0.0.0.0', port=8000)
```

## License

This project is proprietary software developed for TradeUP. All rights reserved.

## Support

For technical support and questions:
- Internal documentation: Available through Swagger UI
- System monitoring: Available through `/health` and `/api/stats` endpoints
- Error logging: Check application logs for detailed error information