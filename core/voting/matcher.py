def match_templates(template1_bytes, template2_bytes):
    """
    Simplified fingerprint template matching placeholder.
    Compares two byte arrays and returns a similarity score (0–100).
    """
    if len(template1_bytes) != 512 or len(template2_bytes) != 512:
        return 0

    match_count = sum(a == b for a, b in zip(template1_bytes, template2_bytes))
    score = (match_count / 512) * 100
    return score
