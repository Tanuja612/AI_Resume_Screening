"""
Resume validation module to ensure uploaded files are actually resumes.
Returns validation results and handles non-resume PDFs with 0 score.
"""

import re
import os
from typing import Dict, Tuple

# Common resume section headers - these indicate a resume document
RESUME_SECTION_KEYWORDS = {
    "experience", "work experience", "employment", "professional experience",
    "education", "skills", "certifications", "projects", "achievements",
    "summary", "objective", "technical skills", "core competencies",
    "languages", "awards", "publications"
}

# Resume-related keywords - documents should contain some of these
RESUME_CONTENT_KEYWORDS = {
    "responsible", "developed", "implemented", "managed", "led",
    "designed", "engineered", "coordinated", "collaborated",
    "bachelor", "master", "phd", "diploma", "certification",
    "proficiency", "expert", "intermediate", "proficient"
}

# Non-resume document indicators - if a document has these, it's likely NOT a resume
NON_RESUME_INDICATORS = {
    "chapter", "section", "introduction", "abstract", "methodology",
    "literature review", "references", "appendix", "table of contents",
    "please note", "disclaimer", "terms and conditions", "privacy policy"
}


def is_valid_resume_content(text: str) -> Tuple[bool, Dict]:
    """
    Determine if extracted text looks like a resume.
    
    Returns:
        Tuple of (is_valid_resume: bool, analysis_dict: dict)
    """
    
    if not text or not text.strip():
        return False, {
            "reason": "No extractable text",
            "text_length": 0,
            "has_sections": False,
            "has_content_keywords": False,
            "is_non_resume": False
        }
    
    text_lower = text.lower()
    words = text.split()
    text_length = len(words)
    
    # Check for resume section headers
    has_sections = any(section in text_lower for section in RESUME_SECTION_KEYWORDS)
    
    # Check for resume-related content
    content_matches = sum(1 for keyword in RESUME_CONTENT_KEYWORDS if keyword in text_lower)
    has_content_keywords = content_matches >= 2  # Need at least 2 matches
    
    # Check for non-resume document patterns
    non_resume_matches = sum(1 for indicator in NON_RESUME_INDICATORS if indicator in text_lower)
    is_non_resume = non_resume_matches >= 3  # If too many indicators, likely not a resume
    
    # Resume validation logic:
    # 1. Must have extractable text
    # 2. Must be a reasonable length (100+ words)
    # 3. Must have resume-like sections OR content keywords
    # 4. Should NOT look like a book/article/policy document
    
    is_valid = (
        text_length >= 100 and  # Minimum length for a resume
        (has_sections or has_content_keywords) and  # Resume characteristics
        not is_non_resume  # Not a non-resume document
    )
    
    return is_valid, {
        "reason": _get_validation_reason(is_valid, text_length, has_sections, 
                                        has_content_keywords, is_non_resume),
        "text_length": text_length,
        "has_sections": has_sections,
        "has_content_keywords": has_content_keywords,
        "is_non_resume": is_non_resume,
        "content_keyword_matches": content_matches
    }


def _get_validation_reason(is_valid: bool, length: int, has_sections: bool, 
                          has_keywords: bool, is_non_resume: bool) -> str:
    """Generate a human-readable reason for validation result."""
    
    if is_valid:
        return "Valid resume document detected"
    
    reasons = []
    
    if length < 100:
        reasons.append(f"Text too short ({length} words, need 100+)")
    
    if not has_sections and not has_keywords:
        reasons.append("No resume characteristics detected (missing sections and content keywords)")
    
    if is_non_resume:
        reasons.append("Document appears to be a book/article/policy (not a resume)")
    
    return "; ".join(reasons) if reasons else "Not a valid resume"


def validate_resume_file(file_path: str, extracted_text: str = None) -> Dict:
    """
    Comprehensive resume validation for a file.
    
    Args:
        file_path: Path to the resume file
        extracted_text: Pre-extracted text (optional, will extract if not provided)
    
    Returns:
        Dictionary with validation results and scoring info
    """
    
    from nlp.text_extraction import extract_text_from_pdf
    from nlp.ats_analysis import extract_plain_text
    
    result = {
        "file_path": file_path,
        "is_valid_resume": False,
        "confidence_score": 0,
        "validation_details": None,
        "error_message": None
    }
    
    try:
        # Extract text if not provided
        if extracted_text is None:
            # Try pdfplumber first (faster for PDFs)
            if file_path.lower().endswith('.pdf'):
                try:
                    extracted_text = extract_text_from_pdf(file_path)
                except Exception:
                    extracted_text = None
            
            # Fallback to pdfminer
            if extracted_text is None:
                extracted_text = extract_plain_text(file_path)
        
        if not extracted_text:
            result["error_message"] = "Could not extract text from file"
            return result
        
        # Validate content
        is_valid, validation_details = is_valid_resume_content(extracted_text)
        result["is_valid_resume"] = is_valid
        result["validation_details"] = validation_details
        
        # Calculate confidence score (0-100)
        if is_valid:
            result["confidence_score"] = 85  # High confidence for valid resumes
        else:
            result["confidence_score"] = 0  # Invalid = 0 score
        
    except Exception as e:
        result["error_message"] = f"Error validating file: {str(e)}"
        result["confidence_score"] = 0
    
    return result
