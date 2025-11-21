import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from bson import ObjectId

from database import db, create_document, get_documents
from schemas import Exam, Question, Attempt

app = FastAPI(title="Past Exam Paper API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Helpers
class ObjectIdStr(BaseModel):
    id: str


def to_str_id(doc):
    if not doc:
        return doc
    d = dict(doc)
    if d.get("_id") is not None:
        d["id"] = str(d.pop("_id"))
    return d


@app.get("/")
def read_root():
    return {"message": "Past Exam Paper API running"}


@app.get("/api/exams")
def list_exams():
    try:
        exams = get_documents("exam")
        # Count questions per exam
        result = []
        for e in exams:
            exam_id = str(e.get("_id"))
            q_count = db["question"].count_documents({"exam_id": exam_id}) if db else 0
            e = to_str_id(e)
            e["total_questions"] = q_count
            result.append(e)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/exams", response_model=dict)
def create_exam(exam: Exam):
    try:
        inserted_id = create_document("exam", exam)
        return {"id": inserted_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class CreateQuestion(BaseModel):
    exam_id: str
    prompt: str
    options: List[str]
    answer_index: int
    marks: int = 1


@app.post("/api/questions", response_model=dict)
def add_question(q: CreateQuestion):
    # Validate exam exists
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    if not db["exam"].find_one({"_id": ObjectId(q.exam_id)}):
        raise HTTPException(status_code=404, detail="Exam not found")
    try:
        inserted_id = create_document("question", q.model_dump())
        return {"id": inserted_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/exams/{exam_id}/questions")
def list_questions(exam_id: str):
    try:
        qs = get_documents("question", {"exam_id": exam_id})
        return [to_str_id(q) for q in qs]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class SubmitAttempt(BaseModel):
    exam_id: str
    user_name: Optional[str] = None
    answers: List[int]


@app.post("/api/attempts", response_model=dict)
def submit_attempt(payload: SubmitAttempt):
    try:
        qs = list(db["question"].find({"exam_id": payload.exam_id}).sort("_id")) if db else []
        if not qs:
            raise HTTPException(status_code=400, detail="No questions for this exam")
        score = 0
        max_score = 0
        for idx, q in enumerate(qs):
            marks = int(q.get("marks", 1))
            max_score += marks
            if idx < len(payload.answers) and payload.answers[idx] == q.get("answer_index"):
                score += marks
        attempt = Attempt(
            exam_id=payload.exam_id,
            user_name=payload.user_name,
            answers=payload.answers,
            score=score,
            max_score=max_score,
        )
        inserted_id = create_document("attempt", attempt)
        return {"id": inserted_id, "score": score, "max_score": max_score}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/exams/{exam_id}/attempts")
def get_attempts(exam_id: str):
    try:
        atts = get_documents("attempt", {"exam_id": exam_id})
        return [to_str_id(a) for a in atts]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
    return response


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
