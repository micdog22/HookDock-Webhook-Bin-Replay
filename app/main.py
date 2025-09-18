import os, datetime
from typing import Optional
import httpx
from fastapi import FastAPI, Request, Depends, HTTPException, Form, Body
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import select, desc, func, or_, cast, String
from sqlalchemy.orm import Session
from dotenv import load_dotenv

from .db import Base, engine, SessionLocal
from .models import Bin, Event
from .schemas import BinCreate, BinOut, ReplayIn
from .utils import gen_bin_id

load_dotenv()
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "").strip()

app = FastAPI(title="HookDock")
templates = Jinja2Templates(directory="app/templates")
app.mount("/static", StaticFiles(directory="app/static"), name="static")

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/", response_class=HTMLResponse)
def home(request: Request, db: Session = Depends(get_db)):
    rows = db.execute(
        select(Bin.id, Bin.name, func.count(Event.id))
        .outerjoin(Event).group_by(Bin.id).order_by(desc(Bin.created_at))
    ).all()
    bins = [type("Row", (), dict(id=r[0], name=r[1], events_count=r[2])) for r in rows]
    return templates.TemplateResponse("index.html", {"request": request, "bins": bins})

@app.post("/bins")
def create_bin(name: Optional[str] = Form(None), token: Optional[str] = Form(None), db: Session = Depends(get_db)):
    if ADMIN_TOKEN and token != ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="ADMIN_TOKEN inválido")
    bid = gen_bin_id(8)
    b = Bin(id=bid, name=name or None)
    db.add(b); db.commit()
    return RedirectResponse(url=f"/bins/{bid}", status_code=303)

@app.post("/bins/{bin_id}/delete")
def delete_bin(bin_id: str, token: Optional[str] = Form(None), db: Session = Depends(get_db)):
    if ADMIN_TOKEN and token != ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="ADMIN_TOKEN inválido")
    b = db.get(Bin, bin_id)
    if not b:
        raise HTTPException(status_code=404, detail="Bin não encontrado")
    db.delete(b); db.commit()
    return RedirectResponse(url="/", status_code=303)

@app.get("/bins/{bin_id}", response_class=HTMLResponse)
def bin_page(bin_id: str, request: Request, q: Optional[str] = None, db: Session = Depends(get_db)):
    b = db.get(Bin, bin_id)
    if not b:
        raise HTTPException(status_code=404, detail="Bin não encontrado")
    stmt = select(Event).where(Event.bin_id == bin_id).order_by(desc(Event.created_at))
    if q:
        stmt = stmt.filter(or_(Event.body.ilike(f"%{q}%"), cast(Event.headers, String).ilike(f"%{q}%")))
    events = db.scalars(stmt).all()
    return templates.TemplateResponse("bin.html", {"request": request, "bin": b, "events": events, "q": q})

@app.api_route("/i/{bin_id}", methods=["GET","POST","PUT","PATCH","DELETE","HEAD","OPTIONS"])
async def ingest(bin_id: str, request: Request, db: Session = Depends(get_db)):
    b = db.get(Bin, bin_id)
    if not b:
        raise HTTPException(status_code=404, detail="Bin não encontrado")
    raw = await request.body()
    try:
        body_text = raw.decode("utf-8", errors="replace")
    except Exception:
        body_text = ""
    headers = {k:v for k,v in request.headers.items()}
    q = dict(request.query_params)
    ip = request.client.host if request.client else None
    e = Event(bin_id=bin_id, method=request.method[:8], path=request.url.path, ip=ip, headers=headers, query=q, body=body_text)
    db.add(e); db.commit(); db.refresh(e)
    return {"status":"ok","event_id":e.id}

# API
@app.post("/api/bins", response_model=BinOut)
def api_create_bin(payload: BinCreate = Body(...), token: Optional[str] = None, db: Session = Depends(get_db)):
    if ADMIN_TOKEN and token != ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="ADMIN_TOKEN inválido")
    bid = gen_bin_id(8)
    b = Bin(id=bid, name=payload.name or None)
    db.add(b); db.commit()
    return BinOut(id=bid, name=b.name, ingest_url=f"/i/{bid}")

@app.get("/api/bins")
def api_list_bins(db: Session = Depends(get_db)):
    rows = db.execute(select(Bin.id, Bin.name, func.count(Event.id)).outerjoin(Event).group_by(Bin.id).order_by(desc(Bin.created_at))).all()
    return [{"id": r[0], "name": r[1], "events": r[2]} for r in rows]

@app.delete("/api/bins/{bin_id}")
def api_delete_bin(bin_id: str, token: Optional[str] = None, db: Session = Depends(get_db)):
    if ADMIN_TOKEN and token != ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="ADMIN_TOKEN inválido")
    b = db.get(Bin, bin_id)
    if not b:
        raise HTTPException(status_code=404, detail="Bin não encontrado")
    db.delete(b); db.commit()
    return {"status":"deleted"}

@app.get("/api/bins/{bin_id}/events")
def api_list_events(bin_id: str, q: Optional[str] = None, db: Session = Depends(get_db)):
    if not db.get(Bin, bin_id):
        raise HTTPException(status_code=404, detail="Bin não encontrado")
    stmt = select(Event).where(Event.bin_id == bin_id).order_by(desc(Event.created_at))
    if q:
        stmt = stmt.filter(or_(Event.body.ilike(f"%{q}%"), cast(Event.headers, String).ilike(f"%{q}%")))
    items = db.scalars(stmt.limit(200)).all()
    return [{"id": e.id, "created_at": e.created_at.isoformat(), "method": e.method, "path": e.path, "ip": e.ip} for e in items]

@app.get("/api/events/{event_id}")
def api_event_detail(event_id: int, db: Session = Depends(get_db)):
    e = db.get(Event, event_id)
    if not e:
        raise HTTPException(status_code=404, detail="Evento não encontrado")
    return {"id": e.id, "bin_id": e.bin_id, "created_at": e.created_at.isoformat(), "method": e.method, "path": e.path, "ip": e.ip, "headers": e.headers, "query": e.query, "body": e.body}

@app.post("/replay/{event_id}")
async def replay_form(event_id: int, target_url: str = Form(...), db: Session = Depends(get_db)):
    await do_replay(event_id, target_url, db)
    b = db.get(Event, event_id)
    return RedirectResponse(url=f"/bins/{b.bin_id}", status_code=303)

@app.post("/api/events/{event_id}/replay")
async def api_replay(event_id: int, payload: ReplayIn, db: Session = Depends(get_db)):
    return await do_replay(event_id, payload.target_url, db)

async def do_replay(event_id: int, target_url: str, db: Session):
    e = db.get(Event, event_id)
    if not e:
        raise HTTPException(status_code=404, detail="Evento não encontrado")
    blocked = {"host","content-length","connection","keep-alive","proxy-authenticate","proxy-authorization","te","trailers","transfer-encoding","upgrade"}
    headers = {k:v for k,v in (e.headers or {}).items() if k.lower() not in blocked}
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.request(e.method or "POST", target_url, headers=headers, content=(e.body or "").encode("utf-8"))
    e.last_replay_status = r.status_code
    e.last_replay_at = datetime.datetime.now(datetime.timezone.utc)
    db.add(e); db.commit()
    return {"status": r.status_code, "text": r.text[:1000]}
