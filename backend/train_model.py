"""
train_model.py - STEPS 2 & 3 of the implementation guide:
  "Extract text features" and "Train a classification model".

Approach (as suggested in the problem statement):  TF-IDF  +  Logistic Regression / SVM
  * Word TF-IDF (1-2 grams)  -> captures keywords like "invoice no", "date of birth", "closing balance"
  * Char TF-IDF (3-5 grams)  -> robust to OCR spelling mistakes ("inv0ice", "rece1pt")
  * Three classifiers are compared on an 80/20 stratified split; the best one (macro F1) is
    re-trained on all data and saved to models/document_classifier.joblib together with metrics.

Run:  python train_model.py
"""
import csv
import json
import os
import time
from datetime import datetime

import joblib
import numpy as np
from sklearn.calibration import CalibratedClassifierCV
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import FeatureUnion, Pipeline
from sklearn.svm import LinearSVC

import config
from classifier import DocumentClassifier, preprocess


def load_dataset(extra_rows=None):
    """Read the labelled corpus. extra_rows = [(label, text), ...] from human corrections."""
    texts, labels = [], []
    with open(config.DATASET_CSV, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            texts.append(row["text"])
            labels.append(row["label"])
    for label, text in extra_rows or []:
        texts.append(text)
        labels.append(label)
    return [preprocess(t) for t in texts], np.array(labels)


def build_pipeline(classifier):
    features = FeatureUnion([
        ("word", TfidfVectorizer(ngram_range=(1, 2), min_df=2, max_features=20000, sublinear_tf=True,
                                 stop_words="english", token_pattern=r"(?u)\b[a-z][a-z]+\b")),
        ("char", TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), min_df=2, max_features=30000,
                                 sublinear_tf=True)),
    ])
    return Pipeline([("features", features), ("clf", classifier)])


def candidate_models():
    return {
        "Logistic Regression": LogisticRegression(C=10, max_iter=3000),
        "Linear SVM (calibrated)": CalibratedClassifierCV(LinearSVC(C=0.5, dual="auto"), cv=3),
        "Multinomial Naive Bayes": MultinomialNB(alpha=0.05),
    }


def top_keywords(pipeline, labels, n=10):
    """Most important word features per class (what the model 'looks for')."""
    clf = pipeline.named_steps["clf"]
    weights_all = DocumentClassifier._class_weights(clf)    # works for LR, calibrated SVM and NB
    if weights_all is None:
        return {}
    names = pipeline.named_steps["features"].get_feature_names_out()
    word_idx = np.array([i for i, nm in enumerate(names) if nm.startswith("word__")])
    out = {}
    for ci, label in enumerate(clf.classes_):
        weights = weights_all[ci][word_idx]
        best = word_idx[np.argsort(weights)[::-1][:n]]
        out[label] = [names[i].replace("word__", "") for i in best]
    return out


def train(extra_rows=None, verbose=True):
    log = print if verbose else (lambda *a, **k: None)
    start = time.time()
    texts, labels = load_dataset(extra_rows)
    classes = sorted(set(labels))
    log(f"Loaded {len(texts)} documents, {len(classes)} classes")

    X_train, X_test, y_train, y_test = train_test_split(texts, labels, test_size=0.2, stratify=labels, random_state=7)

    # ---- compare candidate models on the held-out test set ----
    comparison, best_name, best_f1, best_pred = [], None, -1, None
    for name, clf in candidate_models().items():
        pipe = build_pipeline(clf)
        t0 = time.time()
        pipe.fit(X_train, y_train)
        train_s = time.time() - t0
        t0 = time.time()
        pred = pipe.predict(X_test)
        pred_ms = (time.time() - t0) * 1000 / len(X_test)
        acc, f1 = accuracy_score(y_test, pred), f1_score(y_test, pred, average="macro")
        comparison.append({"model": name, "accuracy": round(acc, 4), "macro_f1": round(f1, 4),
                           "train_time_s": round(train_s, 2), "predict_ms_per_doc": round(pred_ms, 3)})
        log(f"  {name:28s} accuracy={acc:.4f}  macroF1={f1:.4f}  train={train_s:.1f}s")
        if f1 > best_f1 + 1e-9:
            best_name, best_f1, best_pred = name, f1, pred

    log(f"Selected model: {best_name}")
    report = classification_report(y_test, best_pred, labels=classes, output_dict=True, zero_division=0)
    cm = confusion_matrix(y_test, best_pred, labels=classes)

    mistakes = [{"true": t, "predicted": p, "snippet": x[:160]}
                for x, t, p in zip(X_test, y_test, best_pred) if t != p][:10]

    # ---- 5-fold cross validation of the chosen model on all data ----
    cv = cross_val_score(build_pipeline(candidate_models()[best_name]), texts, labels,
                         cv=StratifiedKFold(5, shuffle=True, random_state=7), scoring="accuracy", n_jobs=1)
    log(f"5-fold CV accuracy: {cv.mean():.4f} +/- {cv.std():.4f}")

    # ---- final model: re-train on 100% of the data and save ----
    final = build_pipeline(candidate_models()[best_name])
    final.fit(texts, labels)

    previous = {}
    if os.path.exists(config.METRICS_PATH):
        with open(config.METRICS_PATH, encoding="utf-8") as f:
            previous = json.load(f)
    version = previous.get("version", 0) + 1

    metrics = {
        "version": version,
        "trained_at": datetime.now().isoformat(timespec="seconds"),
        "model_name": best_name,
        "features": "Word TF-IDF (1-2 grams) + Char TF-IDF (3-5 grams)",
        "feature_count": len(final.named_steps["features"].get_feature_names_out()),
        "classes": classes,
        "dataset": {
            "total": len(texts),
            "train_size": len(X_train),
            "test_size": len(X_test),
            "feedback_samples": len(extra_rows or []),
            "per_class": {c: int((labels == c).sum()) for c in classes},
        },
        "test_accuracy": round(accuracy_score(y_test, best_pred), 4),
        "test_macro_f1": round(best_f1, 4),
        "cv_accuracy_mean": round(float(cv.mean()), 4),
        "cv_accuracy_std": round(float(cv.std()), 4),
        "per_class": {c: {k: round(v, 4) for k, v in report[c].items()} for c in classes},
        "confusion_matrix": cm.tolist(),
        "model_comparison": comparison,
        "top_keywords": top_keywords(final, classes),
        "misclassified_examples": mistakes,
        "training_time_s": round(time.time() - start, 1),
    }

    os.makedirs(config.MODEL_DIR, exist_ok=True)
    joblib.dump({"pipeline": final, "classes": classes, "version": version, "model_name": best_name}, config.MODEL_PATH)
    with open(config.METRICS_PATH, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)
    log(f"Saved model v{version} -> {config.MODEL_PATH}  ({metrics['training_time_s']}s)")
    return metrics


if __name__ == "__main__":
    train()
