from careeros.knowledge import GraphEdge, GraphNode, KnowledgeGraph, KnowledgeGraphBuilder


def _minimal_profile() -> dict:
    return {
        "profileVersion": "1.0.0",
        "person": {
            "id": "person-raul",
            "names": [{"value": "Raul Gongora", "usage": "professional"}],
        },
        "professionalSummaries": [],
        "experiences": [],
        "organizations": [],
        "projects": [],
        "skills": [],
        "achievements": [],
        "evidence": [],
        "education": [],
        "certifications": [],
        "artifacts": [],
        "targetContexts": [],
    }


def _full_profile() -> dict:
    return {
        "profileVersion": "1.0.0",
        "person": {
            "id": "person-raul",
            "names": [{"value": "Raul Gongora", "usage": "professional"}],
            "contact": {
                "email": "raul@example.com",
                "phone": "+46-70-123-4567",
            },
            "location": {"label": "Stockholm, Sweden"},
            "links": [
                {"label": "LinkedIn", "href": "https://linkedin.com/in/raul"},
            ],
        },
        "professionalSummaries": [],
        "experiences": [
            {
                "id": "exp-qred-bank",
                "title": "Senior DevSecOps Engineer",
                "organizationRefs": [
                    {"id": "org-qred-bank", "type": "organization"}
                ],
                "dateRange": {
                    "start": "2022-03",
                    "end": "2025-01",
                    "isCurrent": False,
                },
                "location": {"label": "Stockholm, Sweden"},
                "engagementType": "Full-time",
                "scope": "Full stack developer",
            },
            {
                "id": "exp-kth",
                "title": "Teaching Assistant",
                "organizationRefs": [
                    {"id": "org-kth", "type": "organization"}
                ],
                "dateRange": {
                    "start": "2019-09",
                    "end": "2020-06",
                    "isCurrent": False,
                },
            },
        ],
        "organizations": [
            {"id": "org-qred-bank", "name": "Qred Bank"},
            {"id": "org-kth", "name": "KTH Royal Institute of Technology"},
        ],
        "projects": [],
        "skills": [
            {
                "id": "skill-python",
                "name": "Python",
                "category": "Programming Language",
                "extensions": {
                    "proficiency": "Advanced",
                    "experienceEvidence": [
                        {
                            "experienceId": "exp-qred-bank",
                            "organization": "Qred Bank",
                            "title": "Senior DevSecOps Engineer",
                        }
                    ],
                },
            },
            {
                "id": "skill-kubernetes",
                "name": "Kubernetes",
                "category": "Orchestration",
                "extensions": {
                    "experienceEvidence": [
                        {
                            "experienceId": "exp-qred-bank",
                            "organization": "Qred Bank",
                            "title": "Senior DevSecOps Engineer",
                        }
                    ],
                },
            },
            {
                "id": "skill-java",
                "name": "Java",
                "extensions": {
                    "experienceEvidence": [
                        {
                            "experienceId": "exp-kth",
                            "organization": "KTH",
                            "title": "Teaching Assistant",
                        }
                    ],
                },
            },
        ],
        "achievements": [],
        "evidence": [],
        "education": [
            {
                "id": "edu-kth-m-sc",
                "program": "M.Sc. in Computer Science",
                "fieldOfStudy": "Computer Science",
                "institutionRef": {
                    "id": "org-kth",
                    "type": "organization",
                },
                "dateRange": {"start": "2018", "end": "2021", "isCurrent": False},
            }
        ],
        "certifications": [],
        "artifacts": [],
        "targetContexts": [],
    }


# ---------------------------------------------------------------------------
# Node & Edge creation
# ---------------------------------------------------------------------------


def test_graph_node_immutable() -> None:
    n = GraphNode(id="n1", type="skill", label="Python", properties={"name": "Python"})
    assert n.id == "n1"
    assert n.type == "skill"
    assert n.label == "Python"
    assert n.properties == {"name": "Python"}


