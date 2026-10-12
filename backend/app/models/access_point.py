from sqlalchemy import Column, Integer, String

from app.database import Base


class AccessPoint(Base):
    __tablename__ = "access_points"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(
        String(100),
        nullable=False,
    )

    point_type = Column(
        String(30),
        nullable=False,
    )