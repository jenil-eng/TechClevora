/* ==========================================================================
   TECH CLEVORA - GLOBAL SEARCHABLE SELECT & CUSTOM DROPDOWN SYSTEM
   Full keyboard accessibility (Arrow Up/Down, Enter, Esc, Tab),
   real-time substring filtering, optgroups, dark & light theme, mobile-safe
   ========================================================================== */
class SearchableSelect {
    constructor(selectEl, options = {}) {
        if (!selectEl || selectEl.dataset.searchableSelectInit === 'true') return;
        this.select = selectEl;
        this.options = Object.assign({
            placeholder: selectEl.getAttribute('data-placeholder') || 'Select option...',
            searchPlaceholder: selectEl.getAttribute('data-search-placeholder') || 'Search options...',
            allowClear: selectEl.hasAttribute('data-allow-clear'),
            onSelect: null
        }, options);

        this.isOpen = false;
        this.highlightedIndex = -1;
        this.items = [];
        this.init();
    }

    init() {
        this.select.dataset.searchableSelectInit = 'true';

        // Wrapper container
        this.container = document.createElement('div');
        this.container.className = 'searchable-select-wrap';
        if (this.select.disabled) this.container.classList.add('is-disabled');

        if (this.select.style.flex) {
            this.container.style.flex = this.select.style.flex;
        }

        // Hide the original native select visually while keeping it in the DOM for forms
        this.select.classList.add('searchable-select-native-hidden');
        this.select.parentNode.insertBefore(this.container, this.select);
        this.container.appendChild(this.select);

        // Trigger button
        this.trigger = document.createElement('button');
        this.trigger.type = 'button';
        this.trigger.className = 'searchable-select-trigger';
        this.trigger.setAttribute('role', 'combobox');
        this.trigger.setAttribute('aria-expanded', 'false');
        this.trigger.setAttribute('aria-haspopup', 'listbox');

        this.triggerValue = document.createElement('span');
        this.triggerValue.className = 'trigger-value';

        this.triggerIcons = document.createElement('span');
        this.triggerIcons.className = 'trigger-icons';

        if (this.options.allowClear) {
            this.clearBtn = document.createElement('span');
            this.clearBtn.className = 'clear-btn';
            this.clearBtn.innerHTML = '<i class="fa-solid fa-xmark"></i>';
            this.clearBtn.title = 'Clear selection';
            this.clearBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.clearSelection();
            });
            this.triggerIcons.appendChild(this.clearBtn);
        }

        this.chevron = document.createElement('i');
        this.chevron.className = 'fa-solid fa-chevron-down chevron-icon';
        this.triggerIcons.appendChild(this.chevron);

        this.trigger.appendChild(this.triggerValue);
        this.trigger.appendChild(this.triggerIcons);
        this.container.appendChild(this.trigger);

        // Dropdown menu
        this.dropdown = document.createElement('div');
        this.dropdown.className = 'searchable-select-dropdown';
        this.dropdown.setAttribute('role', 'listbox');

        // Search input bar
        this.searchWrap = document.createElement('div');
        this.searchWrap.className = 'searchable-select-search';
        this.searchWrap.innerHTML = `
            <i class="fa-solid fa-magnifying-glass" aria-hidden="true"></i>
            <input type="text" placeholder="${this.options.searchPlaceholder}" autocomplete="off" spellcheck="false" role="searchbox" aria-label="${this.options.searchPlaceholder}">
        `;
        this.searchInput = this.searchWrap.querySelector('input');
        this.dropdown.appendChild(this.searchWrap);

        // Scrollable Options List
        this.list = document.createElement('div');
        this.list.className = 'searchable-select-list';
        this.dropdown.appendChild(this.list);

        // No-results state
        this.emptyState = document.createElement('div');
        this.emptyState.className = 'searchable-select-empty';
        this.emptyState.style.display = 'none';
        this.emptyState.innerHTML = `
            <div class="empty-title">No results found</div>
            <div style="font-size:12px; color:var(--text-muted);">Try another keyword.</div>
        `;
        this.dropdown.appendChild(this.emptyState);

        this.container.appendChild(this.dropdown);

        // Build list and sync trigger
        this.buildOptions();
        this.updateTriggerDisplay();

        // Bind interactive events
        this.bindEvents();
    }

    buildOptions() {
        this.list.innerHTML = '';
        this.items = [];

        const children = Array.from(this.select.children);

        children.forEach(child => {
            if (child.tagName === 'OPTGROUP') {
                const groupTitle = document.createElement('div');
                groupTitle.className = 'searchable-select-group-title';
                groupTitle.textContent = child.label;
                this.list.appendChild(groupTitle);

                Array.from(child.children).forEach(opt => {
                    this.createOptionItem(opt, child.label, groupTitle);
                });
            } else if (child.tagName === 'OPTION') {
                this.createOptionItem(child, null, null);
            }
        });
    }

    createOptionItem(optionEl, groupLabel = null, groupTitleEl = null) {
        const itemEl = document.createElement('div');
        itemEl.className = 'searchable-select-item';
        itemEl.setAttribute('role', 'option');
        itemEl.textContent = optionEl.text;
        itemEl.dataset.value = optionEl.value;

        if (optionEl.selected) {
            itemEl.classList.add('is-selected');
            itemEl.setAttribute('aria-selected', 'true');
        }
        if (optionEl.disabled) {
            itemEl.classList.add('is-disabled');
            itemEl.style.opacity = '0.5';
            itemEl.style.pointerEvents = 'none';
        }

        const itemObj = {
            value: optionEl.value,
            text: optionEl.text,
            optionEl: optionEl,
            itemEl: itemEl,
            groupLabel: groupLabel,
            groupTitleEl: groupTitleEl,
            visible: true
        };

        itemEl.addEventListener('click', (e) => {
            e.stopPropagation();
            this.selectValue(itemObj.value);
            this.close();
            this.trigger.focus();
        });

        this.list.appendChild(itemEl);
        this.items.push(itemObj);
    }

    updateTriggerDisplay() {
        const selectedOpt = this.select.options[this.select.selectedIndex];
        if (selectedOpt && selectedOpt.value !== '') {
            this.triggerValue.textContent = selectedOpt.text;
            this.triggerValue.classList.remove('is-placeholder');
            this.container.classList.add('has-value');
        } else {
            this.triggerValue.textContent = this.options.placeholder;
            this.triggerValue.classList.add('is-placeholder');
            this.container.classList.remove('has-value');
        }

        this.items.forEach(item => {
            const isSel = item.value === (selectedOpt ? selectedOpt.value : null);
            item.itemEl.classList.toggle('is-selected', isSel);
            item.itemEl.setAttribute('aria-selected', isSel ? 'true' : 'false');
        });
    }

    selectValue(value) {
        if (this.select.value !== value) {
            this.select.value = value;
            this.select.dispatchEvent(new Event('change', { bubbles: true }));
            this.select.dispatchEvent(new Event('input', { bubbles: true }));
        }
        this.updateTriggerDisplay();
        if (typeof this.options.onSelect === 'function') {
            this.options.onSelect(value);
        }
    }

    clearSelection() {
        this.select.value = '';
        this.select.dispatchEvent(new Event('change', { bubbles: true }));
        this.select.dispatchEvent(new Event('input', { bubbles: true }));
        this.updateTriggerDisplay();
    }

    filterOptions(query) {
        const q = (query || '').trim().toLowerCase();
        let visibleCount = 0;
        const groupVisibility = new Map();

        this.items.forEach(item => {
            const matches = !q || item.text.toLowerCase().includes(q) || (item.groupLabel && item.groupLabel.toLowerCase().includes(q));
            item.visible = matches;
            item.itemEl.style.display = matches ? 'flex' : 'none';
            if (matches) {
                visibleCount++;
                if (item.groupTitleEl) groupVisibility.set(item.groupTitleEl, true);
            }
        });

        this.items.forEach(item => {
            if (item.groupTitleEl) {
                const hasVisible = groupVisibility.get(item.groupTitleEl) || false;
                item.groupTitleEl.style.display = hasVisible ? 'flex' : 'none';
            }
        });

        this.emptyState.style.display = visibleCount === 0 ? 'block' : 'none';
        this.highlightedIndex = -1;
        this.highlightFirstVisible();
    }

    highlightFirstVisible() {
        const visibleItems = this.items.filter(i => i.visible && !i.optionEl.disabled);
        if (visibleItems.length > 0) {
            this.setHighlighted(0);
        } else {
            this.clearHighlight();
        }
    }

    setHighlighted(index) {
        const visibleItems = this.items.filter(i => i.visible && !i.optionEl.disabled);
        this.clearHighlight();
        if (index >= 0 && index < visibleItems.length) {
            this.highlightedIndex = index;
            const target = visibleItems[index];
            target.itemEl.classList.add('is-focused');
            target.itemEl.scrollIntoView({ block: 'nearest' });
        }
    }

    clearHighlight() {
        this.items.forEach(i => i.itemEl.classList.remove('is-focused'));
    }

    open() {
        if (this.isOpen || this.select.disabled) return;
        document.querySelectorAll('.searchable-select-wrap.is-open').forEach(el => {
            if (el.__searchableSelect) el.__searchableSelect.close();
        });

        this.isOpen = true;
        this.container.classList.add('is-open');
        this.trigger.setAttribute('aria-expanded', 'true');

        const rect = this.container.getBoundingClientRect();
        const spaceBelow = window.innerHeight - rect.bottom;
        const spaceAbove = rect.top;
        if (spaceBelow < 280 && spaceAbove > spaceBelow) {
            this.container.classList.add('open-upward');
        } else {
            this.container.classList.remove('open-upward');
        }

        this.searchInput.value = '';
        this.filterOptions('');
        setTimeout(() => this.searchInput.focus(), 60);
    }

    close() {
        if (!this.isOpen) return;
        this.isOpen = false;
        this.container.classList.remove('is-open');
        this.trigger.setAttribute('aria-expanded', 'false');
        this.clearHighlight();
    }

    toggle() {
        if (this.isOpen) this.close();
        else this.open();
    }

    bindEvents() {
        this.container.__searchableSelect = this;

        this.trigger.addEventListener('click', (e) => {
            e.stopPropagation();
            this.toggle();
        });

        this.trigger.addEventListener('keydown', (e) => {
            if (e.key === 'ArrowDown' || e.key === 'ArrowUp' || e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                this.open();
            }
        });

        this.searchInput.addEventListener('input', (e) => {
            this.filterOptions(e.target.value);
        });

        this.searchInput.addEventListener('keydown', (e) => {
            const visibleItems = this.items.filter(i => i.visible && !i.optionEl.disabled);
            if (e.key === 'ArrowDown') {
                e.preventDefault();
                const nextIdx = this.highlightedIndex < visibleItems.length - 1 ? this.highlightedIndex + 1 : 0;
                this.setHighlighted(nextIdx);
            } else if (e.key === 'ArrowUp') {
                e.preventDefault();
                const prevIdx = this.highlightedIndex > 0 ? this.highlightedIndex - 1 : visibleItems.length - 1;
                this.setHighlighted(prevIdx);
            } else if (e.key === 'Enter') {
                e.preventDefault();
                if (this.highlightedIndex >= 0 && this.highlightedIndex < visibleItems.length) {
                    this.selectValue(visibleItems[this.highlightedIndex].value);
                    this.close();
                    this.trigger.focus();
                }
            } else if (e.key === 'Escape') {
                e.preventDefault();
                this.close();
                this.trigger.focus();
            } else if (e.key === 'Tab') {
                this.close();
            }
        });

        this.select.addEventListener('change', () => {
            this.updateTriggerDisplay();
        });
    }

    sync() {
        this.buildOptions();
        this.updateTriggerDisplay();
    }
}

window.SearchableSelect = SearchableSelect;

window.initSearchableSelects = function(scope = document) {
    const targets = scope.querySelectorAll('select.searchable-select, #resume-target-role, #recruiter-sort-select, #interview-job-role, #interview-exp-level, #interview-difficulty, #filter-salary, #report-period, #report-type');
    targets.forEach(el => {
        if (!el.dataset.searchableSelectInit) {
            new SearchableSelect(el);
        }
    });
};

document.addEventListener('click', (e) => {
    if (!e.target.closest('.searchable-select-wrap')) {
        document.querySelectorAll('.searchable-select-wrap.is-open').forEach(el => {
            if (el.__searchableSelect) el.__searchableSelect.close();
        });
    }
});

