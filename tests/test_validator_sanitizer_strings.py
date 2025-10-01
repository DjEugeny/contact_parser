import copy

from src.core.validator import LLMResponseValidator
from src.postprocessing.postprocessor import PostProcessor


def test_sanitizer_converts_numeric_strings():
    validator = LLMResponseValidator()

    payload = {
        "organizations": [
            {
                "organization_id": 1,
                "name": 123,
                "emails": [12345],
                "phones": [89005553535],
                "city": 42,
                "address": 75,
                "website": 101,
            }
        ],
        "contacts": [
            {
                "contact_id": 1,
                "name": 321,
                "organization_id": 1,
                "position": 777,
                "email": 999,
                "phones": [{"number": 88005553535, "formatted": 123}],
                "city": 213,
                "address": 456,
                "role_in_message": 789,
                "confidence": 0.9,
            }
        ],
        "business_context": 404,
        "summary": {
            "topic": 111,
            "product_interest": None,
            "communication_stage": 222,
            "request_type": 333,
        },
        "key_points": [123, None, 456],
        "commercial_offers": [
            {
                "found": True,
                "offer_type": 1,
                "offer_number": 2,
                "equipment_items": [
                    {
                        "name": 3,
                        "quantity": 1,
                        "unit_price": 1000,
                    }
                ],
            }
        ],
        "interactions": [
            {
                "interaction_local_id": 1,
                "contact_id": 1,
                "organization_id": 1,
                "message_subject": 1010,
                "message_date": 2020,
                "role_in_message": 3030,
                "interaction_type": "other",
                "summary": 4040,
                "attachments": [5050],
                "participants": {
                    "actor": 6060,
                    "audience": [7070, None],
                },
                "confidence": 0.5,
            }
        ],
    }

    sanitized = validator._sanitize_response(copy.deepcopy(payload))

    contact = sanitized["contacts"][0]
    phone_entry = contact["phones"][0]
    organization = sanitized["organizations"][0]
    interaction = sanitized["interactions"][0]

    assert isinstance(contact["name"], str)
    assert isinstance(phone_entry["number"], str)
    assert isinstance(organization["name"], str)
    assert isinstance(interaction["summary"], str)

    sanitizer_meta = sanitized["postprocessing_metadata"]["sanitizer"]
    assert sanitizer_meta["converted_to_string"] > 0


def test_postprocessor_handles_numeric_phone_fields():
    postprocessor = PostProcessor()

    contacts = [
        {
            "contact_id": 1,
            "organization_id": 1,
            "name": 123,
            "position": 456,
            "email": 789,
            "phones": [{"number": 88005553535}],
            "role_in_message": "sender",
            "confidence": 0.9,
        }
    ]
    organizations = {
        1: {
            "organization_id": 1,
            "name": "Org",
            "city": "Москва",
            "address": "улица",
        }
    }

    backfilled, _ = postprocessor._backfill_contact_city_address(contacts, organizations)
    normalized_contact = backfilled[0]

    assert isinstance(normalized_contact["name"], str)
    assert isinstance(normalized_contact["phones"][0]["number"], str)
