from flask import Flask, render_template, request, jsonify, redirect, session, url_for
from utils.db import get_db
from werkzeug.utils import secure_filename
import os

from chatbot.interview_bot import start_interview
from nlp.text_extraction import extract_text_from_pdf
from nlp.preprocessing import preprocess_text
from nlp.scoring import calculate_score, DEFAULT_KEYWORDS
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET', 'change-me-for-prod')

UPLOAD_FOLDER = "resumes"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# -------------------- INDEX / RANKING --------------------
@app.route("/", methods=["GET", "POST"])
def index():
    # authentication removed — index is public now
    if request.method == "POST":

        job_desc = preprocess_text(request.form.get("job_desc"))

        files = request.files.getlist("resumes")
        results = []

        for file in files:
            if file.filename == "":
                continue

            path = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
            file.save(path)

            text = extract_text_from_pdf(path)
            text = preprocess_text(text)

            score = calculate_score(text, job_desc)

            results.append({
                "name": file.filename,
                "score": score
            })

        results = sorted(results, key=lambda x: x["score"], reverse=True)

        return render_template("results.html", results=results)

    return render_template("index.html")


def login_required(f):
    from functools import wraps
    @wraps(f)
    def wrapped(*args, **kwargs):
        # authentication removed — allow access
        return f(*args, **kwargs)
    return wrapped


# -------------------- CHATBOT --------------------
@app.route("/chatbot", methods=["GET", "POST"])
@login_required
def chatbot():
    # If POST (API), return JSON questions; otherwise render template
    questions = start_interview()
    if request.method == 'POST':
        return jsonify({"questions": questions})
    return render_template("chatbot.html", questions=questions)


# -------------------- INTERVIEW SCORING --------------------
@app.route("/interview", methods=["GET", "POST"])
@login_required
def interview():
    if request.method == "POST":
        # Accept file upload (from index UI) and return JSON score/details
        if 'file' in request.files:
            file = request.files['file']
            if file.filename == '':
                return jsonify({"error": "no file provided"}), 400

            filename = secure_filename(file.filename)
            save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(save_path)

            # extract and preprocess
            text = extract_text_from_pdf(save_path) or ""
            text = preprocess_text(text)

            # If a job description was provided, use the existing TF-IDF scoring
            job_desc = request.form.get('job_desc')
            try:
                if job_desc:
                    jd = preprocess_text(job_desc)
                    score = calculate_score(text, jd)
                    details = {"method": "tfidf_similarity"}
                else:
                    # fallback: simple keyword heuristic
                    keywords = {"python", "java", "sql", "aws", "docker", "kubernetes", "ml", "nlp", "react"}
                    words = set(text.split())
                    matches = words & keywords
                    kw_score = min(1.0, len(matches) / max(1, len(keywords)))
                    score = round(kw_score * 100, 2)
                    details = {"method": "keyword_fallback", "keywords_found": list(matches), "keyword_match": round(kw_score * 100, 2)}
            except Exception:
                return jsonify({"error": "scoring failed"}), 500

            # persist resume record linked to user
            # persist resume record linked to user and return resume id
            resume_id = None
            try:
                db = get_db()
                cur = db.execute('INSERT INTO resumes (user_id, filename, score, details, created_at) VALUES (?, ?, ?, ?, ?)',
                           (session.get('user_id'), filename, score, str(details), datetime.utcnow().isoformat()))
                db.commit()
                resume_id = cur.lastrowid
            except Exception:
                resume_id = None

            # also return suggested questions based on resume text
            questions = start_interview(text)
            return jsonify({"score": score, "details": details, "questions": questions, "resume_id": resume_id})

        # legacy interview form handling
        answers = request.form.getlist("answers")
        score = len([a for a in answers if len(a.split()) > 5]) * 10
        return f"Interview Score: {score}%"

    questions = start_interview()
    return render_template("interview.html", questions=questions)


@app.route('/logout')
def logout():
    # keep logout but redirect to index now that auth is removed
    session.clear()
    return redirect(url_for('index'))


@app.route('/submit_answers', methods=['POST'])
@login_required
def submit_answers():
    """Accept JSON: { answers: [...], resume_id?: int, base_score?: number }
    Returns updated combined score.
    """
    data = request.get_json(force=True)
    answers = data.get('answers', [])
    resume_id = data.get('resume_id')
    base_score = data.get('base_score')

    if not answers:
        return jsonify({'error': 'no answers provided'}), 400

    # Scoring each answer by length, keyword presence, and lexical diversity
    def score_answer(text):
        toks = [t.strip('.,()[]') for t in text.lower().split() if t.strip()]
        total = len(toks)
        if total == 0:
            return 0.0
        unique = len(set(toks))

        # length score: saturates at 20 words
        length_score = min(1.0, total / 20.0)

        # keyword score: fraction of DEFAULT_KEYWORDS present
        kw_matches = sum(1 for k in DEFAULT_KEYWORDS if k in toks)
        kw_score = kw_matches / max(1, len(DEFAULT_KEYWORDS))

        # lexical diversity
        diversity = unique / total

        # weighted combination
        sc = 0.5 * length_score + 0.4 * kw_score + 0.1 * diversity
        return round(sc * 100, 2)

    per_answer = [score_answer(a) for a in answers]
    answer_score = round(sum(per_answer) / len(per_answer), 2)

    # combine with base_score (resume/job match) — weights can be tuned
    resume_weight = 0.7
    interview_weight = 0.3
    base = float(base_score) if base_score is not None else 0.0
    combined = round(base * resume_weight + answer_score * interview_weight, 2)

    # persist answer result (optional): update resumes table if resume_id provided
    if resume_id:
        try:
            db = get_db()
            db.execute('UPDATE resumes SET score = ?, details = ? WHERE id = ?',
                       (combined, str({'answer_score': answer_score, 'base_score': base}), resume_id))
            db.commit()
        except Exception:
            pass

    return jsonify({'answer_score': answer_score, 'combined_score': combined})


# -------------------- RUN --------------------
if __name__ == "__main__":
    app.run(debug=True)