# backend/routes/__init__.py
from .auth import auth_bp
from .chat import chat_bp

__all__ = ['auth_bp', 'chat_bp']