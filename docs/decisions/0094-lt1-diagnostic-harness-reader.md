# 0094 — LT1 diagnostic construction and fractional trace reader

Date: 1 November 2026. Status: selected for source/fixture qualification only.

## Question and preserved boundary

Implement the next scope of [decision 0093](0093-lt1-sampled-preparation.md):
can independent direct/reference and wrapped audit-1 constructions preserve the
selected Cambridge Simulator, IdealCGM and static-pump lifecycle while withholding
unavailable observations? Keep the thirty-minute UTC development window, seed 101,
fixed Cambridge parameterization, native solver/default one-minute step and
five-minute sensor/control cadence. No historical runtime, reader, allowlist,
baseline or tolerance changes. No efficacy or cross-engine estimand is selected.

## Decision and acceptance selected before implementation

Use whole elapsed milliseconds in the new trace/plan. Convert dates and native
meal durations explicitly; refuse sub-minute durations that native setMeals would
clamp, or durations that cannot round-trip through its minute argument exactly.
Native sensor generation precedes release filtering. The wrapped path uses a
release queue and the existing sampled kernel; the direct reference implements
selection and lagged updates independently. Neither path calls the other adapter.
Only their plan validation and recording schema are shared. The native simulator
and pump remain responsible for every callback and modeled delivery. A controller's
next requested stop must be strictly after the current time, including the terminal
callback, which holds command without a new sampled transition.

The production native entry refuses before source loading: no runtime/setup/host
execution admission exists. Dependency-injected constructors are trusted fixture
code, not an arbitrary-code sandbox or a native execution permission. Register no
SDK/GUI task or new process owner. Later admitted execution must reuse the existing
owned runner/project services; full native lifecycle/store migration is not claimed.

The new trusted data reader binds the plan bytes, current implementation identity
and an externally supplied expected packet hash. It never imports archived code.
It validates the declared native outer grid, raw IdealCGM sample cadence, causal
sample release, one sampled transition per tick, announced versus actual meals,
lagged command order, finite signal/state fields and explicit terminal status.
Integrate modeled U/h over pairs of present valid native endpoints only. Report
the integral as an exact rational of the recorded decimal rates and integer
durations; this avoids ambient Decimal-context rounding. It does not establish
that the physiological solution or pump output is correct. Native reference/parity
and admitted source/runtime receipts remain independent requirements.

Preselect controls: the known 1.2/1.2/1.2/1.8 policy prefix; delayed sample measured at minute 10
released at 15 with minute 15 masked; newest measured sample resisting a late older
release; the 2.5-minute meal with 1.5-minute duration; strict future stop at 30;
command versus delivery; zero/one-row and shortened failed prefixes; complete
rows retaining failure; simultaneous primary/diagnostic errors; malformed/truncated
JSON, unknown fields, changed source/plan/packet identities and a relocated no-site
read. Alter two identical wrong transcripts and require the independent reader to
reject them. Preserve failures and unavailable native evidence explicitly.

Byte identity is not history authentication: the expected hash must come from a
trusted external inventory/project store, not the producer being inspected. This
reader handles one attempt and does not replace the planned-slot/all-attempt
ledger. Invented and declared-unadmitted-native records never supply execution
authorization or verified native parity. Keep full future native records private.
