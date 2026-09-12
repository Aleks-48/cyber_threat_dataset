import os
import subprocess

stages = [
    "01_keywords", "02_sources", "03_collection", "04_raw_data",
    "05_cleaning", "06_candidates", "07_manual_100", "08_quality_analysis", "09_verdict"
]

for stage in stages:
    print(f"\n{'='*50}\nRunning {stage}...\n{'='*50}")
    run_script = os.path.join(stage, "run.py")
    if os.path.exists(run_script):
        subprocess.run(["python", "run.py"], cwd=stage)
    else:
        print(f"No run.py found in {stage}")
