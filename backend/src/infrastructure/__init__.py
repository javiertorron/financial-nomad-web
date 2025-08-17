"""
Infrastructure layer for external service clients.
"""
from .firestore import FirestoreService, cleanup_firestore, get_firestore

__all__ = [
    "FirestoreService",
    "get_firestore", 
    "cleanup_firestore",
]