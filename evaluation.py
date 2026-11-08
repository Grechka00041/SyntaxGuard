"""Метрики SyntaxGuard на размеченном корпусе.

Sentence-level: предсказывается наличие хотя бы одной ошибки в предложении.
Rule-level: expected_rules сравнивается с множеством реально обнаруженных правил.
Метрики не оценивают точные позиции всех запятых.
"""
from collections import defaultdict


def _safe_div(numerator, denominator):
    return numerator / denominator if denominator else 0.0


def _binary_counts(gold, predicted):
    tp = fp = tn = fn = 0
    for actual, guess in zip(gold, predicted):
        actual, guess = bool(actual), bool(guess)
        if actual and guess:
            tp += 1
        elif not actual and guess:
            fp += 1
        elif not actual and not guess:
            tn += 1
        else:
            fn += 1
    precision = _safe_div(tp, tp + fp)
    recall = _safe_div(tp, tp + fn)
    f1 = _safe_div(2 * precision * recall, precision + recall)
    accuracy = _safe_div(tp + tn, len(gold))
    return {
        "total": len(gold), "tp": tp, "fp": fp, "tn": tn, "fn": fn,
        "precision": precision, "recall": recall, "f1": f1, "accuracy": accuracy,
    }


def calculate_metrics(gold_labels, predicted_labels):
    if len(gold_labels) != len(predicted_labels):
        raise ValueError("Число эталонных и предсказанных меток должно совпадать")
    return _binary_counts(gold_labels, predicted_labels)


def evaluate_records(records, analyzer):
    sentence_gold, sentence_predicted, details = [], [], []
    rule_names = sorted({rule for record in records for rule in record.get("expected_rules", [])})
    rule_names = sorted(set(rule_names) | {
        "Вводное слово", "Деепричастный оборот", "Обращение",
        "Однородные члены предложения", "Причастный оборот",
        "Противительный союз", "Сложносочинённое предложение",
        "Сравнительный оборот", "Уточняющий член предложения",
    })
    per_rule_gold = {rule: [] for rule in rule_names}
    per_rule_pred = {rule: [] for rule in rule_names}
    per_category = defaultdict(lambda: {"gold": [], "predicted": []})
    per_split = defaultdict(lambda: {"gold": [], "predicted": []})
    exact_matches = 0

    for record in records:
        result = analyzer.analyze_sentence(record["sentence"])
        predicted_rules = sorted({item.get("rule", "") for item in result.get("findings", []) if item.get("rule")})
        expected_rules = sorted(set(record.get("expected_rules", [])))
        gold_error = bool(record["has_punctuation_error"])
        predicted_error = result.get("status") == "error" or bool(predicted_rules)
        sentence_gold.append(gold_error)
        sentence_predicted.append(predicted_error)
        expected_set, predicted_set = set(expected_rules), set(predicted_rules)
        exact_match = expected_set == predicted_set
        exact_matches += int(exact_match)

        for rule in rule_names:
            per_rule_gold[rule].append(rule in expected_set)
            per_rule_pred[rule].append(rule in predicted_set)

        category = record.get("rule_group", "Без категории")
        per_category[category]["gold"].append(gold_error)
        per_category[category]["predicted"].append(predicted_error)
        split = record.get("split", "unspecified")
        per_split[split]["gold"].append(gold_error)
        per_split[split]["predicted"].append(predicted_error)

        details.append({
            "id": record.get("id"),
            "rule_group": category,
            "pair_id": record.get("pair_id"),
            "sentence": record["sentence"],
            "gold_error": gold_error,
            "predicted_error": predicted_error,
            "expected_rules": expected_rules,
            "detected_rules": predicted_rules,
            "missed_rules": sorted(expected_set - predicted_set),
            "unexpected_rules": sorted(predicted_set - expected_set),
            "findings": result.get("findings", []),
            "sentence_match": gold_error == predicted_error,
            "exact_rule_match": exact_match,
        })

    sentence_metrics = _binary_counts(sentence_gold, sentence_predicted)
    per_rule_metrics = {
        rule: _binary_counts(per_rule_gold[rule], per_rule_pred[rule])
        for rule in rule_names
    }
    per_category_metrics = {
        category: _binary_counts(values["gold"], values["predicted"])
        for category, values in sorted(per_category.items())
    }
    per_split_metrics = {
        split: _binary_counts(values["gold"], values["predicted"])
        for split, values in sorted(per_split.items())
    }

    macro = {
        metric: _safe_div(sum(row[metric] for row in per_rule_metrics.values()), len(per_rule_metrics))
        for metric in ("precision", "recall", "f1", "accuracy")
    }
    false_positives = [item for item in details if not item["gold_error"] and item["predicted_error"]]
    false_negatives = [item for item in details if item["gold_error"] and not item["predicted_error"]]
    rule_false_positives = [item for item in details if item["unexpected_rules"]]
    rule_false_negatives = [item for item in details if item["missed_rules"]]

    # Backwards-compatible concise recall summary.
    per_rule_recall = {
        rule: {
            "total": row["tp"] + row["fn"],
            "detected": row["tp"],
            "missed": row["fn"],
            "recall": row["recall"],
        }
        for rule, row in per_rule_metrics.items()
    }

    return {
        "metrics": sentence_metrics,
        "rule_level_metrics": per_rule_metrics,
        "macro_rule_metrics": macro,
        "per_category_sentence_metrics": per_category_metrics,
        "per_split_sentence_metrics": per_split_metrics,
        "per_rule_recall": per_rule_recall,
        "exact_rule_match_rate": _safe_div(exact_matches, len(records)),
        "exact_rule_matches": exact_matches,
        "false_positives": false_positives,
        "false_negatives": false_negatives,
        "rule_false_positives": rule_false_positives,
        "rule_false_negatives": rule_false_negatives,
        "details": details,
        "metric_level": "sentence_and_rule_group",
    }
