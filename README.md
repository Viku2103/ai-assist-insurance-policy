# 🛡️ AI Assist – Insurance Policy Information System

AI Assist is a Retrieval-Augmented Generation (RAG) based application designed to help users understand insurance policy documents through natural-language questions.

The system retrieves relevant information from insurance documents and uses a Large Language Model (LLM) to generate clear, context-grounded answers along with supporting source information.

---

## 🎯 Project Objective

Insurance policy documents can be lengthy and difficult to understand.

AI Assist enables users to ask questions such as:

- What is the maximum medical assistance available?
- Is the spouse covered under the scheme?
- What documents are required for a claim?
- What does motor insurance cover?
- What happens when treatment is taken at a non-network hospital?

The system searches the available policy documents and generates an answer based on the retrieved information.

---

## 🧠 What is RAG?

Retrieval-Augmented Generation (RAG) combines:

**Information Retrieval + Large Language Model**

Instead of asking an LLM to answer only from its existing knowledge, relevant information is first retrieved from the provided documents.

That information is then supplied to the LLM as context for generating the final answer.

---

## 🏗️ System Architecture

```text
Insurance PDF Documents
        ↓
PDF Loading
        ↓
Text Extraction
        ↓
Text Chunking
        ↓
HuggingFace Embeddings
        ↓
ChromaDB Vector Store
        ↓
        ↓
User Question
        ↓
Query Embedding
        ↓
Semantic Similarity Search
        ↓
Top Relevant Chunks
        ↓
Prompt + Retrieved Context
        ↓
Gemini LLM
        ↓
Grounded Answer
        ↓
Source Document + Page
```

---

## 📚 Knowledge Bases

The application currently supports two document collections:

### Synthetic Insurance Documents

Includes synthetic documents covering areas such as:

- Health Insurance
- Life Insurance
- Motor Insurance
- Travel Insurance
- Home Insurance
- Critical Illness
- Personal Accident
- Claims
- Policy Endorsements
- Insurance Terminology

### Tamil Nadu NHIS 2026

The application also supports the Tamil Nadu New Health Insurance Scheme 2026 document as a separate searchable knowledge base.

---

## 🛠️ Technology Stack

| Component | Technology |
|---|---|
| Programming Language | Python |
| RAG Framework | LangChain |
| Embeddings | HuggingFace Sentence Transformers |
| Vector Database | ChromaDB |
| Large Language Model | Google Gemini |
| PDF Processing | PyPDFLoader |
| Frontend | Streamlit |
| Version Control | Git & GitHub |

---

## 🔄 RAG Workflow

### 1. Document Loading

Insurance PDF documents are loaded and their textual content is extracted.

### 2. Text Chunking

Large document content is divided into smaller chunks so relevant portions can be retrieved efficiently.

### 3. Embedding Generation

Each text chunk is converted into a numerical vector representation using a HuggingFace embedding model.

### 4. Vector Storage

The generated vectors and document metadata are stored in ChromaDB.

### 5. User Query

The user enters an insurance-related question through the Streamlit interface.

### 6. Semantic Retrieval

The question is converted into an embedding and compared with stored vectors.

The most semantically relevant chunks are retrieved.

### 7. Prompt Assembly

The retrieved policy information and user question are combined into a structured prompt.

### 8. LLM Generation

Gemini generates a clear response using the retrieved context.

### 9. Source Grounding

The application displays the source document and page associated with the retrieved information.

---

## 📁 Project Structure

```text
ai-assist-insurance-policy/
│
├── app.py
├── main.py
├── requirements.txt
├── README.md
├── .gitignore
│
├── docs/
│   ├── synthetic/
│   └── government/
│
├── chroma_db/
│
└── src/
    ├── ingestion/
    ├── embeddings/
    ├── vectorstore/
    ├── retrieval/
    └── generation/
```

---

## ▶️ Running the Application

### Create a virtual environment

```bash
python -m venv .venv
```

### Activate the environment on Windows

```bash
.venv\Scripts\activate
```

### Install dependencies

```bash
pip install -r requirements.txt
```

### Configure the Gemini API Key

Create a `.env` file in the project root and configure the required Gemini API key.

Do not commit the `.env` file to GitHub.

### Start the Streamlit application

```bash
streamlit run app.py
```

---

## 🛡️ Hallucination Control

AI Assist is instructed to generate answers using the retrieved policy context.

If relevant information cannot be found in the selected documents, the system responds that the information could not be found rather than intentionally generating unsupported policy information.

---

## ⚡ Performance Optimization

The embedding model and retriever are cached after initialization.

The initial request can take longer because the local embedding model must be loaded into memory. Subsequent requests are significantly faster because the initialized components are reused.

---

## 🔮 Future Enhancements

Potential improvements include:

- Additional government and private insurance policies
- PDF upload through the user interface
- Conversation history
- Hybrid keyword + semantic search
- Improved document filtering
- Reranking retrieved chunks
- Authentication
- Automated vector-store updates when documents change

---

## ⚠️ Disclaimer

AI Assist is intended for insurance policy information retrieval and understanding.

Generated responses should not be treated as legal, financial, medical, claim-approval, or professional insurance advice.