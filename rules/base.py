from dataclasses import dataclass

@dataclass
class Finding:
    rule: str
    message: str
    start: int
    end: int
    suggestion: str = ""
    severity: str = "warning"

def deduplicate_findings(findings):
    """Удаляет только полностью одинаковые замечания.

    Рекомендация входит в ключ: для обращения в середине предложения
    пропуск запятой до слова и после него — две разные ошибки, даже если
    у них совпадают название правила, объяснение и диапазон слова.
    """
    unique = {}
    for finding in findings:
        key = (
            finding.rule, finding.message, finding.start, finding.end,
            finding.suggestion, finding.severity,
        )
        unique[key] = finding
    return list(unique.values())
