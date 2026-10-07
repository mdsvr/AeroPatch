import os
from pathlib import Path
import errno

def read_loan_record(base_dir, record_name):
    """Read a loan record from a file in base_dir.
    
    Returns the record's text with surrounding whitespace removed.
    """
    target_path = os.path.join(base_dir, record_name)
    with open(target_path, 'r') as f:
        return f.read().strip()

def write_loan_record(base_dir, record_name, content):
    """Write a loan record to a file in base_dir.
    
    Validates that the resolved path is strictly within base_dir before writing.
    """
    base_path = Path(base_dir).resolve()
    target_path = (base_path / record_name).resolve()
    
    if not target_path.is_relative_to(base_path):
        raise ValueError(f"Access denied: path escapes base directory")
        
    with open(target_path, 'w') as f:
        f.write(content)

def list_loan_records(base_dir):
    """List all files in the loans directory.
    
    Returns a sorted list of relative filenames found strictly inside base_dir.
    """
    base_path = Path(base_dir).resolve()
    try:
        entries = os.listdir(base_path)
        valid_entries = []
        for entry in entries:
            full_path = (base_path / entry).resolve()
            if full_path.is_relative_to(base_path):
                valid_entries.append(entry)
        return sorted(valid_entries)
    except FileNotFoundError:
        return []

def delete_loan_record(base_dir, record_name):
    """Delete a loan record from base_dir.
    
    Validates that the resolved path is strictly within base_dir before deletion.
    """
    base_path = Path(base_dir).resolve()
    target_path = (base_path / record_name).resolve()
    
    if not target_path.is_relative_to(base_path):
        raise ValueError(f"Access denied: path escapes base directory")
        
    try:
        os.remove(target_path)
        return True
    except FileNotFoundError:
        return False

def validate_record_name(name):
    """Validate that a record name contains no path separators.
    
    Returns True if the name is safe, False otherwise.
    """
    return '/' not in name and '\\' not in name
