import os
from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify, redirect, session, url_for, send_from_directory, flash
from utils.db import get_db
from utils.email_service import send_applicant_status_email, send_batch_applicant_emails
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash

import logging
import shutil
import webbrowser
from threading import Timer

from nlp.text_extraction import extract_text_from_pdf
from nlp.preprocessing import preprocess_text
from nlp.scoring import calculate_score, DEFAULT_KEYWORDS
from nlp.ats_analysis import analyze_resume, generate_corrected_resume, extract_plain_text
from nlp.chatbot.interview_bot import start_interview
from nlp.resume_builder import generate_resume_from_template, validate_resume_data, get_available_templates
from datetime import datetime

# automatically load environment variables from .env for local development
load_dotenv()

# configure logging for application
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('app.log')
    ]
)
logger = logging.getLogger(__name__)




def _score_answers_list(answers):
    """Score a list of answer texts and return the average answer score (0-100).

    This mirrors the logic used by the JSON `submit_answers` endpoint so both
    form-based and AJAX flows produce the same result.
    """
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
    if not per_answer:
        return 0.0
    return round(sum(per_answer) / len(per_answer), 2)

app = Flask(__name__)

# security headers via Talisman (CSP, HSTS, etc.)
from flask_talisman import Talisman
# allow inline styles for existing templates; tighten as needed
csp = {
    'default-src': "'self'",
    # we include 'unsafe-inline' for now to support embedded <style> tags;
    # a production deployment should replace inline CSS with external files
    'style-src': ["'self'", 'https://cdn.jsdelivr.net', "'unsafe-inline'"],
    'script-src': ["'self'", 'https://cdn.jsdelivr.net', "'unsafe-inline'"],
}
Talisman(app, content_security_policy=csp)

# secret key must be set via environment variable in production
app.secret_key = os.environ.get('FLASK_SECRET', 'change-me-for-prod')

# session cookie security
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SECURE'] = os.environ.get('FLASK_ENV') == 'production'
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# disable debug mode unless explicitly enabled
app.debug = os.environ.get('FLASK_DEBUG', '0') == '1'

# upload directories (consider storing outside web root in prod)
UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', 'resumes')
PROCESSED_FOLDER = os.environ.get('PROCESSED_FOLDER', 'processed_resumes')
ATS_FOLDER = os.environ.get('ATS_FOLDER', 'ats_resumes')
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["PROCESSED_FOLDER"] = PROCESSED_FOLDER
app.config["ATS_FOLDER"] = ATS_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PROCESSED_FOLDER, exist_ok=True)
os.makedirs(ATS_FOLDER, exist_ok=True)

# limit maximum file size to 5MB, adjust as needed
default_max = 5 * 1024 * 1024
app.config['MAX_CONTENT_LENGTH'] = int(os.environ.get('MAX_CONTENT_LENGTH', default_max))

