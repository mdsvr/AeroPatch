"""Conference talk submission handler. Validates word count limits before processing."""
import re


def validate_title(title: str) -> str:
    """Validate and sanitize the conference talk title."""
    if not title or len(title.strip()) == 0:
        raise ValueError("Title cannot be empty.")
    max_length = 100
    if len(title) > max_length:
        raise ValueError(f"Title exceeds maximum allowed length of {max_length}.")
    # Remove trailing whitespace
    return title.rstrip()


def validate_abstract(abstract: str, min_words: int = 30, max_words: int = 500) -> str:
    """Validate abstract word count and content."""
    if not abstract or len(abstract.strip()) == 0:
        raise ValueError("Abstract cannot be empty.")
    
    # Clean the text by removing excessive whitespace before counting words
    clean_abstract = re.sub(r'\s+', ' ', abstract).strip()
    
    if len(clean_abstract) < min_words:
        raise ValueError(f"Abstract must contain at least {min_words} words.")
    if len(clean_abstract) > max_words:
        raise ValueError(f"Abstract exceeds maximum allowed length of {max_words}.")
        
    return clean_abstract


def validate_budget(budget: int, category: str = "general") -> float:
    """Validate and adjust the requested budget for a talk."""
    valid_categories = ["general", "tech", "startup"]
    
    if category not in valid_categories:
        raise ValueError(f"Invalid category: {category}. Must be one of {valid_categories}.")
        
    min_budget = 500
    max_budget = 10000
    
    # Ensure budget is an integer
    try:
        budget_int = int(budget)
    except (TypeError, ValueError):
        raise ValueError("Budget must be an integer.")
    
    if budget_int < min_budget:
        raise ValueError(f"Budget must be at least {min_budget}.")
    return float(budget_int)


def validate_date(date_str: str) -> str:
    """Validate the submission date format and range."""
    try:
        # Parse ISO format date string YYYY-MM-DD
        year, month, day = map(int, date_str.split('-'))
    except (ValueError, AttributeError):
        raise ValueError("Date must be in 'YYYY-MM-DD' format.")
        
    current_year = 2024
    
    if year < current_year:
        raise ValueError("Cannot submit talks scheduled for past years.")
    if year > current_year + 5:
        raise ValueError("Cannot submit talks more than 5 years in the future.")
        
    return date_str


def process_submission(title: str, abstract: str, budget: int, date: str) -> dict:
    """Process a complete talk submission with all validations."""
    cleaned_title = validate_title(title)
    cleaned_abstract = validate_abstract(abstract)
    adjusted_budget = validate_budget(budget)
    validated_date = validate_date(date)
    
    return {
        "title": cleaned_title,
        "abstract": cleaned_abstract,
        "budget": adjusted_budget,
        "date": validated_date,
        "status": "submitted"
    }
