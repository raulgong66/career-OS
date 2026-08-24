from __future__ import annotations

from typing import Any, ClassVar

from ..person_data import PersonData
from ..utils import person_id_from_name
from .base import BaseBuilder, BuilderContext


class PersonBuilder(BaseBuilder):
    entity_type: ClassVar[type] = PersonData
    profile_key: ClassVar[str] = "person"
    extraction_field: ClassVar[str] = "person"
    singular: ClassVar[bool] = True

    def normalize(self, items: list) -> list:
        return items

    def build_many(
        self,
        items: list,
        context: BuilderContext,
    ) -> list[dict[str, Any]]:
        if not items:
            return []
        person = items[0]
        person_dict: dict[str, Any] = {
            "id": self._resolve_person_id(person),
            "names": [{"value": person.full_name or "", "usage": "professional"}],
        }
        contact: dict[str, str] = {}
        if person.email:
            contact["email"] = person.email
        if person.phone:
            contact["phone"] = person.phone
        if contact:
            person_dict["contact"] = contact

        if person.location:
            person_dict["location"] = {"label": person.location}

        links = []
        if person.linkedin:
            links.append({"label": "LinkedIn", "href": person.linkedin})
        if person.github:
            links.append({"label": "GitHub", "href": person.github})
        if links:
            person_dict["links"] = links

        return [person_dict]

    @staticmethod
    def _resolve_person_id(person: PersonData) -> str:
        """Deterministic person.id derived from identity, never from the LLM.

        The LLM-provided id is only a fallback when no usable name is available.
        """
        name = (person.full_name or "").strip()
        if not name:
            name = " ".join(
                part for part in (person.first_name or "", person.last_name or "") if part
            ).strip()
        if name:
            derived = person_id_from_name(name)
            if derived:
                return derived
        return person.id or "person-unknown"
