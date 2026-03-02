# Intelligent Banking Platform with Real-Time Fraud Detection & MLOps

A production-style intelligent banking system integrating real-time fraud detection using machine learning, microservices architecture, and MLOps best practices.

---

##  Project Overview

This project simulates a modern banking platform with:

- Real-time fraud detection
- Microservices-based architecture
- SQL-based feature engineering
- Time-aware model training
- Business-cost optimized decision threshold
- Drift detection monitoring
- Experiment tracking with MLflow
- Dockerized deployment

The goal is to demonstrate end-to-end ML system design, not just model training.

---

## Why This Project Matters?
Fraud detection systems must carefully balance false positives and false negatives. 
In real banking environments, an incorrect decision threshold can either cause 
significant financial losses (missed fraud) or customer dissatisfaction (blocked 
legitimate transactions).

Modern ML systems also face data drift, evolving fraud patterns, and operational 
constraints. This project simulates real-world trade-offs by incorporating 
cost-sensitive optimization, time-aware validation, and monitoring mechanisms 
that reflect production-grade ML system requirements.

---

## Key Features

- Real-time fraud prediction via a dedicated microservice
- Cost-sensitive decision threshold optimization
- Time-aware training pipeline to prevent data leakage
- SQL-based feature engineering for realistic data processing
- Drift detection monitoring for model reliability
- Experiment tracking and model versioning using MLflow
- Secure authentication with JWT and bcrypt hashing
- Dockerized multi-service architecture

---

##  System Architecture

Client → FastAPI Backend → Fraud Detection Microservice → XGBoost Model  
                          ↓  
                   PostgreSQL Database  
                          ↓  
                   Monitoring + Drift Detection  

---

##  Machine Learning Design

### Key Decisions

- Time-based train/test split (prevents data leakage)
- `scale_pos_weight` for class imbalance handling
- Precision-Recall optimization
- F1-based threshold selection
- Business-cost optimization:
  - False Negative cost = 1000
  - False Positive cost = 10
- Model versioning with timestamp
- Experiment tracking with MLflow

---

##  Tech Stack

Backend:
- FastAPI
- JWT Authentication
- Passlib (bcrypt hashing)

Machine Learning:
- XGBoost
- scikit-learn
- MLflow

Database:
- PostgreSQL
- SQL feature engineering

Infrastructure:
- Docker
- Docker Compose

Monitoring:
- Custom drift detection module

---

##  Setup Instructions

### 1. Clone Repository
```bash
git clone https://github.com/Shriyans2414/intelligent-banking-mlops.git
cd intelligent-banking-mlops
```

### 2. Create Environment
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Create PostgreSQL Database & Initialize Database Schema
```bash
createdb banking_db
psql banking_db < database/schema.sql
```

### 4. Configure Environment Variables
Create a file named .env in the root directory:
```bash
DB_NAME=banking_db
DB_USER=your_user
DB_PASSWORD=
DB_HOST=localhost
DB_PORT=5432
```

### 5. Generate Data 
```bash
python ml_pipeline/data_generator/orchestrator.py
```
After running, note the generated snapshot table name, e.g.:
```bash
fraud_training_snapshot_20260302_143210
```
Now update your .env file:
```bash
SNAPSHOT_TABLE=fraud_training_snapshot_20260302_143210
```

### 6. Train Model
```bash
python ml_pipeline/training/train_model.py
```

### 7. Start Fraud Service
```bash
uvicorn fraud_service.app:app --port 8001 --reload
```
(Open a new terminal)

### 8. Start Backend
```bash
uvicorn backend.app:app --port 8000 --reload
```

Then open:
http://localhost:8000

## Project Goals

This project demonstrates:
- End-to-end ML system design
- Production-grade fraud detection architecture
- Microservices integration
- Business-aware model optimization
- MLOps pipeline implementation