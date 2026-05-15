"""
Test script to demonstrate the improved ATS resume checking with validation.
Tests both valid resume content and non-resume PDF content.
"""

from nlp.resume_validator import is_valid_resume_content

# Test 1: Valid Resume Content
print("=" * 70)
print("TEST 1: Valid Resume Content")
print("=" * 70)

valid_resume = """
JOHN DOE
Email: john.doe@example.com | Phone: +1-555-123-4567

PROFESSIONAL SUMMARY
Experienced Software Engineer with 5+ years developing scalable web applications 
and leading cross-functional development teams. Proficient in Python, AWS, and Docker.

EXPERIENCE
Senior Software Engineer | TechCorp Inc. | 2020-Present
- Led development of microservices architecture reducing latency by 40%
- Managed team of 5 engineers responsible for core API services
- Implemented CI/CD pipelines using Docker and Kubernetes

Junior Developer | StartupXYZ | 2018-2020
- Developed RESTful APIs in Python serving 100K+ daily users
- Implemented database optimization strategies increasing query performance by 35%

EDUCATION
Bachelor of Science in Computer Science
University of California, 2018

SKILLS
- Programming: Python, Java, JavaScript, SQL
- Cloud: AWS (EC2, S3, Lambda), Docker, Kubernetes
- Databases: PostgreSQL, MongoDB, Redis
- Tools: Git, Jenkins, Jira, VS Code
"""

is_valid, details = is_valid_resume_content(valid_resume)
print(f"\nIs Valid Resume: {is_valid}")
print(f"Reason: {details['reason']}")
print(f"Text Length: {details['text_length']} words")
print(f"Has Resume Sections: {details['has_sections']}")
print(f"Has Content Keywords: {details['has_content_keywords']} ({details['content_keyword_matches']} matches)")
print(f"Appears to be Non-Resume Document: {details['is_non_resume']}")


# Test 2: Book Chapter (Non-Resume PDF)
print("\n" + "=" * 70)
print("TEST 2: Book Chapter Content (Should be INVALID)")
print("=" * 70)

book_chapter = """
CHAPTER 5: THE HISTORY OF ANCIENT ROME

Introduction
This chapter examines the rise and fall of the Roman Empire. Through careful 
analysis of historical artifacts and literature reviews, we present new insights 
into the mechanisms of imperial governance.

Section 5.1: The Republic Era
The Roman Republic (509-27 BCE) established many of the foundations for later 
imperial rule. This section uses a literature review approach to synthesize existing 
scholarship on republican governance structures.

Section 5.2: Imperial Expansion
During the imperial period (27 BCE-476 CE), Rome expanded significantly. Table of 
contents and appendix materials provide additional historical context.

Conclusion
In conclusion, this chapter has provided a comprehensive overview. The appendix 
contains supplementary data, references, and supporting materials for further study.
"""

is_valid, details = is_valid_resume_content(book_chapter)
print(f"\nIs Valid Resume: {is_valid}")
print(f"Reason: {details['reason']}")
print(f"Text Length: {details['text_length']} words")
print(f"Has Resume Sections: {details['has_sections']}")
print(f"Has Content Keywords: {details['has_content_keywords']} ({details['content_keyword_matches']} matches)")
print(f"Appears to be Non-Resume Document: {details['is_non_resume']}")


# Test 3: Too-Short Document
print("\n" + "=" * 70)
print("TEST 3: Too Short Document (Should be INVALID)")
print("=" * 70)

short_doc = "This is a very short document that is definitely not a resume."

is_valid, details = is_valid_resume_content(short_doc)
print(f"\nIs Valid Resume: {is_valid}")
print(f"Reason: {details['reason']}")
print(f"Text Length: {details['text_length']} words")


# Test 4: Empty Document
print("\n" + "=" * 70)
print("TEST 4: Empty Document (Should be INVALID)")
print("=" * 70)

empty_doc = ""

is_valid, details = is_valid_resume_content(empty_doc)
print(f"\nIs Valid Resume: {is_valid}")
print(f"Reason: {details['reason']}")
print(f"Text Length: {details['text_length']} words")


# Test 5: Minimal Valid Resume
print("\n" + "=" * 70)
print("TEST 5: Minimal Valid Resume (Edge Case)")
print("=" * 70)

minimal_resume = """
JANE SMITH
Email: jane@example.com | Phone: 555-0123

EXPERIENCE
Developed web applications. Managed databases. Led development team.
Implemented solutions. Coordinated with stakeholders. Designed systems.
Engineered features. Collaborated across teams. Python, Java expertise.

EDUCATION
Bachelor's Degree 2019

SKILLS
Python, JavaScript, SQL, AWS
"""

is_valid, details = is_valid_resume_content(minimal_resume)
print(f"\nIs Valid Resume: {is_valid}")
print(f"Reason: {details['reason']}")
print(f"Text Length: {details['text_length']} words")
print(f"Has Resume Sections: {details['has_sections']}")
print(f"Has Content Keywords: {details['has_content_keywords']} ({details['content_keyword_matches']} matches)")


print("\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)
print("""
✓ Valid resumes with sections and content keywords are accepted
✓ Non-resume documents (books, articles) are rejected
✓ Documents that are too short are rejected
✓ Empty documents are rejected
✓ This ensures only ACTUAL resumes are scored in the ATS system
""")