def test_graph_edge_immutable() -> None:
    e = GraphEdge(
        source_id="n1", target_id="n2", type="USES_SKILL"
    )
    assert e.source_id == "n1"
    assert e.target_id == "n2"
    assert e.type == "USES_SKILL"


# ---------------------------------------------------------------------------
# KnowledgeGraph construction & immutability
# ---------------------------------------------------------------------------


def test_graph_empty() -> None:
    g = KnowledgeGraph([], [])
    assert g.node_count == 0
    assert g.edge_count == 0
    assert g.nodes == {}
    assert g.edges == []


def test_graph_nodes_defensive_copy() -> None:
    n = GraphNode(id="n1", type="skill", label="Py")
    g = KnowledgeGraph([n], [])
    returned = g.nodes
    assert returned == {"n1": n}
    # Mutating returned dict does NOT affect internal graph
    del returned["n1"]
    assert g.node_count == 1


def test_graph_duplicate_node_raises() -> None:
    n = GraphNode(id="dup", type="skill", label="Py")
    try:
        KnowledgeGraph([n, n], [])
        assert False, "Expected ValueError"
    except ValueError as e:
        assert "Duplicate" in str(e)


def test_builder_dedupes_duplicate_node_ids() -> None:
    """A profile listing the same entity id twice must build a valid graph.

    Regression: repeated education entries (same school/degree, different
    dates) produced duplicate node ids that crashed health analysis with a
    ``Duplicate node ID`` ValueError.
    """
    profile = _minimal_profile()
    profile["education"] = [
        {
            "id": "edu-dup",
            "program": "B.S.",
            "institutionRef": {"id": "org-uni", "type": "organization"},
        },
        {
            "id": "edu-dup",
            "program": "B.S.",
            "institutionRef": {"id": "org-uni", "type": "organization"},
        },
    ]
    profile["organizations"] = [{"id": "org-uni", "name": "University"}]
    g = KnowledgeGraphBuilder().build(profile)
    assert g.node_count == 3  # person + one education (deduplicated) + org
    assert "edu-dup" in g.nodes
    assert len(g.education()) == 1
    assert g.nodes["edu-dup"].type == "education"


def test_builder_dedupe_keeps_first_occurrence() -> None:
    profile = _minimal_profile()
    profile["experiences"] = [{"id": "person-raul", "title": "collision"}]
    g = KnowledgeGraphBuilder().build(profile)
    assert g.nodes["person-raul"].type == "person"


# ---------------------------------------------------------------------------
# Builder — minimal profile
# ---------------------------------------------------------------------------


def test_builder_empty_profile() -> None:
    profile = _minimal_profile()
    assert profile is not None
    g = KnowledgeGraphBuilder().build(profile)
    assert g.node_count == 1  # only person
    assert g.edge_count == 0


def test_builder_minimal_person() -> None:
    profile = _minimal_profile()
    g = KnowledgeGraphBuilder().build(profile)
    person = g.nodes["person-raul"]
    assert person.type == "person"
    assert person.label == "Raul Gongora"
    assert person.properties == {}


# ---------------------------------------------------------------------------
# Builder — full profile node counts & types
# ---------------------------------------------------------------------------


def test_builder_node_types() -> None:
    g = KnowledgeGraphBuilder().build(_full_profile())
    assert g.node_count == 9  # 1 person + 2 exp + 3 skill + 1 edu + 2 org
    types = {n.type for n in g.nodes.values()}
    assert types == {"person", "experience", "skill", "education", "organization"}


def test_builder_person_node() -> None:
    g = KnowledgeGraphBuilder().build(_full_profile())
    p = g.nodes["person-raul"]
    assert p.type == "person"
    assert p.label == "Raul Gongora"
    assert p.properties == {
        "email": "raul@example.com",
        "phone": "+46-70-123-4567",
        "location": "Stockholm, Sweden",
    }


