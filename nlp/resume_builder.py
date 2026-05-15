"""
Resume Builder Module - Creates professional resumes from templates.
Supports multiple resume formats and styles for ATS compatibility.
"""

from datetime import datetime
import os
import json

# Pre-defined resume templates
RESUME_TEMPLATES = {
    "professional": {
        "name": "Professional Resume",
        "description": "Classic professional format - ATS friendly",
        "format": """
{name}
{email} | {phone}{location}{social_links}

PROFESSIONAL SUMMARY
{summary}

CORE COMPETENCIES
{skills}

PROFESSIONAL EXPERIENCE
{experience}

PROJECTS
{projects}

EDUCATION
{education}

CERTIFICATIONS & AWARDS
{certifications}
"""
    },
    "chronological": {
        "name": "Chronological Resume",
        "description": "Focus on work history and progression",
        "format": """
{name}
{email} | {phone} | {location}{social_links}

OBJECTIVE
{objective}

WORK EXPERIENCE
{experience}

PROJECTS
{projects}

TECHNICAL SKILLS
{skills}

EDUCATION
{education}

ADDITIONAL INFORMATION
{additional}
"""
    },
    "functional": {
        "name": "Functional Resume",
        "description": "Emphasize skills and achievements over chronology",
        "format": """
{name}
{email} | {phone}{social_links}

PROFESSIONAL SUMMARY
{summary}

KEY SKILLS & ACHIEVEMENTS
{skills}
{experience}

PROJECTS
{projects}

WORK HISTORY
{work_history}

EDUCATION
{education}
"""
    },
    "modern": {
        "name": "Modern ATS Resume",
        "description": "Clean, simple format optimized for ATS systems",
        "format": """
{name}
{location}
{email} | {phone}{social_links}

PROFILE
{summary}

SKILLS
{skills}

EXPERIENCE
{experience}

PROJECTS
{projects}

EDUCATION
{education}

LANGUAGES
{languages}
"""
    }
}

def get_available_templates():
    """Return list of available resume templates."""
    return [
        {"id": "professional", "name": RESUME_TEMPLATES["professional"]["name"], "description": RESUME_TEMPLATES["professional"]["description"]},
        {"id": "chronological", "name": RESUME_TEMPLATES["chronological"]["name"], "description": RESUME_TEMPLATES["chronological"]["description"]},
        {"id": "functional", "name": RESUME_TEMPLATES["functional"]["name"], "description": RESUME_TEMPLATES["functional"]["description"]},
        {"id": "modern", "name": RESUME_TEMPLATES["modern"]["name"], "description": RESUME_TEMPLATES["modern"]["description"]}
    ]

def generate_resume_from_template(template_id: str, data: dict) -> str:
    """
    Generate a resume from a template with provided data.
    
    Args:
        template_id: Template identifier (professional, chronological, functional, modern)
        data: Dictionary with resume fields:
            - name: Full name
            - email: Email address
            - phone: Phone number
            - location: (optional) City/Country
            - summary: Professional summary
            - objective: (optional) Career objective
            - skills: Skills (comma-separated or formatted)
            - experience: Work experience section
            - work_history: Work history section (for functional)
            - education: Education section
            - certifications: Certifications and awards
            - additional: Additional information
            - languages: Languages spoken
    
    Returns:
        Generated resume text as string
    """
    if template_id not in RESUME_TEMPLATES:
        raise ValueError(f"Template '{template_id}' not found")
    
    template = RESUME_TEMPLATES[template_id]["format"]
    
    # Build social links string
    social_links = ""
    if data.get("github") or data.get("linkedin"):
        social_links = " | "
        links = []
        if data.get("github"):
            links.append(data.get("github").strip())
        if data.get("linkedin"):
            links.append(data.get("linkedin").strip())
        social_links += " | ".join(links)
    
    # Prepare data with defaults
    resume_data = {
        "name": data.get("name", "Your Name").strip(),
        "email": data.get("email", "email@example.com").strip(),
        "phone": data.get("phone", "").strip(),
        "location": data.get("location", "").strip(),
        "social_links": social_links,
        "summary": format_section(data.get("summary", ""), "summary"),
        "objective": format_section(data.get("objective", ""), "objective"),
        "skills": format_skills(data.get("skills", "")),
        "experience": format_section(data.get("experience", ""), "experience"),
        "projects": format_section(data.get("projects", ""), "projects"),
        "work_history": format_section(data.get("work_history", ""), "work_history"),
        "education": format_section(data.get("education", ""), "education"),
        "certifications": format_section(data.get("certifications", ""), "certifications"),
        "additional": format_section(data.get("additional", ""), "additional"),
        "languages": format_section(data.get("languages", ""), "languages"),
    }
    
    # Generate resume
    resume = template.format(**resume_data).strip()
    
    return resume

