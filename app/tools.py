"""
Tools module for the Data Analyst Agent.
Contains utilities for web scraping, data analysis, visualization, and more.
"""

import requests
import pandas as pd
import numpy as np

# Visualization (optional)
try:
    import matplotlib.pyplot as plt
    import seaborn as sns
    VISUALIZATION_AVAILABLE = True
except ImportError:
    VISUALIZATION_AVAILABLE = False
import base64
import io
import json
import duckdb
import plotly.graph_objects as go
import plotly.express as px
from bs4 import BeautifulSoup
from typing import Any, Dict, List, Union, Optional
from scipy import stats
import re
from urllib.parse import urljoin, urlparse
import warnings

warnings.filterwarnings("ignore")


class DataAnalystTools:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
        )

    def scrape_web_data(
        self, url: str, table_selector: str = None
    ) -> Union[pd.DataFrame, Dict]:
        """
        Scrape data from a website, particularly tables.
        """
        try:
            response = self.session.get(url)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, "html.parser")
            tables = soup.find_all("table")
            if tables:
                dfs = pd.read_html(str(tables[0]))
                if dfs:
                    return dfs[0]
            return {
                "title": soup.title.string if soup.title else "",
                "content": soup.get_text()[:1000],
            }
        except Exception as e:
            return {"error": f"Failed to scrape {url}: {str(e)}"}

    def scrape_wikipedia_table(self, url: str, table_index: int = 0) -> pd.DataFrame:
        """
        Specifically scrape Wikipedia tables.
        """
        try:
            tables = pd.read_html(url)
            if tables and len(tables) > table_index:
                df = tables[table_index]
                df.columns = [str(col).strip() for col in df.columns]
                return df
            else:
                raise ValueError(f"No table found at index {table_index}")
        except Exception as e:
            raise Exception(f"Failed to scrape Wikipedia table: {str(e)}")

    def clean_monetary_values(self, df: pd.DataFrame, column: str) -> pd.DataFrame:
        """
        Clean monetary values from text (remove $, commas, convert to numbers).
        """
        df = df.copy()
        if column in df.columns:
            df[column] = df[column].astype(str)
            df[column] = df[column].str.replace(r"[\$,]", "", regex=True)
            df[column] = df[column].str.extract(r"([\d.]+)")[0]
            df[column] = pd.to_numeric(df[column], errors="coerce")
        return df

    def clean_year_column(
        self, df: pd.DataFrame, column: str, **kwargs
    ) -> pd.DataFrame:
        """
        Extract year from text columns.
        """
        df = df.copy()
        if column in df.columns:
            df[column] = df[column].astype(str)
            years = df[column].str.extract(r"(\d{4})")[0]
            df[column] = pd.to_numeric(years, errors="coerce")
        return df

    def analyze_data(
        self, df: pd.DataFrame, analysis_type: str, **kwargs
    ) -> Union[float, int, str, Dict, pd.DataFrame]:
        """
        Perform various data analysis operations.
        Now robust to missing/ambiguous columns and parameters.
        """
        try:
            if analysis_type == "count_condition":
                column = kwargs.get("column")
                value = kwargs.get("value")
                operator = kwargs.get("operator", ">")
                if not column or column not in df.columns:
                    column = self._find_best_column(df, column, "number")
                if column not in df.columns:
                    return {"error": f"No suitable column found for count_condition."}
                if value is None:
                    value = (
                        df[column].median()
                        if pd.api.types.is_numeric_dtype(df[column])
                        else None
                    )
                if value is None:
                    return {
                        "error": f"No value provided or inferred for count_condition."
                    }
                if operator == ">":
                    result = len(df[df[column] > value])
                elif operator == "<":
                    result = len(df[df[column] < value])
                elif operator == ">=":
                    result = len(df[df[column] >= value])
                elif operator == "<=":
                    result = len(df[df[column] <= value])
                elif operator == "==":
                    result = len(df[df[column] == value])
                else:
                    return {"error": f"Unknown operator: {operator}"}
                return result

            elif analysis_type == "filter_and_count":
                filters = kwargs.get("filters", []) or kwargs.get("conditions", [])
                if isinstance(filters, str):
                    try:
                        filters = json.loads(filters)
                    except:
                        return {"error": f"Invalid filters format: {filters}"}
                filtered_df = df.copy()
                for filter_condition in filters:
                    column = filter_condition.get("column")
                    operator = filter_condition.get("operator", ">")
                    value = filter_condition.get("value")
                    if not column or column not in filtered_df.columns:
                        column = self._find_best_column(filtered_df, column, "number")
                    if column not in filtered_df.columns:
                        continue
                    if operator == ">":
                        filtered_df = filtered_df[filtered_df[column] > value]
                    elif operator == "<":
                        filtered_df = filtered_df[filtered_df[column] < value]
                    elif operator == ">=":
                        filtered_df = filtered_df[filtered_df[column] >= value]
                    elif operator == "<=":
                        filtered_df = filtered_df[filtered_df[column] <= value]
                    elif operator == "==":
                        filtered_df = filtered_df[filtered_df[column] == value]
                return len(filtered_df)

            elif analysis_type == "filter_sort_select":
                filters = kwargs.get("filters", [])
                sort_by = kwargs.get("sort_by") or kwargs.get("sort_column")
                ascending = kwargs.get("ascending", True)
                select_column = kwargs.get("select_column")
                n_rows = kwargs.get("n_rows", 1)
                if isinstance(filters, str):
                    try:
                        filters = json.loads(filters)
                    except:
                        return {"error": f"Invalid filters format: {filters}"}
                filtered_df = df.copy()
                for filter_condition in filters:
                    column = filter_condition.get("column")
                    operator = filter_condition.get("operator", ">")
                    value = filter_condition.get("value")
                    if not column or column not in filtered_df.columns:
                        column = self._find_best_column(filtered_df, column)
                    if column not in filtered_df.columns:
                        continue
                    if operator == ">":
                        filtered_df = filtered_df[filtered_df[column] > value]
                    elif operator == "<":
                        filtered_df = filtered_df[filtered_df[column] < value]
                    elif operator == ">=":
                        filtered_df = filtered_df[filtered_df[column] >= value]
                    elif operator == "<=":
                        filtered_df = filtered_df[filtered_df[column] <= value]
                    elif operator == "==":
                        filtered_df = filtered_df[filtered_df[column] == value]
                if filtered_df.empty:
                    return None
                if not sort_by or sort_by not in filtered_df.columns:
                    sort_by = self._find_best_column(filtered_df, sort_by)
                if not select_column or select_column not in filtered_df.columns:
                    select_column = self._find_best_column(filtered_df, select_column)
                filtered_df = filtered_df.sort_values(sort_by, ascending=ascending)
                if select_column and select_column in filtered_df.columns:
                    # Return the selected and sort columns when possible for clarity
                    if sort_by in filtered_df.columns and select_column != sort_by:
                        result_df = filtered_df[[select_column, sort_by]].head(n_rows)
                    else:
                        result_df = filtered_df[[select_column]].head(n_rows)
                else:
                    result_df = filtered_df.head(n_rows)
                return result_df

            elif analysis_type == "earliest_with_condition":
                column = kwargs.get("column")
                value_column = kwargs.get("value_column")
                threshold = kwargs.get("threshold")
                filtered_df = df[df[value_column] >= threshold]
                if not filtered_df.empty:
                    earliest = filtered_df.loc[filtered_df[column].idxmin()]
                    return earliest.to_dict()
                return None

            elif analysis_type == "correlation":
                col1 = kwargs.get("col1") or kwargs.get("column1")
                col2 = kwargs.get("col2") or kwargs.get("column2")
                if not col1 or col1 not in df.columns:
                    col1 = self._find_best_column(df, col1, "number")
                if not col2 or col2 not in df.columns:
                    col2 = self._find_best_column(df, col2, "number")
                if col1 not in df.columns or col2 not in df.columns:
                    return {"error": f"No suitable columns found for correlation."}
                clean_df = df[[col1, col2]].copy()
                for col in [col1, col2]:
                    if col in clean_df.columns:
                        numeric_col = pd.to_numeric(clean_df[col], errors="coerce")
                        if numeric_col.isna().sum() > len(numeric_col) * 0.5:
                            clean_df[col] = pd.to_numeric(
                                clean_df[col]
                                .astype(str)
                                .str.extract(r"(\d+\.?\d*)")[0],
                                errors="coerce",
                            )
                        else:
                            clean_df[col] = numeric_col
                clean_df = clean_df.dropna()
                if len(clean_df) > 1:
                    correlation = clean_df[col1].corr(clean_df[col2])
                    return {"correlation": correlation}
                else:
                    return {"error": "Insufficient data for correlation"}

            elif analysis_type == "regression":
                x_col = kwargs.get("x_col")
                y_col = kwargs.get("y_col")
                if y_col == "delay_days" and "date_diff" in df.columns:
                    y_col = "date_diff"
                elif y_col == "delay_days" and "delay" in df.columns:
                    y_col = "delay"
                elif "date_diff" in df.columns and (
                    "delay" in y_col or "diff" in y_col
                ):
                    y_col = "date_diff"
                if x_col not in df.columns:
                    return {
                        "error": f"Column '{x_col}' not found. Available columns: {list(df.columns)}"
                    }
                if y_col not in df.columns:
                    return {
                        "error": f"Column '{y_col}' not found. Available columns: {list(df.columns)}"
                    }
                clean_df = df[[x_col, y_col]].dropna()
                if len(clean_df) < 2:
                    return {
                        "error": f"Insufficient data for regression. Only {len(clean_df)} valid data points."
                    }
                slope, intercept, r_value, p_value, std_err = stats.linregress(
                    clean_df[x_col], clean_df[y_col]
                )
                return {
                    "slope": slope,
                    "intercept": intercept,
                    "r_value": r_value,
                    "p_value": p_value,
                    "std_err": std_err,
                }

            elif analysis_type == "date_difference_regression":
                # Generic regression of date differences over time (by year or provided group)
                date1_col = kwargs.get("date1_col")
                date2_col = kwargs.get("date2_col")
                group_by = kwargs.get("group_by")
                df_copy = df.copy()
                # Ensure date_diff is available
                if "date_diff" not in df_copy.columns:
                    df_copy[date1_col] = pd.to_datetime(
                        df_copy[date1_col], errors="coerce"
                    )
                    df_copy[date2_col] = pd.to_datetime(
                        df_copy[date2_col], errors="coerce"
                    )
                    df_copy["date_diff"] = (
                        df_copy[date2_col] - df_copy[date1_col]
                    ).dt.days
                df_copy = df_copy.dropna(subset=["date_diff"])
                if len(df_copy) == 0:
                    return {"error": "No valid date differences found"}
                # If grouping is provided and exists, use it directly
                if group_by and group_by in df_copy.columns:
                    grouped = (
                        df_copy.groupby(group_by)["date_diff"].mean().reset_index()
                    )
                    if len(grouped) > 1 and pd.api.types.is_numeric_dtype(
                        grouped[group_by]
                    ):
                        slope, intercept, r_value, p_value, std_err = stats.linregress(
                            grouped[group_by], grouped["date_diff"]
                        )
                        return {
                            "slope": slope,
                            "intercept": intercept,
                            "r_value": r_value,
                            "p_value": p_value,
                            "std_err": std_err,
                            "grouped_data": grouped,
                        }
                    else:
                        return grouped
                # Otherwise infer a year column from any datetime-like column
                # Prefer the first valid datetime column among inputs
                datetime_source_col = None
                for candidate in [date1_col, date2_col] + list(df_copy.columns):
                    if candidate in df_copy.columns:
                        series = pd.to_datetime(df_copy[candidate], errors="coerce")
                        if series.notna().any():
                            df_copy[candidate] = series
                            datetime_source_col = candidate
                            break
                if datetime_source_col is None:
                    return {
                        "error": "No datetime column found to infer 'year' for regression"
                    }
                df_copy["year"] = pd.to_datetime(
                    df_copy[datetime_source_col], errors="coerce"
                ).dt.year
                df_copy = df_copy.dropna(subset=["year", "date_diff"])
                if len(df_copy) > 1:
                    slope, intercept, r_value, p_value, std_err = stats.linregress(
                        df_copy["year"], df_copy["date_diff"]
                    )
                    return {
                        "slope": slope,
                        "intercept": intercept,
                        "r_value": r_value,
                        "p_value": p_value,
                        "std_err": std_err,
                    }
                return {"error": "Insufficient data for regression"}

            elif analysis_type == "top_by_count":
                group_by = kwargs.get("group_by")
                count_column = kwargs.get("count_column") or kwargs.get("column")
                limit = kwargs.get("limit", 1)
                df_copy = df.copy()
                if count_column and count_column in df_copy.columns:
                    result = df_copy.sort_values(count_column, ascending=False).head(
                        limit
                    )
                    return result
                if group_by:
                    result = df_copy.groupby(group_by).size().reset_index(name="count")
                    result = result.sort_values("count", ascending=False).head(limit)
                    return result
                return {
                    "error": "No group_by or count_column specified for top_by_count analysis"
                }

        except Exception as e:
            return {"error": f"Analysis failed: {str(e)}"}

    def create_visualization(self, df: pd.DataFrame, plot_type: str, **kwargs) -> str:
        """
        Create various types of visualizations and return as base64 encoded string.
        Now robust to missing/ambiguous columns and parameters.
        """
        try:
            plt.figure(figsize=(10, 6))
            if plot_type == "scatter_with_regression":
                x_col = kwargs.get("x_col") or kwargs.get("x")
                y_col = kwargs.get("y_col") or kwargs.get("y")
                if y_col == "delay_days" and "date_diff" in df.columns:
                    y_col = "date_diff"
                elif y_col == "delay_days" and "delay" in df.columns:
                    y_col = "delay"
                elif "date_diff" in df.columns and (
                    "delay" in y_col or "diff" in y_col
                ):
                    y_col = "date_diff"
                if not x_col or x_col not in df.columns:
                    x_col = self._find_best_column(df, x_col, "number")
                if not y_col or y_col not in df.columns:
                    y_col = self._find_best_column(df, y_col, "number")
                if x_col not in df.columns or y_col not in df.columns:
                    return f"Error: No suitable columns found for scatter_with_regression. Available columns: {list(df.columns)}"
                clean_df = df[[x_col, y_col]].copy()
                for col in [x_col, y_col]:
                    if col in clean_df.columns:
                        numeric_col = pd.to_numeric(clean_df[col], errors="coerce")
                        if numeric_col.isna().sum() > len(numeric_col) * 0.5:
                            clean_df[col] = pd.to_numeric(
                                clean_df[col]
                                .astype(str)
                                .str.extract(r"(\d+\.?\d*)")[0],
                                errors="coerce",
                            )
                        else:
                            clean_df[col] = numeric_col
                clean_df = clean_df.dropna()
                if len(clean_df) < 2:
                    return f"Error: Insufficient data for visualization. Only {len(clean_df)} valid data points."
                plt.scatter(clean_df[x_col], clean_df[y_col], alpha=0.6, s=50)
                slope, intercept, r_value, p_value, std_err = stats.linregress(
                    clean_df[x_col], clean_df[y_col]
                )
                line_x = np.linspace(clean_df[x_col].min(), clean_df[x_col].max(), 100)
                line_y = slope * line_x + intercept
                plt.plot(
                    line_x,
                    line_y,
                    "r--",
                    linewidth=2,
                    label=f"Regression Line (R²={r_value**2:.3f})",
                )
                plt.xlabel(x_col)
                plt.ylabel(y_col)
                plt.title(f"Scatter Plot: {x_col} vs {y_col}")
                plt.legend()
                plt.grid(True, alpha=0.3)
            elif plot_type == "time_series":
                x_col = kwargs.get("x_col")
                y_col = kwargs.get("y_col")
                clean_df = df[[x_col, y_col]].dropna().sort_values(x_col)
                plt.plot(
                    clean_df[x_col],
                    clean_df[y_col],
                    marker="o",
                    linewidth=2,
                    markersize=6,
                )
                plt.xlabel(x_col)
                plt.ylabel(y_col)
                plt.title(f"{y_col} over {x_col}")
                plt.grid(True, alpha=0.3)
            elif plot_type == "bar":
                x_col = kwargs.get("x_col")
                y_col = kwargs.get("y_col")
                plt.bar(df[x_col], df[y_col])
                plt.xlabel(x_col)
                plt.ylabel(y_col)
                plt.title(f"Bar Plot: {y_col} by {x_col}")
                plt.xticks(rotation=45)
            plt.tight_layout()
            buffer = io.BytesIO()
            plt.savefig(buffer, format="png", dpi=100, bbox_inches="tight")
            buffer.seek(0)
            plot_data = buffer.getvalue()
            buffer.close()
            plt.close()
            plot_base64 = base64.b64encode(plot_data).decode("utf-8")
            return f"data:image/png;base64,{plot_base64}"
        except Exception as e:
            plt.close()
            return f"Error creating visualization: {str(e)}"

    def query_duckdb(self, query: str) -> pd.DataFrame:
        """
        Execute DuckDB queries.
        """
        try:
            conn = duckdb.connect()
            conn.execute("INSTALL httpfs; LOAD httpfs;")
            conn.execute("INSTALL parquet; LOAD parquet;")
            result = conn.execute(query).fetchdf()
            conn.close()
            return result
        except Exception as e:
            error_msg = str(e)
            if "julianday" in error_msg:
                error_msg += " (Use DATEDIFF('day', CAST(date1 AS DATE), CAST(date2 AS DATE)) instead of julianday())"
            elif "function" in error_msg.lower() and "does not exist" in error_msg:
                error_msg += " (Check DuckDB function documentation for correct syntax)"
            elif (
                "no function matches" in error_msg.lower()
                and "datediff" in error_msg.lower()
            ):
                error_msg += " (Use explicit type casting: DATEDIFF('day', CAST(date1 AS DATE), CAST(date2 AS DATE)))"
            elif (
                "binder error" in error_msg.lower()
                and "argument types" in error_msg.lower()
            ):
                error_msg += " (Add explicit type casts for date columns)"
            elif "date field value out of range" in error_msg.lower():
                error_msg += " (Use STRPTIME(date_string, '%d-%m-%Y') to convert DD-MM-YYYY format to DATE)"
            elif (
                "conversion error" in error_msg.lower() and "date" in error_msg.lower()
            ):
                error_msg += " (Use STRPTIME() for date format conversion)"
            elif (
                "could not parse string" in error_msg.lower()
                and "format specifier" in error_msg.lower()
            ):
                error_msg += " (Ensure you parse non-ISO date strings using STRPTIME with the correct format string)"
            return pd.DataFrame({"error": [f"DuckDB query failed: {error_msg}"]})

    def extract_numbers_from_text(self, text: str) -> List[float]:
        """
        Extract numbers from text using regex.
        """
        numbers = re.findall(r"-?\d+\.?\d*", str(text))
        return [float(n) for n in numbers if n]

    def process_currency_to_billions(self, value: str) -> float:
        """
        Convert currency strings to billions (for movie grossings).
        """
        try:
            value = str(value).lower()
            value = re.sub(r"[\$,]", "", value)
            numbers = re.findall(r"\d+\.?\d*", value)
            if not numbers:
                return 0.0
            num = float(numbers[0])
            if "billion" in value or "bn" in value:
                return num
            elif "million" in value or "mn" in value:
                return num / 1000.0
            else:
                return num / 1_000_000_000.0
        except:
            return 0.0

    def safe_extract_year(self, text: str) -> Optional[int]:
        """
        Safely extract year from text.
        """
        try:
            years = re.findall(r"(19|20)\d{2}", str(text))
            if years:
                return int(years[0])
            return None
        except:
            return None

    def calculate_date_difference(
        self,
        df: pd.DataFrame,
        date1_col: str,
        date2_col: str,
        unit: str = "days",
        **kwargs,
    ) -> pd.DataFrame:
        """
        Calculate difference between two date columns.
        """
        df = df.copy()
        try:

            def parse_date_flexible(date_series):
                for fmt in ["%Y-%m-%d", "%d-%m-%Y", "%m/%d/%Y", "%Y/%m/%d"]:
                    try:
                        return pd.to_datetime(date_series, format=fmt, errors="coerce")
                    except:
                        continue
                return pd.to_datetime(date_series, errors="coerce")

            df[date1_col] = parse_date_flexible(df[date1_col])
            df[date2_col] = parse_date_flexible(df[date2_col])
            diff = df[date2_col] - df[date1_col]
            if unit == "days":
                df["date_diff"] = diff.dt.days
            elif unit == "months":
                df["date_diff"] = diff.dt.days / 30.44
            elif unit == "years":
                df["date_diff"] = diff.dt.days / 365.25
            return df
        except Exception as e:
            df["date_diff"] = np.nan
            return df

    def group_and_aggregate(
        self,
        df: pd.DataFrame,
        group_by: str = None,
        agg_col: str = None,
        agg_func: str = "count",
    ) -> pd.DataFrame:
        """
        Group data and apply aggregation. If group_by is None or '', aggregate over all rows.
        """
        try:
            if not group_by or group_by == "":
                # Aggregate over all rows
                if agg_func == "count":
                    result = pd.DataFrame({agg_col: [df[agg_col].count()]})
                elif agg_func == "sum":
                    result = pd.DataFrame({agg_col: [df[agg_col].sum()]})
                elif agg_func == "mean":
                    result = pd.DataFrame({agg_col: [df[agg_col].mean()]})
                elif agg_func == "max":
                    result = pd.DataFrame({agg_col: [df[agg_col].max()]})
                elif agg_func == "min":
                    result = pd.DataFrame({agg_col: [df[agg_col].min()]})
                else:
                    result = pd.DataFrame({agg_col: [df[agg_col].agg(agg_func)]})
                return result
            # ...existing code for group_by...
            if agg_func == "count":
                result = df.groupby(group_by).size().reset_index(name="count")
            elif agg_func == "sum":
                result = df.groupby(group_by)[agg_col].sum().reset_index()
            elif agg_func == "mean":
                result = df.groupby(group_by)[agg_col].mean().reset_index()
            elif agg_func == "max":
                result = df.groupby(group_by)[agg_col].max().reset_index()
            elif agg_func == "min":
                result = df.groupby(group_by)[agg_col].min().reset_index()
            else:
                result = df.groupby(group_by).agg({agg_col: agg_func}).reset_index()
            return result
        except Exception as e:
            return pd.DataFrame({"error": [f"Grouping failed: {str(e)}"]})

    def _find_best_column(
        self, df: pd.DataFrame, target: str = None, dtype: str = None
    ) -> str:
        """
        Find the best column in a DataFrame for a given type or target.
        """
        columns = list(df.columns)
        if target and target in columns:
            return target
        if dtype == "number":
            num_cols = df.select_dtypes(include=[np.number]).columns
            if len(num_cols) > 0:
                return num_cols[0]
        elif dtype == "datetime":
            dt_cols = df.select_dtypes(include=["datetime", "datetimetz"]).columns
            if len(dt_cols) > 0:
                return dt_cols[0]
        return columns[0] if columns else None

    def execute_action(self, action: str, params: Dict[str, Any]) -> Any:
        """
        Execute a named action with the given parameters.
        Dispatches to the appropriate method based on the action name.
        """
        try:
            # Preprocess parameters: convert all keys to lowercase
            processed_params = {k.lower(): v for k, v in params.items()}

            if action == "scrape_web_data":
                url = processed_params.get("url")
                table_selector = processed_params.get("table_selector")
                return self.scrape_web_data(url, table_selector)

            elif action == "scrape_wikipedia_table":
                url = processed_params.get("url")
                table_index = processed_params.get("table_index", 0)
                return self.scrape_wikipedia_table(url, table_index)

            elif action == "clean_monetary_values":
                df = processed_params.get("df")
                column = processed_params.get("column")
                return self.clean_monetary_values(df, column)

            elif action == "clean_year_column":
                df = processed_params.get("df")
                column = processed_params.get("column")
                return self.clean_year_column(df, column)

            elif action == "analyze_data":
                df = processed_params.get("df")
                analysis_type = processed_params.get("analysis_type")
                return self.analyze_data(df, analysis_type, **processed_params)

            elif action == "create_visualization":
                df = processed_params.get("df")
                plot_type = processed_params.get("plot_type")
                return self.create_visualization(df, plot_type, **processed_params)

            elif action == "query_duckdb":
                query = processed_params.get("query")
                return self.query_duckdb(query)

            elif action == "extract_numbers_from_text":
                text = processed_params.get("text")
                return self.extract_numbers_from_text(text)

            elif action == "process_currency_to_billions":
                value = processed_params.get("value")
                return self.process_currency_to_billions(value)

            elif action == "safe_extract_year":
                text = processed_params.get("text")
                return self.safe_extract_year(text)

            elif action == "calculate_date_difference":
                df = processed_params.get("df")
                date1_col = processed_params.get("date1_col")
                date2_col = processed_params.get("date2_col")
                return self.calculate_date_difference(
                    df, date1_col, date2_col, **processed_params
                )

            elif action == "group_and_aggregate":
                df = processed_params.pop("df")
                # Fallback for missing group_by
                if (
                    "group_by" not in processed_params
                    or not processed_params["group_by"]
                ):
                    processed_params["group_by"] = None
                result = self.group_and_aggregate(df, **processed_params)
                return result

        except Exception as e:
            return {"error": f"Action execution failed: {str(e)}"}
