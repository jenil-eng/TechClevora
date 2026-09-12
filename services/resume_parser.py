import os
import re
import io
import PyPDF2
import docx

class ResumeParser:
    """
    Production-grade resume text extractor and structured data parser.
    Never invents missing data and strictly parses from uploaded content.
    """

    # Categorized skill taxonomy with canonical names
    SKILL_TAXONOMY = {
        'languages': {
            'python': 'Python', 'javascript': 'JavaScript', 'typescript': 'TypeScript',
            'java': 'Java', 'c++': 'C++', 'cpp': 'C++', 'c#': 'C#', 'csharp': 'C#',
            'c': 'C', 'go': 'Go', 'golang': 'Go', 'rust': 'Rust', 'swift': 'Swift',
            'kotlin': 'Kotlin', 'php': 'PHP', 'ruby': 'Ruby', 'sql': 'SQL',
            'html': 'HTML', 'html5': 'HTML5', 'css': 'CSS', 'css3': 'CSS3',
            'r': 'R', 'scala': 'Scala', 'dart': 'Dart', 'bash': 'Bash', 'shell': 'Shell',
            'powershell': 'PowerShell', 'perl': 'Perl', 'matlab': 'MATLAB'
        },
        'frameworks': {
            'react': 'React', 'react.js': 'React', 'reactjs': 'React',
            'next.js': 'Next.js', 'nextjs': 'Next.js', 'angular': 'Angular',
            'vue': 'Vue.js', 'vue.js': 'Vue.js', 'vuejs': 'Vue.js',
            'node.js': 'Node.js', 'nodejs': 'Node.js', 'express': 'Express.js',
            'express.js': 'Express.js', 'django': 'Django', 'flask': 'Flask',
            'fastapi': 'FastAPI', 'spring': 'Spring', 'spring boot': 'Spring Boot',
            'asp.net': 'ASP.NET', '.net': '.NET', 'dotnet': '.NET',
            'laravel': 'Laravel', 'ruby on rails': 'Ruby on Rails', 'rails': 'Ruby on Rails',
            'tailwind': 'Tailwind CSS', 'tailwind css': 'Tailwind CSS',
            'bootstrap': 'Bootstrap', 'redux': 'Redux', 'graphql': 'GraphQL',
            'rest api': 'REST APIs', 'restful api': 'REST APIs', 'rest apis': 'REST APIs',
            'svelte': 'Svelte', 'flutter': 'Flutter', 'react native': 'React Native'
        },
        'databases': {
            'postgresql': 'PostgreSQL', 'postgres': 'PostgreSQL', 'mysql': 'MySQL',
            'sqlite': 'SQLite', 'sqlite3': 'SQLite', 'mongodb': 'MongoDB',
            'redis': 'Redis', 'dynamodb': 'DynamoDB', 'cassandra': 'Cassandra',
            'oracle': 'Oracle DB', 'mariadb': 'MariaDB', 'couchdb': 'CouchDB',
            'firebase': 'Firebase', 'supabase': 'Supabase', 'neo4j': 'Neo4j',
            'elasticsearch': 'Elasticsearch'
        },
        'cloud_devops': {
            'aws': 'AWS', 'amazon web services': 'AWS', 'azure': 'Azure',
            'microsoft azure': 'Azure', 'gcp': 'GCP', 'google cloud': 'GCP',
            'google cloud platform': 'GCP', 'docker': 'Docker', 'kubernetes': 'Kubernetes',
            'k8s': 'Kubernetes', 'terraform': 'Terraform', 'ansible': 'Ansible',
            'jenkins': 'Jenkins', 'github actions': 'GitHub Actions', 'gitlab ci': 'GitLab CI',
            'ci/cd': 'CI/CD', 'cicd': 'CI/CD', 'linux': 'Linux', 'ubuntu': 'Ubuntu',
            'nginx': 'Nginx', 'apache': 'Apache', 'helm': 'Helm', 'prometheus': 'Prometheus',
            'grafana': 'Grafana', 'serverless': 'Serverless', 'lambda': 'AWS Lambda'
        },
        'tools': {
            'git': 'Git', 'github': 'GitHub', 'gitlab': 'GitLab', 'bitbucket': 'Bitbucket',
            'jira': 'Jira', 'confluence': 'Confluence', 'postman': 'Postman',
            'figma': 'Figma', 'vs code': 'VS Code', 'visual studio code': 'VS Code',
            'intellij': 'IntelliJ', 'pycharm': 'PyCharm', 'webpack': 'Webpack',
            'vite': 'Vite', 'npm': 'NPM', 'yarn': 'Yarn', 'pnpm': 'PNPM',
            'pytest': 'PyTest', 'jest': 'Jest', 'mocha': 'Mocha', 'cypress': 'Cypress',
            'selenium': 'Selenium', 'junit': 'JUnit'
        },
        'ai_datascience': {
            'machine learning': 'Machine Learning', 'deep learning': 'Deep Learning',
            'artificial intelligence': 'AI', 'ai': 'AI', 'nlp': 'NLP',
            'natural language processing': 'NLP', 'computer vision': 'Computer Vision',
            'opencv': 'OpenCV', 'pytorch': 'PyTorch', 'tensorflow': 'TensorFlow',
            'keras': 'Keras', 'scikit-learn': 'Scikit-Learn', 'sklearn': 'Scikit-Learn',
            'pandas': 'Pandas', 'numpy': 'NumPy', 'scipy': 'SciPy',
            'data science': 'Data Science', 'data analysis': 'Data Analysis',
            'data engineering': 'Data Engineering', 'llm': 'LLM', 'generative ai': 'Generative AI',
            'langchain': 'LangChain', 'transformers': 'HuggingFace Transformers'
        },
        'soft_skills': {
            'leadership': 'Leadership', 'communication': 'Communication',
            'teamwork': 'Teamwork', 'collaboration': 'Collaboration',
            'problem solving': 'Problem Solving', 'critical thinking': 'Critical Thinking',
            'time management': 'Time Management', 'agile': 'Agile', 'scrum': 'Scrum',
            'mentoring': 'Mentoring', 'project management': 'Project Management',
            'adaptability': 'Adaptability', 'analytical skills': 'Analytical Skills'
        }
    }

    # Common section header keywords
    SECTION_KEYWORDS = {
        'contact': ['contact', 'personal info', 'personal details', 'get in touch'],
        'summary': ['summary', 'professional summary', 'executive summary', 'about me', 'profile', 'objective', 'career objective'],
        'skills': ['skills', 'technical skills', 'core competencies', 'technologies', 'proficiencies', 'expertise', 'tech stack'],
        'experience': ['experience', 'work experience', 'employment history', 'professional experience', 'work history', 'career history'],
        'education': ['education', 'academic background', 'academic history', 'qualifications', 'degrees'],
        'projects': ['projects', 'personal projects', 'key projects', 'academic projects', 'portfolio projects'],
        'certifications': ['certifications', 'certificates', 'licenses', 'accreditations', 'professional certifications'],
        'achievements': ['achievements', 'awards', 'honors', 'accomplishments', 'recognition', 'publications'],
        'languages': ['languages', 'languages spoken', 'language proficiency']
    }

    @classmethod
    def extract_text_from_pdf(cls, file_input):
        """Extracts text from PDF file path or binary stream."""
        text = ""
        try:
            if isinstance(file_input, (str, os.PathLike)):
                with open(file_input, 'rb') as f:
                    reader = PyPDF2.PdfReader(f)
                    for page in reader.pages:
                        extracted = page.extract_text()
                        if extracted:
                            text += extracted + "\n"
            else:
                reader = PyPDF2.PdfReader(file_input)
                for page in reader.pages:
                    extracted = page.extract_text()
                    if extracted:
                        text += extracted + "\n"
        except Exception as e:
            print(f"PDF extraction error: {e}")
            return ""
        return text

    @classmethod
    def extract_text_from_docx(cls, file_input):
        """Extracts text from DOCX file path or binary stream."""
        text_parts = []
        try:
            doc = docx.Document(file_input)
            for para in doc.paragraphs:
                if para.text.strip():
                    text_parts.append(para.text.strip())
            for table in doc.tables:
                for row in table.rows:
                    row_cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                    if row_cells:
                        text_parts.append(" | ".join(row_cells))
        except Exception as e:
            print(f"DOCX extraction error: {e}")
            return ""
        return "\n".join(text_parts)

    @classmethod
    def clean_text(cls, raw_text):
        """Sanitizes and normalizes extracted resume text."""
        if not raw_text:
            return ""
        # Remove non-printable characters except newlines and tabs
        cleaned = re.sub(r'[^\x20-\x7E\n\t\r]', ' ', raw_text)
        # Normalize carriage returns
        cleaned = cleaned.replace('\r\n', '\n').replace('\r', '\n')
        # Collapse 3+ consecutive newlines into 2
        cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
        # Strip trailing whitespaces on each line
        lines = [line.strip() for line in cleaned.split('\n')]
        return "\n".join(lines).strip()

    @classmethod
    def extract_candidate_info(cls, text):
        """Extracts candidate contact and profile fields without inventing missing data."""
        info = {
            'name': None,
            'email': None,
            'phone': None,
            'location': None,
            'linkedin': None,
            'github': None,
            'portfolio': None,
            'title': None
        }

        if not text:
            return info

        # 1. Email extraction
        email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b', text)
        if email_match:
            info['email'] = email_match.group(0).lower()

        # 2. Phone extraction (North American and international formats)
        phone_patterns = [
            r'(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',
            r'\+?\d{1,3}[-.\s]?\d{4,5}[-.\s]?\d{4,5}'
        ]
        for pattern in phone_patterns:
            phone_match = re.search(pattern, text)
            if phone_match:
                candidate_phone = phone_match.group(0).strip()
                # Ensure it has at least 7 digits to avoid year numbers
                if len(re.sub(r'\D', '', candidate_phone)) >= 7:
                    info['phone'] = candidate_phone
                    break

        # 3. Social / Profile links
        linkedin_match = re.search(r'(?:https?://)?(?:www\.)?linkedin\.com/in/([a-zA-Z0-9_\-]+)', text, re.IGNORECASE)
        if linkedin_match:
            info['linkedin'] = f"https://linkedin.com/in/{linkedin_match.group(1)}"

        github_match = re.search(r'(?:https?://)?(?:www\.)?github\.com/([a-zA-Z0-9_\-]+)', text, re.IGNORECASE)
        if github_match:
            username = github_match.group(1)
            if username.lower() not in ['pricing', 'features', 'login', 'signup', 'explore']:
                info['github'] = f"https://github.com/{username}"

        # 3. Portfolio / Website URL
        email_domain = info['email'].split('@')[-1] if info['email'] else ""
        portfolio_matches = re.finditer(r'(?:https?://)?(?:www\.)?([a-zA-Z0-9_\-]+\.(?:dev|me|io|tech|app|vercel\.app|netlify\.app|portfolio))\b', text, re.IGNORECASE)
        for pm in portfolio_matches:
            domain = pm.group(1).lower()
            if domain != email_domain and not domain.startswith(('linkedin', 'github', 'twitter', 'google', 'gmail', 'yahoo', 'outlook')):
                info['portfolio'] = f"https://{pm.group(1)}"
                break

        # 4. Location extraction (e.g. City, State / Country)
        loc_match = re.search(r'\b([A-Z][a-zA-Z\s]+,\s*[A-Z]{2}\b|[A-Z][a-zA-Z\s]+,\s*(?:USA|India|UK|Canada|Germany|Australia|Singapore|France))\b', text)
        if loc_match:
            info['location'] = loc_match.group(0).strip()

        # 5. Candidate Name extraction (from top 8 lines, excluding non-name text)
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        for line in lines[:8]:
            # Skip lines with contact markers, common words, or links
            line_lower = line.lower()
            if any(term in line_lower for term in ['resume', 'curriculum', 'cv', 'email', 'phone', 'linkedin', 'github', 'http', '@', '.com']):
                continue
            if len(line) > 50 or len(line) < 3:
                continue
            # Match standard 2-4 word alphabetic capitalized name
            if re.match(r'^[A-Z][a-zA-Z\'\-]*(?:\s+[A-Z][a-zA-Z\'\-]*){1,3}$', line):
                info['name'] = line
                break

        # 6. Professional title extraction
        title_keywords = [
            'Software Engineer', 'Full Stack Developer', 'Frontend Developer', 'Backend Developer',
            'Python Developer', 'Java Developer', 'Data Scientist', 'Machine Learning Engineer',
            'AI Engineer', 'Cloud Engineer', 'DevOps Engineer', 'Mobile Developer', 'UI/UX Designer',
            'Product Manager', 'Data Analyst', 'Systems Engineer', 'Security Engineer'
        ]
        for t in title_keywords:
            if re.search(r'\b' + re.escape(t) + r'\b', text[:800], re.IGNORECASE):
                info['title'] = t
                break

        return info

    @classmethod
    def extract_skills(cls, text):
        """
        Scans resume text for genuine mentions in the taxonomy.
        Returns both categorized skills dict and flat normalized skills list.
        """
        if not text:
            return {'all': [], 'categorized': {}}

        text_lower = text.lower()
        categorized = {cat: [] for cat in cls.SKILL_TAXONOMY}
        all_skills_set = set()

        for category, skill_map in cls.SKILL_TAXONOMY.items():
            for trigger, canonical in skill_map.items():
                # Word-boundary matching with special handling for punctuation symbols
                if trigger in ['c++', 'c#', '.net', 'asp.net', 'ci/cd', 'node.js', 'vue.js', 'next.js', 'express.js']:
                    escaped_trigger = re.escape(trigger)
                    pattern = r'(?:^|\s|[(\[,;/])' + escaped_trigger + r'(?:$|\s|[)\],;./])'
                else:
                    pattern = r'\b' + re.escape(trigger) + r'\b'

                if re.search(pattern, text_lower):
                    if canonical not in categorized[category]:
                        categorized[category].append(canonical)
                    all_skills_set.add(canonical)

        # Sort alphabetically
        all_skills = sorted(list(all_skills_set))
        return {
            'all': all_skills,
            'categorized': categorized
        }

    @classmethod
    def extract_sections(cls, text):
        """Detects standard resume sections present and missing."""
        text_lower = text.lower()
        present = []
        missing = []

        for section, keywords in cls.SECTION_KEYWORDS.items():
            found = False
            for kw in keywords:
                # Look for section headings (isolated or start of line)
                if re.search(r'(?:^|\n)\s*' + re.escape(kw) + r'\s*[:\-]?\s*(?:\n|$)', text_lower):
                    found = True
                    break
                # Or header within first few words of a line
                if re.search(r'(?:^|\n)\s*' + re.escape(kw) + r'\b', text_lower):
                    found = True
                    break
            if found:
                present.append(section)
            else:
                missing.append(section)

        return {
            'present': present,
            'missing': missing
        }

    @classmethod
    def extract_education(cls, text):
        """Extracts education entries based on degrees, institutions, and graduation years."""
        entries = []
        if not text:
            return entries

        degree_patterns = [
            r'\b(?:Bachelor|Master|B\.?S\.?|M\.?S\.?|B\.?Tech|M\.?Tech|B\.?E\.?|M\.?E\.?|BCA|MCA|MBA|Ph\.?D\.?|Associate|Diploma)\b[^\n,]*'
        ]
        year_pattern = r'\b(19\d{2}|20\d{2})\s*(?:-|–|to)\s*(19\d{2}|20\d{2}|Present|Current|Ongoing)?\b'
        
        lines = text.split('\n')
        in_edu_section = False
        
        for i, line in enumerate(lines):
            line_clean = line.strip()
            if not line_clean:
                continue
            line_lower = line_clean.lower()
            
            # Check section header
            if any(h in line_lower for h in cls.SECTION_KEYWORDS['education']):
                in_edu_section = True
                continue
            elif in_edu_section and any(h in line_lower for h in cls.SECTION_KEYWORDS['experience'] + cls.SECTION_KEYWORDS['projects'] + cls.SECTION_KEYWORDS['skills']):
                in_edu_section = False
                
            # If line matches degree pattern
            for dp in degree_patterns:
                match = re.search(dp, line_clean, re.IGNORECASE)
                if match:
                    degree_name = match.group(0).strip()
                    # Look around nearby lines for institution and year
                    surrounding = " ".join(lines[max(0, i-1):min(len(lines), i+3)])
                    year_match = re.search(year_pattern, surrounding, re.IGNORECASE)
                    year_str = year_match.group(0) if year_match else None
                    
                    entries.append({
                        'degree': degree_name,
                        'details': line_clean,
                        'year': year_str
                    })
                    break

        return entries

    @classmethod
    def extract_experience(cls, text):
        """Extracts work experience records, roles, companies, and measurable metrics."""
        entries = []
        if not text:
            return entries

        lines = text.split('\n')
        in_exp_section = False
        current_entry = None
        
        date_pattern = r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{4}\s*(?:-|–|to)\s*(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec[a-z]*\.?\s+\d{4}|Present|Current)\b|\b\d{4}\s*(?:-|–|to)\s*(?:\d{4}|Present|Current)\b'
        action_verbs = ['developed', 'designed', 'built', 'implemented', 'led', 'managed', 'created', 'optimized', 'engineered', 'spearheaded', 'orchestrated', 'automated']

        for line in lines:
            line_clean = line.strip()
            if not line_clean:
                continue
            line_lower = line_clean.lower()

            if any(h in line_lower for h in cls.SECTION_KEYWORDS['experience']):
                in_exp_section = True
                continue
            elif in_exp_section and any(h in line_lower for h in cls.SECTION_KEYWORDS['education'] + cls.SECTION_KEYWORDS['projects'] + cls.SECTION_KEYWORDS['skills'] + cls.SECTION_KEYWORDS['certifications']):
                in_exp_section = False
                if current_entry:
                    entries.append(current_entry)
                    current_entry = None

            if in_exp_section:
                # Detect date marker indicating new experience block
                date_match = re.search(date_pattern, line_clean, re.IGNORECASE)
                if date_match or (len(line_clean) < 60 and any(title in line_lower for title in ['engineer', 'developer', 'intern', 'consultant', 'manager', 'lead', 'analyst', 'architect'])):
                    if current_entry:
                        entries.append(current_entry)
                    current_entry = {
                        'title_company': line_clean,
                        'dates': date_match.group(0) if date_match else None,
                        'responsibilities': [],
                        'measurable_results': []
                    }
                elif current_entry:
                    if line_clean.startswith(('•', '-', '*', '–')) or any(v in line_lower for v in action_verbs):
                        clean_bullet = line_clean.lstrip('•-*– ').strip()
                        current_entry['responsibilities'].append(clean_bullet)
                        # Check for metrics (% or numbers or $)
                        if re.search(r'\b\d+(?:\.\d+)?%|\$\d+|\b\d+\s*(?:ms|seconds|users|clients|requests|X)\b', clean_bullet, re.IGNORECASE):
                            current_entry['measurable_results'].append(clean_bullet)

        if current_entry:
            entries.append(current_entry)

        return entries

    @classmethod
    def extract_projects(cls, text):
        """Extracts project entries with descriptions and technology stacks."""
        projects = []
        if not text:
            return projects

        lines = text.split('\n')
        in_proj_section = False
        current_proj = None

        for line in lines:
            line_clean = line.strip()
            if not line_clean:
                continue
            line_lower = line_clean.lower()

            if any(h in line_lower for h in cls.SECTION_KEYWORDS['projects']):
                in_proj_section = True
                continue
            elif in_proj_section and any(h in line_lower for h in cls.SECTION_KEYWORDS['experience'] + cls.SECTION_KEYWORDS['education'] + cls.SECTION_KEYWORDS['skills'] + cls.SECTION_KEYWORDS['certifications']):
                in_proj_section = False
                if current_proj:
                    projects.append(current_proj)
                    current_proj = None

            if in_proj_section:
                # Project header line: typically bold / short line with pipe or parenthesis
                if len(line_clean) < 80 and not line_clean.startswith(('•', '-', '*')) and (any(c in line_clean for c in ['|', '-', ':', '–', '(']) or re.match(r'^[A-Z0-9][A-Za-z0-9\s\-_]{2,35}$', line_clean)):
                    if current_proj:
                        projects.append(current_proj)
                    current_proj = {
                        'name': line_clean,
                        'bullets': [],
                        'link': None
                    }
                    link_match = re.search(r'https?://[^\s)]+', line_clean)
                    if link_match:
                        current_proj['link'] = link_match.group(0)
                elif current_proj:
                    clean_bullet = line_clean.lstrip('•-*– ').strip()
                    current_proj['bullets'].append(clean_bullet)
                    link_match = re.search(r'https?://[^\s)]+', clean_bullet)
                    if link_match and not current_proj['link']:
                        current_proj['link'] = link_match.group(0)

        if current_proj:
            projects.append(current_proj)

        return projects

    @classmethod
    def extract_certifications(cls, text):
        """Extracts certifications and licenses."""
        certs = []
        if not text:
            return certs
        cert_keywords = [
            'AWS Certified', 'Google Cloud Certified', 'Microsoft Certified', 'Azure Certified',
            'Certified Kubernetes', 'CKA', 'CKAD', 'PMP', 'Scrum Master', 'CSM', 'CISSP',
            'CompTIA', 'CCNA', 'CCNP', 'TensorFlow Developer Certificate', 'Meta Certified'
        ]
        for kw in cert_keywords:
            if re.search(r'\b' + re.escape(kw) + r'\b', text, re.IGNORECASE):
                certs.append(kw)
        return list(set(certs))

    @classmethod
    def extract_achievements(cls, text):
        """Extracts awards, honors, and competition rankings."""
        achievements = []
        if not text:
            return achievements
        lines = text.split('\n')
        for line in lines:
            line_clean = line.strip()
            if any(term in line_clean.lower() for term in ['award', 'winner', 'scholarship', 'rank', 'dean\'s list', 'hackathon', 'published', 'patent']):
                if len(line_clean) < 150 and not line_clean.lower().startswith('achievement'):
                    achievements.append(line_clean.lstrip('•-*– '))
        return achievements[:5]

    @classmethod
    def parse_resume(cls, file_path_or_bytes, filename=""):
        """
        Complete parsing pipeline from raw document to fully structured schema.
        Rejects empty/scanned PDFs with no readable text.
        """
        ext = ""
        if isinstance(file_path_or_bytes, (str, os.PathLike)):
            _, ext = os.path.splitext(file_path_or_bytes)
        elif filename:
            _, ext = os.path.splitext(filename)

        ext = ext.lower()
        if ext == '.pdf':
            raw_text = cls.extract_text_from_pdf(file_path_or_bytes)
        elif ext in ['.docx', '.doc']:
            raw_text = cls.extract_text_from_docx(file_path_or_bytes)
        else:
            raw_text = cls.extract_text_from_pdf(file_path_or_bytes)
            if not raw_text:
                raw_text = cls.extract_text_from_docx(file_path_or_bytes)

        if not raw_text:
            try:
                if isinstance(file_path_or_bytes, (str, os.PathLike)):
                    with open(file_path_or_bytes, 'r', encoding='utf-8', errors='ignore') as f:
                        raw_text = f.read()
                elif hasattr(file_path_or_bytes, 'getvalue'):
                    raw_text = file_path_or_bytes.getvalue().decode('utf-8', errors='ignore')
            except Exception:
                pass

        clean = cls.clean_text(raw_text)

        # Validation: check if document yielded readable text
        if len(clean.strip()) < 30:
            return {
                'success': False,
                'error': 'Unable to extract readable text. The document appears empty or is an image-scanned PDF.',
                'text': '',
                'word_count': 0
            }

        words = clean.split()
        candidate_info = cls.extract_candidate_info(clean)
        skills_data = cls.extract_skills(clean)
        sections = cls.extract_sections(clean)
        education = cls.extract_education(clean)
        experience = cls.extract_experience(clean)
        projects = cls.extract_projects(clean)
        certifications = cls.extract_certifications(clean)
        achievements = cls.extract_achievements(clean)

        return {
            'success': True,
            'text': clean,
            'word_count': len(words),
            'candidate': candidate_info,
            'name': candidate_info.get('name'),
            'email': candidate_info.get('email'),
            'phone': candidate_info.get('phone'),
            'location': candidate_info.get('location'),
            'linkedin': candidate_info.get('linkedin'),
            'github': candidate_info.get('github'),
            'portfolio': candidate_info.get('portfolio'),
            'title': candidate_info.get('title'),
            'summary': candidate_info.get('summary'),
            'skills': skills_data['all'],
            'skills_categorized': skills_data['categorized'],
            'sections_present': sections['present'],
            'sections_missing': sections['missing'],
            'education': education,
            'experience': experience,
            'projects': projects,
            'certifications': certifications,
            'achievements': achievements
        }
