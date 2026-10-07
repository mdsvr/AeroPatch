import pytest
from app.library_loans import read_loan_record, write_loan_record, list_loan_records, delete_loan_record

def test_read_existing_file(tmp_path):
    """Test reading a normal file inside the base directory."""
    test_file = tmp_path / 'loan_001.txt'
    test_file.write_text('BOOK: 123')
    
    content = read_loan_record(str(tmp_path), 'loan_001.txt')
    assert content == 'BOOK: 123'


def test_list_files_in_directory(tmp_path):
    """Test listing files in a directory with mixed contents."""
    file1 = tmp_path / 'file1.txt'
    file2 = tmp_path / 'file2.txt'
    file1.write_text('content 1')
    file2.write_text('content 2')
    
    files = list_loan_records(str(tmp_path))
    assert set(files) == {'file1.txt', 'file2.txt'}

def test_delete_existing_file(tmp_path):
    """Test deleting a file inside the base directory."""
    to_delete = tmp_path / 'delete_me.txt'
    to_delete.write_text('TO BE DELETED')
    
    result = delete_loan_record(str(tmp_path), 'delete_me.txt')
    assert result is True
    
    with pytest.raises(FileNotFoundError):
        read_loan_record(str(tmp_path), 'delete_me.txt')

def test_delete_nonexistent_file(tmp_path):
    """Test deleting a file that does not exist."""
    result = delete_loan_record(str(tmp_path), 'does_not_exist.txt')
    assert result is False

def test_read_special_characters_in_name(tmp_path):
    """Test reading a file with special characters in the name."""
    safe_name = 'loan_file-with_dots.txt'
    content = 'DATA FOR FILE'
    
    write_loan_record(str(tmp_path), safe_name, content)
    result = read_loan_record(str(tmp_path), safe_name)
    assert result == content
