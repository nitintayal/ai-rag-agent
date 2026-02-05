from pathlib import Path

def load_text_documents(folder_path: str):
    documents = []

    folder = Path(folder_path)
    for file in folder.glob("*.txt"):
        with open(file, "r", encoding="utf-8") as f:
            content = f.read()
            documents.append({
                "source": file.name,
                "content": content
            })

    return documents
