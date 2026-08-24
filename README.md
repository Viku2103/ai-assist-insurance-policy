# PolicyWise AI

PolicyWise AI is a Retrieval-Augmented Generation (RAG) based
insurance policy understanding assistant.

## Objective

Allow users to ask questions about insurance policy documents
and receive answers grounded in the policy content.

## Architecture

PDF Documents
→ Text Extraction
→ Chunking
→ Embeddings
→ ChromaDB
→ Retrieval
→ LLM
→ Answer