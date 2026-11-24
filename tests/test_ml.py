import joblib
import pytest

from ml.build_dataset import report_features
from ml.features import FEATURE_NAMES, feature_vector
from ml.train_risk_model import MODEL_PATH


def test_feature_vector():
    features = feature_vector(58, 1, 4, 3, 2, True)
    assert len(features) == len(FEATURE_NAMES) == 6
    assert features == (58.0, 1, 4, 3, 2, 1)


def test_report_features():
    report = {"patient": {
        "patientonsetage": "18", "patientonsetageunit": "802", "patientsex": "2",
        "drug": [{"medicinalproduct": "ASPIRIN"}, {"openfda": {"generic_name": ["Warfarin"]}},
                 {"medicinalproduct": "warfarin"}],
    }}
    assert report_features(report, {"aspirin": 1, "warfarin": 2}, {(1, 2): 3}, {2}) == (1.5, 1, 3, 3, 1, 1)
    assert report_features({}, {}, {}, set()) is None


@pytest.mark.skipif(not MODEL_PATH.exists(), reason="Run the FAERS training command to produce the model")
def test_saved_model_probability():
    model = joblib.load(MODEL_PATH)["model"]
    probability = model.predict_proba([feature_vector(58, 1, 4, 3, 2, True)])[0, 1]
    assert 0 <= probability <= 1
