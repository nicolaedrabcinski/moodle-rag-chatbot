"""
Document processing service.
"""

import uuid
from pathlib import Path
from typing import Dict, List, Optional

from pypdf import PdfReader
from pdf2image import convert_from_path
import pytesseract

from src.core.config import settings
from src.core.config.logging import LoggerAdapter
from src.core.embeddings import get_embedding_service
from src.data_pipeline.storage import get_qdrant_storage

logger = LoggerAdapter(__name__)


class DocumentProcessor:
    """Document processor for handling file uploads and processing."""

    def __init__(self):
        """Initialize document processor."""
        self.data_dir = Path(settings.data_dir)
        self.raw_dir = self.data_dir / "raw"
        self.raw_dir.mkdir(parents=True, exist_ok=True)

    async def process_course(
        self,
        course_id: str,
        course_name: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> Dict[str, int]:
        """
        Process all documents in a course directory.

        Args:
            course_id: Course identifier
            course_name: Optional course name
            session_id: Optional session ID for progress tracking

        Returns:
            Dict with processing statistics
        """
        from src.services.progress_tracker import get_progress_tracker
        progress = get_progress_tracker() if session_id else None
        
        course_dir = self.raw_dir / course_id

        if not course_dir.exists():
            raise ValueError(f"Course directory not found: {course_dir}")

        logger.info(
            "Processing course documents",
            course_id=course_id,
            course_name=course_name,
            directory=str(course_dir),
        )

        # Get services
        embedding_service = get_embedding_service()
        storage = get_qdrant_storage()

        # Find all supported files
        files = list(course_dir.glob("**/*.txt"))
        files.extend(course_dir.glob("**/*.md"))
        files.extend(course_dir.glob("**/*.pdf"))
        
        total_size = sum(f.stat().st_size for f in files)
        logger.info(
            f"📁 Found {len(files)} files to process (total size: {total_size / 1024:.1f} KB)",
            course_id=course_id,
            files_count=len(files),
            total_size_kb=total_size / 1024
        )

        if not files:
            raise ValueError(f"No processable files found in {course_dir}")

        # Process files
        total_chunks = 0
        for file_idx, file_path in enumerate(files, 1):
            try:
                file_size = file_path.stat().st_size
                logger.info(
                    f"📄 [{file_idx}/{len(files)}] Processing: {file_path.name} ({file_size / 1024:.1f} KB)",
                    file=file_path.name,
                    progress=f"{file_idx}/{len(files)}",
                    size_kb=file_size / 1024
                )
                
                # Read file content
                if progress:
                    await progress.emit(session_id, "progress", {
                        "message": f"📖 [{file_idx}/{len(files)}] Читаем: {file_path.name}",
                        "step": "reading",
                        "progress": 30 + (file_idx / len(files) * 15)
                    })
                
                if file_path.suffix == '.pdf':
                    content = self._read_pdf(file_path)
                else:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                
                logger.info(f"   📖 Read {len(content)} characters from {file_path.name}")
                
                # Skip empty files
                if not content or len(content.strip()) == 0:
                    logger.warning(
                        f"   ⚠️  Skipping empty file: {file_path.name}",
                        file=file_path.name
                    )
                    continue

                # Split into chunks (simple paragraph-based splitting)
                if progress:
                    await progress.emit(session_id, "progress", {
                        "message": f"✂️  [{file_idx}/{len(files)}] Разбиваем на фрагменты: {file_path.name}",
                        "step": "chunking",
                        "progress": 45 + (file_idx / len(files) * 15)
                    })
                
                chunks = self._split_text(content)
                logger.info(f"   ✂️  Split into {len(chunks)} chunks")
                
                # Prepare points for Qdrant
                if progress:
                    await progress.emit(session_id, "progress", {
                        "message": f"🧮 [{file_idx}/{len(files)}] Генерируем эмбеддинги для {len(chunks)} фрагментов...",
                        "step": "embedding",
                        "progress": 60 + (file_idx / len(files) * 20)
                    })
                
                logger.info(f"   🧮 Generating embeddings for {len(chunks)} chunks...")
                # Encode all chunks in one batch call instead of one-by-one
                embeddings = await embedding_service.encode_documents_async(chunks)

                points = []
                for i, (chunk_text, embedding) in enumerate(zip(chunks, embeddings)):
                    point_id = str(uuid.uuid4())
                    points.append({
                        "id": point_id,
                        "vector": embedding,
                        "payload": {
                            "text": chunk_text,
                            "course_id": course_id,
                            "course_name": course_name or course_id,
                            "topic": file_path.stem,
                            "file_path": str(file_path.relative_to(course_dir)),
                            "chunk_index": i,
                        }
                    })
                
                # Store in Qdrant
                if progress:
                    await progress.emit(session_id, "progress", {
                        "message": f"💾 [{file_idx}/{len(files)}] Сохраняем в базу данных...",
                        "step": "storing",
                        "progress": 80 + (file_idx / len(files) * 15)
                    })
                
                logger.info(f"   💾 Uploading {len(points)} vectors to Qdrant...")

                vectors = [p["vector"] for p in points]
                payloads = [p["payload"] for p in points]
                ids = [p["id"] for p in points]

                await storage.upsert_points_async(vectors=vectors, payloads=payloads, ids=ids)
                total_chunks += len(chunks)
                
                logger.info(
                    f"   ✅ File processed successfully: {file_path.name} ({len(chunks)} chunks)",
                    chunks=len(chunks),
                    total_chunks_so_far=total_chunks
                )

            except Exception as e:
                logger.error(
                    f"Failed to process file: {file_path.name}",
                    error=str(e),
                )
                # Continue with other files

        logger.info(
            "Course processing completed",
            course_id=course_id,
            files=len(files),
            chunks=total_chunks,
        )

        return {
            "files_processed": len(files),
            "chunks_created": total_chunks,
        }

    def _read_pdf(self, file_path: Path) -> str:
        """
        Extract text from PDF file with OCR fallback for scanned PDFs.
        
        Args:
            file_path: Path to PDF file
            
        Returns:
            Extracted text content
        """
        try:
            # First try direct text extraction
            reader = PdfReader(file_path)
            text_parts = []
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    text_parts.append(text)
            
            extracted_text = "\n\n".join(text_parts)
            
            # If extracted text is empty or very short, try OCR
            if not extracted_text or len(extracted_text.strip()) < 100:
                logger.info(f"   🔍 PDF appears to be scanned, using OCR for {file_path.name}")
                return self._ocr_pdf(file_path)
            
            return extracted_text
            
        except Exception as e:
            logger.error(f"Failed to read PDF {file_path.name}: {e}")
            # Try OCR as last resort
            try:
                logger.info(f"   🔍 Trying OCR as fallback for {file_path.name}")
                return self._ocr_pdf(file_path)
            except Exception as ocr_error:
                logger.error(f"OCR also failed for {file_path.name}: {ocr_error}")
                raise ValueError(f"Failed to process PDF file: {e}")
    
    def _ocr_pdf(self, file_path: Path, max_pages: int = 50) -> str:
        """
        Extract text from PDF using OCR.
        
        Args:
            file_path: Path to PDF file
            max_pages: Maximum number of pages to process (to avoid timeout)
            
        Returns:
            Extracted text content
        """
        try:
            logger.info(f"   📸 Converting PDF to images for OCR...")
            
            # Convert PDF to images (limit pages to avoid memory issues)
            images = convert_from_path(
                file_path,
                dpi=200,  # Lower DPI for faster processing
                first_page=1,
                last_page=max_pages,
                grayscale=True,  # Faster processing
            )
            
            logger.info(f"   🔤 OCR processing {len(images)} pages...")
            
            text_parts = []
            for i, image in enumerate(images, 1):
                # Log progress every page for better visibility
                logger.info(f"      📄 OCR страница {i}/{len(images)}")
                
                # Perform OCR with Russian and English languages
                text = pytesseract.image_to_string(
                    image,
                    lang='rus+eng',
                    config='--psm 1'  # Automatic page segmentation with OSD
                )
                
                if text.strip():
                    text_parts.append(text)
            
            logger.info(f"   ✅ OCR completed for {file_path.name}")
            return "\n\n".join(text_parts)
            
        except Exception as e:
            logger.error(f"OCR failed for {file_path.name}: {e}")
            raise ValueError(f"Failed to OCR PDF file: {e}")

    def _split_text(self, text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
        """
        Split text into chunks.

        Args:
            text: Text to split
            chunk_size: Target chunk size in characters
            overlap: Overlap between chunks

        Returns:
            List of text chunks
        """
        # Split by paragraphs first
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        
        chunks = []
        current_chunk = ""
        
        for paragraph in paragraphs:
            # If paragraph alone is too long, split it
            if len(paragraph) > chunk_size:
                # Save current chunk if any
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    current_chunk = ""
                
                # Split long paragraph
                words = paragraph.split()
                temp_chunk = ""
                for word in words:
                    if len(temp_chunk) + len(word) + 1 <= chunk_size:
                        temp_chunk += (" " if temp_chunk else "") + word
                    else:
                        if temp_chunk:
                            chunks.append(temp_chunk.strip())
                        temp_chunk = word
                
                if temp_chunk:
                    current_chunk = temp_chunk
            
            # Normal paragraph
            elif len(current_chunk) + len(paragraph) + 2 <= chunk_size:
                current_chunk += ("\n\n" if current_chunk else "") + paragraph
            else:
                # Save current chunk and start new one
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = paragraph
        
        # Add last chunk
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks if chunks else [text]

    async def list_courses(self) -> List[Dict[str, any]]:
        """
        List all available courses.

        Returns:
            List of course information dictionaries
        """
        courses = []
        
        # Scan raw directory for courses
        if self.raw_dir.exists():
            for course_dir in self.raw_dir.iterdir():
                if course_dir.is_dir():
                    # Count documents
                    doc_count = len(list(course_dir.glob("**/*.txt")))
                    doc_count += len(list(course_dir.glob("**/*.md")))
                    doc_count += len(list(course_dir.glob("**/*.pdf")))
                    
                    courses.append({
                        "id": course_dir.name,
                        "name": course_dir.name.replace("-", " ").title(),
                        "documents_count": doc_count,
                    })

        # Get additional info from vector DB
        try:
            storage = get_qdrant_storage()
            # Just return basic info, don't need to query DB
        except Exception as e:
            logger.error("Failed to get vector DB info", error=str(e))

        return courses


# Global instance
_document_processor: Optional[DocumentProcessor] = None


def get_document_processor() -> DocumentProcessor:
    """Get document processor instance."""
    global _document_processor
    
    if _document_processor is None:
        _document_processor = DocumentProcessor()
    
    return _document_processor
