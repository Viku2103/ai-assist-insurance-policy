# 🛡️ AI Assist
## RAG-Based Insurance Policy Information System

> **An intelligent insurance policy assistant that transforms complex policy documents into clear, source-grounded answers using Retrieval-Augmented Generation (RAG).**

AI Assist is a Retrieval-Augmented Generation (RAG) application designed to simplify the understanding of insurance policies and government insurance schemes.

Instead of relying only on a Large Language Model's general knowledge, AI Assist retrieves relevant information directly from the configured insurance documents and provides that context to the LLM before generating an answer.

The result is a more transparent and grounded question-answering experience with supporting **source document and page information**.

---

## ✨ Key Features

🔎 **Semantic Policy Search**  
Understands the meaning of a user's question and retrieves relevant information using vector similarity search.

🤖 **RAG-Based Question Answering**  
Combines document retrieval with Google Gemini to generate context-grounded responses.

📚 **Multiple Knowledge Bases**  
Supports synthetic insurance policies and a separate government insurance scheme collection.

🏛️ **Government Employee Access**  
Government users can create an employee account and access government scheme information.

🌐 **Public Insurance Access**  
Public users can directly explore general synthetic insurance information without creating an account.

🔐 **Persistent Authentication**  
Government employee accounts are securely persisted using Supabase PostgreSQL rather than temporary local application storage.

📑 **Source Transparency**  
Answers are accompanied by retrieved source document names and page numbers.

⚡ **Optimized Retrieval**  
Streamlit resource caching avoids repeatedly initializing expensive embedding and retrieval components.

🛡️ **Grounded Response Control**  
The system is instructed to avoid inventing policy information when sufficient evidence is unavailable in the retrieved context.

---

# 🎯 Problem Statement

Insurance policies and government insurance scheme documents often contain:

- lengthy terms and conditions,
- technical insurance terminology,
- eligibility rules,
- exclusions,
- claim procedures,
- coverage limits,
- reimbursement conditions,
- and scheme-specific guidelines.

Finding a specific answer manually may require searching through several pages of documentation.

AI Assist addresses this problem by allowing users to ask questions naturally, such as:

> **"What is the maximum medical assistance available?"**

> **"Is the spouse covered under the scheme?"**

> **"What documents are required for a claim?"**

> **"What does motor insurance cover?"**

> **"What happens if treatment is taken at a non-network hospital?"**

The system retrieves relevant document sections and uses them as context to generate the response.

---

# 🧠 What is Retrieval-Augmented Generation?

**Retrieval-Augmented Generation (RAG)** combines two important capabilities:

**Information Retrieval + Large Language Model Generation**

A traditional LLM may generate an answer primarily from knowledge learned during training.

AI Assist instead follows this process:

```text
User Question
      ↓
Search the configured insurance knowledge base
      ↓
Retrieve relevant policy sections
      ↓
Provide retrieved information to the LLM
      ↓
Generate a grounded answer
      ↓
Display supporting sources
```

This architecture helps reduce unsupported answers and makes the response easier to verify against the underlying documents.

---

# 🏗️ System Architecture

```text
                     ┌──────────────────────────┐
                     │   Insurance PDF Files    │
                     └────────────┬─────────────┘
                                  │
                                  ▼
                     ┌──────────────────────────┐
                     │      PyPDFLoader         │
                     │   Text + Metadata Load   │
                     └────────────┬─────────────┘
                                  │
                                  ▼
                     ┌──────────────────────────┐
                     │      Text Chunking       │
                     └────────────┬─────────────┘
                                  │
                                  ▼
                     ┌──────────────────────────┐
                     │ HuggingFace Embeddings   │
                     └────────────┬─────────────┘
                                  │
                                  ▼
                     ┌──────────────────────────┐
                     │        ChromaDB          │
                     │      Vector Store        │
                     └────────────┬─────────────┘
                                  │
                                  │
       ┌──────────────────────────┴──────────────────────────┐
       │                                                     │
       │                 QUERY PIPELINE                      │
       │                                                     │
       │   User Question                                     │
       │        ↓                                            │
       │   Query Embedding                                   │
       │        ↓                                            │
       │   Semantic Similarity Search                        │
       │        ↓                                            │
       │   Top Relevant Chunks                               │
       │        ↓                                            │
       │   Prompt + Retrieved Context                        │
       │        ↓                                            │
       │   Google Gemini                                     │
       │        ↓                                            │
       │   Grounded Answer                                   │
       │        ↓                                            │
       │   Source Document + Page                            │
       │                                                     │
       └─────────────────────────────────────────────────────┘
```

---

# 🔄 RAG Pipeline

## 1. 📄 Document Loading

Insurance PDF documents are loaded using **PyPDFLoader**.

