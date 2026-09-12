from flask import Blueprint, request, jsonify, current_app, send_file
from models import db, User, Resume, InterviewSession, InterviewQuestion, PerformanceReport, Company, Notification, Feedback, BulkJob
from routes.auth import token_required
from services.resume_parser import ResumeParser
from services.resume_scorer import ResumeScorer
from services.ai_service import AIService
from services.report_service import ReportService
import os
import json
import jwt
import hashlib
import logging
import time
from datetime import datetime
import zipfile
import threading
import io
from concurrent.futures import ThreadPoolExecutor
from werkzeug.utils import secure_filename

logger = logging.getLogger(__name__)

api_bp = Blueprint('api', __name__)

@api_bp.route('/dashboard/stats', methods=['GET'])
@token_required
def dashboard_stats(current_user):
    # Fetch user data statistics
    latest_resume = Resume.query.filter_by(user_id=current_user.id).order_by(Resume.created_at.desc()).first()
    latest_report = PerformanceReport.query.filter_by(user_id=current_user.id).order_by(PerformanceReport.created_at.desc()).first()
    interview_count = InterviewSession.query.filter_by(user_id=current_user.id).count()
    completed_count = InterviewSession.query.filter_by(user_id=current_user.id, status='completed').count()
    
    recent_reports = PerformanceReport.query.filter_by(user_id=current_user.id).order_by(PerformanceReport.created_at.desc()).limit(5).all()
    notifications = Notification.query.filter_by(user_id=current_user.id, is_read=False).order_by(Notification.created_at.desc()).all()
    
    ats_score = latest_resume.ats_score if latest_resume else 0
    resume_score = latest_resume.resume_score if latest_resume else 0

    # 1. Calculate historical ATS trend
    all_resumes = Resume.query.filter_by(user_id=current_user.id).order_by(Resume.created_at.asc()).all()
    if all_resumes:
        ats_trend = [r.ats_score for r in all_resumes]
        while len(ats_trend) < 5:
            ats_trend.insert(0, max(ats_trend[0] - 5, 45))
    else:
        ats_trend = [50, 55, 60, 65, 70, 75]

    # 2. Calculate historical readiness trend
    all_reports = PerformanceReport.query.filter_by(user_id=current_user.id).order_by(PerformanceReport.created_at.asc()).all()
    if all_reports:
        readiness_trend = [r.overall_score for r in all_reports]
        while len(readiness_trend) < 5:
            readiness_trend.insert(0, max(readiness_trend[0] - 6, 40))
    else:
        readiness_trend = [40, 50, 60, 68, 76]

    # 3. Calculate keyword match/density from real extracted resume text
    keyword_labels = []
    keyword_data = []
    if latest_resume and latest_resume.skills_json:
        try:
            skills = json.loads(latest_resume.skills_json)
        except Exception:
            skills = []
        text = latest_resume.extracted_text.lower() if latest_resume.extracted_text else ""
        counts = {}
        for s in skills[:8]:
            counts[s] = text.count(s.lower())
        sorted_skills = sorted(counts.items(), key=lambda x: x[1], reverse=True)[:5]
        for skill, count in sorted_skills:
            keyword_labels.append(skill)
            keyword_data.append(min(70 + count * 5, 98))
    
    if not keyword_labels:
        keyword_labels = ['Python', 'SQL', 'Git', 'REST APIs', 'Docker']
        keyword_data = [90, 85, 75, 65, 50]

    # 4. Calculate resume section score metrics based on real parsed data
    text_content = latest_resume.extracted_text.lower() if (latest_resume and latest_resume.extracted_text) else ""
    try:
        exp_data = json.loads(latest_resume.experience_json) if (latest_resume and latest_resume.experience_json) else []
    except Exception:
        exp_data = []
    try:
        skills_data = json.loads(latest_resume.skills_json) if (latest_resume and latest_resume.skills_json) else []
    except Exception:
        skills_data = []
    try:
        edu_data = json.loads(latest_resume.education_json) if (latest_resume and latest_resume.education_json) else []
    except Exception:
        edu_data = []
    try:
        proj_data = json.loads(latest_resume.projects_json) if (latest_resume and latest_resume.projects_json) else []
    except Exception:
        proj_data = []

    sec_exp = min(len(exp_data) * 45, 95) if exp_data else 0
    sec_proj = min(len(proj_data) * 45, 90) if proj_data else (50 if 'project' in text_content else 0)
    sec_skills = min(len(skills_data) * 10, 95) if skills_data else 0
    sec_sum = 85 if (latest_resume and latest_resume.summary and len(latest_resume.summary) > 20) else (40 if len(text_content) > 300 else 10)
    sec_ach = 80 if (latest_resume and latest_resume.achievements_json and len(json.loads(latest_resume.achievements_json)) > 0) else 40
    sec_edu = 90 if edu_data else 0
    sec_certs = 85 if (latest_resume and latest_resume.certifications_json and len(json.loads(latest_resume.certifications_json)) > 0) else 30
    sec_lang = 70 if any(k in text_content for k in ['english', 'spanish', 'french', 'hindi', 'german']) else 40
    
    section_scores = [sec_exp, sec_proj, sec_skills, sec_sum, sec_ach, sec_edu, sec_certs, sec_lang]

    # 5. Calculate resume completeness
    completed_sections = sum(1 for s in [sec_exp, sec_skills, sec_edu, sec_proj, sec_sum] if s > 0)
    completed_percent = int((completed_sections / 5.0) * 100)
    completeness = [completed_percent, max(100 - completed_percent, 0)]

    # 6. Count matching jobs
    user_skills_set = set(s.lower() for s in skills_data) if skills_data else set()
    jobs_list = [
        ["React", "TypeScript", "Next.js"], [".NET", "Azure", "React"], ["React", "Node.js", "AWS"],
        ["JavaScript", "React"], ["Java", "SQL"], ["JavaScript", "HTML5"], ["Node.js", "MongoDB"],
        ["Kubernetes", "Docker"], ["React", "GraphQL"], ["Swift", "Node.js"],
        ["Java", "Spring Boot"], ["Angular", "AWS"], ["Python", "SQL"], ["React", "JavaScript"],
        ["AWS", "Terraform"], ["Node.js", "Vue.js"], ["Node.js", "Redis"], ["React", "TypeScript"],
        ["Go", "Docker", "PostgreSQL"], ["Python", "Machine Learning", "Pandas"]
    ]
    matching_jobs_count = 0
    for job_skills in jobs_list:
        job_skills_set = set(s.lower() for s in job_skills)
        if user_skills_set and user_skills_set.intersection(job_skills_set):
            matching_jobs_count += 1
    if matching_jobs_count == 0 and latest_resume:
        matching_jobs_count = 3
    
    return jsonify({
        'user': {
            'username': current_user.username,
            'email': current_user.email,
            'profile_pic': current_user.profile_pic,
            'role': current_user.role
        },
        'stats': {
            'ats_score': ats_score,
            'resume_score': resume_score,
            'total_interviews': interview_count,
            'completed_interviews': completed_count,
            'pending_interviews': interview_count - completed_count,
            'has_resume': latest_resume is not None,
            'has_report': latest_report is not None,
            'ats_trend': ats_trend,
            'readiness_trend': readiness_trend,
            'keyword_labels': keyword_labels,
            'keyword_data': keyword_data,
            'section_scores': section_scores,
            'completeness': completeness,
            'jobs_found': matching_jobs_count
        },
        'latest_resume': latest_resume.to_dict() if latest_resume else None,
        'latest_report': latest_report.to_dict() if latest_report else None,
        'recent_reports': [r.to_dict() for r in recent_reports],
        'notifications': [n.to_dict() for n in notifications]
    }), 200

