from __future__ import annotations

import os
from pathlib import Path
from typing import List, Tuple

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ai import summarize_text
from db import async_session_maker, init_db
from models import Client, Document, DocumentTag, DocumentVersion, Matter, Tag


app = FastAPI(title="MatterDocs")
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")
STORAGE_ROOT = Path(os.getenv("STORAGE_ROOT", "storage"))


async def get_session() -> AsyncSession:
    async with async_session_maker() as session:
        yield session


@app.on_event("startup")
async def on_startup() -> None:
    try:
        # Ensure storage directory exists
        STORAGE_ROOT.mkdir(parents=True, exist_ok=True)
        
        # Initialize database
        await init_db()
        await seed_data()
        print("✅ Application startup completed successfully")
    except Exception as e:
        print(f"❌ Startup error: {e}")


async def seed_data() -> None:
    async with async_session_maker() as session:
        result = await session.execute(select(func.count(Client.id)))
        (client_count,) = result.one()
        if client_count == 0:
            acme = Client(name="Acme LLP")
            globex = Client(name="Globex Law")
            session.add_all([acme, globex])
            await session.flush()

            session.add_all(
                [
                    Matter(client_id=acme.id, name="M and A Transaction"),
                    Matter(client_id=globex.id, name="Litigation Case"),
                ]
            )
            await session.commit()


@app.get("/health")
async def health_check():
    """Health check endpoint for Railway."""
    return {"status": "healthy", "service": "MatterDocs"}

@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/addin/taskpane", response_class=HTMLResponse)
async def addin_taskpane(request: Request) -> HTMLResponse:
    """Lightweight taskpane page for the Outlook add-in that links to MatterDocs."""
    return templates.TemplateResponse("addin_taskpane.html", {"request": request})


@app.get("/addin/commands", response_class=HTMLResponse)
async def addin_commands(request: Request) -> HTMLResponse:
    """Function file hosting Office.js commands."""
    return templates.TemplateResponse("addin_commands.html", {"request": request})


@app.get("/matterdocs-outlook-manifest.xml")
async def serve_manifest() -> FileResponse:
    """Serve the Outlook add-in manifest over HTTPS for Add-from-URL installs."""
    manifest_path = Path("matterdocs-outlook-manifest.xml")
    if not manifest_path.exists():
        raise HTTPException(status_code=404, detail="Manifest not found")
    return FileResponse(manifest_path, media_type="application/xml")


@app.get("/matters", response_class=HTMLResponse)
async def list_matters(request: Request, session: AsyncSession = Depends(get_session)) -> HTMLResponse:
    result = await session.execute(
        select(Matter).options(selectinload(Matter.client)).order_by(Matter.id)
    )
    matters = result.scalars().all()
    return templates.TemplateResponse("matters.html", {"request": request, "matters": matters})


@app.get("/matters/{matter_id}", response_class=HTMLResponse)
async def matter_detail(
    request: Request, matter_id: int, session: AsyncSession = Depends(get_session)
) -> HTMLResponse:
    result = await session.execute(
        select(Matter)
        .where(Matter.id == matter_id)
        .options(selectinload(Matter.client), selectinload(Matter.documents))
    )
    matter = result.scalars().first()
    if matter is None:
        raise HTTPException(status_code=404, detail="Matter not found")

    documents_with_versions: List[Tuple[Document, DocumentVersion | None]] = []
    for document in matter.documents:
        version_result = await session.execute(
            select(DocumentVersion)
            .where(DocumentVersion.document_id == document.id)
            .order_by(DocumentVersion.version_number.desc())
            .limit(1)
        )
        latest_version = version_result.scalars().first()
        documents_with_versions.append((document, latest_version))

    context = {
        "request": request,
        "matter": matter,
        "client": matter.client,
        "documents_with_versions": documents_with_versions,
    }
    return templates.TemplateResponse("matter_detail.html", context)


@app.post("/matters/{matter_id}/upload")
async def upload_document(
    matter_id: int,
    title: str = Form(...),
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
) -> RedirectResponse:
    matter_result = await session.execute(
        select(Matter)
        .where(Matter.id == matter_id)
        .options(selectinload(Matter.client))
    )
    matter = matter_result.scalars().first()
    if matter is None:
        raise HTTPException(status_code=404, detail="Matter not found")

    doc_result = await session.execute(
        select(Document).where(Document.matter_id == matter.id, Document.title == title)
    )
    document = doc_result.scalars().first()

    if document:
        version_result = await session.execute(
            select(DocumentVersion)
            .where(DocumentVersion.document_id == document.id)
            .order_by(DocumentVersion.version_number.desc())
            .limit(1)
        )
        latest_version = version_result.scalars().first()
        next_version_number = (latest_version.version_number if latest_version else 0) + 1
    else:
        document = Document(matter_id=matter.id, title=title)
        session.add(document)
        await session.flush()
        next_version_number = 1

    file_bytes = await file.read()
    storage_dir = STORAGE_ROOT / str(matter.client_id) / str(matter.id) / str(document.id) / str(next_version_number)
    storage_dir.mkdir(parents=True, exist_ok=True)
    file_path = storage_dir / file.filename
    file_path.write_bytes(file_bytes)

    try:
        text_content = file_bytes.decode(errors="ignore")
    except Exception:
        text_content = ""
    if not text_content:
        text_content = "No textual content extracted from this file."

    summary, tags = await summarize_text(text_content)

    doc_version = DocumentVersion(
        document_id=document.id,
        version_number=next_version_number,
        file_path=str(file_path),
        summary=summary,
    )
    session.add(doc_version)
    await session.flush()

    for tag_name in tags:
        tag_result = await session.execute(select(Tag).where(Tag.name == tag_name))
        tag_obj = tag_result.scalars().first()
        if tag_obj is None:
            tag_obj = Tag(name=tag_name)
            session.add(tag_obj)
            await session.flush()
        session.add(DocumentTag(document_version_id=doc_version.id, tag_id=tag_obj.id))

    await session.commit()
    return RedirectResponse(url=f"/matters/{matter.id}", status_code=303)


# Local development instructions:
# 1. python -m venv .venv
# 2. .venv\\Scripts\\activate
# 3. pip install fastapi uvicorn sqlalchemy aiosqlite jinja2 python-multipart python-dotenv
# 4. uvicorn main:app --reload

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
