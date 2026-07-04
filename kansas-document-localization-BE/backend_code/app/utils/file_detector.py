def detect_file_type(filename: str) -> str:
    extension = filename.lower().split(".")[-1]

    if extension == "pdf":
        return "pdf"
    elif extension == "docx":
        return "docx"
    elif extension == "xdp":
        return "xdp"

    raise ValueError(f"Unsupported file type: {extension}")