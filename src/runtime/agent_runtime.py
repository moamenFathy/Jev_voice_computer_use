"""
Agent Runtime for JEV Reliability Architecture (Phase 1).
Executes actions within a bounded retry loop with explicit observations, concrete verifications,
and reliability metrics.
"""

import time
from typing import Any, Callable, Dict, Optional
from src.core.tool_result import ToolResult, FailureReason
from src.core.observation import Observation
from src.verification.verifier import Verifier, VerificationResult


class AgentRuntime:
    """
    Orchestrates execution of atomic actions with observation, verification,
    and bounded retries.
    """

    def __init__(self, max_retries: int = 2, retry_delay: float = 0.5):
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        # Reliability metrics
        self.total_goals = 0
        self.successful_goals = 0
        self.total_steps = 0
        self.successful_steps = 0
        self.retries_attempted = 0
        self.verification_failures = 0
        self.execution_failures = 0

    def execute_step(
        self,
        action: str,
        target: str,
        execute_fn: Callable[[], ToolResult],
        observer_fn: Optional[Callable[[], Observation]] = None,
        verifier: Optional[Verifier] = None,
        expected: str = "",
        step_idx: int = 1,
        total_steps: int = 1,
        on_step_callback: Optional[Callable[[str, str], None]] = None,
    ) -> ToolResult:
        """
        Executes a single step with the reliability cycle:
        Execute -> Observe -> Verify -> Success / Retry / Failure
        """
        self.total_steps += 1
        last_result: Optional[ToolResult] = None

        for attempt in range(1, self.max_retries + 2):
            step_header = f"[STEP {step_idx}/{total_steps}] Action: {action} | Target: '{target}' | Attempt: {attempt}"
            print(f"\n{step_header}")

            if on_step_callback and attempt == 1:
                on_step_callback("action", f"⚡ {action}: '{target}'...")

            # 1. Execution
            try:
                result = execute_fn()
            except Exception as e:
                result = ToolResult(
                    success=False,
                    tool=action,
                    error=f"Exception during execution: {e}",
                    failure_reason=FailureReason.EXECUTION_ERROR,
                    retryable=False,
                )

            last_result = result
            print(f"[EXECUTION] success={str(result.success).lower()}")

            # 2. If Execution Failed
            if not result.success:
                self.execution_failures += 1
                err_msg = result.error or result.message or "Execution failed"
                print(f"[ERROR] {err_msg}")

                if result.retryable and attempt <= self.max_retries:
                    self.retries_attempted += 1
                    print(f"[RETRY] retryable=true. Waiting {self.retry_delay}s before attempt {attempt + 1}...")
                    if on_step_callback:
                        on_step_callback("status", f"⏳ Retrying {action} (attempt {attempt + 1})...")
                    time.sleep(self.retry_delay)
                    continue
                else:
                    print("[RESULT] FAILED")
                    if on_step_callback:
                        on_step_callback("error", f"❌ {action} failed: {err_msg}")
                    return result

            # 3. If Execution Succeeded -> Observation & Verification
            if verifier and observer_fn:
                try:
                    observation = observer_fn()
                except Exception as e:
                    observation = Observation(
                        source="system",
                        description=f"Observation error: {e}",
                        data={},
                    )

                print(f"[OBSERVATION] source={observation.source} | {observation.description}")

                verification_target = expected if expected else target
                try:
                    ver_result: VerificationResult = verifier.verify(verification_target, observation)
                except Exception as e:
                    ver_result = VerificationResult(
                        verified=False,
                        message=f"Verifier exception: {e}",
                    )

                print(f"[VERIFICATION] verified={str(ver_result.verified).lower()} | {ver_result.message}")

                if ver_result.verified:
                    self.successful_steps += 1
                    print("[RESULT] SUCCESS")
                    final_tool_res = ToolResult(
                        success=True,
                        tool=action,
                        message=ver_result.message or result.message,
                        data=observation.data,
                        evidence=ver_result.evidence,
                    )
                    if on_step_callback:
                        on_step_callback("finished", final_tool_res.message)
                    return final_tool_res
                else:
                    self.verification_failures += 1
                    if attempt <= self.max_retries:
                        self.retries_attempted += 1
                        print(f"[RETRY] Verification failed, retryable=true. Waiting {self.retry_delay}s...")
                        if on_step_callback:
                            on_step_callback("status", f"⏳ Re-verifying {action} (attempt {attempt + 1})...")
                        time.sleep(self.retry_delay)
                        continue
                    else:
                        print("[RESULT] FAILED (Verification)")
                        fail_res = ToolResult(
                            success=False,
                            tool=action,
                            error=f"Verification failed: {ver_result.message}",
                            failure_reason=FailureReason.VERIFICATION_FAILED,
                            retryable=False,
                            evidence=ver_result.evidence,
                        )
                        if on_step_callback:
                            on_step_callback("error", f"❌ Verification failed: {ver_result.message}")
                        return fail_res

            # No verifier needed, pure tool success
            self.successful_steps += 1
            print("[RESULT] SUCCESS")
            if on_step_callback:
                on_step_callback("finished", result.message)
            return result

        print("[RESULT] FAILED (Retries exhausted)")
        return last_result or ToolResult(
            success=False,
            tool=action,
            error="Exhausted all retries without success.",
            failure_reason=FailureReason.TIMEOUT,
            retryable=False,
        )

    def record_goal_outcome(self, success: bool):
        self.total_goals += 1
        if success:
            self.successful_goals += 1

    def get_metrics(self) -> Dict[str, Any]:
        """Returns structured reliability metrics."""
        goal_rate = (self.successful_goals / self.total_goals * 100.0) if self.total_goals > 0 else 0.0
        step_rate = (self.successful_steps / self.total_steps * 100.0) if self.total_steps > 0 else 0.0
        return {
            "total_goals": self.total_goals,
            "successful_goals": self.successful_goals,
            "goal_success_rate_pct": round(goal_rate, 2),
            "total_steps": self.total_steps,
            "successful_steps": self.successful_steps,
            "step_success_rate_pct": round(step_rate, 2),
            "retries_attempted": self.retries_attempted,
            "verification_failures": self.verification_failures,
            "execution_failures": self.execution_failures,
        }
