from sqlalchemy import String, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.models.base import Base

class Publisher(Base):
    __tablename__ = "publishers"

    id: Mapped[str] = mapped_column(
        String(50), 
        primary_key=True
    )  # e.g., 'bbc', 'reuters'
    name: Mapped[str] = mapped_column(
        String(100), 
        nullable=False
    )
    base_url: Mapped[str] = mapped_column(
        String(255), 
        nullable=False
    )
    credibility_score: Mapped[float] = mapped_column(
        Numeric(3, 2), 
        default=1.00
    )
    bias_rating: Mapped[str] = mapped_column(
        String(20), 
        default="center"
    )

    # Relationships
    articles = relationship("Article", back_populates="publisher", cascade="all, delete-orphan")
