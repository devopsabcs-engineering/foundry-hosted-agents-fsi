"""Bilingual (en-CA / fr-CA) message catalog for web-chat backend error text."""

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
        "en-CA": "Chat permission is required.",
        "fr-CA": "L'autorisation de clavardage est requise.",
    },
    "MEMBERSHIP_REQUIRED": {
        "en-CA": "Pilot membership is required. Contact the pilot administrator.",
        "fr-CA": "L'adhésion au programme pilote est requise. Communiquez avec l'administrateur du programme pilote.",
    },
    "IDENTITY_REQUIRED": {
        "en-CA": "A user identity is required.",
        "fr-CA": "Une identité d'utilisateur est requise.",
    },
    "SIGNIN_REQUIRED": {
        "en-CA": "Sign in to continue.",
        "fr-CA": "Connectez-vous pour continuer.",
    },
    "PILOT_CAPACITY": {
        "en-CA": "Pilot capacity reached. Try again later.",
        "fr-CA": "Capacité du programme pilote atteinte. Réessayez plus tard.",
    },
    "SESSION_LIMIT": {
        "en-CA": "Close an existing conversation before starting another.",
        "fr-CA": "Fermez une conversation existante avant d'en commencer une autre.",
    },
    "CONVERSATION_NOT_FOUND": {
        "en-CA": "Conversation not found. Start a new conversation.",
        "fr-CA": "Conversation introuvable. Commencez une nouvelle conversation.",
    },
    "CONVERSATION_EXPIRED": {
        "en-CA": "Conversation expired. Start a new conversation.",
        "fr-CA": "Conversation expirée. Commencez une nouvelle conversation.",
    },
    "REQUEST_TOO_LARGE": {
        "en-CA": "Request too large.",
        "fr-CA": "Demande trop volumineuse.",
    },
    "RESPONSE_IN_PROGRESS": {
        "en-CA": "Stop the current response first.",
        "fr-CA": "Arrêtez d'abord la réponse en cours.",
    },
    "IDEMPOTENCY_KEY_REUSED": {
        "en-CA": "This request key was already used for a different message.",
        "fr-CA": "Cette clé de demande a déjà été utilisée pour un message différent.",
    },
    "RESPONSE_BUSY": {
        "en-CA": "A response is already in progress.",
        "fr-CA": "Une réponse est déjà en cours.",
    },
    "CONVERSATION_LIMIT": {
        "en-CA": "Conversation limit reached. Start a new conversation.",
        "fr-CA": "Limite de conversation atteinte. Commencez une nouvelle conversation.",
    },
    "PILOT_BUSY": {
        "en-CA": "The pilot is busy. Try again shortly.",
        "fr-CA": "Le programme pilote est occupé. Réessayez sous peu.",
    },
    "ASSESSMENT_FAILED": {
        "en-CA": "The assessment could not complete. Try again.",
        "fr-CA": "L'évaluation n'a pas pu se terminer. Réessayez.",
    },
    "SERVICE_UNAVAILABLE": {
        "en-CA": "The service is temporarily unavailable.",
        "fr-CA": "Le service est temporairement indisponible.",
    },
}


def pick_language(header_value: str | None) -> str:
    return header_value if header_value in LANGUAGES else DEFAULT_LANGUAGE


def message(code: str, language: str) -> str:
    return MESSAGES[code][language if language in LANGUAGES else DEFAULT_LANGUAGE]
