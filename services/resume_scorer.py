import re

class ResumeScorer:
    """
    Transparent, deterministic 100-point scoring engine for resumes.
    Calculates scores purely from verifiable document characteristics and content.
    The exact same resume input will always produce the exact same score.
    """

    ROLE_BENCHMARK_SKILLS = {
        'Software Engineer': ['Python', 'Java', 'C++', 'Git', 'SQL', 'Data Structures', 'Algorithms', 'Docker', 'Linux', 'REST APIs'],
        'Software Developer': ['Python', 'Java', 'C++', 'Git', 'SQL', 'Data Structures', 'Algorithms', 'Docker', 'Linux', 'REST APIs'],
        'Web Developer': ['HTML', 'CSS', 'JavaScript', 'React', 'Node.js', 'Git', 'Responsive Design', 'REST APIs', 'TypeScript'],
        'Frontend Developer': ['HTML', 'CSS', 'JavaScript', 'TypeScript', 'React', 'Vue.js', 'Next.js', 'Tailwind CSS', 'Redux', 'Figma'],
        'Backend Developer': ['Python', 'Java', 'Node.js', 'Go', 'PostgreSQL', 'MySQL', 'MongoDB', 'Redis', 'Docker', 'REST APIs', 'Microservices'],
        'Full Stack Developer': ['JavaScript', 'TypeScript', 'React', 'Node.js', 'Python', 'SQL', 'MongoDB', 'Docker', 'AWS', 'Git', 'REST APIs'],
        'Python Developer': ['Python', 'Django', 'Flask', 'FastAPI', 'PostgreSQL', 'SQL', 'Git', 'Docker', 'PyTest', 'Pandas'],
        'Java Developer': ['Java', 'Spring Boot', 'Hibernate', 'Microservices', 'SQL', 'Git', 'Docker', 'REST APIs', 'JUnit', 'Maven'],
        'JavaScript Developer': ['JavaScript', 'TypeScript', 'Node.js', 'React', 'HTML', 'CSS', 'Git', 'REST APIs', 'Webpack', 'Jest'],
        'TypeScript Developer': ['TypeScript', 'JavaScript', 'Node.js', 'React', 'Next.js', 'Git', 'REST APIs', 'GraphQL', 'Docker', 'Jest'],
        'React Developer': ['React', 'JavaScript', 'TypeScript', 'Redux', 'HTML', 'CSS', 'Tailwind CSS', 'Next.js', 'Git', 'REST APIs'],
        'Angular Developer': ['Angular', 'TypeScript', 'RxJS', 'HTML', 'CSS', 'JavaScript', 'Git', 'REST APIs', 'Karma', 'Node.js'],
        'Node.js Developer': ['Node.js', 'Express', 'JavaScript', 'TypeScript', 'MongoDB', 'PostgreSQL', 'REST APIs', 'Docker', 'Git', 'Redis'],
        '.NET Developer': ['C#', '.NET', 'ASP.NET', 'SQL Server', 'Entity Framework', 'Azure', 'REST APIs', 'Git', 'Docker', 'Microservices'],
        'PHP Developer': ['PHP', 'Laravel', 'MySQL', 'JavaScript', 'HTML', 'CSS', 'Git', 'REST APIs', 'Composer', 'Docker'],
        'Mobile Developer': ['React Native', 'Flutter', 'Swift', 'Kotlin', 'iOS', 'Android', 'REST APIs', 'Git', 'Mobile Architecture'],
        'iOS Developer': ['Swift', 'iOS', 'Xcode', 'UIKit', 'SwiftUI', 'CoreData', 'Git', 'REST APIs', 'CocoaPods', 'CI/CD'],
        'Android Developer': ['Kotlin', 'Java', 'Android SDK', 'Android Studio', 'Jetpack Compose', 'Git', 'REST APIs', 'Room', 'Coroutines', 'Gradle'],
        'AI Engineer': ['Python', 'PyTorch', 'TensorFlow', 'Machine Learning', 'Deep Learning', 'NLP', 'Computer Vision', 'LLM', 'Docker', 'Git'],
        'Machine Learning Engineer': ['Python', 'PyTorch', 'TensorFlow', 'Scikit-Learn', 'MLOps', 'Docker', 'Kubernetes', 'Pandas', 'NumPy', 'Git'],
        'Data Scientist': ['Python', 'R', 'SQL', 'Pandas', 'NumPy', 'Scikit-Learn', 'Machine Learning', 'Data Analysis', 'Statistics', 'Git'],
        'Data Analyst': ['SQL', 'Python', 'Excel', 'Tableau', 'Power BI', 'Pandas', 'Data Analysis', 'Statistics', 'Data Visualization', 'R'],
        'Data Engineer': ['Python', 'SQL', 'Spark', 'Kafka', 'Hadoop', 'AWS', 'Airflow', 'PostgreSQL', 'Docker', 'Data Pipelines'],
        'NLP Engineer': ['Python', 'NLP', 'BERT', 'Transformers', 'PyTorch', 'HuggingFace', 'LLM', 'Spacy', 'NLTK', 'Git'],
        'Computer Vision Engineer': ['Python', 'OpenCV', 'PyTorch', 'TensorFlow', 'Deep Learning', 'Computer Vision', 'CNN', 'YOLO', 'C++', 'Docker'],
        'Generative AI Engineer': ['Python', 'LLM', 'LangChain', 'OpenAI', 'RAG', 'Vector Databases', 'PyTorch', 'Prompt Engineering', 'FastAPI', 'Docker'],
        'Cloud Engineer': ['AWS', 'Azure', 'GCP', 'Docker', 'Kubernetes', 'Terraform', 'Linux', 'CI/CD', 'Ansible', 'Security'],
        'Cloud Architect': ['AWS', 'Azure', 'GCP', 'Cloud Architecture', 'Terraform', 'Kubernetes', 'Microservices', 'Security', 'Docker', 'CI/CD'],
        'DevOps Engineer': ['Docker', 'Kubernetes', 'Jenkins', 'GitHub Actions', 'Terraform', 'Linux', 'CI/CD', 'AWS', 'Bash', 'Prometheus'],
        'Site Reliability Engineer': ['Linux', 'Kubernetes', 'Docker', 'Terraform', 'Prometheus', 'Grafana', 'Python', 'Go', 'CI/CD', 'Bash'],
        'Kubernetes Engineer': ['Kubernetes', 'Docker', 'Helm', 'Terraform', 'Linux', 'CI/CD', 'Prometheus', 'AWS', 'Bash', 'Networking'],
        'Platform Engineer': ['Kubernetes', 'Terraform', 'Docker', 'Go', 'Python', 'CI/CD', 'AWS', 'Linux', 'Microservices', 'ArgoCD'],
        'Cybersecurity Engineer': ['Cybersecurity', 'Network Security', 'Linux', 'Python', 'SIEM', 'Firewalls', 'Vulnerability Assessment', 'Penetration Testing', 'Cryptography', 'Wireshark'],
        'Security Analyst': ['SIEM', 'Incident Response', 'SOC', 'Splunk', 'Threat Intelligence', 'Cybersecurity', 'Wireshark', 'Network Security', 'Python', 'Linux'],
        'SOC Analyst': ['SOC', 'SIEM', 'Splunk', 'Incident Response', 'Threat Hunting', 'Log Analysis', 'Cybersecurity', 'Firewalls', 'Wireshark', 'EDR'],
        'Penetration Tester': ['Penetration Testing', 'Kali Linux', 'Burp Suite', 'Metasploit', 'Vulnerability Assessment', 'Python', 'Network Security', 'OWASP', 'Ethical Hacking', 'Nmap'],
        'Security Engineer': ['Security', 'Cybersecurity', 'Cloud Security', 'IAM', 'Encryption', 'Python', 'Linux', 'Docker', 'CI/CD', 'Threat Modeling'],
        'Cloud Security Engineer': ['Cloud Security', 'AWS', 'Azure', 'IAM', 'Terraform', 'Kubernetes', 'Security', 'Compliance', 'Docker', 'Linux'],
        'UI UX Designer': ['Figma', 'UI/UX', 'Wireframing', 'Prototyping', 'User Research', 'HTML', 'CSS', 'Adobe XD', 'Design Systems'],
        'Product Designer': ['Figma', 'UI/UX', 'Design Systems', 'Prototyping', 'User Research', 'Wireframing', 'Interaction Design', 'Product Design', 'Visual Design', 'Usability Testing'],
        'UX Researcher': ['User Research', 'Usability Testing', 'User Interviews', 'Personas', 'Wireframing', 'Figma', 'Analytics', 'A/B Testing', 'Information Architecture', 'Surveys'],
        'Graphic Designer': ['Adobe Photoshop', 'Illustrator', 'InDesign', 'Typography', 'Branding', 'Figma', 'Visual Design', 'Layout Design', 'Creativity', 'Digital Design'],
        'Product Manager': ['Product Strategy', 'Roadmapping', 'Agile', 'Scrum', 'User Stories', 'Data Analysis', 'Jira', 'Stakeholder Management', 'Market Research', 'KPIs'],
        'Technical Product Manager': ['Product Strategy', 'System Architecture', 'APIs', 'Agile', 'Scrum', 'Data Analysis', 'SQL', 'Roadmapping', 'Technical Specs', 'Jira'],
        'Project Manager': ['Project Management', 'Agile', 'Scrum', 'Jira', 'Risk Management', 'Budgeting', 'Stakeholder Communication', 'PMP', 'Planning', 'Scheduling'],
        'Business Analyst': ['Business Analysis', 'Requirements Gathering', 'SQL', 'Data Analysis', 'Process Modeling', 'User Stories', 'Agile', 'Excel', 'Tableau', 'Documentation']
    }

    ACTION_VERBS = [
        'developed', 'designed', 'built', 'implemented', 'created', 'led', 'managed',
        'optimized', 'engineered', 'spearheaded', 'orchestrated', 'automated', 'delivered',
        'accelerated', 'established', 'integrated', 'refactored', 'scaled', 'mentored'
    ]

    @classmethod
    def calculate_score(cls, parsed_data, target_role="Software Engineer", target_job_description=None):
        """
        Calculates deterministic ATS score, resume score, and detailed score breakdown.
        """
        if not parsed_data or not parsed_data.get('success', False):
            return {
                'ats_score': 0,
                'resume_score': 0,
                'score_breakdown': {
                    'ats_compatibility': 0,
                    'skills_relevance': 0,
                    'experience': 0,
                    'education': 0,
                    'projects': 0,
                    'achievements': 0,
                    'structure': 0,
                    'keywords': 0,
                    'profile_completeness': 0
                },
                'ats_issues': ['Unable to extract readable text from resume document.']
            }

        text = parsed_data.get('text', '')
        text_lower = text.lower()
        candidate = parsed_data.get('candidate', {})
        skills = parsed_data.get('skills', [])
        categorized_skills = parsed_data.get('skills_categorized', {})
        sections_present = parsed_data.get('sections_present', [])
        education = parsed_data.get('education', [])
        experience = parsed_data.get('experience', [])
        projects = parsed_data.get('projects', [])
        certifications = parsed_data.get('certifications', [])
        achievements = parsed_data.get('achievements', [])
        word_count = parsed_data.get('word_count', 0)

        ats_issues = []

        # -------------------------------------------------------------
        # 1. ATS Compatibility & Formatting (Max 20 pts)
        # -------------------------------------------------------------
        score_ats_compat = 0
        # Standard headings present (up to 6 pts)
        core_headers = ['skills', 'experience', 'education', 'projects', 'summary', 'contact']
        matching_headers = [h for h in core_headers if h in sections_present]
        score_ats_compat += min(len(matching_headers), 6)
        if len(matching_headers) < 3:
            ats_issues.append("Resume is missing standard section headings (e.g. Experience, Education, Skills).")

        # Length / word density (up to 6 pts)
        if 250 <= word_count <= 1400:
            score_ats_compat += 6
        elif 150 <= word_count < 250 or 1400 < word_count <= 2000:
            score_ats_compat += 4
            ats_issues.append("Resume word count is slightly outside standard 1-2 page length (400-800 words).")
        else:
            score_ats_compat += 2
            ats_issues.append("Resume word count is too short or excessively long for standard ATS parsing.")

        # Clean ASCII/formatting safety (up to 4 pts)
        unusual_chars = len(re.findall(r'[^\x00-\x7F]', text))
        if unusual_chars < 15:
            score_ats_compat += 4
        elif unusual_chars < 50:
            score_ats_compat += 2
        else:
            score_ats_compat += 1
            ats_issues.append("Detected high volume of special Unicode/glyph characters that may break ATS parsers.")

        # Bullet point structure (up to 4 pts)
        bullet_count = len(re.findall(r'(?:^|\n)\s*[•\-*–]\s+', text))
        if bullet_count >= 6:
            score_ats_compat += 4
        elif bullet_count >= 2:
            score_ats_compat += 2
        else:
            score_ats_compat += 1
            ats_issues.append("Lack of standard bullet-point formatting in experience or projects.")

        score_ats_compat = min(score_ats_compat, 20)

        # -------------------------------------------------------------
        # 2. Skills Relevance & Diversity (Max 20 pts)
        # -------------------------------------------------------------
        score_skills = 0
        # Total skill volume (up to 10 pts)
        if len(skills) >= 10:
            score_skills += 10
        elif len(skills) >= 6:
            score_skills += 7
        elif len(skills) >= 3:
            score_skills += 4
        elif len(skills) >= 1:
            score_skills += 2
        else:
            ats_issues.append("No technical skills from standard taxonomy detected.")

        # Category breadth (up to 5 pts)
        active_cats = sum(1 for cat, cat_skills in categorized_skills.items() if len(cat_skills) > 0)
        if active_cats >= 4:
            score_skills += 5
        elif active_cats >= 2:
            score_skills += 3
        elif active_cats >= 1:
            score_skills += 1

        # Role benchmark alignment (up to 5 pts)
        benchmark = cls.ROLE_BENCHMARK_SKILLS.get(target_role, cls.ROLE_BENCHMARK_SKILLS['Software Engineer'])
        matched_benchmarks = [s for s in benchmark if s.lower() in [sk.lower() for sk in skills]]
        match_ratio = len(matched_benchmarks) / max(len(benchmark), 1)
        score_skills += min(int(match_ratio * 5), 5)

        score_skills = min(score_skills, 20)

        # -------------------------------------------------------------
        # 3. Experience Quality & Impact (Max 15 pts)
        # -------------------------------------------------------------
        score_exp = 0
        if len(experience) >= 2:
            score_exp += 6
        elif len(experience) == 1:
            score_exp += 4
        elif 'experience' in sections_present:
            score_exp += 2

        # Action verb density (up to 5 pts)
        verbs_found = sum(1 for v in cls.ACTION_VERBS if re.search(r'\b' + re.escape(v) + r'\b', text_lower))
        if verbs_found >= 6:
            score_exp += 5
        elif verbs_found >= 3:
            score_exp += 3
        elif verbs_found >= 1:
            score_exp += 1
        else:
            ats_issues.append("Experience bullets lack strong action verbs (e.g., Developed, Engineered, Spearheaded).")

        # Measurable metrics (up to 4 pts)
        metrics_found = len(re.findall(r'\b\d+(?:\.\d+)?%|\$\d+|\b\d+\s*(?:ms|users|clients|requests|X|fold)\b', text, re.IGNORECASE))
        if metrics_found >= 3:
            score_exp += 4
        elif metrics_found >= 1:
            score_exp += 2
        else:
            ats_issues.append("No quantifiable metrics or measurable outcomes (e.g. %, numbers, performance boosts) found.")

        score_exp = min(score_exp, 15)

        # -------------------------------------------------------------
        # 4. Education & Qualifications (Max 10 pts)
        # -------------------------------------------------------------
        score_edu = 0
        if len(education) >= 1:
            score_edu += 6
            # Check for year/dates in education
            if any(e.get('year') for e in education):
                score_edu += 4
            else:
                score_edu += 2
        elif 'education' in sections_present:
            score_edu += 4
        else:
            ats_issues.append("Education section or recognized degree not detected.")

        score_edu = min(score_edu, 10)

        # -------------------------------------------------------------
        # 5. Projects Portfolio (Max 10 pts)
        # -------------------------------------------------------------
        score_projects = 0
        if len(projects) >= 2:
            score_projects += 6
        elif len(projects) == 1:
            score_projects += 4
        elif 'projects' in sections_present:
            score_projects += 2

        # Project links or live demos (up to 4 pts)
        has_links = any(p.get('link') for p in projects) or ('github.com' in text_lower or 'vercel.app' in text_lower or 'netlify.app' in text_lower)
        if has_links:
            score_projects += 4
        elif len(projects) > 0:
            score_projects += 1

        score_projects = min(score_projects, 10)

        # -------------------------------------------------------------
        # 6. Achievements & Certifications (Max 5 pts)
        # -------------------------------------------------------------
        score_achieve = 0
        if len(certifications) >= 1 and len(achievements) >= 1:
            score_achieve = 5
        elif len(certifications) >= 1 or len(achievements) >= 1:
            score_achieve = 4
        elif 'certifications' in sections_present or 'achievements' in sections_present:
            score_achieve = 2

        score_achieve = min(score_achieve, 5)

        # -------------------------------------------------------------
        # 7. Resume Structure & Section Completeness (Max 10 pts)
        # -------------------------------------------------------------
        score_structure = 0
        # Contact, Skills, Experience, Education, Projects
        key_sections = ['contact', 'skills', 'experience', 'education', 'projects']
        for ks in key_sections:
            if ks in sections_present:
                score_structure += 2

        score_structure = min(score_structure, 10)

        # -------------------------------------------------------------
        # 8. Keyword Optimization & Density (Max 5 pts)
        # -------------------------------------------------------------
        score_keywords = 0
        if target_job_description and len(target_job_description.strip()) > 20:
            jd_words = set(re.findall(r'\b[A-Za-z]{3,}\b', target_job_description.lower()))
            # Filter common stop words
            stops = {'and', 'the', 'for', 'with', 'you', 'will', 'that', 'this', 'from', 'are', 'have', 'our', 'team', 'work'}
            jd_keywords = jd_words - stops
            resume_words = set(re.findall(r'\b[A-Za-z]{3,}\b', text_lower))
            if jd_keywords:
                overlap = len(jd_keywords.intersection(resume_words)) / len(jd_keywords)
                score_keywords = min(int(overlap * 5) + 1, 5)
        else:
            # Baseline keyword density
            role_kw = cls.ROLE_BENCHMARK_SKILLS.get(target_role, cls.ROLE_BENCHMARK_SKILLS['Software Engineer'])
            kw_hits = sum(1 for kw in role_kw if kw.lower() in text_lower)
            score_keywords = min(int((kw_hits / max(len(role_kw), 1)) * 5) + 1, 5)

        score_keywords = min(score_keywords, 5)

        # -------------------------------------------------------------
        # 9. Contact & Profile Completeness (Max 5 pts)
        # -------------------------------------------------------------
        score_contact = 0
        if candidate.get('email'): score_contact += 1
        else: ats_issues.append("Candidate email address not found in resume header.")
        
        if candidate.get('phone'): score_contact += 1
        else: ats_issues.append("Candidate phone number not found in resume header.")
        
        if candidate.get('location'): score_contact += 1
        if candidate.get('linkedin'): score_contact += 1
        if candidate.get('github') or candidate.get('portfolio'): score_contact += 1

        score_contact = min(score_contact, 5)

        # -------------------------------------------------------------
        # Total Deterministic Calculation
        # -------------------------------------------------------------
        breakdown = {
            'ats_compatibility': score_ats_compat,
            'skills_relevance': score_skills,
            'experience': score_exp,
            'education': score_edu,
            'projects': score_projects,
            'achievements': score_achieve,
            'structure': score_structure,
            'keywords': score_keywords,
            'profile_completeness': score_contact
        }

        resume_score = sum(breakdown.values())
        resume_score = min(max(resume_score, 10), 100)

        # ATS score weighted on parseability, keywords, structure, and contact
        ats_score = int(
            (score_ats_compat * 2.0) +      # 40%
            (score_structure * 1.5) +       # 15%
            (score_keywords * 3.0) +        # 15%
            (score_skills * 0.75) +         # 15%
            (score_contact * 3.0)           # 15%
        )
        ats_score = min(max(ats_score, 15), 99)

        return {
            'ats_score': ats_score,
            'resume_score': resume_score,
            'score_breakdown': breakdown,
            'ats_issues': ats_issues
        }
