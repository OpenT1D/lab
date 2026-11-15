"""Fixed scripted observations and delivery: explicitly not a physiological model."""

from .contract import STEP


class ScriptedEngine:
    """No external factory, plugin, resource filename, random source or native import."""

    def __init__(self, config):
        self.config = config
        self.index = 0
        self.calls = {
            "constructed": 1,
            "reset": 0,
            "step": 0,
            "close": 0,
            "sampled_observations": 0,
        }
        self.actions = []

    def _sample(self):
        self.calls["sampled_observations"] += 1
        return {
            "measured_ms": self.index * STEP,
            "glucose_mg_dl": self.config["samples"][self.index],
        }

    def reset(self):
        self.calls["reset"] += 1
        self.index = 0
        if self.config["fault"] == "reset-error":
            raise RuntimeError("scripted-reset-error")
        return self._sample()

    def step(self, basal_u_min, bolus_u_min):
        self.calls["step"] += 1
        self.actions.append({"basal_u_min": basal_u_min, "bolus_u_min": bolus_u_min})
        if self.index == 2:
            if self.config["fault"] == "after-two":
                raise RuntimeError("scripted-after-two")
            if self.config["fault"] == "cancel-after-two":
                raise InterruptedError("scripted-cancel-after-two")
        rate = self.config["delivered_rates_u_min"][self.index]
        self.index += 1
        return {
            "observation": self._sample(),
            "delivered_rate_u_min": rate,
            "done": self.config["fault"] == "early-done" and self.index == 2,
            "diagnostic_tail": (
                {"time_ms": self.index * STEP, "error": "scripted-nonfinite-terminal-command"}
                if self.index == 10 and self.config["fault"] == "terminal-tail"
                else None
            ),
        }

    def close(self):
        self.calls["close"] += 1
        if self.config["close_error"]:
            raise RuntimeError("scripted-close-error")
