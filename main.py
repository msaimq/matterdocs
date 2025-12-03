from __future__ import annotations

import os
import tempfile
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
import base64
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
        print("✅ Storage directory created")
        
        # Try database initialization (non-blocking)
        try:
            await init_db()
            await seed_data()
            print("✅ Database initialized successfully")
        except Exception as db_error:
            print(f"⚠️ Database initialization failed: {db_error}")
            print("ℹ️ App will continue without database (add PostgreSQL to Railway)")
            
    except Exception as e:
        print(f"⚠️ Startup warning: {e}")
    
    print("✅ MatterDocs startup completed")


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


@app.get("/api/matters/list")
async def list_matters_api(session: AsyncSession = Depends(get_session)):
    """API endpoint to get all matters for dropdown selection."""
    result = await session.execute(
        select(Matter, Client.name.label('client_name'))
        .join(Client)
        .order_by(Client.name, Matter.name)
    )
    matters = []
    for matter, client_name in result.all():
        matters.append({
            "id": matter.id,
            "name": matter.name,
            "client_name": client_name
        })
    return matters


@app.post("/api/matters/create")
async def create_matter(
    request: Request,
    session: AsyncSession = Depends(get_session)
):
    """Create a new client and matter."""
    data = await request.json()
    client_name = data.get('clientName', '').strip()
    matter_name = data.get('matterName', '').strip()
    
    if not client_name or not matter_name:
        raise HTTPException(status_code=400, detail="Client name and matter name are required")
    
    # Check if client exists, create if not
    client_result = await session.execute(
        select(Client).where(Client.name == client_name)
    )
    client = client_result.scalars().first()
    
    if not client:
        client = Client(name=client_name)
        session.add(client)
        await session.flush()
    
    # Create matter
    matter = Matter(client_id=client.id, name=matter_name)
    session.add(matter)
    await session.flush()
    
    await session.commit()
    
    return {
        "success": True,
        "client": {"id": client.id, "name": client.name},
        "matter": {"id": matter.id, "name": matter.name}
    }


@app.get("/api/documents/recent")
async def get_recent_documents(session: AsyncSession = Depends(get_session)):
    """Get recently created documents."""
    result = await session.execute(
        select(Document, Client.name.label('client_name'), Matter.name.label('matter_name'))
        .join(Matter)
        .join(Client)
        .order_by(Document.created_at.desc())
        .limit(10)
    )
    
    documents = []
    for document, client_name, matter_name in result.all():
        documents.append({
            "id": document.id,
            "title": document.title,
            "client_name": client_name,
            "matter_name": matter_name,
            "created_at": document.created_at.isoformat()
        })
    
    return documents


@app.post("/api/email/save")
async def save_email(
    request: Request,
    session: AsyncSession = Depends(get_session)
):
    """Save email content as a document."""
    data = await request.json()
    matter_id = int(data.get('matterId'))  # Convert to integer
    subject = data.get('subject', 'No Subject')
    from_addr = data.get('from', '')
    date = data.get('date', '')
    body = data.get('body', '')
    document_type = data.get('documentType', 'Email')
    
    # Verify matter exists
    matter_result = await session.execute(
        select(Matter).where(Matter.id == matter_id)
    )
    matter = matter_result.scalars().first()
    if not matter:
        raise HTTPException(status_code=404, detail="Matter not found")
    
    # Create email document
    email_content = f"From: {from_addr}\nDate: {date}\nSubject: {subject}\n\n{body}"
    document_title = f"{document_type}: {subject[:50]}..."
    
    # Check if document already exists
    doc_result = await session.execute(
        select(Document).where(Document.matter_id == matter.id, Document.title == document_title)
    )
    document = doc_result.scalars().first()
    
    if document:
        # Create new version
        version_result = await session.execute(
            select(DocumentVersion)
            .where(DocumentVersion.document_id == document.id)
            .order_by(DocumentVersion.version_number.desc())
            .limit(1)
        )
        latest_version = version_result.scalars().first()
        next_version_number = (latest_version.version_number if latest_version else 0) + 1
    else:
        # Create new document
        document = Document(matter_id=matter.id, title=document_title)
        session.add(document)
        await session.flush()
        next_version_number = 1
    
    # Generate AI summary
    summary, tags = await summarize_text(email_content)
    
    # Save document version
    doc_version = DocumentVersion(
        document_id=document.id,
        version_number=next_version_number,
        file_path=f"email_{document.id}_{next_version_number}.txt",
        summary=summary,
    )
    session.add(doc_version)
    await session.flush()
    
    # Add tags
    for tag_name in tags:
        tag_result = await session.execute(select(Tag).where(Tag.name == tag_name))
        tag_obj = tag_result.scalars().first()
        if tag_obj is None:
            tag_obj = Tag(name=tag_name)
            session.add(tag_obj)
            await session.flush()
        session.add(DocumentTag(document_version_id=doc_version.id, tag_id=tag_obj.id))
    
    await session.commit()
    
    return {"success": True, "document_id": document.id, "summary": summary}


