from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse
import uvicorn
from sentence_transformers import SentenceTransformer, util
import requests
model = SentenceTransformer('all-MiniLM-L6-v2')

app = FastAPI()

@app.post("/api/")
async def analyze_file(file: UploadFile = File(...)):
    if not file.filename.endswith(".txt"):
        return JSONResponse(status_code=400, content={"error": "Only .txt files allowed."})
    
    try:
        import pandas as pd

        content = await file.read()
        task_text = content.decode("utf-8").strip().lower()

        # Load a fixed sample dataset
        df = pd.read_csv("data/sample.csv")  # Make sure this file exists

        import re

        def get_closest_column(task, columns):
            # Use SentenceTransformer embeddings to find the closest column
            task_embedding = model.encode(task, convert_to_tensor=True)
            column_embeddings = model.encode(columns, convert_to_tensor=True)
            similarities = util.pytorch_cos_sim(task_embedding, column_embeddings)[0]
            best_idx = similarities.argmax().item()
            return columns[best_idx]

        results = {}
        lines = task_text.strip().split("\n")
        numeric_cols = df.select_dtypes(include='number').columns

        for line in lines:
            line = line.strip()
            answer = None

            if "average" in line or "mean" in line:
                col = get_closest_column(line, numeric_cols)
                if col:
                    answer = df[col].mean()

            elif "max" in line:
                col = get_closest_column(line, numeric_cols)
                if col:
                    answer = df[col].max()

            elif "min" in line:
                col = get_closest_column(line, numeric_cols)
                if col:
                    answer = df[col].min()

            else:
                answer = "Unsupported query"

            results[line] = answer

        clean_results = {}
        for question, value in results.items():
            if hasattr(value, "item"):  # for NumPy int64/float64
                clean_results[question] = value.item()
            else:
                clean_results[question] = value

        return JSONResponse(content={
            "questions": lines,
            "results": clean_results
        })

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

if __name__ == "__main__":
    uvicorn.run("fastapi_app:app", host="0.0.0.0", port=8000)