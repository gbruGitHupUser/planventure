from datetime import date

from flask import Blueprint, g, jsonify, request

from extensions import db
from itinerary import generate_default_itinerary
from middleware import auth_required
from models import Trip

trips_bp = Blueprint("trips", __name__, url_prefix="/api/trips")

MAX_DESTINATION_LENGTH = 255


def _parse_date(value, field, errors):
    if not isinstance(value, str):
        errors[field] = "Must be a date string in YYYY-MM-DD format"
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        errors[field] = "Must be a valid date in YYYY-MM-DD format"
        return None


def _parse_coordinate(value, field, limit, errors):
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        errors[field] = "Must be a number"
        return None
    if not -limit <= value <= limit:
        errors[field] = f"Must be between -{limit} and {limit}"
        return None
    return float(value)


def parse_trip_payload(data, partial=False):
    """Validate a trip payload.

    Returns (values, errors). `values` only contains the fields that were
    provided; with partial=False the required fields must be present.
    """
    values = {}
    errors = {}

    if "destination" in data:
        destination = data["destination"]
        if not isinstance(destination, str) or not destination.strip():
            errors["destination"] = "Destination must be a non-empty string"
        elif len(destination.strip()) > MAX_DESTINATION_LENGTH:
            errors["destination"] = f"Must be at most {MAX_DESTINATION_LENGTH} characters"
        else:
            values["destination"] = destination.strip()
    elif not partial:
        errors["destination"] = "Destination is required"

    for field in ("start_date", "end_date"):
        if field in data:
            parsed = _parse_date(data[field], field, errors)
            if parsed is not None:
                values[field] = parsed
        elif not partial:
            errors[field] = f"{field} is required"

    # Coordinates may be sent as top-level latitude/longitude or as a
    # nested "coordinates" object (the shape returned by the API).
    coords = data.get("coordinates")
    if coords is not None and not isinstance(coords, dict):
        errors["coordinates"] = "Must be an object with latitude and longitude"
        coords = None
    source = {**(coords or {}), **{k: data[k] for k in ("latitude", "longitude") if k in data}}
    if "latitude" in source:
        lat = _parse_coordinate(source["latitude"], "latitude", 90, errors)
        if "latitude" not in errors:
            values["latitude"] = lat
    if "longitude" in source:
        lng = _parse_coordinate(source["longitude"], "longitude", 180, errors)
        if "longitude" not in errors:
            values["longitude"] = lng

    if "itinerary" in data:
        if not isinstance(data["itinerary"], (dict, list)):
            errors["itinerary"] = "Itinerary must be a JSON object or array"
        else:
            values["itinerary"] = data["itinerary"]

    return values, errors


def _validation_error(errors):
    return jsonify({"error": "Validation failed", "details": errors}), 400


def _get_json_object():
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else None


def _get_user_trip(trip_id):
    return Trip.query.filter_by(id=trip_id, user_id=g.current_user.id).first()


@trips_bp.route("", methods=["GET"])
@auth_required
def list_trips():
    trips = (
        Trip.query.filter_by(user_id=g.current_user.id)
        .order_by(Trip.start_date, Trip.id)
        .all()
    )
    return jsonify({"trips": [t.to_dict() for t in trips]})


@trips_bp.route("", methods=["POST"])
@auth_required
def create_trip():
    data = _get_json_object()
    if data is None:
        return jsonify({"error": "Request body must be a JSON object"}), 400

    values, errors = parse_trip_payload(data)
    if not errors and values["end_date"] < values["start_date"]:
        errors["end_date"] = "end_date must not be before start_date"
    if errors:
        return _validation_error(errors)

    if "itinerary" not in values:
        values["itinerary"] = generate_default_itinerary(
            values["start_date"], values["end_date"], values["destination"]
        )

    trip = Trip(user_id=g.current_user.id, **values)
    db.session.add(trip)
    db.session.commit()
    return jsonify({"trip": trip.to_dict()}), 201


@trips_bp.route("/<int:trip_id>", methods=["GET"])
@auth_required
def get_trip(trip_id):
    trip = _get_user_trip(trip_id)
    if trip is None:
        return jsonify({"error": "Trip not found"}), 404
    return jsonify({"trip": trip.to_dict()})


@trips_bp.route("/<int:trip_id>", methods=["PUT", "PATCH"])
@auth_required
def update_trip(trip_id):
    trip = _get_user_trip(trip_id)
    if trip is None:
        return jsonify({"error": "Trip not found"}), 404

    data = _get_json_object()
    if data is None:
        return jsonify({"error": "Request body must be a JSON object"}), 400

    values, errors = parse_trip_payload(data, partial=request.method == "PATCH")
    if not errors:
        start = values.get("start_date", trip.start_date)
        end = values.get("end_date", trip.end_date)
        if end < start:
            errors["end_date"] = "end_date must not be before start_date"
    if errors:
        return _validation_error(errors)

    for field, value in values.items():
        setattr(trip, field, value)
    db.session.commit()
    return jsonify({"trip": trip.to_dict()})


@trips_bp.route("/<int:trip_id>", methods=["DELETE"])
@auth_required
def delete_trip(trip_id):
    trip = _get_user_trip(trip_id)
    if trip is None:
        return jsonify({"error": "Trip not found"}), 404

    db.session.delete(trip)
    db.session.commit()
    return "", 204