@app.post("/api/attachments/save")
async def save_attachment(
    request: Request,
    session: AsyncSession = Depends(get_session)
):
    """Save email attachment as a document."""
    data = await request.json()
    matter_id = int(data.get('matterId'))  # Convert to integer
    name = data.get('name')
    content = data.get('content')  # Base64 encoded
    content_type = data.get('contentType')
    document_type = data.get('documentType', 'Attachment')
    
    # Verify matter exists
    matter_result = await session.execute(
        select(Matter).where(Matter.id == matter_id)
    )
    matter = matter_result.scalars().first()
    if not matter:
        raise HTTPException(status_code=404, detail="Matter not found")
    
    # Decode attachment content
    import base64
    try:
        file_bytes = base64.b64decode(content)
    except Exception as e:
        raise HTTPException(status_code=400, detail="Invalid attachment content")
    
    # Create document
    document_title = f"{document_type}: {name}"
    
    # Check if document already exists
    doc_result = await session.execute(
        select(Document).where(Document.matter_id == matter.id, Document.title == document_title)
    )
    document = doc_result.scalars().first()
    
    if document:
        # Create new version
        version_result = await session.execute(
            select(DocumentVersion)
            .where(DocumentVersion.document_id == document.id)
            .order_by(DocumentVersion.version_number.desc())
            .limit(1)
        )
        latest_version = version_result.scalars().first()
        next_version_number = (latest_version.version_number if latest_version else 0) + 1
    else:
        # Create new document
        document = Document(matter_id=matter.id, title=document_title)
        session.add(document)
        await session.flush()
        next_version_number = 1
    
    # Save file to storage
    storage_dir = STORAGE_ROOT / str(matter.client_id) / str(matter.id) / str(document.id) / str(next_version_number)
    storage_dir.mkdir(parents=True, exist_ok=True)
    file_path = storage_dir / name
    file_path.write_bytes(file_bytes)
    
    # Extract text for AI processing
    try:
        text_content = file_bytes.decode('utf-8', errors='ignore')
    except:
        text_content = f"Binary file: {name}"
    
    # Generate AI summary
    summary, tags = await summarize_text(text_content)
    
    # Save document version
    doc_version = DocumentVersion(
        document_id=document.id,
        version_number=next_version_number,
        file_path=str(file_path),
        summary=summary,
    )
    session.add(doc_version)
    await session.flush()
    
    # Add tags
    for tag_name in tags:
        tag_result = await session.execute(select(Tag).where(Tag.name == tag_name))
        tag_obj = tag_result.scalars().first()
        if tag_obj is None:
            tag_obj = Tag(name=tag_name)
            session.add(tag_obj)
            await session.flush()
        session.add(DocumentTag(document_version_id=doc_version.id, tag_id=tag_obj.id))
    
    await session.commit()
    
    return {"success": True, "document_id": document.id, "summary": summary}


