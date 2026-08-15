# Multi-Tenant RAG Application

A production-ready, containerized Retrieval-Augmented Generation (RAG) application with built-in multi-tenancy, designed to ensure strict data isolation and scalable performance.

## Features

- **Strict Multi-Tenancy**: Built from the ground up to support multiple organizations. Each organization (tenant) is securely isolated via API keys. Vector database queries strictly filter by tenant, ensuring data privacy and preventing context bleed between organizations.
- **Production-Ready Architecture**: 
  - **FastAPI Backend**: Asynchronous, highly performant API endpoints.
  - **PostgreSQL**: Robust persistence for tenant profiles and metadata.
  - **Qdrant Vector DB**: High-performance semantic search database.
  - **Redis & Celery**: Background worker architecture to process and embed documents without blocking the main API.
  - **React Frontend**: A modern, lightweight user interface proxying requests securely through Nginx.
- **Advanced Retrieval**: Utilizes Hybrid Search (Dense Embeddings + Sparse BM25 Keyword Search) combined via Reciprocal Rank Fusion, followed by a Cross-Encoder Reranker for state-of-the-art accuracy.
- **Fully Containerized**: Defined via `docker-compose.yml`, spinning up 6 interconnected, internally secure microservices in one command.

## How it differs from other RAG applications

Most RAG prototypes and tutorials are single-user applications that store documents in a flat vector database or memory. This application solves the **B2B / Multi-Organization problem**:
1. It automatically isolates document contexts so Tenant A cannot accidentally generate answers using Tenant B's uploaded proprietary documents.
2. It scales document ingestion by offloading the heavy embedding and chunking pipeline to background Celery workers, rather than blocking the web server.
3. It securely proxies all services behind Nginx and keeps database ports closed to the outside world, adhering to production security best practices.

## Running Locally

1. Clone the repository.
2. Ensure you have Docker and Docker Compose installed.
3. Create a `.env` file (if necessary) with your Gemini API key:
   ```env
   GEMINI_API_KEY=your_api_key_here
   ```
4. Build and start the cluster:
   ```bash
   docker-compose up -d --build
   ```
5. Access the application at `http://localhost`.

## Production Deployment ($0 Architecture)

This repository is configured to be deployed using entirely free cloud services.

- **Frontend**: Vercel (React/Vite)
- **Backend API**: Render Web Service (Free Tier)
- **Background Worker**: Render Background Worker (Celery)
- **Redis Broker**: Render Key Value (Free)
- **Database**: Supabase PostgreSQL (Free)
- **Vector Store**: Qdrant Cloud (Free)

See `.env.example` for the environment variables required to deploy to these platforms. For full deployment steps, configure the Vercel frontend to point to your Render backend via the `VITE_API_BASE_URL` environment variable.
