"""Canonical classification for policy and research findings."""

from enum import StrEnum


class FindingClass(StrEnum):
    MECHANICAL_POLICY_BUG = "MECHANICAL_POLICY_BUG"
    CONTROL_POLICY_LIMITATION = "CONTROL_POLICY_LIMITATION"
    MISSING_POPULATION_LAYER = "MISSING_POPULATION_LAYER"
    RESEARCH_BLOCKED = "RESEARCH_BLOCKED"
