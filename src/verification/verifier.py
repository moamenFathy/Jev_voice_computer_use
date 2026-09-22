"""
Verification Engine for JEV Reliability Architecture (Phase 1).
Separates Tool Execution from Goal Verification ("Execution != Goal Achievement").
Enforces real computer state inspection and prevents false-positive verifications.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, List
import re
from src.core.observation import Observation
from src.core.tool_result import VerificationStatus


@dataclass
class VerificationResult:
    verified: bool
    status: Optional[VerificationStatus] = None
    message: str = ""
    evidence: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.status is None:
            self.status = VerificationStatus.VERIFIED if self.verified else VerificationStatus.FAILED

    def to_dict(self) -> Dict[str, Any]:
        return {
            "verified": self.verified,
            "status": self.status.value if self.status else None,
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
    """
    Verifies that an application window exists, is active, and strictly
    matches the requested application name/identity (eliminating false positives).
    """

    def verify(self, expected: str, observation: Observation) -> VerificationResult:
        expected_clean = expected.lower().strip()
        data = observation.data or {}
        obs_title = str(data.get("window_title", "")).lower().strip()
        obs_process = str(data.get("process_name", "")).lower().strip()
        window_found = bool(data.get("window_found", False))

        evidence = {
            "expected_app": expected,
            "observed_window": obs_title,
            "observed_process": obs_process,
            "window_found": window_found,
            "source": observation.source,
        }

        # Check against empty or generic non-app windows
        if not obs_title or obs_title in ["desktop", "unknown", "unknown window"]:
            return VerificationResult(
                verified=False,
                status=VerificationStatus.FAILED,
                message=f"No active application window detected for '{expected}'.",
                evidence=evidence,
            )

        # Canonical application alias and process executable mappings
        alias_matches = {
            "notepad": ["notepad", "notepad.exe", "مفكرة", "المفكرة", "untitled - notepad", "بلا عنوان - المفكرة"],
            "calculator": ["calculator", "calculatorapp.exe", "calc.exe", "calculator.exe", "حاسبة", "الحاسبة", "calc"],
            "spotify": ["spotify", "spotify.exe", "سبوتيفاي", "سبوتفاي", "spotify free", "spotify premium"],
            "rider": ["rider", "rider64.exe", "jetbrains rider"],
            "code": ["visual studio code", "code.exe", "vscode", "code"],
            "visual studio": ["visual studio", "devenv.exe", "devenv"],
            "paint": ["paint", "mspaint.exe", "الرسام", "untitled - paint"],
            "chrome": ["google chrome", "chrome.exe", "chrome"],
            "edge": ["microsoft edge", "msedge.exe", "edge"],
            "discord": ["discord", "discord.exe"],
            "telegram": ["telegram", "telegram.exe"],
            "whatsapp": ["whatsapp", "whatsapp.exe"],
        }

        expected_aliases = [expected_clean]
        for app_key, aliases in alias_matches.items():
            if expected_clean == app_key or expected_clean in aliases:
                expected_aliases.extend(aliases)
                break

        # Verification: window title or process name MUST match expected app or its aliases
        title_matches = any(al in obs_title for al in expected_aliases)
        process_matches = any(al in obs_process for al in expected_aliases) if obs_process else False

        if title_matches or process_matches:
            return VerificationResult(
                verified=True,
                status=VerificationStatus.VERIFIED,
                message=f"Application window '{expected}' detected and verified (Window: '{obs_title}', Process: '{obs_process}').",
                evidence=evidence,
            )

        return VerificationResult(
            verified=False,
            status=VerificationStatus.FAILED,
            message=f"Expected app '{expected}' not found. Active window is '{obs_title}' (Process: '{obs_process}').",
            evidence=evidence,
        )


class TextVerifier(Verifier):
    """
    Verifies that expected text actually exists in the target editor/document control.
    Fails if the editor text is unavailable or does not contain the expected content.
    """

    def verify(self, expected: str, observation: Observation) -> VerificationResult:
        expected_clean = expected.strip()
        data = observation.data or {}
        observed_text = data.get("text")

        evidence = {
            "expected_text": expected_clean,
            "observed_text_sample": str(observed_text)[:100] if observed_text is not None else None,
            "source": observation.source,
        }

        if not expected_clean:
            return VerificationResult(
                verified=True,
                status=VerificationStatus.VERIFIED,
                message="Empty expected text trivially verified.",
                evidence=evidence,
            )

        # Real Observation Check: If editor value was not observed / None -> FAIL
        if observed_text is None:
            return VerificationResult(
                verified=False,
                status=VerificationStatus.FAILED,
                message=f"Target editor text could not be observed from UI for '{expected_clean}'.",
                evidence=evidence,
            )

        norm_expected = re.sub(r"\s+", " ", expected_clean).strip()
        norm_observed = re.sub(r"\s+", " ", str(observed_text)).strip()

        if norm_expected in norm_observed or norm_expected.lower() in norm_observed.lower():
            return VerificationResult(
                verified=True,
                status=VerificationStatus.VERIFIED,
                message=f"Text '{expected_clean}' verified in target control.",
                evidence=evidence,
            )

        return VerificationResult(
            verified=False,
            status=VerificationStatus.FAILED,
            message=f"Text '{expected_clean}' not found in observed editor text '{norm_observed[:60]}...'",
            evidence=evidence,
        )


class UIElementVerifier(Verifier):
    """
    Verifies that a UI element was found, interactable, and action executed.
    Does not assume goal achievement from blind action dispatch.
    """

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

        if not element_found:
            return VerificationResult(
                verified=False,
                status=VerificationStatus.FAILED,
                message=f"UI element '{expected}' was not found in active window.",
                evidence=evidence,
            )

        if not is_enabled:
            return VerificationResult(
                verified=False,
                status=VerificationStatus.FAILED,
                message=f"UI element '{expected}' is disabled and cannot be interacted with.",
                evidence=evidence,
            )

        if action_performed:
            return VerificationResult(
                verified=True,
                status=VerificationStatus.VERIFIED,
                message=f"UI element '{expected}' verified and interacted with successfully.",
                evidence=evidence,
            )

        return VerificationResult(
            verified=False,
            status=VerificationStatus.FAILED,
            message=f"UI element '{expected}' action could not be performed.",
            evidence=evidence,
        )


class SearchVerifier(Verifier):
    """
    Verifies that web navigation or in-app search reached an actual search/result state
    in the active browser or target application window.
    Eliminates false positives from generic blank browser tabs or unrelated pages.
    """

    def verify(self, expected: str, observation: Observation) -> VerificationResult:
        expected_clean = expected.lower().strip()
        data = observation.data or {}
        obs_title = str(data.get("window_title", "")).lower().strip()
        browser_active = bool(data.get("browser_active", False))
        target_in_title = bool(data.get("target_in_title", False))
        results_loaded = bool(data.get("results_loaded", False))

        evidence = {
            "expected_query": expected,
            "observed_window": obs_title,
            "browser_active": browser_active,
            "target_in_title": target_in_title,
            "results_loaded": results_loaded,
            "source": observation.source,
        }

        # 1. Reject generic blank/empty windows
        generic_non_result_titles = ["desktop", "unknown", "new tab", "about:blank", "tab", ""]
        if not obs_title or obs_title in generic_non_result_titles:
            return VerificationResult(
                verified=False,
                status=VerificationStatus.FAILED,
                message=f"No active search or browser window detected for '{expected}'.",
                evidence=evidence,
            )

        if not expected_clean:
            return VerificationResult(
                verified=True,
                status=VerificationStatus.VERIFIED,
                message="Empty expected query trivially verified.",
                evidence=evidence,
            )

        # 2. Extract significant query words
        query_words = [w for w in expected_clean.split() if len(w) >= 2]
        query_in_title = any(qw in obs_title for qw in query_words) if query_words else False

        # 3. Known platform navigation domains / titles
        platform_keywords = ["youtube", "spotify", "anghami", "soundcloud", "github", "chatgpt", "claude", "google", "search"]
        expected_has_platform = any(pk in expected_clean for pk in platform_keywords)
        title_has_platform = any(pk in obs_title for pk in platform_keywords)

        # 4. Strict verification logic: Target terms in title, or query in title, or verified results loaded with query in title
        if target_in_title or query_in_title or (expected_has_platform and title_has_platform):
            return VerificationResult(
                verified=True,
                status=VerificationStatus.VERIFIED,
                message=f"Search/Navigation for '{expected}' verified in window '{obs_title}'.",
                evidence=evidence,
            )

        if browser_active and results_loaded and query_in_title:
            return VerificationResult(
                verified=True,
                status=VerificationStatus.VERIFIED,
                message=f"Search/Navigation for '{expected}' verified in window '{obs_title}'.",
                evidence=evidence,
            )

        return VerificationResult(
            verified=False,
            status=VerificationStatus.FAILED,
            message=f"Search/Navigation for '{expected}' could not be verified in active window '{obs_title}'.",
            evidence=evidence,
        )
