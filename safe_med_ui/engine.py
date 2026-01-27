from dataclasses import dataclass
from typing import Dict, List, Tuple, Any

from .safe_med_adapter import SafeMedAdapter
from .rule_fallback import FallbackRuleEngine


@dataclass
class DeidEngine:
    custom_terms: Dict[str, List[str]]
    enable_categories: Dict[str, bool]
    replacement_mode: str = "tag"
    prefer_native_safe_med: bool = True

    def __post_init__(self):
        self.adapter = SafeMedAdapter().discover()
        self.fallback = FallbackRuleEngine(
            custom_terms=self.custom_terms,
            enable_categories=self.enable_categories,
            replacement_mode=self.replacement_mode,
        )

    def deidentify_text(self, text: str) -> Tuple[str, Dict[str, int], str]:
        """
        return: (text_out, stats, backend_name)
        """
        if self.prefer_native_safe_med and self.adapter.found:
            try:
                out, stats = self.adapter.deidentify(
                    text,
                    custom_terms=self.custom_terms,
                    enable_categories=self.enable_categories,
                    replacement_mode=self.replacement_mode,
                )
                return out, stats, f"safe_med_native:{self.adapter.where}"
            except Exception:
                # native 调用失败则回退
                pass

        out, stats = self.fallback.deidentify(text)
        return out, stats, "fallback_rules"