# allowed resume file extensions
ALLOWED_EXTENSIONS = {'pdf', 'docx'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# -------------------- GLOBAL ERROR HANDLERS --------------------
@app.errorhandler(404)
def page_not_found(e):
    logger.warning(f"404 at {request.path}")
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(e):
    logger.error(f"500 error: {str(e)}", exc_info=True)
    return render_template('500.html'), 500

# -------------------- INDEX / RANKING --------------------
@app.route("/", methods=["GET", "POST"])
def index():
    # if user isn't logged in, show the homepage with login/registration
    if not session.get('user_id'):
        # Check if this is a login or signup form submission
        if request.method == 'POST':
            form_type = request.form.get('form_type', '')
            
            if form_type == 'login':
                username = request.form.get('username')
                password = request.form.get('password')
                db = get_db()
                user = db.execute('SELECT id,password_hash FROM users WHERE username=?', (username,)).fetchone()
                if user and check_password_hash(user['password_hash'], password):
                    session['user_id'] = user['id']
                    session['username'] = username
                    # Update last login time
                    db.execute('UPDATE users SET last_login=? WHERE id=?', (datetime.utcnow().isoformat(), user['id']))
                    db.commit()
                    return redirect(url_for('dashboard'))
                else:
                    error = 'invalid credentials'
                    return render_template('index.html', error=error, signup_error=None)
            
            elif form_type == 'signup':
                username = request.form.get('username')
                password = request.form.get('password')
                name = request.form.get('name')
                email = request.form.get('email')
                phone_number = request.form.get('phone_number')
                
                if not username or not password:
                    signup_error = 'username & password required'
                    return render_template('index.html', error=None, signup_error=signup_error)
                
                db = get_db()
                try:
                    db.execute('INSERT INTO users (username, password_hash, name, email, phone_number, created_at) VALUES (?,?,?,?,?,?)',
                               (username, generate_password_hash(password), name, email, phone_number, datetime.utcnow().isoformat()))
                    db.commit()
                except Exception:
                    signup_error = 'user already exists'
                    return render_template('index.html', error=None, signup_error=signup_error)
                
                # After successful registration, redirect back to index to show login modal
                return render_template('index.html', error='Account created successfully! Please log in.', signup_error=None)
        
        # Show homepage with login/registration forms
        error = request.args.get('error')
        signup_error = request.args.get('signup_error')
        return render_template('index.html', error=error, signup_error=signup_error)

    return render_template("index.html")


def login_required(f):
    from functools import wraps
    @wraps(f)
    def wrapped(*args, **kwargs):
        # simple session-based check: redirect to login if no user_id
        if not session.get('user_id'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return wrapped


# -------------------- DASHBOARD & UPLOAD --------------------
@app.route('/dashboard')
@login_required
def dashboard():
    """Show dashboard with Create Resume and Upload Resume options."""
    db = get_db()
    user_id = session.get('user_id')
    
    # Get recent resumes for this user
    recent_resumes = db.execute(
        'SELECT id, filename, score, final_score, created_at FROM resumes WHERE user_id = ? ORDER BY created_at DESC LIMIT 5',
        (user_id,)
    ).fetchall()
    
    return render_template('dashboard.html', recent_resumes=recent_resumes)


@app.route('/upload_resume')
@login_required
def upload_resume():
    """Show upload resume form."""
    return render_template('upload_resume.html')


@app.route('/upload_resumes', methods=['POST'])
@login_required
def upload_resumes():
    """Handle resume file uploads."""
    # at upload time we only store files and processed text; scoring happens once
    # the job description is provided on the review page.
    files = request.files.getlist("resumes")
    results = []
    db = get_db()
    user_id = session.get('user_id')
    for file in files:
        if file.filename == "":
            continue
        if not allowed_file(file.filename):
            logger.warning(f"Skipping disallowed file type: {file.filename}")
            continue

        filename = secure_filename(file.filename)
        path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        file.save(path)

        text = extract_text_from_pdf(path) or ""
        processed = preprocess_text(text)

        results.append({
            "name": filename,
            "score": None,
            "text": processed
        })

        # persist resume record for this user (score unknown yet)
        try:
            db.execute(
                "INSERT INTO resumes (user_id, filename, score, details, created_at) VALUES (?,?,?,?,?)",
                (user_id, filename, None, str({'text': processed}), datetime.utcnow().isoformat())
            )
            db.commit()
        except Exception:
            pass

    # we don't yet have scores; just record results list for the review page
    session['last_results'] = results
    # clear any leftover scoring info
    session.pop('last_resume', None)
    session.pop('last_score', None)
    session.pop('last_text', None)

    # redirect user to the ATS check page first
    redirect_url = url_for('ats_check')

    # if client expects JSON return only the redirect; scoring happens later
    if request.headers.get('Accept', '').startswith('application/json') or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({
            "redirect": redirect_url
        })

    # normal form submit -> just redirect to results page
    return redirect(redirect_url)


# -------------------- AUTHENTICATION --------------------
@app.route('/signup', methods=['GET','POST'])
def signup():
    # already authenticated?
    if session.get('user_id'):
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        name = request.form.get('name')
        email = request.form.get('email')
        phone_number = request.form.get('phone_number')
        
        if not username or not password:
            return redirect(url_for('index', signup_error='username & password required'))
        db = get_db()
        try:
            db.execute('INSERT INTO users (username, password_hash, name, email, phone_number, created_at) VALUES (?,?,?,?,?,?)',
                       (username, generate_password_hash(password), name, email, phone_number, datetime.utcnow().isoformat()))
            db.commit()
        except Exception:
            return redirect(url_for('index', signup_error='user already exists'))
        user = db.execute('SELECT id FROM users WHERE username=?', (username,)).fetchone()
        session['user_id'] = user['id']
        session['username'] = username
        return redirect(url_for('index'))
    return redirect(url_for('index'))


@app.route('/login', methods=['GET','POST'])
def login():
    # if already logged in just go to index
    if session.get('user_id'):
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        db = get_db()
        user = db.execute('SELECT id,password_hash FROM users WHERE username=?', (username,)).fetchone()
        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['username'] = username
            # Update last login time
            db.execute('UPDATE users SET last_login=? WHERE id=?', (datetime.utcnow().isoformat(), user['id']))
            db.commit()
            return redirect(url_for('index'))
        else:
            return redirect(url_for('index', error='invalid credentials'))
    return redirect(url_for('index'))


# -------------------- RESUME BUILDER --------------------
@app.route('/resume_builder')
@login_required
def resume_builder():
    """Display resume builder page with templates."""
    templates = get_available_templates()
    return render_template('resume_builder.html', templates=templates)


@app.route('/save_resume', methods=['POST'])
@login_required
def save_resume():
    """Save a created resume to the database and file system."""
    try:
        # Get form data
        if request.is_json:
            data = request.get_json()
        else:
            data = request.form.to_dict()
        
        # Validate required fields
        is_valid, errors = validate_resume_data(data)
        if not is_valid:
            return jsonify({'success': False, 'errors': errors}), 400
        
        template_id = data.get('template', 'modern')
        
        # Generate resume content
        resume_content = generate_resume_from_template(template_id, data)
        
        # Save to file
        user_id = session.get('user_id')
        filename = secure_filename(f"resume_{user_id}_{int(datetime.utcnow().timestamp())}.txt")
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(resume_content)
        
        # Save to database
        db = get_db()
        db.execute(
            "INSERT INTO resumes (user_id, filename, score, details, created_at) VALUES (?,?,?,?,?)",
            (user_id, filename, None, str({'template': template_id}), datetime.utcnow().isoformat())
        )
        db.commit()
        
        # Add to session results so user can proceed with ATS check
        session['last_results'] = [{
            "name": filename,
            "score": None,
            "text": preprocess_text(resume_content)
        }]
        session['created_resume_filename'] = filename
        session['resume_content'] = resume_content
        
        return jsonify({'success': True, 'filename': filename})
    
    except Exception as e:
        logger.error(f"Error saving resume: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/resume_created/<filename>')
@login_required
def resume_created_page(filename):
    """Show success page with download option after resume creation."""
    session['created_resume_filename'] = filename
    return render_template('resume_created.html', filename=filename)
# -------------------- CHATBOT --------------------
@app.route("/results")
def results_page():
    # this endpoint is still available but the main flow now uses /review
    results = session.pop('last_results', [])
    return render_template("results.html", results=results)


@app.route("/ats_check", methods=["GET","POST"])
@login_required
# new page between upload and job description that verifies ATS compatibility
# and optionally produces an improved version. Also validates that uploaded files
# are actual resumes (PDFs with non-resume content get 0 score).
def ats_check():
    results = session.get('last_results', [])
    if not results:
        return redirect(url_for('index'))

    # run analysis on POST; job_desc not collected here
    job_desc = None

    # determine friendliness / analyze if not already set
    for r in results:
        if 'analysis' not in r:
            path = os.path.join(app.config['UPLOAD_FOLDER'], r['name'])
            r['analysis'] = analyze_resume(path, job_desc=None)
            # Check if this is actually a valid resume
            is_valid_resume = r['analysis'].get('is_valid_resume', True)  # Default to True for backward compat
            if not is_valid_resume:
                # Non-resume PDFs get score of 0
                r['ats_friendly'] = False
                r['ats_updated'] = False
                r['validation_error'] = r['analysis'].get('validation_details', {}).get('reason', 'Not a valid resume')
            else:
                # mark friendly based on score threshold (only for valid resumes)
                r['ats_friendly'] = r['analysis']['score'] >= 70
                r['ats_updated'] = False
                r['validation_error'] = None

    if request.method == 'POST':
        filename = request.form.get('improve')
        if filename:
            for r in results:
                if r['name'] == filename and not r.get('ats_friendly', False):
                    # Only improve if it's a valid resume
                    if not r.get('validation_error'):
                        dest, corrections = improve_for_ats(filename, r.get('analysis', {}))
                        r['ats_updated'] = True
                        r['corrections_made'] = corrections
                        r['corrected_filename'] = os.path.basename(dest)
                        # re-run analysis on improved file
                        r['analysis'] = analyze_resume(dest, job_desc=job_desc)
                        r['ats_friendly'] = r['analysis']['score'] >= 70
                        # update text for later scoring
                        try:
                            with open(dest, 'r', encoding='utf-8', errors='ignore') as fr:
                                txt = fr.read()
                        except Exception:
                            txt = r.get('text', '')
                        r['text'] = preprocess_text(txt)
                    break
        session['last_results'] = results

    return render_template('ats_check.html', results=results, job_desc=job_desc)


@app.route("/review", methods=["GET","POST"])
@login_required
def review_page():
    results = session.get('last_results', [])
    if not results:
        return redirect(url_for('index'))

    # job description will only be provided on this page via POST
    job_desc = None
    if request.method == "POST":
        job_desc = preprocess_text(request.form.get("job_desc") or "")
        # score each entry and sort
        for r in results:
            r['score'] = calculate_score(r.get('text',''), job_desc)
        results = sorted(results, key=lambda x: x.get("score") or 0, reverse=True)
        session['last_results'] = results

        top = results[0] if results else None
        if top:
            session['last_resume'] = top['name']
            session['last_score'] = top['score']
            session['last_text'] = top.get('text')
        else:
            session.pop('last_resume', None)
            session.pop('last_score', None)
            session.pop('last_text', None)
        score = session.get('last_score')
        resume_name = session.get('last_resume')
        # make updated copy right away
        try:
            _ensure_updated_resume(resume_name, score)
        except Exception:
            pass
        return render_template('review.html', resume_name=resume_name, score=score, results=results, job_desc=job_desc)

    # GET path: show form, maybe with scores already if posted earlier
    resume_name = session.get('last_resume')
    score = session.get('last_score')
    # pre-generate updated if score exists
    if resume_name and score is not None:
        try:
            _ensure_updated_resume(resume_name, score)
        except Exception:
            pass
    return render_template('review.html', resume_name=resume_name, score=score, results=results, job_desc=None)


@app.route('/download_original/<path:filename>')
def download_original(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)



def _ensure_updated_resume(filename, score=None):
    """Create a copy of the uploaded resume in the processed folder.
    For text files we append the score at the end. Returns path to updated file.
    """
    orig = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    proc_dir = app.config['PROCESSED_FOLDER']
    os.makedirs(proc_dir, exist_ok=True)
    dest = os.path.join(proc_dir, filename)
    if not os.path.exists(dest):
        # for text files append score, else just copy
        if filename.lower().endswith('.txt'):
            try:
                with open(orig, 'r', encoding='utf-8', errors='ignore') as fr:
                    content = fr.read()
            except Exception:
                content = ''
            score_val = score if score is not None else session.get('last_score', '')
            with open(dest, 'w', encoding='utf-8') as fw:
                fw.write(content + f"\n\nScore: {score_val}\n")
        else:
            shutil.copy2(orig, dest)
    return dest


@app.route('/download_updated/<path:filename>')
def download_updated(filename):
    # ensure the updated file exists before sending
    _ensure_updated_resume(filename)
    proc_dir = app.config['PROCESSED_FOLDER']
    return send_from_directory(proc_dir, filename, as_attachment=True)


# -------------------- ATS Helper / Routing --------------------
def is_ats_friendly(filename: str) -> bool:
    """Simple heuristic to estimate ATS compatibility.

    Factors considered:
    1. **Extracted text exists** – image‑only PDFs or corrupt files will
       have very few words.
    2. **Minimum word count** – trivial documents (<50 words) are unlikely
       to parse well.
    3. **Presence of common resume section headers** such as "Experience",
       "Education", "Skills", etc. ATS systems expect some identifiable
       structure.
    4. **Avoidance of unusual characters/formatting** – tabs or long runs of
       spaces can indicate tables or layouts that break parsers.

    This heuristic is intentionally permissive and can be tuned over time.
    """
    path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    text = ''
    try:
        if filename.lower().endswith('.pdf'):
            text = extract_text_from_pdf(path) or ''
        elif filename.lower().endswith('.txt'):
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                text = f.read()
        else:
            return False
    except Exception:
        return False

    words = text.split()
    if len(words) < 50:
        # too short to be a real resume
        return False

    lowered = text.lower()
    headers = ['experience', 'education', 'skills', 'projects', 'certifications', 'work experience']
    if not any(h in lowered for h in headers):
        # missing typical sections
        return False

    # check for formatting likely to confuse ATS (tables, tabs)
    if '\t' in text or '    ' in text:
        return False

    return True


def improve_for_ats(filename: str) -> str:
    """Generate an ATS-friendly copy of the resume and return its path.
    Currently this just copies the file to the ATS folder and, for text
    documents, adds a small comment.  More advanced logic can be inserted
    later.
    """
    orig = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    ats_dir = app.config['ATS_FOLDER']
    os.makedirs(ats_dir, exist_ok=True)
    dest = os.path.join(ats_dir, filename)
    if not os.path.exists(dest):
        if filename.lower().endswith('.txt'):
            try:
                with open(orig, 'r', encoding='utf-8', errors='ignore') as fr:
                    content = fr.read()
            except Exception:
                content = ''
            # rudimentary “improvement” – strip non-ASCII and append note
            cleaned = ''.join(c for c in content if ord(c) < 128)
            with open(dest, 'w', encoding='utf-8') as fw:
                fw.write(cleaned + "\n\n[Converted to ATS-friendly format]\n")
        else:
            shutil.copy2(orig, dest)
    return dest


@app.route('/download_ats/<path:filename>')
def download_ats(filename):
    return send_from_directory(app.config['ATS_FOLDER'], filename, as_attachment=True)


@app.route('/download_created/<path:filename>')
def download_created(filename):
    """Download a resume that was created by the user."""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)


@app.route('/get_resume_content/<path:filename>')
@login_required
def get_resume_content(filename):
    """Get the content of a resume for preview."""
    try:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if not os.path.exists(file_path):
            return jsonify({'error': 'File not found'}), 404
        
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        return jsonify({'content': content})
    except Exception as e:
        logger.error(f"Error reading resume: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/export_report/<path:filename>')
def export_report(filename):
    # find analysis for given resume in session
    results = session.get('last_results', [])
    report_text = ''
    for r in results:
        if r['name'] == filename and r.get('analysis'):
            a = r['analysis']
            report_text += f"Resume: {filename}\n"
            report_text += f"Score: {a['score']}/100\n\n"
            report_text += "Strengths:\n"
            for s in a.get('strengths', []):
                report_text += f"- {s}\n"
            report_text += "\nWeaknesses:\n"
            for w in a.get('weaknesses', []):
                report_text += f"- {w}\n"
            report_text += "\nRecommendations:\n"
            for rcmd in a.get('recommendations', []):
                report_text += f"- {rcmd}\n"
            break
    if not report_text:
        report_text = "No analysis available."
    return (report_text, 200, {
        'Content-Type': 'text/plain; charset=utf-8',
        'Content-Disposition': f'attachment; filename={filename}_report.txt'
    })



# -------------------- INTERVIEW SCORING --------------------
@app.route("/interview", methods=["GET", "POST"])
@login_required
def interview():
    # pull base information from session so we can display it
    base_score = session.get('last_score')
    resume_name = session.get('last_resume')
    # no chatbot/questions logic any more

    if request.method == "POST":
        answers = request.form.getlist("answers")
        answer_score = _score_answers_list(answers)

        # Combined score is now a simple sum of resume match and interview score
        base = float(base_score) if base_score is not None else 0.0
        combined = round(base + answer_score, 2)

        session['interview_score'] = answer_score
        session['combined_score'] = combined
        session['final_base_score'] = base_score
        session['final_resume_name'] = resume_name

        session.pop('last_score', None)
        session.pop('last_text', None)

        return redirect(url_for('interview_result'))

    # GET request: generate interview questions from candidate text
    try:
        questions = start_interview(session.get('last_text'))
    except Exception:
        questions = []

    return render_template("interview.html", questions=questions,
                           base_score=base_score, resume_name=resume_name)


@app.route('/interview_choice', methods=['GET'])
@login_required
def interview_choice():
    """Let user choose between text or voice interview."""
    base_score = session.get('last_score')
    resume_name = session.get('last_resume')
    return render_template('interview_choice.html', 
                          base_score=base_score, 
                          resume_name=resume_name)


@app.route("/voice_interview", methods=["GET", "POST"])
@login_required
def voice_interview():
    """Voice-based interview with speech recognition and text-to-speech."""
    base_score = session.get('last_score')
    resume_name = session.get('last_resume')

    if request.method == "POST":
        try:
            data = request.get_json()
            answers = data.get('answers', [])
            answer_score = _score_answers_list(answers)

            # Combined score
            base = float(base_score) if base_score is not None else 0.0
            combined = round(base + answer_score, 2)

            session['interview_score'] = answer_score
            session['combined_score'] = combined
            session['final_base_score'] = base_score
            session['final_resume_name'] = resume_name

            session.pop('last_score', None)
            session.pop('last_text', None)

            return redirect(url_for('interview_result'))
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    # GET request: render voice interview interface
    return render_template("voice_interview.html", 
                           base_score=base_score, 
                           resume_name=resume_name)


@app.route('/logout')
def logout():
    # clear session and send user back to the homepage (which will show login)
    session.clear()
    return redirect(url_for('index'))


# -------------------- ADMIN ROUTES --------------------
@app.route('/admin_login', methods=['GET','POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        # Simple admin credentials (change in production)
        admin_username = os.environ.get('ADMIN_USERNAME', 'admin')
        admin_password = os.environ.get('ADMIN_PASSWORD', 'admin123')
        
        if username == admin_username and password == admin_password:
            session['admin_logged_in'] = True
            session['admin_username'] = username
            return redirect(url_for('admin_dashboard'))
        else:
            error = 'invalid admin credentials'
            return render_template('admin_login.html', error=error)
    return render_template('admin_login.html')


@app.route('/admin_dashboard')
def admin_dashboard():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    db = get_db()
    # Get all users with their resume count and last login
    users = db.execute('''
        SELECT u.id, u.username, u.name, u.email, u.phone_number, u.created_at, u.last_login, COUNT(r.id) as resume_count
        FROM users u
        LEFT JOIN resumes r ON u.id = r.user_id
        GROUP BY u.id
        ORDER BY u.created_at DESC
    ''').fetchall()
    
    return render_template('admin_dashboard.html', users=users)


@app.route('/admin_logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    session.pop('admin_username', None)
    return redirect(url_for('index'))


# -------------------- ADMIN API ROUTES --------------------
@app.route('/admin/user_resumes/<int:user_id>')
def admin_user_resumes(user_id):
    """Get all resumes for a specific user with their scores and status."""
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    db = get_db()
    
    # Get user info
    user = db.execute('SELECT username FROM users WHERE id = ?', (user_id,)).fetchone()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    # Get all resumes for this user
    resumes = db.execute('''
        SELECT id, filename, score, final_score, selection_status, created_at, details
        FROM resumes
        WHERE user_id = ?
        ORDER BY created_at DESC
    ''', (user_id,)).fetchall()
    
    resume_list = []
    for resume in resumes:
        resume_list.append({
            'id': resume['id'],
            'filename': resume['filename'],
            'score': resume['score'],
            'final_score': resume['final_score'],
            'selection_status': resume['selection_status'] or 'pending',
            'created_at': resume['created_at'],
            'details': resume['details']
        })
    
    return jsonify({
        'username': user['username'],
        'user_id': user_id,
        'resumes': resume_list
    })


@app.route('/admin/update_resume_status', methods=['POST'])
def admin_update_resume_status():
    """Update the selection status of a resume."""
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.get_json()
    resume_id = data.get('resume_id')
    status = data.get('status')
    
    if status not in ['selected', 'rejected', 'pending']:
        return jsonify({'error': 'Invalid status'}), 400
    
    db = get_db()
    try:
        db.execute(
            'UPDATE resumes SET selection_status = ? WHERE id = ?',
            (status, resume_id)
        )
        db.commit()
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Error updating resume status: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/admin/update_final_score', methods=['POST'])
def admin_update_final_score():
    """Update the final score of a resume."""
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.get_json()
    resume_id = data.get('resume_id')
    final_score = data.get('final_score')
    
    if not isinstance(final_score, (int, float)) or not (0 <= final_score <= 100):
        return jsonify({'error': 'Invalid score'}), 400
    
    db = get_db()
    try:
        db.execute(
            'UPDATE resumes SET final_score = ? WHERE id = ?',
            (final_score, resume_id)
        )
        db.commit()
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Error updating final score: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/candidate/my_resumes')
@login_required
def candidate_my_resumes():
    """Get all resumes for the logged-in candidate (shows pending status regardless of actual status unless rejected)."""
    user_id = session.get('user_id')
    db = get_db()
    
    # Get all resumes for this user
    resumes = db.execute('''
        SELECT id, filename, score, final_score, selection_status, created_at, details
        FROM resumes
        WHERE user_id = ?
        ORDER BY created_at DESC
    ''', (user_id,)).fetchall()
    
    resume_list = []
    for resume in resumes:
        # For candidate view: show "pending" if status is "selected" or "pending", only show "rejected" if actually rejected
        display_status = 'rejected' if resume['selection_status'] == 'rejected' else 'pending'
        
        resume_list.append({
            'id': resume['id'],
            'filename': resume['filename'],
            'score': resume['score'],
            'final_score': resume['final_score'],
            'selection_status': display_status,  # Show "pending" to candidate, except if "rejected"
            'created_at': resume['created_at'],
            'details': resume['details']
        })
    
    return jsonify({'resumes': resume_list})


@app.route('/about')
def about():
    return render_template('about.html')



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

    answer_score = _score_answers_list(answers)

    # combine with base_score (resume/job match) by summing both scores
    base = float(base_score) if base_score is not None else 0.0
    combined = round(base + answer_score, 2)

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


@app.route('/send_applicant_email', methods=['GET', 'POST'])
@login_required
def send_applicant_email():
    """
    Route to send applicant status email.
    GET: Shows form to send email
    POST: Sends email and returns result
    """
    if request.method == 'POST':
        applicant_name = request.form.get('applicant_name', '').strip()
        applicant_email = request.form.get('applicant_email', '').strip()
        status = request.form.get('status', '').strip()
        
        # Validate inputs
        if not all([applicant_name, applicant_email, status]):
            return jsonify({
                'success': False,
                'message': 'All fields (name, email, status) are required.'
            }), 400
        
        # Send email
        success, message = send_applicant_status_email(applicant_email, applicant_name, status)
        
        return jsonify({
            'success': success,
            'message': message
        })
    
    # GET request: render form
    return render_template('send_email.html')


@app.route('/send_batch_emails', methods=['GET', 'POST'])
@login_required
def send_batch_emails():
    """
    Route to send batch status emails to multiple applicants.
    GET: Shows form or upload interface
    POST: Processes CSV/JSON and sends emails
    """
    if request.method == 'POST':
        # Handle JSON request with applicants list
        if request.is_json:
            data = request.get_json()
            applicants = data.get('applicants', [])
            company_name = data.get('company_name', 'AI Resume Screening System')
            
            # Validate applicants list
            if not applicants or not isinstance(applicants, list):
                return jsonify({
                    'success': False,
                    'message': 'Invalid applicants data. Expected list of applicants.'
                }), 400
            
            # Send batch emails
            results = send_batch_applicant_emails(applicants, company_name)
            
            # Calculate summary
            successful = sum(1 for r in results.values() if r['success'])
            total = len(results)
            
            return jsonify({
                'success': True,
                'message': f'Batch email sending completed: {successful}/{total} successful',
                'results': results,
                'summary': {
                    'total': total,
                    'successful': successful,
                    'failed': total - successful
                }
            })
        
        # Handle form data with CSV
        else:
            import csv
            import io
            
            csv_file = request.files.get('csv_file')
            company_name = request.form.get('company_name', 'AI Resume Screening System')
            
            if not csv_file:
                return jsonify({
                    'success': False,
                    'message': 'No CSV file provided.'
                }), 400
            
            try:
                # Parse CSV file
                stream = io.StringIO(csv_file.stream.read().decode('UTF8'), newline=None)
                csv_data = csv.DictReader(stream)
                
                applicants = []
                for row in csv_data:
                    if 'name' in row and 'email' in row and 'status' in row:
                        applicants.append({
                            'name': row['name'].strip(),
                            'email': row['email'].strip(),
                            'status': row['status'].strip()
                        })
                
                if not applicants:
                    return jsonify({
                        'success': False,
                        'message': 'No valid applicants found in CSV. Required columns: name, email, status'
                    }), 400
                
                # Send batch emails
                results = send_batch_applicant_emails(applicants, company_name)
                
                # Calculate summary
                successful = sum(1 for r in results.values() if r['success'])
                total = len(results)
                
                return jsonify({
                    'success': True,
                    'message': f'CSV processed and emails sent: {successful}/{total} successful',
                    'results': results,
                    'summary': {
                        'total': total,
                        'successful': successful,
                        'failed': total - successful
                    }
                })
            
            except Exception as e:
                return jsonify({
                    'success': False,
                    'message': f'Error processing CSV file: {str(e)}'
                }), 400
    
    # GET request: render batch email form
    return render_template('send_batch_emails.html')


@app.route('/interview_result')
@login_required
def interview_result():
    interview_score = session.get('interview_score')
    combined_score = session.get('combined_score')
    base_score = session.get('final_base_score')
    resume_name = session.get('final_resume_name')

    # Save final score and selection status to database based on interview performance
    if resume_name and combined_score is not None:
        try:
            user_id = session.get('user_id')
            db = get_db()
            
            # Determine selection status based on combined score (70+ = selected, <70 = rejected)
            selection_status = 'selected' if float(combined_score) >= 70 else 'rejected'
            
            # Update both final_score and selection_status
            db.execute(
                'UPDATE resumes SET final_score = ?, selection_status = ? WHERE filename = ? AND user_id = ?',
                (combined_score, selection_status, resume_name, user_id)
            )
            db.commit()
        except Exception as e:
            logger.warning(f"Could not save final score and status: {str(e)}")

    # clear the saved scores once we've displayed them
    session.pop('interview_score', None)
    session.pop('combined_score', None)
    session.pop('final_base_score', None)
    session.pop('final_resume_name', None)

    status = None
    try:
        if combined_score is not None:
            status = "Selected" if float(combined_score) >= 70 else "Rejected"
    except Exception:
        status = None

    return render_template('interview_result.html',
                           interview_score=interview_score,
                           combined_score=combined_score,
                           base_score=base_score,
                           resume_name=resume_name,
                           status=status)

# -------------------- RUN --------------------
if __name__ == "__main__":
    # Auto-open browser after a short delay
    def open_browser():
        webbrowser.open('http://127.0.0.1:5000')
    
    # Schedule browser to open after 1 second (gives Flask time to start)
    timer = Timer(1.0, open_browser)
    timer.daemon = True
    timer.start()
    
    print("\n" + "="*60)
    print("🎓 AI Resume Screening System")
    print("="*60)
    print("Server running at: http://127.0.0.1:5000")
    print("Press CTRL+C to stop the server")
    print("="*60 + "\n")
    
    app.run(debug=True, use_reloader=False)
  