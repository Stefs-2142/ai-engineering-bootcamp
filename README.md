# 🛒 Amazon Product Search Assistant

Intelligent AI-powered product search system combining **Hybrid RAG**, **SQL Agent**, and **Smart Query Routing** using LangGraph.

## 🎯 Features

### Smart Query Routing

The system automatically classifies user queries into three types:

- **🔍 RAG (Semantic Search)**: Natural language product discovery

  - *"wireless earbuds for running"*
  - *"tell me about coffee makers with grinder"*
- **📊 SQL (Structured Queries)**: Data analytics and aggregations

  - *"how many products cost over $100"*
  - *"show categories with average ratings"*
- **⚡ Hybrid (Filters + Semantic)**: Best of both worlds

  - *"best headphones under $50"*
  - *"top rated coffee machines"*
  - *"wireless earbuds with good bass under $100"*

### Tech Stack

- **LLM**: OpenAI GPT-5-nano (reasoning model)
- **Vector DB**: Qdrant (semantic search)
- **SQL DB**: PostgreSQL (structured data)
- **Router**: LangGraph (intent classification)
- **API**: FastAPI
- **UI**: Streamlit
- **Monitoring**: LangSmith tracing
- **Orchestration**: Docker Compose

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- OpenAI API key
- LangSmith API key (optional, for tracing)

### Installation

1. **Clone the repository**

```bash
git clone <repo-url>
cd ai-engineering-bootcamp
```

2. **Setup environment variables**

```bash
cp env.example .env
```

Edit `.env` and add your API keys:

```env
OPENAI_API_KEY=your_openai_api_key
LANGSMITH_API_KEY=your_langsmith_api_key  
LANGSMITH_TRACING_V2=true
```

3. **Run the application**

```bash
make run-docker-compose
```

Or manually:

```bash
docker-compose up --build
```

### Access the Services

- 🎨 **Streamlit UI**: http://localhost:8501
- 🔌 **API Docs**: http://localhost:8000/docs
- 📊 **Qdrant Dashboard**: http://localhost:6333/dashboard
- 🗄️ **PostgreSQL**: `localhost:5432`

## 📚 API Endpoints

### `/chat` - Smart Router (Recommended)

Automatically routes to the best pipeline:

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "best headphones under $100"}'
```

### `/rag` - Semantic Search Only

```bash
curl -X POST http://localhost:8000/rag \
  -H "Content-Type: application/json" \
  -d '{"query": "wireless earbuds for running"}'
```

### `/sql` - SQL Query Only

```bash
curl -X POST http://localhost:8000/sql \
  -H "Content-Type: application/json" \
  -d '{"query": "how many products cost over $100"}'
```

## 🏗️ Architecture

```
User Query
    ↓
[Router Agent (LangGraph)]
    ↓
┌───────────┬────────────┬──────────────┐
│    RAG    │    SQL     │   HYBRID     │
├───────────┼────────────┼──────────────┤
│  Qdrant   │ PostgreSQL │ Both DBs     │
│  Vector   │ Structured │ Filters +    │
│  Search   │  Queries   │ Semantic     │
└───────────┴────────────┴──────────────┘
    ↓
[LLM Response Generation]
    ↓
User Answer
```

## 📁 Project Structure

```
.
├── apps/
│   ├── api/                    # FastAPI backend
│   │   ├── src/api/
│   │   │   ├── agents/        # AI agents
│   │   │   │   ├── router.py          # LangGraph router
│   │   │   │   ├── sql_agent.py       # SQL pipeline
│   │   │   │   ├── retrieval_generation.py  # RAG pipeline
│   │   │   │   └── hybrid.py          # Hybrid pipeline
│   │   │   ├── api/
│   │   │   │   ├── endpoints.py       # API routes
│   │   │   │   └── models.py          # Pydantic models
│   │   │   └── app.py         # FastAPI app
│   │   └── evals/             # Evaluation scripts
│   └── chatbot_ui/            # Streamlit frontend
│       └── src/chatbot_ui/app.py
├── notebooks/                  # Jupyter notebooks
│   └── week_1/
│       ├── 05-RAG-Evals.ipynb
│       └── 06-etl-postgres.ipynb
├── data/                       # Amazon Electronics dataset
├── docker-compose.yml          # Docker orchestration
└── README.md
```

## 🧠 How It Works

### 1. Router Agent (LangGraph)

- Classifies query intent using GPT-5-nano
- Extracts structured filters (price, rating, category)
- Routes to appropriate pipeline

### 2. SQL Agent

- Generates PostgreSQL queries from natural language
- Executes queries with safety checks
- Formats results into natural language

### 3. RAG Pipeline

- Embeds query using OpenAI embeddings
- Searches Qdrant vector database
- Generates contextual answers

### 4. Hybrid Pipeline

- Applies SQL filters to narrow results
- Performs semantic search on filtered data
- Combines structured + unstructured retrieval

## 🔧 Development

### Run Notebooks

```bash
jupyter notebook notebooks/
```

### View Logs

```bash
docker-compose logs -f api
docker-compose logs -f streamlit-app
```

### Database Access

```bash
# PostgreSQL
psql -h localhost -p 5432 -U bootcamp -d amazon_products

# Qdrant
curl http://localhost:6333/collections
```

## 📊 Dataset

This project uses Amazon Electronics product data (2022-2023):

- ~100K products with ratings and reviews
- Fields: title, price, rating, category, features, description
- Hive-style partitioned JSONL format

**Citation:**

```bibtex
@article{hou2024bridging,
  title={Bridging Language and Items for Retrieval and Recommendation},
  author={Hou, Yupeng and Li, Jiacheng and He, Zhankui and Yan, An and Chen, Xiusi and McAuley, Julian},
  journal={arXiv preprint arXiv:2403.03952},
  year={2024}
}
```

## 🧪 Testing & Evaluation

Run retrieval evaluations:

```bash
cd apps/api
python evals/eval_retriever.py
```

## 🐛 Troubleshooting

### API Returns 400 Error (Temperature)

If you see `Unsupported value: 'temperature'`, ensure you're using `gpt-5-nano` or another reasoning model without the `temperature` parameter.

### SQL Query Blocked

The system has security checks to prevent dangerous SQL operations. Only SELECT queries are allowed.

### Qdrant Connection Error

Wait for Qdrant to fully start (~10 seconds after `docker-compose up`).

## 📝 Environment Variables

| Variable                 | Description              | Required                      |
| ------------------------ | ------------------------ | ----------------------------- |
| `OPENAI_API_KEY`       | OpenAI API key           | ✅                            |
| `LANGSMITH_API_KEY`    | LangSmith API key        | ✅                            |
| `LANGSMITH_TRACING_V2` | Enable LangSmith tracing | ✅                            |
| `POSTGRES_HOST`        | PostgreSQL host          | ✅ (default: postgres)        |
| `POSTGRES_DB`          | Database name            | ✅ (default: amazon_products) |
| `POSTGRES_USER`        | Database user            | ✅ (default: bootcamp)        |
| `POSTGRES_PASSWORD`    | Database password        | ✅ (default: bootcamp)        |

## 📬 Contact

**Instructor**: Aurimas Griciunas

- 📧 Email: aurimas@swirlai.com
- 💼 LinkedIn: [aurimas-griciunas](https://www.linkedin.com/in/aurimas-griciunas)
- 🐦 Twitter: [@Aurimas_Gr](https://x.com/Aurimas_Gr)
- 📰 Newsletter: [swirlai.com/newsletter](https://www.newsletter.swirlai.com/)

**Built with ❤️ as part of the AI Engineering Bootcamp**
