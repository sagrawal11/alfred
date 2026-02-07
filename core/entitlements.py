"""
Plan entitlements and feature gating.

Single source of truth for Free / Core / Pro: turn quotas and which
features each plan can use. Used by routes and SMS handler to enforce
limits and gate access.
"""

from __future__ import annotations

from typing import Optional

# Plan names as stored on user (e.g. from Stripe).
PLAN_FREE = "free"
PLAN_CORE = "core"
PLAN_PRO = "pro"

# Feature names for gating (trends, integrations, image upload).
FEATURE_TRENDS = "trends"
FEATURE_INTEGRATIONS = "integrations"
FEATURE_IMAGE_UPLOAD = "image_upload"

# Turn quotas per plan (monthly). None means unlimited.
_TURN_QUOTA_BY_PLAN = {
    PLAN_FREE: 50,
    PLAN_CORE: 1000,
    PLAN_PRO: None,
}

# Features allowed per plan. Free: none of these; Core and Pro: all.
_FEATURES_BY_PLAN = {
    PLAN_FREE: set(),
    PLAN_CORE: {FEATURE_TRENDS, FEATURE_INTEGRATIONS, FEATURE_IMAGE_UPLOAD},
    PLAN_PRO: {FEATURE_TRENDS, FEATURE_INTEGRATIONS, FEATURE_IMAGE_UPLOAD},
}


def normalize_plan(plan: Optional[str]) -> str:
    """
    Normalize plan string from user record to a known plan name.

    Args:
        plan: Raw plan value (e.g. user.get("plan")).

    Returns:
        One of "free", "core", "pro"; defaults to "free" if unknown or missing.
    """
    if not plan or not isinstance(plan, str):
        return PLAN_FREE
    p = plan.strip().lower()
    if p in (PLAN_FREE, PLAN_CORE, PLAN_PRO):
        return p
    return PLAN_FREE


def get_turn_quota(plan: str) -> Optional[int]:
    """
    Monthly agent turn quota for the given plan.

    Args:
        plan: Normalized plan name (use normalize_plan if from user record).

    Returns:
        Max turns per month, or None for unlimited.
    """
    return _TURN_QUOTA_BY_PLAN.get(normalize_plan(plan), _TURN_QUOTA_BY_PLAN[PLAN_FREE])


def can_use_feature(plan: str, feature: str) -> bool:
    """
    Whether the plan is allowed to use the given feature.

    Args:
        plan: Normalized plan name.
        feature: One of FEATURE_TRENDS, FEATURE_INTEGRATIONS, FEATURE_IMAGE_UPLOAD.

    Returns:
        True if the plan includes the feature, False otherwise.
    """
    allowed = _FEATURES_BY_PLAN.get(normalize_plan(plan), _FEATURES_BY_PLAN[PLAN_FREE])
    return feature in allowed
