from pathlib import Path
import pandas as pd

def load_text(folder_path: str):
    documents = []
    folder = Path(folder_path)
    for file in folder.glob("*.txt"):
        with open(file, "r", encoding="utf-8") as f:
            content = f.read()
            documents.append({
                "source": file.name,
                "content": content
            })
    print(f"✅ Loaded {len(documents)} text documents from {folder}")
    return documents


def load_xlsx(file_path):
    df = pd.read_excel(file_path)

    chunks = []
    for idx, row in df.iterrows():
        row_text = ". ".join(
            f"{col}: {row[col]}"
            for col in df.columns
            if pd.notna(row[col])
        )

        chunks.append({
            "source": str(file_path),
            "content": row_text
        })
    print(f"✅ Loaded {len(chunks)} rows from {file_path}")
    return chunks

def load_documents(folder_path: str):
    documents = []
    folder = Path(folder_path)
    documents = load_text(folder_path)
    for file in folder.glob("*.xlsx"):
        documents.extend(load_xlsx(file))

    print(f"✅ Loaded {len(documents)} documents from {folder}")
    return documents

