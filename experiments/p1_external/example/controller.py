"""Invented rate controller for testing the P1 intake, not a treatment method."""


class ExampleController:
    def reset(self):
        self.last_time = None

    def command(self, observation, announced_g):
        time_min = observation["time_min"]
        if self.last_time is not None and time_min != self.last_time + 3:
            raise ValueError("Unexpected observation clock")
        self.last_time = time_min
        # A held sample is visible but is not treated as a new measurement.
        glucose = observation["glucose_mg_dl"]
        correction = max(0.0, min(0.05, (glucose - 140.0) * 0.0002))
        if not observation["available"]:
            correction = 0.0
        return {
            "basal_u_min": 0.02 + correction,
            "bolus_u_min": min(1.8, announced_g / 36.0),
        }


def make_controller(seed):
    if type(seed) is not int:
        raise ValueError("Expected a declared integer seed")
    return ExampleController()
