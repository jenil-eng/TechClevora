import unittest
import os
import json
from app import create_app
from models import db, User, Resume

class TechClevoraTestCase(unittest.TestCase):
    def setUp(self):
        # Configure app for testing
        self.app = create_app({
            'TESTING': True,
            'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:'
        })
        
        self.client = self.app.test_client()
        
        # Bind the app context
        self.ctx = self.app.app_context()
        self.ctx.push()
        
        # Create all tables
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def test_user_registration_and_login(self):
        # 1. Register a user
        reg_payload = {
            'username': 'TestCandidate',
            'email': 'candidate@test.com',
            'password': 'securepassword123'
        }
        res = self.client.post('/api/auth/register', 
                               data=json.dumps(reg_payload),
                               content_type='application/json')
        self.assertEqual(res.status_code, 201)
        data = json.loads(res.data)
        self.assertIn('token', data)
        self.assertEqual(data['user']['username'], 'TestCandidate')
        self.assertEqual(data['user']['role'], 'admin') # First user registered becomes admin

        # 2. Login the user
        login_payload = {
            'email': 'candidate@test.com',
            'password': 'securepassword123'
        }
        res = self.client.post('/api/auth/login',
                               data=json.dumps(login_payload),
                               content_type='application/json')
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertIn('token', data)

    def test_unauthorized_dashboard_stats(self):
        # Request dashboard without token
        res = self.client.get('/api/dashboard/stats')
        self.assertEqual(res.status_code, 401)
        data = json.loads(res.data)
        self.assertEqual(data['message'], 'Token is missing!')

    def test_resume_parser_service_fallback(self):
        from services.parser_service import ResumeParserService
        # Test empty parser trigger
        parsed = ResumeParserService.parse_resume('non_existent_file.pdf')
        self.assertEqual(parsed['text'], '')
        self.assertEqual(parsed['skills'], [])

    def test_mock_interview_flow(self):
        # 1. Register and get token
        reg_payload = {
            'username': 'Interviewee',
            'email': 'interviewee@test.com',
            'password': 'password123'
        }
        res = self.client.post('/api/auth/register', 
                               data=json.dumps(reg_payload),
                               content_type='application/json')
        token = json.loads(res.data)['token']
        headers = {'Authorization': f'Bearer {token}'}

        # 2. Start interview
        start_payload = {
            'job_role': 'Software Engineer',
            'experience_level': 'Entry Level',
            'difficulty': 'Medium',
            'question_types': ['Technical']
        }
        res = self.client.post('/api/interview/start',
                               data=json.dumps(start_payload),
                               content_type='application/json',
                               headers=headers)
        self.assertEqual(res.status_code, 201)
        data = json.loads(res.data)
        session_id = data['session_id']
        questions = data['questions']
        self.assertEqual(len(questions), 5)

        # 3. Answer a question
        ans_payload = {
            'question_id': questions[0]['id'],
            'user_answer': 'QuickSort average time complexity is O(N log N) and space complexity is O(log N).'
        }
        res = self.client.post('/api/interview/answer',
                               data=json.dumps(ans_payload),
                               content_type='application/json',
                               headers=headers)
        self.assertEqual(res.status_code, 200)
        ans_data = json.loads(res.data)
        self.assertIn('scores', ans_data)

        # 4. Submit interview
        submit_payload = {
            'session_id': session_id
        }
        res = self.client.post('/api/interview/submit',
                               data=json.dumps(submit_payload),
                               content_type='application/json',
                               headers=headers)
        self.assertEqual(res.status_code, 201)
        report_data = json.loads(res.data)['report']
        
        # Verify scores are populated correctly (and not all defaults of 50)
        self.assertNotEqual(report_data['scores']['technical'], 50)
        self.assertNotEqual(report_data['scores']['grammar'], 50)

        # 5. Download report
        res = self.client.get(f'/api/reports/{report_data["id"]}/download?token={token}')
        self.assertEqual(res.status_code, 200)
        self.assertIn('AI Interview Assessment', res.data.decode('utf-8'))

    def test_bulk_scanner_workflow(self):
        # 1. Register and get token
        reg_payload = {
            'username': 'RecruiterUser',
            'email': 'recruiter@test.com',
            'password': 'password123'
        }
        res = self.client.post('/api/auth/register', 
                               data=json.dumps(reg_payload),
                               content_type='application/json')
        token = json.loads(res.data)['token']
        headers = {'Authorization': f'Bearer {token}'}

        # 2. Get initial dashboard stats (must be empty/default values)
        res = self.client.get('/api/bulk-dashboard', headers=headers)
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertIsNone(data['job'])
        self.assertEqual(len(data['candidates']), 0)

        # 3. Simulating file uploads
        import io
        data = {
            'files': [
                (io.BytesIO(b"Dummy resume text with React, Node skills"), 'ResumeJohn.pdf'),
                (io.BytesIO(b"Dummy resume text with Python, Cloud skills"), 'ResumeEmily.docx')
            ]
        }
        res = self.client.post('/api/bulk-upload',
                               data=data,
                               content_type='multipart/form-data',
                               headers=headers)
        self.assertEqual(res.status_code, 201)
        res_data = json.loads(res.data)
        bulk_job_id = res_data['bulk_job_id']
        file_tasks = res_data['file_tasks']
        self.assertEqual(len(file_tasks), 2)

        # 4. Trigger bulk analysis
        analysis_payload = {
            'bulk_job_id': bulk_job_id,
            'file_tasks': file_tasks
        }
        res = self.client.post('/api/bulk-analysis',
                               data=json.dumps(analysis_payload),
                               content_type='application/json',
                               headers=headers)
        self.assertEqual(res.status_code, 200)

        # Poll until the background thread completes processing
        import time
        from models import BulkJob
        for _ in range(50):
            db.session.expire_all()
            bulk_job = db.session.get(BulkJob, bulk_job_id)
            if bulk_job.status == 'completed':
                break
            time.sleep(0.1)

        # 5. Fetch bulk recruiter dashboard stats
        res = self.client.get(f'/api/bulk-dashboard?bulk_job_id={bulk_job_id}', headers=headers)
        self.assertEqual(res.status_code, 200)
        dash_data = json.loads(res.data)
        self.assertIsNotNone(dash_data['job'])
        self.assertEqual(dash_data['stats']['total_uploaded'], 2)
        self.assertEqual(dash_data['stats']['processed'], 2)
        self.assertEqual(len(dash_data['candidates']), 2)
        self.assertEqual(len(dash_data['ranking']), 2)

        # Check candidate scorecard view
        cand_id = dash_data['candidates'][0]['id']
        res = self.client.get(f'/api/candidate/{cand_id}', headers=headers)
        self.assertEqual(res.status_code, 200)
        c_details = json.loads(res.data)['candidate']
        self.assertEqual(c_details['id'], cand_id)

        # Check zip download
        res = self.client.get(f'/api/download-all/{bulk_job_id}')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.mimetype, 'application/zip')

        # Clean up candidate
        res = self.client.delete(f'/api/analysis/{cand_id}', headers=headers)
        self.assertEqual(res.status_code, 200)

if __name__ == '__main__':
    unittest.main()
