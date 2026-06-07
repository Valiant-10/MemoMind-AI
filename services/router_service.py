def is_pdf_request(user_input: str) -> bool:
    """
    Checks if the user's input asks about the PDF document.
    """
    pdf_keywords = [
        "pdf",
        "document",
        "uploaded file",
        "from the pdf",
        "from the document",
        "in the pdf",
        "in the document",
        "according to the pdf",
        "according to the document"
    ]
    user_input = user_input.lower()
    return any(keyword in user_input for keyword in pdf_keywords)


def is_summary_request(user_input: str) -> bool:
    """
    Checks if the user's input asks for a summary of the PDF document.
    """
    summary_keywords = [
        "summarize",
        "summary",
        "summarise",
        "give summary",
        "brief summary",
        "overview",
        "summarize pdf",
        "summarize document"
    ]
    user_input = user_input.lower()
    return any(keyword in user_input for keyword in summary_keywords)


def route_request(user_input: str, has_documents: bool) -> str:
    """
    Routes the request to 'summary', 'pdf', or 'normal' based on user input and documents status.
    """
    if is_summary_request(user_input) and has_documents:
        return "summary"
    elif is_pdf_request(user_input) and has_documents:
        return "pdf"
    else:
        return "normal"
