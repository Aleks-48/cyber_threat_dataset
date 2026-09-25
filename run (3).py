"""Print and save a fresh audit of the checked-in snapshot."""
import json
from audit import audit, save_report

if __name__ == "__main__":
    report = audit()
    save_report(report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
