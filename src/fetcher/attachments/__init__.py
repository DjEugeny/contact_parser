"""
Attachment components for email processing.

Компоненты для работы с вложениями:
- AttachmentRegistry - реестр вложений с message_id
"""

from .attachment_registry import AttachmentRegistry

__all__ = [
    'AttachmentRegistry'
]