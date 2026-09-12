import unittest
import os
import io
import json
import docx
import PyPDF2
from app import create_app
from models import db, User, Resume, InterviewSession, PerformanceReport
from services.resume_parser import ResumeParser
from services.resume_scorer import ResumeScorer
from services.ai_service import AIService
from services.report_service import ReportService

def create_sample_pdf_bytes(text_content):
    """Generates a standard compliant valid PDF binary stream in pure Python."""
    normalized = text_content.replace('•', '-').replace('–', '-').replace('—', '-').replace('“', '"').replace('”', '"')
    lines = normalized.strip().split('\n')
    text_ops = []
    y = 720
    for line in lines:
        clean_l = line.strip().replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')
        text_ops.append(f"1 0 0 1 50 {y} Tm ({clean_l}) Tj")
        y -= 14
        if y < 40:
            break
    stream_content = "BT /F1 11 Tf\n" + "\n".join(text_ops) + "\nET"
    stream_bytes = stream_content.encode('latin1', errors='replace')
    stream_len = len(stream_bytes)
    
    pdf_bytes = (
        b"%PDF-1.4\n"
        b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n"
        b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n"
        b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >> endobj\n"
        b"4 0 obj << /Length " + str(stream_len).encode('ascii') + b" >>\nstream\n" + stream_bytes + b"\nendstream\nendobj\n"
        b"5 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n"
        b"xref\n0 6\n0000000000 65535 f \n"
        b"0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \n"
        b"0000000244 00000 n \n0000000350 00000 n \n"
        b"trailer << /Size 6 /Root 1 0 R >>\nstartxref\n450\n%%EOF\n"
    )
    return io.BytesIO(pdf_bytes)

def create_sample_docx_bytes(text_content):
    """Helper to generate a real DOCX in memory with custom text."""
    doc = docx.Document()
    for line in text_content.split('\n'):
        if line.strip():
            doc.add_paragraph(line.strip())
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer


class ResumeAnalyzerTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app({
            'TESTING': True,
            'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:'
        })
        self.client = self.app.test_client()
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()

        # Create test user
        self.user = User(username='testengineer', email='engineer@test.com')
        self.user.set_password('Secret123!')
        db.session.add(self.user)
        db.session.commit()

        # Generate auth token
        from routes.auth import generate_token
        self.token = generate_token(self.user.id)
        self.headers = {'Authorization': f'Bearer {self.token}'}

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def test_pdf_text_extraction(self):
        """Verify real PDF extraction."""
        sample_text = "Jane Doe\njane@example.com\nSoftware Engineer with Python and Docker skills."
        pdf_buf = create_sample_pdf_bytes(sample_text)
        extracted = ResumeParser.extract_text_from_pdf(pdf_buf)
        self.assertIn("Jane Doe", extracted)
        self.assertIn("jane@example.com", extracted)
        self.assertIn("Python", extracted)

    def test_docx_text_extraction(self):
        """Verify real DOCX extraction."""
        sample_text = "John Smith\njohn@example.com\nFrontend Developer with React and TypeScript."
        docx_buf = create_sample_docx_bytes(sample_text)
        extracted = ResumeParser.extract_text_from_docx(docx_buf)
        self.assertIn("John Smith", extracted)
        self.assertIn("React", extracted)

    def test_empty_document_rejection(self):
        """Verify empty or blank documents are rejected gracefully."""
        res = ResumeParser.parse_resume(io.BytesIO(b""), filename="empty.pdf")
        self.assertFalse(res['success'])
        self.assertIn('Unable to extract', res['error'])

    def test_candidate_info_extraction(self):
        """Verify accurate contact and profile extraction without hallucinations."""
        text = """
        Alex Morgan
        alex.morgan@techcorp.io
        +1 (555) 234-5678
        San Francisco, CA
        https://linkedin.com/in/alexmorgan
        https://github.com/alexmorgan-dev
        https://alexmorgan.dev

        Professional Summary
        Senior Full Stack Engineer with 6+ years of experience.
        """
        info = ResumeParser.extract_candidate_info(text)
        self.assertEqual(info['name'], 'Alex Morgan')
        self.assertEqual(info['email'], 'alex.morgan@techcorp.io')
        self.assertIn('555', info['phone'])
        self.assertEqual(info['linkedin'], 'https://linkedin.com/in/alexmorgan')
        self.assertEqual(info['github'], 'https://github.com/alexmorgan-dev')
        self.assertEqual(info['portfolio'], 'https://alexmorgan.dev')

    def test_skill_extraction_differentiation(self):
        """Assert Resume A and Resume B extract completely distinct resume-specific skills."""
        resume_a_text = """
        Python Developer Resume
        Skills: Python, Django, Flask, PostgreSQL, Redis, Celery, PyTest, Pandas, NumPy
        Experience: Backend Engineer at TechLab building APIs.
        """
        resume_b_text = """
        Java Enterprise Developer Resume
        Skills: Java, Spring Boot, MySQL, Docker, Kubernetes, Jenkins, Maven, JUnit
        Experience: Enterprise Developer at FinanceCorp.
        """
        parsed_a = ResumeParser.extract_skills(resume_a_text)
        parsed_b = ResumeParser.extract_skills(resume_b_text)

        self.assertIn('Python', parsed_a['all'])
        self.assertIn('Django', parsed_a['all'])
        self.assertIn('PostgreSQL', parsed_a['all'])
        self.assertNotIn('Java', parsed_a['all'])
        self.assertNotIn('Spring Boot', parsed_a['all'])

        self.assertIn('Java', parsed_b['all'])
        self.assertIn('Spring Boot', parsed_b['all'])
        self.assertIn('Kubernetes', parsed_b['all'])
        self.assertNotIn('Python', parsed_b['all'])
        self.assertNotIn('Django', parsed_b['all'])

    def test_deterministic_scoring_stability(self):
        """Assert that running scorer twice on same resume produces identical deterministic score and breakdown."""
        resume_text = """
        Sarah Connor
        sarah@cyberdyne.com | +1 555-444-3333 | Los Angeles, CA
        https://github.com/sarahconnor
        
        Summary
        Security and Software Engineer with expertise in Linux and Systems.
        
        Skills
        Python, C++, Linux, Docker, Bash, Git, PostgreSQL, REST APIs
        
        Experience
        Senior Systems Engineer - Cyberdyne Systems (2020 - Present)
        • Developed automated monitoring agents in Python improving uptime by 25%.
        • Orchestrated containerized deployment pipelines with Docker.
        • Refactored legacy C++ backend reducing memory overhead by 40%.
        
        Education
        Bachelor of Science in Computer Science - UCLA (2016 - 2020)
        
        Projects
        Distributed Defense Network (https://github.com/sarahconnor/defense-net)
        • Built resilient mesh communication protocol handling 10k requests/second.
        
        Certifications
        AWS Certified Security Specialist
        """
        docx_buf1 = create_sample_docx_bytes(resume_text)
        parsed1 = ResumeParser.parse_resume(docx_buf1, filename="sarah.docx")
        score1 = ResumeScorer.calculate_score(parsed1, target_role="Software Engineer")

        docx_buf2 = create_sample_docx_bytes(resume_text)
        parsed2 = ResumeParser.parse_resume(docx_buf2, filename="sarah.docx")
        score2 = ResumeScorer.calculate_score(parsed2, target_role="Software Engineer")

        self.assertEqual(score1['ats_score'], score2['ats_score'])
        self.assertEqual(score1['resume_score'], score2['resume_score'])
        self.assertEqual(score1['score_breakdown'], score2['score_breakdown'])

    def test_distinct_resumes_distinct_scores(self):
        """Assert that comprehensive senior resume scores higher than sparse incomplete resume."""
        sparse_text = "Candidate Name\nNo contact info.\nWorked on basic computer stuff.\nNo education listed."
        comprehensive_text = """
        Dr. Alan Turing
        alan@cambridge.edu | +1 555-123-4567 | Cambridge, UK
        https://github.com/alanturing | https://turing.org
        
        Summary
        Pioneering Computer Scientist and Software Architect.
        
        Skills
        Python, Java, C++, Algorithms, Machine Learning, Cryptography, SQL, Linux, Git, Docker, Cloud
        
        Experience
        Chief Systems Architect - Bletchley Labs (2018 - 2024)
        • Designed high-throughput analytical compute engine accelerating processing by 300%.
        • Led team of 15 engineers delivering secure microservice infrastructure.
        • Automated statistical test validation suites.
        
        Education
        Ph.D. in Mathematical Logic - Princeton University (2014 - 2018)
        Bachelor of Arts in Mathematics - King's College Cambridge
        
        Projects
        Universal Turing Engine (https://github.com/alanturing/engine)
        • Implemented state-machine computational emulator in Python with 99% test coverage.
        
        Certifications
        AWS Certified Solutions Architect
        
        Achievements
        Dean's List Award Winner, Published 5 peer-reviewed papers
        """
        parsed_sparse = ResumeParser.parse_resume(create_sample_pdf_bytes(sparse_text), filename="sparse.pdf")
        score_sparse = ResumeScorer.calculate_score(parsed_sparse)

        parsed_comp = ResumeParser.parse_resume(create_sample_pdf_bytes(comprehensive_text), filename="comp.pdf")
        score_comp = ResumeScorer.calculate_score(parsed_comp)

        self.assertTrue(score_comp['resume_score'] > score_sparse['resume_score'])
        self.assertTrue(score_comp['ats_score'] > score_sparse['ats_score'])
        self.assertTrue(len(parsed_comp['skills']) > len(parsed_sparse['skills']))

    def test_job_description_matching(self):
        """Verify semantic JD matching."""
        resume_text = "Python, Flask, PostgreSQL, Docker, Git developer with REST API experience."
        jd_text = """
        Looking for a Backend Python Engineer:
        Requirements:
        - Deep knowledge of Python, Flask, or Django
        - Relational database experience with PostgreSQL
        - Containerization with Docker and Kubernetes
        - Cloud infrastructure on AWS
        """
        match_res = AIService.match_job_description(resume_text, ['Python', 'Flask', 'PostgreSQL', 'Docker', 'Git'], jd_text)
        self.assertIsNotNone(match_res)
        self.assertIn('Python', match_res['matched_skills'])
        self.assertTrue(any('AWS' in s or 'Kubernetes' in s for s in match_res['missing_skills']))

    def test_report_service_dict_and_object(self):
        """Verify ReportService works with both dict and model objects and handles None session cleanly."""
        report_dict = {
            'overall_score': 85,
            'scores': {'technical': 90, 'fluency': 80, 'grammar': 85, 'confidence': 85},
            'strengths': ['Strong algorithm mastery'],
            'weaknesses': ['Elaborate further on concurrency'],
            'suggestions': 'Practice multi-threading questions.'
        }
        # Test with None session
        html1 = ReportService.generate_html_report(report_dict, self.user, None)
        self.assertIn('AI Interview Assessment', html1)
        self.assertIn('85%', html1)

        # Test resume report
        resume_dict = {
            'name': 'Test Candidate',
            'email': 'cand@test.com',
            'ats_score': 88,
            'resume_score': 82,
            'analysis': {
                'strengths': ['Clean layout'],
                'weaknesses': [],
                'missing_skills': ['Redis'],
                'suggestions': ['Add portfolio link']
            }
        }
        html2 = ReportService.generate_resume_html_report(resume_dict, self.user)
        self.assertIn('Test Candidate', html2)
        self.assertIn('88%', html2)

    def test_api_resume_analyze_end_to_end(self):
        """Verify full POST /api/resume/analyze endpoint flow."""
        resume_content = """
        David Miller
        david.miller@devmail.com | +1 555-890-1234
        https://github.com/davidmiller
        
        Summary
        Full Stack Engineer with 4 years building scalable web apps.
        
        Skills
        JavaScript, TypeScript, React, Node.js, Express, PostgreSQL, MongoDB, Docker, Git
        
        Experience
        Full Stack Engineer - CloudApps Inc (2022 - Present)
        • Developed real-time dashboard in React and Node.js decreasing latency by 35%.
        • Managed PostgreSQL database schema migrations.
        
        Education
        Bachelor of Science in Software Engineering - San Jose State University
        
        Projects
        TaskFlow Web Platform (https://github.com/davidmiller/taskflow)
        • Full stack collaborative management tool with 5,000 active users.
        """
        pdf_buf = create_sample_pdf_bytes(resume_content)
        data = {
            'resume': (pdf_buf, 'David_Miller_Resume.pdf'),
            'job_role': 'Full Stack Developer',
            'job_description': 'Looking for a Full Stack Developer with React, Node.js, and Docker.'
        }

        response = self.client.post(
            '/api/resume/analyze',
            data=data,
            content_type='multipart/form-data',
            headers=self.headers
        )

        self.assertEqual(response.status_code, 201)
        res_json = response.get_json()
        self.assertTrue(res_json['success'])
        self.assertIn('resume', res_json)
        res_data = res_json['resume']
        self.assertEqual(res_data['name'], 'David Miller')
        self.assertEqual(res_data['email'], 'david.miller@devmail.com')
        self.assertIn('React', res_data['skills'])
        self.assertIn('Node.js', res_data['skills'])
        self.assertTrue(res_data['ats_score'] > 50)
        self.assertTrue(res_data['resume_score'] > 50)
        self.assertIn('ats_compatibility', res_data['score_breakdown'])

        # Check that Resume row is saved in database
        saved_resume = db.session.get(Resume, res_data['id'])
        self.assertIsNotNone(saved_resume)
        self.assertEqual(saved_resume.user_id, self.user.id)
        self.assertIsNotNone(saved_resume.file_hash)
        self.assertEqual(saved_resume.analysis_version, 'v2')


if __name__ == '__main__':
    unittest.main()
