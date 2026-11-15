"""BloodRequest response shape (contract schema BloodRequest). No requester email or name."""


def request_dto(blood_request) -> dict:
    return {
        'id': str(blood_request.id),
        'requester_id': str(blood_request.requester_id),
        'blood_group': blood_request.blood_group,
        'component_type': blood_request.component_type,
        'quantity': blood_request.quantity,
        'fulfilled_quantity': blood_request.fulfilled_quantity,
        'urgency_level': blood_request.urgency_level,
        'status': blood_request.status,
        'rejection_reason': blood_request.rejection_reason,
        'created_at': blood_request.created_at.isoformat(),
    }
