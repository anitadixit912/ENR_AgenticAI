"""SAP AI Core credential validation and LLM factory with clear error reporting."""
import logging
import os

logger = logging.getLogger(__name__)

REQUIRED_AICORE_VARS = {
    "AICORE_AUTH_URL": "Token endpoint URL (from AI Core service key â url)",
    "AICORE_CLIENT_ID": "OAuth client ID (from AI Core service key â clientid)",
    "AICORE_CLIENT_SECRET": "OAuth client secret (from AI Core service key â clientsecret)",
    "AICORE_BASE_URL": "AI API base URL (from AI Core service key â serviceurls.AI_API_URL)",
}


def validate_aicore_credentials() -> tuple[bool, list[str]]:
    """
    Check that all required AI Core env vars are set and non-empty.

    Returns:
        (all_present: bool, missing_vars: list[str])
    """
    missing = [
        f"  â¢ {var}  â {hint}"
        for var, hint in REQUIRED_AICORE_VARS.items()
        if not os.environ.get(var, "").strip()
    ]
    return (len(missing) == 0), missing


def log_aicore_status() -> bool:
    """
    Log a startup banner showing AI Core credential status.

    Returns True if all credentials are present, False otherwise.
    """
    ok, missing = validate_aicore_credentials()

    if ok:
        model = os.environ.get("AICORE_LLM_MODEL", "gpt-4o")
        resource_group = os.environ.get("AICORE_RESOURCE_GROUP", "default")
        logger.info(
            "â SAP AI Core credentials OK â model=%s, resource_group=%s",
            model, resource_group,
        )
    else:
        logger.warning(
            "â ï¸  SAP AI Core credentials are MISSING or EMPTY.\n"
            "LLM-based risk scoring and conversational queries will NOT work.\n"
            "The following environment variables must be set:\n%s\n\n"
            "For local development: fill in .env (never commit credentials).\n"
            "For BTP deployment:    inject via Kubernetes secrets "
            "(the platform uses the 'cred-customer-agent' secret automatically).\n"
            "Falling back to rule-based scoring where possible.",
            "\n".join(missing),
        )
    return ok


def build_llm(temperature: float = 0.1):
    """
    Build a ChatLiteLLM instance backed by SAP AI Core.

    Raises a descriptive RuntimeError if credentials are missing so the caller
    can surface a clear message rather than an opaque authentication error.
    """
    ok, missing = validate_aicore_credentials()
    if not ok:
        raise RuntimeError(
            "Cannot initialise LLM â SAP AI Core credentials are not configured.\n"
            "Missing environment variables:\n"
            + "\n".join(missing)
            + "\n\nSet them in .env (local) or as Kubernetes secrets (BTP)."
        )

    from langchain_litellm import ChatLiteLLM  # ChatLiteLLM lives in langchain_litellm, not litellm

    model = os.environ.get("AICORE_LLM_MODEL", "gpt-4o")
    logger.debug("Building ChatLiteLLM: model=%s, temperature=%s", model, temperature)
    return ChatLiteLLM(model=model, temperature=temperature)
