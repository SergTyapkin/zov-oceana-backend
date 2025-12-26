import geoip2.errors
from flask import request
from geoip2 import database

from src.config import CONFIG


_reader = database.Reader(CONFIG.geolite_db_path)


def detectGeoLocation():
    try:
        response = _reader.city(request.environ['IP_ADDRESS'])
    except geoip2.errors.AddressNotFoundError:
        return 'Unknown position'
    res = []
    if response.city.name is not None:
        res.append(response.city.name)
    if response.subdivisions.most_specific.name is not None:
        res.append(response.subdivisions.most_specific.name)
    if response.country.name is not None:
        res.append(response.country.name)

    return ', '.join(res)
