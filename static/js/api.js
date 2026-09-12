/* 
   ==========================================================================
   TECH CLEVORA - API Integration Wrapper
   ==========================================================================
*/

const TechClevoraAPI = {
    TOKEN_KEY: 'techclevora_token',

    /**
     * Persists the JWT issued by /api/auth/login.
     * persist=true  -> localStorage (survives browser restarts, "Remember me")
     * persist=false -> sessionStorage (cleared when the tab/browser closes)
     */
    setToken(token, persist = true) {
        localStorage.removeItem(this.TOKEN_KEY);
        sessionStorage.removeItem(this.TOKEN_KEY);
        localStorage.removeItem('meetai_token');
        sessionStorage.removeItem('meetai_token');
        if (!token) return;

        if (persist) {
            localStorage.setItem(this.TOKEN_KEY, token);
        } else {
            sessionStorage.setItem(this.TOKEN_KEY, token);
        }
    },

    getToken() {
        return localStorage.getItem(this.TOKEN_KEY) || sessionStorage.getItem(this.TOKEN_KEY) || localStorage.getItem('meetai_token') || sessionStorage.getItem('meetai_token');
    },

    isLoggedIn() {
        return !!this.getToken();
    },

    logout() {
        this.setToken(null);
    },

    getBaseUrl() {
        return window.API_BASE_URL || localStorage.getItem('techclevora_api_url') || '';
    },

    async request(endpoint, options = {}) {
        const token = this.getToken();
        const headers = options.headers || {};
        
        // If data is not FormData, default to application/json
        if (!(options.body instanceof FormData) && !headers['Content-Type']) {
            headers['Content-Type'] = 'application/json';
        }
        
        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }

        const baseUrl = this.getBaseUrl();
        const fullUrl = endpoint.startsWith('http') ? endpoint : `${baseUrl}${endpoint}`;
        
        options.headers = headers;
        
        try {
            const response = await fetch(fullUrl, options);
            const data = await response.json().catch(() => ({}));
            
            if (!response.ok) {
                if (response.status === 401) {
                    this.logout();
                    window.location.hash = '#login';
                }
                const errMsg = data.message || `API error (status: ${response.status})`;
                throw new Error(errMsg);
            }
            return data;
        } catch (error) {
            console.error(`API Request Failure [${endpoint}]:`, error);
            throw error;
        }
    },

    /* --- Auth APIs --- */
    register(username, email, password) {
        return this.request('/api/auth/register', {
            method: 'POST',
            body: JSON.stringify({ username, email, password })
        });
    },

    login(email, password) {
        return this.request('/api/auth/login', {
            method: 'POST',
            body: JSON.stringify({ email, password })
        });
    },

    getProfile() {
        return this.request('/api/auth/profile', { method: 'GET' });
    },

    updateProfile(data) {
        return this.request('/api/auth/profile', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    },

    uploadAvatar(formData) {
        return this.request('/api/auth/profile-pic', {
            method: 'POST',
            body: formData
        });
    },

    verifyOTP(email, otp) {
        return this.request('/api/auth/verify-otp', {
            method: 'POST',
            body: JSON.stringify({ email, otp })
        });
    },

    forgotPassword(email) {
        return this.request('/api/auth/forgot-password', {
            method: 'POST',
            body: JSON.stringify({ email })
        });
    },

    /* --- User / Features APIs --- */
    getStats() {
        return this.request('/api/dashboard/stats', { method: 'GET' });
    },

    analyzeResume(formData) {
        return this.request('/api/resume/analyze', {
            method: 'POST',
            body: formData
        });
    },

    startInterview(jobRole, experienceLevel, difficulty, questionTypes) {
        return this.request('/api/interview/start', {
            method: 'POST',
            body: JSON.stringify({
                job_role: jobRole,
                experience_level: experienceLevel,
                difficulty: difficulty,
                question_types: questionTypes
            })
        });
    },

    submitAnswer(questionId, userAnswer) {
        return this.request('/api/interview/answer', {
            method: 'POST',
            body: JSON.stringify({
                question_id: questionId,
                user_answer: userAnswer
            })
        });
    },

    submitInterview(sessionId) {
        return this.request('/api/interview/submit', {
            method: 'POST',
            body: JSON.stringify({ session_id: sessionId })
        });
    },

    getReport(reportId) {
        return this.request(`/api/reports/${reportId}`, { method: 'GET' });
    },

    getCompanies() {
        return this.request('/api/companies', { method: 'GET' });
    },

    getCompanyPrep(name) {
        return this.request(`/api/companies/${name}`, { method: 'GET' });
    },

    getNotifications() {
        return this.request('/api/notifications', { method: 'GET' });
    },

    markNotificationsRead() {
        return this.request('/api/notifications/read', { method: 'POST' });
    },

    submitFeedback(name, email, message) {
        return this.request('/api/feedback', {
            method: 'POST',
            body: JSON.stringify({ name, email, message })
        });
    }
};

window.TechClevoraAPI = TechClevoraAPI;
window.MeetAiAPI = TechClevoraAPI;

