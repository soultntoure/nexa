"""PII functions — currently disabled, kept for interface compatibility.

These are intentional no-ops. PII masking and scanning are disabled
because all identifiers are kept visible for audit purposes.

TODO: implement if PII handling requirements change.
"""


def mask_pii(text: str) -> str:
    """No-op: PII masking is currently disabled."""
    return text


def scan_text_for_pii(text: str) -> bool:
    """No-op: PII scanning is currently disabled. Always returns False."""
    return False
