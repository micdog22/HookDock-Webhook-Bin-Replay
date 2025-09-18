from sqlalchemy import Integer, String, Text, DateTime, JSON, func, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .db import Base

class Bin(Base):
    __tablename__ = "bins"
    id: Mapped[str] = mapped_column(String(16), primary_key=True)
    name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped["DateTime"] = mapped_column(DateTime(timezone=True), server_default=func.now())
    events: Mapped[list["Event"]] = relationship("Event", back_populates="bin", cascade="all, delete-orphan")

class Event(Base):
    __tablename__ = "events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    bin_id: Mapped[str] = mapped_column(ForeignKey("bins.id", ondelete="CASCADE"), index=True)
    created_at: Mapped["DateTime"] = mapped_column(DateTime(timezone=True), server_default=func.now())
    method: Mapped[str] = mapped_column(String(8))
    path: Mapped[str] = mapped_column(String(512))
    ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    headers: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    query: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_replay_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_replay_at: Mapped["DateTime | None"] = mapped_column(DateTime(timezone=True), nullable=True)
    bin: Mapped["Bin"] = relationship("Bin", back_populates="events")
