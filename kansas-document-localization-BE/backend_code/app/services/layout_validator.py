class LayoutValidator:

    def check_risk(self, original_text: str, translated_text: str, segment: dict) -> str:
        original_len = len(original_text)
        translated_len = len(translated_text)

        if original_len == 0:
            return "low"

        expansion_ratio = translated_len / original_len

        if expansion_ratio <= 1.2:
            return "low"
        elif expansion_ratio <= 1.4:
            return "medium"
        else:
            return "high"