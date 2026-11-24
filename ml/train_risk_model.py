"""Compare two classifiers with stratified cross-validation and save the winner."""
import json
from pathlib import Path

import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import sklearn
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    ConfusionMatrixDisplay, auc, f1_score, precision_score, recall_score, roc_auc_score, roc_curve,
)
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from ml.build_dataset import DATA_PATH
from ml.features import FEATURE_NAMES, ROOT

MODEL_PATH = ROOT / "model_risk_v1.joblib"
METRICS_PATH = ROOT / "metrics.json"
FIGURES = Path(__file__).resolve().parents[1] / "reports" / "figures"
THRESHOLD = 0.5


def cross_validate(model, x, y, folds):
    scores = np.empty(len(y))
    results = []
    for train, test in folds:
        model.fit(x[train], y[train])
        prob = model.predict_proba(x[test])[:, 1]
        scores[test] = prob
        predicted = prob >= THRESHOLD
        results.append({
            "roc_auc": roc_auc_score(y[test], prob),
            "precision": precision_score(y[test], predicted, zero_division=0),
            "recall": recall_score(y[test], predicted, zero_division=0),
            "f1": f1_score(y[test], predicted, zero_division=0),
        })
    metrics = {metric: float(np.mean([row[metric] for row in results])) for metric in results[0]}
    metrics["folds"] = results
    return scores, metrics


def save_plot(fig, filename):
    fig.tight_layout()
    fig.savefig(FIGURES / filename, dpi=300)
    plt.close(fig)


def make_figures(y, scores, best, fitted):
    FIGURES.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(6.2, 4.5))
    for name, prob in scores.items():
        fpr, tpr, _ = roc_curve(y, prob)
        ax.plot(fpr, tpr, label=f"{name} (AUC {auc(fpr, tpr):.3f})")
    ax.plot([0, 1], [0, 1], color="#64748B", linestyle="--")
    ax.set(xlabel="False positive rate", ylabel="True positive rate", title="Out-of-fold ROC curves")
    ax.legend(loc="lower right")
    save_plot(fig, "risk_roc.png")

    fig, ax = plt.subplots(figsize=(5.3, 4.6))
    ConfusionMatrixDisplay.from_predictions(y, scores[best] >= THRESHOLD,
                                            display_labels=["Nonserious", "Serious"], cmap="Blues",
                                            colorbar=False, ax=ax)
    ax.set_title(f"{best} — out of fold at {THRESHOLD:.2f}")
    save_plot(fig, "risk_confusion.png")

    fig, ax = plt.subplots(figsize=(6.2, 4.2))
    if isinstance(fitted, RandomForestClassifier):
        importance = fitted.feature_importances_
        axis_label = "Mean decrease in impurity"
    else:
        importance = np.abs(fitted.named_steps["logisticregression"].coef_[0])
        axis_label = "Absolute standardized coefficient"
    order = np.argsort(importance)
    ax.barh(np.asarray(FEATURE_NAMES)[order], importance[order], color="#0E7A5C")
    ax.set(xlabel=axis_label, title=f"{best} — feature importance")
    save_plot(fig, "risk_feature_importance.png")


def main():
    data = pd.read_csv(DATA_PATH)
    y = data["y"].to_numpy(dtype=int)
    counts = data["y"].value_counts()
    if not (set(counts.index) == {0, 1} and counts.min() >= 5):
        raise SystemExit("Five-fold validation needs at least five reports in each class.")
    x = data.loc[:, list(FEATURE_NAMES)].to_numpy(dtype=float)
    models = {
        "Logistic regression": make_pipeline(
            StandardScaler(), LogisticRegression(class_weight="balanced", random_state=42, max_iter=2000)
        ),
        "Random forest": RandomForestClassifier(class_weight="balanced", random_state=42,
                                                 max_depth=10, n_jobs=-1),
    }
    split = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    folds = list(split.split(x, y))
    scores, metrics = {}, {}
    for name, model in models.items():
        scores[name], metrics[name] = cross_validate(model, x, y, folds)
        summary = " | ".join(f"{key} {metrics[name][key]:.3f}" for key in ("roc_auc", "precision", "recall", "f1"))
        print(f"{name}: {summary}")
    best = max(models, key=lambda name: metrics[name]["roc_auc"])
    fitted = models[best].fit(x, y)
    model_temp = MODEL_PATH.with_suffix(".tmp")
    joblib.dump({"model": fitted, "feature_names": FEATURE_NAMES, "sklearn_version": sklearn.__version__},
                model_temp, compress=3)
    model_temp.replace(MODEL_PATH)
    METRICS_PATH.write_text(json.dumps({
        "selected_model": best, "features": FEATURE_NAMES, "threshold": THRESHOLD,
        "cv_folds": len(folds), "rows": len(data), "class_counts": {str(k): int(v) for k, v in counts.items()},
        "sklearn_version": sklearn.__version__, "models": metrics,
    }, indent=2) + "\n", encoding="utf-8")
    make_figures(y, scores, best, fitted)
    print(f"Selected: {best} | Saved: {MODEL_PATH}")


if __name__ == "__main__":
    main()