def test_builder_experience_nodes() -> None:
    g = KnowledgeGraphBuilder().build(_full_profile())
    exp = g.nodes["exp-qred-bank"]
    assert exp.type == "experience"
    assert exp.label == "Senior DevSecOps Engineer"
    assert exp.properties == {
        "title": "Senior DevSecOps Engineer",
        "startDate": "2022-03",
        "endDate": "2025-01",
        "isCurrent": False,
        "engagementType": "Full-time",
        "scope": "Full stack developer",
        "location": "Stockholm, Sweden",
    }

    exp2 = g.nodes["exp-kth"]
    assert exp2.type == "experience"
    assert exp2.label == "Teaching Assistant"
    assert exp2.properties == {
        "title": "Teaching Assistant",
        "startDate": "2019-09",
        "endDate": "2020-06",
        "isCurrent": False,
    }


def test_builder_skill_nodes() -> None:
    g = KnowledgeGraphBuilder().build(_full_profile())
    py = g.nodes["skill-python"]
    assert py.type == "skill"
    assert py.label == "Python"
    assert py.properties == {
        "name": "Python",
        "category": "Programming Language",
        "proficiency": "Advanced",
    }

    k8s = g.nodes["skill-kubernetes"]
    assert k8s.type == "skill"
    assert k8s.label == "Kubernetes"
    assert k8s.properties == {"name": "Kubernetes", "category": "Orchestration"}

    java = g.nodes["skill-java"]
    assert java.type == "skill"
    assert java.label == "Java"
    assert java.properties == {"name": "Java"}


def test_builder_education_node() -> None:
    g = KnowledgeGraphBuilder().build(_full_profile())
    edu = g.nodes["edu-kth-m-sc"]
    assert edu.type == "education"
    assert edu.label == "M.Sc. in Computer Science"
    assert edu.properties == {
        "program": "M.Sc. in Computer Science",
        "fieldOfStudy": "Computer Science",
        "startDate": "2018",
        "endDate": "2021",
        "isCurrent": False,
    }


def test_builder_organization_nodes() -> None:
    g = KnowledgeGraphBuilder().build(_full_profile())
    qred = g.nodes["org-qred-bank"]
    assert qred.type == "organization"
    assert qred.label == "Qred Bank"
    assert qred.properties == {"name": "Qred Bank"}

    kth = g.nodes["org-kth"]
    assert kth.type == "organization"
    assert kth.label == "KTH Royal Institute of Technology"
    assert kth.properties == {"name": "KTH Royal Institute of Technology"}


# ---------------------------------------------------------------------------
# Edge types & counts
# ---------------------------------------------------------------------------


def test_builder_edge_types() -> None:
    g = KnowledgeGraphBuilder().build(_full_profile())
    edge_types = {e.type for e in g.edges}
    assert edge_types == {
        "HAS_EXPERIENCE",
        "HAS_SKILL",
        "HAS_EDUCATION",
        "AT_ORGANIZATION",
        "USES_SKILL",
        "USED_IN_EXPERIENCE",
    }


def test_builder_edge_count() -> None:
    g = KnowledgeGraphBuilder().build(_full_profile())
    # 2 HAS_EXPERIENCE (person→each exp)
    # 3 HAS_SKILL (person→each skill)
    # 1 HAS_EDUCATION (person→edu)
    # 3 AT_ORGANIZATION (2 exp→org + 1 edu→org)
    # 3 USES_SKILL (each experienceEvidence entry)
    # 3 USED_IN_EXPERIENCE (reverse of each USES_SKILL)
    assert g.edge_count == 2 + 3 + 1 + 3 + 3 + 3  # 15


# ---------------------------------------------------------------------------
# Relationship correctness
# ---------------------------------------------------------------------------


def test_person_has_experience_edges() -> None:
    g = KnowledgeGraphBuilder().build(_full_profile())
    person_id = "person-raul"
    exp_ids = {"exp-qred-bank", "exp-kth"}
    has_exp = [
        e for e in g.edges
        if e.source_id == person_id and e.type == "HAS_EXPERIENCE"
    ]
    assert len(has_exp) == 2
    assert {e.target_id for e in has_exp} == exp_ids


