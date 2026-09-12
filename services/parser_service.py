import re
import os
import PyPDF2
import docx

class ResumeParserService:
    @staticmethod
    def extract_text_from_pdf(file_path):
        text = ""
        try:
            with open(file_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
        except Exception as e:
            print(f"Error parsing PDF: {e}")
        return text

    @staticmethod
    def extract_text_from_docx(file_path):
        text = ""
        try:
            doc = docx.Document(file_path)
            for para in doc.paragraphs:
                text += para.text + "\n"
        except Exception as e:
            print(f"Error parsing DOCX: {e}")
        return text

    @classmethod
    def parse_resume(cls, file_path):
        _, ext = os.path.splitext(file_path)
        ext = ext.lower()
        
        if ext == '.pdf':
            text = cls.extract_text_from_pdf(file_path)
        elif ext in ['.docx', '.doc']:
            text = cls.extract_text_from_docx(file_path)
        else:
            text = ""
            
        if not text:
            return {
                'text': '',
                'name': '',
                'email': '',
                'phone': '',
                'skills': [],
                'education': [],
                'experience': []
            }
            
        email = cls._extract_email(text)
        phone = cls._extract_phone(text)
        name = cls._extract_name(text)
        skills = cls._extract_skills(text)
        education = cls._extract_education(text)
        experience = cls._extract_experience(text)
        
        return {
            'text': text,
            'name': name,
            'email': email,
            'phone': phone,
            'skills': skills,
            'education': education,
            'experience': experience
        }

    @staticmethod
    def _extract_email(text):
        pattern = r'[\w\.-]+@[\w\.-]+\.\w+'
        match = re.search(pattern, text)
        return match.group(0) if match else ''

    @staticmethod
    def _extract_phone(text):
        # Broad pattern covering various international formats
        pattern = r'(?:(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4})'
        match = re.search(pattern, text)
        return match.group(0).strip() if match else ''

    @staticmethod
    def _extract_name(text):
        # Look for first two capitalized words on the first line as a fallback
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        if not lines:
            return ''
            
        first_line = lines[0]
        # Match names like "John Doe" or "John M. Doe"
        match = re.match(r'^([A-Z][a-z]+(?:\s+[A-Z]\.?\s+|\s+)[A-Z][a-z]+)', first_line)
        if match:
            return match.group(1)
            
        # Fallback to the first line if it's short
        if len(first_line) < 50 and not any(kw in first_line.lower() for kw in ['resume', 'curriculum', 'cv']):
            return first_line
            
        return 'Job Seeker'

    @staticmethod
    def _extract_skills(text):
        # Predefined checklist of popular technical skills
        common_skills = [
            'python', 'javascript', 'typescript', 'java', 'c\\+\\+', 'c#', 'php', 'ruby', 'go', 'rust', 'swift', 'kotlin',
            'html', 'css', 'react', 'angular', 'vue', 'next\\.js', 'node\\.js', 'express', 'django', 'flask', 'spring boot',
            'mysql', 'postgresql', 'mongodb', 'sqlite', 'redis', 'oracle', 'cassandra', 'dynamodb',
            'aws', 'azure', 'gcp', 'docker', 'kubernetes', 'jenkins', 'git', 'github', 'gitlab', 'ci/cd', 'terraform', 'ansible',
            'machine learning', 'deep learning', 'nlp', 'computer vision', 'tensorflow', 'pytorch', 'scikit-learn', 'pandas', 'numpy',
            'data science', 'ai', 'devops', 'cyber security', 'blockchain', 'agile', 'scrum', 'jira', 'figma', 'ui/ux'
        ]
        
        found = []
        text_lower = text.lower()
        for skill in common_skills:
            # Word boundary check, escaping visual skills like C++ or Next.js
            pattern = r'\b' + skill + r'\b'
            if skill in ['c\\+\\+', 'ci/cd', 'next\\.js', 'node\\.js']:
                pattern = skill
            if re.search(pattern, text_lower):
                # Clean visual name
                clean_skill = skill.replace('\\', '').title()
                if clean_skill == 'Aws': clean_skill = 'AWS'
                if clean_skill == 'Gcp': clean_skill = 'GCP'
                if clean_skill == 'Html': clean_skill = 'HTML'
                if clean_skill == 'Css': clean_skill = 'CSS'
                if clean_skill == 'Ui/Ux': clean_skill = 'UI/UX'
                if clean_skill == 'Nlp': clean_skill = 'NLP'
                if clean_skill == 'Ci/Cd': clean_skill = 'CI/CD'
                found.append(clean_skill)
        return found

    @staticmethod
    def _extract_education(text):
        education_keywords = ['education', 'academic', 'qualification', 'degree', 'university', 'college', 'school', 'bachelor', 'master', 'phd', 'b.tech', 'm.tech', 'bca', 'mca', 'bsc', 'msc']
        lines = text.split('\n')
        extracted = []
        
        recording = False
        captured = []
        for line in lines:
            line_clean = line.strip()
            if not line_clean:
                continue
            
            line_lower = line_clean.lower()
            # If we see another major section header, stop
            if recording and any(header in line_lower for header in ['experience', 'work', 'projects', 'skills', 'certificates', 'achievements', 'languages']):
                recording = False
                if captured:
                    extracted.append(" ".join(captured))
                    captured = []
                    
            if any(kw in line_lower for kw in education_keywords):
                recording = True
                captured.append(line_clean)
            elif recording:
                captured.append(line_clean)
                if len(captured) > 4: # limit size of block
                    recording = False
                    extracted.append(" ".join(captured))
                    captured = []
                    
        if captured:
            extracted.append(" ".join(captured))
            
        return extracted if extracted else ["Self-Taught / General Degree"]

    @staticmethod
    def _extract_experience(text):
        exp_keywords = ['experience', 'employment', 'work history', 'professional background', 'job history']
        lines = text.split('\n')
        extracted = []
        
        recording = False
        captured = []
        for line in lines:
            line_clean = line.strip()
            if not line_clean:
                continue
            
            line_lower = line_clean.lower()
            # If we see another major section header, stop
            if recording and any(header in line_lower for header in ['education', 'skills', 'projects', 'certificates', 'achievements', 'languages']):
                recording = False
                if captured:
                    extracted.append(" ".join(captured))
                    captured = []
                    
            if any(kw in line_lower for kw in exp_keywords):
                recording = True
                captured.append(line_clean)
            elif recording:
                captured.append(line_clean)
                if len(captured) > 6: # limit size of block
                    recording = False
                    extracted.append(" ".join(captured))
                    captured = []
                    
        if captured:
            extracted.append(" ".join(captured))
            
        return extracted if extracted else ["Fresher / Entry Level Experience"]
