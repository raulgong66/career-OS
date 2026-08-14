"""Unit tests for deterministic Phase 2A import classification."""

from __future__ import annotations

import hashlib
from pathlib import Path
from types import SimpleNamespace

import pytest

from careeros.import_classification import (
    IDENTITY_CONFLICT,
    NEW_PERSON,
    POSSIBLE_SAME_PERSON,
    SAME_DOCUMENT,
    classify_import,
    retain_source,
    source_hash_for_bytes,
)


def _record(profile_id: str, data: dict) -> SimpleNamespace:
    return SimpleNamespace(profile_id=profile_id, data=data)


def _person(
    pid: str,
    name: str | None = None,
    email: str | None = None,
    phone: str | None = None,
    linkedin: str | None = None,
) -> dict:
    person: dict = {"id": pid}
    if name:
        person["names"] = [{"value": name, "usage": "professional"}]
    contact: dict = {}
    if email:
        contact["email"] = email
    if phone:
        contact["phone"] = phone
    if contact:
        person["contact"] = contact
    if linkedin:
        person["links"] = [{"label": "LinkedIn", "href": linkedin}]
    return person


def _profile(
    pid: str,
    name: str | None = None,
    email: str | None = None,
    phone: str | None = None,
    linkedin: str | None = None,
    source_hash: str | None = None,
) -> dict:
    data: dict = {
        "profileVersion": "1.0.0",
        "person": _person(pid, name, email, phone, linkedin),
        "extensions": {},
    }
    if source_hash:
        data["extensions"]["_acquisition"] = {"sourceHash": source_hash}
    return data


def _classify(
    existing: list[SimpleNamespace],
    *,
    source_hash: str = "",
    profile: dict | None = None,
    exclude: str | None = None,
):
    return classify_import(
        existing,
        source_hash=source_hash,
        profile_data=profile or _profile("person-raul-gongora-betancourt", name="Raul Gongora Betancourt"),
        exclude_profile_id=exclude,
    )


class TestSourceHashing:
    def test_hash_is_deterministic_and_sha256(self) -> None:
        payload = b"identical document bytes"
        assert source_hash_for_bytes(payload) == hashlib.sha256(payload).hexdigest()
        assert source_hash_for_bytes(payload) == source_hash_for_bytes(payload)

    def test_modified_bytes_produce_different_hash(self) -> None:
        assert source_hash_for_bytes(b"cv version one") != source_hash_for_bytes(b"cv version two")


class TestRetainSource:
    def test_retain_source_persists_bytes_under_hash_name(self, tmp_path: Path) -> None:
        sources = tmp_path / "_sources"
        payload = b"raw docx bytes"
        path = retain_source(payload, sources, "abc123", ".docx")
        assert path == sources / "abc123.docx"
        assert path.read_bytes() == payload

    def test_retain_source_creates_directory(self, tmp_path: Path) -> None:
        sources = tmp_path / "nested" / "_sources"
        path = retain_source(b"x", sources, "h1", ".docx")
        assert path.parent.is_dir()

    def test_retain_source_filename_never_uses_user_input(self, tmp_path: Path) -> None:
        path = retain_source(b"x", tmp_path, "h1", "../../evil")
        assert path.parent == tmp_path
        assert path.name.startswith("h1")
        assert "/" not in path.name and "\\" not in path.name

    def test_retain_source_uses_final_extension_only(self, tmp_path: Path) -> None:
        assert retain_source(b"x", tmp_path, "h1", ".docx").name == "h1.docx"
        assert retain_source(b"x", tmp_path, "h1", ".DOCX").name == "h1.docx"
        assert retain_source(b"x", tmp_path, "h1", "not-an-extension").name == "h1"


class TestSameDocumentDetection:
    def test_same_hash_detected_as_same_document(self) -> None:
        existing = [_record("person-jane-doe", _profile("person-jane-doe", name="Jane Doe", source_hash="h-same"))]
        result = _classify(existing, source_hash="h-same")
        assert result.result == SAME_DOCUMENT
        assert result.candidates[0].profile_id == "person-jane-doe"
        assert result.candidates[0].matched_on == ("sourceHash",)

    def test_legacy_profile_without_acquisition_never_hash_matches(self) -> None:
        existing = [_record("person-old", _profile("person-old", name="Old Person"))]
        assert _classify(existing, source_hash="h-new").result == NEW_PERSON

    def test_same_document_precedes_identity(self) -> None:
        existing = [
            _record("person-jane-doe", _profile("person-jane-doe", name="Jane Doe", source_hash="h-same")),
            _record("person-raul", _profile("person-raul", name="Raul Gongora Betancourt")),
        ]
        result = _classify(existing, source_hash="h-same")
        assert result.result == SAME_DOCUMENT
        assert len(result.candidates) == 1
        assert result.candidates[0].profile_id == "person-jane-doe"

    def test_excluded_profile_cannot_match_itself(self) -> None:
        existing = [_record("person-raul-gongora-betancourt-profile", _profile("person-x", name="Raul Gongora Betancourt", source_hash="h"))]
        result = _classify(existing, source_hash="h", exclude="person-raul-gongora-betancourt-profile")
        assert result.result == NEW_PERSON


