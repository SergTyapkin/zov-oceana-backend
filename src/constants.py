from dataclasses import dataclass

HTTP_INVALID_DATA = 400
HTTP_INVALID_AUTH_DATA = 401
HTTP_NO_PERMISSIONS = 403
HTTP_NOT_FOUND = 404
HTTP_DATA_CONFLICT = 409
HTTP_TEAPOT = 418
HTTP_NOT_FULL_DATA = 424
HTTP_INTERNAL_ERROR = 500
HTTP_OK = 200

@dataclass
class OrderStatuses:
    created = 'created'
    accepted = 'accepted'
    prepared = 'prepared'
    delivered = 'delivered'
    cancelled = 'cancelled'

@dataclass
class OrderPaymentStatuses:
    new = 'new'
    authorized = 'authorized'
    confirmed = 'confirmed'
    expired = 'expired'
    rejected = 'rejected'
    refunded = 'refunded'    
    cancelled = 'cancelled'    
