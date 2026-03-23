def process_jd_file_placeholder(file_url: str) -> dict:
    """
    Dummy placeholder utility for future JD parsing/processing.

    Right now it does nothing meaningful, as requested.
    Later this can:
    - parse PDF
    - extract text
    - generate embeddings
    - map JD skills to employee role expectations
    """

    return {
        "status": "success",
        "message": "JD file received. Processing is currently a placeholder.",
        "file_url": file_url,
    }