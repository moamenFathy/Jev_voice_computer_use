"""
Verification Engine for JEV Reliability Architecture (Phase 1).
Separates Tool Execution from Goal Verification ("Execution != Goal Achievement").
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, List
import re
import uiautomation as auto
from src.core.observation import Observation


@dataclass
class VerificationResult:
    verified: bool
    message: str = ""
    evidence: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "verified": self.verified,
            "message": self.message,
            "evidence": self.evidence,
        }


class Verifier(ABC):
    """Abstract base class for all domain verifiers."""

    @abstractmethod
    def verify(self, expected: str, observation: Observation) -> VerificationResult:
        """
        Validates whether the observation confirms that the expected goal/state was achieved.
        """
        pass


class AppLaunchVerifier(Verifier):
    """Verifies that an application window exists, is active, or is running."""

    def verify(self, expected: str, observation: Observation) -> VerificationResult:
        expected_clean = expected.lower().strip()
        data = observation.data or {}
        obs_title = str(data.get("window_title", "") or observation.description).lower()
        process_exists = bool(data.get("process_exists", False))
        window_found = bool(data.get("window_found", False))

        evidence = {
            "expected_app": expected,
            "observed_window": obs_title,
            "process_exists": process_exists,
            "window_found": window_found,
            "source": observation.source,
        }

        # Check direct substring match in window title
        if expected_clean in obs_title or (window_found and process_exists):
            return VerificationResult(
                verified=True,
                message=f"Application window '{expected}' detected and verified.",
                evidence=evidence,
            )

        # Check known aliases
        alias_matches = {
            "notepad": ["notepad", "مفكرة", "المفكرة", "untitled - notepad", "بلا عنوان - المفكرة"],
            "calculator": ["calculator", "حاسبة", "الحاسبة", "calc"],
            "spotify": ["spotify", "سبوتيفاي", "سبوتفاي", "spotify free", "spotify premium"],
            "rider": ["rider", "jetbrains rider"],
            "code": ["visual studio code", "vscode", "code"],
            "visual studio": ["visual studio", "devenv"],
            "paint": ["paint", "الرسام", "untitled - paint"],
            "chrome": ["google chrome", "chrome"],
            "edge": ["microsoft edge", "edge"],
        }

        for app_key, aliases in alias_matches.items():
            if expected_clean == app_key or expected_clean in aliases:
                if any(al in obs_title for al in aliases) or window_found:
                    return VerificationResult(
                        verified=True,
                        message=f"Application '{expected}' matched window '{obs_title}'.",
                        evidence=evidence,
                    )

        return VerificationResult(
            verified=False,
            message=f"Expected app '{expected}' not found in active window '{obs_title}'.",
            evidence=evidence,
        )


class TextVerifier(Verifier):
    """Verifies that expected text exists in the target editor, control value, or clipboard."""

    def verify(self, expected: str, observation: Observation) -> VerificationResult:
        expected_clean = expected.strip()
        data = observation.data or {}
        observed_text = str(data.get("text", "") or observation.description or "")

        evidence = {
            "expected_text": expected_clean,
            "observed_text_sample": observed_text[:100],
            "source": observation.source,
        }

        if not expected_clean:
            return VerificationResult(
                verified=True,
                message="Empty expected text trivially verified.",
                evidence=evidence,
            )

        # Normalize spaces for comparison
        norm_expected = re.sub(r"\s+", " ", expected_clean).strip()
        norm_observed = re.sub(r"\s+", " ", observed_text).strip()

        if norm_expected in norm_observed or norm_expected.lower() in norm_observed.lower():
            return VerificationResult(
                verified=True,
                message=f"Text '{expected_clean}' verified in target control.",
                evidence=evidence,
            )

        return VerificationResult(
            verified=False,
            message=f"Text '{expected_clean}' not found in observed text '{observed_text[:60]}...'",
            evidence=evidence,
        )


class UIElementVerifier(Verifier):
    """Verifies that a UI element was clicked, toggled, or exists in the active window."""

    def verify(self, expected: str, observation: Observation) -> VerificationResult:
        data = observation.data or {}
        element_found = bool(data.get("element_found", False))
        is_enabled = bool(data.get("is_enabled", True))
        action_performed = bool(data.get("action_performed", False))

        evidence = {
            "expected_element": expected,
            "element_found": element_found,
            "is_enabled": is_enabled,
            "action_performed": action_performed,
            "source": observation.source,
        }

        if element_found or action_performed:
            return VerificationResult(
                verified=True,
                message=f"UI element '{expected}' verified.",
                evidence=evidence,
            )

        return VerificationResult(
            verified=False,
            message=f"UI element '{expected}' verification failed.",
            evidence=evidence,
        )


class SearchVerifier(Verifier):
    """Verifies that search query was submitted or navigation occurred."""

    def verify(self, expected: str, observation: Observation) -> VerificationResult:
        data = observation.data or {}
        submitted = bool(data.get("submitted", False))
        url_opened = bool(data.get("url_opened", False))
        results_loaded = bool(data.get("results_loaded", False))

        evidence = {
            "expected_query": expected,
            "submitted": submitted,
            "url_opened": url_opened,
            "results_loaded": results_loaded,
            "source": observation.source,
        }

        if submitted or url_opened or results_loaded:
            return VerificationResult(
                verified=True,
                message=f"Search/Navigation for '{expected}' verified.",
                evidence=evidence,
            )

        return VerificationResult(
            verified=False,
            message=f"Search/Navigation for '{expected}' could not be verified.",
            evidence=evidence,
        )
