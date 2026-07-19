"""Guarded execution sandbox — actually RUN a submission, not just pattern-match it.

Upgrades behavioral grading from static checks to a dynamic signal: the
submission is concatenated with the exercise's hidden test harness and run in a
subprocess with a hard wall-clock timeout, CPU/memory rlimits (POSIX), isolated
interpreter mode, a temp cwd, and a stripped environment. Success is the harness
printing SANDBOX_PASS.

Executing user code is inherently risky, so this is OFF by default
(`settings.enable_sandbox`) and only ever runs an exercise's own test harness.
It is a lightweight guard, not a hostile-multi-tenant jail — network isn't hard
-blocked; the timeout + rlimits bound a runaway or accidental loop.
"""

from __future__ import annotations

import asyncio
import os
import sys
import tempfile

_PASS = "SANDBOX_PASS"


def _limit_resources(cpu_seconds: int, mem_bytes: int):  # pragma: no cover - POSIX preexec
    try:
        import resource

        resource.setrlimit(resource.RLIMIT_CPU, (cpu_seconds, cpu_seconds))
        resource.setrlimit(resource.RLIMIT_AS, (mem_bytes, mem_bytes))
    except Exception:
        pass


async def run_submission(
    submission: str, tests: str, *, timeout: float = 5.0, mem_mb: int = 256
) -> dict:
    """Run `submission` + `tests` in a subprocess. Returns
    {ran, passed, stdout, stderr, error}."""
    script = f"{submission}\n\n# --- hidden test harness ---\n{tests}\n"
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "candidate.py")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(script)

        env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "PYTHONDONTWRITEBYTECODE": "1"}
        preexec = None
        if os.name == "posix":
            preexec = lambda: _limit_resources(int(timeout) + 1, mem_mb * 1024 * 1024)  # noqa: E731

        try:
            proc = await asyncio.create_subprocess_exec(
                sys.executable,
                "-I",  # isolated: ignore env/user site, no implicit cwd on path
                path,
                cwd=tmp,
                env=env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                preexec_fn=preexec,
            )
        except Exception as e:  # noqa: BLE001
            return {"ran": False, "passed": False, "stdout": "", "stderr": "", "error": str(e)}

        try:
            out, err = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            return {"ran": True, "passed": False, "stdout": "", "stderr": "", "error": "timeout"}

        stdout = out.decode("utf-8", "replace")
        stderr = err.decode("utf-8", "replace")
        passed = proc.returncode == 0 and _PASS in stdout
        return {
            "ran": True,
            "passed": passed,
            "stdout": stdout[-2000:],
            "stderr": stderr[-2000:],
            "error": "" if passed else (stderr[-400:] or "tests did not pass"),
        }
