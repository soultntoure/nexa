"""
Base repository abstract class for all data access operations.

Contains:
- BaseRepository[T] abstract class with generic type support
- Common CRUD methods:
  - get_by_id(id: UUID) -> T | None
  - create(entity: T) -> T
  - update(entity: T) -> T
  - delete(id: UUID) -> bool
  - list_all(skip: int, limit: int) -> list[T]
  - exists(id: UUID) -> bool
  - count() -> int
- Shared utilities:
  - Session management (flush, rollback)
  - Expunge logic for detached entities
  - Error handling with context

Rules: async only, returns detached entities, concrete repos must set model_class.
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from sqlalchemy import select, exists, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from app.data.db.base import Base

# Generic type for models that inherit from Base
T = TypeVar("T", bound=Base)


class BaseRepository(ABC, Generic[T]):
    """
    Abstract base repository providing common CRUD operations.
    
    Concrete repositories must set the model_class attribute to specify
    the SQLAlchemy model they work with.
    
    Example:
        class CustomerRepository(BaseRepository[Customer]):
            model_class = Customer
            
            def __init__(self, session: AsyncSession):
                super().__init__(session)
    """

    model_class: type[T]

    def __init__(self, session: AsyncSession):
        """
        Initialize repository with async database session.
        
        Args:
            session: SQLAlchemy async session for database operations
        """
        if not hasattr(self, "model_class"):
            raise NotImplementedError(
                f"{self.__class__.__name__} must define model_class attribute"
            )
        self.session = session

    async def get_by_id(self, id: uuid.UUID) -> T | None:
        """
        Retrieve an entity by its UUID.
        
        Args:
            id: UUID of the entity to retrieve
            
        Returns:
            Detached entity if found, None otherwise
        """
        try:
            result = await self.session.get(self.model_class, id)
            if result:
                self._expunge(result)
            return result
        except SQLAlchemyError as e:
            raise RuntimeError(
                f"Error retrieving {self.model_class.__name__} by id {id}"
            ) from e

    async def create(self, entity: T) -> T:
        """
        Create a new entity in the database.
        
        Args:
            entity: Entity instance to create
            
        Returns:
            Created entity (detached)
        """
        try:
            self.session.add(entity)
            await self.session.commit()
            await self.session.refresh(entity)
            self._expunge(entity)
            return entity
        except SQLAlchemyError as e:
            await self.session.rollback()
            raise RuntimeError(
                f"Error creating {self.model_class.__name__}"
            ) from e

    async def update(self, entity: T) -> T:
        """
        Update an existing entity in the database.
        
        Args:
            entity: Entity instance with updated values
            
        Returns:
            Updated entity (detached)
        """
        try:
            merged = await self.session.merge(entity)
            await self.session.commit()
            await self.session.refresh(merged)
            self._expunge(merged)
            return merged
        except SQLAlchemyError as e:
            await self.session.rollback()
            raise RuntimeError(
                f"Error updating {self.model_class.__name__}"
            ) from e

    async def delete(self, id: uuid.UUID) -> bool:
        """
        Delete an entity by its UUID.
        
        Args:
            id: UUID of the entity to delete
            
        Returns:
            True if entity was deleted, False if not found
        """
        try:
            entity = await self.session.get(self.model_class, id)
            if not entity:
                return False
            
            await self.session.delete(entity)
            await self.session.commit()
            return True
        except SQLAlchemyError as e:
            await self.session.rollback()
            raise RuntimeError(
                f"Error deleting {self.model_class.__name__} with id {id}"
            ) from e

    async def list_all(
        self, skip: int = 0, limit: int = 100
    ) -> list[T]:
        """
        List all entities with pagination.
        
        Args:
            skip: Number of records to skip (offset)
            limit: Maximum number of records to return
            
        Returns:
            List of detached entities
        """
        try:
            stmt = (
                select(self.model_class)
                .offset(skip)
                .limit(limit)
            )
            result = await self.session.execute(stmt)
            entities = list(result.scalars().all())
            
            # Expunge all entities
            for entity in entities:
                self._expunge(entity)
            
            return entities
        except SQLAlchemyError as e:
            raise RuntimeError(
                f"Error listing {self.model_class.__name__} entities"
            ) from e

    async def exists(self, id: uuid.UUID) -> bool:
        """
        Check if an entity exists by its UUID.
        
        Args:
            id: UUID of the entity to check
            
        Returns:
            True if entity exists, False otherwise
        """
        try:
            stmt = select(
                exists().where(self.model_class.id == id)
            )
            result = await self.session.execute(stmt)
            return result.scalar() or False
        except SQLAlchemyError as e:
            raise RuntimeError(
                f"Error checking existence of {self.model_class.__name__} with id {id}"
            ) from e

    async def count(self) -> int:
        """
        Count total number of entities.
        
        Returns:
            Total count of entities
        """
        try:
            stmt = select(func.count()).select_from(self.model_class)
            result = await self.session.execute(stmt)
            return result.scalar() or 0
        except SQLAlchemyError as e:
            raise RuntimeError(
                f"Error counting {self.model_class.__name__} entities"
            ) from e

    def _expunge(self, entity: T) -> None:
        """
        Expunge entity from session to create detached instance.
        
        This allows entities to be used outside of the session context
        without triggering lazy loading errors.
        
        Args:
            entity: Entity to expunge from session
        """
        self.session.expunge(entity)

    async def flush(self) -> None:
        """
        Flush pending changes to the database without committing.
        
        Useful for operations that need to generate IDs before commit.
        """
        try:
            await self.session.flush()
        except SQLAlchemyError as e:
            raise RuntimeError("Error flushing session") from e

    async def rollback(self) -> None:
        """
        Rollback the current transaction.
        
        Useful for error recovery in complex operations.
        """
        await self.session.rollback()