@api_bp.route('/resume/analyze', methods=['POST'])
@token_required
def analyze_resume(current_user):
    t0 = time.time()
    if 'resume' not in request.files:
        return jsonify({'success': False, 'stage': 'upload', 'message': 'No resume file attached.'}), 400
        
    file = request.files['resume']
    job_role = request.form.get('job_role', 'Software Engineer')
    job_description = request.form.get('job_description', '')
    
    if file.filename == '':
        return jsonify({'success': False, 'stage': 'upload', 'message': 'No selected file.'}), 400
        
    # Check extension
    _, ext = os.path.splitext(file.filename)
    if ext.lower() not in ['.pdf', '.docx', '.doc']:
        return jsonify({'success': False, 'stage': 'validation', 'message': 'Supported formats are PDF and DOCX only.'}), 400
        
    # Read bytes and compute file hash
    file_bytes = file.read()
    if len(file_bytes) == 0:
        return jsonify({'success': False, 'stage': 'validation', 'message': 'The uploaded file is empty.'}), 400
        
    file_hash = hashlib.sha256(file_bytes).hexdigest()
    file.seek(0) # Reset stream position
    
    # Save file to uploads directory
    upload_dir = os.path.join(current_app.root_path, 'static', 'uploads', 'resumes')
    os.makedirs(upload_dir, exist_ok=True)
    
    filename = f"resume_{current_user.id}_{int(datetime.utcnow().timestamp())}_{secure_filename(file.filename)}"
    file_path = os.path.join(upload_dir, filename)
    file.save(file_path)
    
    logger.info(f"[RESUME_UPLOAD] user_id={current_user.id} file={file.filename} hash={file_hash}")
    
    # 1. Parse Resume Document
    t_parse = time.time()
    parsed_data = ResumeParser.parse_resume(file_path, filename=file.filename)
    logger.info(f"[RESUME_PARSE] user_id={current_user.id} success={parsed_data.get('success')} words={parsed_data.get('word_count', 0)} time={time.time()-t_parse:.3f}s")
    
    if not parsed_data.get('success', False):
        return jsonify({
            'success': False,
            'stage': 'text_extraction',
            'message': parsed_data.get('error', 'Unable to extract readable text from this document. Please ensure the document is not an image-only scanned PDF.')
        }), 400

    # 2. Deterministic ATS and Resume Scoring
    t_score = time.time()
    score_result = ResumeScorer.calculate_score(
        parsed_data,
        target_role=job_role,
        target_job_description=job_description
    )
    logger.info(f"[ATS_SCORING] user_id={current_user.id} ats={score_result['ats_score']} resume_score={score_result['resume_score']} time={time.time()-t_score:.3f}s")

    # 3. Semantic AI Quality Analysis
    t_ai = time.time()
    ai_result = AIService.analyze_resume(
        parsed_data['text'],
        parsed_data=parsed_data,
        job_role=job_role,
        job_description=job_description
    )
    
    # Optional Job Description Match analysis
    jd_match = None
    if job_description and len(job_description.strip()) > 20:
        jd_match = AIService.match_job_description(
            parsed_data['text'],
            parsed_data['skills'],
            job_description
        )
    logger.info(f"[AI_ANALYSIS] user_id={current_user.id} time={time.time()-t_ai:.3f}s")

    # Merge AI analysis details with ATS issues
    combined_analysis = {
        'strengths': ai_result.get('strengths', []),
        'weaknesses': ai_result.get('weaknesses', []),
        'missing_skills': ai_result.get('missing_skills', []),
        'suggestions': ai_result.get('suggestions', []),
        'ats_issues': score_result.get('ats_issues', []),
        'keyword_analysis': ai_result.get('keyword_analysis', {'present': [], 'missing': []}),
        'bullet_quality': ai_result.get('bullet_quality', []),
        'job_match': jd_match
    }

    # 4. Save Unique Record in Database
    resume_row = Resume(
        user_id=current_user.id,
        filename=file.filename,
        file_path=f"/static/uploads/resumes/{filename}",
        file_hash=file_hash,
        analysis_version="v2",
        job_role=job_role,
        target_job_description=job_description,
        extracted_text=parsed_data['text'],
        name=parsed_data.get('name') or current_user.username,
        email=parsed_data.get('email') or current_user.email,
        phone=parsed_data.get('phone'),
        location=parsed_data.get('location'),
        linkedin=parsed_data.get('linkedin'),
        github=parsed_data.get('github'),
        portfolio=parsed_data.get('portfolio'),
        title=parsed_data.get('title'),
        summary=parsed_data.get('summary'),
        skills_json=json.dumps(parsed_data.get('skills', [])),
        education_json=json.dumps(parsed_data.get('education', [])),
        experience_json=json.dumps(parsed_data.get('experience', [])),
        projects_json=json.dumps(parsed_data.get('projects', [])),
        certifications_json=json.dumps(parsed_data.get('certifications', [])),
        achievements_json=json.dumps(parsed_data.get('achievements', [])),
        ats_score=score_result['ats_score'],
        resume_score=score_result['resume_score'],
        score_breakdown_json=json.dumps(score_result['score_breakdown']),
        analysis_json=json.dumps(combined_analysis),
        processing_status='completed'
    )
    
    try:
        db.session.add(resume_row)
        
        # Dispatch notification
        notification = Notification(
            user_id=current_user.id,
            message=f"Resume Analysis for '{job_role}' complete! ATS score: {resume_row.ats_score}%"
        )
        db.session.add(notification)
        db.session.commit()
        
        logger.info(f"[DATABASE_SAVE] resume_id={resume_row.id} user_id={current_user.id} total_time={time.time()-t0:.3f}s")
        
        return jsonify({
            'success': True,
            'message': 'Resume analyzed successfully.',
            'resume': resume_row.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Database error saving resume: {e}")
        return jsonify({'success': False, 'message': f'Database error saving resume: {str(e)}'}), 500

@api_bp.route('/interview/start', methods=['POST'])
@token_required
def start_interview(current_user):
    data = request.get_json() or {}
    job_role = data.get('job_role', 'Software Engineer')
    experience_level = data.get('experience_level', 'Entry Level')
    difficulty = data.get('difficulty', 'Medium')
    question_types = data.get('question_types', ['Technical'])
    
    # Get user skills if available
    latest_resume = Resume.query.filter_by(user_id=current_user.id).order_by(Resume.created_at.desc()).first()
    skills = []
    if latest_resume and latest_resume.skills_json:
        skills = json.loads(latest_resume.skills_json)
        
    # Generate Questions
    questions_data = AIService.generate_questions(
        resume_skills=skills,
        job_role=job_role,
        experience_level=experience_level,
        difficulty=difficulty,
        question_types=question_types
    )
    
    if not questions_data:
        return jsonify({'message': 'Unable to generate interview questions. Try again later.'}), 500
        
    # Initialize Interview Session
    session = InterviewSession(
        user_id=current_user.id,
        job_role=job_role,
        experience_level=experience_level,
        difficulty=difficulty,
        question_types=",".join(question_types),
        current_question_index=0,
        status='pending'
    )
    
    try:
        db.session.add(session)
        db.session.flush() # Get session.id atomically without committing yet
        
        # Populate Questions Table
        for q in questions_data:
            q_row = InterviewQuestion(
                session_id=session.id,
                question_text=q.get('question_text') or 'No question text provided.',
                expected_answer=q.get('expected_answer') or '',
                hints=q.get('hints') or '',
                difficulty=q.get('difficulty') or difficulty,
                concept=q.get('concept') or 'General',
                time_limit=q.get('time_limit') or 60
            )
            db.session.add(q_row)
            
        db.session.commit()
        
        # Return all questions without expected answers / grades to prevent tampering
        output_questions = []
        for index, q in enumerate(session.questions):
            output_questions.append({
                'id': q.id,
                'index': index,
                'question_text': q.question_text,
                'hints': q.hints,
                'concept': q.concept,
                'difficulty': q.difficulty,
                'time_limit': q.time_limit
            })
            
        return jsonify({
            'message': 'Mock interview session created.',
            'session_id': session.id,
            'questions': output_questions
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Error initializing session: {str(e)}'}), 500

@api_bp.route('/interview/answer', methods=['POST'])
@token_required
def submit_answer(current_user):
    data = request.get_json() or {}
    question_id = data.get('question_id')
    user_answer = data.get('user_answer', '')
    
    if not question_id:
        return jsonify({'message': 'Question ID is required.'}), 400
        
    question = db.session.get(InterviewQuestion, int(question_id))
    if not question:
        return jsonify({'message': 'Question not found.'}), 404
        
    # Verify ownership
    session = question.session
    if session.user_id != current_user.id:
        return jsonify({'message': 'Access unauthorized.'}), 403
        
    # Evaluate Answer
    eval_result = AIService.evaluate_answer(
        question_text=question.question_text,
        expected_answer=question.expected_answer,
        user_answer=user_answer
    )
    
    question.user_answer = user_answer
    question.feedback_text = eval_result.get('feedback_text', 'Answer evaluated.')
    
    scores = eval_result.get('scores') or {}
    question.technical_score = scores.get('technical', 50)
    question.grammar_score = scores.get('grammar', 50)
    question.fluency_score = scores.get('fluency', 50)
    question.overall_score = scores.get('overall', 50)
    
    try:
        db.session.commit()
        return jsonify({
            'message': 'Answer processed.',
            'question_id': question.id,
            'scores': question.to_dict()['scores'],
            'feedback': question.feedback_text
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Error saving response: {str(e)}'}), 500

@api_bp.route('/interview/submit', methods=['POST'])
@token_required
def submit_interview(current_user):
    data = request.get_json() or {}
    session_id = data.get('session_id')
    
    if not session_id:
        return jsonify({'message': 'Session ID is required.'}), 400
        
    session = db.session.get(InterviewSession, int(session_id))
    if not session:
        return jsonify({'message': 'Session not found.'}), 404
        
    if session.user_id != current_user.id:
        return jsonify({'message': 'Access unauthorized.'}), 403
        
    if session.status == 'completed':
        # Report already generated, return existing
        existing_report = PerformanceReport.query.filter_by(session_id=session.id).first()
        if existing_report:
            return jsonify({
                'message': 'Report already created for this session.',
                'report': existing_report.to_dict()
            }), 200
            
    # Accumulate questions details
    session_questions = []
    for q in session.questions:
        session_questions.append({
            'question_text': q.question_text,
            'expected_answer': q.expected_answer,
            'user_answer': q.user_answer or '',
            'feedback_text': q.feedback_text or '',
            'scores': {
                'technical': q.technical_score,
                'grammar': q.grammar_score,
                'fluency': q.fluency_score,
                'overall': q.overall_score
            }
        })
        
    # Generate report
    report_data = AIService.generate_performance_report(session_questions, session.job_role)
    
    scores = report_data.get('scores') or {}
    
    communication_score = scores.get('communication') or report_data.get('communication_score') or report_data.get('communication') or 50
    technical_score = scores.get('technical') or report_data.get('technical_score') or report_data.get('technical') or 50
    confidence_score = scores.get('confidence') or report_data.get('confidence_score') or report_data.get('confidence') or 50
    grammar_score = scores.get('grammar') or report_data.get('grammar_score') or report_data.get('grammar') or 50
    vocabulary_score = scores.get('vocabulary') or report_data.get('vocabulary_score') or report_data.get('vocabulary') or 50
    fluency_score = scores.get('fluency') or report_data.get('fluency_score') or report_data.get('fluency') or 50

    report = PerformanceReport(
        user_id=current_user.id,
        session_id=session.id,
        overall_score=report_data.get('overall_score', 50),
        communication_score=communication_score,
        technical_score=technical_score,
        confidence_score=confidence_score,
        grammar_score=grammar_score,
        vocabulary_score=vocabulary_score,
        fluency_score=fluency_score,
        speaking_speed=report_data.get('speaking_speed', 120),
        strengths_json=json.dumps(report_data.get('strengths', [])),
        weaknesses_json=json.dumps(report_data.get('weaknesses', [])),
        roadmap_json=json.dumps(report_data.get('roadmap', {})),
        suggestions=report_data.get('suggestions', 'Practice regularly.')
    )
    
    session.status = 'completed'
    
    try:
        db.session.add(report)
        
        # Dispatch notification
        notification = Notification(
            user_id=current_user.id,
            message=f"Mock Interview for '{session.job_role}' graded! Overall score: {report.overall_score}%"
        )
        db.session.add(notification)
        db.session.commit()
        
        return jsonify({
            'message': 'Mock Interview completed and evaluated.',
            'report': report.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Error generating report: {str(e)}'}), 500

@api_bp.route('/reports/<int:report_id>', methods=['GET'])
@token_required
def get_report(current_user, report_id):
    report = db.session.get(PerformanceReport, int(report_id))
    if not report:
        return jsonify({'message': 'Report not found.'}), 404
        
    if report.user_id != current_user.id and current_user.role != 'admin':
        return jsonify({'message': 'Access unauthorized.'}), 403
        
    # Get session details
    session = report.session
    questions_list = [q.to_dict() for q in session.questions]
    
    output = report.to_dict()
    output['job_role'] = session.job_role
    output['experience_level'] = session.experience_level
    output['difficulty'] = session.difficulty
    output['questions'] = questions_list
    
    return jsonify({'report': output}), 200

@api_bp.route('/reports/<int:report_id>/download', methods=['GET'])
def download_report(report_id):
    # This does NOT require JWT in headers directly if clicked from a simple anchor target,
    # but we can verify ownership or token via query parameter ?token=xxx
    token = request.args.get('token', '')
    if not token:
        return "Unauthorized: Missing token query parameter.", 401
        
    try:
        data = jwt.decode(token, os.getenv("JWT_SECRET_KEY", "meetai_secret_key_998877"), algorithms=['HS256'])
        user = db.session.get(User, int(data['sub']))
        if not user:
            return "Unauthorized: User not found.", 401
    except Exception:
        return "Unauthorized: Invalid token.", 401
        
    report = db.session.get(PerformanceReport, int(report_id))
    if not report:
        return "Report not found.", 404
        
    if report.user_id != user.id and user.role != 'admin':
        return "Unauthorized access.", 403
        
    html = ReportService.generate_html_report(report.to_dict(), user, report.session)
    return html, 200

@api_bp.route('/companies', methods=['GET'])
def list_companies():
    # Hardcoded company lists and profiles
    companies_data = [
        {"name": "Google", "description": "Highly algorithmic, focuses heavily on scale, complexity, and system design."},
        {"name": "Amazon", "description": "Focused on customer obsession and leadership principles alongside data structure implementation."},
        {"name": "Microsoft", "description": "Strong emphasis on software patterns, architecture, API design, and OOP principles."},
        {"name": "Meta", "description": "Rapid product iterations, complex algorithms, system architecture, and React foundations."},
        {"name": "Netflix", "description": "Focuses on adaptability, performance, high throughput architectures, and culture alignment."},
        {"name": "Apple", "description": "Detail-oriented questions, systems programming, memory safety, and custom architectures."},
        {"name": "Infosys", "description": "Broad technical aptitude, object-oriented concepts, and basic database management."},
        {"name": "TCS", "description": "Logical puzzle solving, software engineering principles, SQL queries, and basic algorithms."},
        {"name": "Wipro", "description": "Core Java/Python fundamentals, web building blocks, and cloud basics."},
        {"name": "Accenture", "description": "Business case studies, cloud transformation projects, agile, and full-stack patterns."},
        {"name": "Capgemini", "description": "System migration strategies, database indexing, API integration concepts, and testing."},
        {"name": "IBM", "description": "Mainframes, hybrid cloud infrastructures, security rules, and analytics modeling."},
        {"name": "Oracle", "description": "Database internals, SQL query tuning, Java runtime environments, and virtualization."}
    ]
    return jsonify({'companies': companies_data}), 200

@api_bp.route('/companies/<string:name>', methods=['GET'])
@token_required
def get_company_prep(current_user, name):
    # Retrieve structured guidelines for specific companies
    mock_prep = {
        "Google": {
            "tips": [
                "Always state your algorithm complexity (Time & Space) before writing code.",
                "Discuss multiple approaches (brute force -> optimized) explaining trade-offs.",
                "Be ready for open-ended system design questions relating to petabyte scale."
            ],
            "coding": [
                {"title": "Merge k Sorted Lists", "type": "Hard", "description": "Merge k sorted linked lists and return it as one sorted list. Analyze complexity."},
                {"title": "Binary Tree Maximum Path Sum", "type": "Hard", "description": "Find the path in a binary tree that has the maximum sum of node values."}
            ],
            "behavioral": [
                "Tell me about a time you worked on a project with ambiguous requirements.",
                "How do you handle disagreement with a technical lead?"
            ]
        },
        "Amazon": {
            "tips": [
                "Study the 16 Leadership Principles intensely; frame ALL behavioral answers around them.",
                "Prepare for live coding focusing on graphs, BFS/DFS, and dynamic arrays."
            ],
            "coding": [
                {"title": "LRU Cache", "type": "Medium", "description": "Design a data structure that follows the constraints of a Least Recently Used (LRU) cache."},
                {"title": "Top K Frequent Words", "type": "Medium", "description": "Given an array of strings, return the k most frequent words."}
            ],
            "behavioral": [
                "Describe a situation where you had to make a decision without having all the information.",
                "Tell me about a time you went out of your way to deliver results for a customer."
            ]
        }
    }
    
    prep = mock_prep.get(name, {
        "tips": [
            "Be strong in core software engineering paradigms.",
            "Explain your thought process step by step during the coding challenges."
        ],
        "coding": [
            {"title": "Two Sum", "type": "Easy", "description": "Find indices of two numbers that add up to a target value."},
            {"title": "Reverse Linked List", "type": "Easy", "description": "Reverse a singly linked list in-place."}
        ],
        "behavioral": [
            "What has been your most challenging academic or professional project?",
            "How do you stay up-to-date with emerging technology trends?"
        ]
    })
    
    return jsonify({
        'company': name,
        'prep': prep
    }), 200

@api_bp.route('/notifications', methods=['GET'])
@token_required
def get_notifications(current_user):
    notifications = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).limit(15).all()
    return jsonify({'notifications': [n.to_dict() for n in notifications]}), 200

@api_bp.route('/notifications/read', methods=['POST'])
@token_required
def mark_read_notifications(current_user):
    notifications = Notification.query.filter_by(user_id=current_user.id, is_read=False).all()
    for n in notifications:
        n.is_read = True
    try:
        db.session.commit()
        return jsonify({'message': 'Notifications marked as read.'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Error: {str(e)}'}), 500

@api_bp.route('/feedback', methods=['POST'])
def submit_feedback():
    data = request.get_json() or {}
    name = data.get('name')
    email = data.get('email')
    message = data.get('message')
    
    if not name or not email or not message:
        return jsonify({'message': 'All fields are required.'}), 400
        
    feedback = Feedback(name=name, email=email, message=message)
    try:
        db.session.add(feedback)
        db.session.commit()
        return jsonify({'message': 'Thank you! Your feedback has been recorded.'}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Error recording feedback: {str(e)}'}), 500

# --- Additional AI Career Platform Mock APIs ---

@api_bp.route('/ats', methods=['GET'])
@token_required
def get_ats_data(current_user):
    latest_resume = Resume.query.filter_by(user_id=current_user.id).order_by(Resume.created_at.desc()).first()
    
    if not latest_resume:
        return jsonify({
            'ats_score': 0,
            'resume_health': 'No Resume Uploaded',
            'formatting_score': 0,
            'readability_score': 0,
            'keyword_density': {},
            'missing_keywords': [],
            'ats_trend': [],
            'completeness_data': [0, 100],
            'section_scores': {
                'Experience': 0, 'Projects': 0, 'Skills': 0, 'Summary': 0,
                'Achievements': 0, 'Education': 0, 'Certificates': 0, 'Languages': 0
            },
            'suggestions': [{'type': 'warning', 'text': 'Please upload a resume to run the ATS optimizer.'}]
        }), 200

    analysis = json.loads(latest_resume.analysis_json) if latest_resume.analysis_json else {}
    skills = json.loads(latest_resume.skills_json) if latest_resume.skills_json else []
    
    text = latest_resume.extracted_text.lower() if latest_resume.extracted_text else ""
    keyword_density = {}
    words_count = len(text.split()) if text else 1
    for s in skills[:5]:
        count = text.count(s.lower())
        keyword_density[s] = round((count / words_count) * 100, 1)

    missing_skills = analysis.get('missing_skills', [])
    missing_keywords = []
    categories = ['DevOps', 'Cloud', 'Database', 'Frameworks', 'Security']
    for idx, ms in enumerate(missing_skills):
        missing_keywords.append({
            'keyword': ms,
            'importance': 'High' if idx < 2 else 'Medium',
            'category': categories[idx % len(categories)]
        })

    suggestions_data = []
    raw_suggs = analysis.get('suggestions', [])
    for idx, s in enumerate(raw_suggs):
        suggestions_data.append({
            'type': 'error' if idx == 0 else 'warning' if idx == 1 else 'info',
            'text': s
        })
    if not suggestions_data:
        suggestions_data = [{'type': 'info', 'text': 'Resume formatting matches industry standards.'}]

    all_resumes = Resume.query.filter_by(user_id=current_user.id).order_by(Resume.created_at.asc()).all()
    ats_trend = [{'upload': f'Upload {i+1}', 'score': r.ats_score} for i, r in enumerate(all_resumes)]

    sec_exp = 90 if (latest_resume.experience_json and len(json.loads(latest_resume.experience_json)) > 0) else 0
    sec_proj = 85 if (latest_resume.experience_json and len(json.loads(latest_resume.experience_json)) > 1) else 40
    sec_skills = 95 if (latest_resume.skills_json and len(json.loads(latest_resume.skills_json)) > 0) else 0
    sec_sum = 80 if (latest_resume.extracted_text and len(latest_resume.extracted_text) > 200) else 30
    sec_ach = 75 if any(k in text for k in ['award', 'achieved', 'scholarship', 'winner']) else 50
    sec_edu = 90 if (latest_resume.education_json and len(json.loads(latest_resume.education_json)) > 0) else 0
    sec_certs = 80 if any(k in text for k in ['certificat', 'certified', 'license']) else 40
    sec_lang = 70 if any(k in text for k in ['english', 'spanish', 'french', 'hindi']) else 50

    section_scores = {
        'Experience': sec_exp,
        'Projects': sec_proj,
        'Skills': sec_skills,
        'Summary': sec_sum,
        'Achievements': sec_ach,
        'Education': sec_edu,
        'Certificates': sec_certs,
        'Languages': sec_lang
    }

    completeness_data = [
        {'section': 'Contact Info', 'status': 'Complete', 'score': 100},
        {'section': 'Summary', 'status': 'Complete' if sec_sum > 0 else 'Incomplete', 'score': sec_sum},
        {'section': 'Work Experience', 'status': 'Complete' if sec_exp > 0 else 'Incomplete', 'score': sec_exp},
        {'section': 'Education', 'status': 'Complete' if sec_edu > 0 else 'Incomplete', 'score': sec_edu},
        {'section': 'Skills', 'status': 'Complete' if sec_skills > 0 else 'Incomplete', 'score': sec_skills},
        {'section': 'Projects', 'status': 'Complete' if sec_proj > 40 else 'Incomplete', 'score': sec_proj}
    ]

    return jsonify({
        'ats_score': latest_resume.ats_score,
        'resume_health': 'Excellent' if latest_resume.ats_score > 80 else 'Good' if latest_resume.ats_score > 60 else 'Needs Improvement',
        'formatting_score': latest_resume.resume_score,
        'readability_score': 85 if len(text) > 1000 else 70,
        'keyword_density': keyword_density,
        'missing_keywords': missing_keywords,
        'ats_trend': ats_trend,
        'completeness_data': completeness_data,
        'section_scores': section_scores,
        'suggestions': suggestions_data
    }), 200

@api_bp.route('/jobs', methods=['GET'])
@token_required
def get_job_matcher_data(current_user):
    latest_resume = Resume.query.filter_by(user_id=current_user.id).order_by(Resume.created_at.desc()).first()
    
    user_skills = set()
    if latest_resume and latest_resume.skills_json:
        user_skills = set(s.lower() for s in json.loads(latest_resume.skills_json))

    jobs = [
        {"id": 1, "company": "Google", "logo": "https://api.dicebear.com/7.x/initials/svg?seed=Google", "role": "Senior Frontend Developer", "salary": "₹28 LPA", "location": "Bangalore, India", "type": "Remote", "experience": "5+ years", "skills": ["React", "TypeScript", "Next.js", "Tailwind"]},
        {"id": 2, "company": "Microsoft", "logo": "https://api.dicebear.com/7.x/initials/svg?seed=Microsoft", "role": "Software Engineer II", "salary": "₹24 LPA", "location": "Hyderabad, India", "type": "Hybrid", "experience": "3+ years", "skills": ["C#", ".NET", "Azure", "React"]},
        {"id": 3, "company": "Amazon", "logo": "https://api.dicebear.com/7.x/initials/svg?seed=Amazon", "role": "Full Stack Engineer", "salary": "₹26 LPA", "location": "Pune, India", "type": "On-site", "experience": "4+ years", "skills": ["React", "Node.js", "AWS", "DynamoDB"]},
        {"id": 4, "company": "Adobe", "logo": "https://api.dicebear.com/7.x/initials/svg?seed=Adobe", "role": "Frontend Developer", "salary": "₹20 LPA", "location": "Noida, India", "type": "Remote", "experience": "2+ years", "skills": ["JavaScript", "React", "Redux", "CSS Grid"]},
        {"id": 5, "company": "Infosys", "logo": "https://api.dicebear.com/7.x/initials/svg?seed=Infosys", "role": "System Engineer", "salary": "₹8 LPA", "location": "Mysore, India", "type": "On-site", "experience": "1+ years", "skills": ["Java", "SQL", "HTML", "CSS"]},
        {"id": 6, "company": "TCS", "logo": "https://api.dicebear.com/7.x/initials/svg?seed=TCS", "role": "Frontend Developer", "salary": "₹7.5 LPA", "location": "Chennai, India", "type": "Hybrid", "experience": "1-3 years", "skills": ["JavaScript", "HTML5", "CSS3", "Bootstrap"]},
        {"id": 7, "company": "Accenture", "logo": "https://api.dicebear.com/7.x/initials/svg?seed=Accenture", "role": "Application Developer", "salary": "₹12 LPA", "location": "Mumbai, India", "type": "Remote", "experience": "2-4 years", "skills": ["Node.js", "Express", "MongoDB", "React"]},
        {"id": 8, "company": "IBM", "logo": "https://api.dicebear.com/7.x/initials/svg?seed=IBM", "role": "Cloud Developer", "salary": "₹16 LPA", "location": "Bangalore, India", "type": "Hybrid", "experience": "3+ years", "skills": ["Kubernetes", "Docker", "Go", "Python"]},
        {"id": 9, "company": "Netflix", "logo": "https://api.dicebear.com/7.x/initials/svg?seed=Netflix", "role": "UI Engineer", "salary": "₹35 LPA", "location": "Mumbai, India", "type": "Remote", "experience": "5+ years", "skills": ["React", "TypeScript", "GraphQL", "WebPerf"]},
        {"id": 10, "company": "Meta", "logo": "https://api.dicebear.com/7.x/initials/svg?seed=Meta", "role": "Software Engineer", "salary": "₹32 LPA", "location": "Bangalore, India", "type": "Hybrid", "experience": "4+ years", "skills": ["React", "Flow", "PHP", "GraphQL"]},
        {"id": 11, "company": "Apple", "logo": "https://api.dicebear.com/7.x/initials/svg?seed=Apple", "role": "Full Stack Engineer", "salary": "₹30 LPA", "location": "Hyderabad, India", "type": "On-site", "experience": "4+ years", "skills": ["Swift", "Node.js", "PostgreSQL", "React"]},
        {"id": 12, "company": "Oracle", "logo": "https://api.dicebear.com/7.x/initials/svg?seed=Oracle", "role": "Java Cloud Developer", "salary": "₹18 LPA", "location": "Bangalore, India", "type": "On-site", "experience": "3+ years", "skills": ["Java", "Spring Boot", "Docker", "Oracle DB"]},
        {"id": 13, "company": "Capgemini", "logo": "https://api.dicebear.com/7.x/initials/svg?seed=Capgemini", "role": "Full Stack Dev", "salary": "₹11 LPA", "location": "Pune, India", "type": "Hybrid", "experience": "2+ years", "skills": ["Angular", "Spring Boot", "MySQL", "AWS"]},
        {"id": 14, "company": "Wipro", "logo": "https://api.dicebear.com/7.x/initials/svg?seed=Wipro", "role": "Project Engineer", "salary": "₹6.8 LPA", "location": "Bangalore, India", "type": "On-site", "experience": "Entry Level", "skills": ["Python", "SQL", "Git", "HTML"]},
        {"id": 15, "company": "Cognizant", "logo": "https://api.dicebear.com/7.x/initials/svg?seed=Cognizant", "role": "React UI Developer", "salary": "₹10 LPA", "location": "Kolkata, India", "type": "Remote", "experience": "2+ years", "skills": ["React", "JavaScript", "Redux Toolkit", "Webpack"]},
        {"id": 16, "company": "HCLTech", "logo": "https://api.dicebear.com/7.x/initials/svg?seed=HCLTech", "role": "Cloud Architect", "salary": "₹22 LPA", "location": "Noida, India", "type": "On-site", "experience": "7+ years", "skills": ["AWS", "Terraform", "CI/CD", "Python"]},
        {"id": 17, "company": "Tech Mahindra", "logo": "https://api.dicebear.com/7.x/initials/svg?seed=TechMahindra", "role": "Full Stack Engineer", "salary": "₹9 LPA", "location": "Pune, India", "type": "Hybrid", "experience": "2+ years", "skills": ["Node.js", "Vue.js", "MongoDB", "Git"]},
        {"id": 18, "company": "Paytm", "logo": "https://api.dicebear.com/7.x/initials/svg?seed=Paytm", "role": "Backend Engineer", "salary": "₹20 LPA", "location": "Noida, India", "type": "Hybrid", "experience": "3+ years", "skills": ["Node.js", "Redis", "Kafka", "MySQL"]},
        {"id": 19, "company": "Flipkart", "logo": "https://api.dicebear.com/7.x/initials/svg?seed=Flipkart", "role": "UI Developer II", "salary": "₹22 LPA", "location": "Bangalore, India", "type": "Hybrid", "experience": "3+ years", "skills": ["React", "TypeScript", "Node.js", "Sass"]},
        {"id": 20, "company": "Swiggy", "logo": "https://api.dicebear.com/7.x/initials/svg?seed=Swiggy", "role": "Software Engineer II", "salary": "₹24 LPA", "location": "Bangalore, India", "type": "Remote", "experience": "3+ years", "skills": ["Go", "React Native", "PostgreSQL", "AWS"]}
    ]

    matching_jobs = []
    for job in jobs:
        job_skills = set(s.lower() for s in job['skills'])
        if user_skills:
            overlap = user_skills.intersection(job_skills)
            match_score = int((len(overlap) / max(len(job_skills), 1)) * 100)
            job['match_score'] = max(match_score, 45 if overlap else 30)
        else:
            job['match_score'] = 50

        matching_jobs.append(job)

    matching_jobs = sorted(matching_jobs, key=lambda x: x['match_score'], reverse=True)
    remote_count = sum(1 for j in matching_jobs if j["type"] == "Remote")

    stats = {
        "jobs_found": len(matching_jobs),
        "best_match": f"{matching_jobs[0]['match_score']}%" if matching_jobs else "0%",
        "avg_salary": "₹18.5 LPA" if not user_skills else "₹24.0 LPA" if any(s in user_skills for s in ['aws', 'kubernetes', 'docker']) else "₹15.5 LPA",
        "remote_jobs": remote_count,
        "applied_jobs": 4 if latest_resume else 0,
        "saved_jobs": 5 if latest_resume else 0
    }
    
    return jsonify({
        "stats": stats,
        "jobs": matching_jobs
    }), 200

@api_bp.route('/roadmap', methods=['GET'])
@token_required
def get_career_roadmap(current_user):
    latest_resume = Resume.query.filter_by(user_id=current_user.id).order_by(Resume.created_at.desc()).first()
    
    if not latest_resume:
        return jsonify({
            "target_role": "Full Stack Developer",
            "learning_progress": 0,
            "timeline": [],
            "milestones": [],
            "skills_required": []
        }), 200

    analysis = json.loads(latest_resume.analysis_json) if latest_resume.analysis_json else {}
    missing_skills = analysis.get('missing_skills', [])
    skills = json.loads(latest_resume.skills_json) if latest_resume.skills_json else []

    timeline = []
    if missing_skills:
        timeline.append({"phase": "Phase 1: Bridge Core Skills Gap", "focus": f"Master: {', '.join(missing_skills[:2])}", "status": "In Progress", "progress": 30})
        if len(missing_skills) > 2:
            timeline.append({"phase": "Phase 2: Advanced Integrations", "focus": f"Learn and build systems using: {', '.join(missing_skills[2:4])}", "status": "Pending", "progress": 0})
        timeline.append({"phase": "Phase 3: Production & Deployment", "focus": "System Design, containerization, and cloud deployment setups", "status": "Pending", "progress": 0})
    else:
        timeline.append({"phase": "Phase 1: Professional Refactoring", "focus": "Clean Architecture, Unit Testing, and Performance Tuning", "status": "In Progress", "progress": 60})
        timeline.append({"phase": "Phase 2: Cloud Architectures", "focus": "Multi-region AWS setup, Docker/Kubernetes orchestration", "status": "Pending", "progress": 0})

    milestones = [
        {"title": "Core Foundations Validated", "desc": "Skills successfully parsed from uploaded resume", "status": "Completed"}
    ]
    for ms in missing_skills[:3]:
        milestones.append({
            "title": f"Master {ms}",
            "desc": f"Build technical capstone project incorporating {ms}",
            "status": "In Progress" if len(milestones) == 1 else "Pending"
        })
        
    required_skills = skills + missing_skills

    return jsonify({
        "target_role": "Software Engineer" if not skills else f"{skills[0]} Developer",
        "learning_progress": 72 if missing_skills else 95,
        "timeline": timeline,
        "milestones": milestones,
        "skills_required": required_skills[:12]
    }), 200

@api_bp.route('/skills', methods=['GET'])
@token_required
def get_skills_analysis(current_user):
    latest_resume = Resume.query.filter_by(user_id=current_user.id).order_by(Resume.created_at.desc()).first()
    
    if not latest_resume:
        return jsonify({
            'technical': [],
            'soft': [],
            'feedback': {'strengths': [], 'weaknesses': [], 'courses': []}
        }), 200

    skills = json.loads(latest_resume.skills_json) if latest_resume.skills_json else []
    analysis = json.loads(latest_resume.analysis_json) if latest_resume.analysis_json else {}

    tech_skills = []
    categories = ['Programming', 'Frameworks', 'Frontend', 'Databases', 'Cloud', 'DevOps']
    for idx, s in enumerate(skills):
        level = max(95 - idx * 5, 50)
        tech_skills.append({
            'name': s,
            'level': level,
            'category': categories[idx % len(categories)]
        })

    soft_skills = [
        {'name': 'Communication', 'level': 85},
        {'name': 'Problem Solving', 'level': 90},
        {'name': 'Teamwork', 'level': 80},
        {'name': 'Time Management', 'level': 75},
        {'name': 'Adaptability', 'level': 88}
    ]

    missing_skills = analysis.get('missing_skills', [])
    courses = []
    for ms in missing_skills[:3]:
        courses.append({
            'title': f'{ms} Complete Developer Bootcamp',
            'platform': 'Udemy',
            'duration': '20 hours'
        })
    if not courses:
        courses = [
            {'title': 'System Design & Scalability Masterclass', 'platform': 'Coursera', 'duration': '15 hours'}
        ]

    feedback = {
        'strengths': analysis.get('strengths', []),
        'weaknesses': analysis.get('weaknesses', []),
        'courses': courses
    }

    return jsonify({
        'technical': tech_skills,
        'soft': soft_skills,
        'feedback': feedback
    }), 200

@api_bp.route('/projects', methods=['GET'])
@token_required
def get_projects(current_user):
    latest_resume = Resume.query.filter_by(user_id=current_user.id).order_by(Resume.created_at.desc()).first()
    
    if not latest_resume:
        return jsonify({"projects": []}), 200

    skills = json.loads(latest_resume.skills_json) if latest_resume.skills_json else []
    
    projects = []
    if skills:
        primary_skill = skills[0]
        secondary_skill = skills[1] if len(skills) > 1 else 'Python'
        db_skill = next((s for s in skills if s.lower() in ['mongodb', 'sql', 'postgresql', 'sqlite', 'mysql']), 'SQLite')
        
        projects = [
            {
                "id": 1,
                "name": f"AI-Driven {primary_skill} Platform",
                "tech": f"{primary_skill}, {secondary_skill}, {db_skill}, Flask",
                "completion": 95,
                "github": "https://github.com/example/ai-platform",
                "live": "https://platform.techclevora.com",
                "ai_score": 98
            },
            {
                "id": 2,
                "name": f"Distributed {secondary_skill} Microservices",
                "tech": f"{secondary_skill}, Docker, {db_skill}",
                "completion": 88,
                "github": "https://github.com/example/microservices",
                "live": None,
                "ai_score": 92
            }
        ]
        
        if len(skills) > 2:
            projects.append({
                "id": 3,
                "name": f"Responsive {skills[2]} SPA",
                "tech": f"{skills[2]}, CSS Grid, Tailwind",
                "completion": 100,
                "github": "https://github.com/example/spa-app",
                "live": "https://spa.techclevora.com",
                "ai_score": 95
            })
    else:
        projects = [
            {"id": 1, "name": "Web Portfolio Showcase", "tech": "HTML, CSS, JavaScript", "completion": 100, "github": None, "live": None, "ai_score": 85}
        ]

    return jsonify({"projects": projects}), 200

@api_bp.route('/certificates', methods=['GET'])
@token_required
def get_certificates(current_user):
    latest_resume = Resume.query.filter_by(user_id=current_user.id).order_by(Resume.created_at.desc()).first()
    
    if not latest_resume:
        return jsonify({
            "stats": {"total": 0, "verified": 0, "pending": 0, "expired": 0},
            "certificates": []
        }), 200

    text = latest_resume.extracted_text.lower() if latest_resume.extracted_text else ""
    skills = json.loads(latest_resume.skills_json) if latest_resume.skills_json else []

    certs = []
    cert_id = 1
    
    if 'aws' in text or 'amazon' in text:
        certs.append({"id": cert_id, "name": "AWS Certified Solutions Architect", "platform": "Amazon Web Services", "issue_date": "2025-10-15", "expiry": "2028-10-15", "credential_id": "AWS-ASA-9988", "status": "Verified"})
        cert_id += 1
    if 'ux' in text or 'figma' in text or 'design' in text:
        certs.append({"id": cert_id, "name": "Google UX Design Professional Certificate", "platform": "Coursera / Google", "issue_date": "2025-06-20", "expiry": "N/A", "credential_id": "G-UX-1122", "status": "Verified"})
        cert_id += 1
    if 'react' in text or 'javascript' in text:
        certs.append({"id": cert_id, "name": "Meta Front-End Developer Certificate", "platform": "Coursera / Meta", "issue_date": "2025-03-10", "expiry": "N/A", "credential_id": "META-FED-3344", "status": "Verified"})
        cert_id += 1
    if 'docker' in text or 'kubernetes' in text:
        certs.append({"id": cert_id, "name": "Certified Kubernetes Administrator (CKA)", "platform": "CNCF / Linux Foundation", "issue_date": "2026-01-05", "expiry": "2029-01-05", "credential_id": "CKA-5566", "status": "Verified"})
        cert_id += 1
        
    if not certs and skills:
        certs.append({
            "id": 1,
            "name": f"Oracle Certified Professional: {skills[0]} Developer",
            "platform": "Oracle Academy",
            "issue_date": "Pending",
            "expiry": "N/A",
            "credential_id": "N/A",
            "status": "Pending"
        })

    stats = {
        "total": len(certs),
        "verified": sum(1 for c in certs if c["status"] == "Verified"),
        "pending": sum(1 for c in certs if c["status"] == "Pending"),
        "expired": sum(1 for c in certs if c["status"] == "Expired")
    }
    
    return jsonify({
        "stats": stats,
        "certificates": certs
    }), 200

@api_bp.route('/applications', methods=['GET'])
@token_required
def get_applications(current_user):
    latest_resume = Resume.query.filter_by(user_id=current_user.id).order_by(Resume.created_at.desc()).first()
    
    if not latest_resume:
        return jsonify({
            "applications": [],
            "upcoming_interviews": []
        }), 200

    skills = json.loads(latest_resume.skills_json) if latest_resume.skills_json else []
    primary = skills[0] if skills else "Software"

    applications = [
        {"id": "app-1", "company": "Google", "role": f"Senior {primary} Developer" if skills else "Senior Developer", "salary": "₹28 LPA", "applied_date": "2026-07-28", "status": "interview", "location": "Remote"},
        {"id": "app-2", "company": "Microsoft", "role": f"{primary} Engineer II" if skills else "Software Engineer II", "salary": "₹24 LPA", "applied_date": "2026-07-29", "status": "applied", "location": "Hybrid"},
        {"id": "app-3", "company": "Amazon", "role": f"Full Stack {primary} Engineer" if skills else "Full Stack Engineer", "salary": "₹26 LPA", "applied_date": "2026-07-30", "status": "technical", "location": "On-site"},
        {"id": "app-4", "company": "Adobe", "role": f"{primary} Developer" if skills else "Developer", "salary": "₹20 LPA", "applied_date": "2026-08-01", "status": "applied", "location": "Remote"},
        {"id": "app-5", "company": "Accenture", "role": "Application Developer", "salary": "₹12 LPA", "applied_date": "2026-07-25", "status": "hr", "location": "Remote"},
        {"id": "app-6", "company": "IBM", "role": "Cloud Developer", "salary": "₹16 LPA", "applied_date": "2026-07-26", "status": "offer", "location": "Hybrid"}
    ]
    
    interviews = [
        {"id": "int-1", "company": "Google", "date": "2026-08-10 14:00", "round": "Coding & Algorithms"},
        {"id": "int-2", "company": "Amazon", "date": "2026-08-12 16:30", "round": "System Design"}
    ]
    
    return jsonify({
        "applications": applications,
        "upcoming_interviews": interviews
    }), 200

@api_bp.route('/analytics', methods=['GET'])
@token_required
def get_analytics(current_user):
    latest_resume = Resume.query.filter_by(user_id=current_user.id).order_by(Resume.created_at.desc()).first()
    
    all_resumes = Resume.query.filter_by(user_id=current_user.id).order_by(Resume.created_at.asc()).all()
    ats_growth = [r.ats_score for r in all_resumes]
    while len(ats_growth) < 6:
        ats_growth.insert(0, max(ats_growth[0] - 5, 45) if ats_growth else 60)
    
    return jsonify({
        "resume_views": [10, 25, 40, 68, 110, 150] if latest_resume else [0, 0, 0, 0, 0, 0],
        "ats_growth": ats_growth,
        "application_trend": [1, 2, 4, 6, 8, 12] if latest_resume else [0, 0, 0, 0, 0, 0],
        "interview_success": {
            "applied": 12 if latest_resume else 0,
            "interviews": 4 if latest_resume else 0,
            "technical": 2 if latest_resume else 0,
            "hr": 1 if latest_resume else 0,
            "offers": 1 if latest_resume else 0
        },
        "salary_expectations": [
            {"company": "Accenture", "offered": 12, "expected": 14},
            {"company": "IBM", "offered": 16, "expected": 18},
            {"company": "Amazon", "offered": 26, "expected": 28},
            {"company": "Microsoft", "offered": 24, "expected": 26},
            {"company": "Google", "offered": 28, "expected": 30}
        ],
        "resume_downloads": 15 if latest_resume else 0
    }), 200

@api_bp.route('/reports', methods=['GET'])
@token_required
def get_reports_center(current_user):
    reports = PerformanceReport.query.filter_by(user_id=current_user.id).order_by(PerformanceReport.created_at.desc()).all()
    output = []
    for r in reports:
        output.append({
            "id": r.id,
            "name": f"AI Interview Assessment ({r.session.job_role})",
            "type": "Interview",
            "date": r.created_at.strftime('%Y-%m-%d') if r.created_at else datetime.now().strftime('%Y-%m-%d'),
            "score": r.overall_score,
            "format": "PDF"
        })
    if not output:
        latest_resume = Resume.query.filter_by(user_id=current_user.id).order_by(Resume.created_at.desc()).first()
        if latest_resume:
            output.append({
                "id": "rep-101",
                "name": f"Resume Optimization Audit ({latest_resume.filename})",
                "type": "Resume",
                "date": latest_resume.created_at.strftime('%Y-%m-%d') if latest_resume.created_at else datetime.now().strftime('%Y-%m-%d'),
                "score": latest_resume.resume_score,
                "format": "PDF"
            })
            output.append({
                "id": "rep-102",
                "name": "ATS Alignment Evaluation",
                "type": "ATS",
                "date": latest_resume.created_at.strftime('%Y-%m-%d') if latest_resume.created_at else datetime.now().strftime('%Y-%m-%d'),
                "score": latest_resume.ats_score,
                "format": "PDF"
            })
    return jsonify({"reports": output}), 200

# --- Bulk Resume Analyzer (HR / Recruiter Platform) APIs ---

def analyze_single_file(app, bulk_job_id, user_id, filepath, filename):
    with app.app_context():
        bulk_job = db.session.get(BulkJob, bulk_job_id)
        if not bulk_job:
            return
        
        try:
            # 1. Parse text from document using ResumeParser
            parsed_data = ResumeParser.parse_resume(filepath, filename=filename)
            if not parsed_data.get('success', False):
                bulk_job.failed_files += 1
                db.session.commit()
                return
            
            # Read bytes for file hash
            with open(filepath, 'rb') as f:
                f_bytes = f.read()
            f_hash = hashlib.sha256(f_bytes).hexdigest() if f_bytes else None

            # 2. Run deterministic scoring
            skills_list = parsed_data.get('skills', [])
            primary_role = f"{skills_list[0]} Developer" if skills_list else "Software Engineer"
            score_res = ResumeScorer.calculate_score(parsed_data, target_role=primary_role)
            
            # 3. Run semantic AI analysis
            ai_result = AIService.analyze_resume(parsed_data.get('text', ''), parsed_data=parsed_data, job_role=primary_role)
            
            combined_analysis = {
                'missing_skills': ai_result.get('missing_skills', []),
                'strengths': ai_result.get('strengths', []),
                'weaknesses': ai_result.get('weaknesses', []),
                'suggestions': ai_result.get('suggestions', []),
                'ats_issues': score_res.get('ats_issues', [])
            }

            # 4. Save parsed Resume row linked to BulkJob
            resume_row = Resume(
                user_id=user_id,
                bulk_job_id=bulk_job_id,
                filename=filename,
                file_path=filepath,
                file_hash=f_hash,
                analysis_version="v2",
                job_role=primary_role,
                extracted_text=parsed_data.get('text', ''),
                name=parsed_data.get('name') or filename.replace('.pdf', '').replace('.docx', '').replace('.doc', '').title(),
                email=parsed_data.get('email'),
                phone=parsed_data.get('phone'),
                location=parsed_data.get('location'),
                linkedin=parsed_data.get('linkedin'),
                github=parsed_data.get('github'),
                portfolio=parsed_data.get('portfolio'),
                title=parsed_data.get('title'),
                summary=parsed_data.get('summary'),
                skills_json=json.dumps(parsed_data.get('skills', [])),
                education_json=json.dumps(parsed_data.get('education', [])),
                experience_json=json.dumps(parsed_data.get('experience', [])),
                projects_json=json.dumps(parsed_data.get('projects', [])),
                certifications_json=json.dumps(parsed_data.get('certifications', [])),
                achievements_json=json.dumps(parsed_data.get('achievements', [])),
                ats_score=score_res['ats_score'],
                resume_score=score_res['resume_score'],
                score_breakdown_json=json.dumps(score_res['score_breakdown']),
                analysis_json=json.dumps(combined_analysis),
                processing_status='completed'
            )
            db.session.add(resume_row)
            
            # Increment processed count
            bulk_job.processed_files += 1
            db.session.commit()
            
        except Exception as e:
            db.session.rollback()
            bulk_job.failed_files += 1
            db.session.commit()
            print(f"Error analyzing {filename}: {str(e)}")

def process_bulk_resumes_async(app, bulk_job_id, user_id, file_tasks):
    with app.app_context():
        bulk_job = db.session.get(BulkJob, bulk_job_id)
        if bulk_job:
            bulk_job.status = 'processing'
            db.session.commit()

    if app.config.get('TESTING'):
        # Under testing, run sequentially in the main request thread to avoid thread connection issues
        for filepath, filename in file_tasks:
            analyze_single_file(app, bulk_job_id, user_id, filepath, filename)
    else:
        # Process files in parallel threads in production
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [
                executor.submit(analyze_single_file, app, bulk_job_id, user_id, filepath, filename)
                for filepath, filename in file_tasks
            ]
            for f in futures:
                try:
                    f.result()
                except Exception as e:
                    print(f"Worker thread error: {e}")

    with app.app_context():
        bulk_job = db.session.get(BulkJob, bulk_job_id)
        if bulk_job:
            bulk_job.status = 'completed'
            db.session.commit()

@api_bp.route('/bulk-upload', methods=['POST'])
@token_required
def bulk_upload(current_user):
    if 'files' not in request.files:
        return jsonify({'message': 'No files uploaded.'}), 400
        
    uploaded_files = request.files.getlist('files')
    if not uploaded_files or uploaded_files[0].filename == '':
        return jsonify({'message': 'No selected files.'}), 400
        
    bulk_dir = os.path.join(current_app.root_path, 'static', 'uploads', 'bulk')
    os.makedirs(bulk_dir, exist_ok=True)
    
    file_tasks = []
    
    for file in uploaded_files:
        filename = secure_filename(file.filename)
        if not filename:
            continue
            
        ext = os.path.splitext(filename)[1].lower()
        if ext not in ['.pdf', '.docx', '.doc', '.zip']:
            continue
            
        filepath = os.path.join(bulk_dir, filename)
        file.save(filepath)
        
        # Zip extractor helper
        if ext == '.zip':
            extract_dir = os.path.join(bulk_dir, f"zip_extract_{datetime.now().timestamp()}")
            os.makedirs(extract_dir, exist_ok=True)
            try:
                with zipfile.ZipFile(filepath, 'r') as zip_ref:
                    zip_ref.extractall(extract_dir)
                for root, dirs, files in os.walk(extract_dir):
                    for f in files:
                        f_ext = os.path.splitext(f)[1].lower()
                        if f_ext in ['.pdf', '.docx', '.doc']:
                            task_filepath = os.path.join(root, f)
                            file_tasks.append((task_filepath, f))
            except Exception as e:
                print(f"Error extracting ZIP: {e}")
        else:
            file_tasks.append((filepath, filename))
            
    if not file_tasks:
        return jsonify({'message': 'No valid document files found.'}), 400
        
    bulk_job = BulkJob(
        user_id=current_user.id,
        status='pending',
        total_files=len(file_tasks),
        processed_files=0,
        failed_files=0
    )
    db.session.add(bulk_job)
    db.session.commit()
    
    return jsonify({
        'message': 'Files uploaded successfully.',
        'bulk_job_id': bulk_job.id,
        'total_files': bulk_job.total_files,
        'file_tasks': file_tasks
    }), 201

@api_bp.route('/bulk-analysis', methods=['POST'])
@token_required
def bulk_analysis(current_user):
    data = request.get_json() or {}
    bulk_job_id = data.get('bulk_job_id')
    file_tasks = data.get('file_tasks', [])
    
    if not bulk_job_id or not file_tasks:
        return jsonify({'message': 'Missing job ID or tasks.'}), 400
        
    app = current_app._get_current_object()
    if current_app.config.get('TESTING'):
        # In test environment, run synchronously to prevent SQLite in-memory thread isolation errors
        process_bulk_resumes_async(app, int(bulk_job_id), current_user.id, file_tasks)
    else:
        threading.Thread(
            target=process_bulk_resumes_async,
            args=(app, int(bulk_job_id), current_user.id, file_tasks)
        ).start()
    
    return jsonify({'message': 'Analysis started in parallel.'}), 200

@api_bp.route('/bulk-dashboard', methods=['GET'])
@token_required
def get_bulk_dashboard(current_user):
    job_id = request.args.get('bulk_job_id')
    if job_id:
        bulk_job = db.session.get(BulkJob, int(job_id))
    else:
        bulk_job = BulkJob.query.filter_by(user_id=current_user.id).order_by(BulkJob.created_at.desc()).first()
        
    if not bulk_job:
        return jsonify({
            'job': None,
            'stats': {
                'total_uploaded': 0, 'processed': 0, 'failed': 0,
                'avg_ats': 0, 'max_ats': 0, 'min_ats': 0,
                'avg_exp': 0, 'avg_resume_score': 0, 'avg_job_match': 0
            },
            'candidates': [],
            'ranking': []
        }), 200
        
    resumes = Resume.query.filter_by(bulk_job_id=bulk_job.id).all()
    
    total = len(resumes)
    avg_ats = int(sum(r.ats_score for r in resumes) / total) if total > 0 else 0
    max_ats = max(r.ats_score for r in resumes) if total > 0 else 0
    min_ats = min(r.ats_score for r in resumes) if total > 0 else 0
    avg_resume = int(sum(r.resume_score for r in resumes) / total) if total > 0 else 0
    
    exp_years = []
    for r in resumes:
        years = 0
        if r.experience_json:
            try:
                exp_list = json.loads(r.experience_json)
                years = len(exp_list) * 2
            except Exception:
                pass
        exp_years.append(years)
    avg_exp = round(sum(exp_years) / len(exp_years), 1) if total > 0 else 0.0
    avg_match = int(avg_ats * 0.95)

    stats = {
        'total_uploaded': bulk_job.total_files,
        'processed': bulk_job.processed_files,
        'failed': bulk_job.failed_files,
        'avg_ats': avg_ats,
        'max_ats': max_ats,
        'min_ats': min_ats,
        'avg_exp': avg_exp,
        'avg_resume_score': avg_resume,
        'avg_job_match': avg_match
    }

    candidates = []
    for idx, r in enumerate(resumes):
        skills_list = json.loads(r.skills_json) if r.skills_json else []
        candidates.append({
            'id': r.id,
            'name': r.name,
            'email': r.email or 'N/A',
            'phone': r.phone or 'N/A',
            'ats_score': r.ats_score,
            'resume_score': r.resume_score,
            'experience': f"{exp_years[idx]} Yrs",
            'skills': ', '.join(skills_list[:3]),
            'match_score': int(r.ats_score * 0.95),
            'status': 'Done'
        })

    sorted_resumes = sorted(resumes, key=lambda x: x.ats_score, reverse=True)
    ranking = []
    for rank_idx, r in enumerate(sorted_resumes):
        score = r.ats_score
        recommendation = "Upskill Required"
        if score >= 90: recommendation = "Hire Immediately"
        elif score >= 80: recommendation = "Strong Match"
        elif score >= 70: recommendation = "Interview"
        elif score >= 50: recommendation = "Consider"
        
        ranking.append({
            'rank': rank_idx + 1,
            'name': r.name,
            'score': score,
            'recommendation': recommendation
        })

    return jsonify({
        'job': bulk_job.to_dict(),
        'stats': stats,
        'candidates': candidates,
        'ranking': ranking
    }), 200

@api_bp.route('/candidate/<int:resume_id>', methods=['GET'])
@token_required
def get_candidate_details(current_user, resume_id):
    resume = db.session.get(Resume, int(resume_id))
    if not resume:
        return jsonify({'message': 'Candidate not found.'}), 404
        
    if resume.user_id != current_user.id and current_user.role != 'admin':
        return jsonify({'message': 'Unauthorized access.'}), 403
        
    return jsonify({'candidate': resume.to_dict()}), 200

@api_bp.route('/download-all/<int:bulk_job_id>', methods=['GET'])
def download_all_reports(bulk_job_id):
    resumes = Resume.query.filter_by(bulk_job_id=bulk_job_id).all()
    if not resumes:
        return "No reports found for this job ID.", 404
        
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
        for r in resumes:
            user = db.session.get(User, r.user_id)
            html_content = ReportService.generate_resume_html_report(r.to_dict(), user)
            zip_file.writestr(f"{secure_filename(r.name)}_assessment.html", html_content)
            
    zip_buffer.seek(0)
    return send_file(
        zip_buffer,
        mimetype='application/zip',
        as_attachment=True,
        download_name=f"bulk_job_{bulk_job_id}_reports.zip"
    )

@api_bp.route('/analysis/<int:resume_id>', methods=['DELETE'])
@token_required
def delete_candidate_analysis(current_user, resume_id):
    resume = db.session.get(Resume, int(resume_id))
    if not resume:
        return jsonify({'message': 'Candidate not found.'}), 404
        
    if resume.user_id != current_user.id and current_user.role != 'admin':
        return jsonify({'message': 'Access unauthorized.'}), 403
        
    db.session.delete(resume)
    db.session.commit()
    return jsonify({'message': 'Candidate analysis deleted.'}), 200

