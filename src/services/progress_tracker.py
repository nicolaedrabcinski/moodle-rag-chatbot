"""
Progress tracker for document processing with SSE support.
"""

import asyncio
import json
from typing import AsyncGenerator, Dict, Optional
from datetime import datetime


class ProgressTracker:
    """Track and broadcast progress updates."""
    
    def __init__(self):
        self.sessions: Dict[str, asyncio.Queue] = {}
    
    def create_session(self, session_id: str) -> asyncio.Queue:
        """Create a new progress tracking session."""
        queue = asyncio.Queue()
        self.sessions[session_id] = queue
        return queue
    
    def remove_session(self, session_id: str):
        """Remove a progress tracking session."""
        if session_id in self.sessions:
            del self.sessions[session_id]
    
    async def emit(self, session_id: str, event_type: str, data: dict):
        """Emit a progress event to a specific session."""
        if session_id in self.sessions:
            event = {
                "type": event_type,
                "timestamp": datetime.utcnow().isoformat(),
                **data
            }
            await self.sessions[session_id].put(event)
    
    async def stream_progress(self, session_id: str) -> AsyncGenerator[str, None]:
        """Stream progress events as SSE."""
        queue = self.create_session(session_id)
        
        try:
            while True:
                try:
                    # Wait for next event with timeout
                    event = await asyncio.wait_for(queue.get(), timeout=30.0)
                    
                    # Format as SSE
                    yield f"data: {json.dumps(event)}\n\n"
                    
                    # If it's a completion event, stop streaming
                    if event.get("type") in ["complete", "error"]:
                        break
                        
                except asyncio.TimeoutError:
                    # Send keepalive
                    yield f": keepalive\n\n"
                    
        finally:
            self.remove_session(session_id)


# Global instance
_progress_tracker: Optional[ProgressTracker] = None


def get_progress_tracker() -> ProgressTracker:
    """Get progress tracker instance."""
    global _progress_tracker
    
    if _progress_tracker is None:
        _progress_tracker = ProgressTracker()
    
    return _progress_tracker
