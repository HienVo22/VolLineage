
"""Summarize player identity matching decisions for VolLineage."""

from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
REVIEW_FILE = ROOT / "data/processed/review_queue.csv"
OUTPUT_DIR = ROOT / "reports"

def main():
    df = pd.read_csv(REVIEW_FILE)

    print("\n=== Player Identity Validation ===")
    print(f"Total candidate pairs: {len(df)}")

    print("\nDecisions:")
    print(df["decision"].value_counts().to_string())

    uncertain = df[
        df["decision"].isin([
            "review",
            "review_conflicting_fields"
        ])
    ].copy()

    print(f"\nPairs requiring manual review: {len(uncertain)}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output = OUTPUT_DIR / "uncertain_player_matches.csv"
    uncertain.to_csv(output, index=False)

    print(f"\nSaved: {output}")

if __name__ == "__main__":
    main()
