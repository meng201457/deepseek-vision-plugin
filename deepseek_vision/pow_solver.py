from .models import PowChallenge, PowSolution


class PowSolver:
    """Wrapper around deepseek-pow WASM solver"""

    def __init__(self):
        self._solver = None

    def _get_solver(self):
        if self._solver is None:
            from deepseek_pow import registry
            self._solver = registry.get("DeepSeekHashV1")
        return self._solver

    def solve(self, challenge: PowChallenge) -> PowSolution:
        from deepseek_pow.models import Challenge as DsChallenge

        ds_challenge = DsChallenge(
            algorithm=challenge.algorithm,
            challenge=challenge.challenge,
            salt=challenge.salt,
            difficulty=challenge.difficulty,
            expire_at=challenge.expire_at,
            signature=challenge.signature,
        )

        solver = self._get_solver()
        ds_solution = solver.solve(ds_challenge)

        return PowSolution(
            algorithm=ds_solution.algorithm,
            challenge=ds_solution.challenge,
            salt=ds_solution.salt,
            answer=ds_solution.answer,
            signature=ds_solution.signature,
            target_path=challenge.target_path,
        )
