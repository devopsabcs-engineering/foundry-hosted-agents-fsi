"""Bilingual error-message catalog for the reviewer approval surface.

Each backend error path gets a stable machine-readable `code` and a localized
`detail` string, selected by the `X-UI-Language` header the frontend sends
with every request. `pick_language` is the boundary helper that turns a raw
header value into a supported language, falling back to `DEFAULT_LANGUAGE`
for anything absent or unrecognized; `message` never raises for an
unrecognized language either, for callers (like `auth.py`) that pass a
`language` value straight through without going via `pick_language` first.
"""

LANGUAGES = ("en-CA", "fr-CA")
DEFAULT_LANGUAGE = "en-CA"

MESSAGES: dict[str, dict[str, str]] = {
    "SIGNIN_UNAVAILABLE": {
        "en-CA": "Sign-in verification is temporarily unavailable.",
        "fr-CA": "La vérification de connexion est temporairement indisponible.",
    },
    "INVALID_TOKEN": {
        "en-CA": "A valid access token is required.",
        "fr-CA": "Un jeton d'accès valide est requis.",
    },
    "APP_NOT_AUTHORIZED": {
        "en-CA": "This application is not authorized.",
        "fr-CA": "Cette application n'est pas autorisée.",
    },
    "SCOPE_REQUIRED": {
        "en-CA": "Review permission is required.",
        "fr-CA": "L'autorisation de révision est requise.",
    },
    "ROLE_REQUIRED": {
        "en-CA": "Reviewer role is required. Contact the pilot administrator.",
        "fr-CA": "Le rôle de réviseur est requis. Communiquez avec l'administrateur du projet pilote.",
    },
    "IDENTITY_REQUIRED": {
        "en-CA": "A user identity is required.",
        "fr-CA": "Une identité d'utilisateur est requise.",
    },
    "SIGNIN_REQUIRED": {
        "en-CA": "Sign in to continue.",
        "fr-CA": "Connectez-vous pour continuer.",
    },
    "CASE_NOT_FOUND": {
        "en-CA": "Case not found.",
        "fr-CA": "Dossier introuvable.",
    },
    "SELF_APPROVAL": {
        "en-CA": "You prepared this case and cannot decide it.",
        "fr-CA": "Vous avez préparé ce dossier et ne pouvez pas le trancher.",
    },
    "INVALID_TRANSITION": {
        "en-CA": "This case changed since it was loaded. Reload and try again.",
        "fr-CA": "Ce dossier a changé depuis son chargement. Rechargez la page et réessayez.",
    },
    "CASE_ALREADY_EXISTS": {
        "en-CA": "This case already exists.",
        "fr-CA": "Ce dossier existe déjà.",
    },
    "STORE_UNAVAILABLE": {
        "en-CA": "The case store is unavailable.",
        "fr-CA": "Le magasin de dossiers est indisponible.",
    },
    "REQUEST_TOO_LARGE": {
        "en-CA": "Request too large.",
        "fr-CA": "La demande est trop volumineuse.",
    },
    "STALE_REVISION": {
        "en-CA": "This case changed since it was loaded. Reload and try again.",
        "fr-CA": "Ce dossier a changé depuis son chargement. Rechargez la page et réessayez.",
    },
    "CLEAR_CONFIRMATION_REQUIRED": {
        "en-CA": "Type the confirmation phrase exactly to clear the queue.",
        "fr-CA": "Saisissez exactement la phrase de confirmation pour vider la file.",
    },
}


def pick_language(header_value: str | None) -> str:
    return header_value if header_value in LANGUAGES else DEFAULT_LANGUAGE


def message(code: str, language: str) -> str:
    return MESSAGES[code].get(language, MESSAGES[code][DEFAULT_LANGUAGE])
