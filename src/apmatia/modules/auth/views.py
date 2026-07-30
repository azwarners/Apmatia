from __future__ import annotations

from apmatia.core.registry import ViewContribution


_USERNAME_FIELD = {
    "key": "username",
    "label": "Username",
    "required": True,
}
_PASSWORD_FIELD = {
    "key": "password",
    "label": "Password",
    "type": "password",
    "required": True,
}


VIEW_DESCRIPTORS: tuple[ViewContribution, ...] = (
    ViewContribution(
        module_id="auth",
        action_id="auth.login",
        view_id="auth.login.view",
        name="Sign In",
        description="Sign in to Apmatia with an existing account.",
        metadata={
            "object_type": "authentication",
            "ui": {
                "render_mode": "form",
                "navigation": "pre_authentication",
                "title": "Sign In",
                "form": {
                    "key": "login",
                    "title": "Sign In",
                    "submit_label": "Sign In",
                    "cancel_label": "",
                    "fields": [_USERNAME_FIELD, _PASSWORD_FIELD],
                },
                "view_actions": [
                    {
                        "key": "login",
                        "label": "Sign In",
                        "intent": "save",
                        "scope": "view",
                        "style": "primary",
                        "payload": {"auth_action": "login"},
                    }
                ],
            },
        },
    ),
    ViewContribution(
        module_id="auth",
        action_id="auth.register",
        view_id="auth.register.view",
        name="Create Account",
        description="Create an Apmatia account and sign in.",
        metadata={
            "object_type": "authentication",
            "ui": {
                "render_mode": "form",
                "navigation": "pre_authentication",
                "title": "Create Account",
                "form": {
                    "key": "register",
                    "title": "Create Account",
                    "submit_label": "Create Account",
                    "cancel_label": "",
                    "fields": [
                        _USERNAME_FIELD,
                        _PASSWORD_FIELD,
                        {
                            "key": "password_confirm",
                            "label": "Confirm Password",
                            "type": "password",
                            "required": True,
                        },
                    ],
                },
                "view_actions": [
                    {
                        "key": "register",
                        "label": "Create Account",
                        "intent": "save",
                        "scope": "view",
                        "style": "primary",
                        "payload": {"auth_action": "register"},
                    }
                ],
            },
        },
    ),
)
