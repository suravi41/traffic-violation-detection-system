from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=False)
    role = Column(String, default="officer")


class Detection(Base):
    __tablename__ = "detections"

    id = Column(Integer, primary_key=True, index=True)
    image_name = Column(String, nullable=False)
    helmet_count = Column(Integer, default=0)
    plate_count = Column(Integer, default=0)
    violation = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    plates = relationship("Plate", back_populates="detection", cascade="all, delete")
    evidence = relationship("Evidence", back_populates="detection", uselist=False, cascade="all, delete")


class Plate(Base):
    __tablename__ = "plates"

    id = Column(Integer, primary_key=True, index=True)
    detection_id = Column(Integer, ForeignKey("detections.id"))
    plate_text = Column(String, nullable=True)
    confidence = Column(String, nullable=True)

    detection = relationship("Detection", back_populates="plates")


class Evidence(Base):
    __tablename__ = "evidence"

    id = Column(Integer, primary_key=True, index=True)
    detection_id = Column(Integer, ForeignKey("detections.id"))
    json_path = Column(String, nullable=True)
    annotated_image_path = Column(String, nullable=True)

    detection = relationship("Detection", back_populates="evidence")