document.addEventListener('DOMContentLoaded', () => {
    // Application state
    const state = {
        user: null,
        stats: null,
        currentInterviewSession: null,
        questions: [],
        currentQuestionIndex: 0,
        interviewAnswers: {},
        timerInterval: null,
        remainingSeconds: 60,
        activeRadarChart: null,
        speechRecognition: null,
        isRecording: false,
        theme: 'dark'
    };

    // Initialize Global Searchable Selects
    window.initSearchableSelects();

    // Initialize Web Speech API components
    initSpeechRecognition();

    // --- Routing Handler ---
    function router() {
        const hash = window.location.hash || '#';
        window.initSearchableSelects();

        // Hide all views
        document.querySelectorAll('.view-section').forEach(sec => sec.style.display = 'none');

        // Check if route is public
        const isPublicRoute = hash === '#login' || hash === '#register';

        // Full-bleed auth layout: hides the app chrome while signing in / signing up
        document.body.classList.toggle('auth-mode', isPublicRoute);

        // Redirect to login if user is unauthenticated and tries to access private routes
        if (!MeetAiAPI.isLoggedIn() && !isPublicRoute) {
            window.location.hash = '#login';
            return;
        }

        // Shell state is class-driven so CSS breakpoints stay in control of
        // the sidebar width and content offset (inline styles used to win here).
        document.body.classList.toggle('is-authed', MeetAiAPI.isLoggedIn());
        closeSidebarDrawer();

        // Render matching view
        if (hash === '#' || hash === '#features' || hash === '#pricing') {
            document.getElementById('landing-view').style.display = 'block';
            updateActiveNavItem('landing-view');
        } else if (hash === '#login' || hash === '#register') {
            // Split-screen auth layout relies on a grid container
            document.getElementById('login-view').style.display = 'grid';
            if (typeof window.switchAuthTab === 'function') {
                window.switchAuthTab(hash === '#register' ? 'register' : 'login');
            }
            resetLoginFormState();
        } else if (hash === '#dashboard') {
            document.getElementById('dashboard-view').style.display = 'block';
            updateActiveNavItem('dashboard-view');
            loadDashboard();
        } else if (hash === '#bulk-scan') {
            document.getElementById('bulk-scan-view').style.display = 'block';
            updateActiveNavItem('bulk-scan-view');
            loadBulkDashboard();
        } else if (hash === '#resume-analyzer') {
            document.getElementById('resume-view').style.display = 'block';
            updateActiveNavItem('resume-view');
            resetResumeAnalyzer();
        } else if (hash === '#mock-interview') {
            // Clean up any ongoing timers/recordings before loading setup
            cleanupInterviewSession();
            document.getElementById('interview-setup-view').style.display = 'block';
            updateActiveNavItem('interview-setup-view');
        } else if (hash.startsWith('#interview-console')) {
            document.getElementById('interview-active-view').style.display = 'block';
            updateActiveNavItem('interview-setup-view'); // keep active nav highlighted
        } else if (hash.startsWith('#report/')) {
            const reportId = hash.split('/')[1];
            document.getElementById('report-view').style.display = 'block';
            updateActiveNavItem('dashboard-view');
            loadPerformanceReport(reportId);
        } else if (hash === '#roadmap') {
            document.getElementById('roadmap-view').style.display = 'block';
            updateActiveNavItem('roadmap-view');
            loadRoadmap();
        } else if (hash === '#companies') {
            document.getElementById('company-view').style.display = 'block';
            updateActiveNavItem('company-view');
            loadCompanies();
        } else if (hash === '#resume-builder') {
            document.getElementById('builder-view').style.display = 'block';
            updateActiveNavItem('builder-view');
        } else if (hash === '#ats-optimizer') {
            document.getElementById('ats-optimizer-view').style.display = 'block';
            updateActiveNavItem('ats-optimizer-view');
            loadAtsOptimizer();
        } else if (hash === '#job-matcher') {
            document.getElementById('job-matcher-view').style.display = 'block';
            updateActiveNavItem('job-matcher-view');
            loadJobMatcher();
        } else if (hash === '#skills-analyzer') {
            document.getElementById('skills-analyzer-view').style.display = 'block';
            updateActiveNavItem('skills-analyzer-view');
            loadSkillsAnalyzer();
        } else if (hash === '#projects') {
            document.getElementById('projects-view').style.display = 'block';
            updateActiveNavItem('projects-view');
            loadProjectsPortfolio();
        } else if (hash === '#certificates') {
            document.getElementById('certificates-view').style.display = 'block';
            updateActiveNavItem('certificates-view');
            loadCertificatesManager();
        } else if (hash === '#applications') {
            document.getElementById('applications-view').style.display = 'block';
            updateActiveNavItem('applications-view');
            loadApplicationsTracker();
        } else if (hash === '#analytics') {
            document.getElementById('analytics-view').style.display = 'block';
            updateActiveNavItem('analytics-view');
            loadAnalyticsDashboard();
        } else if (hash === '#reports') {
            document.getElementById('reports-view').style.display = 'block';
            updateActiveNavItem('reports-view');
            loadReportsCenter();
        } else if (hash === '#settings') {
            document.getElementById('settings-view').style.display = 'block';
            updateActiveNavItem('settings-view');
            loadSettings();
        } else if (hash === '#admin') {
            document.getElementById('admin-view').style.display = 'block';
            updateActiveNavItem('admin-view');
            loadAdminPanel();
        }

        // Scroll to top
        window.scrollTo(0, 0);
    }

    window.addEventListener('hashchange', router);

    // --- Mobile navigation drawer ---
    function openSidebarDrawer() {
        document.body.classList.add('sidebar-open');
        const btn = document.getElementById('sidebar-toggle');
        if (btn) {
            btn.setAttribute('aria-expanded', 'true');
            btn.setAttribute('aria-label', 'Close navigation menu');
        }
    }

    function closeSidebarDrawer() {
        document.body.classList.remove('sidebar-open');
        const btn = document.getElementById('sidebar-toggle');
        if (btn) {
            btn.setAttribute('aria-expanded', 'false');
            btn.setAttribute('aria-label', 'Open navigation menu');
        }
    }

    const sidebarToggle = document.getElementById('sidebar-toggle');
    if (sidebarToggle) {
        sidebarToggle.addEventListener('click', () => {
            if (document.body.classList.contains('sidebar-open')) closeSidebarDrawer();
            else openSidebarDrawer();
        });
    }

    const sidebarBackdrop = document.getElementById('sidebar-backdrop');
    if (sidebarBackdrop) sidebarBackdrop.addEventListener('click', closeSidebarDrawer);

    // Close the drawer after picking a destination, and keep the label
    // reachable as a tooltip while the sidebar is collapsed to an icon rail.
    document.querySelectorAll('#sidebar-nav .nav-item a').forEach(link => {
        link.addEventListener('click', closeSidebarDrawer);
        const label = link.querySelector('span');
        if (label && !link.title) {
            link.title = label.textContent.trim();
            link.setAttribute('aria-label', label.textContent.trim());
        }
    });

    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && document.body.classList.contains('sidebar-open')) {
            closeSidebarDrawer();
            const btn = document.getElementById('sidebar-toggle');
            if (btn) btn.focus();
        }
    });

    // --- Top bar feature search (navigates the app; no fabricated results) ---
    const SEARCH_INDEX = [
        { label: 'Dashboard', hash: '#dashboard', icon: 'fa-chart-pie', keywords: 'home overview stats kpi summary' },
        { label: 'Resume Analyzer', hash: '#resume-analyzer', icon: 'fa-file-invoice', keywords: 'ats scan upload cv parse' },
        { label: 'Bulk Scan', hash: '#bulk-scan', icon: 'fa-users-gear', keywords: 'batch recruiter multiple candidates' },
        { label: 'Resume Builder', hash: '#resume-builder', icon: 'fa-file-pen', keywords: 'create cv template write' },
        { label: 'ATS Optimizer', hash: '#ats-optimizer', icon: 'fa-circle-check', keywords: 'keywords score improve match' },
        { label: 'Job Matcher', hash: '#job-matcher', icon: 'fa-briefcase', keywords: 'jobs roles openings vacancies' },
        { label: 'AI Career Roadmap', hash: '#roadmap', icon: 'fa-route', keywords: 'plan learning path goals' },
        { label: 'AI Mock Interview', hash: '#mock-interview', icon: 'fa-microphone', keywords: 'interview prep practice questions voice' },
        { label: 'Skills Analyzer', hash: '#skills-analyzer', icon: 'fa-brain', keywords: 'gaps strengths abilities' },
        { label: 'Projects', hash: '#projects', icon: 'fa-folder-open', keywords: 'portfolio work samples' },
        { label: 'Certificates', hash: '#certificates', icon: 'fa-award', keywords: 'courses credentials learning' },
        { label: 'Applications', hash: '#applications', icon: 'fa-list-check', keywords: 'tracker kanban applied status' },
        { label: 'Analytics', hash: '#analytics', icon: 'fa-chart-line', keywords: 'charts trends metrics' },
        { label: 'Reports', hash: '#reports', icon: 'fa-file-prescription', keywords: 'performance results export' },
        { label: 'Settings', hash: '#settings', icon: 'fa-gear', keywords: 'profile account preferences password' },
    ];

    const searchInput = document.getElementById('global-search');
    const searchResults = document.getElementById('global-search-results');

    function closeSearchResults() {
        if (!searchResults) return;
        searchResults.hidden = true;
        searchResults.innerHTML = '';
        if (searchInput) searchInput.setAttribute('aria-expanded', 'false');
    }

    function renderSearchResults(query) {
        if (!searchResults) return;
        const q = query.trim().toLowerCase();
        if (!q) return closeSearchResults();

        const matches = SEARCH_INDEX.filter(item =>
            item.label.toLowerCase().includes(q) || item.keywords.includes(q));

        searchResults.innerHTML = '';
        if (!matches.length) {
            const empty = document.createElement('div');
            empty.className = 'search-empty';
            empty.textContent = `No feature matches "${query.trim()}"`;
            searchResults.appendChild(empty);
        } else {
            matches.slice(0, 7).forEach(item => {
                const btn = document.createElement('button');
                btn.type = 'button';
                btn.setAttribute('role', 'option');
                const icon = document.createElement('i');
                icon.className = `fa-solid ${item.icon}`;
                const text = document.createElement('span');
                text.textContent = item.label;
                btn.append(icon, text);
                btn.addEventListener('click', () => {
                    window.location.hash = item.hash;
                    searchInput.value = '';
                    closeSearchResults();
                });
                searchResults.appendChild(btn);
            });
        }
        searchResults.hidden = false;
        searchInput.setAttribute('aria-expanded', 'true');
    }

    if (searchInput) {
        searchInput.addEventListener('input', () => renderSearchResults(searchInput.value));
        searchInput.addEventListener('focus', () => {
            if (searchInput.value.trim()) renderSearchResults(searchInput.value);
        });
        searchInput.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') { searchInput.value = ''; closeSearchResults(); }
            if (e.key === 'ArrowDown') {
                const first = searchResults && searchResults.querySelector('button');
                if (first) { e.preventDefault(); first.focus(); }
            }
            if (e.key === 'Enter') {
                const first = searchResults && searchResults.querySelector('button');
                if (first) { e.preventDefault(); first.click(); }
            }
        });
        document.addEventListener('click', (e) => {
            if (!e.target.closest('.top-search')) closeSearchResults();
        });
    }

    // Set active link in sidebar navigation
    function updateActiveNavItem(targetViewId) {
        document.querySelectorAll('.nav-links .nav-item').forEach(item => {
            if (item.getAttribute('data-target') === targetViewId) {
                item.classList.add('active');
            } else {
                item.classList.remove('active');
            }
        });
    }

    // --- Authentication Flow ---

    // Only the email address is remembered locally - credentials are never stored.
    const REMEMBERED_EMAIL_KEY = 'meetai_remembered_email';
    const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;

    // Inline, per-field validation messaging
    function setFieldError(inputId, message) {
        const input = document.getElementById(inputId);
        const errorEl = document.getElementById(`${inputId}-error`);
        if (!input || !errorEl) return;

        const field = input.closest('.auth-field');
        if (message) {
            errorEl.innerHTML = '';
            const icon = document.createElement('i');
            icon.className = 'fa-solid fa-circle-exclamation';
            const text = document.createElement('span');
            text.textContent = message;
            errorEl.append(icon, text);
            errorEl.hidden = false;
            input.setAttribute('aria-invalid', 'true');
            if (field) field.classList.add('has-error');
        } else {
            errorEl.textContent = '';
            errorEl.hidden = true;
            input.removeAttribute('aria-invalid');
            if (field) field.classList.remove('has-error');
        }
    }

    // Form-level alert (credential failures, server errors, success)
    function showLoginAlert(type, message) {
        const box = document.getElementById('login-alert');
        if (!box) return;

        if (!message) {
            box.hidden = true;
            box.textContent = '';
            box.className = 'auth-alert';
            return;
        }

        const icons = {
            error: 'fa-circle-exclamation',
            success: 'fa-circle-check',
            info: 'fa-circle-info'
        };
        box.className = `auth-alert is-${type}`;
        box.innerHTML = '';
        const icon = document.createElement('i');
        icon.className = `fa-solid ${icons[type] || icons.info}`;
        const text = document.createElement('span');
        text.textContent = message;
        box.append(icon, text);
        box.hidden = false;
    }

    function setLoginLoading(isLoading) {
        const btn = document.getElementById('login-submit-btn');
        if (!btn) return;

        const label = btn.querySelector('.auth-submit-label');
        btn.disabled = isLoading;
        btn.classList.toggle('is-loading', isLoading);
        btn.setAttribute('aria-busy', String(isLoading));
        if (label) label.textContent = isLoading ? 'Signing in...' : 'Sign In';

        ['login-email', 'login-password', 'login-remember'].forEach(id => {
            const el = document.getElementById(id);
            if (el) el.disabled = isLoading;
        });
    }

    // Called by the router each time the auth view is shown, so a stale
    // loading/error state never survives a logout -> login round trip.
    function resetLoginFormState() {
        const passwordInput = document.getElementById('login-password');
        if (!passwordInput) return;

        showLoginAlert(null, null);
        setFieldError('login-email', null);
        setFieldError('login-password', null);
        setLoginLoading(false);
        passwordInput.value = '';

        // Always re-mask the password field
        passwordInput.type = 'password';
        const toggle = document.getElementById('login-pw-toggle');
        if (toggle) {
            toggle.setAttribute('aria-pressed', 'false');
            toggle.setAttribute('aria-label', 'Show password');
            toggle.innerHTML = '<i class="fa-solid fa-eye" aria-hidden="true"></i>';
        }

        const capsHint = document.getElementById('login-caps-hint');
        if (capsHint) capsHint.hidden = true;
    }

    const loginForm = document.getElementById('login-form');
    if (loginForm) {
        const emailInput = document.getElementById('login-email');
        const passwordInput = document.getElementById('login-password');
        const rememberInput = document.getElementById('login-remember');
        const capsHint = document.getElementById('login-caps-hint');
        const pwToggle = document.getElementById('login-pw-toggle');
        const forgotLink = document.getElementById('forgot-pass-link');

        // Restore a previously remembered email address
        const rememberedEmail = localStorage.getItem(REMEMBERED_EMAIL_KEY);
        if (rememberedEmail) {
            emailInput.value = rememberedEmail;
            rememberInput.checked = true;
        }

        // Clear inline errors as soon as the user starts correcting them
        emailInput.addEventListener('input', () => setFieldError('login-email', null));
        passwordInput.addEventListener('input', () => setFieldError('login-password', null));

        // Show / hide password
        if (pwToggle) {
            pwToggle.addEventListener('click', () => {
                const isVisible = passwordInput.type === 'text';
                passwordInput.type = isVisible ? 'password' : 'text';
                pwToggle.setAttribute('aria-pressed', String(!isVisible));
                pwToggle.setAttribute('aria-label', isVisible ? 'Show password' : 'Hide password');
                pwToggle.innerHTML = `<i class="fa-solid ${isVisible ? 'fa-eye' : 'fa-eye-slash'}" aria-hidden="true"></i>`;
                passwordInput.focus();
            });
        }

        // Caps Lock warning
        if (capsHint) {
            ['keydown', 'keyup'].forEach(evt => {
                passwordInput.addEventListener(evt, (e) => {
                    if (typeof e.getModifierState !== 'function') return;
                    capsHint.hidden = !e.getModifierState('CapsLock');
                });
            });
            passwordInput.addEventListener('blur', () => { capsHint.hidden = true; });
        }

        // Forgot password -> existing /api/auth/forgot-password endpoint
        if (forgotLink) {
            forgotLink.addEventListener('click', async () => {
                const email = emailInput.value.trim();
                showLoginAlert(null, null);

                if (!email || !EMAIL_PATTERN.test(email)) {
                    setFieldError('login-email', 'Enter your email address first, then tap "Forgot password?".');
                    emailInput.focus();
                    return;
                }

                const originalLabel = forgotLink.textContent;
                forgotLink.disabled = true;
                forgotLink.textContent = 'Sending...';
                try {
                    const res = await MeetAiAPI.forgotPassword(email);
                    showLoginAlert('info', res.message || 'Password reset link sent (if that account exists).');
                } catch (err) {
                    showLoginAlert('error', err.message || 'Could not start the password reset. Please try again.');
                } finally {
                    forgotLink.disabled = false;
                    forgotLink.textContent = originalLabel;
                }
            });
        }

        loginForm.addEventListener('submit', async (e) => {
            e.preventDefault();

            const email = emailInput.value.trim();
            const password = passwordInput.value;
            const remember = rememberInput.checked;

            // Reset previous state
            showLoginAlert(null, null);
            setFieldError('login-email', null);
            setFieldError('login-password', null);

            // Client-side validation
            let firstInvalid = null;
            if (!email) {
                setFieldError('login-email', 'Email address is required.');
                firstInvalid = emailInput;
            } else if (!EMAIL_PATTERN.test(email)) {
                setFieldError('login-email', 'Enter a valid email address, e.g. name@domain.com');
                firstInvalid = emailInput;
            }
            if (!password) {
                setFieldError('login-password', 'Password is required.');
                firstInvalid = firstInvalid || passwordInput;
            }
            if (firstInvalid) {
                firstInvalid.focus();
                return;
            }

            setLoginLoading(true);
            try {
                const data = await MeetAiAPI.login(email, password);

                // Reuse the existing JWT mechanism; session-only unless "Remember me"
                MeetAiAPI.setToken(data.token, remember);
                if (remember) {
                    localStorage.setItem(REMEMBERED_EMAIL_KEY, email);
                } else {
                    localStorage.removeItem(REMEMBERED_EMAIL_KEY);
                }

                passwordInput.value = '';
                const name = (data.user && data.user.username) ? data.user.username : 'there';
                showLoginAlert('success', `Welcome back, ${name}! Taking you to your dashboard...`);

                // Every user - including admins - lands on the dashboard.
                // Admin tooling stays behind the server-side role check.
                setTimeout(() => { window.location.hash = '#dashboard'; }, 600);
            } catch (err) {
                setLoginLoading(false);
                const message = (err && err.message) ? err.message : '';

                if (/invalid credentials/i.test(message)) {
                    showLoginAlert('error', 'Incorrect email or password. Please try again.');
                    setFieldError('login-password', 'Double-check your password.');
                    passwordInput.focus();
                    passwordInput.select();
                } else if (/failed to fetch|networkerror|load failed|network request failed/i.test(message)) {
                    showLoginAlert('error', 'Cannot reach the server. Check your connection and try again.');
                } else if (/status: 5\d\d|internal server error/i.test(message)) {
                    showLoginAlert('error', 'Something went wrong on our end. Please try again in a moment.');
                } else {
                    showLoginAlert('error', message || 'Unable to sign in right now. Please try again.');
                }
            }
        });
    }

    // Theme toggle mirrored inside the auth panel (app chrome is hidden there)
    const authThemeBtn = document.getElementById('auth-theme-toggle');
    if (authThemeBtn) {
        authThemeBtn.addEventListener('click', () => {
            const mainToggle = document.getElementById('theme-toggle');
            if (mainToggle) mainToggle.click();
            const isLight = document.body.classList.contains('light-mode');
            authThemeBtn.innerHTML = `<i class="fa-solid ${isLight ? 'fa-sun' : 'fa-moon'}"></i>`;
        });
    }

    const registerForm = document.getElementById('register-form');
    if (registerForm) {
        registerForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const username = document.getElementById('reg-username').value;
            const email = document.getElementById('reg-email').value;
            const password = document.getElementById('reg-password').value;
            try {
                const data = await MeetAiAPI.register(username, email, password);
                MeetAiAPI.setToken(data.token);
                // Trigger OTP Verification
                state.unverifiedEmail = email;
                document.getElementById('otp-view-desc').innerText = `We simulated sending a verification OTP to ${email}. Submit the OTP to complete activation.`;
                document.getElementById('login-view').style.display = 'none';
                document.body.classList.remove('auth-mode');
                document.getElementById('otp-view').style.display = 'block';
            } catch (err) {
                alert(err.message);
            }
        });
    }

    const otpForm = document.getElementById('otp-form');
    if (otpForm) {
        otpForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const otp = document.getElementById('otp-code').value;
            try {
                await MeetAiAPI.verifyOTP(state.unverifiedEmail, otp);
                alert('Account activated!');
                window.location.hash = '#dashboard';
            } catch (err) {
                alert(err.message);
            }
        });
    }

    const logoutBtn = document.getElementById('logout-btn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', (e) => {
            e.preventDefault();
            MeetAiAPI.logout();
            cleanupInterviewSession();
            alert('Signed out successfully.');
            window.location.hash = '#';
            router();
        });
    }

    // --- Dashboard Loader ---
    async function loadDashboard() {
        try {
            const data = await MeetAiAPI.getStats();
            state.user = data.user;
            state.stats = data.stats;
 
            // Render profile header fields
            document.getElementById('sidebar-username').innerText = data.user.username;
            document.getElementById('sidebar-email').innerText = data.user.email;
            document.getElementById('dash-user-greet').innerText = data.user.username;
 
            if (data.user.profile_pic) {
                document.getElementById('sidebar-avatar').src = data.user.profile_pic;
            }

            // Top bar identity
            const topName = document.getElementById('top-user-name');
            if (topName) topName.innerText = data.user.username;
            const topAvatar = document.getElementById('top-user-avatar');
            if (topAvatar && data.user.profile_pic) topAvatar.src = data.user.profile_pic;

            // Animate Job Match counter based on actual matching jobs
            animateNumberCounter('counter-job-match', data.stats.jobs_found || 0, 1500);
 
            // Update Card Values Dynamically
            const resumeScore = data.stats.resume_score || 0;
            const atsScore = data.stats.ats_score || 0;
            const totalInterviews = data.stats.total_interviews || 0;
            const completedInterviews = data.stats.completed_interviews || 0;
            
            // Calculate dynamic interview readiness based on report or default
            let readinessScore = 70;
            if (data.latest_report) {
                readinessScore = data.latest_report.overall_score;
            } else if (completedInterviews > 0) {
                readinessScore = 75 + Math.min(completedInterviews * 5, 20);
            }
            
            // Skills count and missing skills count
            let skillsCount = 0;
            let weakSkillsCount = 0;
            if (data.latest_resume) {
                if (data.latest_resume.skills) {
                    skillsCount = data.latest_resume.skills.length;
                }
                if (data.latest_resume.analysis && data.latest_resume.analysis.missing_skills) {
                    weakSkillsCount = data.latest_resume.analysis.missing_skills.length;
                }
            }
 
            // Calculate career health score
            const healthScore = Math.round((resumeScore + atsScore + readinessScore) / 3) || 60;
            let healthLabel = "Excellent";
            if (healthScore < 50) healthLabel = "Critical";
            else if (healthScore < 70) healthLabel = "Average";
            else if (healthScore < 85) healthLabel = "Good";
 
            // Update UI elements if present
            const resumeScoreEl = document.getElementById('dash-resume-score');
            if (resumeScoreEl) resumeScoreEl.innerText = `${resumeScore}%`;
            
            const resumeScoreCircle = document.getElementById('dash-resume-score-circle');
            if (resumeScoreCircle) {
                resumeScoreCircle.setAttribute('stroke-dasharray', `${resumeScore}, 100`);
            }
 
            const atsScoreEl = document.getElementById('dash-ats-score');
            if (atsScoreEl) atsScoreEl.innerText = `${atsScore}%`;
 
            const readinessScoreEl = document.getElementById('dash-readiness-score');
            if (readinessScoreEl) readinessScoreEl.innerText = `${readinessScore}%`;
 
            const skillsCountEl = document.getElementById('dash-skills-count');
            if (skillsCountEl) skillsCountEl.innerText = skillsCount;
 
            const weakSkillsCountEl = document.getElementById('dash-weak-skills-count');
            if (weakSkillsCountEl) weakSkillsCountEl.innerText = weakSkillsCount;
 
            const healthScoreEl = document.getElementById('dash-health-score');
            if (healthScoreEl) healthScoreEl.innerText = `${healthScore}%`;
 
            const healthLabelEl = document.getElementById('dash-health-label');
            if (healthLabelEl) healthLabelEl.innerText = healthLabel;
 
            const healthGaugeFill = document.getElementById('dash-health-gauge-fill');
            if (healthGaugeFill) {
                // Circumference is 251.2. Offset = 251.2 * (1 - score/100)
                const offset = 251.2 * (1 - healthScore / 100);
                healthGaugeFill.setAttribute('stroke-dashoffset', offset);
            }
 
            const healthCoachEl = document.getElementById('dash-health-coach-text');
            if (healthCoachEl) {
                healthCoachEl.innerHTML = `<strong>AI Coach:</strong> "Your overall career readiness score is ${healthScore}%. You have verified ${skillsCount} core skills and identified ${weakSkillsCount} key focus areas to work on."`;
            }
 
            // Toggle admin role button if user is administrator
            const adminMenu = document.querySelector('.admin-only');
            if (data.user.role === 'admin') {
                if (adminMenu) adminMenu.style.display = 'block';
            } else {
                if (adminMenu) adminMenu.style.display = 'none';
            }
 
            // Career snapshot row (progress / activity / recommendations)
            renderCareerProgress(data);
            renderRecentActivity(data);
            renderRecommendations(data);

            // Initialize charts and dynamic components
            initializePremiumDashboardCharts(data);
            populateActivityHeatmap();
            triggerAIInsightsCoachTyping(data.user.username);

            // Notifications
            loadNotifications(data.notifications);

        } catch (err) {
            console.error("Dashboard failed to load:", err.message);
            showSnapshotError(err.message);
        }
    }

    // --- Career Snapshot renderers (all values come from /api/dashboard/stats) ---

    function setProgressRow(key, percent, label) {
        const pct = Math.max(0, Math.min(100, Math.round(percent || 0)));
        const bar = document.getElementById(`prog-${key}-bar`);
        const val = document.getElementById(`prog-${key}-val`);
        const track = document.getElementById(`prog-${key}-track`);
        if (bar) bar.style.width = `${pct}%`;
        if (val) val.textContent = label || `${pct}%`;
        if (track) track.setAttribute('aria-valuenow', String(pct));
    }

    function renderCareerProgress(data) {
        const stats = data.stats || {};

        // Resume readiness — latest analysed resume score
        setProgressRow('resume', stats.resume_score || 0,
            stats.has_resume ? `${stats.resume_score || 0}%` : 'No resume yet');

        // Interview readiness — latest report, else derived from completed sessions
        let readiness = 0;
        if (data.latest_report) readiness = data.latest_report.overall_score || 0;
        else if (stats.completed_interviews > 0) readiness = Math.min(75 + stats.completed_interviews * 5, 95);
        setProgressRow('interview', readiness,
            stats.has_report || stats.completed_interviews > 0 ? `${Math.round(readiness)}%` : 'Not started');

        // Skill progress — average of the parsed resume section scores
        const sections = Array.isArray(stats.section_scores) ? stats.section_scores : [];
        const skillPct = sections.length
            ? sections.reduce((a, b) => a + (b || 0), 0) / sections.length : 0;
        setProgressRow('skills', skillPct, stats.has_resume ? `${Math.round(skillPct)}%` : 'No data');

        // Career roadmap — resume completeness drives the roadmap checklist
        const roadmapPct = Array.isArray(stats.completeness) ? stats.completeness[0] : 0;
        setProgressRow('roadmap', roadmapPct, `${Math.round(roadmapPct || 0)}%`);
    }

    function timeAgo(isoString) {
        if (!isoString) return '';
        const then = new Date(isoString);
        if (isNaN(then)) return '';
        const mins = Math.floor((Date.now() - then.getTime()) / 60000);
        if (mins < 1) return 'Just now';
        if (mins < 60) return `${mins} min${mins === 1 ? '' : 's'} ago`;
        const hrs = Math.floor(mins / 60);
        if (hrs < 24) return `${hrs} hour${hrs === 1 ? '' : 's'} ago`;
        const days = Math.floor(hrs / 24);
        if (days === 1) return 'Yesterday';
        if (days < 30) return `${days} days ago`;
        return then.toLocaleDateString();
    }

    function buildTimelineItem({ marker, time, title, desc }) {
        const item = document.createElement('div');
        item.className = 'timeline-event-item';

        const dot = document.createElement('div');
        dot.className = `timeline-marker ${marker}`;

        const content = document.createElement('div');
        content.className = 'timeline-event-content';

        const timeEl = document.createElement('div');
        timeEl.className = 'event-time-text';
        timeEl.textContent = time;

        const titleEl = document.createElement('div');
        titleEl.className = 'event-title-text';
        titleEl.textContent = title;

        content.append(timeEl, titleEl);

        if (desc) {
            const descEl = document.createElement('p');
            descEl.className = 'event-desc-text';
            descEl.textContent = desc;
            content.appendChild(descEl);
        }

        item.append(dot, content);
        return item;
    }

    function renderRecentActivity(data) {
        const box = document.getElementById('dash-activity-list');
        if (!box) return;

        const events = [];

        if (data.latest_resume) {
            events.push({
                at: data.latest_resume.created_at,
                marker: 'marker-blue',
                title: 'Resume analyzed',
                desc: `${data.latest_resume.filename || 'Resume'} — ATS ${data.latest_resume.ats_score || 0}%`
            });
        }

        (data.recent_reports || []).slice(0, 4).forEach(r => {
            events.push({
                at: r.created_at,
                marker: 'marker-green',
                title: 'Mock interview completed',
                desc: `Overall score ${r.overall_score || 0}%`
            });
        });

        (data.notifications || []).slice(0, 4).forEach(n => {
            events.push({
                at: n.created_at,
                marker: 'marker-purple',
                title: 'Notification',
                desc: n.message
            });
        });

        events.sort((a, b) => new Date(b.at || 0) - new Date(a.at || 0));

        box.innerHTML = '';
        if (!events.length) {
            const empty = document.createElement('p');
            empty.className = 'snapshot-note';
            empty.textContent = 'No activity yet. Analyze a resume or run a mock interview to start your history.';
            box.appendChild(empty);
            return;
        }

        events.slice(0, 6).forEach(e => box.appendChild(buildTimelineItem({
            marker: e.marker,
            time: timeAgo(e.at),
            title: e.title,
            desc: e.desc
        })));
    }

    function renderRecommendations(data) {
        const box = document.getElementById('dash-reco-list');
        if (!box) return;

        const stats = data.stats || {};
        const recos = [];

        if (!stats.has_resume) {
            recos.push({ icon: 'fa-file-arrow-up', title: 'Upload your first resume', sub: 'Unlocks ATS scoring and skill analysis', hash: '#resume-analyzer', cta: 'Upload' });
        } else if ((stats.ats_score || 0) < 75) {
            recos.push({ icon: 'fa-circle-check', title: 'Improve your ATS score', sub: `Currently ${stats.ats_score || 0}% — aim for 75%+`, hash: '#ats-optimizer', cta: 'Optimize' });
        }

        if (!stats.completed_interviews) {
            recos.push({ icon: 'fa-microphone', title: 'Practice a mock interview', sub: 'Build interview readiness with AI feedback', hash: '#mock-interview', cta: 'Start' });
        }

        const roadmapPct = Array.isArray(stats.completeness) ? stats.completeness[0] : 0;
        if (roadmapPct < 100) {
            recos.push({ icon: 'fa-route', title: 'Complete your career roadmap', sub: `${Math.round(roadmapPct || 0)}% complete`, hash: '#roadmap', cta: 'Continue' });
        }

        if (stats.has_resume && (stats.jobs_found || 0) === 0) {
            recos.push({ icon: 'fa-briefcase', title: 'Find matching roles', sub: 'No job matches from your current skills yet', hash: '#job-matcher', cta: 'Match' });
        }

        box.innerHTML = '';
        if (!recos.length) {
            const done = document.createElement('p');
            done.className = 'snapshot-note';
            done.textContent = 'You are on track — nothing needs attention right now.';
            box.appendChild(done);
            return;
        }

        recos.slice(0, 4).forEach(r => {
            const row = document.createElement('div');
            row.className = 'reco-item';

            const icon = document.createElement('span');
            icon.className = 'reco-icon';
            icon.innerHTML = `<i class="fa-solid ${r.icon}" aria-hidden="true"></i>`;

            const body = document.createElement('div');
            body.className = 'reco-body';
            const t = document.createElement('div');
            t.className = 'reco-title';
            t.textContent = r.title;
            const s = document.createElement('div');
            s.className = 'reco-sub';
            s.textContent = r.sub;
            body.append(t, s);

            const cta = document.createElement('a');
            cta.className = 'reco-cta';
            cta.href = r.hash;
            cta.textContent = r.cta;

            row.append(icon, body, cta);
            box.appendChild(row);
        });
    }

    function showSnapshotError(message) {
        ['dash-activity-list', 'dash-reco-list'].forEach(id => {
            const box = document.getElementById(id);
            if (!box) return;
            box.innerHTML = '';
            const p = document.createElement('p');
            p.className = 'snapshot-note';
            p.textContent = `Could not load dashboard data. ${message || ''}`.trim();
            box.appendChild(p);
        });
        ['resume', 'interview', 'skills', 'roadmap'].forEach(k => setProgressRow(k, 0, '—'));
    }

    // --- Premium 2026 SaaS Dashboard Helper Functions ---
    
    function animateNumberCounter(id, targetValue, duration) {
        const el = document.getElementById(id);
        if (!el) return;
        let startValue = 0;
        const stepTime = Math.abs(Math.floor(duration / targetValue));
        const timer = setInterval(() => {
            startValue++;
            el.innerText = `${startValue} Jobs`;
            if (startValue >= targetValue) {
                clearInterval(timer);
                el.innerText = `${targetValue} Jobs`;
            }
        }, stepTime);
    }

    function triggerAIInsightsCoachTyping(username) {
        const holder = document.getElementById('ai-coach-text-holder');
        if (!holder) return;
        
        const originalText = `Great work ${username || 'Candidate'}! Your resume optimization rate has increased compared to the industry benchmark. Here is your targeted actionable checklist to cross the 95% threshold:`;
        holder.textContent = '';
        let index = 0;

        // Slice the source string each tick — appending to innerText swallows
        // the spaces, which is why the sentence used to render as one long word.
        function typeChar() {
            if (index < originalText.length) {
                index++;
                holder.textContent = originalText.slice(0, index);
                setTimeout(typeChar, 25);
            }
        }
        typeChar();
    }

    function populateActivityHeatmap() {
        const grid = document.getElementById('heatmap-contributions-grid');
        if (!grid) return;
        grid.innerHTML = '';
        
        for (let i = 0; i < 294; i++) {
            const cell = document.createElement('div');
            cell.className = 'heatmap-day-cell';
            
            let level = 0;
            const rand = Math.random();
            if (rand > 0.9) level = 4;
            else if (rand > 0.75) level = 3;
            else if (rand > 0.55) level = 2;
            else if (rand > 0.25) level = 1;
            
            cell.classList.add(`level-${level}`);
            
            const date = new Date();
            date.setDate(date.getDate() - (294 - i));
            cell.title = `Activity level: ${level} on ${date.toDateString()}`;
            grid.appendChild(cell);
        }
    }

    function initializePremiumDashboardCharts(data) {
        state.activeCharts = state.activeCharts || {};
        
        const stats = data.stats || {};
 
        // Sparkline 1: ATS
        const sparkAts = document.getElementById('sparkline-ats');
        if (sparkAts) {
            if (state.activeCharts.sparklineAts) state.activeCharts.sparklineAts.destroy();
            const atsTrend = stats.ats_trend || [60, 68, 75, 81, 88, 92];
            state.activeCharts.sparklineAts = new Chart(sparkAts, {
                type: 'line',
                data: {
                    labels: atsTrend.map((_, i) => i + 1),
                    datasets: [{
                        data: atsTrend,
                        borderColor: '#8B5CF6',
                        borderWidth: 2,
                        tension: 0.4,
                        pointRadius: 0,
                        fill: false
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: { x: { display: false }, y: { display: false } }
                }
            });
        }
 
        // Sparkline 2: Interview Readiness
        const sparkReady = document.getElementById('sparkline-readiness');
        if (sparkReady) {
            if (state.activeCharts.sparklineReady) state.activeCharts.sparklineReady.destroy();
            const readinessTrend = stats.readiness_trend || [50, 62, 68, 72, 76];
            state.activeCharts.sparklineReady = new Chart(sparkReady, {
                type: 'line',
                data: {
                    labels: readinessTrend.map((_, i) => i + 1),
                    datasets: [{
                        data: readinessTrend,
                        borderColor: '#00D084',
                        borderWidth: 2,
                        tension: 0.3,
                        pointRadius: 0,
                        fill: false
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: { x: { display: false }, y: { display: false } }
                }
            });
        }
 
        // Chart 1: Keyword Match
        const chartKw = document.getElementById('chart-keyword-match');
        if (chartKw) {
            if (state.activeCharts.keyword) state.activeCharts.keyword.destroy();
            const labels = stats.keyword_labels || ['React', 'Node.js', 'MongoDB', 'AWS', 'Docker'];
            const chartData = stats.keyword_data || [95, 82, 75, 55, 40];
            state.activeCharts.keyword = new Chart(chartKw, {
                type: 'bar',
                data: {
                    labels: labels,
                    datasets: [{
                        label: 'Match Percentage',
                        data: chartData,
                        backgroundColor: ['#4F7CFF', '#8B5CF6', '#00D084', '#FACC15', '#FF4D6D'],
                        borderRadius: 6
                    }]
                },
                options: {
                    indexAxis: 'y',
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: {
                        x: { grid: { color: 'rgba(255, 255, 255, 0.05)' }, ticks: { color: '#9CA3AF' }, max: 100 },
                        y: { grid: { display: false }, ticks: { color: '#9CA3AF' } }
                    }
                }
            });
        }
 
        // Chart 2: Resume Sections Score
        const chartSec = document.getElementById('chart-sections-score');
        if (chartSec) {
            if (state.activeCharts.sections) state.activeCharts.sections.destroy();
            const sectionScores = stats.section_scores || [90, 85, 95, 75, 80, 85, 70, 60];
            state.activeCharts.sections = new Chart(chartSec, {
                type: 'radar',
                data: {
                    labels: ['Experience', 'Projects', 'Skills', 'Summary', 'Achievements', 'Education', 'Certificates', 'Languages'],
                    datasets: [{
                        label: 'Scores',
                        data: sectionScores,
                        backgroundColor: 'rgba(139, 92, 246, 0.2)',
                        borderColor: '#8B5CF6',
                        pointBackgroundColor: '#4F7CFF'
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: {
                        r: {
                            angleLines: { color: 'rgba(255,255,255,0.08)' },
                            grid: { color: 'rgba(255,255,255,0.08)' },
                            pointLabels: { color: '#9CA3AF', font: { size: 10 } },
                            ticks: { display: false, max: 100, min: 0 }
                        }
                    }
                }
            });
        }
 
        // Chart 3: ATS & Interview Progress Trend
        const chartTrend = document.getElementById('chart-ats-trend');
        if (chartTrend) {
            if (state.activeCharts.trend) state.activeCharts.trend.destroy();
            const atsTrend = stats.ats_trend || [60, 65, 70, 75, 82, 88];
            const readinessTrend = stats.readiness_trend || [50, 58, 65, 70, 76, 80];
            state.activeCharts.trend = new Chart(chartTrend, {
                type: 'line',
                data: {
                    labels: atsTrend.map((_, i) => `Attempt ${i + 1}`),
                    datasets: [
                        {
                            label: 'ATS Resume Score',
                            data: atsTrend,
                            borderColor: '#8B5CF6',
                            backgroundColor: 'rgba(139, 92, 246, 0.1)',
                            fill: true,
                            tension: 0.4
                        },
                        {
                            label: 'Interview Readiness',
                            data: readinessTrend,
                            borderColor: '#00D084',
                            backgroundColor: 'rgba(0, 208, 132, 0.1)',
                            fill: true,
                            tension: 0.4
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: true, position: 'top', labels: { color: '#9CA3AF', usePointStyle: true, boxWidth: 8 } }
                    },
                    scales: {
                        x: { grid: { display: false }, ticks: { color: '#9CA3AF' } },
                        y: { grid: { color: 'rgba(255, 255, 255, 0.05)' }, ticks: { color: '#9CA3AF' }, min: 0, max: 100 }
                    }
                }
            });
        }
 
        // Chart 4: Resume Completeness
        const chartComp = document.getElementById('chart-completeness');
        if (chartComp) {
            if (state.activeCharts.completeness) state.activeCharts.completeness.destroy();
            const completeness = stats.completeness || [75, 25];
            state.activeCharts.completeness = new Chart(chartComp, {
                type: 'doughnut',
                data: {
                    labels: ['Completed', 'Missing'],
                    datasets: [{
                        data: completeness,
                        backgroundColor: ['#00D084', '#FF4D6D'],
                        borderWidth: 0
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { position: 'bottom', labels: { color: '#9CA3AF', boxWidth: 10 } } }
                }
            });
        }

        // Chart 5: AI Readability Index
        const chartRead = document.getElementById('chart-readability');
        if (chartRead) {
            if (state.activeCharts.readability) state.activeCharts.readability.destroy();
            state.activeCharts.readability = new Chart(chartRead, {
                type: 'doughnut',
                data: {
                    labels: ['Readability', 'Remaining'],
                    datasets: [{
                        data: [85, 15],
                        backgroundColor: ['#4F7CFF', 'rgba(255, 255, 255, 0.05)'],
                        borderWidth: 0
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    rotation: -90,
                    circumference: 180,
                    plugins: { legend: { display: false } }
                }
            });
        }

        // Chart 6: Grammar & Tone Audit
        const chartGram = document.getElementById('chart-grammar-analysis');
        if (chartGram) {
            if (state.activeCharts.grammar) state.activeCharts.grammar.destroy();
            state.activeCharts.grammar = new Chart(chartGram, {
                type: 'pie',
                data: {
                    labels: ['Grammar', 'Passive Voice', 'Weak Verbs', 'Buzzwords', 'Spelling'],
                    datasets: [{
                        data: [65, 12, 10, 8, 5],
                        backgroundColor: ['#4F7CFF', '#8B5CF6', '#FACC15', '#00D084', '#FF4D6D'],
                        borderWidth: 0
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { position: 'bottom', labels: { color: '#9CA3AF', boxWidth: 10 } } }
                }
            });
        }

        // Radar chart: Interview performance
        const chartIntRadar = document.getElementById('chart-interview-radar');
        if (chartIntRadar) {
            if (state.activeCharts.intRadar) state.activeCharts.intRadar.destroy();
            state.activeCharts.intRadar = new Chart(chartIntRadar, {
                type: 'radar',
                data: {
                    labels: ['Confidence', 'Tech Accuracy', 'Speed', 'Communication', 'Eye Contact'],
                    datasets: [{
                        label: 'Performance',
                        data: [82, 78, 85, 88, 72],
                        backgroundColor: 'rgba(79, 124, 255, 0.2)',
                        borderColor: '#4F7CFF',
                        pointBackgroundColor: '#8B5CF6'
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: {
                        r: {
                            angleLines: { color: 'rgba(255,255,255,0.08)' },
                            grid: { color: 'rgba(255,255,255,0.08)' },
                            pointLabels: { color: '#9CA3AF', font: { size: 9 } },
                            ticks: { display: false, max: 100, min: 0 }
                        }
                    }
                }
            });
        }

        // Area chart: Career Growth Projections
        const chartGrowth = document.getElementById('chart-career-growth-area');
        if (chartGrowth) {
            if (state.activeCharts.growth) state.activeCharts.growth.destroy();
            state.activeCharts.growth = new Chart(chartGrowth, {
                type: 'line',
                data: {
                    labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul'],
                    datasets: [
                        {
                            label: 'Skills Strengths',
                            data: [40, 50, 60, 75, 80, 88, 91],
                            borderColor: '#4F7CFF',
                            backgroundColor: 'rgba(79, 124, 255, 0.05)',
                            fill: true,
                            tension: 0.3
                        },
                        {
                            label: 'Resume Score',
                            data: [60, 68, 75, 81, 88, 92, 92],
                            borderColor: '#8B5CF6',
                            backgroundColor: 'rgba(139, 92, 246, 0.05)',
                            fill: true,
                            tension: 0.3
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: true, labels: { color: '#9CA3AF' } } },
                    scales: {
                        x: { grid: { display: false }, ticks: { color: '#9CA3AF' } },
                        y: { grid: { color: 'rgba(255, 255, 255, 0.05)' }, ticks: { color: '#9CA3AF' } }
                    }
                }
            });
        }
    }

    // Draggable Kanban drag-and-drop bindings
    window.allowDrop = function (ev) {
        ev.preventDefault();
    };

    window.drag = function (ev) {
        ev.dataTransfer.setData("text", ev.target.id);
    };

    window.drop = function (ev, columnId) {
        ev.preventDefault();
        const data = ev.dataTransfer.getData("text");
        const card = document.getElementById(data);
        if (!card) return;
        
        const column = document.getElementById(`col-${columnId}`);
        if (!column) return;
        const wrapper = column.querySelector('.kanban-cards-wrapper');
        if (wrapper) {
            wrapper.appendChild(card);
            recalculateKanbanCounts();
        }
    };

    function recalculateKanbanCounts() {
        document.querySelectorAll('.kanban-column').forEach(col => {
            const countBadge = col.querySelector('.column-count-badge');
            const cards = col.querySelectorAll('.kanban-card');
            if (countBadge) {
                countBadge.innerText = cards.length;
            }
        });
    }

    // Floating assistant logic
    window.toggleFloatingAssistant = function () {
        const chat = document.getElementById('floating-coach-chat');
        if (!chat) return;
        chat.style.display = chat.style.display === 'none' ? 'flex' : 'none';
    };

    window.handleChatKeyDown = function (ev) {
        if (ev.key === 'Enter') {
            sendFloatingChatMessage();
        }
    };

    window.sendFloatingChatMessage = function () {
        const input = document.getElementById('floating-chat-input');
        const log = document.getElementById('floating-chat-log');
        if (!input || !log || !input.value.trim()) return;
        
        const userText = input.value.trim();
        input.value = '';
        
        const userMsg = document.createElement('div');
        userMsg.className = 'chat-msg user-msg';
        userMsg.innerText = userText;
        log.appendChild(userMsg);
        
        log.scrollTop = log.scrollHeight;
        
        setTimeout(() => {
            const replyMsg = document.createElement('div');
            replyMsg.className = 'chat-msg coach-msg';
            
            let response = "That's a great question! For a Full Stack Developer profile, make sure to list projects detailing specific React state management strategies and Node scaling patterns.";
            const normText = userText.toLowerCase();
            if (normText.includes('docker') || normText.includes('container')) {
                response = "Docker is highly recommended! Mention container configurations, volume bindings, and multi-stage builds in your resume project summaries.";
            } else if (normText.includes('ats') || normText.includes('score') || normText.includes('optimize')) {
                response = "To optimize your ATS score, ensure you run the Resume Analyzer to extract target role keywords, then embed them in context under your job descriptions.";
            } else if (normText.includes('interview') || normText.includes('prep') || normText.includes('mock')) {
                response = "For the AI Mock Interview, sit in a quiet room, speak clearly into the microphone using industry terminologies, and try to state solutions using the STAR method.";
            } else if (normText.includes('hello') || normText.includes('hi')) {
                response = "Hello Meet! I'm your AI Resume Coach. How can I help optimize your profile today?";
            }
            
            replyMsg.innerText = response;
            log.appendChild(replyMsg);
            log.scrollTop = log.scrollHeight;
        }, 1000);
    };

    // Load Notifications Dropdown & update bell badge
    function loadNotifications(list) {
        const container = document.getElementById('notifications-list');
        const countBadge = document.getElementById('notification-count');

        if (!list || list.length === 0) {
            container.innerHTML = `<p style="font-size:12px; color:var(--text-muted); text-align:center;">No new updates.</p>`;
            countBadge.style.display = 'none';
            return;
        }

        countBadge.style.display = 'block';
        countBadge.innerText = list.length;

        container.innerHTML = list.map(item => `
            <div style="background:rgba(255,255,255,0.02); padding:10px; border-radius:8px; border-left:3px solid var(--color-primary);">
                <p style="font-size:13px; margin-bottom:4px;">${item.message}</p>
                <span style="font-size:10px; color:var(--text-muted);">${new Date(item.created_at).toLocaleString()}</span>
            </div>
        `).join('');
    }

    // Bell dropdown toggle
    const bellBtn = document.getElementById('notification-bell');
    const bellDropdown = document.getElementById('notification-dropdown');
    if (bellBtn && bellDropdown) {
        bellBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            bellDropdown.style.display = bellDropdown.style.display === 'none' ? 'block' : 'none';
        });
        document.addEventListener('click', () => {
            bellDropdown.style.display = 'none';
        });
        bellDropdown.addEventListener('click', (e) => e.stopPropagation());
    }

    const markReadBtn = document.getElementById('mark-read-btn');
    if (markReadBtn) {
        markReadBtn.addEventListener('click', async (e) => {
            e.preventDefault();
            try {
                await MeetAiAPI.markNotificationsRead();
                document.getElementById('notification-count').style.display = 'none';
                document.getElementById('notifications-list').innerHTML = `<p style="font-size:12px; color:var(--text-muted); text-align:center;">No new updates.</p>`;
            } catch (err) {
                console.error(err.message);
            }
        });
    }

    // --- Resume Analyzer Handler ---
    const dragDropZone = document.getElementById('drag-drop-zone');
    const resumeFileInput = document.getElementById('resume-file-input');
    const selectedFileDisplay = document.getElementById('selected-file-display');
    const resumeUploadForm = document.getElementById('resume-upload-form');
    let selectedResumeFile = null;

    function resetResumeAnalyzer() {
        selectedResumeFile = null;
        if (selectedFileDisplay) selectedFileDisplay.innerText = '';
        document.getElementById('analysis-results-box').style.display = 'none';
    }

    if (dragDropZone) {
        dragDropZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            dragDropZone.classList.add('dragover');
        });
        dragDropZone.addEventListener('dragleave', () => {
            dragDropZone.classList.remove('dragover');
        });
        dragDropZone.addEventListener('drop', (e) => {
            e.preventDefault();
            dragDropZone.classList.remove('dragover');
            if (e.dataTransfer.files.length > 0) {
                selectedResumeFile = e.dataTransfer.files[0];
                selectedFileDisplay.innerText = `Selected File: ${selectedResumeFile.name}`;
            }
        });
    }

    if (resumeFileInput) {
        resumeFileInput.addEventListener('change', (e) => {
            if (e.target.files.length > 0) {
                selectedResumeFile = e.target.files[0];
                selectedFileDisplay.innerText = `Selected File: ${selectedResumeFile.name}`;
            }
        });
    }

    if (resumeUploadForm) {
        resumeUploadForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            if (!selectedResumeFile) {
                alert('Please drop or select a resume file first.');
                return;
            }

            const role = document.getElementById('resume-target-role').value;
            const jdElem = document.getElementById('resume-target-jd');
            const jobDescription = jdElem ? jdElem.value.trim() : '';

            const formData = new FormData();
            formData.append('resume', selectedResumeFile);
            formData.append('job_role', role);
            if (jobDescription) {
                formData.append('job_description', jobDescription);
            }

            try {
                // Show loading placeholder
                const resultsBox = document.getElementById('analysis-results-box');
                resultsBox.style.display = 'block';
                resultsBox.innerHTML = `
                    <div class="loading-container" style="padding:40px; text-align:center;">
                        <span class="ai-loader"></span>
                        <p style="margin-top:15px; font-weight:600; font-size:16px;">Running Deterministic ATS & AI Analysis Pipeline...</p>
                        <p style="font-size:13px; color:var(--text-muted);">Extracting text, auditing section structure, measuring keyword density, and verifying skills against "${role}"...</p>
                    </div>
                `;

                const res = await MeetAiAPI.analyzeResume(formData);
                if (res.success && res.resume) {
                    renderResumeAnalysis(res.resume);
                } else if (res.resume) {
                    renderResumeAnalysis(res.resume);
                } else {
                    throw new Error(res.message || 'Analysis could not be completed.');
                }
            } catch (err) {
                alert(err.message || 'Error analyzing resume.');
                document.getElementById('analysis-results-box').style.display = 'none';
            }
        });
    }

    function renderResumeAnalysis(resume) {
        const container = document.getElementById('analysis-results-box');
        const analysis = resume.analysis || {};
        const breakdown = resume.score_breakdown || {};
        const candidateName = resume.name || 'Candidate';
        const candidateTitle = resume.title || `${resume.job_role || 'Software'} Professional`;

        // Lists
        const strengthsList = (analysis.strengths || []).map(s => `<li><i class="fa-solid fa-check" style="color:var(--color-success); margin-right:8px;"></i> ${s}</li>`).join('');
        const weaknessesList = (analysis.weaknesses || []).map(w => `<li><i class="fa-solid fa-triangle-exclamation" style="color:var(--color-danger); margin-right:8px;"></i> ${w}</li>`).join('');
        const suggestionsList = (analysis.suggestions || []).map(g => `<li><i class="fa-solid fa-lightbulb" style="color:var(--color-warning); margin-right:8px;"></i> ${g}</li>`).join('');
        const atsIssuesList = (analysis.ats_issues || []).map(iss => `<li><i class="fa-solid fa-circle-exclamation" style="color:var(--color-danger); margin-right:8px;"></i> ${iss}</li>`).join('');

        // Skills Badges
        const skills = resume.skills || [];
        const skillsBadges = skills.length > 0 
            ? skills.map(s => `<span class="badge badge-primary" style="font-size:12px; padding:6px 12px;">${s}</span>`).join('')
            : '<span style="color:var(--text-muted); font-size:13px;">No explicit technical skills extracted.</span>';

        const missingBadges = (analysis.missing_skills || []).map(s => `
            <span class="badge badge-danger" style="font-size:12px; padding:6px 12px;">${s}</span>
        `).join('');

        // Contact chips
        const contactChips = [];
        if (resume.email) contactChips.push(`<span><i class="fa-solid fa-envelope"></i> ${resume.email}</span>`);
        if (resume.phone) contactChips.push(`<span><i class="fa-solid fa-phone"></i> ${resume.phone}</span>`);
        if (resume.location) contactChips.push(`<span><i class="fa-solid fa-location-dot"></i> ${resume.location}</span>`);
        if (resume.linkedin) contactChips.push(`<a href="${resume.linkedin}" target="_blank" style="color:var(--color-primary);"><i class="fa-brands fa-linkedin"></i> LinkedIn</a>`);
        if (resume.github) contactChips.push(`<a href="${resume.github}" target="_blank" style="color:var(--color-primary);"><i class="fa-brands fa-github"></i> GitHub</a>`);
        if (resume.portfolio) contactChips.push(`<a href="${resume.portfolio}" target="_blank" style="color:var(--color-secondary);"><i class="fa-solid fa-globe"></i> Portfolio</a>`);

        // Experience timeline HTML
        const expItems = resume.experience || [];
        let experienceHtml = '';
        if (expItems.length > 0) {
            experienceHtml = `
                <div style="margin-top:25px; border-top:1px solid var(--border-color); padding-top:20px;">
                    <h4 style="margin-bottom:15px;"><i class="fa-solid fa-briefcase"></i> Extracted Work History (${expItems.length})</h4>
                    <div style="display:flex; flex-direction:column; gap:12px;">
                        ${expItems.map(exp => `
                            <div style="background:rgba(255,255,255,0.03); padding:15px; border-radius:8px; border-left:3px solid var(--color-primary);">
                                <div style="display:flex; justify-content:space-between; font-weight:600; font-size:14px;">
                                    <span>${exp.title_company || 'Position'}</span>
                                    <span style="color:var(--text-muted); font-size:12px;">${exp.dates || ''}</span>
                                </div>
                                ${exp.responsibilities && exp.responsibilities.length > 0 ? `
                                    <ul style="margin-top:8px; padding-left:18px; font-size:13px; color:var(--text-muted); display:flex; flex-direction:column; gap:4px;">
                                        ${exp.responsibilities.slice(0, 3).map(r => `<li>${r}</li>`).join('')}
                                    </ul>
                                ` : ''}
                            </div>
                        `).join('')}
                    </div>
                </div>
            `;
        }

        // Projects HTML
        const projItems = resume.projects || [];
        let projectsHtml = '';
        if (projItems.length > 0) {
            projectsHtml = `
                <div style="margin-top:25px; border-top:1px solid var(--border-color); padding-top:20px;">
                    <h4 style="margin-bottom:15px;"><i class="fa-solid fa-folder-open"></i> Extracted Project Portfolio (${projItems.length})</h4>
                    <div style="display:grid; grid-template-columns:1fr 1fr; gap:15px;">
                        ${projItems.map(p => `
                            <div style="background:rgba(255,255,255,0.03); padding:15px; border-radius:8px; border:1px solid var(--border-color);">
                                <div style="font-weight:600; font-size:14px; margin-bottom:5px;">
                                    ${p.link ? `<a href="${p.link}" target="_blank" style="color:var(--color-secondary);">${p.name} <i class="fa-solid fa-arrow-up-right-from-square" style="font-size:10px;"></i></a>` : p.name}
                                </div>
                                ${p.bullets && p.bullets.length > 0 ? `
                                    <p style="font-size:12px; color:var(--text-muted); line-height:1.4;">${p.bullets[0]}</p>
                                ` : ''}
                            </div>
                        `).join('')}
                    </div>
                </div>
            `;
        }

        // Job description match card if analyzed
        let jdMatchHtml = '';
        if (analysis.job_match) {
            const jm = analysis.job_match;
            jdMatchHtml = `
                <div style="margin-top:25px; background:rgba(79, 70, 229, 0.08); border:1px solid rgba(79, 70, 229, 0.25); border-radius:12px; padding:20px;">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
                        <h4 style="color:var(--color-primary); margin:0;"><i class="fa-solid fa-bullseye"></i> Job Description Alignment</h4>
                        <span style="font-size:24px; font-weight:800; color:var(--color-primary);">${jm.match_percentage}% Match</span>
                    </div>
                    <p style="font-size:13px; color:var(--text-muted); margin-bottom:12px;">Role Fit: <strong>${jm.role_match || 'Evaluated'}</strong> | Experience Fit: <strong>${jm.experience_match || 'Evaluated'}</strong></p>
                    ${jm.recommendations && jm.recommendations.length > 0 ? `<p style="font-size:13px; font-weight:500;">Recommendation: ${jm.recommendations[0]}</p>` : ''}
                </div>
            `;
        }

        container.innerHTML = `
            <!-- Candidate Profile Header -->
            <div style="display:flex; justify-content:space-between; align-items:flex-start; border-bottom:1px solid var(--border-color); padding-bottom:20px; margin-bottom:25px; flex-wrap:wrap; gap:15px;">
                <div>
                    <h2 style="margin:0 0 5px 0; font-size:24px;" id="parsed-candidate-name">${candidateName}</h2>
                    <div style="color:var(--color-secondary); font-weight:600; font-size:14px; margin-bottom:10px;">${candidateTitle}</div>
                    <div style="display:flex; flex-wrap:wrap; gap:15px; font-size:13px; color:var(--text-muted);">
                        ${contactChips.join(' • ') || '<span>No direct contact details found in header.</span>'}
                    </div>
                </div>
                <div style="text-align:right;">
                    <span class="badge badge-primary" style="font-size:12px; padding:6px 12px;">Pipeline v2 • Deterministic</span>
                </div>
            </div>
            
            <!-- Main Score Cards -->
            <div style="display:grid; grid-template-columns: repeat(4, 1fr); gap:15px; margin-bottom:30px;">
                <div style="background:rgba(255,255,255,0.02); padding:20px; border-radius:12px; text-align:center; border:1px solid rgba(79, 70, 229, 0.2);">
                    <div style="font-size:12px; color:var(--text-muted); margin-bottom:5px;">ATS Match Score</div>
                    <div style="font-size:36px; font-weight:800; color:var(--color-primary);">${resume.ats_score}%</div>
                    <div style="font-size:11px; color:var(--text-muted);">Recruiter Screen Pass</div>
                </div>
                <div style="background:rgba(255,255,255,0.02); padding:20px; border-radius:12px; text-align:center; border:1px solid rgba(6, 182, 212, 0.2);">
                    <div style="font-size:12px; color:var(--text-muted); margin-bottom:5px;">Overall Resume Score</div>
                    <div style="font-size:36px; font-weight:800; color:var(--color-secondary);">${resume.resume_score}/100</div>
                    <div style="font-size:11px; color:var(--text-muted);">Composite Quality</div>
                </div>
                <div style="background:rgba(255,255,255,0.02); padding:20px; border-radius:12px; text-align:center; border:1px solid rgba(16, 185, 129, 0.2);">
                    <div style="font-size:12px; color:var(--text-muted); margin-bottom:5px;">Verified Skills</div>
                    <div style="font-size:36px; font-weight:800; color:var(--color-success);">${skills.length}</div>
                    <div style="font-size:11px; color:var(--text-muted);">Identified in Content</div>
                </div>
                <div style="background:rgba(255,255,255,0.02); padding:20px; border-radius:12px; text-align:center; border:1px solid var(--border-color);">
                    <div style="font-size:12px; color:var(--text-muted); margin-bottom:5px;">Profile Completeness</div>
                    <div style="font-size:24px; font-weight:700; margin-top:8px;">
                        ${resume.email && resume.phone ? '<span style="color:var(--color-success);"><i class="fa-solid fa-circle-check"></i> Complete</span>' : '<span style="color:var(--color-warning);"><i class="fa-solid fa-circle-half-stroke"></i> Partial</span>'}
                    </div>
                </div>
            </div>

            <!-- Transparent Score Breakdown (100 pts) -->
            ${Object.keys(breakdown).length > 0 ? `
                <div style="background:rgba(255,255,255,0.02); border:1px solid var(--border-color); border-radius:12px; padding:20px; margin-bottom:30px;">
                    <h4 style="margin-bottom:15px; display:flex; justify-content:space-between;">
                        <span><i class="fa-solid fa-chart-simple"></i> Deterministic Score Breakdown</span>
                        <span style="font-size:13px; color:var(--text-muted); font-weight:normal;">Total: ${resume.resume_score} / 100</span>
                    </h4>
                    <div style="display:grid; grid-template-columns: repeat(3, 1fr); gap:12px; font-size:12px;">
                        <div>ATS Compatibility: <strong>${breakdown.ats_compatibility || 0}/20</strong></div>
                        <div>Skills Relevance: <strong>${breakdown.skills_relevance || 0}/20</strong></div>
                        <div>Work Experience: <strong>${breakdown.experience || 0}/15</strong></div>
                        <div>Education & Degrees: <strong>${breakdown.education || 0}/10</strong></div>
                        <div>Project Portfolio: <strong>${breakdown.projects || 0}/10</strong></div>
                        <div>Structure & Sections: <strong>${breakdown.structure || 0}/10</strong></div>
                        <div>Achievements/Certs: <strong>${breakdown.achievements || 0}/5</strong></div>
                        <div>Keyword Density: <strong>${breakdown.keywords || 0}/5</strong></div>
                        <div>Contact Details: <strong>${breakdown.profile_completeness || 0}/5</strong></div>
                    </div>
                </div>
            ` : ''}

            <!-- Extracted Skills Chips -->
            <div style="margin-bottom:30px;">
                <h4 style="margin-bottom:12px;"><i class="fa-solid fa-code"></i> Actual Extracted Skills (${skills.length})</h4>
                <div style="display:flex; flex-wrap:wrap; gap:8px;">
                    ${skillsBadges}
                </div>
            </div>

            ${jdMatchHtml}

            <!-- 2-Column AI & ATS Insights -->
            <div style="display:grid; grid-template-columns:1fr 1fr; gap:25px; margin-top:25px;">
                <div>
                    <h4 style="color:var(--color-success); margin-bottom:12px;"><i class="fa-solid fa-circle-check"></i> Core Strengths</h4>
                    <ul style="padding-left:0; list-style:none; line-height:1.6; display:flex; flex-direction:column; gap:8px;">
                        ${strengthsList || '<li>No specific strengths recorded.</li>'}
                    </ul>
                    
                    <h4 style="color:var(--color-danger); margin-top:25px; margin-bottom:12px;"><i class="fa-solid fa-triangle-exclamation"></i> Gaps & Weaknesses</h4>
                    <ul style="padding-left:0; list-style:none; line-height:1.6; display:flex; flex-direction:column; gap:8px;">
                        ${weaknessesList || '<li>No major gaps detected.</li>'}
                    </ul>
                </div>
                <div>
                    <h4 style="color:var(--color-warning); margin-bottom:12px;"><i class="fa-solid fa-bullseye"></i> Recommended Missing Skills</h4>
                    <div style="display:flex; flex-wrap:wrap; gap:8px; margin-bottom:25px;">
                        ${missingBadges || '<span class="badge badge-success">No critical skill gaps for target role!</span>'}
                    </div>

                    ${atsIssuesList ? `
                        <h4 style="color:var(--color-danger); margin-bottom:12px;"><i class="fa-solid fa-shield-halved"></i> ATS Formatting Alerts</h4>
                        <ul style="padding-left:0; list-style:none; line-height:1.6; display:flex; flex-direction:column; gap:8px; margin-bottom:25px;">
                            ${atsIssuesList}
                        </ul>
                    ` : ''}
                    
                    <h4 style="color:var(--text-main); margin-bottom:12px;"><i class="fa-solid fa-circle-info"></i> Actionable Improvement Tips</h4>
                    <ul style="padding-left:0; list-style:none; line-height:1.6; display:flex; flex-direction:column; gap:8px;">
                        ${suggestionsList || '<li>Maintain standard technical formatting.</li>'}
                    </ul>
                </div>
            </div>

            ${experienceHtml}
            ${projectsHtml}

            <!-- Analysis Inspection & Audit Details -->
            <div style="margin-top:35px; border-top:1px solid var(--border-color); padding-top:20px;">
                <details style="cursor:pointer;">
                    <summary style="font-weight:600; font-size:13px; color:var(--text-muted);"><i class="fa-solid fa-fingerprint"></i> Inspection & Verification Details (Click to Expand)</summary>
                    <div style="margin-top:15px; background:rgba(0,0,0,0.2); padding:15px; border-radius:8px; font-size:12px; font-family:monospace; color:var(--text-muted);">
                        <div><strong>File:</strong> ${resume.filename || 'N/A'}</div>
                        <div><strong>File SHA-256:</strong> ${resume.file_hash || 'Calculated'}</div>
                        <div><strong>Analysis Pipeline:</strong> ${resume.analysis_version || 'v2'} (Deterministic Scorer + Semantic AI)</div>
                        <div><strong>Analyzed At:</strong> ${resume.created_at || 'Just now'}</div>
                    </div>
                </details>
            </div>
        `;
    }

    // --- Speech Mock Interview Controller ---
    const setupForm = document.getElementById('interview-setup-form');
    if (setupForm) {
        setupForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const jobRole = document.getElementById('interview-job-role').value;
            const expLevel = document.getElementById('interview-exp-level').value;
            const difficulty = document.getElementById('interview-difficulty').value;

            const qTypes = [];
            document.querySelectorAll('input[name="q_types"]:checked').forEach(cb => {
                qTypes.push(cb.value);
            });

            if (qTypes.length === 0) {
                alert('Please select at least one question type (e.g. Technical).');
                return;
            }

            try {
                // Show loading block on active screen setup
                document.getElementById('interview-setup-view').style.display = 'none';
                document.getElementById('interview-active-view').style.display = 'block';
                document.getElementById('active-session-meta').innerText = `Generating interview questions...`;
                document.getElementById('active-question-text').innerHTML = `
                    <div style="display:flex; align-items:center; gap:15px;">
                        <span class="ai-loader" style="width:30px; height:30px; border-width:3px;"></span>
                        Preparing mock panel guidelines...
                    </div>
                `;

                const res = await MeetAiAPI.startInterview(jobRole, expLevel, difficulty, qTypes);

                state.currentInterviewSession = res.session_id;
                state.questions = res.questions;
                state.currentQuestionIndex = 0;
                state.interviewAnswers = {};

                window.location.hash = `#interview-console/${res.session_id}`;
                loadQuestionIndex(0);
            } catch (err) {
                alert(err.message);
                window.location.hash = '#mock-interview';
            }
        });
    }

    function loadQuestionIndex(index) {
        if (!state.questions || state.questions.length === 0 || index >= state.questions.length) {
            submitWholeInterview();
            return;
        }

        state.currentQuestionIndex = index;
        const q = state.questions[index];

        // Meta texts
        document.getElementById('active-session-meta').innerText = `Question ${index + 1} of ${state.questions.length}`;
        document.getElementById('active-question-concept').innerText = q.concept || 'General Competency';
        document.getElementById('active-question-text').innerText = q.question_text;
        document.getElementById('speech-transcript-box').value = '';

        // Setup Hints
        const hintBtn = document.getElementById('show-hint-btn');
        const hintBox = document.getElementById('hint-display-box');
        if (hintBox) hintBox.style.display = 'none';

        if (hintBtn) {
            hintBtn.onclick = () => {
                const hintText = document.getElementById('hint-text-content');
                if (hintText) hintText.innerText = q.hints || 'No hint available.';
                if (hintBox) hintBox.style.display = 'block';
            };
        }

        // Voice narration of question (Optional read feature)
        const speakBtn = document.getElementById('speak-question-btn');
        if (speakBtn) {
            speakBtn.onclick = () => speakQuestionText(q.question_text);
        }

        // Timer reset
        state.remainingSeconds = q.time_limit || 60;
        startTimer();
    }

    function startTimer() {
        clearInterval(state.timerInterval);
        updateTimerDisplay();

        state.timerInterval = setInterval(() => {
            state.remainingSeconds--;
            updateTimerDisplay();

            if (state.remainingSeconds <= 0) {
                clearInterval(state.timerInterval);
                // Trigger auto-submit on timeout
                submitAnsweringStep();
            }
        }, 1000);
    }

    function updateTimerDisplay() {
        const timerBox = document.getElementById('question-timer-display');
        const min = Math.floor(state.remainingSeconds / 60);
        const sec = state.remainingSeconds % 60;
        const timeStr = `${min.toString().padStart(2, '0')}:${sec.toString().padStart(2, '0')}`;

        if (timerBox) {
            timerBox.querySelector('span').innerText = timeStr;
            if (state.remainingSeconds <= 15) {
                timerBox.classList.add('warning');
            } else {
                timerBox.classList.remove('warning');
            }
        }
    }

    // Submit Answer & Continue to next question
    const submitAnswerBtn = document.getElementById('submit-answer-btn');
    if (submitAnswerBtn) {
        submitAnswerBtn.addEventListener('click', () => {
            submitAnsweringStep();
        });
    }

    async function submitAnsweringStep() {
        // Stop current speech recognition if running
        stopSpeechDictation();

        const q = state.questions[state.currentQuestionIndex];
        const answerVal = document.getElementById('speech-transcript-box').value.trim();

        // Lock button, show loading
        const originalBtnText = submitAnswerBtn.innerHTML;
        submitAnswerBtn.disabled = true;
        submitAnswerBtn.innerHTML = `<span class="ai-loader" style="width:16px; height:16px; border-width:2px; vertical-align:middle; margin-right:5px;"></span> Scoring...`;

        try {
            await MeetAiAPI.submitAnswer(q.id, answerVal);

            // Go to next question or compile report
            state.currentQuestionIndex++;
            submitAnswerBtn.disabled = false;
            submitAnswerBtn.innerHTML = originalBtnText;

            loadQuestionIndex(state.currentQuestionIndex);
        } catch (err) {
            alert(`Error saving answer: ${err.message}`);
            submitAnswerBtn.disabled = false;
            submitAnswerBtn.innerHTML = originalBtnText;
        }
    }

    async function submitWholeInterview() {
        cleanupInterviewSession();

        // Show loading screen in console
        const consoleLayout = document.getElementById('interview-active-view');
        consoleLayout.innerHTML = `
            <div class="loading-container" style="padding: 100px 0;">
                <span class="ai-loader"></span>
                <h2>Compiling Performance Metrics...</h2>
                <p style="color:var(--text-muted);">AI is evaluating grammar metrics, technical validity, confidence metrics, and formulating roadmaps.</p>
            </div>
        `;

        try {
            const data = await MeetAiAPI.submitInterview(state.currentInterviewSession);
            window.location.hash = `#report/${data.report.id}`;
            // Refresh view to pull dynamic elements
            router();
        } catch (err) {
            alert(`Report generation failed: ${err.message}`);
            window.location.hash = '#dashboard';
        }
    }

    function cleanupInterviewSession() {
        clearInterval(state.timerInterval);
        stopSpeechDictation();
        // Reset console layouts
        const activeConsole = document.getElementById('interview-active-view');
        if (activeConsole) {
            activeConsole.innerHTML = `
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:30px;">
                    <div>
                        <h2>Session Interview Console</h2>
                        <p style="color:var(--text-muted);" id="active-session-meta">Role: Software Engineer | Question 1 of 5</p>
                    </div>
                    <div class="timer-box" id="question-timer-display">
                        <i class="fa-regular fa-clock"></i> <span>00:60</span>
                    </div>
                </div>

                <div class="interview-console-grid">
                    <div>
                        <div class="glass-card" style="margin-bottom:25px;">
                            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:15px;">
                                <span class="badge badge-primary" id="active-question-concept">Core Algorithms</span>
                                <button class="btn-secondary" id="speak-question-btn" style="padding:6px 12px; font-size:12px;">
                                    <i class="fa-solid fa-volume-high"></i> Read Question
                                </button>
                            </div>
                            <h3 id="active-question-text" style="font-size:20px; line-height:1.6; min-height:80px;">What is the primary difference between a process and a thread?</h3>
                        </div>

                        <div class="glass-card">
                            <h4 style="margin-bottom:15px; display:flex; justify-content:space-between;">
                                <span>Voice Transcript</span>
                                <span style="font-size:12px; font-weight:normal; color:var(--text-muted);" id="dictation-status">Microphone Off</span>
                            </h4>
                            
                            <div class="audio-level-container">
                                <button class="theme-toggle-btn" style="color:var(--color-primary);" id="mic-trigger-btn">
                                    <i class="fa-solid fa-microphone"></i>
                                </button>
                                <div class="audio-bar">
                                    <div class="audio-bar-fill" id="mic-meter-fill"></div>
                                </div>
                            </div>

                            <textarea class="transcript-area" id="speech-transcript-box" placeholder="Your spoken answers will appear here in real-time. You can also edit the transcript directly if necessary..."></textarea>
                            
                            <div class="interview-actions">
                                <button class="btn-secondary" id="show-hint-btn">Show Hints</button>
                                <button class="btn-primary" id="submit-answer-btn">Submit & Continue <i class="fa-solid fa-chevron-right"></i></button>
                            </div>
                        </div>
                    </div>

                    <div style="display:flex; flex-direction:column; gap:25px;">
                        <div class="glass-card" style="flex:1;">
                            <h4 style="margin-bottom:15px;"><i class="fa-solid fa-triangle-exclamation" style="color:var(--color-warning);"></i> Guidelines</h4>
                            <ul style="padding-left:20px; font-size:13px; color:var(--text-muted); display:flex; flex-direction:column; gap:12px; line-height:1.5;">
                                <li><strong>Speak Clearly:</strong> Sit in a quiet room and speak directly into your microphone.</li>
                                <li><strong>Be Explicit:</strong> Mention industry standard terminology and system designs in your response.</li>
                                <li><strong>Time Constraints:</strong> Try to formulate and finish your answer within the specified limit.</li>
                                <li><strong>Manual Adjusts:</strong> If the dictation mismatches key words, you can clean up the transcript via keyboard.</li>
                            </ul>
                        </div>
                        
                        <div class="glass-card" id="hint-display-box" style="display:none;">
                            <h4 style="margin-bottom:10px; color:var(--color-secondary);"><i class="fa-solid fa-lightbulb"></i> Answer Hint</h4>
                            <p id="hint-text-content" style="font-size:14px; line-height:1.6; color:var(--text-muted);"></p>
                        </div>
                    </div>
                </div>
            `;

            // Re-bind listeners for the reconstructed DOM elements
            const btn = document.getElementById('submit-answer-btn');
            if (btn) btn.addEventListener('click', submitAnsweringStep);

            const micBtn = document.getElementById('mic-trigger-btn');
            if (micBtn) micBtn.addEventListener('click', toggleSpeechDictation);
        }
    }

    // --- Web Speech API integrations ---
    function initSpeechRecognition() {
        if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
            const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
            state.speechRecognition = new SpeechRec();
            state.speechRecognition.continuous = true;
            state.speechRecognition.interimResults = true;
            state.speechRecognition.lang = 'en-US';

            state.speechRecognition.onstart = () => {
                state.isRecording = true;
                updateMicUI(true);
            };

            state.speechRecognition.onerror = (e) => {
                console.error("Speech Recognition Error:", e);
                state.isRecording = false;
                updateMicUI(false);
            };

            state.speechRecognition.onend = () => {
                state.isRecording = false;
                updateMicUI(false);
            };

            state.speechRecognition.onresult = (e) => {
                let finalTranscript = '';
                for (let i = e.resultIndex; i < e.results.length; ++i) {
                    if (e.results[i].isFinal) {
                        finalTranscript += e.results[i][0].transcript;
                    }
                }
                if (finalTranscript) {
                    const txtBox = document.getElementById('speech-transcript-box');
                    if (txtBox) {
                        // Append text or fill
                        txtBox.value = (txtBox.value + ' ' + finalTranscript).trim();
                    }
                }
            };
        } else {
            console.warn("Speech recognition is not natively supported in this browser.");
        }
    }

    function toggleSpeechDictation() {
        if (!state.speechRecognition) {
            alert("Speech Recognition API is not supported in this browser. Please use Chrome/Edge or input answers manually via keyboard.");
            return;
        }

        if (state.isRecording) {
            stopSpeechDictation();
        } else {
            startSpeechDictation();
        }
    }

    function startSpeechDictation() {
        if (state.speechRecognition && !state.isRecording) {
            try {
                state.speechRecognition.start();
            } catch (err) {
                console.error(err);
            }
        }
    }

    function stopSpeechDictation() {
        if (state.speechRecognition && state.isRecording) {
            try {
                state.speechRecognition.stop();
            } catch (err) {
                console.error(err);
            }
        }
    }

    function updateMicUI(active) {
        const micBtn = document.getElementById('mic-trigger-btn');
        const status = document.getElementById('dictation-status');
        const meter = document.getElementById('mic-meter-fill');

        if (active) {
            if (micBtn) {
                micBtn.style.background = 'rgba(239, 68, 68, 0.15)';
                micBtn.style.borderColor = 'var(--color-danger)';
                micBtn.innerHTML = `<i class="fa-solid fa-microphone-slash" style="color:var(--color-danger)"></i>`;
            }
            if (status) status.innerText = 'Listening... Speak now.';

            // Animate meter bars
            state.meterInterval = setInterval(() => {
                if (meter) {
                    // Random noise simulation to visual level indicator
                    const val = Math.floor(Math.random() * 60) + 20;
                    meter.style.width = `${val}%`;
                }
            }, 150);

        } else {
            if (micBtn) {
                micBtn.style.background = 'var(--bg-surface)';
                micBtn.style.borderColor = 'var(--border-color)';
                micBtn.innerHTML = `<i class="fa-solid fa-microphone" style="color:var(--color-primary)"></i>`;
            }
            if (status) status.innerText = 'Microphone Off';
            clearInterval(state.meterInterval);
            if (meter) meter.style.width = '0%';
        }
    }

    // Text to speech narration of questions
    function speakQuestionText(text) {
        if ('speechSynthesis' in window) {
            window.speechSynthesis.cancel(); // stop any active reads
            const utterance = new SpeechSynthesisUtterance(text);
            utterance.rate = 1.0;
            utterance.pitch = 1.0;
            window.speechSynthesis.speak(utterance);
        } else {
            alert("Text-to-speech narration is not supported in this browser.");
        }
    }

    // Bind initial setup triggers
    const micBtn = document.getElementById('mic-trigger-btn');
    if (micBtn) micBtn.addEventListener('click', toggleSpeechDictation);


    // --- Performance Report Loader ---
    async function loadPerformanceReport(reportId) {
        try {
            const data = await MeetAiAPI.getReport(reportId);
            const report = data.report;

            // Fill meta information
            document.getElementById('report-meta').innerText = `Role: ${report.job_role} (${report.experience_level}) | Difficulty: ${report.difficulty}`;
            document.getElementById('perf-overall').innerText = `${report.overall_score}%`;
            document.getElementById('perf-speed').innerText = `${report.speaking_speed} wpm`;
            document.getElementById('perf-grammar').innerText = `${report.scores.grammar}%`;
            document.getElementById('perf-confidence').innerText = `${report.scores.confidence}%`;
            document.getElementById('perf-suggestions').innerText = report.suggestions;

            // Print report binder
            const printBtn = document.getElementById('report-print-btn');
            if (printBtn) {
                printBtn.onclick = () => {
                    window.open(`/api/reports/${report.id}/download?token=${MeetAiAPI.getToken()}`, '_blank');
                };
            }

            // Graded Questions Log
            const qContainer = document.getElementById('report-question-logs-container');
            qContainer.innerHTML = report.questions.map((q, idx) => `
                <div style="background:rgba(255,255,255,0.01); border:1px solid var(--border-color); padding:20px; border-radius:12px;">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
                        <span class="badge badge-primary">Q${idx + 1}: ${q.concept || 'Competency'}</span>
                        <span class="badge badge-success">Overall: ${q.scores.overall}%</span>
                    </div>
                    <h4 style="margin-bottom:15px; line-height:1.5;">${q.question_text}</h4>
                    <div style="font-size:13px; color:var(--text-muted); background:rgba(0,0,0,0.15); padding:12px; border-radius:8px; margin-bottom:15px;">
                        <strong>Your answer:</strong> "${q.user_answer || '(No answer provided)'}"
                    </div>
                    <div style="font-size:13px; line-height:1.5;">
                        <i class="fa-solid fa-circle-nodes" style="color:var(--color-secondary);"></i> <strong>AI Feedback:</strong> ${q.feedback_text}
                    </div>
                </div>
            `).join('');

            // Chart.js Radar Render
            renderRadarChart(report.scores);

        } catch (err) {
            alert(`Error pulling performance report: ${err.message}`);
            window.location.hash = '#dashboard';
        }
    }

    function renderRadarChart(scores) {
        const ctx = document.getElementById('scoresRadarChart');
        if (!ctx) return;

        if (state.activeRadarChart) {
            state.activeRadarChart.destroy();
        }

        const data = {
            labels: ['Technical', 'Communication', 'Confidence', 'Grammar', 'Vocabulary', 'Fluency'],
            datasets: [{
                label: 'Grade Assessment',
                data: [
                    scores.technical,
                    scores.communication,
                    scores.confidence,
                    scores.grammar,
                    scores.vocabulary,
                    scores.fluency
                ],
                fill: true,
                backgroundColor: 'rgba(79, 70, 229, 0.2)',
                borderColor: 'var(--color-primary)',
                pointBackgroundColor: 'var(--color-secondary)',
                pointBorderColor: '#FFF',
                pointHoverBackgroundColor: '#FFF',
                pointHoverBorderColor: 'var(--color-primary)'
            }]
        };

        const config = {
            type: 'radar',
            data: data,
            options: {
                responsive: true,
                scales: {
                    r: {
                        angleLines: { color: 'rgba(255,255,255,0.08)' },
                        grid: { color: 'rgba(255,255,255,0.08)' },
                        pointLabels: { color: 'var(--text-muted)', font: { size: 11 } },
                        ticks: { display: false, max: 100, min: 0 }
                    }
                },
                plugins: {
                    legend: { display: false }
                }
            }
        };

        state.activeRadarChart = new Chart(ctx, config);
    }


    // --- Career Roadmap ---
    async function loadRoadmap() {
        const missingSkillsBox = document.getElementById('roadmap-missing-skills-box');
        const coursesBox = document.getElementById('roadmap-courses-box');
        const booksBox = document.getElementById('roadmap-books-box');
        const timelineBox = document.getElementById('roadmap-timeline-box');

        try {
            const data = await MeetAiAPI.getStats();
            const report = data.latest_report;
            const resume = data.latest_resume;

            // Gather missing skills from latest scan or mock feedback
            let missing = [];
            if (resume && resume.analysis.missing_skills) {
                missing = resume.analysis.missing_skills;
            }
            if (report && report.roadmap && report.roadmap.missing_skills) {
                missing = Array.from(new Set([...missing, ...report.roadmap.missing_skills]));
            }

            if (missing.length > 0) {
                missingSkillsBox.innerHTML = missing.map(s => `<span class="badge badge-danger">${s}</span>`).join('');
            } else {
                missingSkillsBox.innerHTML = `<span class="badge badge-success">No gaps identified!</span>`;
            }

            // Recommendations Lists
            if (report && report.roadmap) {
                const rd = report.roadmap;
                coursesBox.innerHTML = (rd.courses || []).map(c => `<li>${c}</li>`).join('') || '<li>No immediate courses recommended.</li>';
                booksBox.innerHTML = (rd.books || []).map(b => `<li>${b}</li>`).join('') || '<li>No specific books recommended.</li>';

                // Timeline milestones
                timelineBox.innerHTML = (rd.timeline || []).map((t, idx) => `
                    <div style="display:flex; gap:15px; position:relative;">
                        <div style="display:flex; flex-direction:column; align-items:center;">
                            <div style="width:28px; height:28px; border-radius:50%; background:var(--color-secondary); color:white; display:flex; align-items:center; justify-content:center; font-size:12px; font-weight:bold; z-index:2;">${idx + 1}</div>
                            ${idx < rd.timeline.length - 1 ? '<div style="flex-grow:1; width:2px; background:var(--border-color); margin-top:5px; margin-bottom:5px;"></div>' : ''}
                        </div>
                        <div style="padding-bottom:15px;">
                            <h4 style="font-size:14px; margin-bottom:4px; color:var(--color-secondary);">${t.phase}</h4>
                            <p style="font-size:13px; color:var(--text-muted); line-height:1.4;">${t.focus}</p>
                        </div>
                    </div>
                `).join('');
            } else {
                coursesBox.innerHTML = '<li>Upload a resume or take an interview to view recommended courses.</li>';
                booksBox.innerHTML = '<li>Recommended literature will appear here.</li>';
                timelineBox.innerHTML = '<p style="color:var(--text-muted); font-size:13px;">Timeline milestones will be structured based on AI evaluations.</p>';
            }

        } catch (err) {
            console.error("Roadmap loading failed:", err.message);
        }
    }


    // --- Company Library ---
    async function loadCompanies() {
        const grid = document.getElementById('companies-cards-grid');
        try {
            const data = await MeetAiAPI.getCompanies();
            grid.innerHTML = data.companies.map(c => `
                <div class="glass-card" style="padding:20px; cursor:pointer; text-align:center;" onclick="loadCompanyPrepDetails('${c.name}')">
                    <div class="action-icon" style="margin: 0 auto 12px auto;"><i class="fa-solid fa-building"></i></div>
                    <h4 style="margin-bottom:8px;">${c.name}</h4>
                    <p style="font-size:11px; color:var(--text-muted); line-height:1.4;">${c.description}</p>
                </div>
            `).join('');
        } catch (err) {
            console.error(err.message);
        }
    }

    // Expose company prep loader globally to allow onclick templates trigger
    window.loadCompanyPrepDetails = async function (name) {
        const prepBox = document.getElementById('company-prep-details');
        try {
            const data = await MeetAiAPI.getCompanyPrep(name);
            const prep = data.prep;

            document.getElementById('current-company-name').innerText = data.company;
            document.getElementById('company-tips-list').innerHTML = (prep.tips || []).map(t => `<li>${t}</li>`).join('');
            document.getElementById('company-behavioral-list').innerHTML = (prep.behavioral || []).map(b => `<li>${b}</li>`).join('');

            document.getElementById('company-coding-list').innerHTML = (prep.coding || []).map(code => `
                <div style="background:rgba(255,255,255,0.01); border:1px solid var(--border-color); padding:12px; border-radius:8px;">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:5px;">
                        <span style="font-weight:600; font-size:13px;">${code.title}</span>
                        <span class="badge ${code.type === 'Hard' ? 'badge-danger' : 'badge-warning'}">${code.type}</span>
                    </div>
                    <p style="font-size:12px; color:var(--text-muted); line-height:1.4; margin:0;">${code.description}</p>
                </div>
            `).join('');

            prepBox.style.display = 'block';

            // Scroll down to prep details
            prepBox.scrollIntoView({ behavior: 'smooth' });

        } catch (err) {
            alert(`Error getting company details: ${err.message}`);
        }
    };


    // --- Resume Builder PDF Generation ---
    const builderForm = document.getElementById('builder-form');
    if (builderForm) {
        builderForm.addEventListener('submit', (e) => {
            e.preventDefault();
            const name = document.getElementById('build-name').value || 'Meet Vekariya';
            const email = document.getElementById('build-email').value || 'meet@example.com';
            const phone = document.getElementById('build-phone').value || '+91 98765 43210';
            const skills = document.getElementById('build-skills').value || 'React, Python, SQL';
            const exp = document.getElementById('build-experience').value || '';
            const edu = document.getElementById('build-education').value || '';

            // Generate clean print content
            const printWindow = window.open('', '_blank');
            printWindow.document.write(`
                <!DOCTYPE html>
                <html>
                <head>
                    <title>${name} - Professional Resume</title>
                    <style>
                        body { font-family: sans-serif; line-height: 1.5; color: #333; margin: 40px; }
                        h1 { color: #1e3a8a; border-bottom: 2px solid #1e3a8a; padding-bottom: 8px; margin-bottom: 5px; }
                        .contact { color: #666; font-size: 13px; margin-bottom: 25px; }
                        .section-title { font-size: 18px; color: #1e3a8a; border-bottom: 1px solid #ddd; padding-bottom: 4px; margin-top: 25px; margin-bottom: 10px; text-transform: uppercase; }
                        p, li { font-size: 14px; }
                        ul { padding-left: 20px; }
                    </style>
                </head>
                <body>
                    <h1>${name}</h1>
                    <div class="contact">Email: ${email} | Phone: ${phone}</div>
                    
                    <div class="section-title">Professional Skills</div>
                    <p>${skills}</p>
                    
                    <div class="section-title">Work Experience</div>
                    <p style="white-space: pre-wrap;">${exp || 'Fresher / Entry Level'}</p>
                    
                    <div class="section-title">Education</div>
                    <p style="white-space: pre-wrap;">${edu}</p>
                    
                    <script>
                        window.onload = function() {
                            window.print();
                        };
                    </script>
                </body>
                </html>
            `);
            printWindow.document.close();
        });
    }


    // --- Settings / Profile management ---
    async function loadSettings() {
        try {
            const data = await MeetAiAPI.getProfile();
            document.getElementById('settings-username').value = data.user.username;
            document.getElementById('settings-email').value = data.user.email;

            if (data.user.profile_pic) {
                document.getElementById('settings-avatar-preview').src = data.user.profile_pic;
            }
        } catch (err) {
            console.error(err.message);
        }
    }

    const settingsForm = document.getElementById('settings-profile-form');
    if (settingsForm) {
        settingsForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const username = document.getElementById('settings-username').value;
            const email = document.getElementById('settings-email').value;
            const password = document.getElementById('settings-password').value;

            const payload = { username, email };
            if (password) payload.password = password;

            try {
                await MeetAiAPI.updateProfile(payload);
                alert('Profile updated successfully!');
                loadDashboard();
            } catch (err) {
                alert(err.message);
            }
        });
    }

    const avatarInput = document.getElementById('avatar-file-input');
    if (avatarInput) {
        avatarInput.addEventListener('change', async (e) => {
            if (e.target.files.length > 0) {
                const file = e.target.files[0];
                const formData = new FormData();
                formData.append('profile_pic', file);

                try {
                    const data = await MeetAiAPI.uploadAvatar(formData);
                    document.getElementById('settings-avatar-preview').src = data.profile_pic;
                    document.getElementById('sidebar-avatar').src = data.profile_pic;
                    alert('Profile picture updated!');
                } catch (err) {
                    alert(err.message);
                }
            }
        });
    }

    // --- Admin panel logic ---
    async function loadAdminPanel() {
        const usersTable = document.getElementById('admin-users-table-body');
        const logBox = document.getElementById('admin-system-logs');

        try {
            // Get stats
            const res = await MeetAiAPI.request('/api/admin/dashboard', { method: 'GET' });

            document.getElementById('admin-users-count').innerText = res.stats.total_users;
            document.getElementById('admin-resumes-count').innerText = res.stats.total_resumes;
            document.getElementById('admin-sessions-count').innerText = res.stats.total_sessions;
            document.getElementById('admin-feedbacks-count').innerText = res.stats.total_feedbacks;

            // Render logs
            logBox.innerHTML = res.system_logs.map(log => `
                <div class="log-item ${log.level.toLowerCase()}">
                    [${log.timestamp}] ${log.level}: ${log.message}
                </div>
            `).join('');

            // Render users list
            const usersRes = await MeetAiAPI.request('/api/admin/users', { method: 'GET' });
            usersTable.innerHTML = usersRes.users.map(u => `
                <tr>
                    <td>${u.username}</td>
                    <td>${u.email}</td>
                    <td><span class="badge ${u.role === 'admin' ? 'badge-primary' : 'badge-success'}">${u.role}</span></td>
                    <td>${new Date(u.created_at).toLocaleDateString()}</td>
                    <td>
                        <button class="btn-secondary btn-sm" onclick="toggleAdminRole(${u.id})" style="padding: 4px 8px; font-size:11px;">Toggle Role</button>
                        <button class="btn-secondary btn-sm" onclick="deleteUserAccount(${u.id})" style="padding: 4px 8px; font-size:11px; border-color:var(--color-danger); color:var(--color-danger);">Delete</button>
                    </td>
                </tr>
            `).join('');

        } catch (err) {
            console.error("Admin screen load fail:", err.message);
        }
    }

    // Expose Admin Toggles globally for table row inputs
    window.toggleAdminRole = async function (userId) {
        try {
            const data = await MeetAiAPI.request(`/api/admin/users/${userId}`, { method: 'POST' });
            alert(data.message);
            loadAdminPanel();
        } catch (err) {
            alert(err.message);
        }
    };

    window.deleteUserAccount = async function (userId) {
        if (!confirm('Are you absolutely sure you want to delete this user profile? This action is irreversible.')) {
            return;
        }
        try {
            const data = await MeetAiAPI.request(`/api/admin/users/${userId}`, { method: 'DELETE' });
            alert(data.message);
            loadAdminPanel();
        } catch (err) {
            alert(err.message);
        }
    };


    // --- General theme toggler ---
    const themeBtn = document.getElementById('theme-toggle');
    if (themeBtn) {
        themeBtn.addEventListener('click', () => {
            const body = document.body;
            if (body.classList.contains('light-mode')) {
                body.classList.remove('light-mode');
                themeBtn.innerHTML = `<i class="fa-solid fa-moon"></i>`;
                state.theme = 'dark';
            } else {
                body.classList.add('light-mode');
                themeBtn.innerHTML = `<i class="fa-solid fa-sun"></i>`;
                state.theme = 'light';
            }
        });
    }

    // --- Premium 2026 AI Career Platform Modules Loaders ---

    // 1. ATS Optimizer
    async function loadAtsOptimizer() {
        try {
            const data = await MeetAiAPI.request('/api/ats', { method: 'GET' });
            state.atsData = data;

            document.getElementById('ats-opt-score').innerText = `${data.ats_score}%`;
            document.getElementById('ats-opt-health').innerText = data.resume_health;
            document.getElementById('ats-opt-format').innerText = `${data.formatting_score}%`;
            document.getElementById('ats-opt-readability').innerText = `${data.readability_score}%`;

            renderAtsKeywordsTable(data.missing_keywords);
            renderAtsSuggestions(data.suggestions);
            renderAtsCharts(data);
        } catch (err) {
            console.error("ATS Optimizer failed to load:", err.message);
        }
    }

    function renderAtsKeywordsTable(list) {
        const body = document.getElementById('ats-keywords-table-body');
        if (!body) return;
        body.innerHTML = list.map(item => `
            <tr>
                <td><strong>${item.keyword}</strong></td>
                <td><span class="badge ${item.importance === 'High' ? 'badge-primary' : 'badge-success'}">${item.importance}</span></td>
                <td>${item.category}</td>
            </tr>
        `).join('');
    }

    function renderAtsSuggestions(list) {
        const box = document.getElementById('ats-suggestions-box');
        if (!box) return;
        box.innerHTML = list.map(item => {
            let icon = 'fa-circle-info';
            let color = 'var(--text-muted)';
            if (item.type === 'error') { icon = 'fa-circle-xmark'; color = 'var(--color-danger)'; }
            else if (item.type === 'warning') { icon = 'fa-triangle-exclamation'; color = 'var(--color-warning)'; }
            return `
                <div class="glass-card" style="display:flex; align-items:center; gap:15px; padding:15px; border-left:4px solid ${color};">
                    <i class="fa-solid ${icon}" style="font-size:20px; color:${color};"></i>
                    <p style="margin:0; font-size:13px;">${item.text}</p>
                </div>
            `;
        }).join('');
    }

    window.filterAtsKeywords = function() {
        const searchVal = document.getElementById('ats-keyword-search').value.toLowerCase();
        if (!state.atsData) return;
        const filtered = state.atsData.missing_keywords.filter(item => 
            item.keyword.toLowerCase().includes(searchVal) || item.category.toLowerCase().includes(searchVal)
        );
        renderAtsKeywordsTable(filtered);
    };

    window.exportAtsReport = function() {
        alert("Preparing Premium PDF Report generation... Your download will begin in a moment.");
        window.print();
    };

    function renderAtsCharts(data) {
        state.activeCharts = state.activeCharts || {};

        // Gauge Chart
        const atsGauge = document.getElementById('chart-ats-gauge');
        if (atsGauge) {
            if (state.activeCharts.atsGauge) state.activeCharts.atsGauge.destroy();
            state.activeCharts.atsGauge = new Chart(atsGauge, {
                type: 'doughnut',
                data: {
                    labels: ['Score', 'Remaining'],
                    datasets: [{
                        data: [data.ats_score, 100 - data.ats_score],
                        backgroundColor: ['#4F7CFF', 'rgba(255,255,255,0.03)'],
                        borderWidth: 0
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    rotation: -90,
                    circumference: 180,
                    plugins: { legend: { display: false } }
                }
            });
        }

        // Radar Chart
        const atsRadar = document.getElementById('chart-ats-radar');
        if (atsRadar) {
            if (state.activeCharts.atsRadar) state.activeCharts.atsRadar.destroy();
            state.activeCharts.atsRadar = new Chart(atsRadar, {
                type: 'radar',
                data: {
                    labels: Object.keys(data.section_scores),
                    datasets: [{
                        label: 'Section Scores',
                        data: Object.values(data.section_scores),
                        backgroundColor: 'rgba(139, 92, 246, 0.2)',
                        borderColor: '#8B5CF6',
                        pointBackgroundColor: '#4F7CFF'
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: {
                        r: {
                            angleLines: { color: 'rgba(255,255,255,0.08)' },
                            grid: { color: 'rgba(255,255,255,0.08)' },
                            pointLabels: { color: '#9CA3AF', font: { size: 9 } },
                            ticks: { display: false, max: 100, min: 0 }
                        }
                    }
                }
            });
        }

        // Trend Chart
        const atsTrend = document.getElementById('chart-ats-trend-optimizer');
        if (atsTrend) {
            if (state.activeCharts.atsTrend) state.activeCharts.atsTrend.destroy();
            state.activeCharts.atsTrend = new Chart(atsTrend, {
                type: 'line',
                data: {
                    labels: data.ats_trend.map(t => t.upload),
                    datasets: [{
                        label: 'ATS History',
                        data: data.ats_trend.map(t => t.score),
                        borderColor: '#00D084',
                        backgroundColor: 'rgba(0, 208, 132, 0.1)',
                        fill: true,
                        tension: 0.4
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: {
                        x: { grid: { display: false }, ticks: { color: '#9CA3AF' } },
                        y: { grid: { color: 'rgba(255, 255, 255, 0.05)' }, ticks: { color: '#9CA3AF' } }
                    }
                }
            });
        }

        // Donut Chart
        const atsComp = document.getElementById('chart-ats-completeness-donut');
        if (atsComp) {
            if (state.activeCharts.atsComp) state.activeCharts.atsComp.destroy();
            state.activeCharts.atsComp = new Chart(atsComp, {
                type: 'doughnut',
                data: {
                    labels: data.completeness_data.map(c => c.section),
                    datasets: [{
                        data: data.completeness_data.map(c => c.score),
                        backgroundColor: ['#4F7CFF', '#8B5CF6', '#00D084', '#FACC15', '#FF4D6D', '#E2E8F0'],
                        borderWidth: 0
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } }
                }
            });
        }
    }

    // 2. Job Matcher
    async function loadJobMatcher() {
        try {
            const data = await MeetAiAPI.request('/api/jobs', { method: 'GET' });
            state.jobsData = data;

            document.getElementById('jobs-found-count').innerText = data.stats.jobs_found;
            document.getElementById('jobs-best-match').innerText = data.stats.best_match;
            document.getElementById('jobs-avg-salary').innerText = data.stats.avg_salary;
            document.getElementById('jobs-remote-count').innerText = data.stats.remote_jobs;

            renderJobsOpportunitiesList(data.jobs);
            renderJobsCharts(data.jobs);
        } catch (err) {
            console.error("Job Matcher load error:", err.message);
        }
    }

    function renderJobsOpportunitiesList(list) {
        const container = document.getElementById('job-opportunities-list');
        if (!container) return;
        if (list.length === 0) {
            container.innerHTML = `
                <div class="glass-card" style="text-align:center; padding:30px;">
                    <i class="fa-solid fa-briefcase" style="font-size:32px; color:var(--text-muted); margin-bottom:10px;"></i>
                    <p style="color:var(--text-muted);">No job opportunities matched your filters.</p>
                </div>
            `;
            return;
        }
        container.innerHTML = list.map(job => `
            <div class="glass-card job-match-card" style="display:flex; justify-content:space-between; align-items:center; gap:20px; padding:20px;">
                <div style="display:flex; gap:15px; align-items:center;">
                    <img src="${job.logo}" alt="${job.company}" style="width:50px; height:50px; border-radius:10px; background:rgba(255,255,255,0.05); padding:5px;">
                    <div>
                        <h4 style="margin:0 0 5px 0;">${job.role}</h4>
                        <div style="font-size:12px; color:var(--text-muted); display:flex; gap:12px;">
                            <span><i class="fa-solid fa-building"></i> ${job.company}</span>
                            <span><i class="fa-solid fa-location-dot"></i> ${job.location}</span>
                            <span><i class="fa-solid fa-money-bill-wave"></i> ${job.salary}</span>
                        </div>
                        <div style="margin-top:10px; display:flex; flex-wrap:wrap; gap:6px;">
                            ${job.skills.map(s => `<span class="badge" style="font-size:10px;">${s}</span>`).join('')}
                        </div>
                    </div>
                </div>
                <div style="text-align:right; min-width:120px;">
                    <div style="font-size:11px; color:var(--text-muted); margin-bottom:4px;">Match Rate</div>
                    <div style="font-size:22px; font-weight:800; color:var(--color-primary); margin-bottom:10px;">${job.match_score}%</div>
                    <button class="btn-primary btn-sm" onclick="applyJob(${job.id})" style="width:100%; justify-content:center;">Apply Now</button>
                </div>
            </div>
        `).join('');
    }

    window.filterJobs = function() {
        if (!state.jobsData) return;
        const loc = document.getElementById('filter-location').value.toLowerCase();
        const sal = parseInt(document.getElementById('filter-salary').value, 10);
        const exp = document.getElementById('filter-experience').value.toLowerCase();

        const filtered = state.jobsData.jobs.filter(job => {
            const matchLoc = job.location.toLowerCase().includes(loc) || job.type.toLowerCase().includes(loc);
            const salaryNumeric = parseInt(job.salary.replace(/[^0-9.]/g, ''), 10) || 0;
            const matchSal = sal === 0 || salaryNumeric >= sal;
            const matchExp = job.experience.toLowerCase().includes(exp) || exp === '';
            return matchLoc && matchSal && matchExp;
        });

        renderJobsOpportunitiesList(filtered);
    };

    window.applyJob = function(jobId) {
        alert(`Application initiated successfully for opportunity reference ID: #${jobId}. A confirmation email will follow.`);
    };

    function renderJobsCharts(jobs) {
        state.activeCharts = state.activeCharts || {};

        // Match Distribution (Bar)
        const distCanvas = document.getElementById('chart-job-match-dist');
        if (distCanvas) {
            if (state.activeCharts.jobDist) state.activeCharts.jobDist.destroy();
            const ranges = {'90%+': 0, '80-89%': 0, '70-79%': 0, '<70%': 0};
            jobs.forEach(j => {
                if (j.match_score >= 90) ranges['90%+']++;
                else if (j.match_score >= 80) ranges['80-89%']++;
                else if (j.match_score >= 70) ranges['70-79%']++;
                else ranges['<70%']++;
            });

            state.activeCharts.jobDist = new Chart(distCanvas, {
                type: 'bar',
                data: {
                    labels: Object.keys(ranges),
                    datasets: [{
                        data: Object.values(ranges),
                        backgroundColor: '#8B5CF6',
                        borderRadius: 5
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: {
                        x: { ticks: { color: '#9CA3AF' } },
                        y: { ticks: { color: '#9CA3AF' }, grid: { color: 'rgba(255,255,255,0.05)' } }
                    }
                }
            });
        }

        // Salary Range (Pie)
        const salCanvas = document.getElementById('chart-job-salary-range');
        if (salCanvas) {
            if (state.activeCharts.jobSalary) state.activeCharts.jobSalary.destroy();
            const categories = {'Low (<₹10L)': 0, 'Mid (₹10-20L)': 0, 'High (₹20L+)': 0};
            jobs.forEach(j => {
                const s = parseInt(j.salary.replace(/[^0-9.]/g, ''), 10) || 0;
                if (s >= 20) categories['High (₹20L+)']++;
                else if (s >= 10) categories['Mid (₹10-20L)']++;
                else categories['Low (<₹10L)']++;
            });

            state.activeCharts.jobSalary = new Chart(salCanvas, {
                type: 'pie',
                data: {
                    labels: Object.keys(categories),
                    datasets: [{
                        data: Object.values(categories),
                        backgroundColor: ['#00D084', '#FACC15', '#FF4D6D'],
                        borderWidth: 0
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { position: 'right', labels: { color: '#9CA3AF', boxWidth: 10 } } }
                }
            });
        }
    }

    // 3. AI Career Roadmap
    async function loadRoadmap() {
        try {
            const data = await MeetAiAPI.request('/api/roadmap', { method: 'GET' });
            state.roadmapData = data;

            document.getElementById('roadmap-target-role').innerText = data.target_role;
            document.getElementById('roadmap-progress-text').innerText = `${data.learning_progress}%`;

            const circle = document.getElementById('roadmap-progress-circle');
            if (circle) {
                const maxOffset = 213; 
                const offset = maxOffset - (maxOffset * data.learning_progress) / 100;
                circle.style.strokeDashoffset = offset;
            }

            renderRoadmapTimeline(data.timeline);
            renderRoadmapMilestones(data.milestones);
            renderRoadmapHeatmap();
        } catch (err) {
            console.error("Roadmap failed to load:", err.message);
        }
    }

    function renderRoadmapTimeline(list) {
        const lane = document.getElementById('roadmap-timeline-lane');
        if (!lane) return;
        lane.innerHTML = list.map(phase => {
            let className = '';
            if (phase.status === 'Completed') className = 'completed';
            else if (phase.status === 'In Progress') className = 'in-progress';
            return `
                <div class="roadmap-timeline-phase ${className}">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <h4 style="margin:0 0 5px 0;">${phase.phase}</h4>
                        <span class="badge" style="font-size:10px;">${phase.status}</span>
                    </div>
                    <p style="font-size:13px; color:var(--text-muted); margin:0 0 8px 0;">${phase.focus}</p>
                    <div class="progress-bar-bg" style="height:6px;">
                        <div class="progress-bar-fill" style="width:${phase.progress}%; background:var(--color-primary);"></div>
                    </div>
                </div>
            `;
        }).join('');
    }

    function renderRoadmapMilestones(list) {
        const container = document.getElementById('roadmap-milestones-list');
        if (!container) return;
        container.innerHTML = list.map((item, idx) => `
            <div style="display:flex; align-items:center; gap:12px; font-size:13px;">
                <input type="checkbox" id="milestone-${idx}" ${item.status === 'Completed' ? 'checked' : ''} onchange="toggleMilestone(${idx})">
                <label for="milestone-${idx}" style="cursor:pointer; text-decoration: ${item.status === 'Completed' ? 'line-through' : 'none'};">
                    <strong>${item.title}</strong> - <span style="color:var(--text-muted);">${item.desc}</span>
                </label>
            </div>
        `).join('');
    }

    window.toggleMilestone = function(idx) {
        if (!state.roadmapData) return;
        const milestone = state.roadmapData.milestones[idx];
        milestone.status = milestone.status === 'Completed' ? 'In Progress' : 'Completed';
        
        const total = state.roadmapData.milestones.length;
        const completed = state.roadmapData.milestones.filter(m => m.status === 'Completed').length;
        state.roadmapData.learning_progress = Math.round((completed / total) * 100);

        document.getElementById('roadmap-progress-text').innerText = `${state.roadmapData.learning_progress}%`;
        const circle = document.getElementById('roadmap-progress-circle');
        if (circle) {
            const maxOffset = 213;
            const offset = maxOffset - (maxOffset * state.roadmapData.learning_progress) / 100;
            circle.style.strokeDashoffset = offset;
        }

        renderRoadmapMilestones(state.roadmapData.milestones);
    };

    function renderRoadmapHeatmap() {
        const grid = document.getElementById('roadmap-heatmap-grid');
        if (!grid) return;
        grid.innerHTML = '';
        for (let i = 0; i < 140; i++) {
            const cell = document.createElement('div');
            cell.className = 'heatmap-day-cell';
            let level = 0;
            const rand = Math.random();
            if (rand > 0.85) level = 4;
            else if (rand > 0.7) level = 3;
            else if (rand > 0.5) level = 2;
            else if (rand > 0.2) level = 1;
            cell.classList.add(`level-${level}`);
            cell.style.width = '8px';
            cell.style.height = '8px';
            grid.appendChild(cell);
        }
    }

    // 4. Skills Analyzer
    async function loadSkillsAnalyzer() {
        try {
            const data = await MeetAiAPI.request('/api/skills', { method: 'GET' });
            state.skillsData = data;

            renderSkillsProgressList(data.technical.concat(data.soft.map(s => ({...s, category: 'Soft Skills'}))));
            renderSkillsAISection(data.feedback);
            renderSkillsCharts(data);
        } catch (err) {
            console.error("Skills Analyzer failed to load:", err.message);
        }
    }

    function renderSkillsProgressList(list) {
        const container = document.getElementById('skills-progress-list');
        if (!container) return;
        if (list.length === 0) {
            container.innerHTML = `<p style="color:var(--text-muted); text-align:center;">No matching skills found.</p>`;
            return;
        }
        container.innerHTML = list.map(skill => `
            <div>
                <div style="display:flex; justify-content:space-between; font-size:12px; margin-bottom:5px;">
                    <span><strong>${skill.name}</strong> <span style="font-size:10px; color:var(--text-muted); text-transform:uppercase;">[${skill.category}]</span></span>
                    <span>${skill.level}% Mastery</span>
                </div>
                <div class="progress-bar-bg" style="height:8px;">
                    <div class="progress-bar-fill" style="width:${skill.level}%; background:linear-gradient(90deg, var(--color-primary), var(--color-secondary));"></div>
                </div>
            </div>
        `).join('');
    }

    function renderSkillsAISection(feedback) {
        const strengths = document.getElementById('skills-ai-strengths');
        const gaps = document.getElementById('skills-ai-weaknesses');
        const courses = document.getElementById('skills-courses-list');

        if (strengths) {
            strengths.innerHTML = feedback.strengths.map(s => `<li>${s}</li>`).join('');
        }
        if (gaps) {
            gaps.innerHTML = feedback.weaknesses.map(w => `<li>${w}</li>`).join('');
        }
        if (courses) {
            courses.innerHTML = feedback.courses.map(c => `
                <div class="glass-card" style="padding:12px; font-size:13px; display:flex; justify-content:space-between; align-items:center;">
                    <div>
                        <strong>${c.title}</strong>
                        <div style="font-size:11px; color:var(--text-muted); margin-top:2px;">${c.platform} • ${c.duration}</div>
                    </div>
                    <button class="btn-secondary btn-sm" onclick="window.open('https://udemy.com','_blank')">Enroll</button>
                </div>
            `).join('');
        }
    }

    window.filterSkills = function() {
        if (!state.skillsData) return;
        const searchVal = document.getElementById('skills-search-input').value.toLowerCase();
        const allSkills = state.skillsData.technical.concat(state.skillsData.soft.map(s => ({...s, category: 'Soft Skills'})));
        const filtered = allSkills.filter(s => 
            s.name.toLowerCase().includes(searchVal) || s.category.toLowerCase().includes(searchVal)
        );
        renderSkillsProgressList(filtered);
    };

    function renderSkillsCharts(data) {
        state.activeCharts = state.activeCharts || {};

        // Skills Radar Chart
        const rCanvas = document.getElementById('chart-skills-radar');
        if (rCanvas) {
            if (state.activeCharts.skillsRadar) state.activeCharts.skillsRadar.destroy();
            const techSample = data.technical.slice(0, 5);
            state.activeCharts.skillsRadar = new Chart(rCanvas, {
                type: 'radar',
                data: {
                    labels: techSample.map(t => t.name),
                    datasets: [{
                        label: 'Proficiency',
                        data: techSample.map(t => t.level),
                        backgroundColor: 'rgba(79, 124, 255, 0.2)',
                        borderColor: '#4F7CFF',
                        pointBackgroundColor: '#8B5CF6'
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: {
                        r: {
                            angleLines: { color: 'rgba(255,255,255,0.08)' },
                            grid: { color: 'rgba(255,255,255,0.08)' },
                            pointLabels: { color: '#9CA3AF', font: { size: 9 } },
                            ticks: { display: false, max: 100, min: 0 }
                        }
                    }
                }
            });
        }

        // Skills Pie Chart
        const pCanvas = document.getElementById('chart-skills-pie');
        if (pCanvas) {
            if (state.activeCharts.skillsPie) state.activeCharts.skillsPie.destroy();
            const categories = {};
            data.technical.forEach(t => {
                categories[t.category] = (categories[t.category] || 0) + 1;
            });

            state.activeCharts.skillsPie = new Chart(pCanvas, {
                type: 'pie',
                data: {
                    labels: Object.keys(categories),
                    datasets: [{
                        data: Object.values(categories),
                        backgroundColor: ['#4F7CFF', '#8B5CF6', '#00D084', '#FACC15', '#FF4D6D'],
                        borderWidth: 0
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { position: 'right', labels: { color: '#9CA3AF', boxWidth: 10 } } }
                }
            });
        }
    }

    // 5. Projects Portfolio
    async function loadProjectsPortfolio() {
        try {
            const data = await MeetAiAPI.request('/api/projects', { method: 'GET' });
            state.projectsList = data.projects;

            renderProjectsGrid(data.projects);
            renderProjectsCharts(data.projects);
        } catch (err) {
            console.error("Projects portfolio load error:", err.message);
        }
    }

    function renderProjectsGrid(list) {
        const container = document.getElementById('projects-grid-list');
        if (!container) return;
        if (list.length === 0) {
            container.innerHTML = `<p style="color:var(--text-muted); text-align:center; grid-column:span 2;">No projects found.</p>`;
            return;
        }
        container.innerHTML = list.map(proj => `
            <div class="glass-card" style="padding:20px; display:flex; flex-direction:column; justify-content:space-between; gap:12px;">
                <div>
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <h4 style="margin:0;">${proj.name}</h4>
                        <span class="badge" style="background:rgba(0, 208, 132, 0.1); color:var(--color-success); font-size:10px;">AI Score: ${proj.ai_score}</span>
                    </div>
                    <div style="font-size:11px; color:var(--text-muted); margin-top:5px; text-transform:uppercase;">${proj.tech}</div>
                    <div style="margin-top:15px; display:flex; justify-content:space-between; font-size:12px;">
                        <span>Completion Rate</span>
                        <span>${proj.completion}%</span>
                    </div>
                    <div class="progress-bar-bg" style="height:6px; margin-top:5px;">
                        <div class="progress-bar-fill" style="width:${proj.completion}%; background:var(--color-primary);"></div>
                    </div>
                </div>
                <div style="display:flex; justify-content:space-between; gap:10px; margin-top:10px;">
                    <div style="display:flex; gap:10px;">
                        ${proj.github ? `<a href="${proj.github}" target="_blank" class="btn-secondary btn-sm" style="padding:6px 10px;"><i class="fa-brands fa-github"></i> Repo</a>` : ''}
                        ${proj.live ? `<a href="${proj.live}" target="_blank" class="btn-primary btn-sm" style="padding:6px 10px;"><i class="fa-solid fa-globe"></i> Live</a>` : ''}
                    </div>
                    <div>
                        <button class="btn-secondary btn-sm" style="padding:6px 10px; color:var(--color-warning); border-color:rgba(250,204,21,0.2);" onclick="openEditProjectModal(${proj.id})"><i class="fa-solid fa-pen-to-square"></i></button>
                        <button class="btn-secondary btn-sm" style="padding:6px 10px; color:var(--color-danger); border-color:rgba(255,77,109,0.2);" onclick="deleteProject(${proj.id})"><i class="fa-solid fa-trash"></i></button>
                    </div>
                </div>
            </div>
        `).join('');
    }

    window.filterProjects = function() {
        if (!state.projectsList) return;
        const searchVal = document.getElementById('project-search-input').value.toLowerCase();
        const filtered = state.projectsList.filter(p => 
            p.name.toLowerCase().includes(searchVal) || p.tech.toLowerCase().includes(searchVal)
        );
        renderProjectsGrid(filtered);
    };

    window.openAddProjectModal = function() {
        document.getElementById('project-modal-title').innerText = "Add Project";
        document.getElementById('modal-project-id').value = '';
        document.getElementById('modal-project-name').value = '';
        document.getElementById('modal-project-tech').value = '';
        document.getElementById('modal-project-completion').value = '';
        document.getElementById('modal-project-github').value = '';
        document.getElementById('modal-project-live').value = '';
        document.getElementById('add-project-modal').style.display = 'flex';
    };

    window.openEditProjectModal = function(id) {
        const proj = state.projectsList.find(p => p.id === id);
        if (!proj) return;
        document.getElementById('project-modal-title').innerText = "Edit Project";
        document.getElementById('modal-project-id').value = proj.id;
        document.getElementById('modal-project-name').value = proj.name;
        document.getElementById('modal-project-tech').value = proj.tech;
        document.getElementById('modal-project-completion').value = proj.completion;
        document.getElementById('modal-project-github').value = proj.github || '';
        document.getElementById('modal-project-live').value = proj.live || '';
        document.getElementById('add-project-modal').style.display = 'flex';
    };

    window.closeProjectModal = function() {
        document.getElementById('add-project-modal').style.display = 'none';
    };

    window.deleteProject = function(id) {
        if (!confirm("Are you sure you want to delete this project record?")) return;
        state.projectsList = state.projectsList.filter(p => p.id !== id);
        renderProjectsGrid(state.projectsList);
        renderProjectsCharts(state.projectsList);
    };

    const projectForm = document.getElementById('project-modal-form');
    if (projectForm) {
        projectForm.addEventListener('submit', (e) => {
            e.preventDefault();
            const idVal = document.getElementById('modal-project-id').value;
            const name = document.getElementById('modal-project-name').value;
            const tech = document.getElementById('modal-project-tech').value;
            const completion = parseInt(document.getElementById('modal-project-completion').value, 10);
            const github = document.getElementById('modal-project-github').value;
            const live = document.getElementById('modal-project-live').value;

            if (idVal) {
                const proj = state.projectsList.find(p => p.id === parseInt(idVal, 10));
                if (proj) {
                    proj.name = name;
                    proj.tech = tech;
                    proj.completion = completion;
                    proj.github = github;
                    proj.live = live;
                }
            } else {
                const newId = state.projectsList.length > 0 ? Math.max(...state.projectsList.map(p => p.id)) + 1 : 1;
                state.projectsList.push({
                    id: newId,
                    name, tech, completion, github, live,
                    ai_score: Math.floor(Math.random() * 15) + 85
                });
            }

            closeProjectModal();
            renderProjectsGrid(state.projectsList);
            renderProjectsCharts(state.projectsList);
        });
    }

    function renderProjectsCharts(list) {
        state.activeCharts = state.activeCharts || {};

        const uCanvas = document.getElementById('chart-project-tech-usage');
        if (uCanvas) {
            if (state.activeCharts.projTech) state.activeCharts.projTech.destroy();
            const counts = {};
            list.forEach(p => {
                p.tech.split(',').map(t => t.trim()).forEach(tech => {
                    counts[tech] = (counts[tech] || 0) + 1;
                });
            });

            state.activeCharts.projTech = new Chart(uCanvas, {
                type: 'bar',
                data: {
                    labels: Object.keys(counts),
                    datasets: [{
                        data: Object.values(counts),
                        backgroundColor: '#4F7CFF',
                        borderRadius: 4
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: {
                        x: { ticks: { color: '#9CA3AF' } },
                        y: { ticks: { color: '#9CA3AF' }, grid: { color: 'rgba(255,255,255,0.05)' } }
                    }
                }
            });
        }

        const cCanvas = document.getElementById('chart-project-completion');
        if (cCanvas) {
            if (state.activeCharts.projComp) state.activeCharts.projComp.destroy();
            const ranges = {'Complete (90%+)': 0, 'In Progress': 0};
            list.forEach(p => {
                if (p.completion >= 90) ranges['Complete (90%+)']++;
                else ranges['In Progress']++;
            });

            state.activeCharts.projComp = new Chart(cCanvas, {
                type: 'doughnut',
                data: {
                    labels: Object.keys(ranges),
                    datasets: [{
                        data: Object.values(ranges),
                        backgroundColor: ['#00D084', '#FACC15'],
                        borderWidth: 0
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { position: 'right', labels: { color: '#9CA3AF', boxWidth: 10 } } }
                }
            });
        }
    }

    // 6. Certificates Manager
    async function loadCertificatesManager() {
        try {
            const data = await MeetAiAPI.request('/api/certificates', { method: 'GET' });
            state.certsData = data;

            document.getElementById('certs-total-count').innerText = data.stats.total;
            document.getElementById('certs-verified-count').innerText = data.stats.verified;
            document.getElementById('certs-pending-count').innerText = data.stats.pending;
            document.getElementById('certs-expired-count').innerText = data.stats.expired;

            renderCertificatesTable(data.certificates);
            renderCertificatesCharts(data.certificates);
        } catch (err) {
            console.error("Certificates manager load failed:", err.message);
        }
    }

    function renderCertificatesTable(list) {
        const body = document.getElementById('certs-table-body');
        if (!body) return;
        if (list.length === 0) {
            body.innerHTML = `<tr><td colspan="7" style="text-align:center; color:var(--text-muted);">No certificates verified yet.</td></tr>`;
            return;
        }
        body.innerHTML = list.map(cert => `
            <tr>
                <td><strong>${cert.name}</strong></td>
                <td>${cert.platform}</td>
                <td>${cert.issue_date}</td>
                <td>${cert.expiry}</td>
                <td><code>${cert.credential_id}</code></td>
                <td>
                    <span class="badge ${cert.status === 'Verified' ? 'badge-success' : cert.status === 'Pending' ? 'badge-warning' : 'badge-danger'}">
                        ${cert.status}
                    </span>
                </td>
                <td>
                    <button class="btn-secondary btn-sm" onclick="alert('Viewing credential: ${cert.credential_id}')" style="padding: 4px 8px; font-size:11px;">View</button>
                    <button class="btn-secondary btn-sm" onclick="alert('Downloading certificate file format...')" style="padding: 4px 8px; font-size:11px;">Download</button>
                </td>
            </tr>
        `).join('');
    }

    window.filterCertificates = function() {
        if (!state.certsData) return;
        const searchVal = document.getElementById('cert-search-input').value.toLowerCase();
        const filtered = state.certsData.certificates.filter(c => 
            c.name.toLowerCase().includes(searchVal) || c.platform.toLowerCase().includes(searchVal)
        );
        renderCertificatesTable(filtered);
    };

    window.openUploadCertModal = function() {
        document.getElementById('upload-cert-modal').style.display = 'flex';
    };

    window.closeCertModal = function() {
        document.getElementById('upload-cert-modal').style.display = 'none';
    };

    const certForm = document.getElementById('cert-modal-form');
    if (certForm) {
        certForm.addEventListener('submit', (e) => {
            e.preventDefault();
            const name = document.getElementById('modal-cert-name').value;
            const platform = document.getElementById('modal-cert-platform').value;
            const issue = document.getElementById('modal-cert-issue').value;
            const expiry = document.getElementById('modal-cert-expiry').value || 'N/A';
            const credential = document.getElementById('modal-cert-credential').value;

            state.certsData.certificates.push({
                id: state.certsData.certificates.length + 1,
                name, platform, issue_date: issue, expiry, credential_id: credential,
                status: 'Verified'
            });

            state.certsData.stats.total++;
            state.certsData.stats.verified++;
            document.getElementById('certs-total-count').innerText = state.certsData.stats.total;
            document.getElementById('certs-verified-count').innerText = state.certsData.stats.verified;

            closeCertModal();
            renderCertificatesTable(state.certsData.certificates);
            renderCertificatesCharts(state.certsData.certificates);
        });
    }

    function renderCertificatesCharts(certs) {
        state.activeCharts = state.activeCharts || {};

        const cCanvas = document.getElementById('chart-certs-monthly');
        if (cCanvas) {
            if (state.activeCharts.certsMonthly) state.activeCharts.certsMonthly.destroy();
            const counts = {};
            certs.forEach(c => {
                counts[c.platform] = (counts[c.platform] || 0) + 1;
            });

            state.activeCharts.certsMonthly = new Chart(cCanvas, {
                type: 'bar',
                data: {
                    labels: Object.keys(counts),
                    datasets: [{
                        data: Object.values(counts),
                        backgroundColor: '#8B5CF6',
                        borderRadius: 4
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: {
                        x: { ticks: { color: '#9CA3AF', font: { size: 9 } } },
                        y: { ticks: { color: '#9CA3AF' }, grid: { color: 'rgba(255,255,255,0.05)' } }
                    }
                }
            });
        }

        const sCanvas = document.getElementById('chart-certs-skills');
        if (sCanvas) {
            if (state.activeCharts.certsSkills) state.activeCharts.certsSkills.destroy();
            const categories = {'Cloud': 0, 'Design': 0, 'Development': 0, 'Database': 0, 'Network': 0};
            certs.forEach(c => {
                const n = c.name.toLowerCase();
                if (n.includes('aws') || n.includes('azure') || n.includes('cloud')) categories['Cloud']++;
                else if (n.includes('ux') || n.includes('design')) categories['Design']++;
                else if (n.includes('react') || n.includes('front-end')) categories['Development']++;
                else if (n.includes('sql') || n.includes('database')) categories['Database']++;
                else categories['Network']++;
            });

            state.activeCharts.certsSkills = new Chart(sCanvas, {
                type: 'pie',
                data: {
                    labels: Object.keys(categories),
                    datasets: [{
                        data: Object.values(categories),
                        backgroundColor: ['#4F7CFF', '#8B5CF6', '#00D084', '#FACC15', '#FF4D6D'],
                        borderWidth: 0
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { position: 'right', labels: { color: '#9CA3AF', boxWidth: 10 } } }
                }
            });
        }
    }

    // 7. Applications Tracker
    async function loadApplicationsTracker() {
        try {
            const data = await MeetAiAPI.request('/api/applications', { method: 'GET' });
            state.applicationsData = data;

            renderKanbanBoard(data.applications);
            renderUpcomingInterviews(data.upcoming_interviews);
            renderApplicationsCharts(data.applications);
        } catch (err) {
            console.error("Applications tracker failed to load:", err.message);
        }
    }

    function renderKanbanBoard(list) {
        const columns = {
            'applied-tracker': document.getElementById('wrap-applied-tracker'),
            'interview-tracker': document.getElementById('wrap-interview-tracker'),
            'technical-tracker': document.getElementById('wrap-technical-tracker'),
            'hr-tracker': document.getElementById('wrap-hr-tracker'),
            'offer-tracker': document.getElementById('wrap-offer-tracker')
        };

        Object.values(columns).forEach(col => { if(col) col.innerHTML = ''; });

        list.forEach(app => {
            let colName = 'applied-tracker';
            if (app.status === 'interview') colName = 'interview-tracker';
            else if (app.status === 'technical') colName = 'technical-tracker';
            else if (app.status === 'hr') colName = 'hr-tracker';
            else if (app.status === 'offer') colName = 'offer-tracker';

            const wrapper = columns[colName];
            if (wrapper) {
                const card = document.createElement('div');
                card.className = 'kanban-card';
                card.id = app.id;
                card.draggable = true;
                card.setAttribute('ondragstart', 'drag(event)');
                card.innerHTML = `
                    <div style="font-size:12px; font-weight:800; color:#FFF; margin-bottom:5px;">${app.company}</div>
                    <div style="font-size:11px; color:var(--text-muted); margin-bottom:10px;">${app.role}</div>
                    <div style="display:flex; justify-content:space-between; align-items:center; font-size:10px;">
                        <span style="color:var(--color-primary);">${app.salary}</span>
                        <span style="color:var(--text-muted);">${app.location}</span>
                    </div>
                `;
                wrapper.appendChild(card);
            }
        });

        ['applied-tracker', 'interview-tracker', 'technical-tracker', 'hr-tracker', 'offer-tracker'].forEach(c => {
            const wrap = document.getElementById(`wrap-${c}`);
            const badge = document.getElementById(`badge-${c}`);
            if (wrap && badge) {
                badge.innerText = wrap.children.length;
            }
        });
    }

    function renderUpcomingInterviews(list) {
        const container = document.getElementById('upcoming-interviews-calendar-list');
        if (!container) return;
        container.innerHTML = list.map(item => `
            <div class="glass-card" style="padding:12px; display:flex; align-items:center; gap:15px; border-left: 3px solid var(--color-secondary);">
                <div style="text-align:center; min-width:50px;">
                    <i class="fa-regular fa-calendar-check" style="font-size:20px; color:var(--color-secondary);"></i>
                </div>
                <div>
                    <h5 style="margin:0 0 4px 0;">${item.company} • ${item.round}</h5>
                    <p style="margin:0; font-size:11px; color:var(--text-muted);">${item.date}</p>
                </div>
            </div>
        `).join('');
    }

    function renderApplicationsCharts(apps) {
        state.activeCharts = state.activeCharts || {};

        const canvas = document.getElementById('chart-app-success');
        if (canvas) {
            if (state.activeCharts.appSuccess) state.activeCharts.appSuccess.destroy();
            const counts = {'Active': 0, 'Offers': 0, 'Rejected': 0};
            apps.forEach(a => {
                if (a.status === 'offer') counts['Offers']++;
                else if (a.status === 'rejected') counts['Rejected']++;
                else counts['Active']++;
            });

            state.activeCharts.appSuccess = new Chart(canvas, {
                type: 'doughnut',
                data: {
                    labels: Object.keys(counts),
                    datasets: [{
                        data: Object.values(counts),
                        backgroundColor: ['#4F7CFF', '#00D084', '#FF4D6D'],
                        borderWidth: 0
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { position: 'bottom', labels: { color: '#9CA3AF', boxWidth: 10 } } }
                }
            });
        }
    }

    // 8. Analytics Dashboard
    async function loadAnalyticsDashboard() {
        try {
            const data = await MeetAiAPI.request('/api/analytics', { method: 'GET' });
            renderAnalyticsCharts(data);
        } catch (err) {
            console.error("Analytics load error:", err.message);
        }
    }

    function renderAnalyticsCharts(data) {
        state.activeCharts = state.activeCharts || {};

        const line = document.getElementById('chart-analytics-progression');
        if (line) {
            if (state.activeCharts.analyticsLine) state.activeCharts.analyticsLine.destroy();
            state.activeCharts.analyticsLine = new Chart(line, {
                type: 'line',
                data: {
                    labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
                    datasets: [
                        {
                            label: 'Resume Views',
                            data: data.resume_views,
                            borderColor: '#4F7CFF',
                            tension: 0.3,
                            fill: false
                        },
                        {
                            label: 'ATS Alignment Score',
                            data: data.ats_growth,
                            borderColor: '#8B5CF6',
                            tension: 0.3,
                            fill: false
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { labels: { color: '#9CA3AF' } } },
                    scales: {
                        x: { ticks: { color: '#9CA3AF' } },
                        y: { ticks: { color: '#9CA3AF' }, grid: { color: 'rgba(255,255,255,0.05)' } }
                    }
                }
            });
        }

        const fun = document.getElementById('chart-analytics-conversion');
        if (fun) {
            if (state.activeCharts.analyticsFunnel) state.activeCharts.analyticsFunnel.destroy();
            state.activeCharts.analyticsFunnel = new Chart(fun, {
                type: 'doughnut',
                data: {
                    labels: Object.keys(data.interview_success),
                    datasets: [{
                        data: Object.values(data.interview_success),
                        backgroundColor: ['#4F7CFF', '#8B5CF6', '#FACC15', '#00D084', '#FF4D6D'],
                        borderWidth: 0
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { position: 'bottom', labels: { color: '#9CA3AF', boxWidth: 10 } } }
                }
            });
        }

        const sal = document.getElementById('chart-analytics-salary');
        if (sal) {
            if (state.activeCharts.analyticsSalary) state.activeCharts.analyticsSalary.destroy();
            state.activeCharts.analyticsSalary = new Chart(sal, {
                type: 'bar',
                data: {
                    labels: data.salary_expectations.map(s => s.company),
                    datasets: [
                        {
                            label: 'Expected LPA',
                            data: data.salary_expectations.map(s => s.expected),
                            backgroundColor: '#4F7CFF'
                        },
                        {
                            label: 'Offered LPA',
                            data: data.salary_expectations.map(s => s.offered),
                            backgroundColor: '#8B5CF6'
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { labels: { color: '#9CA3AF' } } },
                    scales: {
                        x: { ticks: { color: '#9CA3AF' } },
                        y: { ticks: { color: '#9CA3AF' }, grid: { color: 'rgba(255,255,255,0.05)' } }
                    }
                }
            });
        }

        const activity = document.getElementById('chart-analytics-weekly-heatmap');
        if (activity) {
            if (state.activeCharts.analyticsActivity) state.activeCharts.analyticsActivity.destroy();
            state.activeCharts.analyticsActivity = new Chart(activity, {
                type: 'bar',
                data: {
                    labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
                    datasets: [{
                        data: [4, 6, 8, 3, 5, 2, 1],
                        backgroundColor: '#00D084',
                        borderRadius: 3
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: {
                        x: { ticks: { color: '#9CA3AF' } },
                        y: { ticks: { color: '#9CA3AF' }, grid: { color: 'rgba(255,255,255,0.05)' } }
                    }
                }
            });
        }
    }

    // 9. Reports Center
    async function loadReportsCenter() {
        try {
            const data = await MeetAiAPI.request('/api/reports', { method: 'GET' });
            state.reportsData = data;
            renderReportsList(data.reports);
        } catch (err) {
            console.error("Reports center load failed:", err.message);
        }
    }

    function renderReportsList(list) {
        const body = document.getElementById('reports-table-body');
        if (!body) return;
        if (list.length === 0) {
            body.innerHTML = `<tr><td colspan="6" style="text-align:center; color:var(--text-muted);">No reports matched your selection.</td></tr>`;
            return;
        }
        body.innerHTML = list.map(rep => `
            <tr>
                <td><code>${rep.id}</code></td>
                <td><strong>${rep.name}</strong></td>
                <td><span class="badge" style="background:rgba(255,255,255,0.03); color:#FFF;">${rep.type}</span></td>
                <td>${rep.date}</td>
                <td><strong>${rep.score}%</strong></td>
                <td>
                    <button class="btn-primary btn-sm" onclick="alert('Downloading report: ${rep.id} as ${rep.format}...')" style="padding: 4px 8px; font-size:11px;"><i class="fa-solid fa-download"></i> Download</button>
                    <button class="btn-secondary btn-sm" onclick="window.print()" style="padding: 4px 8px; font-size:11px;"><i class="fa-solid fa-print"></i> Print</button>
                </td>
            </tr>
        `).join('');
    }

    window.filterReports = function() {
        if (!state.reportsData) return;
        const period = document.getElementById('report-period').value;
        const type = document.getElementById('report-type').value;

        const filtered = state.reportsData.reports.filter(rep => {
            const matchType = type === 'all' || rep.type === type;
            let matchPeriod = true;
            if (period === 'week') {
                matchPeriod = new Date(rep.date) >= new Date(Date.now() - 7 * 24 * 60 * 60 * 1000);
            } else if (period === 'month') {
                matchPeriod = new Date(rep.date) >= new Date(Date.now() - 30 * 24 * 60 * 60 * 1000);
            } else if (period === 'year') {
                matchPeriod = new Date(rep.date) >= new Date(Date.now() - 365 * 24 * 60 * 60 * 1000);
            }
            return matchType && matchPeriod;
        });

        renderReportsList(filtered);
    };

    window.exportReportsCSV = function() {
        alert("Preparing CSV export... The table has been parsed and will save to your local system.");
    };

    window.exportReportsExcel = function() {
        alert("Preparing Excel Spreadsheet export... The table has been parsed and will save to your local system.");
    };

    // --- Recruiter AI Bulk Resume Scanner Controller ---
    let bulkSelectedFiles = [];
    let bulkJobId = null;
    let bulkProgressInterval = null;
    let recruiterFilterType = 'all';

    window.showBulkUploadArea = function() {
        document.getElementById('bulk-upload-zone').style.display = 'block';
        document.getElementById('bulk-processing-indicator').style.display = 'none';
        document.getElementById('bulk-recruiter-dashboard').style.display = 'none';
        
        // Reset inputs and queue
        document.getElementById('bulk-file-input').value = '';
        document.getElementById('bulk-folder-input').value = '';
        document.getElementById('bulk-zip-input').value = '';
        document.getElementById('bulk-selected-summary').style.display = 'none';
        bulkSelectedFiles = [];
    };

    window.handleBulkFilesSelect = function(event) {
        const files = event.target.files;
        if (!files || files.length === 0) return;

        // Limit maximum files to 100
        const totalPending = bulkSelectedFiles.length + files.length;
        if (totalPending > 100) {
            alert("Maximum file upload limit is 100 resumes. Selecting the first 100 valid files.");
        }

        for (let i = 0; i < files.length; i++) {
            if (bulkSelectedFiles.length >= 100) break;
            const file = files[i];
            const ext = file.name.split('.').pop().toLowerCase();
            
            // File validation: Reject invalid files
            if (['pdf', 'docx', 'doc', 'zip'].indexOf(ext) === -1) {
                console.warn(`File rejected (invalid format): ${file.name}`);
                continue;
            }
            
            bulkSelectedFiles.push(file);
        }

        updateBulkQueueUI();
    };

    function updateBulkQueueUI() {
        const count = bulkSelectedFiles.length;
        if (count === 0) {
            document.getElementById('bulk-selected-summary').style.display = 'none';
            return;
        }

        document.getElementById('bulk-queue-count').innerText = count;
        
        // Calculate total size and estimated time
        let totalBytes = 0;
        bulkSelectedFiles.forEach(f => totalBytes += f.size);
        const totalMB = (totalBytes / (1024 * 1024)).toFixed(1);
        
        // Max size limit: 500 MB
        if (parseFloat(totalMB) > 500) {
            alert("The total queue size exceeds the 500 MB maximum threshold. Please remove some files.");
            showBulkUploadArea();
            return;
        }

        document.getElementById('bulk-total-size').innerText = `${totalMB} MB`;
        
        // 2 seconds estimated per resume
        const estSec = count * 2;
        const estMin = Math.floor(estSec / 60);
        const estSecRemaining = estSec % 60;
        const estStr = estMin > 0 ? `${estMin}m ${estSecRemaining}s` : `${estSec}s`;
        document.getElementById('bulk-est-time').innerText = estStr;

        // Populate visual files list
        const filesList = document.getElementById('bulk-files-list');
        filesList.innerHTML = bulkSelectedFiles.map((file, idx) => `
            <div style="display:flex; justify-content:space-between; align-items:center; background:rgba(255,255,255,0.02); padding:6px 12px; border-radius:4px; border:1px solid var(--border-color);">
                <span><i class="fa-solid fa-file-invoice" style="margin-right:8px; color:var(--color-primary);"></i> ${file.name}</span>
                <span style="color:var(--text-muted); cursor:pointer;" onclick="removeBulkQueueFile(${idx})">&times;</span>
            </div>
        `).join('');

        document.getElementById('bulk-selected-summary').style.display = 'block';
    }

    window.removeBulkQueueFile = function(idx) {
        bulkSelectedFiles.splice(idx, 1);
        updateBulkQueueUI();
    };

    window.startBulkAIAnalysis = async function() {
        if (bulkSelectedFiles.length === 0) return;

        const formData = new FormData();
        bulkSelectedFiles.forEach(file => {
            formData.append('files', file);
        });

        // Show processing UI
        document.getElementById('bulk-upload-zone').style.display = 'none';
        document.getElementById('bulk-processing-indicator').style.display = 'block';
        
        // Reset progress bar
        document.getElementById('bulk-progress-bar').style.width = '0%';
        document.getElementById('bulk-progress-text').innerText = `0 / ${bulkSelectedFiles.length} Resumes (0%)`;
        document.getElementById('bulk-current-ticker').innerText = bulkSelectedFiles[0].name;

        try {
            // 1. Upload files
            const uploadData = await MeetAiAPI.request('/api/bulk-upload', {
                method: 'POST',
                body: formData
            });

            bulkJobId = uploadData.bulk_job_id;
            const fileTasks = uploadData.file_tasks;

            // 2. Start analysis
            await MeetAiAPI.request('/api/bulk-analysis', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    bulk_job_id: bulkJobId,
                    file_tasks: fileTasks
                })
            });

            // 3. Start polling progress
            pollBulkAnalysisProgress(bulkJobId);

        } catch (err) {
            alert(`Bulk Scan failed: ${err.message}`);
            showBulkUploadArea();
        }
    };

    function pollBulkAnalysisProgress(jobId) {
        if (bulkProgressInterval) clearInterval(bulkProgressInterval);
        
        let estSecondsLeft = bulkSelectedFiles.length * 2;
        
        bulkProgressInterval = setInterval(async () => {
            try {
                const data = await MeetAiAPI.request(`/api/bulk-dashboard?bulk_job_id=${jobId}`, { method: 'GET' });
                const job = data.job;
                if (!job) return;

                const total = job.total_files;
                const processed = job.processed_files + job.failed_files;
                const pct = total > 0 ? Math.round((processed / total) * 100) : 0;

                // Update progress bar
                document.getElementById('bulk-progress-bar').style.width = `${pct}%`;
                document.getElementById('bulk-progress-text').innerText = `${processed} / ${total} Resumes (${pct}%)`;
                
                // Update ticker
                if (data.candidates && data.candidates.length > 0) {
                    const latestCand = data.candidates[data.candidates.length - 1];
                    document.getElementById('bulk-current-ticker').innerText = `${latestCand.name} - Graded`;
                }

                // Decrement estimated timer
                estSecondsLeft = Math.max(estSecondsLeft - 2, 0);
                const estMin = Math.floor(estSecondsLeft / 60);
                const estSec = estSecondsLeft % 60;
                document.getElementById('bulk-time-remaining').innerText = `${estMin.toString().padStart(2, '0')}:${estSec.toString().padStart(2, '0')}`;

                if (job.status === 'completed' || processed >= total) {
                    clearInterval(bulkProgressInterval);
                    alert("AI Bulk Scan successfully completed!");
                    
                    // Show Recruiter Dashboard
                    document.getElementById('bulk-processing-indicator').style.display = 'none';
                    document.getElementById('bulk-recruiter-dashboard').style.display = 'flex';
                    
                    loadBulkDashboard(jobId);
                }

            } catch (err) {
                console.error("Polling progress failed:", err.message);
            }
        }, 2000);
    }

    async function loadBulkDashboard(jobId = null) {
        try {
            const url = jobId ? `/api/bulk-dashboard?bulk_job_id=${jobId}` : '/api/bulk-dashboard';
            const data = await MeetAiAPI.request(url, { method: 'GET' });
            
            if (!data.job) {
                showBulkUploadArea();
                return;
            }

            state.recruiterData = data;
            
            // Set stats
            document.getElementById('stat-bulk-total').innerText = data.stats.total_uploaded;
            document.getElementById('stat-bulk-processed').innerText = data.stats.processed;
            document.getElementById('stat-bulk-failed').innerText = data.stats.failed;
            document.getElementById('stat-bulk-avg-ats').innerText = `${data.stats.avg_ats}%`;
            document.getElementById('stat-bulk-max-ats').innerText = `${data.stats.max_ats}%`;
            document.getElementById('stat-bulk-avg-exp').innerText = `${data.stats.avg_exp} Yrs`;

            // Display recruiter dashboard elements
            document.getElementById('bulk-upload-zone').style.display = 'none';
            document.getElementById('bulk-processing-indicator').style.display = 'none';
            document.getElementById('bulk-recruiter-dashboard').style.display = 'flex';

            renderRecruiterTable(data.candidates);
            renderRecruiterRanking(data.ranking);

        } catch (err) {
            console.error("Recruiter dashboard load error:", err.message);
        }
    }

    function renderRecruiterTable(list) {
        const body = document.getElementById('recruiter-table-body');
        if (!body) return;
        if (list.length === 0) {
            body.innerHTML = `<tr><td colspan="6" style="text-align:center; color:var(--text-muted); padding:20px;">No candidates parsed in this batch.</td></tr>`;
            return;
        }

        body.innerHTML = list.map(c => `
            <tr style="border-bottom:1px solid var(--border-color); hover:background:rgba(255,255,255,0.01);">
                <td style="padding:12px;"><strong>${c.name}</strong><div style="font-size:11px; color:var(--text-muted);">${c.email}</div></td>
                <td style="padding:12px;"><span class="badge ${c.ats_score >= 80 ? 'badge-success' : c.ats_score >= 60 ? 'badge-primary' : 'badge-warning'}">${c.ats_score}% Match</span></td>
                <td style="padding:12px;"><strong>${c.resume_score}%</strong></td>
                <td style="padding:12px;">${c.experience}</td>
                <td style="padding:12px; font-size:11px; color:var(--text-muted); max-width:200px; text-overflow:ellipsis; overflow:hidden; white-space:nowrap;">${c.skills}</td>
                <td style="padding:12px; text-align:center; display:flex; justify-content:center; gap:8px;">
                    <button class="btn-secondary btn-sm" onclick="viewCandidateScorecard(${c.id})" style="padding:4px 8px; font-size:11px;"><i class="fa-solid fa-address-card"></i> View</button>
                    <button class="btn-secondary btn-sm" onclick="deleteCandidate(${c.id})" style="padding:4px 8px; font-size:11px; color:var(--color-danger); border-color:rgba(255,77,109,0.2);"><i class="fa-solid fa-trash"></i></button>
                </td>
            </tr>
        `).join('');
    }

    function renderRecruiterRanking(list) {
        const listContainer = document.getElementById('recruiter-ranking-list');
        if (!listContainer) return;
        if (list.length === 0) {
            listContainer.innerHTML = `<p style="color:var(--text-muted); text-align:center; font-size:12px;">No rankings available yet.</p>`;
            return;
        }

        listContainer.innerHTML = list.map(r => {
            let badgeClass = 'badge-danger';
            if (r.score >= 90) badgeClass = 'badge-success';
            else if (r.score >= 80) badgeClass = 'badge-primary';
            else if (r.score >= 70) badgeClass = 'badge-warning';

            return `
                <div class="glass-card" style="padding:12px 15px; display:flex; justify-content:space-between; align-items:center; border-left:4px solid ${r.score >= 80 ? 'var(--color-success)' : 'var(--color-warning)'};">
                    <div style="display:flex; align-items:center; gap:12px;">
                        <span style="font-size:16px; font-weight:800; color:var(--text-muted);">#${r.rank}</span>
                        <div>
                            <strong style="font-size:13px;">${r.name}</strong>
                            <div style="font-size:11px; color:var(--text-muted);">${r.score}% Match</div>
                        </div>
                    </div>
                    <span class="badge ${badgeClass}" style="font-size:10px;">${r.recommendation}</span>
                </div>
            `;
        }).join('');
    }

    window.applyRecruiterFilters = function() {
        if (!state.recruiterData) return;
        
        const searchVal = document.getElementById('recruiter-search-input').value.toLowerCase();
        const sortVal = document.getElementById('recruiter-sort-select').value;

        // 1. Filter
        let filtered = state.recruiterData.candidates.filter(c => {
            // Text search match
            const matchText = c.name.toLowerCase().includes(searchVal) || 
                              c.email.toLowerCase().includes(searchVal) || 
                              c.skills.toLowerCase().includes(searchVal);

            // Badge filter match
            let matchBadge = true;
            if (recruiterFilterType === 'ats80') {
                matchBadge = c.ats_score > 80;
            } else if (recruiterFilterType === 'exp3') {
                const yrs = parseInt(c.experience, 10) || 0;
                matchBadge = yrs > 3;
            } else if (recruiterFilterType === 'freshers') {
                const yrs = parseInt(c.experience, 10) || 0;
                matchBadge = yrs <= 1;
            }

            return matchText && matchBadge;
        });

        // 2. Sort
        if (sortVal === 'ats-desc') {
            filtered.sort((a, b) => b.ats_score - a.ats_score);
        } else if (sortVal === 'ats-asc') {
            filtered.sort((a, b) => a.ats_score - b.ats_score);
        } else if (sortVal === 'exp-desc') {
            filtered.sort((a, b) => (parseInt(b.experience, 10) || 0) - (parseInt(a.experience, 10) || 0));
        } else if (sortVal === 'name-asc') {
            filtered.sort((a, b) => a.name.localeCompare(b.name));
        }

        renderRecruiterTable(filtered);
    };

    window.toggleRecruiterFilter = function(badgeElement, filterName) {
        // Toggle active badges
        badgeElement.parentNode.querySelectorAll('.badge').forEach(b => b.classList.remove('active'));
        badgeElement.classList.add('active');
        
        recruiterFilterType = filterName;
        applyRecruiterFilters();
    };

    window.exportRecruiterCSV = function() {
        if (!state.recruiterData || state.recruiterData.candidates.length === 0) return;
        
        // Generate CSV content
        let csvContent = "data:text/csv;charset=utf-8,";
        csvContent += "Candidate Name,Email,Phone,ATS Match,Resume Score,Experience,Skills\n";
        
        state.recruiterData.candidates.forEach(c => {
            const row = [
                `"${c.name}"`,
                `"${c.email}"`,
                `"${c.phone}"`,
                `"${c.ats_score}%"`,
                `"${c.resume_score}%"`,
                `"${c.experience}"`,
                `"${c.skills.replace(/"/g, '""')}"`
            ].join(",");
            csvContent += row + "\n";
        });

        const encodedUri = encodeURI(csvContent);
        const link = document.createElement("a");
        link.setAttribute("href", encodedUri);
        link.setAttribute("download", `candidates_roster_job_${bulkJobId || 'latest'}.csv`);
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    };

    window.downloadAllReportsZip = function() {
        if (!bulkJobId && (!state.recruiterData || !state.recruiterData.job)) {
            alert("No reports zip archive available for download.");
            return;
        }
        const jobId = bulkJobId || state.recruiterData.job.id;
        window.open(`/api/download-all/${jobId}`, '_blank');
    };

    window.viewCandidateScorecard = async function(resumeId) {
        try {
            const data = await MeetAiAPI.request(`/api/candidate/${resumeId}`, { method: 'GET' });
            const c = data.candidate;

            document.getElementById('modal-candidate-name').innerText = c.name;
            document.getElementById('modal-candidate-contact').innerText = `Email: ${c.email || 'N/A'} | Phone: ${c.phone || 'N/A'}`;

            // Skills
            const skillsHolder = document.getElementById('modal-candidate-skills');
            skillsHolder.innerHTML = c.skills.map(s => `<span class="badge badge-primary" style="font-size:11px;">${s}</span>`).join('');

            // Education
            const eduHolder = document.getElementById('modal-candidate-education');
            eduHolder.innerHTML = c.education.length > 0 ? c.education.map(e => `<li><strong>${e.degree || 'Degree'}</strong> - ${e.institution || 'Institution'} (${e.year || 'N/A'})</li>`).join('') : '<li>No education details extracted.</li>';

            // Experience
            const expHolder = document.getElementById('modal-candidate-experience');
            expHolder.innerHTML = c.experience.length > 0 ? c.experience.map(e => `<li><strong>${e.title || 'Role'}</strong> at ${e.company || 'Company'} (${e.duration || 'N/A'})</li>`).join('') : '<li>No work experience details extracted.</li>';

            // Recommendations
            const feedback = c.analysis.suggestions && c.analysis.suggestions.length > 0 ? c.analysis.suggestions.join(" ") : "Candidate profile is highly aligned and recommended for immediate technical recruiter screening.";
            document.getElementById('modal-candidate-feedback').innerText = feedback;

            // Set download URL
            const token = MeetAiAPI.getToken();
            document.getElementById('modal-btn-download').onclick = function() {
                window.open(`/api/reports/${c.id}/download?token=${token}`, '_blank');
            };

            document.getElementById('candidate-scorecard-modal').style.display = 'flex';
        } catch (err) {
            alert(`Failed to load candidate: ${err.message}`);
        }
    };

    window.closeCandidateModal = function() {
        document.getElementById('candidate-scorecard-modal').style.display = 'none';
    };

    window.deleteCandidate = async function(resumeId) {
        if (!confirm("Are you sure you want to delete this candidate analysis file?")) return;
        try {
            await MeetAiAPI.request(`/api/analysis/${resumeId}`, { method: 'DELETE' });
            alert("Candidate deleted successfully.");
            
            // Reload dashboard
            loadBulkDashboard(bulkJobId);
        } catch (err) {
            alert(`Deletion failed: ${err.message}`);
        }
    };

    // Helper method to capitalize file title strings
    String.prototype.title = function() {
        return this.split(' ').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
    };

    // Auth Tab Switcher (keeps the URL hash in sync with the visible panel)
    window.switchAuthTab = function(tabName) {
        const isRegister = tabName === 'register';
        const loginContainer = document.getElementById('auth-login-form-container');
        const regContainer = document.getElementById('auth-register-form-container');
        const loginTab = document.getElementById('tab-btn-login');
        const regTab = document.getElementById('tab-btn-register');

        if (!loginContainer || !regContainer) return;

        loginContainer.style.display = isRegister ? 'none' : 'block';
        regContainer.style.display = isRegister ? 'block' : 'none';

        if (loginTab) {
            loginTab.classList.toggle('active', !isRegister);
            loginTab.setAttribute('aria-selected', String(!isRegister));
        }
        if (regTab) {
            regTab.classList.toggle('active', isRegister);
            regTab.setAttribute('aria-selected', String(isRegister));
        }

        const targetHash = isRegister ? '#register' : '#login';
        if (window.location.hash !== targetHash) {
            window.location.hash = targetHash;
        }
    };

    // --- Bootstrapping Router ---
    async function bootstrap() {
        // Flask serves /login and /register as the same SPA shell, so translate
        // a direct visit to those paths into the matching hash route.
        if (!window.location.hash) {
            const path = window.location.pathname.replace(/\/+$/, '');
            if (path === '/login' || path === '/register') {
                window.location.hash = path === '/register' ? '#register' : '#login';
            }
        }

        const hash = window.location.hash;
        if (!MeetAiAPI.isLoggedIn()) {
            if (hash === '' || hash === '#' || hash === '#features' || hash === '#pricing' || hash === '#dashboard') {
                window.location.hash = '#login';
            }
        } else {
            if (hash === '' || hash === '#' || hash === '#features' || hash === '#pricing' || hash === '#login' || hash === '#register') {
                window.location.hash = '#dashboard';
            }
        }
        router();
    }
    bootstrap();
});