def test_person_has_skill_edges() -> None:
    g = KnowledgeGraphBuilder().build(_full_profile())
    person_id = "person-raul"
    skill_ids = {"skill-python", "skill-kubernetes", "skill-java"}
    has_skill = [
        e for e in g.edges
        if e.source_id == person_id and e.type == "HAS_SKILL"
    ]
    assert len(has_skill) == 3
    assert {e.target_id for e in has_skill} == skill_ids


def test_person_has_education_edges() -> None:
    g = KnowledgeGraphBuilder().build(_full_profile())
    person_id = "person-raul"
    has_edu = [
        e for e in g.edges
        if e.source_id == person_id and e.type == "HAS_EDUCATION"
    ]
    assert len(has_edu) == 1
    assert has_edu[0].target_id == "edu-kth-m-sc"


def test_experience_at_organization_edges() -> None:
    g = KnowledgeGraphBuilder().build(_full_profile())
    at_org = {e for e in g.edges if e.type == "AT_ORGANIZATION"}
    assert len(at_org) == 3
    expected = {
        ("exp-qred-bank", "org-qred-bank"),
        ("exp-kth", "org-kth"),
        ("edu-kth-m-sc", "org-kth"),
    }
    assert {(e.source_id, e.target_id) for e in at_org} == expected


def test_experience_uses_skill_edges() -> None:
    g = KnowledgeGraphBuilder().build(_full_profile())
    uses = [e for e in g.edges if e.type == "USES_SKILL"]
    assert len(uses) == 3
    expected = {
        ("exp-qred-bank", "skill-python"),
        ("exp-qred-bank", "skill-kubernetes"),
        ("exp-kth", "skill-java"),
    }
    assert {(e.source_id, e.target_id) for e in uses} == expected


def test_skill_used_in_experience_edges() -> None:
    g = KnowledgeGraphBuilder().build(_full_profile())
    used_in = [e for e in g.edges if e.type == "USED_IN_EXPERIENCE"]
    assert len(used_in) == 3
    expected = {
        ("skill-python", "exp-qred-bank"),
        ("skill-kubernetes", "exp-qred-bank"),
        ("skill-java", "exp-kth"),
    }
    assert {(e.source_id, e.target_id) for e in used_in} == expected


def test_skill_with_no_evidence_has_no_edges() -> None:
    profile = _full_profile()
    profile["skills"] = [
        {
            "id": "skill-solo",
            "name": "SoloSkill",
            "extensions": {},
        }
    ]
    g = KnowledgeGraphBuilder().build(profile)
    # person→skill edge should still exist
    has_skill = [
        e
        for e in g.edges
        if e.source_id == "person-raul" and e.type == "HAS_SKILL"
    ]
    assert len(has_skill) == 1
    assert has_skill[0].target_id == "skill-solo"
    assert not any(e.type == "USES_SKILL" for e in g.edges)
    assert not any(e.type == "USED_IN_EXPERIENCE" for e in g.edges)


# ---------------------------------------------------------------------------
# Duplicate prevention
# ---------------------------------------------------------------------------


def test_no_duplicate_nodes() -> None:
    g = KnowledgeGraphBuilder().build(_full_profile())
    ids = list(g.nodes.keys())
    assert len(ids) == len(set(ids))


def test_no_duplicate_edges() -> None:
    g = KnowledgeGraphBuilder().build(_full_profile())
    edge_tuples = [(e.source_id, e.target_id, e.type) for e in g.edges]
    assert len(edge_tuples) == len(set(edge_tuples))


# ---------------------------------------------------------------------------
# Query API
# ---------------------------------------------------------------------------


def test_query_skills() -> None:
    g = KnowledgeGraphBuilder().build(_full_profile())
    result = g.skills()
    assert len(result) == 3
    assert {n.label for n in result} == {"Python", "Kubernetes", "Java"}


def test_query_experiences() -> None:
    g = KnowledgeGraphBuilder().build(_full_profile())
    result = g.experiences()
    assert len(result) == 2
    assert {n.label for n in result} == {
        "Senior DevSecOps Engineer",
        "Teaching Assistant",
    }


