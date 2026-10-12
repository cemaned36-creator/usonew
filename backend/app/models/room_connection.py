from sqlalchemy import Column, Integer, Numeric, ForeignKey

from app.database import Base


class RoomConnection(Base):
    __tablename__ = "room_connections"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    # Связь с аудиторией
    from_room_id = Column(
        Integer,
        ForeignKey("rooms.id"),
        nullable=True
    )

    to_room_id = Column(
        Integer,
        ForeignKey("rooms.id"),
        nullable=True
    )

    # Связь с отдельной точкой доступа
    # Например: Охрана
    from_access_point_id = Column(
        Integer,
        ForeignKey("access_points.id"),
        nullable=True
    )

    to_access_point_id = Column(
        Integer,
        ForeignKey("access_points.id"),
        nullable=True
    )

    # Расстояние в метрах
    distance = Column(
        Numeric(8, 2),
        nullable=False
    )

    # Время перехода в минутах
    travel_time = Column(
        Integer,
        nullable=False
    )