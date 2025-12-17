# TigerGPT: AI-Powered Smart FAQ Assistant

An intelligent customer service chatbot for TradeUP Securities, featuring LLM-powered responses, real-time market data, and persistent conversation memory.

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![React](https://img.shields.io/badge/React-18.0-61DAFB.svg)
![Flask](https://img.shields.io/badge/Flask-2.0+-green.svg)
![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4o--mini-412991.svg)

---

## Overview

TigerGPT is a production-ready AI assistant that helps TradeUP customers get instant, accurate answers about trading accounts, fees, and platform features. The system combines semantic search over 128+ FAQs with GPT-4 intelligence to deliver contextual responses in under 10 seconds.

### Key Highlights

- **3-5 second average response time** with intelligent caching
- **Multi-language support** (English, Chinese, etc.)
- **Real-time market data** via Yahoo Finance integration
- **Session-based memory** for natural conversations
- **Feedback analytics** for continuous improvement

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     REACT FRONTEND                              │
│              Modern Chat UI + Dark/Light Mode                   │
└───────────────────────────┬─────────────────────────────────────┘
                            │ REST API
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                   FLASK API GATEWAY                             │
│         Intent Analysis → Smart Routing → Response              │
└───────────────────────────┬─────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│  FAQ SYSTEM   │   │ MARKET AGENT  │   │ MEMORY SYSTEM │
│               │   │               │   │               │
│ FAISS Vector  │   │ Yahoo Finance │   │   Supabase    │
│ Search + GPT  │   │  Real-time    │   │  PostgreSQL   │
└───────────────┘   └───────────────┘   └───────────────┘
        │                   │                   │
        └───────────────────┴───────────────────┘
                            │
                            ▼
                ┌───────────────────────┐
                │   OPENAI GPT-4o-mini  │
                │  Response Generation  │
                └───────────────────────┘
```

---

## Features

### 1. Intelligent Question Routing

The system automatically detects question intent and routes to the appropriate handler:

| Question Type | Example | Handler |
|---------------|---------|---------|
| FAQ | "What are the trading fees?" | Vector Search + GPT |
| Market Data | "What's Apple's stock price?" | Yahoo Finance Agent |
| Memory | "What did we discuss?" | Session History |
| Greeting | "Hello!" | Simple Response |

### 2. Semantic FAQ Search

- **128+ Q&A pairs** across 16 categories
- **FAISS vector database** for fast similarity search
- **OpenAI embeddings** for semantic understanding
- Falls back to GPT knowledge when FAQ doesn't match

### 3. Real-Time Market Data

- Live stock quotes and daily changes
- Market overview (S&P 500, NASDAQ, Dow Jones)
- Company news and information
- Powered by Yahoo Finance API

### 4. Conversation Memory

- Session-based chat history stored in Supabase
- Context-aware follow-up responses
- Memory queries: "How many questions did I ask?"
- User identity persists via browser cookies

### 5. User Feedback System

- Thumbs up/down on every response
- Satisfaction analytics dashboard
- Helps identify areas for improvement

---

## Challenges & Solutions

Building a production-quality AI assistant involved solving several complex technical challenges:

### 1. LLM Hallucination Prevention

**Problem:** GPT models can generate plausible-sounding but incorrect information about financial products and trading rules.

**Solution:** Implemented RAG (Retrieval-Augmented Generation) architecture that grounds all responses in verified FAQ data. The system retrieves relevant documents first, then instructs GPT to answer *only* based on retrieved context. When confidence is low, it explicitly states limitations rather than guessing.

### 2. Response Latency Optimization

**Problem:** Initial prototype had 8-12 second response times, unacceptable for customer service.

**Solution:**
- Implemented LRU caching for repeated questions (~30% cache hit rate)
- Optimized FAISS index with flat L2 search for sub-second retrieval
- Used GPT-4o-mini instead of GPT-4 (3x faster, 10x cheaper)
- Parallel initialization of FAQ system, market agent, and memory on startup

### 3. Multi-Intent Query Handling

**Problem:** Users ask compound questions mixing FAQ, market data, and conversation context (e.g., "What's Apple's price and how do I buy it?")

**Solution:** Built a smart routing engine using GPT for intent classification. The router analyzes each query and dispatches to the appropriate handler (FAQ, Market Agent, Memory, or Fallback). For complex queries, it can chain multiple handlers.

### 4. Conversation Context Management

**Problem:** Stateless API couldn't maintain conversation context across requests, leading to disjointed experiences.

**Solution:** Implemented session-based memory using Supabase PostgreSQL. Each user gets a unique session ID (via cookies), and all messages are stored with timestamps and intent metadata. The system can recall previous questions and provide contextual follow-ups.

### 5. Financial Data Accuracy

**Problem:** Ensuring stock prices and market data are current and accurate for a securities platform.

**Solution:** Integrated Yahoo Finance API with real-time data fetching. Built a dedicated Market Agent using LangChain that can query live prices, daily changes, and company information. All market data includes timestamps to show freshness.

### 6. Scalable FAQ Management

**Problem:** Manually maintaining 128+ FAQ entries across 16 categories was error-prone and time-consuming.

**Solution:** Built a web scraper that automatically extracts Q&A pairs from TradeUP's official help pages. The scraper preserves category structure and outputs clean JSON. A separate indexing script converts this to FAISS vectors, making updates as simple as re-running two scripts.

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| **Frontend** | React 18, CSS3, JavaScript ES6 |
| **Backend** | Python 3.8+, Flask, Flask-RESTX |
| **Database** | Supabase (PostgreSQL) |
| **AI/ML** | OpenAI GPT-4o-mini, FAISS, LangChain |
| **Market Data** | Yahoo Finance (yfinance) |
| **API Docs** | Swagger/OpenAPI 3.0 |

### Why These Technologies?

| Technology | Why I Chose It |
|------------|----------------|
| **GPT-4o-mini** | Best cost-performance ratio for production. 3x faster than GPT-4, 10x cheaper ($0.15/1M input tokens), while maintaining high quality for FAQ responses. Full GPT-4 was overkill for structured Q&A tasks. |
| **FAISS** | Meta's vector search library offers millisecond-level similarity search even with 100K+ vectors. Unlike cloud solutions (Pinecone, Weaviate), FAISS runs locally with zero latency overhead and no API costs. Perfect for a bounded FAQ dataset. |
| **Supabase** | PostgreSQL with a generous free tier (500MB, unlimited API calls). Provides real-time subscriptions, built-in auth, and REST API out of the box. Easier setup than raw PostgreSQL, more flexible than Firebase. |
| **Flask** | Lightweight and explicit - ideal for API-first backends. Flask-RESTX adds Swagger docs automatically. Django would be overkill; FastAPI was considered but Flask's ecosystem (CORS, sessions) is more mature. |
| **React** | Industry standard for interactive UIs. Component-based architecture made it easy to build a self-contained chat widget. The virtual DOM handles rapid message updates efficiently. |
| **LangChain** | Abstracts away LLM orchestration complexity. Made it trivial to build the Market Agent with tool-calling capabilities. The agent framework handles retries, parsing, and chain-of-thought automatically. |
| **Yahoo Finance** | Free, reliable, no API key required. Provides real-time quotes, historical data, and company info. For a demo/MVP, it's the best option before committing to paid services (Alpha Vantage, Bloomberg). |

---

## Project Structure

```
TigerGPT/
├── frontend/                    # React application
│   ├── src/
│   │   ├── components/
│   │   │   ├── TradeUpFAQ.jsx   # Main chat component
│   │   │   └── TradeUpFAQ.css   # Styling
│   │   ├── App.js
│   │   └── index.js
│   └── package.json
│
├── backend/                     # Flask API server
│   ├── app.py                   # Main application & routes
│   ├── optimized_faq_system.py  # FAQ search & GPT integration
│   ├── supabase_memory.py       # Memory & session management
│   ├── faq_market_agent.py      # Market data agent
│   └── notepad.env              # Environment config
│
├── scripts/                     # Utility scripts
│   ├── comprehensive_scraper.py # FAQ web scraper
│   └── indexing.py              # Vector index builder
│
├── vectorstore/                 # FAISS index
│   ├── index.faiss              # Vector embeddings
│   └── index.pkl                # Document metadata
│
├── data/scraped/                # Raw FAQ data (JSON)
└── archive/                     # Legacy code reference
```

---

## Performance

| Metric | Value |
|--------|-------|
| Average Response Time | 3-5 seconds |
| FAQ Database Size | 128+ Q&A pairs |
| Categories Covered | 16 |
| Cache Hit Rate | ~30% (repeated questions) |
| Supported Languages | English, Chinese |

### Response Time Breakdown

| Stage | Time |
|-------|------|
| Smart Routing | ~0.1s |
| Vector Search | 0.3-1.3s |
| LLM Generation | 2-4s |
| DB Operations | 0.5-1s |
| Response Format | ~0.2s |

---

## Getting Started

### Prerequisites

- Python 3.8+
- Node.js 16+
- OpenAI API key
- Supabase account

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/tigergpt.git
cd tigergpt
```

2. **Set up the backend**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

3. **Configure environment variables**

Create `backend/notepad.env`:
```env
OPENAI_API_KEY=your_openai_api_key
SUPABASE_URL=your_supabase_url
SUPABASE_ANON_KEY=your_supabase_anon_key
SECRET_KEY=your_flask_secret_key
```

4. **Set up the frontend**
```bash
cd frontend
npm install
```

5. **Set up Supabase database**

Run this SQL in Supabase SQL Editor:
```sql
-- Chat sessions
CREATE TABLE chat_sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id TEXT NOT NULL,
  status TEXT DEFAULT 'active',
  metadata JSONB DEFAULT '{}',
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Chat messages
CREATE TABLE chat_messages (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID REFERENCES chat_sessions(id) ON DELETE CASCADE,
  user_id TEXT NOT NULL,
  message_type TEXT NOT NULL CHECK (message_type IN ('human', 'ai')),
  content TEXT NOT NULL,
  intent TEXT,
  sources JSONB,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- User feedback
CREATE TABLE user_feedback (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID REFERENCES chat_sessions(id),
  user_id TEXT NOT NULL,
  question TEXT NOT NULL,
  feedback_type TEXT NOT NULL CHECK (feedback_type IN ('up', 'down')),
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_messages_session ON chat_messages(session_id);
CREATE INDEX idx_sessions_user ON chat_sessions(user_id);
```

### Running the Application

**Terminal 1 - Backend:**
```bash
cd backend
python app.py
# Server runs at http://localhost:8000
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm start
# App runs at http://localhost:3000
```

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/ask` | Submit a question |
| GET | `/api/quick-questions` | Get common FAQ questions |
| POST | `/api/search-faqs` | Search FAQ database |
| POST | `/api/feedback` | Submit thumbs up/down |
| GET | `/api/stats` | System statistics |
| GET | `/api/session-info` | Current session info |
| GET | `/health` | Health check |
| GET | `/docs/` | Swagger API documentation |

### Example Request

```bash
curl -X POST http://localhost:8000/api/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "How do I open an account?"}'
```

### Example Response

```json
{
  "success": true,
  "response": "To open a Tiger Securities account, you will need...",
  "sources_count": 2,
  "categories": ["New Accounts"],
  "suggested_questions": [
    "What documents do I need?",
    "How long does approval take?"
  ],
  "processing_time": 3.41
}
```

---

## Cost Analysis

| Monthly Queries | API Cost | Supabase | Total |
|-----------------|----------|----------|-------|
| 1,000 | $1.55 | Free | $1.55 |
| 10,000 | $15.50 | Free | $15.50 |
| 100,000 | $155.00 | Free | $155.00 |
| 1,000,000 | $1,550.00 | $25 | $1,575.00 |

*Based on GPT-4o-mini at ~$0.155 per 100 queries*

---

## Future Improvements

1. **Long-term Memory** - RAG-based cross-session context retrieval
2. **Scalability** - Request queuing, API key rotation, Redis caching
3. **Deployment** - Vercel (frontend) + Render (backend)
4. **Analytics Dashboard** - Admin panel for monitoring usage

---

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## License

This project was developed as an internship project for Tiger Securities / TradeUP.

---

## Acknowledgments

- **TradeUP Securities** - Project sponsor
- **OpenAI** - GPT-4o-mini API
- **Meta AI** - FAISS vector search
- **Supabase** - Database hosting
