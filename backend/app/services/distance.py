import heapq

from sqlalchemy.orm import Session

from app.models.room_connection import RoomConnection


def _room_node(room_id: int) -> str:
    return f"R{room_id}"


def _access_point_node(access_point_id: int) -> str:
    return f"A{access_point_id}"


def get_travel_time(
    db: Session,
    from_room_id: int,
    to_room_id: int,
):
    """
    Возвращает кратчайшее время перемещения
    между двумя аудиториями.
    """

    if from_room_id == to_room_id:
        return 0

    return get_node_travel_time(
        db=db,
        from_node=_room_node(from_room_id),
        to_node=_room_node(to_room_id),
    )


def get_room_to_access_point_time(
    db: Session,
    room_id: int,
    access_point_id: int,
):
    """
    Время перемещения:
    аудитория -> точка доступа.
    """

    return get_node_travel_time(
        db=db,
        from_node=_room_node(room_id),
        to_node=_access_point_node(access_point_id),
    )


def get_access_point_to_room_time(
    db: Session,
    access_point_id: int,
    room_id: int,
):
    """
    Время перемещения:
    точка доступа -> аудитория.
    """

    return get_node_travel_time(
        db=db,
        from_node=_access_point_node(access_point_id),
        to_node=_room_node(room_id),
    )


def get_node_travel_time(
    db: Session,
    from_node: str,
    to_node: str,
):
    """
    Универсальный поиск кратчайшего пути
    между аудиториями и точками доступа.
    """

    if from_node == to_node:
        return 0

    connections = db.query(RoomConnection).all()

    graph = {}

    def add_edge(
        source: str,
        target: str,
        travel_time: int,
    ):
        if source not in graph:
            graph[source] = []

        graph[source].append(
            (target, travel_time)
        )

    for connection in connections:

        if connection.from_room_id is not None:
            from_node_id = _room_node(
                connection.from_room_id
            )
        else:
            from_node_id = _access_point_node(
                connection.from_access_point_id
            )

        if connection.to_room_id is not None:
            to_node_id = _room_node(
                connection.to_room_id
            )
        else:
            to_node_id = _access_point_node(
                connection.to_access_point_id
            )

        add_edge(
            from_node_id,
            to_node_id,
            connection.travel_time,
        )

    queue = [
        (0, from_node)
    ]

    distances = {
        from_node: 0
    }

    while queue:

        current_time, current_node = heapq.heappop(
            queue
        )

        if current_time > distances.get(
            current_node,
            float("inf"),
        ):
            continue

        if current_node == to_node:
            return current_time

        for (
            next_node,
            travel_time,
        ) in graph.get(
            current_node,
            [],
        ):

            new_time = (
                current_time
                + travel_time
            )

            if new_time < distances.get(
                next_node,
                float("inf"),
            ):
                distances[next_node] = new_time

                heapq.heappush(
                    queue,
                    (
                        new_time,
                        next_node,
                    ),
                )

    return None