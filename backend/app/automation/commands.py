"""
Command and result dataclasses for browser worker communication
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
import json


@dataclass
class BrowserCommand:
    """
    Command sent to browser worker process.
    
    Commands are serialized and sent via multiprocessing Queue.
    Each command has a unique ID for matching with results.
    """
    command_id: str
    command_type: str  # navigate, fill_form, submit_form, detect_captcha, get_page_content, extract_form_fields_dom, take_screenshot, close
    params: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        """Convert command to dictionary for serialization"""
        return {
            "command_id": self.command_id,
            "command_type": self.command_type,
            "params": self.params
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "BrowserCommand":
        """Create command from dictionary"""
        return cls(
            command_id=data["command_id"],
            command_type=data["command_type"],
            params=data.get("params", {})
        )


@dataclass
class BrowserResult:
    """
    Result returned from browser worker process.
    
    Results are serialized and sent back via multiprocessing Queue.
    Contains status, data, and any error information.
    """
    command_id: str
    status: str  # success, error
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    error_type: Optional[str] = None
    
    def to_dict(self) -> Dict:
        """Convert result to dictionary for serialization"""
        return {
            "command_id": self.command_id,
            "status": self.status,
            "data": self.data,
            "error": self.error,
            "error_type": self.error_type
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "BrowserResult":
        """Create result from dictionary"""
        return cls(
            command_id=data["command_id"],
            status=data["status"],
            data=data.get("data"),
            error=data.get("error"),
            error_type=data.get("error_type")
        )
    
    @classmethod
    def success(cls, command_id: str, data: Optional[Dict] = None) -> "BrowserResult":
        """Create a success result"""
        return cls(
            command_id=command_id,
            status="success",
            data=data or {}
        )
    
    @classmethod
    def error_result(cls, command_id: str, error: str, error_type: Optional[str] = None) -> "BrowserResult":
        """Create an error result"""
        return cls(
            command_id=command_id,
            status="error",
            error=error,
            error_type=error_type or "UnknownError"
        )
