"""
ML/Inference Service - Model serving, predictions, model management
Port: 8000 (standard)
Host Port: 8119
"""

import os
import json
from datetime import datetime
from typing import List, Optional
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Float, Text, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from pydantic import BaseModel, Field
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@db:5432/piddy_ml_inference")
engine = create_engine(DATABASE_URL, echo=False, pool_size=10, max_overflow=20)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# SQLAlchemy Models
class MLModel(Base):
    __tablename__ = "ml_model"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    version = Column(String)
    model_type = Column(String)  # classification, regression, clustering, nlp
    framework = Column(String)  # tensorflow, pytorch, sklearn
    model_path = Column(String)
    input_schema = Column(Text)  # JSON schema
    output_schema = Column(Text)  # JSON schema
    metrics = Column(Text)  # JSON accuracy, precision, recall
    status = Column(String, default="inactive")  # active, inactive, deprecated
    owner_id = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class ModelVersion(Base):
    __tablename__ = "model_version"
    id = Column(Integer, primary_key=True, index=True)
    model_id = Column(Integer, ForeignKey('ml_model.id'))
    version = Column(String)
    model_path = Column(String)
    metrics = Column(Text)  # JSON
    deployed = Column(Boolean, default=False)
    deployment_date = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

class Prediction(Base):
    __tablename__ = "prediction"
    id = Column(Integer, primary_key=True, index=True)
    model_id = Column(Integer, ForeignKey('ml_model.id'))
    user_id = Column(Integer)
    input_data = Column(Text)  # JSON
    prediction_output = Column(Text)  # JSON
    confidence = Column(Float)
    latency_ms = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)

class PredictionBatch(Base):
    __tablename__ = "prediction_batch"
    id = Column(Integer, primary_key=True, index=True)
    model_id = Column(Integer, ForeignKey('ml_model.id'))
    user_id = Column(Integer)
    batch_size = Column(Integer)
    status = Column(String)  # processing, completed, failed
    results_file = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

class ModelFeature(Base):
    __tablename__ = "model_feature"
    id = Column(Integer, primary_key=True, index=True)
    model_id = Column(Integer, ForeignKey('ml_model.id'))
    feature_name = Column(String)
    feature_type = Column(String)  # numeric, categorical, text
    importance_score = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)

# Pydantic Schemas
class ModelRegister(BaseModel):
    name: str
    version: str
    model_type: str
    framework: str
    model_path: str
    input_schema: dict
    output_schema: dict
    metrics: dict
    owner_id: int

class PredictionRequest(BaseModel):
    model_id: int
    user_id: int
    input_data: dict

class BatchPredictionRequest(BaseModel):
    model_id: int
    user_id: int
    input_file_path: str

class ModelDeploy(BaseModel):
    model_version_id: int

