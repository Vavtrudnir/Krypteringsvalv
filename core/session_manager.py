"""
Session timeout manager for Hemliga valvet.
"""

import time
import threading
from typing import Callable, Optional


class SessionManager:
    """Manages automatic session timeout and locking."""
    
    def __init__(self, timeout_minutes: int = 15, lock_callback: Optional[Callable] = None):
        """
        Initialize session manager.
        
        Args:
            timeout_minutes: Minutes of inactivity before timeout
            lock_callback: Function to call when timeout occurs
        """
        self.timeout_minutes = timeout_minutes
        self.lock_callback = lock_callback
        self.last_activity = time.time()
        self.timeout_thread = None
        self._running = False
        self._lock = threading.Lock()
    
    def start_session(self):
        """Start monitoring session activity."""
        with self._lock:
            self.last_activity = time.time()
            self._running = True
            
        if self.timeout_thread is None or not self.timeout_thread.is_alive():
            self.timeout_thread = threading.Thread(target=self._monitor_activity, daemon=True)
            self.timeout_thread.start()
    
    def stop_session(self):
        """Stop monitoring session activity."""
        with self._lock:
            self._running = False
    
    def update_activity(self):
        """Update last activity timestamp."""
        with self._lock:
            self.last_activity = time.time()
    
    def _monitor_activity(self):
        """Monitor activity and trigger timeout."""
        while self._running:
            time.sleep(30)  # Check every 30 seconds
            
            with self._lock:
                if not self._running:
                    break
                
                current_time = time.time()
                inactive_seconds = current_time - self.last_activity
                inactive_minutes = inactive_seconds / 60
                
                if inactive_minutes >= self.timeout_minutes:
                    # Timeout occurred
                    self._running = False
                    if self.lock_callback:
                        self.lock_callback()
                    break
    
    def get_time_until_timeout(self) -> float:
        """
        Get minutes until timeout.
        
        Returns:
            Minutes until timeout, or 0 if already timed out
        """
        with self._lock:
            if not self._running:
                return 0
            
            current_time = time.time()
            inactive_seconds = current_time - self.last_activity
            inactive_minutes = inactive_seconds / 60
            remaining = self.timeout_minutes - inactive_minutes
            return max(0, remaining)
    
    def set_timeout(self, minutes: int):
        """Update timeout duration."""
        self.timeout_minutes = max(1, minutes)  # Minimum 1 minute
