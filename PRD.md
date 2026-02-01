Project Requirements Document (PRD): Universal RAG Platform

Vision: To provide a secure, local-first intelligence engine that automates document-heavy workflows, starting with judicial research and expanding into autonomous social commerce in Kenya.

Core Functional Requirements:

 Multi-Tenant Ingestion: Ability to ingest and segment data into isolated collections (e.g., judicialdata vs. salescatalog) using metadata tagging.
 Parameterized Retrieval: A query engine that adjusts retrieval depth () and system personas based on the active mode.
 Privacy-First Inference: 100% local processing via Ollama to ensure legal confidentiality and data sovereignty.
 Actionable Output: Integration of functional triggers, specifically the M-Pesa Daraja API for "Sales Mode" to initiate STK pushes.
 Citation Engine: Mandatory mapping of AI responses to specific source document chunks to eliminate hallucinations in legal contexts.

Success Metrics:

 Successful deployment of a single Dockerized unit on a local server.
 Response latency under 8 seconds for 1,000-page document sets.
 Zero external data leakage during inference.