"""
File upload API routes.
"""

import os
import shutil
from pathlib import Path
from typing import List

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from src.core.config import settings
from src.core.config.logging import LoggerAdapter
from src.services.document_processor import get_document_processor
from src.services.progress_tracker import get_progress_tracker

logger = LoggerAdapter(__name__)
router = APIRouter()


class UploadResponse(BaseModel):
    """Upload response model."""

    success: bool
    message: str
    course_id: str
    session_id: str
    files_processed: int
    chunks_created: int


class CourseInfo(BaseModel):
    """Course information model."""

    id: str
    name: str
    documents_count: int


class CoursesListResponse(BaseModel):
    """Courses list response model."""

    courses: List[CourseInfo]
    total: int


@router.post(
    "/upload",
    response_model=UploadResponse,
    summary="Upload documents",
    description="Upload and process documents for a course",
)
async def upload_documents(
    course_name: str = Form(..., description="Course name"),
    files: List[UploadFile] = File(..., description="Files to upload"),
    session_id: str = Form(None, description="Optional session ID for progress tracking"),
) -> UploadResponse:
    """
    Upload and process documents.

    Args:
        course_name: Name of the course
        files: List of files to upload
        session_id: Optional session ID for progress tracking

    Returns:
        UploadResponse with processing results

    Raises:
        HTTPException: If upload or processing fails
    """
    import uuid
    if not session_id:
        session_id = f"upload_{uuid.uuid4().hex[:8]}"
    
    progress = get_progress_tracker()
    
    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No files provided",
        )

    # Generate course ID from name
    course_id = course_name.upper().replace(" ", "-").replace("_", "-")

    # Create course directory
    course_dir = Path(settings.data_dir) / "raw" / course_id
    course_dir.mkdir(parents=True, exist_ok=True)

    total_size = sum(file.size for file in files if hasattr(file, 'size'))
    
    await progress.emit(session_id, "start", {
        "message": f"📤 Начинаем загрузку {len(files)} файлов",
        "course_name": course_name,
        "files_count": len(files)
    })
    
    logger.info(
        "📤 Starting document upload",
        course_id=course_id,
        course_name=course_name,
        files_count=len(files),
        total_size_mb=total_size / (1024 * 1024) if total_size else 0
    )

    files_processed = 0
    total_chunks = 0

    try:
        # Save uploaded files
        await progress.emit(session_id, "progress", {
            "message": f"💾 Сохраняем файлы на диск...",
            "step": "saving",
            "progress": 10
        })
        
        logger.info(f"💾 Saving {len(files)} files to disk...")
        saved_files = []
        for idx, file in enumerate(files, 1):
            file_path = course_dir / file.filename
            
            await progress.emit(session_id, "progress", {
                "message": f"💾 [{idx}/{len(files)}] Сохраняем: {file.filename}",
                "step": "saving",
                "progress": 10 + (idx / len(files) * 20)
            })
            
            logger.info(f"   [{idx}/{len(files)}] Saving: {file.filename}")
            
            # Save file
            with open(file_path, "wb") as buffer:
                content = await file.read()
                buffer.write(content)
            
            saved_files.append(str(file_path))
            files_processed += 1
            
            logger.info(
                f"   ✅ Saved: {file.filename} ({len(content) / 1024:.1f} KB)",
                filename=file.filename,
                size_kb=len(content) / 1024
            )

        # Process documents
        await progress.emit(session_id, "progress", {
            "message": f"🔄 Обрабатываем документы (извлечение текста, разбивка на фрагменты)...",
            "step": "processing",
            "progress": 30
        })
        
        processor = get_document_processor()
        
        logger.info(
            "🔄 Starting document processing (chunking + embedding + indexing)...",
            course_id=course_id
        )
        
        result = await processor.process_course(
            course_id=course_id,
            course_name=course_name,
            session_id=session_id,  # Pass session_id for detailed progress
        )
        
        total_chunks = result.get("chunks_created", 0)
        
        await progress.emit(session_id, "complete", {
            "message": f"✅ Готово! Обработано {files_processed} файлов, создано {total_chunks} фрагментов",
            "files_processed": files_processed,
            "chunks_created": total_chunks,
            "progress": 100
        })
        
        logger.info(
            "✅ Documents processed successfully!",
            course_id=course_id,
            files=files_processed,
            chunks=total_chunks,
        )

        return UploadResponse(
            success=True,
            message=f"Successfully processed {files_processed} files",
            course_id=course_id,
            session_id=session_id,
            files_processed=files_processed,
            chunks_created=total_chunks,
        )

    except Exception as e:
        await progress.emit(session_id, "error", {
            "message": f"❌ Ошибка: {str(e)}",
            "error": str(e)
        })
        
        logger.error(
            "Failed to process documents",
            course_id=course_id,
            error=str(e),
        )
        
        # Cleanup on error
        if course_dir.exists():
            try:
                shutil.rmtree(course_dir)
            except Exception as cleanup_error:
                logger.error("Failed to cleanup", error=str(cleanup_error))

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process documents: {str(e)}",
        )


@router.get(
    "/courses",
    response_model=CoursesListResponse,
    summary="List courses",
    description="Get list of all available courses with document counts",
)
async def list_courses() -> CoursesListResponse:
    """
    Get list of all courses.

    Returns:
        CoursesListResponse with courses information
    """
    try:
        processor = get_document_processor()
        courses_data = await processor.list_courses()
        
        courses = [
            CourseInfo(
                id=course["id"],
                name=course.get("name", course["id"]),
                documents_count=course.get("documents_count", 0),
            )
            for course in courses_data
        ]
        
        return CoursesListResponse(
            courses=courses,
            total=len(courses),
        )
        
    except Exception as e:
        logger.error("Failed to list courses", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list courses: {str(e)}",
        )


@router.delete(
    "/course/{course_id}",
    summary="Delete a course",
    description="Delete a course and all its documents",
)
async def delete_course(course_id: str):
    """
    Delete a course and all its documents.
    
    Args:
        course_id: Course ID to delete
        
    Returns:
        Success message
    """
    try:
        course_dir = Path(settings.data_dir) / "raw" / course_id
        
        if not course_dir.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Course not found: {course_id}"
            )
        
        # Delete files
        shutil.rmtree(course_dir)
        
        # TODO: Delete from Qdrant (need to implement in storage)
        
        logger.info(
            "Course deleted",
            course_id=course_id,
        )
        
        return {"success": True, "message": f"Course {course_id} deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete course", course_id=course_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete course: {str(e)}"
        )


@router.get(
    "/progress/{session_id}",
    summary="Stream progress updates",
    description="Get real-time progress updates for document upload via SSE",
)
async def stream_progress(session_id: str):
    """
    Stream progress updates via Server-Sent Events.
    
    Args:
        session_id: Session ID to track
        
    Returns:
        SSE stream of progress events
    """
    progress = get_progress_tracker()
    
    return StreamingResponse(
        progress.stream_progress(session_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
    )