Text and metadata such as the source document and page information are extracted for downstream processing.

---

## 2. ✂️ Text Chunking

Large document content is divided into smaller chunks.

Chunking allows the retrieval system to identify relevant sections without supplying an entire PDF to the language model.

---

## 3. 🔢 Embedding Generation

Each chunk is transformed into a numerical vector representation using a **HuggingFace Sentence Transformer embedding model**.

These vectors represent the semantic meaning of the text.

---

## 4. 🗄️ Vector Storage

Document embeddings and their associated metadata are stored in **ChromaDB**.

This provides the vector search layer for the RAG pipeline.

---

## 5. 💬 User Question

The user enters a natural-language insurance question through the **Streamlit** interface.

---

## 6. 🔍 Semantic Retrieval

The question is embedded using the same embedding model.

ChromaDB compares the query vector with stored document vectors and retrieves the most semantically relevant chunks.

---

## 7. 🧩 Prompt Assembly

The retrieved document content is combined with the user's question into a structured prompt.

The prompt instructs the LLM to answer using the supplied policy context.

---

## 8. 🤖 LLM Generation

**Google Gemini** generates the final natural-language response using the retrieved context.

The application streams the generated response to the interface.

---

## 9. 📌 Source Grounding

Supporting retrieval information is displayed with the answer, including:

- source document,
- page number,
- and retrieved text snippet.

This allows users to understand where the supporting information came from.

---

# 📚 Knowledge Bases

AI Assist separates its document collections according to the type of user and information being requested.

## 🌐 Synthetic Insurance Knowledge Base

The general insurance collection contains synthetic documents covering areas such as:

- Health Insurance
- Life Insurance
- Motor Insurance
- Travel Insurance
- Home Insurance
- Critical Illness
- Personal Accident
- Claim Procedures
- Policy Endorsements
- Insurance Terminology
- Hospital Networks
- Rider Benefits
- Underwriting Guidance

These documents are intended for development, demonstration, and testing of the RAG pipeline.

---

## 🏛️ Government Insurance Knowledge Base

The application also supports a separate government insurance knowledge base containing the **Tamil Nadu New Health Insurance Scheme (NHIS) 2026** document.

Government employees can access both:

```text
Government Insurance Documents
            +
Synthetic Insurance Documents
```

This architecture also makes it possible to add additional government insurance documents later.

---

# 👥 User Access Model

AI Assist currently supports two user experiences.

### 🌐 Public User

```text
Public User
     ↓
No Account Required
     ↓
Synthetic Insurance Knowledge Base
     ↓
RAG Assistant
```

Public users can explore general insurance information directly.

### 🏛️ Government User

```text
Government Employee
        ↓
Create Account / Login
        ↓
Streamlit Application
        ↓
Supabase
        ↓
PostgreSQL
        ↓
Government + Synthetic Knowledge Bases
        ↓
RAG Assistant
```

Government users register using:

- Employee ID
- Employee Name
- Department
- Password

Their account information is persisted in Supabase PostgreSQL.

---

# 🔐 Authentication & Security

Government employee authentication is implemented using **Supabase** with PostgreSQL-backed persistent storage.

Passwords are **not stored as plain text**. The application derives a password hash using **PBKDF2-HMAC-SHA256 with a random salt** before persistence.

Sensitive credentials such as:

```text
GOOGLE_API_KEY
SUPABASE_URL
SUPABASE_SECRET_KEY
```

are kept outside the application source code.

Local development uses environment variables from `.env`, while deployed environments can provide secrets through Streamlit's secret-management configuration.

The `.env` file and Streamlit secret file should never be committed to GitHub.

---

# 🛠️ Technology Stack

| Layer | Technology |
|---|---|
| 🐍 Programming Language | Python |
| 🧠 RAG Framework | LangChain |
| 📄 PDF Processing | PyPDFLoader |
| 🔢 Embeddings | HuggingFace Sentence Transformers |
| 🗄️ Vector Database | ChromaDB |
| 🤖 Large Language Model | Google Gemini |
| 🎨 Application UI | Streamlit |
| 🔐 Authentication Storage | Supabase |
| 🗃️ User Database | PostgreSQL |
| 🔧 Version Control | Git & GitHub |
| ☁️ Deployment | Streamlit Community Cloud |

---

# 📁 Project Structure

```text
ai-assist-insurance-policy/
│
├── app.py
├── main.py
├── requirements.txt
├── README.md
├── .gitignore
│
├── assets/
│
├── docs/
│   ├── synthetic/
│   └── government/
│
├── chroma_db/
│
├── tests/
│
└── src/
    ├── ingestion/
    ├── embeddings/
    ├── vectorstore/
    ├── retrieval/
    └── generation/
```

### Main Components

