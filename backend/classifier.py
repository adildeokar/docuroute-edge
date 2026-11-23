"""
classifier.py - STEP 4/5: the trained model running as a local (edge) inference engine.

Loads models/document_classifier.joblib once and answers:
  * which category?          (predicted label)
  * how sure?                (probability of every class)
  * why?                     (words that pushed the decision - explainability)
  * is this even a document? (share of words the model knows - out-of-domain check)
"""
import os
import re
import threading

import joblib
import numpy as np

import config


def preprocess(text):
    """Same cleaning for training and prediction: lowercase, mask digits, squeeze spaces."""
    text = text.lower()
    text = re.sub(r"\d", "0", text)          # numbers (amounts, IDs) vary randomly -> mask them
    return re.sub(r"\s+", " ", text).strip()


class DocumentClassifier:
    def __init__(self, model_path=config.MODEL_PATH):
        self.model_path = model_path
        self.lock = threading.Lock()
        self.pipeline = None
        self.version = None
        self.model_name = None
        self.load()

    # ------------------------------------------------------------------
    def load(self):
        if not os.path.exists(self.model_path):
            raise FileNotFoundError("Model not found. Run: python generate_dataset.py && python kaggle_dataset.py && python train_model.py")
        bundle = joblib.load(self.model_path)
        with self.lock:
            self.pipeline = bundle["pipeline"]
            self.version = bundle["version"]
            self.model_name = bundle["model_name"]
            features = self.pipeline.named_steps["features"]
            self.feature_names = features.get_feature_names_out()
            self.word_vocab = features.transformer_list[0][1].vocabulary_
            self.class_weights = self._class_weights(self.pipeline.named_steps["clf"])

    @staticmethod
    def _class_weights(clf):
        """Per-class feature weights used for explanations (works for LR, calibrated SVM and NB)."""
        if hasattr(clf, "coef_"):
            return clf.coef_
        if hasattr(clf, "calibrated_classifiers_"):
            return np.mean([c.estimator.coef_ for c in clf.calibrated_classifiers_], axis=0)
        if hasattr(clf, "feature_log_prob_"):
            return clf.feature_log_prob_ - clf.feature_log_prob_.mean(axis=0)
        return None

    # ------------------------------------------------------------------
    def known_word_ratio(self, clean):
        words = re.findall(r"[a-z][a-z]+", clean)
        if not words:
            return 0.0
        return sum(1 for w in words if w in self.word_vocab) / len(words)

    def predict(self, text):
        clean = preprocess(text)
        with self.lock:
            features = self.pipeline.named_steps["features"].transform([clean])
            clf = self.pipeline.named_steps["clf"]
            probs = clf.predict_proba(features)[0]
            classes = list(clf.classes_)
            best = int(np.argmax(probs))

            # Explainability: contribution of each word = tf-idf value x class weight
            top_terms = []
            if self.class_weights is not None:
                row = features.tocsr()
                contrib = row.multiply(self.class_weights[best]).toarray()[0]
                order = np.argsort(contrib)[::-1]
                for idx in order:
                    if contrib[idx] <= 0 or len(top_terms) >= 8:
                        break
                    name = self.feature_names[idx]
                    if name.startswith("word__"):
                        top_terms.append({"term": name[6:], "weight": round(float(contrib[idx]), 4)})

        ranking = sorted(zip(classes, probs), key=lambda x: x[1], reverse=True)
        return {
            "category": classes[best],
            "confidence": round(float(probs[best]), 4),
            "probabilities": [{"category": c, "probability": round(float(p), 4)} for c, p in ranking],
            "top_terms": top_terms,
            "known_word_ratio": round(self.known_word_ratio(clean), 3),
            "model_version": self.version,
        }