def format_section(text: str, section_type: str = "general") -> str:
    """Format a resume section with proper spacing and structure."""
    if not text or not text.strip():
        return ""
    
    lines = text.strip().split("\n")
    formatted_lines = []
    
    for line in lines:
        line = line.strip()
        if line:
            formatted_lines.append(line)
    
    return "\n".join(formatted_lines)

def format_skills(skills_text: str) -> str:
    """Format skills section - can handle comma-separated or bullet-point format."""
    if not skills_text or not skills_text.strip():
        return ""
    
    # If comma-separated, convert to bullet points
    if "," in skills_text and "\n" not in skills_text:
        skills = [s.strip() for s in skills_text.split(",") if s.strip()]
        return "\n".join([f"• {skill}" for skill in skills])
    
    # If already formatted, just clean it up
    lines = skills_text.strip().split("\n")
    formatted = []
    for line in lines:
        line = line.strip()
        if line:
            # Add bullet if not already present
            if not line.startswith("•") and not line.startswith("-"):
                formatted.append(f"• {line}")
            else:
                formatted.append(line)
    
    return "\n".join(formatted)

def create_sample_resume() -> str:
    """Create a sample resume for demonstration."""
    sample_data = {
        "name": "John Doe",
        "email": "john.doe@email.com",
        "phone": "(555) 123-4567",
        "location": "San Francisco, CA",
        "summary": "Results-driven professional with 5+ years of experience in data analysis and business intelligence. Proven track record of delivering actionable insights and driving business growth.",
        "skills": "Python, SQL, Tableau, Excel, Data Analysis, Business Intelligence, Power BI, Machine Learning",
        "experience": """
Senior Data Analyst | Tech Company Inc. | Jan 2021 - Present
• Developed and maintained dashboards tracking key performance metrics
• Improved data processing efficiency by 40% through automation
• Led cross-functional team of 3 analysts

Data Analyst | StartUp Co. | Jun 2019 - Dec 2020
• Created SQL queries to extract and analyze large datasets
• Provided weekly business insights to executive team
• Implemented new data validation processes reducing errors by 25%
""",
        "education": """
Master of Business Administration (MBA) | University of California | 2019
Bachelor of Science in Statistics | University of State | 2017
""",
        "certifications": """
Certified Data Analyst | International Institute | 2020
Google Analytics Certification | Google | 2019
"""
    }
    
    return generate_resume_from_template("modern", sample_data)

def validate_resume_data(data: dict) -> tuple:
    """
    Validate resume data for completeness.
    
    Returns:
        (is_valid: bool, errors: list)
    """
    errors = []
    required_fields = ["name", "email", "phone"]
    
    for field in required_fields:
        if not data.get(field) or not str(data.get(field)).strip():
            errors.append(f"Missing required field: {field}")
    
    # Validate email format (basic)
    email = data.get("email", "").strip()
    if email and "@" not in email:
        errors.append("Invalid email format")
    
    return len(errors) == 0, errors