**`app.py`**  
Streamlit user interface, authentication flow, knowledge-base selection, retrieval invocation, answer generation, and source presentation.

**`src/ingestion/`**  
Document loading and text-processing components.

**`src/embeddings/`**  
Embedding-model configuration.

**`src/vectorstore/`**  
Vector-store creation and persistence logic.

**`src/retrieval/`**  
Retriever initialization and semantic document retrieval.

**`src/generation/`**  
Prompt assembly and Gemini response-generation logic.

**`docs/`**  
Insurance PDF knowledge bases.

---

# ⚡ Performance Optimization

Loading the embedding model and initializing retrieval components can be relatively expensive.

AI Assist uses Streamlit resource caching so initialized retrieval components can be reused across application reruns.

```text
First Initialization
       ↓
Load Embedding Model
       ↓
Initialize ChromaDB
       ↓
Create Retriever
       ↓
Cache Resource
       ↓
Reuse for Subsequent Queries
```

This significantly reduces repeated initialization overhead during a running application session.

---

# 🛡️ Grounding & Hallucination Control

AI Assist is designed to prioritize information retrieved from the selected policy documents.

The generation prompt instructs the model to:

- answer from the supplied context,
- avoid inventing policy details,
- clearly indicate when relevant information is unavailable,
- and avoid presenting unsupported assumptions as policy facts.

If sufficient supporting information cannot be retrieved, the expected response is:

> **"The relevant information was not found in the selected documents."**

This does not guarantee that every generated response is error-free, so source verification remains important.

---

# 🚀 Installation & Local Setup

## 1. Clone the Repository

```bash
git clone <repository-url>
cd ai-assist-insurance-policy
```

## 2. Create a Virtual Environment

```bash
python -m venv .venv
```

## 3. Activate the Environment

### Windows

```bash
.venv\Scripts\activate
```

## 4. Install Dependencies

```bash
pip install -r requirements.txt
```

---

# 🔑 Environment Configuration

Create a `.env` file in the project root.

```env
GOOGLE_API_KEY=your_google_api_key
SUPABASE_URL=your_supabase_project_url
SUPABASE_SECRET_KEY=your_supabase_secret_key
```

> ⚠️ **Never commit `.env`, API keys, or Supabase secret keys to GitHub.**

Ensure `.env` is included in `.gitignore`.

---

# ▶️ Run the Application

Start the Streamlit application:

```bash
streamlit run app.py
```

Streamlit will launch the application in your browser.

---

# ☁️ Deployment

The application can be deployed using **Streamlit Community Cloud** with the source code hosted on GitHub.

Deployment secrets should be configured through Streamlit's secret-management settings rather than stored directly in the repository.

Required secrets include:

```toml
GOOGLE_API_KEY = "your_google_api_key"
SUPABASE_URL = "your_supabase_project_url"
SUPABASE_SECRET_KEY = "your_supabase_secret_key"
```

The deployed application communicates with Supabase for persistent government-user authentication.

---

# 🔒 Git & Secret Management

The repository should exclude local and sensitive/generated resources such as:

```gitignore
.venv/
.env
__pycache__/
*.pyc
logs/
*.log
.vscode/
.streamlit/secrets.toml
```

Generated local vector-store artifacts may also be excluded depending on the selected deployment and indexing strategy.

---

# ⚠️ Current Limitations

AI Assist is a document-understanding project and should not be interpreted as an automated insurance decision system.

Current limitations include:

- answers depend on the quality and completeness of the indexed documents,
- semantic retrieval may occasionally return partially relevant context,
- LLM-generated responses can still contain errors,
- the system does not approve or reject insurance claims,
- it does not independently verify policy eligibility,
- and it does not replace official policy documentation.

Users should verify important information against the original policy or scheme document.

---

# 🔮 Future Enhancements

Planned and potential improvements include:

- 📊 RAG evaluation metrics
- 🧪 Expanded automated testing
- 📚 Additional government and private insurance policies
- 📤 Controlled PDF upload and ingestion
- 💬 Conversation history
- 🔍 Hybrid keyword + semantic retrieval
- 🎯 Retrieval reranking
- 🧠 Improved query understanding
- 🔄 Automated vector-store updates when documents change
- 📈 Application logging and monitoring
- 👥 More advanced role-based access control

---

# ⚖️ Disclaimer

AI Assist is intended for **insurance policy information retrieval, document understanding, and educational use**.

The application does not provide:

- legal advice,
- financial advice,
- medical advice,
- claim approval,
- policy approval,
- or official insurance decisions.

For authoritative information, users should refer to the original policy documents and the relevant insurance provider or government authority.

---

## 🛡️ AI Assist

**Making complex insurance information easier to search, understand, and verify.**

Built using **Python • LangChain • HuggingFace • ChromaDB • Gemini • Streamlit • Supabase**