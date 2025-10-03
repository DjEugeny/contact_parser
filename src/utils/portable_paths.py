#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""🔧 Portable Path Utilities for Cross-Platform Project Deployment"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Union, Optional


class PortablePathManager:
    """🔧 Manager for handling portable paths across different environments"""
    
    def __init__(self, project_root: Optional[Path] = None):
        """
        Initialize with project root detection
        
        Args:
            project_root: Optional explicit project root. If None, auto-detects.
        """
        if project_root is None:
            # Auto-detect project root by looking for key files
            current = Path(__file__).resolve()
            while current.parent != current:
                # Look for project markers
                if any((current / marker).exists() for marker in [
                    '.git', 'requirements.txt', 'setup.py', 'pyproject.toml', 'src'
                ]):
                    self.project_root = current
                    break
                current = current.parent
            else:
                # Fallback: use current file's grandparent (src/utils -> src -> project)
                self.project_root = Path(__file__).resolve().parent.parent.parent
        else:
            self.project_root = project_root.resolve()
        
        # Ensure project root exists
        if not self.project_root.exists():
            raise ValueError(f"Project root not found: {self.project_root}")
    
    def get_project_root(self) -> Path:
        """Get the project root directory"""
        return self.project_root
    
    def to_relative(self, path: Union[str, Path]) -> Path:
        """
        Convert any path to relative from project root
        
        Args:
            path: Path to convert (can be absolute or relative)
            
        Returns:
            Path relative to project root
        """
        path_obj = Path(path)
        
        if path_obj.is_absolute():
            try:
                # Try to make it relative to project root
                return path_obj.relative_to(self.project_root)
            except ValueError:
                # Path is outside project root, return as-is
                return path_obj
        else:
            # Already relative, return as-is
            return path_obj
    
    def to_absolute(self, path: Union[str, Path]) -> Path:
        """
        Convert relative path to absolute from project root
        
        Args:
            path: Path to convert (should be relative to project root)
            
        Returns:
            Absolute path
        """
        path_obj = Path(path)
        
        if path_obj.is_absolute():
            return path_obj
        else:
            return (self.project_root / path_obj).resolve()
    
    def safe_resolve(self, path: Union[str, Path]) -> Path:
        """
        Safely resolve a path, handling both absolute and relative cases
        
        Args:
            path: Path to resolve
            
        Returns:
            Resolved absolute path
        """
        path_obj = Path(path)
        
        if path_obj.is_absolute():
            # For absolute paths, try to make them portable
            try:
                relative = path_obj.relative_to(self.project_root)
                return (self.project_root / relative).resolve()
            except ValueError:
                # Path is outside project, return as-is but resolved
                return path_obj.resolve()
        else:
            # For relative paths, resolve from project root
            return (self.project_root / path_obj).resolve()
    
    def get_data_dir(self) -> Path:
        """Get the data directory (portable)"""
        return self.to_absolute("data")
    
    def get_config_dir(self) -> Path:
        """Get the config directory (portable)"""
        return self.to_absolute("config")
    
    def get_logs_dir(self) -> Path:
        """Get the logs directory (portable)"""
        return self.to_absolute("data/logs")
    
    def get_emails_dir(self) -> Path:
        """Get the emails directory (portable)"""
        return self.to_absolute("data/emails")
    
    def get_attachments_dir(self) -> Path:
        """Get the attachments directory (portable)"""
        return self.to_absolute("data/attachments")
    
    def get_results_dir(self) -> Path:
        """Get the results directory (portable)"""
        return self.to_absolute("data/llm_results")
    
    def ensure_directories(self) -> None:
        """Create all standard project directories if they don't exist"""
        directories = [
            self.get_data_dir(),
            self.get_config_dir(),
            self.get_logs_dir(),
            self.get_emails_dir(),
            self.get_attachments_dir(),
            self.get_results_dir(),
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
    
    def normalize_attachment_path(self, attachment_data: dict) -> Optional[Path]:
        """
        Normalize attachment path from email data to be portable
        
        Args:
            attachment_data: Attachment dictionary from email JSON
            
        Returns:
            Normalized path or None if not found
        """
        # Try different path fields in order of preference
        path_fields = ["path", "file_path", "relative_path", "saved_filename"]
        
        for field in path_fields:
            if field in attachment_data and attachment_data[field]:
                raw_path = attachment_data[field]
                
                # Handle different path formats
                if isinstance(raw_path, str):
                    path_obj = Path(raw_path)
                    
                    # If it starts with "attachments/", it's already relative
                    if raw_path.startswith("attachments/"):
                        return self.to_absolute(f"data/{raw_path}")
                    
                    # If it's absolute, try to make it relative
                    elif path_obj.is_absolute():
                        return self.safe_resolve(raw_path)
                    
                    # If it's relative, assume it's from data directory
                    else:
                        return self.to_absolute(f"data/{raw_path}")
        
        return None
    
    def get_env_file(self) -> Path:
        """Get the .env file path (portable)"""
        return self.to_absolute(".env")
    
    def is_portable(self, path: Union[str, Path]) -> bool:
        """
        Check if a path is portable (relative to project root)
        
        Args:
            path: Path to check
            
        Returns:
            True if path is portable (within project structure)
        """
        try:
            path_obj = Path(path)
            if path_obj.is_absolute():
                path_obj.relative_to(self.project_root)
            return True
        except (ValueError, OSError):
            return False


# Global instance for easy access
_portable_paths = None

def get_portable_paths() -> PortablePathManager:
    """Get the global portable paths manager instance"""
    global _portable_paths
    if _portable_paths is None:
        _portable_paths = PortablePathManager()
    return _portable_paths


# Convenience functions
def to_portable_path(path: Union[str, Path]) -> Path:
    """Convert any path to portable format"""
    return get_portable_paths().safe_resolve(path)

def get_project_root() -> Path:
    """Get project root directory"""
    return get_portable_paths().get_project_root()

def ensure_project_structure() -> None:
    """Ensure all project directories exist"""
    get_portable_paths().ensure_directories()