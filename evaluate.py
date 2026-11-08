"""Оценка расширенного корпуса: python evaluate.py"""
import json
from pathlib import Path
from evaluation import evaluate_records

ROOT = Path(__file__).resolve().parent
DATA_PATH = ROOT / "data" / "benchmark.json"
REPORT_DIR = ROOT / "reports"
REPORT_PATH = REPORT_DIR / "latest_benchmark_report.json"


def main():
    try:
        from analyzer import SyntaxAnalyzer
    except ModuleNotFoundError as exc:
        if exc.name == "pymorphy3":
            raise SystemExit("Не найдена pymorphy3. Выполните: python -m pip install -r requirements.txt")
        raise

    records = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    report = evaluate_records(records, SyntaxAnalyzer())
    REPORT_DIR.mkdir(exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    m = report["metrics"]
    print("SyntaxGuard v9.1 — оценка расширенного размеченного корпуса")
    print(f"Всего предложений: {m['total']}")
    print(f"С ошибками в эталоне: {m['tp'] + m['fn']}")
    print(f"Корректных в эталоне: {m['tn'] + m['fp']}")
    print(f"TP={m['tp']}  FP={m['fp']}  TN={m['tn']}  FN={m['fn']}")
    print("\nМетрики на уровне предложения:")
    print(f"Precision: {m['precision']:.3f}")
    print(f"Recall:    {m['recall']:.3f}")
    print(f"F1-score:  {m['f1']:.3f}")
    print(f"Accuracy:  {m['accuracy']:.3f}")

    print("\nМакроусреднение по группам правил (multi-label):")
    for metric, value in report["macro_rule_metrics"].items():
        print(f"{metric}: {value:.3f}")
    print(f"Точное совпадение набора правил: {report['exact_rule_matches']}/{m['total']} "
          f"({report['exact_rule_match_rate']:.3f})")

    if "holdout" in report["per_split_sentence_metrics"]:
        h = report["per_split_sentence_metrics"]["holdout"]
        print("\nОтдельная проверка на отложенной части корпуса:")
        print(f"N={h['total']}  TP={h['tp']}  FP={h['fp']}  TN={h['tn']}  FN={h['fn']}")
        print(f"Precision={h['precision']:.3f}  Recall={h['recall']:.3f}  "
              f"F1={h['f1']:.3f}  Accuracy={h['accuracy']:.3f}")

    print("\nМетрики по группам правил:")
    for rule, row in report["rule_level_metrics"].items():
        print(f"- {rule}: P={row['precision']:.3f}, R={row['recall']:.3f}, "
              f"F1={row['f1']:.3f}, TP={row['tp']}, FP={row['fp']}, FN={row['fn']}")

    if report["false_positives"]:
        print("\nЛожные срабатывания на уровне предложения:")
        for item in report["false_positives"]:
            print(f"- [{item['id']}] {item['sentence']} — обнаружено: {', '.join(item['detected_rules'])}")
    if report["false_negatives"]:
        print("\nПропущенные ошибки на уровне предложения:")
        for item in report["false_negatives"]:
            print(f"- [{item['id']}] {item['sentence']} — ожидалось: {', '.join(item['expected_rules'])}")
    if report["rule_false_positives"]:
        print(f"\nНеожиданные группы правил: {len(report['rule_false_positives'])} предложений (детали в JSON)")
    if report["rule_false_negatives"]:
        print(f"Пропущенные группы правил: {len(report['rule_false_negatives'])} предложений (детали в JSON)")
    print(f"\nПодробный отчёт: {REPORT_PATH}")
    print("Примечание: это учебный корпус; метрики нельзя переносить на все русские тексты.")


if __name__ == "__main__":
    main()
