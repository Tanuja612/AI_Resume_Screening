from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Shared keyword list used by other modules (e.g., interview question generation)
DEFAULT_KEYWORDS = {"python", "java", "sql", "aws", "docker", "kubernetes", "ml", "nlp", "react"}

def calculate_score(resume_text, job_desc_text):
    # Basic guard
    if not resume_text or not job_desc_text:
        return 0.0
    vectorizer = TfidfVectorizer()
    vectors = vectorizer.fit_transform([resume_text, job_desc_text])
    similarity = cosine_similarity(vectors[0], vectors[1])
    return round(similarity[0][0] * 100, 2)
