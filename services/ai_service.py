import os
import json
import logging
import google.generativeai as genai

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure Gemini SDK
api_key = os.getenv("GEMINI_API_KEY", "")
if api_key:
    genai.configure(api_key=api_key)
    logger.info("Gemini API key found and configured.")
else:
    logger.warning("No GEMINI_API_KEY env variable found. Using fallback mock service.")

class AIService:
    @staticmethod
    def _call_gemini_json(prompt, system_instruction=None):
        """Helper to invoke Gemini with structured JSON output configuration."""
        if not api_key:
            return None
            
        try:
            # We use gemini-1.5-flash for speed and reliability in JSON format output
            model_name = "gemini-1.5-flash"
            
            config = {
                "response_mime_type": "application/json"
            }
            
            if system_instruction:
                model = genai.GenerativeModel(
                    model_name=model_name,
                    generation_config=config,
                    system_instruction=system_instruction
                )
            else:
                model = genai.GenerativeModel(
                    model_name=model_name,
                    generation_config=config
                )
                
            response = model.generate_content(prompt)
            if response and response.text:
                return json.loads(response.text.strip())
        except Exception as e:
            logger.error(f"Gemini API invocation error: {e}")
        return None

    @classmethod
    def analyze_resume(cls, resume_text, parsed_data=None, job_role="Software Engineer", job_description=None):
        """
        Runs semantic AI quality analysis on the actual extracted resume text.
        Never fabricates candidate details or invents information not present in the document.
        """
        if not resume_text or len(resume_text.strip()) < 30:
            return {
                "strengths": [],
                "weaknesses": ["Document text is insufficient or empty."],
                "missing_skills": [],
                "suggestions": ["Upload a clear document with selectable text and standard sections."],
                "keyword_analysis": {"present": [], "missing": []},
                "bullet_quality": []
            }

        jd_context = f"\nTarget Job Description:\n{job_description}\n" if job_description else ""

        prompt = f"""
Analyze ONLY the resume supplied below for the target role: "{job_role}".
{jd_context}
Do not use information from previous requests, examples, training examples, or hypothetical candidates.
Do not invent candidate information or fake achievements.
If information is missing, return empty arrays.

RESUME_TEXT:
<<<
{resume_text}
>>>

Provide the output strictly in the following JSON format:
{{
    "strengths": ["specific strength from resume", "another strength..."],
    "weaknesses": ["specific gap or formatting issue in resume", "another gap..."],
    "missing_skills": ["important industry skill missing for this role", "..."],
    "suggestions": ["actionable advice to improve this specific resume", "..."],
    "keyword_analysis": {{
        "present": ["keywords found in resume"],
        "missing": ["keywords recommended for role"]
    }},
    "bullet_quality": ["feedback on experience bullet points"]
}}
"""
        system_inst = "You are a professional ATS auditor and engineering hiring manager. Analyze ONLY the supplied resume text. Return valid JSON only."
        res = cls._call_gemini_json(prompt, system_instruction=system_inst)
        if res and isinstance(res, dict) and "strengths" in res:
            return {
                "strengths": res.get("strengths", []),
                "weaknesses": res.get("weaknesses", []),
                "missing_skills": res.get("missing_skills", []),
                "suggestions": res.get("suggestions", []),
                "keyword_analysis": res.get("keyword_analysis", {"present": [], "missing": []}),
                "bullet_quality": res.get("bullet_quality", [])
            }

        # Deterministic semantic fallback derived dynamically from actual parsed data
        parsed = parsed_data or {}
        actual_skills = set(s.lower() for s in parsed.get('skills', []))
        sections_missing = parsed.get('sections_missing', [])
        candidate = parsed.get('candidate', {})
        experience = parsed.get('experience', [])
        projects = parsed.get('projects', [])

        from services.resume_scorer import ResumeScorer
        benchmark = ResumeScorer.ROLE_BENCHMARK_SKILLS.get(job_role, ResumeScorer.ROLE_BENCHMARK_SKILLS['Software Engineer'])
        missing_role_skills = [b for b in benchmark if b.lower() not in actual_skills]
        matched_role_skills = [b for b in benchmark if b.lower() in actual_skills]

        strengths = []
        if len(actual_skills) >= 6:
            strengths.append(f"Strong technical footprint with {len(actual_skills)} identified competencies ({', '.join(list(parsed.get('skills', []))[:4])}).")
        if len(experience) >= 1:
            strengths.append(f"Documented professional experience timeline with {len(experience)} position(s).")
        if len(projects) >= 1:
            strengths.append(f"Practical portfolio demonstrates hands-on implementation ({len(projects)} projects identified).")
        if candidate.get('github') or candidate.get('portfolio') or candidate.get('linkedin'):
            strengths.append("Direct links to digital profiles (GitHub/LinkedIn/Portfolio) present for technical verification.")
        if not strengths:
            strengths.append("Readable document structure with foundational engineering keywords.")

        weaknesses = []
        if sections_missing:
            human_missing = [s.capitalize() for s in sections_missing if s not in ['languages', 'achievements']]
            if human_missing:
                weaknesses.append(f"Missing standard sections: {', '.join(human_missing)}.")
        if not candidate.get('phone') or not candidate.get('email'):
            weaknesses.append("Incomplete contact information in header (missing verified phone or email).")
        if missing_role_skills:
            weaknesses.append(f"Missing core competencies typical for {job_role}: {', '.join(missing_role_skills[:3])}.")
        if len(experience) == 0:
            weaknesses.append("No distinct work history or internship records identified.")

        suggestions = []
        if missing_role_skills:
            suggestions.append(f"Consider integrating experience or coursework covering: {', '.join(missing_role_skills[:4])}.")
        suggestions.append("Ensure every work experience bullet opens with a strong action verb and includes quantifiable metrics (e.g., % improvement, scale).")
        if 'summary' in sections_missing:
            suggestions.append("Add a 2-3 sentence Professional Summary tailored specifically to the target job role.")

        return {
            "strengths": strengths,
            "weaknesses": weaknesses,
            "missing_skills": missing_role_skills[:5],
            "suggestions": suggestions,
            "keyword_analysis": {
                "present": matched_role_skills,
                "missing": missing_role_skills[:5]
            },
            "bullet_quality": ["Ensure all experience points follow the Action + Context + Quantifiable Result formula."]
        }

    @classmethod
    def match_job_description(cls, resume_text, parsed_skills, job_description):
        """
        Deep semantic comparison between resume text and a specific job description.
        """
        if not job_description or len(job_description.strip()) < 20:
            return None

        prompt = f"""
Compare the following candidate resume with the target job description.
Analyze specific skills overlap, missing requirements, experience alignment, and keyword matches.

RESUME_TEXT:
<<<
{resume_text}
>>>

JOB_DESCRIPTION:
<<<
{job_description}
>>>

Provide output strictly in JSON format:
{{
    "match_percentage": 78,
    "matched_skills": ["Python", "Flask", "PostgreSQL"],
    "missing_skills": ["AWS", "Docker", "CI/CD"],
    "matched_keywords": ["RESTful API", "Microservices", "Unit Testing"],
    "missing_keywords": ["Kubernetes", "GraphQL", "Agile"],
    "experience_match": "High/Medium/Low - explanation",
    "education_match": "High/Medium/Low - explanation",
    "role_match": "Strong/Moderate/Weak - summary",
    "recommendations": ["specific advice for this job application"]
}}
"""
        res = cls._call_gemini_json(prompt, system_instruction="You are an expert technical recruiter analyzing resume-to-job-fit.")
        if res and isinstance(res, dict) and "match_percentage" in res:
            return res

        # Deterministic fallback JD matching
        from services.resume_parser import ResumeParser
        jd_skills_data = ResumeParser.extract_skills(job_description)
        jd_skills = set(s.lower() for s in jd_skills_data['all'])
        user_skills = set(s.lower() for s in (parsed_skills or []))

        matched = [s for s in parsed_skills if s.lower() in jd_skills]
        missing = [s for s in jd_skills_data['all'] if s.lower() not in user_skills]

        if jd_skills:
            match_pct = int((len(matched) / len(jd_skills)) * 100)
        else:
            match_pct = 70

        match_pct = min(max(match_pct, 20), 95)

        return {
            "match_percentage": match_pct,
            "matched_skills": matched,
            "missing_skills": missing[:6],
            "matched_keywords": matched[:5],
            "missing_keywords": missing[:5],
            "experience_match": "Moderate" if len(matched) >= 3 else "Entry Alignment",
            "education_match": "Standard Alignment",
            "role_match": "Strong" if match_pct >= 75 else "Developing",
            "recommendations": [
                f"Highlight experience with {', '.join(missing[:3])} in your project portfolio." if missing else "Your skills match the core requirements of this role well."
            ]
        }

    @classmethod
    def generate_questions(cls, resume_skills, job_role, experience_level, difficulty, question_types):
        skills_str = ", ".join(resume_skills) if resume_skills else "General technical skills"
        q_types_str = ", ".join(question_types) if question_types else "Technical, HR, Behavioral"
        
        prompt = f"""
        Generate exactly 5 interview questions for a candidate with the following profile:
        - Job Role: {job_role}
        - Experience Level: {experience_level}
        - Difficulty: {difficulty}
        - Resume Skills: {skills_str}
        - Question Types to focus on: {q_types_str}
        
        Provide the output in the following JSON format:
        {{
            "questions": [
                {{
                    "question_text": "Describe the difference between virtual DOM and shadow DOM in React.",
                    "expected_answer": "Virtual DOM is a React-specific concept that mirrors the UI in memory, while Shadow DOM is a web standard for encapsulating styles and markup in web components.",
                    "hints": "Think about React performance updates versus web components scoping.",
                    "difficulty": "{difficulty}",
                    "concept": "Frontend Architecture",
                    "time_limit": 90
                }},
                ...
            ]
        }}
        """
        
        res = cls._call_gemini_json(prompt, system_instruction="You are a professional technical interviewer compiling interview sheets.")
        if res and isinstance(res, dict) and "questions" in res:
            return res["questions"]
            
        # Fallback Mock Data
        mock_bank = {
            "Software Engineer": [
                {"question_text": "Explain the time and space complexity of QuickSort in worst and average cases.", "expected_answer": "Average time complexity is O(N log N) and space complexity is O(log N). Worst case time complexity is O(N^2) if pivot choices are sub-optimal.", "hints": "Pivot selection affects recursion depth.", "concept": "Algorithms", "time_limit": 90},
                {"question_text": "What is the difference between an abstract class and an interface?", "expected_answer": "An interface defines a contract of behavior with no state, while an abstract class can provide partial implementation and fields.", "hints": "Abstract classes allow sharing of state/fields.", "concept": "OOP", "time_limit": 60},
                {"question_text": "How do you prevent SQL Injection attacks in database-driven applications?", "expected_answer": "By using parameterized queries (prepared statements), ORM libraries, and validating/sanitizing inputs.", "hints": "Avoid concatenating user input directly into queries.", "concept": "Security", "time_limit": 60},
                {"question_text": "Tell me about a difficult technical challenge you solved and how you approached it.", "expected_answer": "The user should demonstrate structured problem-solving: identifying constraints, evaluating alternatives, selecting a path, and running checks.", "hints": "Use the STAR method (Situation, Task, Action, Result).", "concept": "Behavioral", "time_limit": 120},
                {"question_text": "Why do you want to join our organization and work as a Software Engineer?", "expected_answer": "Aligning personal career growth, company technology stack, and engineering culture.", "hints": "Mention specific products or aspects of company engineering.", "concept": "HR", "time_limit": 60}
            ],
            "Web Developer": [
                {"question_text": "What is the event loop in JavaScript and how does it work?", "expected_answer": "The event loop is a mechanism that allows JS to perform non-blocking I/O operations by offloading tasks to the system kernel and processing callback queues once the call stack is empty.", "hints": "Mention the Call Stack, Web APIs, and Callback/Microtask Queues.", "concept": "JavaScript Engine", "time_limit": 90},
                {"question_text": "Explain CSS flexbox vs CSS grid and when to use each.", "expected_answer": "Flexbox is designed for one-dimensional layouts (row OR column), whereas Grid is designed for two-dimensional layouts (both rows AND columns simultaneously).", "hints": "Think about axes control.", "concept": "CSS Layout", "time_limit": 60},
                {"question_text": "Describe the state management options in React and how they compare.", "expected_answer": "Options include local state (useState), Context API for prop-drilling prevention, and external state stores like Redux, Zustand, or Recoil for larger applications.", "hints": "Discuss prop-drilling, re-renders, and complexity.", "concept": "React state", "time_limit": 90},
                {"question_text": "What are REST APIs and what are standard HTTP methods?", "expected_answer": "REST is architectural style using HTTP. Standard methods are GET (read), POST (create), PUT (update), DELETE (remove), and PATCH (partial update).", "hints": "Mention statelessness and standard status codes.", "concept": "Network APIs", "time_limit": 60},
                {"question_text": "Tell me about a project where you had to work in a team to build web components.", "expected_answer": "Explain collaboration, version control conflicts, component library usage, and deployment workflow.", "hints": "Use the STAR framework.", "concept": "HR / Behavioral", "time_limit": 90}
            ]
        }
        
        # Select closest matching mock set
        questions = mock_bank.get(job_role, mock_bank["Software Engineer"])
        # Custom adjustments based on difficulty/skills
        for idx, q in enumerate(questions):
            q["difficulty"] = difficulty
            if resume_skills and idx < len(resume_skills):
                # Customize concept using skills
                q["concept"] = f"Application of {resume_skills[idx]}"
        return questions

    @classmethod
    def evaluate_answer(cls, question_text, expected_answer, user_answer):
        if not user_answer or len(user_answer.strip()) < 3:
            return {
                "feedback_text": "No answer was recorded, or it was too brief. Please attempt the question with more details.",
                "scores": {
                    "technical": 10,
                    "grammar": 10,
                    "fluency": 10,
                    "overall": 10
                }
            }
            
        prompt = f"""
        As a technical interviewer, evaluate the following candidate response against the expected answer:
        
        Question: "{question_text}"
        Expected Answer Guidelines: "{expected_answer}"
        Candidate Answer: "{user_answer}"
        
        Analyze the correctness of technical points, grammatical structure, fluency of expression, and overall quality.
        Rate each score from 0 to 100. Provide clear, constructive feedback on how to improve.
        
        Output format:
        {{
            "feedback_text": "Constructive feedback details...",
            "scores": {{
                "technical": 80,
                "grammar": 90,
                "fluency": 85,
                "overall": 85
            }}
        }}
        """
        
        res = cls._call_gemini_json(prompt, system_instruction="You are a strict yet helpful engineering interviewer grading a mock test.")
        if res and isinstance(res, dict):
            return res
            
        # Fallback Mock Evaluation Logic
        # Measure similarity, keyword matching, length
        words = user_answer.lower().split()
        expected_keywords = [w.lower() for w in expected_answer.split() if len(w) > 4][:10]
        matches = [kw for kw in expected_keywords if kw in user_answer.lower()]
        
        keyword_ratio = len(matches) / max(len(expected_keywords), 1)
        length_factor = min(len(words) / 30.0, 1.0) # ideal answers have around 30+ words
        
        tech_score = int(35 + (keyword_ratio * 45) + (length_factor * 20))
        tech_score = min(max(tech_score, 20), 98)
        
        grammar_score = 90 if " I " in user_answer or "the" in user_answer else 75
        fluency_score = int(50 + (length_factor * 40))
        overall_score = int((tech_score * 0.5) + (grammar_score * 0.25) + (fluency_score * 0.25))
        
        feedback_notes = []
        if keyword_ratio < 0.3:
            feedback_notes.append("Try referencing key terminology such as " + ", ".join(expected_keywords[:3]) + ".")
        else:
            feedback_notes.append("Good usage of relevant terms.")
            
        if len(words) < 15:
            feedback_notes.append("Your response was very brief. Elaborate further by citing specific engineering examples or system structures.")
        else:
            feedback_notes.append("Elaborated well, showing clear conceptual command.")
            
        return {
            "feedback_text": " ".join(feedback_notes),
            "scores": {
                "technical": tech_score,
                "grammar": grammar_score,
                "fluency": fluency_score,
                "overall": overall_score
            }
        }

    @classmethod
    def generate_performance_report(cls, session_questions, job_role):
        # session_questions is a list of dicts with: question_text, expected_answer, user_answer, feedback_text, scores_dict
        q_summary = []
        for idx, q in enumerate(session_questions):
            q_summary.append(f"Q{idx+1}: {q['question_text']}\nCandidate Answer: {q.get('user_answer', 'None')}\nScores: {q.get('scores', {})}\nFeedback: {q.get('feedback_text', 'None')}")
        
        q_summary_str = "\n\n".join(q_summary)
        
        prompt = f"""
        Compile an overall performance report for the candidate based on these interview question transcriptions for the role of "{job_role}".
        Generate overall score, communication score, technical score, confidence score, grammar score, vocabulary score, and fluency score (all 0 to 100).
        Also provide lists of strengths, weaknesses, generic suggestions, and a structured career roadmap with:
        - "missing_skills": list of skills
        - "courses": list of course recommendations (with provider, e.g. "Coursera: React Basics")
        - "certifications": list of professional certifications
        - "books": list of technical books
        - "youtube_videos": list of recommended search queries or channels
        - "timeline": a simple roadmap outline (e.g. Week 1, Month 1, Month 2 milestones)
        
        Output format:
        {{
            "overall_score": 82,
            "communication_score": 85,
            "technical_score": 80,
            "confidence_score": 75,
            "grammar_score": 88,
            "vocabulary_score": 82,
            "fluency_score": 84,
            "speaking_speed": 130, // words per minute estimation
            "strengths": ["Strong understanding of event cycles", "Good structure of verbal patterns"],
            "weaknesses": ["Hesitated when asked about complexity metrics", "Missed database normalizations"],
            "suggestions": "Practice explaining algorithms using the STAR method.",
            "roadmap": {{
                "missing_skills": ["Algorithms", "AWS Deployment"],
                "courses": ["Coursera: Advanced Data Structures", "Udemy: AWS Cloud Practitioner"],
                "certifications": ["AWS Cloud Practitioner", "Google Cloud Digital Leader"],
                "books": ["Cracking the Coding Interview by Gayle Laakmann McDowell"],
                "youtube_videos": ["CS50 Lectures", "System Design Fight Club"],
                "timeline": [
                    {{"phase": "Week 1-2", "focus": "Algorithms & Complexity analyses"}},
                    {{"phase": "Month 1", "focus": "Database tuning and indexing principles"}},
                    {{"phase": "Month 2", "focus": "Cloud deployments & CI/CD automation setups"}}
                ]
            }}
        }}
        
        Transcripts:
        {q_summary_str}
        """
        
        res = cls._call_gemini_json(prompt, system_instruction="You are an executive career advisor and principal technical grader.")
        if res and isinstance(res, dict):
            return res
            
        # Fallback Mock Report
        avg_tech = int(sum(q.get('scores', {}).get('technical', 50) for q in session_questions) / len(session_questions)) if session_questions else 65
        avg_grammar = int(sum(q.get('scores', {}).get('grammar', 60) for q in session_questions) / len(session_questions)) if session_questions else 70
        avg_fluency = int(sum(q.get('scores', {}).get('fluency', 55) for q in session_questions) / len(session_questions)) if session_questions else 68
        overall = int((avg_tech * 0.4) + (avg_grammar * 0.3) + (avg_fluency * 0.3))
        
        return {
            "overall_score": overall,
            "communication_score": int((avg_grammar + avg_fluency) / 2) + 5,
            "technical_score": avg_tech,
            "confidence_score": 75,
            "grammar_score": avg_grammar,
            "vocabulary_score": 78,
            "fluency_score": avg_fluency,
            "speaking_speed": 125,
            "strengths": ["Structure and clear explanation of processes", "Broad vocabulary use", "Consistent grammatical form"],
            "weaknesses": ["Could outline database constraints and execution patterns in higher detail", "Requires more confident execution of complex system logic description"],
            "suggestions": f"Focus on structuring technical arguments. Read books on system patterns related to {job_role}.",
            "roadmap": {
                "missing_skills": ["System Design", "Cloud Hosting", "Unit Testing"],
                "courses": [f"Coursera: Advanced {job_role} Patterns", "Udemy: Clean Architecture Masterclass"],
                "certifications": ["AWS Certified Developer Associate", "Professional Scrum Master I"],
                "books": [f"Designing Data-Intensive Applications by Martin Kleppmann", f"Clean Code by Robert C. Martin"],
                "youtube_videos": ["Hussein Nasser Backend engineering", "Web Dev Simplified CSS grids"],
                "timeline": [
                    {"phase": "Week 1", "focus": "Focus on data structures, testing routines"},
                    {"phase": "Week 2-4", "focus": "Build full stack projects incorporating mock services"},
                    {"phase": "Month 2", "focus": "Containerize, deploy on AWS/GCP, setup GitHub Actions CI/CD"}
                ]
            }
        }
