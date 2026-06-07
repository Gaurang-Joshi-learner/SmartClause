# SmartClause – AI-Powered ASC 606 Contract Intelligence Platform

## Overview

SmartClause is a full-stack Contract Intelligence Platform that automates ASC 606 revenue recognition analysis from legal agreements.

The platform extracts contract clauses, identifies revenue recognition triggers, detects accounting risks, classifies clauses into ASC 606 categories, generates structured summaries, and exports audit-ready PDF reports.

Designed for finance teams, auditors, accountants, and legal professionals who need to analyze contracts quickly and consistently.

---

## Problem Statement

Manual contract review is:

- Time-consuming
- Error-prone
- Difficult to scale

Organizations must identify:

- Performance Obligations
- Transaction Pricing
- Revenue Recognition Triggers
- Variable Consideration
- Refund Rights
- Warranty Obligations

across hundreds of contracts.

SmartClause automates this process and provides structured outputs for faster financial analysis.

---

## Key Features

### Contract Processing

- Upload PDF and TXT contracts
- Automated text extraction
- Section-based contract segmentation
- Contract metadata extraction

### ASC 606 Intelligence

- Performance Obligation Detection
- Transaction Price Extraction
- Revenue Recognition Classification
- Variable Consideration Detection
- Warranty Analysis
- Refund Rights Detection

### Risk Analysis

- Accounting Risk Flag Generation
- Clause-Level Confidence Scoring
- ASC 606 Relevance Scoring
- Revenue Recognition Insights

### Reporting

- Interactive Dashboard
- Contract Analytics
- JSON Export
- PDF Export
- Historical Contract Storage

### Security

- JWT Authentication
- Protected Routes
- Organization-Based Isolation
- Secure API Access

---



## System Architecture

```text
┌──────────────────────────────────────────────┐
│                  End Users                   │
└──────────────────────┬───────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────┐
│         React + Vite Frontend (Vercel)       │
│                                              │
│ • Dashboard                                  │
│ • Contract Upload                            │
│ • Results Analytics                          │
│ • PDF Export                                 │
│ • JWT Authentication                         │
└──────────────────────┬───────────────────────┘
                       │ REST API
                       ▼
┌──────────────────────────────────────────────┐
│          FastAPI Backend (Railway)           │
│                                              │
│ • Authentication Service                     │
│ • Contract Management API                    │
│ • Extraction API                             │
│ • PDF Generation Service                     │
│ • Async Processing                           │
└──────────────────────┬───────────────────────┘
                       │
      ┌────────────────┼────────────────┐
      │                │                │
      ▼                ▼                ▼

┌───────────────┐ ┌───────────────┐ ┌───────────────┐
│ Authentication│ │ Extraction    │ │ PDF Export    │
│ Service       │ │ Engine        │ │ Service       │
│               │ │               │ │               │
│ • JWT Tokens  │ │ • Clause      │ │ • ReportLab   │
│ • Login       │ │   Detection   │ │ • PDF Export  │
│ • Register    │ │ • ASC 606     │ │ • Downloads   │
│ • Refresh     │ │   Analysis    │ │               │
└───────────────┘ └───────────────┘ └───────────────┘
                       │
                       ▼

┌──────────────────────────────────────────────┐
│           PostgreSQL Database                │
│                                              │
│ • Users                                      │
│ • Organizations                              │
│ • Contracts                                  │
│ • Clauses                                    │
│ • Summaries                                  │
└──────────────────────────────────────────────┘
```

---

## Processing Workflow

```text
User Uploads Contract
          │
          ▼
PDF/TXT Reader
          │
          ▼
Text Extraction
          │
          ▼
Section Splitter
          │
          ▼
ASC 606 Clause Detection
          │
          ▼
Revenue Recognition Analysis
          │
          ▼
Risk Flag Generation
          │
          ▼
Database Storage
          │
          ▼
Dashboard Visualization
          │
          ▼
JSON / PDF Export
```

---

## Tech Stack

### Frontend

- React.js
- Vite
- Tailwind CSS
- Framer Motion
- Axios
- Lucide React
- Recharts

### Backend

- FastAPI
- SQLAlchemy Async
- AsyncPG
- PostgreSQL
- Pydantic
- JWT Authentication
- ReportLab

### Deployment

- Vercel
- Railway
- Railway PostgreSQL

---

## API Endpoints

### Authentication

```http
POST /auth/register
POST /auth/login
POST /auth/refresh
```

### Contracts

```http
POST /contracts/upload
GET /contracts
GET /contracts/{id}
DELETE /contracts/{id}
GET /contracts/{id}/export-pdf
```

### Extractions

```http
GET /extractions/{id}/summary
GET /extractions/{id}/clauses
```

---

## Performance Metrics

| Metric | Value |
|----------|----------|
| Supported Formats | PDF, TXT |
| Clause Categories | 10+ |
| Authentication | JWT |
| Database | PostgreSQL |
| Processing Type | Async |
| Reporting | PDF + JSON |
| Frontend Framework | React |
| Backend Framework | FastAPI |
| Deployment Ready | Yes |

---

## Local Setup

### Clone Repository

```bash
git clone https://github.com/Gaurang-Joshi-learner/SmartClause.git

cd SmartClause
```

---

## Backend Setup

```bash
cd backend

python -m venv venv
```

Windows:

```bash
venv\Scripts\activate
```

Linux/Mac:

```bash
source venv/bin/activate
```

Install Dependencies:

```bash
pip install -r requirements.txt
```

---

## PostgreSQL Setup

Create Database:

```sql
CREATE DATABASE smartclause;
```

Create `.env`

```env
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5433/smartclause

JWT_SECRET=your-secret-key

JWT_ALGORITHM=HS256

ACCESS_TOKEN_EXPIRE_MINUTES=60
```

---

## Run Backend

```bash
python -m uvicorn api:app --reload
```

Backend:

```text
http://localhost:8000
```

Swagger Docs:

```text
http://localhost:8000/docs
```

---

## Frontend Setup

```bash
cd frontend

npm install
```

Create `.env`

```env
VITE_API_URL=http://localhost:8000
```

---

## Run Frontend

```bash
npm run dev
```

Frontend:

```text
http://localhost:5173
```

---

## Deployment

### Frontend (Vercel)

Build Command:

```bash
npm run build
```

Output Directory:

```text
dist
```

Environment Variable:

```env
VITE_API_URL=https://your-backend-url.up.railway.app
```

---

### Backend (Railway)

Environment Variables:

```env
DATABASE_URL=

JWT_SECRET=

JWT_ALGORITHM=HS256

FRONTEND_URL=https://your-vercel-app.vercel.app
```

Start Command:

```bash
uvicorn api:app --host 0.0.0.0 --port $PORT
```

---

## Project Structure

```text
SmartClause/
│
├── backend/
│   ├── api.py
│   ├── auth/
│   ├── db/
│   ├── extractors/
│   ├── routers/
│   ├── utils/
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   ├── public/
│   └── package.json
│
├── screenshots/
│   ├── dashboard.png
│   ├── upload.png
│   ├── results.png
│   └── pdf-export.png
│
├── docs/
│   ├── architecture.png
│   └── workflow.png
│
└── README.md
```

---

## Future Enhancements

- OCR Support for scanned contracts
- Batch Contract Analysis
- Contract Comparison Engine
- Excel Export
- AI-Powered Clause Explanations
- Multi-Language Support
- Audit Trail System
- LLM-Based Contract Summaries

---

```

Recommended Demo Flow:

1. Login
2. Upload Contract
3. Extract Clauses
4. Review ASC 606 Analysis
5. View Risk Flags
6. Export PDF Report

---

