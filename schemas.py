"""
Database Schemas for Past Exam Paper app

Each Pydantic model represents a collection in MongoDB. The collection name
is the lowercase of the class name (e.g., Exam -> "exam").
"""

from pydantic import BaseModel, Field
from typing import List, Optional


class Exam(BaseModel):
    """Exam metadata (collection: exam)"""
    title: str = Field(..., description="Exam title")
    subject: str = Field(..., description="Subject name, e.g., Mathematics")
    year: int = Field(..., description="Exam year")
    description: Optional[str] = Field(None, description="Short description of the exam")
    duration_minutes: int = Field(60, description="Suggested duration in minutes")
    total_questions: Optional[int] = Field(None, description="Number of questions in the exam")


class Question(BaseModel):
    """Multiple-choice question for an exam (collection: question)"""
    exam_id: str = Field(..., description="Reference to Exam _id as string")
    prompt: str = Field(..., description="Question prompt text")
    options: List[str] = Field(..., min_items=2, description="List of answer options")
    answer_index: int = Field(..., ge=0, description="Index of the correct option in options list")
    marks: int = Field(1, ge=0, description="Marks awarded for a correct answer")


class Attempt(BaseModel):
    """A user's attempt on an exam (collection: attempt)"""
    exam_id: str = Field(..., description="Reference to Exam _id as string")
    user_name: Optional[str] = Field(None, description="Name or identifier of the test taker")
    answers: List[int] = Field(..., description="Selected option index for each question (by position)")
    score: int = Field(0, ge=0, description="Total score achieved")
    max_score: int = Field(0, ge=0, description="Maximum possible score for this attempt")
