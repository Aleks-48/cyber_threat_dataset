"""Run the audit, then exploratory model evaluation when dependencies are present."""
import json
from audit import audit, save_report


def main():
    report = audit()
    save_report(report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not report["next_stage_allowed"]:
        print("Quality gate blocked. Model scores, if calculated, are demo-only.")
        return 1
    from train_models import train_and_evaluate
    results, metadata = train_and_evaluate()
    print(json.dumps({"results": results, "metadata": metadata},
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
