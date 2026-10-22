"""Automatic data audit: safety, leakage, shortcut features and balance.

Runs after every build (build_dataset.py calls it) or on its own:
    python data/audit.py

FAIL stops the build. WARN is printed for a human to judge.
Checks that need judgment (wrong labels, language, stereotypes) are left to
manual review.
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedGroupKFold

DATA = Path(__file__).resolve().parent
SEED = 42  # same split as the notebook

MAX_FEATURE_ACC = 0.65   # one surface feature alone must not beat this
MAX_NEAR_DUP = 0.60      # char 3-gram Jaccard between different templates
MAX_TRICKY_SIM = 0.40    # tricky row vs any training row
MAX_REGISTER_GAP = 0.15  # MSA share difference between ham and spam (Arabic)
PURE_TOKEN_MIN = 8       # a token in this many rows of one label and none of the other

LINK_RE = re.compile(r"(?:https?://)?[\w.-]+\.[a-z]{2,}(?:/\S*)?", re.I)
PHONE_RE = re.compile(r"(?:\+\d{2,3}\s*)?X{4}\s*X{4,6}")
REAL_PHONE_RE = re.compile(r"\d[\d\s-]{6,}\d")
CURRENCY_RE = re.compile(r"ر\.ع|ريال|OMR", re.I)
EMOJI_RE = re.compile("[\U0001F300-\U0001FAFF☀-➿]")
TRUSTED = {"bank.example", "pay.example", "shop.example", "store.example", "gov.example", "photos.example"}
REAL_NAMES = re.compile(
    r"bank ?muscat|omantel|ooredoo|vodafone|whats ?app|telegram|instagram|linkedin|facebook|"
    r"iphone|samsung|apple|amazon|aramex|dhl|paypal|google|netflix|huawei|talabat|lulu|"
    r"بنك مسقط|عمانتل|أوريدو|واتس|تيليجرام|تلغرام|آيفون|ايفون|سامسونج|أمازون|أرامكس|مول عمان|"
    r"شرطة عمان|royal oman police",
    re.I,
)


def hosts(text):
    for link in LINK_RE.findall(text):
        host = re.sub(r"^https?://", "", link).split("/")[0].rstrip(".,").lower()
        if "." in host and not re.fullmatch(r"[\d.]+", host):
            yield host


def features(text):
    return {
        "length": len(text),
        "words": len(text.split()),
        "digits": sum(c.isdigit() for c in text),
        "link": int(any(hosts(text))),
        "phone": int(bool(PHONE_RE.search(text))),
        "currency": int(bool(CURRENCY_RE.search(text))),
        "exclamation": text.count("!"),
        "capitals": len(re.findall(r"\b[A-Z]{2,}\b", text)),
        "emoji": len(EMOJI_RE.findall(text)),
    }


def threshold_acc(x_train, y_train, x_test, y_test):
    """Best single threshold on train, scored on test."""
    best, rule = -1, None
    for t in np.unique(x_train):
        for above in (True, False):
            acc = (((x_train >= t) if above else (x_train < t)) == y_train).mean()
            if acc > best:
                best, rule = acc, (t, above)
    t, above = rule
    return (((x_test >= t) if above else (x_test < t)) == y_test).mean()


def trigrams(text):
    s = re.sub(r"\s+", " ", re.sub(r"\d", "0", text.lower()))
    return {s[i:i + 3] for i in range(len(s) - 2)}


def jaccard(a, b):
    return len(a & b) / len(a | b) if a | b else 0.0


class Report:
    def __init__(self):
        self.fails, self.warns = [], []

    def fail(self, msg):
        self.fails.append(msg)

    def warn(self, msg):
        self.warns.append(msg)


def check_safety(rep, df, tricky):
    for name, frame in [("messages", df), ("tricky", tricky)]:
        for row in frame.itertuples():
            for host in hosts(row.text):
                if not host.endswith(".example"):
                    rep.fail(f"{name}: non-reserved domain {host!r}: {row.text}")
                elif row.label == "spam" and host in TRUSTED:
                    rep.fail(f"{name}: trusted domain {host!r} in spam: {row.text}")
            if REAL_PHONE_RE.search(row.text):
                rep.fail(f"{name}: number that looks like a real phone: {row.text}")
            if m := REAL_NAMES.search(row.text):
                rep.fail(f"{name}: real brand or organization {m.group()!r}: {row.text}")


def check_leakage(rep, df, tricky, folds):
    for train_idx, test_idx in folds:
        if set(df.template_id.iloc[train_idx]) & set(df.template_id.iloc[test_idx]):
            rep.fail("a template appears in both train and test")
            break
    grams = [trigrams(t) for t in df.text]
    ids = df.template_id.tolist()
    for i in range(len(grams)):
        for j in range(i + 1, len(grams)):
            if ids[i] != ids[j] and jaccard(grams[i], grams[j]) >= MAX_NEAR_DUP:
                rep.fail(f"near-duplicate templates {ids[i]} and {ids[j]}")
    for row in tricky.itertuples():
        g = trigrams(row.text)
        sim, j = max((jaccard(g, h), k) for k, h in enumerate(grams))
        if sim >= MAX_TRICKY_SIM:
            rep.fail(f"tricky row too close to {ids[j]} ({sim:.2f}): {row.text}")


def check_shortcuts(rep, df, folds):
    feats = pd.DataFrame([features(t) for t in df.text])
    y = (df.label == "spam").values
    rows = []
    for col in feats:
        x = feats[col].values
        acc = np.mean([threshold_acc(x[a], y[a], x[b], y[b]) for a, b in folds])
        rows.append((col, acc))
        if acc > MAX_FEATURE_ACC:
            rep.fail(f"feature {col!r} alone reaches {acc:.0%} (limit {MAX_FEATURE_ACC:.0%})")
    majority = max(y.mean(), 1 - y.mean())
    print(f"\nOne-feature accuracy (mean of {len(folds)} group folds, majority class = {majority:.0%}):")
    for col, acc in rows:
        print(f"  {col:12s} {acc:.0%}")

    counts = {lab: Counter() for lab in ("ham", "spam")}
    for text, lab in zip(df.text, df.label):
        counts[lab].update(set(re.findall(r"\w+", text.lower())))
    for lab, other in (("ham", "spam"), ("spam", "ham")):
        pure = [f"{w} ({n})" for w, n in counts[lab].most_common() if n >= PURE_TOKEN_MIN and counts[other][w] == 0]
        if pure:
            rep.warn(f"words only in {lab}: {', '.join(pure[:15])}")


def check_balance(rep):
    reg = []
    for name in ("ar_ham", "ar_spam"):
        templates = json.loads((DATA / "templates" / f"{name}.json").read_text(encoding="utf-8"))
        reg.append(np.mean([t["register"] == "msa" for t in templates]))
    if abs(reg[0] - reg[1]) > MAX_REGISTER_GAP:
        rep.fail(f"Arabic MSA share differs: ham {reg[0]:.0%}, spam {reg[1]:.0%}")


def run():
    df = pd.read_csv(DATA / "messages.csv")
    tricky = pd.read_csv(DATA / "tricky.csv")
    splitter = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=SEED)
    folds = list(splitter.split(df, df.label + "_" + df.lang, groups=df.template_id))

    rep = Report()
    check_safety(rep, df, tricky)
    check_leakage(rep, df, tricky, folds)
    check_shortcuts(rep, df, folds)
    check_balance(rep)

    print(f"\nRows: {len(df)} messages, {len(tricky)} tricky, {df.template_id.nunique()} templates")
    for msg in rep.warns:
        print(f"WARN  {msg}")
    for msg in rep.fails:
        print(f"FAIL  {msg}")
    print("Audit passed." if not rep.fails else f"Audit failed: {len(rep.fails)} problem(s).")
    return not rep.fails


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(0 if run() else 1)
