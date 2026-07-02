import pytest
from app.services.resume_parser import ResumeParser
import os
import tempfile

@pytest.fixture
def resume_parser():
    return ResumeParser()

def test_resume_parser_empty_text(resume_parser):
    """Test the parser doesn't crash on empty text."""
    result = resume_parser._parse_text("")
    assert isinstance(result, dict)
    assert "skills" in result
    assert "experience" in result

def test_resume_parser_basic_text(resume_parser):
    """Test basic keyword extraction from raw text."""
    text = "Jane Doe\njane@example.com\nSkills: Python, Docker, React\nExperience: 5 years software engineer."
    result = resume_parser._parse_text(text)
    
    assert result["email"] == "jane@example.com"
    # Basic skill extraction should pick up python and react
    # (Note: exact keys depend on the keyword extractor, but it should be a dict/list)
    assert isinstance(result["skills"], (dict, list))
    assert result["total_years_experience"] is not None

def test_resume_parser_invalid_file(resume_parser):
    """Test parsing an invalid file raises exception."""
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        f.write(b"Not a real PDF")
        temp_path = f.name
    
    try:
        with pytest.raises(Exception):
            resume_parser.parse(temp_path, "pdf")
    finally:
        os.unlink(temp_path)
