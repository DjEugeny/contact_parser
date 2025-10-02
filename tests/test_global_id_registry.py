import json
import sys
import tempfile
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
SRC_DIR = PROJECT_ROOT / "src"

for candidate in (PROJECT_ROOT, SRC_DIR):
    candidate_str = str(candidate)
    if candidate_str not in sys.path:
        sys.path.append(candidate_str)

from src.registry import GlobalIDRegistry


def _build_org(name: str, inn: str | None = None, website: str | None = None, city: str | None = None, emails: list[str] | None = None) -> dict:
    return {
        "name": name,
        "inn": inn,
        "website": website,
        "city": city,
        "emails": emails or [],
    }


def _build_contact(name: str, email: str | None = None, phone: str | None = None) -> dict:
    phones = [{"number": phone}] if phone else []
    return {
        "contact_id": 1,
        "organization_id": 1,
        "name": name,
        "email": email,
        "phones": phones,
    }


def test_resolve_organization_stable_gid(tmp_path: Path) -> None:
    registry = GlobalIDRegistry(registry_dir=tmp_path)
    org = _build_org(name="ООО \"ДНК-Технология\"", inn="7708123456", website="https://dna-technology.ru", city="Москва")

    result1 = registry.resolve_organization(org)
    result2 = registry.resolve_organization(org)

    assert result1.gid == result2.gid
    assert result1.match_rule == "INN"
    assert not result2.alias_added


def test_resolve_organization_alias_addition(tmp_path: Path) -> None:
    registry = GlobalIDRegistry(registry_dir=tmp_path)
    org_primary = _build_org(name="МИЛЛАБ", inn=None, website="https://millab.ru", city="Москва")
    org_secondary = _build_org(name="МИЛЛАБ", inn=None, website=None, city="Москва", emails=["info@millab.ru"])

    first = registry.resolve_organization(org_primary)
    second = registry.resolve_organization(org_secondary)

    assert first.gid == second.gid
    assert second.alias_added
    keys = registry.get_all_keys_for_gid(first.gid)
    assert any(key[1] == "EMAIL_DOMAIN" for key in keys)


def test_resolve_contact_fallback(tmp_path: Path) -> None:
    registry = GlobalIDRegistry(registry_dir=tmp_path)
    org = _build_org(name="Центр диагностики", inn="7708123456", website=None, city="Москва")
    org_result = registry.resolve_organization(org)

    contact_full = _build_contact(name="Иван Сергеев", email="ivan@example.com", phone="+7 (900) 123-45-67")
    contact_full["organization_id"] = 1
    first = registry.resolve_contact(contact_full, org_result.gid)

    contact_poor = _build_contact(name="Иван Сергеев", email=None, phone=None)
    contact_poor["organization_id"] = 1
    second = registry.resolve_contact(contact_poor, org_result.gid)

    assert first.gid == second.gid
    keys = registry.get_all_keys_for_gid(first.gid)
    assert any(key[1] == "NAME_POSITION" for key in keys)


def test_overrides_apply_and_conflict(tmp_path: Path) -> None:
    overrides = {
        "org_overrides": [
            {
                "key": ["ORG", "NAME_CITY", "днк-технология", "москва"],
                "gid": "override-gid-1",
            }
        ]
    }
    overrides_path = tmp_path / "overrides.yml"
    overrides_path.write_text(json.dumps(overrides), encoding="utf-8")

    registry = GlobalIDRegistry(registry_dir=tmp_path, overrides_path=overrides_path)

    org = _build_org(name="ООО ДНК-Технология", city="Москва")
    result = registry.resolve_organization(org)

    assert result.gid == "override-gid-1"
    assert result.overrides_applied
