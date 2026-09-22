"""
Agent Runtime for JEV Reliability Architecture (Phase 1).
Executes actions within a bounded retry loop with real observations, concrete verifications,
and explicit verification status (VERIFIED vs UNAVAILABLE vs FAILED).
"""

import time
from typing import Any, Callable, Dict, Optional
from src.core.tool_result import ToolResult, FailureReason, VerificationStatus
from src.core.observation import Observation
from src.verification.verifier import Verifier, VerificationResult
from src.core.telemetry import telemetry


class AgentRuntime:
    """
    Orchestrates execution of atomic actions with real observation, verification,
    telemetry latency benchmarking, and bounded retries.
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
        reobserve_fn: Optional[Callable[[], None]] = None,
        step_idx: int = 1,
        total_steps: int = 1,
        is_idempotent: bool = True,
        decision_path: str = "fast_path",
        t_decision_ms: float = 0.0,
        on_step_callback: Optional[Callable[[str, str], None]] = None,
    ) -> ToolResult:
        """
        Executes a single step with the strict reliability cycle:
        Execute -> Observe -> Verify -> Success / Retry / Failure
        Measures stage-by-stage latencies and records structured telemetry.
        """
        t_start = time.time()
        self.total_steps += 1
        last_result: Optional[ToolResult] = None
        execution_completed = False
        t_exec_ms = 0.0
        t_obs_ms = 0.0
        t_ver_ms = 0.0

        for attempt in range(1, self.max_retries + 2):
            step_header = f"[STEP {step_idx}/{total_steps}]\nAction: {action}\nTarget: '{target}'\nAttempt: {attempt}"
            print(f"\n{step_header}")

            if on_step_callback and attempt == 1:
                on_step_callback("action", f"⚡ {action}: '{target}'...")

            # 1. Execution
            t0 = time.time()
            if attempt == 1 or is_idempotent or not execution_completed:
                try:
                    result = execute_fn()
                    execution_completed = bool(result.execution_success and result.success)
                except Exception as e:
                    result = ToolResult(
                        success=False,
                        tool=action,
                        error=f"Exception during execution: {e}",
                        failure_reason=FailureReason.EXECUTION_ERROR,
                        execution_success=False,
                        verification_status=VerificationStatus.FAILED,
                        retryable=False,
                    )
                    execution_completed = False
            else:
                print(f"[EXECUTION]\nAction '{action}' is non-idempotent and was already dispatched. Re-observing environment.")
                result = last_result or ToolResult(success=True, tool=action, execution_success=True)

            t_exec_ms += (time.time() - t0) * 1000
            last_result = result
            print(f"[EXECUTION]\nsuccess={str(result.execution_success).lower()}")

            # 2. If Execution Failed
            if not result.execution_success or not result.success:
                self.execution_failures += 1
                err_msg = result.error or result.message or "Execution failed"
                print(f"[ERROR]\n{err_msg}")

                if result.retryable and attempt <= self.max_retries:
                    self.retries_attempted += 1
                    print(f"[RETRY]\nretryable=true. Waiting {self.retry_delay}s before attempt {attempt + 1}...")
                    if on_step_callback:
                        on_step_callback("status", f"⏳ Retrying {action} (attempt {attempt + 1})...")
                    time.sleep(self.retry_delay)
                    if reobserve_fn:
                        try:
                            reobserve_fn()
                        except Exception as reobs_err:
                            print(f"[DEBUG] Reobserve error: {reobs_err}")
                    continue
                else:
                    print("[RESULT]\nFAILED")
                    if on_step_callback:
                        on_step_callback("error", f"❌ {action} failed: {err_msg}")
                    t_total_ms = (time.time() - t_start) * 1000
                    telemetry.record_step(
                        goal=target, action=action, target=target, decision_path=decision_path,
                        t_decision_ms=t_decision_ms, t_execution_ms=t_exec_ms, t_total_ms=t_total_ms, success=False
                    )
                    return result

            # 3. If Execution Succeeded -> Real Observation & Verification
            if verifier and observer_fn:
                t_obs_start = time.time()
                try:
                    observation = observer_fn()
                except Exception as e:
                    print(f"[DEBUG] Observation error: {e}")
                    observation = Observation(source="system", description=f"Observation error: {e}", data={})
                t_obs_ms += (time.time() - t_obs_start) * 1000
                print(f"[OBSERVATION]\nsource={observation.source}\n{observation.description}")

                verification_target = expected if expected else target
                t_ver_start = time.time()
                try:
                    ver_result: VerificationResult = verifier.verify(verification_target, observation)
                except Exception as e:
                    ver_result = VerificationResult(
                        verified=False, status=VerificationStatus.FAILED, message=f"Verifier exception: {e}"
                    )
                t_ver_ms += (time.time() - t_ver_start) * 1000
                print(f"[VERIFICATION]\nverified={str(ver_result.verified).lower()}\nstatus={ver_result.status.value if ver_result.status else 'unknown'}")

                # Status: VERIFIED
                if ver_result.verified and ver_result.status == VerificationStatus.VERIFIED:
                    self.successful_steps += 1
                    print("[RESULT]\nSUCCESS")
                    final_tool_res = ToolResult(
                        success=True, tool=action, message=ver_result.message or result.message,
                        data=observation.data, execution_success=True, verification_status=VerificationStatus.VERIFIED,
                        evidence=ver_result.evidence,
                    )
                    if on_step_callback:
                        on_step_callback("finished", final_tool_res.message)
                    t_total_ms = (time.time() - t_start) * 1000
                    telemetry.record_step(
                        goal=target, action=action, target=target, decision_path=decision_path,
                        t_decision_ms=t_decision_ms, t_execution_ms=t_exec_ms, t_observation_ms=t_obs_ms,
                        t_verification_ms=t_ver_ms, t_total_ms=t_total_ms, success=True
                    )
                    return final_tool_res

                # Status: UNAVAILABLE
                elif ver_result.status == VerificationStatus.UNAVAILABLE:
                    self.successful_steps += 1
                    print(f"[VERIFICATION]\nstatus=unavailable ({ver_result.message or 'Verification unavailable'})")
                    print("[RESULT]\nSUCCESS (Executed, verification unavailable)")
                    final_tool_res = ToolResult(
                        success=True, tool=action, message=ver_result.message or result.message,
                        data=observation.data, execution_success=True, verification_status=VerificationStatus.UNAVAILABLE,
                        evidence=ver_result.evidence,
                    )
                    if on_step_callback:
                        on_step_callback("finished", final_tool_res.message)
                    t_total_ms = (time.time() - t_start) * 1000
                    telemetry.record_step(
                        goal=target, action=action, target=target, decision_path=decision_path,
                        t_decision_ms=t_decision_ms, t_execution_ms=t_exec_ms, t_observation_ms=t_obs_ms,
                        t_verification_ms=t_ver_ms, t_total_ms=t_total_ms, success=True
                    )
                    return final_tool_res

                # Status: FAILED
                else:
                    self.verification_failures += 1
                    if attempt <= self.max_retries:
                        self.retries_attempted += 1
                        print(f"[RETRY]\nVerification failed, retryable=true. Waiting {self.retry_delay}s before attempt {attempt + 1}...")
                        if on_step_callback:
                            on_step_callback("status", f"⏳ Re-verifying {action} (attempt {attempt + 1})...")
                        time.sleep(self.retry_delay)
                        if reobserve_fn:
                            try:
                                reobserve_fn()
                            except Exception as reobs_err:
                                print(f"[DEBUG] Reobserve error: {reobs_err}")
                        continue
                    else:
                        print("[RESULT]\nFAILED (Verification)")
                        fail_res = ToolResult(
                            success=False, tool=action, error=f"Verification failed: {ver_result.message}",
                            failure_reason=FailureReason.VERIFICATION_FAILED, execution_success=True,
                            verification_status=VerificationStatus.FAILED, retryable=False, evidence=ver_result.evidence,
                        )
                        if on_step_callback:
                            on_step_callback("error", f"❌ Verification failed: {ver_result.message}")
                        t_total_ms = (time.time() - t_start) * 1000
                        telemetry.record_step(
                            goal=target, action=action, target=target, decision_path=decision_path,
                            t_decision_ms=t_decision_ms, t_execution_ms=t_exec_ms, t_observation_ms=t_obs_ms,
                            t_verification_ms=t_ver_ms, t_total_ms=t_total_ms, success=False
                        )
                        return fail_res

            # No verifier configured
            self.successful_steps += 1
            result.verification_status = VerificationStatus.UNAVAILABLE
            print(f"[VERIFICATION]\nstatus=unavailable (No verifier configured)")
            print("[RESULT]\nSUCCESS (Executed)")
            if on_step_callback:
                on_step_callback("finished", result.message)
            t_total_ms = (time.time() - t_start) * 1000
            telemetry.record_step(
                goal=target, action=action, target=target, decision_path=decision_path,
                t_decision_ms=t_decision_ms, t_execution_ms=t_exec_ms, t_total_ms=t_total_ms, success=True
            )
            return result

        print("[RESULT]\nFAILED (Retries exhausted)")
        t_total_ms = (time.time() - t_start) * 1000
        telemetry.record_step(
            goal=target, action=action, target=target, decision_path=decision_path,
            t_decision_ms=t_decision_ms, t_execution_ms=t_exec_ms, t_total_ms=t_total_ms, success=False
        )
        return last_result or ToolResult(
            success=False,
            tool=action,
            error="Exhausted all retries without success.",
            failure_reason=FailureReason.TIMEOUT,
            execution_success=False,
            verification_status=VerificationStatus.FAILED,
            retryable=False,
        )

    def record_goal_outcome(self, success: bool):
        self.total_goals += 1
        if success:
            self.successful_goals += 1

    def get_metrics(self) -> Dict[str, Any]:
        """Returns structured reliability and telemetry metrics."""
        goal_rate = (self.successful_goals / self.total_goals * 100.0) if self.total_goals > 0 else 0.0
        step_rate = (self.successful_steps / self.total_steps * 100.0) if self.total_steps > 0 else 0.0
        base_metrics = {
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
        base_metrics["telemetry"] = telemetry.get_summary()
        return base_metrics
