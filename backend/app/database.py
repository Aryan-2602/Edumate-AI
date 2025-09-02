from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.sql import func
from datetime import datetime
from app.config import settings

# Database engine
engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, index=True)  # Firebase UID
    email = Column(String, unique=True, index=True)
    display_name = Column(String)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    documents = relationship("Document", back_populates="user")
    questions = relationship("Question", back_populates="user")
    quizzes = relationship("Quiz", back_populates="user")
    progress = relationship("UserProgress", back_populates="user")


class Document(Base):
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"))
    title = Column(String, nullable=False)
    file_name = Column(String, nullable=False)
    file_path = Column(String, nullable=False)  # S3 path
    file_size = Column(Integer)
    file_type = Column(String)
    content_summary = Column(Text)
    chunk_count = Column(Integer, default=0)
    is_processed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="documents")
    chunks = relationship("DocumentChunk", back_populates="document")


class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"))
    chunk_index = Column(Integer)
    content = Column(Text, nullable=False)
    embedding_id = Column(String)  # Chroma embedding ID
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    document = relationship("Document", back_populates="chunks")


class Question(Base):
    __tablename__ = "questions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"))
    question_text = Column(Text, nullable=False)
    answer_text = Column(Text)
    source_documents = Column(Text)  # JSON array of document IDs
    confidence_score = Column(Float)
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="questions")


class Quiz(Base):
    __tablename__ = "quizzes"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"))
    title = Column(String, nullable=False)
    description = Column(Text)
    source_document_id = Column(Integer, ForeignKey("documents.id"))
    question_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="quizzes")
    questions = relationship("QuizQuestion", back_populates="quiz")


class QuizQuestion(Base):
    __tablename__ = "quiz_questions"
    
    id = Column(Integer, primary_key=True, index=True)
    quiz_id = Column(Integer, ForeignKey("quizzes.id"))
    question_text = Column(Text, nullable=False)
    correct_answer = Column(String, nullable=False)
    options = Column(Text)  # JSON array of options
    explanation = Column(Text)
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    quiz = relationship("Quiz", back_populates="questions")


class UserProgress(Base):
    __tablename__ = "user_progress"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"))
    document_id = Column(Integer, ForeignKey("documents.id"))
    questions_asked = Column(Integer, default=0)
    quizzes_taken = Column(Integer, default=0)
    flashcards_reviewed = Column(Integer, default=0)
    study_time_minutes = Column(Integer, default=0)
    last_studied = Column(DateTime, default=func.now())
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="progress")


# Database dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Create tables
def create_tables():
    Base.metadata.create_all(bind=engine)