class TestSamePersonDetection:
    def test_exact_name_matches(self) -> None:
        existing = [_record("person-raul-1", _profile("person-raul-1", name="Raul Gongora Betancourt"))]
        result = _classify(existing)
        assert result.result == POSSIBLE_SAME_PERSON
        assert result.candidates[0].matched_on == ("name",)

    def test_email_equality_matches(self) -> None:
        existing = [_record("person-x", _profile("person-x", name="R. G. B.", email="raul@example.com"))]
        result = _classify(existing, profile=_profile("person-y", name="Raul Gongora Betancourt", email="raul@example.com"))
        assert result.result == POSSIBLE_SAME_PERSON
        assert result.candidates[0].matched_on == ("email",)

    def test_phone_equality_ignores_formatting(self) -> None:
        existing = [_record("person-x", _profile("person-x", name="Raul Gongora Betancourt", phone="+46 70 123 45 67"))]
        result = _classify(existing, profile=_profile("person-y", name="Raul Gongora Betancourt", phone="+46701234567"))
        assert result.result == POSSIBLE_SAME_PERSON
        assert "phone" in result.candidates[0].matched_on

    def test_linkedin_equality_matches(self) -> None:
        existing = [_record("person-x", _profile("person-x", name="Someone Else", linkedin="https://linkedin.com/in/raulgongora"))]
        result = _classify(existing, profile=_profile("person-y", name="Raul Gongora Betancourt", linkedin="https://linkedin.com/in/raulgongora"))
        assert result.result == POSSIBLE_SAME_PERSON
        assert "linkedin" in result.candidates[0].matched_on

    def test_different_deterministic_ids_same_person_candidate(self) -> None:
        # The Phase 2A live scenario: person-raul-gongora vs person-raul-gongora-betancourt.
        existing = [_record("raul-gongora-profile", _profile("person-raul-gongora", name="Raul Gongora"))]
        result = _classify(existing)
        assert result.result == POSSIBLE_SAME_PERSON
        candidate = result.candidates[0]
        assert candidate.profile_id == "raul-gongora-profile"
        assert "name-tokens" in candidate.matched_on

    def test_unrelated_names_do_not_match(self) -> None:
        existing = [_record("person-anna", _profile("person-anna-lindqvist", name="Anna Lindqvist"))]
        result = _classify(existing)
        assert result.result == NEW_PERSON
        assert result.candidates == ()

    def test_single_token_containment_is_not_a_match(self) -> None:
        existing = [_record("person-raul", _profile("person-raul", name="Raul"))]
        result = _classify(existing, profile=_profile("person-raul-gongora", name="Raul Gongora"))
        assert result.result == NEW_PERSON

    def test_no_false_positive_on_disjoint_shared_token(self) -> None:
        existing = [_record("person-gongora", _profile("person-gongora", name="Gongora Studio"))]
        result = _classify(existing, profile=_profile("person-x", name="Raul Gongora Betancourt"))
        assert result.result == NEW_PERSON

    def test_identity_conflict_same_name_different_email(self) -> None:
        existing = [_record("person-old", _profile("person-old", name="Raul Gongora Betancourt", email="old@example.com"))]
        result = _classify(existing, profile=_profile("person-new", name="Raul Gongora Betancourt", email="new@example.com"))
        assert result.result == IDENTITY_CONFLICT
        assert result.candidates[0].conflicting_on == ("email",)
        assert "name" in result.candidates[0].matched_on

    def test_identity_conflict_same_name_different_phone(self) -> None:
        existing = [_record("person-old", _profile("person-old", name="Raul Gongora Betancourt", phone="+11111111111"))]
        result = _classify(existing, profile=_profile("person-new", name="Raul Gongora Betancourt", phone="+22222222222"))
        assert result.result == IDENTITY_CONFLICT
        assert result.candidates[0].conflicting_on == ("phone",)

    def test_email_match_with_absent_other_signal_is_not_a_conflict(self) -> None:
        existing = [_record("person-old", _profile("person-old", name="Raul Gongora Betancourt", email="raul@example.com", phone="+11111111111"))]
        result = _classify(existing, profile=_profile("person-new", name="Raul Gongora Betancourt", email="raul@example.com"))
        assert result.result == POSSIBLE_SAME_PERSON
        assert "phone" not in result.candidates[0].conflicting_on