@app.get("/api/documents/{document_id}/versions/{version_number}/download")
async def download_document(
    document_id: int,
    version_number: int,
    session: AsyncSession = Depends(get_session)
):
    """Download a specific document version."""
    result = await session.execute(
        select(DocumentVersion, Document.title)
        .join(Document)
        .where(
            DocumentVersion.document_id == document_id,
            DocumentVersion.version_number == version_number
        )
    )
    version_data = result.first()
    
    if not version_data:
        raise HTTPException(status_code=404, detail="Document version not found")
    
    version, title = version_data
    file_path = Path(version.file_path)
    
    # Check if file exists on disk
    if not file_path.exists():
        # For Railway: Files are lost on restart, so create a text file with summary
        content = f"Document: {title}\nVersion: {version_number}\nSummary: {version.summary}\n\nNote: Original file not available (Railway storage limitation)"
        
        # Create temporary file
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as temp_file:
            temp_file.write(content)
            temp_path = temp_file.name
        
        return FileResponse(
            path=temp_path,
            filename=f"{title}_v{version_number}_summary.txt",
            media_type='text/plain'
        )
    
    return FileResponse(
        path=file_path,
        filename=f"{title}_v{version_number}{file_path.suffix}",
        media_type='application/octet-stream'
    )


@app.get("/api/documents/{document_id}/versions/{version_number}/preview")
async def preview_document(
    document_id: int,
    version_number: int,
    session: AsyncSession = Depends(get_session)
):
    """Preview a specific document version."""
    result = await session.execute(
        select(DocumentVersion, Document.title)
        .join(Document)
        .where(
            DocumentVersion.document_id == document_id,
            DocumentVersion.version_number == version_number
        )
    )
    version_data = result.first()
    
    if not version_data:
        raise HTTPException(status_code=404, detail="Document version not found")
    
    version, title = version_data
    file_path = Path(version.file_path)
    
    # Try to read file content for preview
    content = "File not available (Railway storage limitation)"
    if file_path.exists():
        try:
            if file_path.suffix.lower() in ['.txt', '.md', '.csv']:
                content = file_path.read_text(encoding='utf-8', errors='ignore')
            elif 'email' in title.lower():
                content = file_path.read_text(encoding='utf-8', errors='ignore')
            else:
                content = f"Binary file: {file_path.name}\nSize: {file_path.stat().st_size} bytes"
        except Exception as e:
            content = f"Error reading file: {str(e)}"
    else:
        # Show summary instead of file content
        content = f"Original file not available.\n\nDocument Summary:\n{version.summary}\n\nNote: Files are not persisted on Railway. Consider using cloud storage (AWS S3, etc.) for production."
    
    return {
        "title": title,
        "version": version_number,
        "summary": version.summary,
        "created_at": version.created_at.isoformat(),
        "content": content[:5000]  # Limit preview to 5000 chars
    }


@app.get("/api/documents/{document_id}/versions")
async def get_document_versions(
    document_id: int,
    session: AsyncSession = Depends(get_session)
):
    """Get all versions of a document."""
    result = await session.execute(
        select(DocumentVersion)
        .where(DocumentVersion.document_id == document_id)
        .order_by(DocumentVersion.version_number.desc())
    )
    versions = result.scalars().all()
    
    if not versions:
        raise HTTPException(status_code=404, detail="Document not found")
    
    return [
        {
            "version_number": version.version_number,
            "summary": version.summary,
            "created_at": version.created_at.isoformat(),
            "file_path": version.file_path
        }
        for version in versions
    ]


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
    
    # For Railway: Store file content in database instead of filesystem
    # TODO: In production, use cloud storage (AWS S3, Cloudinary, etc.)
    storage_dir = STORAGE_ROOT / str(matter.client_id) / str(matter.id) / str(document.id) / str(next_version_number)
    storage_dir.mkdir(parents=True, exist_ok=True)
    file_path = storage_dir / file.filename
    
    # Store file (will be lost on Railway, but works for demo)
    file_path.write_bytes(file_bytes)

    try:
        text_content = file_bytes.decode(errors="ignore")
    except Exception:
        text_content = ""
    if not text_content:
        text_content = "No textual content extracted from this file."

    summary, tags = await summarize_text(text_content)

    # Store file metadata and content
    doc_version = DocumentVersion(
        document_id=document.id,
        version_number=next_version_number,
        file_path=str(file_path),  # Note: This path won't persist on Railway
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
