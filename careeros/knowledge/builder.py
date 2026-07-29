from __future__ import annotations

from typing import Any

from .models import GraphEdge, GraphNode, KnowledgeGraph


class KnowledgeGraphBuilder:
    """Constructs an immutable KnowledgeGraph from a canonical CareerOS profile dict.

    The builder extracts relationship information that is already embedded in
    the profile's reference fields (organizationRefs, institutionRef,
    experienceEvidence) and makes it navigable as a directed graph.
    """

    def build(self, profile: dict[str, Any]) -> KnowledgeGraph:
        nodes: list[GraphNode] = []
        edges: list[GraphEdge] = []

        person = profile.get("person", {})

        self._add_person(nodes, person)
        self._add_experiences(nodes, edges, profile.get("experiences", []), person)
        self._add_skills(nodes, edges, profile.get("skills", []), person)
        self._add_education(nodes, edges, profile.get("education", []), person)
        self._add_organizations(nodes, profile.get("organizations", []))

        return KnowledgeGraph(nodes, edges)

    @staticmethod
    def _add_person(nodes: list[GraphNode], person: dict[str, Any]) -> None:
        pid = person.get("id")
        if not pid:
            return
        names = person.get("names", [])
        label = names[0].get("value", "") if names else ""
        props: dict[str, Any] = {}
        contact = person.get("contact")
        if contact:
            if contact.get("email"):
                props["email"] = contact["email"]
            if contact.get("phone"):
                props["phone"] = contact["phone"]
        location = person.get("location")
        if location and location.get("label"):
            props["location"] = location["label"]
        nodes.append(GraphNode(id=pid, type="person", label=label, properties=props))

    @staticmethod
    def _add_experiences(
        nodes: list[GraphNode],
        edges: list[GraphEdge],
        experiences: list[dict[str, Any]],
        person: dict[str, Any],
    ) -> None:
        pid = person.get("id")
        for exp in experiences:
            eid = exp.get("id")
            if not eid:
                continue
            title = exp.get("title", "")
            props: dict[str, Any] = {
                "title": title,
            }
            dr = exp.get("dateRange")
            if dr:
                if dr.get("start"):
                    props["startDate"] = dr["start"]
                if dr.get("end"):
                    props["endDate"] = dr["end"]
                if "isCurrent" in dr:
                    props["isCurrent"] = dr["isCurrent"]
            if exp.get("engagementType"):
                props["engagementType"] = exp["engagementType"]
            if exp.get("scope"):
                props["scope"] = exp["scope"]
            if exp.get("location"):
                loc = exp["location"]
                if isinstance(loc, dict) and loc.get("label"):
                    props["location"] = loc["label"]
                elif isinstance(loc, str):
                    props["location"] = loc
            nodes.append(
                GraphNode(id=eid, type="experience", label=title, properties=props)
            )
            if pid:
                edges.append(
                    GraphEdge(source_id=pid, target_id=eid, type="HAS_EXPERIENCE")
                )
            for ref in exp.get("organizationRefs", []):
                org_id = ref.get("id")
                if org_id:
                    edges.append(
                        GraphEdge(
                            source_id=eid, target_id=org_id, type="AT_ORGANIZATION"
                        )
                    )

    @staticmethod
    def _add_skills(
        nodes: list[GraphNode],
        edges: list[GraphEdge],
        skills: list[dict[str, Any]],
        person: dict[str, Any],
    ) -> None:
        pid = person.get("id")
        for skill in skills:
            sid = skill.get("id")
            if not sid:
                continue
            name = skill.get("name", "")
            props: dict[str, Any] = {"name": name}
            if skill.get("category"):
                props["category"] = skill["category"]
            exts = skill.get("extensions", {})
            if exts.get("proficiency"):
                props["proficiency"] = exts["proficiency"]
            nodes.append(
                GraphNode(id=sid, type="skill", label=name, properties=props)
            )
            if pid:
                edges.append(
                    GraphEdge(source_id=pid, target_id=sid, type="HAS_SKILL")
                )
            evidence = exts.get("experienceEvidence", [])
            for ev in evidence:
                exp_id = ev.get("experienceId")
                if exp_id:
                    edges.append(
                        GraphEdge(
                            source_id=exp_id, target_id=sid, type="USES_SKILL"
                        )
                    )
                    edges.append(
                        GraphEdge(
                            source_id=sid,
                            target_id=exp_id,
                            type="USED_IN_EXPERIENCE",
                        )
                    )

    @staticmethod
    def _add_education(
        nodes: list[GraphNode],
        edges: list[GraphEdge],
        education: list[dict[str, Any]],
        person: dict[str, Any],
    ) -> None:
        pid = person.get("id")
        for edu in education:
            eid = edu.get("id")
            if not eid:
                continue
            program = edu.get("program", "")
            props: dict[str, Any] = {"program": program}
            if edu.get("fieldOfStudy"):
                props["fieldOfStudy"] = edu["fieldOfStudy"]
            dr = edu.get("dateRange")
            if dr:
                if dr.get("start"):
                    props["startDate"] = dr["start"]
                if dr.get("end"):
                    props["endDate"] = dr["end"]
                if "isCurrent" in dr:
                    props["isCurrent"] = dr["isCurrent"]
            nodes.append(
                GraphNode(
                    id=eid, type="education", label=program, properties=props
                )
            )
            if pid:
                edges.append(
                    GraphEdge(source_id=pid, target_id=eid, type="HAS_EDUCATION")
                )
            inst_ref = edu.get("institutionRef")
            if inst_ref:
                org_id = inst_ref.get("id")
                if org_id:
                    edges.append(
                        GraphEdge(
                            source_id=eid,
                            target_id=org_id,
                            type="AT_ORGANIZATION",
                        )
                    )

    @staticmethod
    def _add_organizations(
        nodes: list[GraphNode], organizations: list[dict[str, Any]]
    ) -> None:
        for org in organizations:
            oid = org.get("id")
            if not oid:
                continue
            name = org.get("name", "")
            nodes.append(
                GraphNode(id=oid, type="organization", label=name, properties={"name": name})
            )
