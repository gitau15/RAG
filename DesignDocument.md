Design Document: Modular Architecture

System Overview:
The platform is designed as a Modular RAG Pipeline, separating the data ingestion logic from the generation interface to allow for industry-agnostic scaling.

Component Breakdown:

 The Orchestrator (FastAPI): Acts as the central brain. It receives requests, identifies the "Mode" (Judicial or Sales), and routes data to the correct vector collection.
 The Librarian (ChromaDB + Sentence-Transformers): Handles the "Manual Mode" memory. It uses recursive character splitting to ensure legal clauses and product descriptions remain intact.
 The Executor (Ollama/Mistral): A local LLM instance that receives a "System Prompt" based on the user's goal--shifting from a formal legal researcher to a persuasive sales closer instantly.
 The Transaction Layer: A dedicated service within the backend that monitors the AI's output for "Purchase Intent" to trigger the M-Pesa payment gateway.

Data Flow:

Ingest: Upload -> PDF Parser -> Recursive Chunking -> Vector Embedding -> Metadata Tagging -> ChromaDB.
Query: User Prompt -> Vector Search (Mode Filter) -> Context Extraction -> Prompt Augmentation -> Local LLM -> Response.