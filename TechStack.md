Tech Stack Document: The "Power" Stack

This stack is selected for portability, allowing the entire platform to be "cloned" into any environment with a single command.

AI & Machine Learning:

 Inference Engine: Ollama running Mistral 7B (Quantized).
 Framework: LangChain (for RAG orchestration and memory management).
 Embeddings: all-MiniLM-L6-v2 (Running locally on CPU).
 Vector Storage: ChromaDB.

Backend & API:

 Language: Python 3.10+.
 Framework: FastAPI (Asynchronous handling of LLM streams).
 Payment Gateway: Safaricom Daraja API (M-Pesa).
 Parsing: PyPDF and Unstructured.io.

Frontend & UI:

 Library: React.js (Component-based dashboard).
 Styling: Tailwind CSS (Professional "Dark Mode" aesthetic).
 Icons: Lucide-React.
 State Management: React Hooks (for real-time chat updates).

Infrastructure:

 Containerization: Docker & Docker-Compose (Unified environment).
 Database Persistence: Docker Volumes for ChromaDB data.
Deployment: Vercel (Frontend) and Local On-Premise Servers (Backend/DB).