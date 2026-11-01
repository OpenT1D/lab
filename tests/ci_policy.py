"""Explicit job rosters for the public boundary and retained historical CI."""

PUBLIC_JOBS = frozenset(
    {
        "repository-checks",
        "root-tests",
        "public-smoke",
        "browser",
        "browser-apps",
        "dependency-review",
        "public-checks",
    }
)
PUBLICATION_JOBS = frozenset({"pages-deploy"})
NATIVE_JOBS = frozenset(
    {
        "beta-cell-feedback",
        "configurable-study-tools",
        "maintained-m4-study",
        "c1-patched-checkpoint-boundary",
        "beta-cell-joint-identifiability",
        "cpeptide-volume-sensitivity",
        "beta-cell-likelihood-profiles",
        "simglucose-reference",
        "lt1-reference",
        "m1-demonstration",
        "m2-cambridge",
        "internal-verification",
        "internal-robustness",
        "m3-forecast",
        "lit002-absorption",
    }
)