def test_query_education() -> None:
    g = KnowledgeGraphBuilder().build(_full_profile())
    result = g.education()
    assert len(result) == 1
    assert result[0].label == "M.Sc. in Computer Science"


def test_query_organizations() -> None:
    g = KnowledgeGraphBuilder().build(_full_profile())
    result = g.organizations()
    assert len(result) == 2
    assert {n.label for n in result} == {
        "Qred Bank",
        "KTH Royal Institute of Technology",
    }


def test_query_skill() -> None:
    g = KnowledgeGraphBuilder().build(_full_profile())
    py = g.skill("Python")
    assert py is not None
    assert py.id == "skill-python"
    assert g.skill("python") is not None  # case-insensitive
    assert g.skill("Unknown") is None


def test_query_skills_used_by() -> None:
    g = KnowledgeGraphBuilder().build(_full_profile())
    skills = g.skills_used_by("exp-qred-bank")
    assert len(skills) == 2
    assert {s.label for s in skills} == {"Python", "Kubernetes"}

    skills2 = g.skills_used_by("exp-kth")
    assert len(skills2) == 1
    assert skills2[0].label == "Java"

    assert g.skills_used_by("nonexistent") == []


def test_query_experiences_using() -> None:
    g = KnowledgeGraphBuilder().build(_full_profile())
    exps = g.experiences_using("Python")
    assert len(exps) == 1
    assert exps[0].label == "Senior DevSecOps Engineer"

    exps2 = g.experiences_using("Java")
    assert len(exps2) == 1
    assert exps2[0].label == "Teaching Assistant"

    assert g.experiences_using("Unknown") == []


def test_query_experiences_using_case_insensitive() -> None:
    g = KnowledgeGraphBuilder().build(_full_profile())
    exps = g.experiences_using("python")
    assert len(exps) == 1


def test_query_organizations_for_skill() -> None:
    g = KnowledgeGraphBuilder().build(_full_profile())
    orgs = g.organizations_for_skill("Python")
    assert len(orgs) == 1
    assert orgs[0].label == "Qred Bank"

    orgs2 = g.organizations_for_skill("Java")
    assert len(orgs2) == 1
    assert orgs2[0].label == "KTH Royal Institute of Technology"

    assert g.organizations_for_skill("Unknown") == []


def test_query_organizations_for_skill_shared_across_experiences() -> None:
    """A skill used across multiple experiences at different orgs."""
    profile = _full_profile()
    profile["skills"].append(
            {
                "id": "skill-python-v2",
                "name": "Python",
            "extensions": {
                "experienceEvidence": [
                    {
                        "experienceId": "exp-qred-bank",
                        "organization": "Qred Bank",
                        "title": "Senior DevSecOps Engineer",
                    },
                    {
                        "experienceId": "exp-kth",
                        "organization": "KTH",
                        "title": "Research Assistant",
                    },
                ],
            },
        }
    )
    # Add another experience at a different org
    profile["experiences"].append(
        {
            "id": "exp-kth-research",
            "title": "Research Assistant",
            "organizationRefs": [
                {"id": "org-kth", "type": "organization"}
            ],
            "dateRange": {"start": "2021-01", "end": "2021-06"},
        }
    )
    g = KnowledgeGraphBuilder().build(profile)
    orgs = g.organizations_for_skill("Python")
    assert len(orgs) == 1  # both refs point to org-kth
    assert orgs[0].label == "Qred Bank"  # only one unique org


def test_query_returns_deterministic_order() -> None:
    """Queries should return nodes in insertion order."""
    g = KnowledgeGraphBuilder().build(_full_profile())
    skill_names = [n.label for n in g.skills()]
    assert skill_names == ["Python", "Kubernetes", "Java"]


# ---------------------------------------------------------------------------
# Graph integrity
# ---------------------------------------------------------------------------


def test_all_nodes_reachable() -> None:
    g = KnowledgeGraphBuilder().build(_full_profile())
    person_id = "person-raul"
    for nid, node in g.nodes.items():
        if nid == person_id:
            continue
        # Every non-person node should have at least one incoming edge
        incoming = [e for e in g.edges if e.target_id == nid]
        assert len(incoming) >= 1, f"Node {nid} ({node.label}) has no incoming edges"


