import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from io import StringIO

st.set_page_config(page_title="🧠 Data Analyst Agent")

st.title("🧠 Data Analyst Agent")
st.write("Upload your CSV file and get instant analysis!")

uploaded_file = st.file_uploader("Upload a CSV file", type=["csv"])

if uploaded_file is not None:
    # Load the data
    try:
        df = pd.read_csv(uploaded_file)
        st.success("File successfully loaded!")
    except Exception as e:
        st.error(f"Error reading file: {e}")
        st.stop()

    st.subheader("📊 Basic Data Overview")
    st.write("**Shape:**", df.shape)
    st.write("**Columns:**", df.columns.tolist())
    st.write("**Missing Values:**")
    st.write(df.isnull().sum())

    st.subheader("📈 Correlation Heatmap")
    try:
        numeric_df = df.select_dtypes(include='number')
        corr = numeric_df.corr()

        fig, ax = plt.subplots()
        sns.heatmap(corr, annot=True, cmap="coolwarm", ax=ax)
        st.pyplot(fig)
    except Exception as e:
        st.warning(f"Could not plot heatmap: {e}")

    st.subheader("❓ Ask a Data Question")

    user_question = st.text_input("Ask a question about your data (e.g., 'average age', 'max salary'):")

    if user_question:
        try:
            question = user_question.lower()

            if "average" in question or "mean" in question:
                for col in df.columns:
                    if col.lower() in question and pd.api.types.is_numeric_dtype(df[col]):
                        st.write(f"Average of `{col}`:", df[col].mean())
                        break
                else:
                    st.warning("Could not match column for average.")

            elif "max" in question:
                for col in df.columns:
                    if col.lower() in question and pd.api.types.is_numeric_dtype(df[col]):
                        st.write(f"Maximum of `{col}`:", df[col].max())
                        break
                else:
                    st.warning("Could not match column for max.")

            elif "min" in question:
                for col in df.columns:
                    if col.lower() in question and pd.api.types.is_numeric_dtype(df[col]):
                        st.write(f"Minimum of `{col}`:", df[col].min())
                        break
                else:
                    st.warning("Could not match column for min.")

            elif "unique" in question:
                for col in df.columns:
                    if col.lower() in question:
                        st.write(f"Unique values in `{col}`:", df[col].nunique())
                        break
                else:
                    st.warning("Could not match column for unique values.")

            else:
                st.info("Try asking about average, max, min, or unique values.")

        except Exception as e:
            st.error(f"Error processing question: {e}")

    st.subheader("🔍 Quick Column Summary")
    selected_col = st.selectbox("Select a column to analyze", df.columns)
    st.write("Data Type:", df[selected_col].dtype)
    st.write("Unique Values:", df[selected_col].nunique())
    st.write("Sample Data:", df[selected_col].sample(5))
    