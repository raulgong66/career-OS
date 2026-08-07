from .assembler import EvidencePackageAssembler
from .engine import ReasoningEngine
from .findings import ProfileRecommendations, ReasoningFindings
from .models import (
    AnalysisModel,
    Evidence,
    EvidencePackage,
    EvidenceSet,
    ProfileRecommendation,
    ReasoningReport,
    ReasoningResult,
    RuleContext,
)
from .registry import CircularDependencyError, DuplicateRuleError, MissingDependencyError, RegistryError, RuleRegistry
from .rule import Rule


def create_default_registry() -> RuleRegistry:
    """Create a RuleRegistry pre-populated with all built-in reasoning rules."""
    from .rules import (
        CareerHighlightsRule,
        CareerProgressionRule,
        CareerStageRule,
        CertificationUnreferencedRule,
        CloudExperienceRule,
        CoreCompetenciesRule,
        CurrentEmployerRule,
        CurrentRoleRule,
        DomainExperienceRule,
        DuplicateNarrativeRule,
        DuplicateSkillsRule,
        EmergingSkillsRule,
        EmploymentGapRule,
        ExperienceNoTechnologiesRule,
        GenericSummaryRule,
        LeadershipExperienceRule,
        LongestTenureRule,
        MissingBusinessOutcomeRule,
        NoMeasurableAchievementRule,
        ProjectWithoutSkillsRule,
        RareSkillsRule,
        SeniorResponsibilityRule,
        SkillCategoryBalanceRule,
        SkillEvidenceStrengthRule,
        SkillProgressionRule,
        SkillWithoutExperienceRule,
        SpecializedSkillsRule,
        StrongestExperienceRule,
        StrongestSkillsRule,
        TechnologyBreadthRule,
        TotalYearsExperienceRule,
        TransferableSkillsRule,
    )

    registry = RuleRegistry()
    for rule_cls in [
        TotalYearsExperienceRule,
        CurrentEmployerRule,
        CurrentRoleRule,
        LongestTenureRule,
        CareerProgressionRule,
        EmploymentGapRule,
        CareerStageRule,
        StrongestExperienceRule,
        LeadershipExperienceRule,
        CloudExperienceRule,
        TechnologyBreadthRule,
        DomainExperienceRule,
        SeniorResponsibilityRule,
        CareerHighlightsRule,
        StrongestSkillsRule,
        EmergingSkillsRule,
        CoreCompetenciesRule,
        SkillCategoryBalanceRule,
        SkillEvidenceStrengthRule,
        RareSkillsRule,
        SpecializedSkillsRule,
        TransferableSkillsRule,
        SkillProgressionRule,
        NoMeasurableAchievementRule,
        SkillWithoutExperienceRule,
        ExperienceNoTechnologiesRule,
        GenericSummaryRule,
        DuplicateSkillsRule,
        DuplicateNarrativeRule,
        MissingBusinessOutcomeRule,
        CertificationUnreferencedRule,
        ProjectWithoutSkillsRule,
    ]:
        registry.register(rule_cls())
    return registry


__all__ = [
    "ReasoningResult",
    "Evidence",
    "EvidenceSet",
    "EvidencePackage",
    "RuleContext",
    "AnalysisModel",
    "Rule",
    "RuleRegistry",
    "ReasoningEngine",
    "EvidencePackageAssembler",
    "ReasoningFindings",
    "ProfileRecommendation",
    "ProfileRecommendations",
    "ReasoningReport",
    "create_default_registry",
    "RegistryError",
    "DuplicateRuleError",
    "MissingDependencyError",
    "CircularDependencyError",
]