def test_all_edges_reference_existing_nodes() -> None:
    g = KnowledgeGraphBuilder().build(_full_profile())
    for e in g.edges:
        assert e.source_id in g.nodes, f"Edge source {e.source_id} not found"
        assert e.target_id in g.nodes, f"Edge target {e.target_id} not found"


def test_every_experience_has_at_least_one_org() -> None:
    g = KnowledgeGraphBuilder().build(_full_profile())
    for exp in g.experiences():
        has_org = any(
            e.source_id == exp.id and e.type == "AT_ORGANIZATION"
            for e in g.edges
        )
        assert has_org, f"Experience {exp.id} missing AT_ORGANIZATION edge"


def test_every_skill_with_evidence_has_bidirectional_edges() -> None:
    g = KnowledgeGraphBuilder().build(_full_profile())
    for skill in g.skills():
        uses_skills = [
            e for e in g.edges
            if e.target_id == skill.id and e.type == "USES_SKILL"
        ]
        used_in = [
            e for e in g.edges
            if e.source_id == skill.id and e.type == "USED_IN_EXPERIENCE"
        ]
        if uses_skills:
            assert len(used_in) == len(uses_skills), (
                f"Skill {skill.id}: {len(uses_skills)} USES_SKILL but {len(used_in)} USED_IN_EXPERIENCE"
            )


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


def test_no_person_in_profile() -> None:
    g = KnowledgeGraphBuilder().build({"person": {}})
    assert g.node_count == 0


def test_person_with_no_contact_has_empty_properties() -> None:
    profile = _minimal_profile()
    g = KnowledgeGraphBuilder().build(profile)
    assert g.nodes["person-raul"].properties == {}


def test_experience_with_empty_refs_has_no_org_edge() -> None:
    profile = _minimal_profile()
    profile["experiences"] = [
        {
            "id": "exp-solo",
            "title": "Solo Project",
            "organizationRefs": [],
        }
    ]
    g = KnowledgeGraphBuilder().build(profile)
    assert "exp-solo" in g.nodes
    assert not any(
        e.source_id == "exp-solo" and e.type == "AT_ORGANIZATION"
        for e in g.edges
    )


def test_education_without_institution_ref() -> None:
    profile = _minimal_profile()
    profile["education"] = [
        {
            "id": "edu-self",
            "program": "Self-Study",
        }
    ]
    g = KnowledgeGraphBuilder().build(profile)
    assert "edu-self" in g.nodes
    assert not any(
        e.source_id == "edu-self" for e in g.edges
    )


def test_multiple_organizations_converge_on_skill() -> None:
    """Skill used at two experiences at different organizations."""
    profile = _minimal_profile()
    profile["experiences"] = [
        {
            "id": "exp-a",
            "title": "Engineer A",
            "organizationRefs": [{"id": "org-a", "type": "organization"}],
        },
        {
            "id": "exp-b",
            "title": "Engineer B",
            "organizationRefs": [{"id": "org-b", "type": "organization"}],
        },
    ]
    profile["organizations"] = [
        {"id": "org-a", "name": "Company A"},
        {"id": "org-b", "name": "Company B"},
    ]
    profile["skills"] = [
        {
            "id": "skill-x",
            "name": "SkillX",
            "extensions": {
                "experienceEvidence": [
                    {"experienceId": "exp-a", "organization": "A", "title": "Eng A"},
                    {"experienceId": "exp-b", "organization": "B", "title": "Eng B"},
                ],
            },
        }
    ]
    g = KnowledgeGraphBuilder().build(profile)

    # Person node only has 1 skill, not repeated
    has_skill = [
        e for e in g.edges if e.source_id == "person-raul" and e.type == "HAS_SKILL"
    ]
    assert len(has_skill) == 1

    orgs = g.organizations_for_skill("SkillX")
    assert len(orgs) == 2
    assert {o.label for o in orgs} == {"Company A", "Company B"}
