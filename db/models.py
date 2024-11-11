from datetime import datetime
from typing import List, Optional, Dict, Set
from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from db.database import get_declarative_base
from abc import ABC, abstractmethod

Base = get_declarative_base()


class ModelBaseInterface(ABC):
    @abstractmethod
    def to_dict(self, exclude: Optional[Set[str]] = {}) -> Dict:
        pass


class ModelBase(ModelBaseInterface, Base):
    def to_dict(self, exclude: Optional[Set[str]] = {}) -> Dict:
        return {c.name: setattr(self, c.name) for c in self.__table__.columns if c.name not in exclude}


class User(ModelBase):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String, unique=True, index=True)
    username: Mapped[str] = mapped_column(String, unique=True, index=True)
    is_confirmed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )
    posts: Mapped[List["Post"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    likes: Mapped[List["Like"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    comments: Mapped[List["Comment"]] = relationship(back_populates="user", cascade="all, delete-orphan")

    def to_dict(self, exclude: Optional[Set[str]] = {}) -> Dict:
        return super().to_dict(self, exclude)


class Post(ModelBase):
    __tablename__: str = "post"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String)
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    author_id: Mapped[int] = mapped_column(ForeignKey("user.id"))
    image_url: Mapped[str] = mapped_column(String)
    user: Mapped["User"] = relationship(back_populates="posts")
    likes: Mapped[List["Like"]] = relationship(back_populates="post", cascade="all, delete-orphan")
    comments: Mapped[List["Comment"]] = relationship(back_populates="post", cascade="all, delete-orphan")

    def to_dict(self, exclude: Optional[Set[str]] = {}) -> Dict:
        return super().to_dict(self, exclude)


class Like(ModelBase):
    __tablename__ = "likes"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    post_id: Mapped[int] = mapped_column(ForeignKey("post.id"))
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    user: Mapped["User"] = relationship(back_populates="likes")
    post: Mapped["Post"] = relationship(back_populates="likes")

    def to_dict(self, exclude: Optional[Set[str]] = {}) -> Dict:
        return super().to_dict(self, exclude)


class Comment(ModelBase):
    __tablename__ = "comments"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    post_id: Mapped[int] = mapped_column(ForeignKey("post.id"))
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"))
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    user: Mapped["User"] = relationship(back_populates="comments")
    post: Mapped["Post"] = relationship(back_populates="comments")

    def to_dict(self, exclude: Optional[Set[str]] = {}) -> Dict:
        return super().to_dict(self, exclude)
