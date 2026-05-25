"""
Couche d'accès aux données (Repository Pattern).
Chaque repository encapsule les opérations CRUD pour un modèle.
La connexion DB est injectée pour permettre la transition progressive.
"""
from abc import ABC, abstractmethod
from typing import Generic, TypeVar, List, Optional
from uuid import UUID

T = TypeVar("T")


class BaseRepository(ABC, Generic[T]):
    """Repository abstrait — définit le contrat CRUD."""

    @abstractmethod
    def get_by_id(self, id: UUID) -> Optional[T]:
        ...

    @abstractmethod
    def list_all(self, limit: int = 100, offset: int = 0) -> List[T]:
        ...

    @abstractmethod
    def create(self, entity: T) -> T:
        ...

    @abstractmethod
    def update(self, entity: T) -> T:
        ...

    @abstractmethod
    def soft_delete(self, id: UUID) -> bool:
        ...

    @abstractmethod
    def hard_delete(self, id: UUID) -> bool:
        ...
