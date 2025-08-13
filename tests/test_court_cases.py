"""
Test script for court case analysis to verify the system is truly generalized.
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.tools import DataAnalystTools
import pandas as pd
from datetime import datetime, timedelta
import random


def create_sample_court_data():
    """Create sample court case data similar to the real dataset."""
    courts = [
        "Madras High Court",
        "Delhi High Court",
        "Bombay High Court",
        "Karnataka High Court",
        "Kerala High Court",
    ]
    disposal_natures = [
        "DISMISSED",
        "ALLOWED",
        "PARTIALLY ALLOWED",
        "REMANDED",
        "WITHDRAWN",
    ]
    data = []
    for i in range(1000):
        year = random.randint(2019, 2022)
        month = random.randint(1, 12)
        day = random.randint(1, 28)
        reg_date = datetime(year, month, day)
        days_to_decision = random.randint(30, 365)
        decision_date = reg_date + timedelta(days=days_to_decision)
        data.append(
            {
                "court_code": f"{random.randint(10, 50)}~{random.randint(1, 20)}",
                "title": f"Case {i+1} of {year}",
                "description": f"Sample case description {i+1}",
                "judge": f"Justice {chr(65 + random.randint(0, 25))}. {chr(65 + random.randint(0, 25))}.",
                "pdf_link": f"court/orders/case_{i+1}.pdf",
                "cnr": f"HC{year}{str(i+1).zfill(6)}",
                "date_of_registration": reg_date.strftime("%d-%m-%Y"),
                "decision_date": decision_date.strftime("%Y-%m-%d"),
                "disposal_nature": random.choice(disposal_natures),
                "court": random.choice(courts),
                "raw_html": f"<div>Case {i+1}</div>",
                "bench": f"bench_{random.randint(1, 5)}",
                "year": year,
            }
        )
    return pd.DataFrame(data)


def test_court_analysis():
    """Test court case analysis with the new generalized tools."""
    print("⚖️ Testing Court Case Analysis")
    print("=" * 50)
    tools = DataAnalystTools()
    df = create_sample_court_data()
    print(f"Created sample data: {df.shape}")
    print(f"Columns: {list(df.columns)}")
    print(f"Year range: {df['year'].min()} - {df['year'].max()}")
    print()

    # Test 1: Which court disposed the most cases from 2019-2022?
    print("1. Testing 'top_by_count' - Which court disposed most cases 2019-2022?")
    filtered_df = df[(df["year"] >= 2019) & (df["year"] <= 2022)]
    result = tools.analyze_data(filtered_df, "top_by_count", group_by="court", limit=1)
    if isinstance(result, pd.DataFrame) and not result.empty:
        print(
            f"   Top court: {result.iloc[0]['court']} with {result.iloc[0]['count']} cases"
        )
    elif isinstance(result, dict) and "error" in result:
        print(f"   ❌ Error: {result['error']}")
    else:
        print(f"   Result: {result}")
    print()

    # Test 2: Regression slope of registration vs decision dates by year
    print("2. Testing 'date_difference_regression' - Registration vs Decision dates")
    result = tools.analyze_data(
        df,
        "date_difference_regression",
        date1_col="date_of_registration",
        date2_col="decision_date",
        group_by="year",
    )
    if isinstance(result, dict) and "slope" in result:
        print(f"   Regression slope: {result['slope']:.2f} days per year")
        print(f"   R-squared: {result['r_value']**2:.3f}")
    elif isinstance(result, dict) and "error" in result:
        print(f"   ❌ Error: {result['error']}")
    else:
        print(f"   Result: {result}")
    print()

    # Test 3: Visualization of the regression data
    print("3. Testing visualization of regression data")
    if isinstance(result, dict) and "grouped_data" in result:
        viz_result = tools.create_visualization(
            result["grouped_data"],
            "scatter_with_regression",
            x_col="year",
            y_col="date_diff",
        )
        if isinstance(viz_result, str) and viz_result.startswith("data:image"):
            print(f"   ✅ Visualization created: {len(viz_result)} chars")
        else:
            print(f"   ❌ Visualization failed: {viz_result}")
    else:
        print("   Skipped visualization (no grouped_data available)")
    print()

    # Test 4: Test DuckDB query (simulated)
    print("4. Testing DuckDB query capability")
    print(
        "   ✅ DuckDB query capability available for S3 parquet files (not tested here)"
    )
    print()


def test_generalization():
    """Test that the system works with completely different data."""
    print("🔄 Testing System Generalization")
    print("=" * 50)
    tools = DataAnalystTools()
    data = {
        "product_id": range(1, 101),
        "sales_amount": [random.randint(1000, 10000) for _ in range(100)],
        "category": [random.choice(["A", "B", "C"]) for _ in range(100)],
        "region": [
            random.choice(["North", "South", "East", "West"]) for _ in range(100)
        ],
        "rating": [random.uniform(1, 5) for _ in range(100)],
    }
    df = pd.DataFrame(data)
    print(f"Different dataset: {df.shape}")
    print(f"Columns: {list(df.columns)}")
    print()

    # Test correlation with different column names
    print("Testing correlation with different columns...")
    result = tools.analyze_data(df, "correlation", col1="sales_amount", col2="rating")
    if isinstance(result, dict) and "correlation" in result:
        print(f"Sales vs Rating correlation: {result['correlation']:.3f}")
    elif isinstance(result, dict) and "error" in result:
        print(f"❌ Error: {result['error']}")
    else:
        print(f"Result: {result}")
    print()

    # Test visualization with different columns
    print("Testing visualization with different columns...")
    viz_result = tools.create_visualization(
        df, "scatter_with_regression", x_col="sales_amount", y_col="rating"
    )
    if isinstance(viz_result, str) and viz_result.startswith("data:image"):
        print(f"✅ Visualization created successfully ({len(viz_result)} chars)")
    else:
        print(f"❌ Visualization failed: {viz_result}")
    print()


if __name__ == "__main__":
    test_court_analysis()
    print("\n" + "=" * 60 + "\n")
    test_generalization()
