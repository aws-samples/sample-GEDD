"""Statistics for GEDD: significance, label quality, calibration, PPI and overoptimization.

Pure Python (standard library only) so it can be reused by experiment scripts without extra
dependencies.
"""

from grounded_evals.stats.agreement import (
    brier_score,
    expected_calibration_error,
    krippendorff_alpha_nominal,
    pairwise_accuracy,
)
from grounded_evals.stats.overoptimization import (
    BonPoint,
    best_of_n_curve,
    kl_best_of_n,
    overoptimization_gap,
)
from grounded_evals.stats.ppi import MeanEstimate, classical_mean, ppi_mean
from grounded_evals.stats.significance import (
    BootstrapResult,
    Comparison,
    McNemarResult,
    cluster_bootstrap,
    cluster_robust_se,
    compare,
    holm,
    mcnemar_exact,
    minimum_detectable_effect,
)

__all__ = [
    "BonPoint",
    "BootstrapResult",
    "Comparison",
    "McNemarResult",
    "MeanEstimate",
    "best_of_n_curve",
    "brier_score",
    "classical_mean",
    "cluster_bootstrap",
    "cluster_robust_se",
    "compare",
    "expected_calibration_error",
    "holm",
    "kl_best_of_n",
    "krippendorff_alpha_nominal",
    "mcnemar_exact",
    "minimum_detectable_effect",
    "overoptimization_gap",
    "pairwise_accuracy",
    "ppi_mean",
]
