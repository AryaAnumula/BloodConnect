"""JSON-ready camp projection shared by services and selectors."""


def camp_dto(camp) -> dict:
    return {
        'id': str(camp.id),
        'name': camp.name,
        'location': camp.location,
        'starts_at': camp.starts_at.isoformat(),
        'ends_at': camp.ends_at.isoformat(),
        'capacity': camp.capacity,
        'status': camp.status,
    }
