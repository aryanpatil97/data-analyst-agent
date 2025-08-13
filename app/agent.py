"""
Main Data Analyst Agent that uses LLM to understand tasks and execute them.
"""

import google.generativeai as genai
import json
import traceback
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Union
from .tools import DataAnalystTools
import re
import os
from dotenv import load_dotenv

load_dotenv()


class DataAnalystAgent:
    def __init__(self, api_key: str = None):
        """
        Initialize the Data Analyst Agent with Gemini API.
        """
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Gemini API key is required. Set GEMINI_API_KEY environment variable or pass api_key parameter."
            )

        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel("gemini-2.5-flash")
        self.tools = DataAnalystTools()
        self.context = {}  # Store data between steps

    def generate_execution_plan(self, task_description: str) -> List[Dict[str, Any]]:
        """
        Use LLM to generate a step-by-step execution plan for the task.
        """
        system_prompt = """
You are an expert data analyst. Given a task description, break it down into specific, executable steps.

Available tools and their capabilities:
1. scrape_web_data(url) - Scrape data from websites, especially tables
2. scrape_wikipedia_table(url, table_index) - Specifically for Wikipedia tables
3. clean_monetary_values(df, column) - Clean currency columns
4. clean_year_column(df, column) - Extract years from text columns
5. analyze_data(df, analysis_type, **kwargs) - Various analysis operations:
   - "count_condition": Count rows matching a condition
   - "filter_and_count": Count rows matching multiple conditions (use 'filters' parameter)
   - "filter_sort_select": Filter, sort, and select specific rows (use 'select_column' not 'select_columns', use 'sort_by' not 'sort_column')
   - "correlation": Calculate correlation between two columns (use 'col1' and 'col2' not 'column1' and 'column2')
   - "regression": Calculate regression statistics
   - "date_difference_regression": Regression of date differences (for court cases)
   - "top_by_count": Find top items by count (e.g., "which court disposed most cases")
6. create_visualization(df, plot_type, **kwargs) - Create plots as base64 images:
   - "scatter_with_regression": Scatter plot with regression line
   - "time_series": Time series plot
   - "bar": Bar chart
7. query_duckdb(query) - Execute DuckDB queries (ONLY for S3/remote data)
8. calculate_date_difference(df, date1_col, date2_col, unit) - Calculate date differences
9. group_and_aggregate(df, group_by, agg_col, agg_func) - Group and aggregate data

For each step, provide:
1. action: The tool/function to use
2. parameters: Dictionary of parameters for the tool
3. description: Human-readable description of what this step does
4. data_key: Key to store the result in context (e.g., "movies_data", "analysis_result")

Return ONLY a JSON array of steps. Example format:
[
  {
    "action": "scrape_wikipedia_table",
    "parameters": {"url": "https://example.com", "table_index": 0},
    "description": "Scrape the main table from Wikipedia",
    "data_key": "raw_data"
  },
  {
    "action": "clean_monetary_values", 
    "parameters": {"df": "raw_data", "column": "Worldwide gross"},
    "description": "Clean monetary values in the gross column",
    "data_key": "cleaned_data"
  }
]

Important notes:
- When referencing previously loaded data, use the data_key as string (e.g., "raw_data")
- For visualization, always use appropriate plot types (scatter_with_regression, time_series, bar)
- For analysis, specify the exact analysis_type and required parameters
- Think about data cleaning needs (monetary values, years, etc.)
- Consider what format the final answer should be in (JSON array or object)
- Use pandas DataFrames for web-scraped data, NOT DuckDB
- Only use DuckDB for remote datasets (S3, parquet files, etc.)
- The system should work with ANY dataset and ANY column names
- Handle mixed data types automatically (numbers, text, dates)
- For visualization, use 'x_col' and 'y_col' parameters, not 'x' and 'y'
- Generate analysis based on the actual data structure, not assumptions
 - For DuckDB date calculations, prefer DATEDIFF('day', CAST(date1 AS DATE), CAST(date2 AS DATE)) with explicit type casting
 - For non-ISO date formats in DuckDB, use STRPTIME(date_string, '%d-%m-%Y') or an appropriate format string to convert to DATE
"""

        prompt = (
            f"{system_prompt}\n\nTask: {task_description}\n\nGenerate execution plan:"
        )
        try:
            response = self.model.generate_content(prompt)
            plan_text = response.text
            json_match = re.search(r"\[.*\]", plan_text, re.DOTALL)
            if json_match:
                plan_json = json_match.group()
                plan = json.loads(plan_json)
                return plan
            else:
                return json.loads(plan_text)
        except Exception as e:
            print(f"Error generating plan: {e}")
            return [
                {
                    "action": "error",
                    "parameters": {},
                    "description": f"Failed to generate plan: {str(e)}",
                    "data_key": "error",
                }
            ]

    def execute_step(self, step: Dict[str, Any]) -> Any:
        """
        Execute a single step from the execution plan.
        """
        action = step.get("action")
        parameters = step.get("parameters", {})
        description = step.get("description", "")
        try:
            processed_params = {}
            for key, value in parameters.items():
                if isinstance(value, str) and value in self.context:
                    processed_params[key] = self.context[value]
                    print(
                        f"  Using context data for {key}: {type(self.context[value]).__name__}"
                    )
                else:
                    processed_params[key] = value

            print(f"Executing: {description}")
            print(f"  Action: {action}")
            print(f"  Parameters: {processed_params}")

            if action == "scrape_web_data":
                result = self.tools.scrape_web_data(**processed_params)
            elif action == "scrape_wikipedia_table":
                result = self.tools.scrape_wikipedia_table(**processed_params)
            elif action == "clean_monetary_values":
                df = processed_params.pop("df")
                result = self.tools.clean_monetary_values(df, **processed_params)
            elif action == "clean_year_column":
                df = processed_params.pop("df")
                result = self.tools.clean_year_column(df, **processed_params)
            elif action == "analyze_data":
                df = processed_params.pop("df")
                result = self.tools.analyze_data(df, **processed_params)
            elif action == "create_visualization":
                df = processed_params.pop("df")
                result = self.tools.create_visualization(df, **processed_params)
            elif action == "query_duckdb":
                result = self.tools.query_duckdb(**processed_params)
            elif action == "calculate_date_difference":
                df = processed_params.pop("df")
                result = self.tools.calculate_date_difference(df, **processed_params)
            elif action == "group_and_aggregate":
                df = processed_params.pop("df")
                # Fallback for missing group_by
                if (
                    "group_by" not in processed_params
                    or not processed_params["group_by"]
                ):
                    processed_params["group_by"] = None
                result = self.tools.group_and_aggregate(df, **processed_params)
            elif action == "custom_analysis":
                result = self.execute_custom_analysis(processed_params)
            else:
                result = {"error": f"Unknown action: {action}"}
            return result
        except Exception as e:
            error_msg = f"Error executing {action}: {str(e)}"
            print(error_msg)
            traceback.print_exc()
            return {"error": error_msg}

    def execute_custom_analysis(self, parameters: Dict) -> Any:
        """
        For complex analysis that requires custom code generation.
        """
        try:
            df = parameters.get("df")
            analysis_description = parameters.get("description", "")
            if "correlation" in analysis_description.lower():
                numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
                if len(numeric_cols) >= 2:
                    return self.tools.analyze_data(
                        df, "correlation", col1=numeric_cols[0], col2=numeric_cols[1]
                    )
            return {
                "result": "Custom analysis completed",
                "description": analysis_description,
            }
        except Exception as e:
            return {"error": f"Custom analysis failed: {str(e)}"}

    def format_final_answer(
        self, task_description: str, results: List[Any]
    ) -> Union[List, Dict]:
        """
        Use LLM to format the final answer based on the task requirements.
        """
        results_summary = []
        for i, result in enumerate(results):
            if isinstance(result, pd.DataFrame):
                summary = f"Step {i+1}: DataFrame with {len(result)} rows, columns: {list(result.columns)[:5]}"
                if len(result) > 0:
                    summary += f"\nSample data: {result.head(2).to_dict()}"
            elif isinstance(result, dict) and "error" not in result:
                summary = f"Step {i+1}: Analysis result: {result}"
            elif isinstance(result, (int, float, str)):
                summary = f"Step {i+1}: {result}"
            else:
                summary = f"Step {i+1}: {type(result).__name__}"
            results_summary.append(summary)

        format_prompt = f"""
Given the task and execution results, format the final answer according to the task requirements.

Task: {task_description}

Execution Results:
{chr(10).join(results_summary)}

Available context data keys: {list(self.context.keys())}

Context Data Details:
"""

        for key, value in self.context.items():
            if key.startswith("q") and key[1].isdigit():
                format_prompt += f"\n{key}: {type(value).__name__}"
                if isinstance(value, pd.DataFrame):
                    format_prompt += f" - DataFrame with {len(value)} rows, columns: {list(value.columns)}"
                    if len(value) > 0:
                        format_prompt += (
                            f"\n  Sample data: {value.head(1).to_dict('records')}"
                        )
                elif isinstance(value, dict):
                    format_prompt += f" - Dict: {value}"
                elif isinstance(value, str) and value.startswith("data:image"):
                    format_prompt += (
                        f" - Base64 image data available (length: {len(value)} chars)"
                    )
                else:
                    format_prompt += f" - Value: {value}"

        format_prompt += f"""

Rules:
1. If the task asks for a JSON array, return an array with answers in order (q1, q2, q3, q4)
2. If the task asks for a JSON object, return an object  
3. Include all requested information in the specified format
4. For visualizations, use the base64 data URI format - the image data is already available in the context
5. For numerical answers, ensure they are properly typed (int/float)
6. If there are multiple questions, answer them in order
7. For DataFrame results, extract the actual answer value (count, name, correlation, etc.)
8. For correlation results, use the correlation value from the dict
9. Do NOT include the actual base64 image data in your response - just reference that it's available

Return ONLY the final formatted answer as valid JSON.
"""

        try:
            response = self.model.generate_content(format_prompt)
            answer_text = response.text.strip()
            json_match = re.search(r"(\[.*\]|\{.*\})", answer_text, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                return json.loads(json_str)
            else:
                return json.loads(answer_text)
        except Exception as e:
            print(f"Error formatting answer: {e}")
            print("Falling back to manual answer extraction...")
            return self.extract_answers_from_context(task_description)

    def extract_answers_from_context(self, task_description: str) -> Union[List, Dict]:
        """
        Generic extraction of answers from context for any question type or format.
        """
        try:
            print(f"DEBUG: Available context keys: {list(self.context.keys())}")
            if "JSON array" in task_description:
                answers = []
                question_keys = [
                    key
                    for key in self.context.keys()
                    if key.startswith("q") and key[1].isdigit()
                ]
                question_keys.sort()
                print(f"DEBUG: Found question keys: {question_keys}")
                for key in question_keys:
                    value = self.context[key]
                    print(f"DEBUG: Processing {key}: {type(value)} = {value}")
                    if isinstance(value, pd.DataFrame):
                        if len(value) > 0:
                            if "count" in value.columns:
                                answers.append(int(value["count"].iloc[0]))
                            elif len(value.columns) == 1:
                                answers.append(value.iloc[0, 0])
                            else:
                                # Return first row as a simple scalar if possible, else as dict
                                first_row = value.iloc[0]
                                scalar_cols = [
                                    c
                                    for c in value.columns
                                    if pd.api.types.is_numeric_dtype(value[c])
                                ]
                                if scalar_cols:
                                    answers.append(first_row[scalar_cols[0]])
                                else:
                                    answers.append(first_row.to_dict())
                        else:
                            answers.append("No data found")
                    elif isinstance(value, dict):
                        if any(
                            k in value
                            for k in ["correlation", "slope", "p_value", "r_value"]
                        ):
                            # Prefer a primary numeric metric if present
                            for primary in [
                                "correlation",
                                "slope",
                                "p_value",
                                "r_value",
                            ]:
                                if primary in value and isinstance(
                                    value[primary], (int, float)
                                ):
                                    answers.append(round(value[primary], 6))
                                    break
                            else:
                                answers.append(
                                    {
                                        k: (
                                            round(v, 6)
                                            if isinstance(v, (int, float))
                                            else v
                                        )
                                        for k, v in value.items()
                                    }
                                )
                        elif "error" in value:
                            answers.append(f"Error: {value['error']}")
                        else:
                            answers.append(value)
                    elif isinstance(value, (int, float)):
                        answers.append(value)
                    elif value is None:
                        answers.append("No data found")
                    elif isinstance(value, str) and value.startswith("data:image"):
                        answers.append(value)
                    else:
                        answers.append(value)
                print(f"DEBUG: Final answers array: {answers}")
                return answers

            elif "JSON object" in task_description:
                # Generic extraction without assuming specific column names
                result_obj = {}
                lines = task_description.split("\n")
                questions = []
                for line in lines:
                    if line.strip().startswith('"') and line.strip().endswith('":'):
                        question = line.strip()[1:-3]
                        questions.append(question)
                for i, question in enumerate(questions):
                    possible_keys = [
                        f"answer_{i}",
                        f"step_{i}_result",
                        f"q{i+1}_result",
                    ]
                    extracted = False
                    for key in possible_keys:
                        if key in self.context:
                            value = self.context[key]
                            if isinstance(value, pd.DataFrame):
                                if len(value) > 0:
                                    result_obj[question] = value.iloc[0].to_dict()
                                else:
                                    result_obj[question] = "No data found"
                            elif isinstance(value, dict):
                                if "error" in value:
                                    result_obj[question] = f"Error: {value['error']}"
                                elif any(
                                    k in value
                                    for k in [
                                        "correlation",
                                        "slope",
                                        "p_value",
                                        "r_value",
                                    ]
                                ):
                                    # Keep numeric analysis values as-is with rounding where sensible
                                    out = {}
                                    for k, v in value.items():
                                        out[k] = (
                                            round(v, 6)
                                            if isinstance(v, (int, float))
                                            else v
                                        )
                                    result_obj[question] = (
                                        out
                                        if len(out) > 1
                                        else next(iter(out.values()))
                                    )
                                else:
                                    result_obj[question] = value
                            elif isinstance(value, str) and value.startswith(
                                "data:image"
                            ):
                                result_obj[question] = value
                            else:
                                result_obj[question] = value
                            extracted = True
                            break
                    if not extracted:
                        result_obj[question] = "No data found"
                return result_obj if result_obj else self.context

            for key in reversed(list(self.context.keys())):
                value = self.context[key]
                if not isinstance(value, dict) or "error" not in value:
                    return value

            # Generic best-effort extraction: return the last non-error value from context
            result_obj = {}
            for key, value in self.context.items():
                if isinstance(value, pd.DataFrame) and len(value) > 0:
                    result_obj[key] = value.head(1).to_dict("records")[0]
                elif isinstance(value, dict) and "error" not in value:
                    # Round numeric scalars inside dicts for readability
                    rounded = {
                        k: (round(v, 6) if isinstance(v, (int, float)) else v)
                        for k, v in value.items()
                    }
                    result_obj[key] = rounded
                elif isinstance(value, str) and value.startswith("data:image"):
                    result_obj[key] = value
                elif not isinstance(value, dict) or "error" not in value:
                    result_obj[key] = value
            return (
                result_obj
                if result_obj
                else {"error": "Could not extract answers from context"}
            )
        except Exception as e:
            print(f"DEBUG: Error in extract_answers_from_context: {e}")
            return {"error": f"Failed to extract answers: {str(e)}"}

    def process_task(self, task_description: str) -> Union[List, Dict]:
        """
        Main method to process a data analysis task.
        """
        try:
            print(f"Processing task: {task_description[:100]}...")
            self.reset_context()
            plan = self.generate_execution_plan(task_description)
            print(f"Generated plan with {len(plan)} steps")
            results = []
            for i, step in enumerate(plan):
                print(
                    f"\nStep {i+1}/{len(plan)}: {step.get('description', 'No description')}"
                )
                result = self.execute_step(step)
                results.append(result)
                data_key = step.get("data_key")
                if data_key:
                    self.context[data_key] = result
                self.context[f"step_{i}_result"] = result
                print(f"Step {i+1} completed. Result type: {type(result).__name__}")
                if isinstance(result, pd.DataFrame):
                    print(
                        f"  DataFrame shape: {result.shape}, columns: {list(result.columns)}"
                    )
                    if len(result) > 0:
                        print(f"  Sample data: {result.head(1).to_dict('records')}")
                elif isinstance(result, dict):
                    print(f"  Dict keys: {list(result.keys())}")
                elif isinstance(result, str) and result.startswith("data:image"):
                    print(f"  Base64 image length: {len(result)}")
                else:
                    print(f"  Result value: {result}")
            print(f"\nAll steps completed. Context keys: {list(self.context.keys())}")
            has_base64_images = any(
                isinstance(value, str) and value.startswith("data:image")
                for value in self.context.values()
            )
            if has_base64_images:
                print(
                    "Detected base64 images in context, using manual extraction to avoid LLM API issues..."
                )
                final_answer = self.extract_answers_from_context(task_description)
                print(
                    f"Manual extraction result: {type(final_answer)} = {final_answer}"
                )
                return final_answer
            try:
                print("Attempting LLM-based answer formatting...")
                final_answer = self.format_final_answer(task_description, results)
                print(f"LLM formatting result: {type(final_answer)} = {final_answer}")
                return final_answer
            except Exception as e:
                print(f"LLM formatting failed: {e}")
                print("Falling back to manual extraction...")
                final_answer = self.extract_answers_from_context(task_description)
                print(
                    f"Manual extraction result: {type(final_answer)} = {final_answer}"
                )
                return final_answer
        except Exception as e:
            error_msg = f"Task processing failed: {str(e)}"
            print(error_msg)
            traceback.print_exc()
            return {"error": error_msg}

    def reset_context(self):
        """
        Clear the context for a new task.
        """
        self.context = {}