# FastAPI App
app = FastAPI(title="ML/Inference Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Endpoints
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "ml-inference",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.post("/models/register", status_code=status.HTTP_201_CREATED)
async def register_model(model: ModelRegister, db=Depends(get_db)):
    """Register new ML model"""
    if db.query(MLModel).filter(MLModel.name == model.name).first():
        raise HTTPException(status_code=400, detail="Model already registered")
    
    db_model = MLModel(
        name=model.name,
        version=model.version,
        model_type=model.model_type,
        framework=model.framework,
        model_path=model.model_path,
        input_schema=json.dumps(model.input_schema),
        output_schema=json.dumps(model.output_schema),
        metrics=json.dumps(model.metrics),
        owner_id=model.owner_id
    )
    db.add(db_model)
    db.commit()
    db.refresh(db_model)
    
    # Create first version
    version = ModelVersion(
        model_id=db_model.id,
        version=model.version,
        model_path=model.model_path,
        metrics=json.dumps(model.metrics)
    )
    db.add(version)
    db.commit()
    
    return {"model_id": db_model.id, "name": model.name, "version": model.version}

@app.get("/models/{model_id}")
async def get_model(model_id: int, db=Depends(get_db)):
    """Get model details"""
    model = db.query(MLModel).filter(MLModel.id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    
    return {
        "id": model.id,
        "name": model.name,
        "version": model.version,
        "model_type": model.model_type,
        "framework": model.framework,
        "status": model.status,
        "metrics": json.loads(model.metrics),
        "created_at": model.created_at
    }

@app.get("/models")
async def list_models(model_type: str = None, status_filter: str = "active", db=Depends(get_db)):
    """List models"""
    query = db.query(MLModel).filter(MLModel.status == status_filter)
    if model_type:
        query = query.filter(MLModel.model_type == model_type)
    
    models = query.limit(50).all()
    return [
        {
            "id": m.id,
            "name": m.name,
            "version": m.version,
            "type": m.model_type,
            "framework": m.framework,
            "status": m.status
        }
        for m in models
    ]

@app.post("/predict")
async def make_prediction(pred_req: PredictionRequest, db=Depends(get_db)):
    """Make prediction using model"""
    model = db.query(MLModel).filter(MLModel.id == pred_req.model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    
    if model.status != "active":
        raise HTTPException(status_code=400, detail="Model is not active")
    
    # Simulate prediction
    import time
    start = time.time()
    
    # Mock prediction logic
    prediction_output = {
        "class": "predicted_class",
        "probability": 0.87
    }
    confidence = 0.87
    
    latency_ms = int((time.time() - start) * 1000)
    
    # Store prediction
    prediction = Prediction(
        model_id=pred_req.model_id,
        user_id=pred_req.user_id,
        input_data=json.dumps(pred_req.input_data),
        prediction_output=json.dumps(prediction_output),
        confidence=confidence,
        latency_ms=latency_ms
    )
    db.add(prediction)
    db.commit()
    
    return {
        "prediction_id": prediction.id,
        "model_id": pred_req.model_id,
        "output": prediction_output,
        "confidence": confidence,
        "latency_ms": latency_ms
    }

@app.post("/predict-batch")
async def predict_batch(batch_req: BatchPredictionRequest, db=Depends(get_db)):
    """Make batch predictions"""
    model = db.query(MLModel).filter(MLModel.id == batch_req.model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    
    if model.status != "active":
        raise HTTPException(status_code=400, detail="Model is not active")
    
    batch = PredictionBatch(
        model_id=batch_req.model_id,
        user_id=batch_req.user_id,
        batch_size=100,  # Mock batch size
        status="processing"
    )
    db.add(batch)
    db.commit()
    
    return {
        "batch_id": batch.id,
        "status": "processing",
        "estimated_duration_seconds": 30
    }

@app.get("/predictions/{prediction_id}")
async def get_prediction(prediction_id: int, db=Depends(get_db)):
    """Get prediction result"""
    pred = db.query(Prediction).filter(Prediction.id == prediction_id).first()
    if not pred:
        raise HTTPException(status_code=404, detail="Prediction not found")
    
    return {
        "id": pred.id,
        "model_id": pred.model_id,
        "output": json.loads(pred.prediction_output),
        "confidence": pred.confidence,
        "latency_ms": pred.latency_ms,
        "created_at": pred.created_at
    }

@app.post("/models/{model_id}/deploy")
async def deploy_model_version(model_id: int, version_id: int, db=Depends(get_db)):
    """Deploy model version"""
    model = db.query(MLModel).filter(MLModel.id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    
    version = db.query(ModelVersion).filter(
        ModelVersion.id == version_id,
        ModelVersion.model_id == model_id
    ).first()
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")
    
    # Deactivate all previous versions
    db.query(ModelVersion).filter(
        ModelVersion.model_id == model_id,
        ModelVersion.deployed == True
    ).update({"deployed": False})
    
    version.deployed = True
    version.deployment_date = datetime.utcnow()
    model.status = "active"
    db.commit()
    
    return {
        "model_id": model_id,
        "version_id": version_id,
        "deployed": True,
        "deployment_time": version.deployment_date
    }

@app.get("/models/{model_id}/versions")
async def get_model_versions(model_id: int, db=Depends(get_db)):
    """Get all versions of model"""
    model = db.query(MLModel).filter(MLModel.id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    
    versions = db.query(ModelVersion).filter(
        ModelVersion.model_id == model_id
    ).order_by(ModelVersion.created_at.desc()).all()
    
    return [
        {
            "version_id": v.id,
            "version": v.version,
            "deployed": v.deployed,
            "metrics": json.loads(v.metrics),
            "deployment_date": v.deployment_date,
            "created_at": v.created_at
        }
        for v in versions
    ]

@app.get("/models/{model_id}/features")
async def get_model_features(model_id: int, db=Depends(get_db)):
    """Get top features for model"""
    model = db.query(MLModel).filter(MLModel.id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    
    features = db.query(ModelFeature).filter(
        ModelFeature.model_id == model_id
    ).order_by(ModelFeature.importance_score.desc()).limit(20).all()
    
    return [
        {
            "feature_name": f.feature_name,
            "feature_type": f.feature_type,
            "importance": f.importance_score
        }
        for f in features
    ]

@app.get("/metrics")
async def get_service_metrics(db=Depends(get_db)):
    """Get service metrics"""
    model_count = db.query(MLModel).count()
    active_models = db.query(MLModel).filter(MLModel.status == "active").count()
    prediction_count = db.query(Prediction).count()
    avg_confidence = db.query(
        db.func.avg(Prediction.confidence)
    ).scalar() or 0.0
    avg_latency = db.query(
        db.func.avg(Prediction.latency_ms)
    ).scalar() or 0.0
    
    return {
        "models_registered": model_count,
        "models_active": active_models,
        "predictions_made": prediction_count,
        "avg_confidence": float(avg_confidence),
        "avg_latency_ms": float(avg_latency),
        "timestamp": datetime.utcnow().isoformat()
    }

if __name__ == "__main__":
    init_db()
    uvicorn.run(app, host="0.0.0.0", port=8000)
