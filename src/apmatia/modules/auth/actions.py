from __future__ import annotations

from apmatia.core.registry import ActionContribution


ACTION_DESCRIPTORS: tuple[ActionContribution, ...] = (
    ActionContribution(
        module_id="auth",
        action_id="auth.login",
        name="Sign In",
        description="Authenticate an existing Apmatia account.",
        metadata={"object_type": "authentication"},
    ),
    ActionContribution(
        module_id="auth",
        action_id="auth.register",
        name="Create Account",
        description="Create and authenticate a new Apmatia account.",
        metadata={"object_type": "authentication"},
    ),
)
