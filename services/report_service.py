import json

class ReportService:
    @staticmethod
    def generate_html_report(report, user, session=None):
        """Generates a premium, print-optimized HTML report from performance metrics."""
        report_data = report.to_dict() if hasattr(report, 'to_dict') else (report if isinstance(report, dict) else {})
        
        username = getattr(user, 'username', None) or (user.get('username') if isinstance(user, dict) else 'User')
        user_email = getattr(user, 'email', None) or (user.get('email') if isinstance(user, dict) else 'N/A')
        
        job_role = 'Software Engineer'
        exp_level = 'General'
        if session is not None:
            job_role = getattr(session, 'job_role', None) or (session.get('job_role') if isinstance(session, dict) else 'Software Engineer')
            exp_level = getattr(session, 'experience_level', None) or (session.get('experience_level') if isinstance(session, dict) else 'General')
            
        scores = report_data.get('scores', {})
        strengths = report_data.get('strengths', [])
        weaknesses = report_data.get('weaknesses', [])
        roadmap = report_data.get('roadmap', {})
        overall_score = report_data.get('overall_score', getattr(report, 'overall_score', 0))
        suggestions_text = report_data.get('suggestions', getattr(report, 'suggestions', 'No specific suggestions provided.'))
        
        # Parse and format the created_at timestamp
        created_at_val = report_data.get('created_at', getattr(report, 'created_at', ''))
        if isinstance(created_at_val, str) and created_at_val:
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(created_at_val)
                date_str = dt.strftime('%Y-%m-%d %H:%M')
            except Exception:
                date_str = created_at_val.replace('T', ' ')[:16]
        elif hasattr(created_at_val, 'strftime'):
            date_str = created_at_val.strftime('%Y-%m-%d %H:%M')
        else:
            date_str = 'N/A'
        
        strengths_li = "".join([f"<li>{s}</li>" for s in strengths])
        weaknesses_li = "".join([f"<li>{s}</li>" for s in weaknesses])
        
        courses_li = "".join([f"<li>{c}</li>" for c in roadmap.get('courses', [])])
        books_li = "".join([f"<li>{b}</li>" for b in roadmap.get('books', [])])
        timeline_divs = "".join([
            f"<div class='timeline-item'><strong>{t.get('phase', 'Phase')}:</strong> {t.get('focus', 'Focus')}</div>" 
            for t in roadmap.get('timeline', [])
        ])

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>AI Mock Interview Performance Report - {user.username}</title>
            <style>
                body {{
                    font-family: 'Inter', 'Segoe UI', Roboto, sans-serif;
                    color: #1E293B;
                    line-height: 1.5;
                    margin: 0;
                    padding: 40px;
                    background-color: #F8FAFC;
                }}
                .report-card {{
                    background: white;
                    border-radius: 12px;
                    border: 1px solid #E2E8F0;
                    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
                    padding: 40px;
                    max-width: 800px;
                    margin: 0 auto;
                }}
                .header {{
                    border-bottom: 2px solid #E2E8F0;
                    padding-bottom: 20px;
                    margin-bottom: 30px;
                }}
                .header h1 {{
                    color: #4F46E5;
                    margin: 0 0 10px 0;
                    font-size: 28px;
                }}
                .header p {{
                    margin: 0;
                    color: #64748B;
                }}
                .score-grid {{
                    display: grid;
                    grid-template-columns: repeat(2, 1fr);
                    gap: 20px;
                    margin-bottom: 35px;
                }}
                .score-card {{
                    background: #F1F5F9;
                    padding: 20px;
                    border-radius: 8px;
                    text-align: center;
                }}
                .score-card.primary {{
                    background: #EEF2FF;
                    border: 1px solid #C7D2FE;
                    grid-column: span 2;
                }}
                .score-value {{
                    font-size: 36px;
                    font-weight: 800;
                    color: #4F46E5;
                    margin: 10px 0;
                }}
                .score-title {{
                    font-weight: 600;
                    text-transform: uppercase;
                    font-size: 12px;
                    color: #64748B;
                    letter-spacing: 0.05em;
                }}
                .section {{
                    margin-bottom: 30px;
                }}
                .section h2 {{
                    color: #1E293B;
                    font-size: 20px;
                    border-left: 4px solid #4F46E5;
                    padding-left: 10px;
                    margin-bottom: 15px;
                }}
                ul {{
                    padding-left: 20px;
                    margin: 0;
                }}
                li {{
                    margin-bottom: 8px;
                }}
                .timeline-item {{
                    background: #FAF5FF;
                    border-left: 3px solid #A855F7;
                    padding: 10px 15px;
                    margin-bottom: 10px;
                    border-radius: 0 6px 6px 0;
                }}
                .footer {{
                    margin-top: 50px;
                    text-align: center;
                    font-size: 12px;
                    color: #94A3B8;
                    border-top: 1px solid #E2E8F0;
                    padding-top: 20px;
                }}
                @media print {{
                    body {{
                        background: white;
                        padding: 0;
                    }}
                    .report-card {{
                        box-shadow: none;
                        border: none;
                        padding: 0;
                        max-width: 100%;
                    }}
                    .no-print {{
                        display: none;
                    }}
                }}
            </style>
        </head>
        <body>
            <div class="report-card">
                <div class="header">
                    <h1>AI Interview Assessment</h1>
                    <p><strong>Candidate:</strong> {username} ({user_email})</p>
                    <p><strong>Role:</strong> {job_role} ({exp_level}) | <strong>Date:</strong> {date_str}</p>
                </div>
                
                <div class="score-grid">
                    <div class="score-card primary">
                        <div class="score-title">Overall Grade</div>
                        <div class="score-value">{overall_score}%</div>
                        <p style="margin:0; font-size: 13px; color:#64748B;">Competency score matched against active {job_role} standards.</p>
                    </div>
                    <div class="score-card">
                        <div class="score-title">Technical Correctness</div>
                        <div class="score-value">{scores.get('technical', 0)}%</div>
                    </div>
                    <div class="score-card">
                        <div class="score-title">Communication & Fluency</div>
                        <div class="score-value">{scores.get('fluency', 0)}%</div>
                    </div>
                    <div class="score-card">
                        <div class="score-title">Grammar & Syntax</div>
                        <div class="score-value">{scores.get('grammar', 0)}%</div>
                    </div>
                    <div class="score-card">
                        <div class="score-title">Confidence & Presence</div>
                        <div class="score-value">{scores.get('confidence', 0)}%</div>
                    </div>
                </div>

                <div class="section">
                    <h2>Key Strengths</h2>
                    <ul>{strengths_li}</ul>
                </div>

                <div class="section">
                    <h2>Areas for Improvement</h2>
                    <ul>{weaknesses_li}</ul>
                </div>

                <div class="section">
                    <h2>Roadmap & Recommendations</h2>
                    <h3>Recommended Learning Path</h3>
                    {timeline_divs}
                    
                    <h3 style="margin-top: 20px;">Top Courses</h3>
                    <ul>{courses_li}</ul>
                    
                    <h3 style="margin-top: 20px;">Suggested Reading</h3>
                    <ul>{books_li}</ul>
                </div>

                <div class="section">
                    <h2>General Suggestions</h2>
                    <p>{report.get('suggestions') or "No specific suggestions provided."}</p>
                </div>
                
                <div class="footer">
                    <p>Generated by TECH CLEVORA AI-Powered Interview Assistant & Resume Analyzer.</p>
                    <button onclick="window.print()" class="no-print" style="margin-top:15px; padding: 10px 20px; background:#4F46E5; color:white; border:none; border-radius:6px; cursor:pointer; font-weight:bold;">Print / Save to PDF</button>
                </div>
            </div>
        </body>
        </html>
        """
        return html

    @staticmethod
    def generate_resume_html_report(resume_dict_or_model, user=None):
        """Generates a premium HTML assessment report for a candidate resume."""
        resume_dict = resume_dict_or_model.to_dict() if hasattr(resume_dict_or_model, 'to_dict') else (resume_dict_or_model if isinstance(resume_dict_or_model, dict) else {})
        analysis = resume_dict.get('analysis', {})
        skills = resume_dict.get('skills', [])
        
        strengths_li = "".join([f"<li>{s}</li>" for s in analysis.get('strengths', [])])
        weaknesses_li = "".join([f"<li>{w}</li>" for w in analysis.get('weaknesses', [])])
        missing_li = "".join([f"<li>{m}</li>" for m in analysis.get('missing_skills', [])])
        suggestions_li = "".join([f"<li>{s}</li>" for s in analysis.get('suggestions', [])])
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Candidate Resume Assessment - {resume_dict.get('name')}</title>
            <style>
                body {{
                    font-family: 'Inter', 'Segoe UI', Roboto, sans-serif;
                    color: #1E293B;
                    line-height: 1.5;
                    margin: 0;
                    padding: 40px;
                    background-color: #F8FAFC;
                }}
                .report-card {{
                    background: white;
                    border-radius: 12px;
                    border: 1px solid #E2E8F0;
                    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
                    padding: 40px;
                    max-width: 800px;
                    margin: 0 auto;
                }}
                .header {{
                    border-bottom: 2px solid #E2E8F0;
                    padding-bottom: 20px;
                    margin-bottom: 30px;
                }}
                .header h1 {{
                    color: #4F46E5;
                    margin: 0 0 10px 0;
                    font-size: 28px;
                }}
                .header p {{
                    margin: 0;
                    color: #64748B;
                }}
                .score-grid {{
                    display: grid;
                    grid-template-columns: repeat(2, 1fr);
                    gap: 20px;
                    margin-bottom: 35px;
                }}
                .score-card {{
                    background: #F1F5F9;
                    padding: 20px;
                    border-radius: 8px;
                    text-align: center;
                }}
                .score-value {{
                    font-size: 36px;
                    font-weight: 800;
                    color: #4F46E5;
                    margin: 10px 0;
                }}
                .score-title {{
                    font-weight: 600;
                    text-transform: uppercase;
                    font-size: 12px;
                    color: #64748B;
                }}
                .section {{
                    margin-bottom: 30px;
                }}
                .section h2 {{
                    color: #1E293B;
                    font-size: 20px;
                    border-left: 4px solid #4F46E5;
                    padding-left: 10px;
                    margin-bottom: 15px;
                }}
                ul {{
                    padding-left: 20px;
                    margin: 0;
                }}
                li {{
                    margin-bottom: 8px;
                }}
            </style>
        </head>
        <body>
            <div class="report-card">
                <div class="header">
                    <h1>AI Candidate Resume Assessment</h1>
                    <p><strong>Candidate Name:</strong> {resume_dict.get('name')}</p>
                    <p><strong>Email:</strong> {resume_dict.get('email') or 'N/A'} | <strong>Phone:</strong> {resume_dict.get('phone') or 'N/A'}</p>
                </div>
                
                <div class="score-grid">
                    <div class="score-card">
                        <div class="score-title">ATS Score</div>
                        <div class="score-value">{resume_dict.get('ats_score', 0)}%</div>
                    </div>
                    <div class="score-card">
                        <div class="score-title">Resume Score</div>
                        <div class="score-value">{resume_dict.get('resume_score', 0)}%</div>
                    </div>
                </div>

                <div class="section">
                    <h2>Key Strengths</h2>
                    <ul>{strengths_li or "<li>Alignment with standard professional structures.</li>"}</ul>
                </div>

                <div class="section">
                    <h2>Weaknesses / Gaps</h2>
                    <ul>{weaknesses_li or "<li>No critical structural weaknesses found.</li>"}</ul>
                </div>

                <div class="section">
                    <h2>Missing Keywords / Tech Skills</h2>
                    <ul>{missing_li or "<li>Targeted technical stack is well represented.</li>"}</ul>
                </div>

                <div class="section">
                    <h2>Actionable Improvement Tips</h2>
                    <ul>{suggestions_li or "<li>Maintain descriptive project logs.</li>"}</ul>
                </div>
                
                <div class="footer">
                    <p>Generated by TECH CLEVORA Recruitment Suite</p>
                </div>
            </div>
        </body>
        </html>
        """
        return html

