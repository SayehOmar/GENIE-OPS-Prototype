"""
Logging utilities with color support
"""
import logging
import sys
from app.core.config import settings

# ANSI color codes
class Colors:
    """ANSI color codes for terminal output"""
    # Basic colors
    RESET = '\033[0m'
    BOLD = '\033[1m'
    
    # Status colors
    GREEN = '\033[92m'      # Success
    RED = '\033[91m'        # Error/Failure
    BLUE = '\033[94m'       # Info/Processing
    YELLOW = '\033[93m'     # Warning
    PURPLE = '\033[95m'     # Special/Important
    CYAN = '\033[96m'       # Debug/Details
    
    # Background colors
    BG_GREEN = '\033[42m'
    BG_RED = '\033[41m'
    BG_BLUE = '\033[44m'
    BG_YELLOW = '\033[43m'
    BG_PURPLE = '\033[45m'


class ColoredFormatter(logging.Formatter):
    """Custom formatter that adds colors based on log level and message content"""
    
    # Color mapping for log levels
    LEVEL_COLORS = {
        'DEBUG': Colors.CYAN,
        'INFO': Colors.BLUE,
        'WARNING': Colors.YELLOW,
        'ERROR': Colors.RED,
        'CRITICAL': Colors.RED + Colors.BOLD,
    }
    
    # Keywords that trigger specific colors
    SUCCESS_KEYWORDS = ['success', 'successful', 'completed', 'approved', 'submitted', 'saved', 'created']
    ERROR_KEYWORDS = ['error', 'failed', 'failure', 'exception', 'crash', 'timeout', 'rejected']
    WARNING_KEYWORDS = ['warning', 'retry', 'skipped', 'fallback', 'partial']
    PROCESS_KEYWORDS = ['processing', 'starting', 'initializing', 'navigating', 'filling', 'submitting', 'analyzing']
    INFO_KEYWORDS = ['info', 'status', 'progress', 'update']
    
    def format(self, record):
        # Get base color from log level
        level_color = self.LEVEL_COLORS.get(record.levelname, Colors.RESET)
        message = record.getMessage()
        message_lower = message.lower()
        
        # Override color based on message content
        if any(keyword in message_lower for keyword in self.SUCCESS_KEYWORDS):
            color = Colors.GREEN
        elif any(keyword in message_lower for keyword in self.ERROR_KEYWORDS):
            color = Colors.RED
        elif any(keyword in message_lower for keyword in self.WARNING_KEYWORDS):
            color = Colors.YELLOW
        elif any(keyword in message_lower for keyword in self.PROCESS_KEYWORDS):
            color = Colors.PURPLE
        elif any(keyword in message_lower for keyword in self.INFO_KEYWORDS):
            color = Colors.BLUE
        else:
            color = level_color
        
        # Apply colors
        record.levelname = f"{color}{record.levelname}{Colors.RESET}"
        record.msg = f"{color}{message}{Colors.RESET}"
        
        return super().format(record)


# Configure logging with colored formatter
def setup_logger():
    """Setup logger with colored output"""
    handler = logging.StreamHandler(sys.stdout)
    
    # Use colored formatter if output is a TTY (terminal)
    if sys.stdout.isatty():
        formatter = ColoredFormatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    else:
        # Plain formatter for non-TTY (e.g., when redirecting to file)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    handler.setFormatter(formatter)
    
    logger = logging.getLogger("genie_ops")
    logger.setLevel(logging.DEBUG if settings.DEBUG else logging.INFO)
    logger.addHandler(handler)
    
    return logger


# Initialize logger
logger = setup_logger()
