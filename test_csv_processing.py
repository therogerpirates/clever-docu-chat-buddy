#!/usr/bin/env python3
"""
Test CSV processing utilities
"""

import os
import sys
import pandas as pd
import json
from pathlib import Path

# Add the backend app directory to Python path
sys.path.append(str(Path(__file__).parent / "backend" / "app"))

def test_csv_processing():
    print("📄 Testing CSV Processing")
    print("=" * 40)

    test_csv_path = "test.csv"
    if not os.path.exists(test_csv_path):
        print(f"❌ Test CSV not found: {test_csv_path}")
        print("Please create a test.csv file in the project root.")
        return False

    print(f"📄 Using test CSV: {test_csv_path}")
    print(f"📏 File size: {os.path.getsize(test_csv_path) / 1024:.2f} KB")

    # Load CSV
    df = pd.read_csv(test_csv_path)
    print(f"✅ Loaded CSV with {len(df)} rows and {len(df.columns)} columns")
    print(f"Columns: {list(df.columns)}")

    # Import embedding function
    from backend.app.csv_utils import get_embedding_with_retry

    # Process each row
    results = []
    for idx, row in df.iterrows():
        row_dict = row.to_dict()
        content_str = json.dumps(row_dict, ensure_ascii=False)
        try:
            embedding = get_embedding_with_retry(content_str)
            print(f"Row {idx+1}: {content_str}")
            print(f"  Embedding: {embedding[:5]}... (total {len(embedding)} dims)")
            results.append({
                "row_number": idx + 1,
                "content": content_str,
                "embedding": embedding
            })
        except Exception as e:
            print(f"  ❌ Error embedding row {idx+1}: {e}")
            results.append({
                "row_number": idx + 1,
                "content": content_str,
                "embedding": None,
                "error": str(e)
            })

    print(f"\n✅ Processed {len(results)} rows.")
    return True

if __name__ == "__main__":
    success = test_csv_processing()
    sys.exit(0 if success else 1)
