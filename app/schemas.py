from pydantic import BaseModel, HttpUrl
from typing import Optional

class BinCreate(BaseModel):
    name: Optional[str] = None

class BinOut(BaseModel):
    id: str
    name: Optional[str] = None
    ingest_url: str

class ReplayIn(BaseModel):
    target_url: HttpUrl
