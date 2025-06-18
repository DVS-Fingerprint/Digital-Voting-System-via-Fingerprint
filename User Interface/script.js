// Global Variables
let currentLanguage = 'en';
let currentVoter = null;
let sessionTimer = null;
let sessionTimeout = 60000; // 1 minute
let candidates = [];
let votes = [];
let activityLogs = [];
let voterVotes = {}; // Track votes per voter per post

// Sample Data with multiple posts
const samplePosts = [
    {
        id: 'president',
        name: 'President',
        nameNp: 'अध्यक्ष',
        description: 'Student Council President',
        descriptionNp: 'विद्यार्थी परिषद अध्यक्ष'
    },
    {
        id: 'vice_president',
        name: 'Vice President',
        nameNp: 'उपाध्यक्ष',
        description: 'Student Council Vice President',
        descriptionNp: 'विद्यार्थी परिषद उपाध्यक्ष'
    },
    {
        id: 'secretary',
        name: 'Secretary',
        nameNp: 'सचिव',
        description: 'Student Council Secretary',
        descriptionNp: 'विद्यार्थी परिषद सचिव'
    },
    {
        id: 'treasurer',
        name: 'Treasurer',
        nameNp: 'कोषाध्यक्ष',
        description: 'Student Council Treasurer',
        descriptionNp: 'विद्यार्थी परिषद कोषाध्यक्ष'
    }
];

const sampleCandidates = [
    {
        id: 1,
        name: "John Smith",
        party: "Student Progressive Party",
        photo: "👨‍🎓",
        post: "president",
        manifesto: "I believe in creating an inclusive environment where every student's voice is heard. My focus will be on improving campus facilities, enhancing academic support, and fostering a strong community spirit.",
        achievements: [
            "Class Representative for 2 years",
            "Organized 5 successful campus events",
            "Led the debate team to regional finals",
            "Maintained 3.8 GPA throughout college"
        ]
    },
    {
        id: 2,
        name: "Sarah Johnson",
        party: "Future Leaders Alliance",
        photo: "👩‍🎓",
        post: "president",
        manifesto: "My vision is to modernize our student council with innovative ideas and digital solutions. I will work towards better communication channels, enhanced career guidance, and improved student welfare programs.",
        achievements: [
            "Vice President of Computer Science Club",
            "Won Best Student Leader Award 2023",
            "Successfully implemented online voting system",
            "Coordinated 3 major tech workshops"
        ]
    },
    {
        id: 3,
        name: "Michael Chen",
        party: "Unity Student Movement",
        photo: "👨‍💼",
        post: "president",
        manifesto: "I stand for unity and collaboration among all departments. My goals include bridging gaps between different student groups, promoting cultural diversity, and creating opportunities for cross-disciplinary learning.",
        achievements: [
            "President of International Students Association",
            "Organized Cultural Fest 2023",
            "Represented college in Model UN",
            "Published 2 research papers"
        ]
    },
    {
        id: 4,
        name: "Emily Davis",
        party: "Student Progressive Party",
        photo: "👩‍💼",
        post: "vice_president",
        manifesto: "I will work closely with the president to ensure smooth operations and represent student interests effectively.",
        achievements: [
            "Class Representative for 1 year",
            "Organized 3 campus events",
            "Member of debate team",
            "Maintained 3.7 GPA"
        ]
    },
    {
        id: 5,
        name: "David Wilson",
        party: "Future Leaders Alliance",
        photo: "👨‍🎓",
        post: "vice_president",
        manifesto: "My focus will be on supporting the president's vision while bringing fresh perspectives to student governance.",
        achievements: [
            "Vice President of Science Club",
            "Won Best Student Award 2023",
            "Coordinated 2 major workshops",
            "Published 1 research paper"
        ]
    },
    {
        id: 6,
        name: "Lisa Brown",
        party: "Unity Student Movement",
        photo: "👩‍💼",
        post: "secretary",
        manifesto: "I will ensure transparent communication and maintain accurate records of all council activities.",
        achievements: [
            "Secretary of Literature Club",
            "Excellent record keeping skills",
            "Organized 4 successful events",
            "Maintained 3.9 GPA"
        ]
    },
    {
        id: 7,
        name: "Robert Taylor",
        party: "Student Progressive Party",
        photo: "👨‍💼",
        post: "secretary",
        manifesto: "I will maintain clear documentation and ensure all students are informed about council decisions.",
        achievements: [
            "Class Secretary for 2 years",
            "Excellent communication skills",
            "Led 3 successful campaigns",
            "Maintained 3.6 GPA"
        ]
    },
    {
        id: 8,
        name: "Maria Garcia",
        party: "Future Leaders Alliance",
        photo: "👩‍🎓",
        post: "treasurer",
        manifesto: "I will ensure transparent financial management and responsible allocation of student funds.",
        achievements: [
            "Treasurer of Finance Club",
            "Excellent financial management skills",
            "Organized 2 fundraising events",
            "Maintained 3.8 GPA"
        ]
    },
    {
        id: 9,
        name: "James Anderson",
        party: "Unity Student Movement",
        photo: "👨‍💼",
        post: "treasurer",
        manifesto: "I will maintain accurate financial records and ensure proper use of student council funds.",
        achievements: [
            "Treasurer of Economics Club",
            "Strong accounting background",
            "Managed 3 club budgets",
            "Maintained 3.7 GPA"
        ]
    }
];

const sampleVoters = [
    { id: 1, name: "John Doe", fingerprint: "finger1", hasVoted: {} },
    { id: 2, name: "Jane Smith", fingerprint: "finger2", hasVoted: {} },
    { id: 3, name: "Bob Wilson", fingerprint: "finger3", hasVoted: {} }
];

// Initialize the application
document.addEventListener('DOMContentLoaded', function() {
    console.log('Voting System Initializing...');
    initializeApp();
    setupEventListeners();
    loadSampleData();
    console.log('Voting System Ready!');
});

function initializeApp() {
    console.log('Initializing app...');
    
    // Initialize data
    candidates = [...sampleCandidates];
    votes = [];
    activityLogs = [];
    
    // Set initial language
    updateLanguage();
    
    // Show welcome page
    showPage('welcomePage');
    
    console.log('App initialized successfully');
}

function setupEventListeners() {
    console.log('Setting up event listeners...');
    
    // Language toggle
    const langToggle = document.getElementById('langToggle');
    if (langToggle) {
        langToggle.addEventListener('click', toggleLanguage);
        console.log('Language toggle listener added');
    }
    
    // Start voting button
    const startVotingBtn = document.getElementById('startVotingBtn');
    if (startVotingBtn) {
        startVotingBtn.addEventListener('click', startFingerprintScan);
        console.log('Start voting button listener added');
    }
    
    // Back to welcome button
    const backToWelcome = document.getElementById('backToWelcome');
    if (backToWelcome) {
        backToWelcome.addEventListener('click', () => showPage('welcomePage'));
    }
    
    // Tab switching
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const tab = e.currentTarget.dataset.tab;
            switchTab(tab);
        });
    });
    
    // Logout button
    const logoutBtn = document.getElementById('logoutBtn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', logout);
    }
    
    // Modal events
    const closeModal = document.getElementById('closeModal');
    if (closeModal) {
        closeModal.addEventListener('click', closeModalFunction);
    }
    
    const cancelVote = document.getElementById('cancelVote');
    if (cancelVote) {
        cancelVote.addEventListener('click', closeModalFunction);
    }
    
    const confirmVote = document.getElementById('confirmVote');
    if (confirmVote) {
        confirmVote.addEventListener('click', confirmVoteFunction);
    }
    
    // New vote button
    const newVoteBtn = document.getElementById('newVoteBtn');
    if (newVoteBtn) {
        newVoteBtn.addEventListener('click', () => showPage('welcomePage'));
    }
    
    // Admin controls
    const refreshData = document.getElementById('refreshData');
    if (refreshData) {
        refreshData.addEventListener('click', refreshAdminData);
    }
    
    const generateReports = document.getElementById('generateReports');
    if (generateReports) {
        generateReports.addEventListener('click', generateReportsFunction);
    }
    
    // Click outside modal to close
    window.addEventListener('click', (e) => {
        const modal = document.getElementById('confirmationModal');
        if (e.target === modal) {
            closeModalFunction();
        }
    });
    
    console.log('All event listeners set up');
}

function loadSampleData() {
    // Load sample votes
    votes = [
        { candidateId: 1, count: 45 },
        { candidateId: 2, count: 38 },
        { candidateId: 3, count: 27 }
    ];
    
    // Load sample activity logs
    activityLogs = [
        { time: '10:30 AM', voter: 'Jane Smith', action: 'Login', status: 'Success' },
        { time: '10:32 AM', voter: 'Jane Smith', action: 'Vote Cast', status: 'Success' },
        { time: '10:35 AM', voter: 'John Doe', action: 'Login', status: 'Success' },
        { time: '10:40 AM', voter: 'Bob Wilson', action: 'Login', status: 'Failed' }
    ];
    
    console.log('Sample data loaded');
}

// Language Management
function toggleLanguage() {
    console.log('Toggling language...');
    currentLanguage = currentLanguage === 'en' ? 'np' : 'en';
    updateLanguage();
    showToast(`Language changed to ${currentLanguage === 'en' ? 'English' : 'नेपाली'}`, 'success');
}

function updateLanguage() {
    const langText = document.getElementById('langText');
    const elements = document.querySelectorAll('[data-en][data-np]');
    
    if (langText) {
        langText.textContent = currentLanguage === 'en' ? 'English' : 'नेपाली';
    }
    
    elements.forEach(element => {
        const text = currentLanguage === 'en' ? element.dataset.en : element.dataset.np;
        if (text) {
            element.textContent = text;
        }
    });
    
    console.log(`Language updated to: ${currentLanguage}`);
}

// Page Navigation
function showPage(pageId) {
    console.log(`Showing page: ${pageId}`);
    
    // Hide all pages
    document.querySelectorAll('.page').forEach(page => {
        page.classList.remove('active');
    });
    
    // Show target page
    const targetPage = document.getElementById(pageId);
    if (targetPage) {
        targetPage.classList.add('active');
    }
    
    // Handle page-specific logic
    switch(pageId) {
        case 'welcomePage':
            resetSession();
            break;
        case 'dashboardPage':
            if (currentVoter) {
                loadDashboard();
            }
            break;
        case 'adminPage':
            loadAdminDashboard();
            break;
    }
}

// Fingerprint Scanning
function startFingerprintScan() {
    console.log('Starting fingerprint scan...');
    showPage('scannerPage');
    simulateFingerprintScan();
}

function simulateFingerprintScan() {
    const scannerCircle = document.querySelector('.scanner-circle');
    const progressBar = document.querySelector('.progress-bar');
    
    if (!scannerCircle || !progressBar) {
        console.error('Scanner elements not found');
        return;
    }
    
    // Start scanning animation
    scannerCircle.classList.add('active');
    
    let progress = 0;
    const interval = setInterval(() => {
        progress += 2;
        progressBar.style.width = progress + '%';
        
        if (progress >= 100) {
            clearInterval(interval);
            scannerCircle.classList.remove('active');
            
            // Simulate fingerprint verification
            setTimeout(() => {
                const success = Math.random() > 0.2; // 80% success rate
                if (success) {
                    const voter = sampleVoters[Math.floor(Math.random() * sampleVoters.length)];
                    authenticateVoter(voter);
                } else {
                    showToast('Fingerprint verification failed. Please try again.', 'error');
                    setTimeout(() => showPage('welcomePage'), 2000);
                }
            }, 1000);
        }
    }, 50);
}

function authenticateVoter(voter) {
    currentVoter = voter;
    addActivityLog(voter.name, 'Login', 'Success');
    showToast(`Welcome, ${voter.name}!`, 'success');
    showPage('dashboardPage');
}

// Dashboard Management
function loadDashboard() {
    console.log('Loading dashboard for voter:', currentVoter.name);
    
    // Update voter info
    document.getElementById('voterName').textContent = currentVoter.name;
    
    // Initialize voter votes if not exists
    if (!currentVoter.hasVoted) {
        currentVoter.hasVoted = {};
    }
    
    // Load the main dashboard view
    loadMainDashboard();
    
    // Start session timer
    startSessionTimer();
    
    // Log activity
    addActivityLog(currentVoter.name, 'Login', 'Success');
    
    console.log('Dashboard loaded successfully');
}

function loadMainDashboard() {
    const voteTab = document.getElementById('voteTab');
    const infoTab = document.getElementById('infoTab');
    
    // Clear existing content
    voteTab.innerHTML = '';
    infoTab.innerHTML = '';
    
    // Create main dashboard content
    const dashboardContent = document.createElement('div');
    dashboardContent.className = 'dashboard-main';
    
    // Create two main sections
    const voteSection = document.createElement('div');
    voteSection.className = 'dashboard-section';
    voteSection.innerHTML = `
        <div class="section-header">
            <i class="fas fa-vote-yea"></i>
            <h3 data-en="Cast Your Vote" data-np="आफ्नो मत दिनुहोस्">Cast Your Vote</h3>
        </div>
        <div class="posts-grid" id="postsGrid">
            <!-- Posts will be populated here -->
        </div>
    `;
    
    const candidateListSection = document.createElement('div');
    candidateListSection.className = 'dashboard-section';
    candidateListSection.innerHTML = `
        <div class="section-header">
            <i class="fas fa-users"></i>
            <h3 data-en="All Candidates" data-np="सबै उम्मेदवारहरू">All Candidates</h3>
        </div>
        <div class="candidates-overview" id="candidatesOverview">
            <!-- All candidates will be shown here -->
        </div>
    `;
    
    voteTab.appendChild(voteSection);
    infoTab.appendChild(candidateListSection);
    
    // Load posts and candidates
    loadPosts();
    loadAllCandidates();
}

function loadPosts() {
    const postsGrid = document.getElementById('postsGrid');
    if (!postsGrid) return;
    
    postsGrid.innerHTML = '';
    
    samplePosts.forEach(post => {
        const postCard = document.createElement('div');
        postCard.className = 'post-card';
        
        const hasVoted = currentVoter.hasVoted[post.id];
        const isVoted = hasVoted ? 'voted' : '';
        
        postCard.innerHTML = `
            <div class="post-icon">
                <i class="fas fa-user-tie"></i>
            </div>
            <div class="post-info">
                <h4 data-en="${post.name}" data-np="${post.nameNp}">${post.name}</h4>
                <p data-en="${post.description}" data-np="${post.descriptionNp}">${post.description}</p>
            </div>
            <div class="post-status ${isVoted}">
                ${hasVoted ? 
                    '<i class="fas fa-check-circle"></i><span data-en="Voted" data-np="मत दिएको">Voted</span>' : 
                    '<i class="fas fa-arrow-right"></i><span data-en="Vote Now" data-np="अहिले मत दिनुहोस्">Vote Now</span>'
                }
            </div>
        `;
        
        if (!hasVoted) {
            postCard.addEventListener('click', () => showCandidatesForPost(post));
            postCard.style.cursor = 'pointer';
        }
        
        postsGrid.appendChild(postCard);
    });
    
    updateLanguage();
}

function loadAllCandidates() {
    const candidatesOverview = document.getElementById('candidatesOverview');
    if (!candidatesOverview) return;
    
    candidatesOverview.innerHTML = '';
    
    // Group candidates by post
    const candidatesByPost = {};
    sampleCandidates.forEach(candidate => {
        if (!candidatesByPost[candidate.post]) {
            candidatesByPost[candidate.post] = [];
        }
        candidatesByPost[candidate.post].push(candidate);
    });
    
    // Create sections for each post
    samplePosts.forEach(post => {
        const postCandidates = candidatesByPost[post.id] || [];
        
        const postSection = document.createElement('div');
        postSection.className = 'post-candidates-section';
        postSection.innerHTML = `
            <h4 data-en="${post.name}" data-np="${post.nameNp}">${post.name}</h4>
            <div class="candidates-mini-grid">
                ${postCandidates.map(candidate => `
                    <div class="candidate-mini-card">
                        <div class="candidate-photo">${candidate.photo}</div>
                        <div class="candidate-info">
                            <h5>${candidate.name}</h5>
                            <p>${candidate.party}</p>
                        </div>
                    </div>
                `).join('')}
            </div>
        `;
        
        candidatesOverview.appendChild(postSection);
    });
    
    updateLanguage();
}

function showCandidatesForPost(post) {
    console.log('Showing candidates for post:', post.name);
    
    const voteTab = document.getElementById('voteTab');
    voteTab.innerHTML = '';
    
    // Create back button and header
    const header = document.createElement('div');
    header.className = 'candidates-header';
    header.innerHTML = `
        <button class="back-btn" onclick="loadMainDashboard()">
            <i class="fas fa-arrow-left"></i>
            <span data-en="Back to Posts" data-np="पदहरूमा फिर्ता">Back to Posts</span>
        </button>
        <h3 data-en="Candidates for ${post.name}" data-np="${post.nameNp} का लागि उम्मेदवारहरू">Candidates for ${post.name}</h3>
    `;
    
    const candidatesContainer = document.createElement('div');
    candidatesContainer.className = 'candidates-container';
    candidatesContainer.id = 'candidatesContainer';
    
    voteTab.appendChild(header);
    voteTab.appendChild(candidatesContainer);
    
    // Load candidates for this specific post
    loadCandidatesForPost(post.id);
    
    updateLanguage();
}

function loadCandidatesForPost(postId) {
    const candidatesContainer = document.getElementById('candidatesContainer');
    if (!candidatesContainer) return;
    
    const postCandidates = sampleCandidates.filter(candidate => candidate.post === postId);
    
    if (postCandidates.length === 0) {
        candidatesContainer.innerHTML = `
            <div class="no-candidates">
                <i class="fas fa-exclamation-triangle"></i>
                <p data-en="No candidates found for this position" data-np="यो पदको लागि कुनै उम्मेदवार फेला परेनन्">No candidates found for this position</p>
            </div>
        `;
        return;
    }
    
    const candidatesGrid = document.createElement('div');
    candidatesGrid.className = 'candidates-grid';
    
    postCandidates.forEach(candidate => {
        const candidateCard = createCandidateCard(candidate);
        candidatesGrid.appendChild(candidateCard);
    });
    
    candidatesContainer.appendChild(candidatesGrid);
}

function createCandidateCard(candidate) {
    const card = document.createElement('div');
    card.className = 'candidate-card';
    
    // Check if voter has already voted for this post
    const hasVotedForPost = currentVoter.hasVoted[candidate.post];
    
    card.innerHTML = `
        <div class="candidate-photo">${candidate.photo}</div>
        <h3 class="candidate-name">${candidate.name}</h3>
        <p class="candidate-party">${candidate.party}</p>
        <button class="vote-btn" onclick="selectCandidate(${candidate.id})" ${hasVotedForPost ? 'disabled' : ''}>
            ${hasVotedForPost ? 'Already Voted' : 'Vote'}
        </button>
    `;
    return card;
}

function createCandidateInfoCard(candidate) {
    const card = document.createElement('div');
    card.className = 'candidate-info-card';
    card.innerHTML = `
        <div class="candidate-info-header">
            <div class="candidate-info-photo">${candidate.photo}</div>
            <div class="candidate-info-details">
                <h4>${candidate.name}</h4>
                <p>${candidate.party}</p>
            </div>
        </div>
        <div class="candidate-manifesto">
            <h5>Manifesto</h5>
            <p>${candidate.manifesto}</p>
        </div>
        <div class="candidate-achievements">
            <h5>Achievements</h5>
            <ul class="achievement-list">
                ${candidate.achievements.map(achievement => `<li>${achievement}</li>`).join('')}
            </ul>
        </div>
    `;
    return card;
}

function selectCandidate(candidateId) {
    console.log('Selecting candidate:', candidateId);
    
    const candidate = sampleCandidates.find(c => c.id === candidateId);
    if (!candidate) {
        console.error('Candidate not found');
        return;
    }
    
    // Check if already voted for this post
    if (currentVoter.hasVoted[candidate.post]) {
        showToast('You have already voted for this position', 'warning');
        return;
    }
    
    // Show confirmation modal
    const modal = document.getElementById('confirmationModal');
    const confirmImg = document.getElementById('confirmCandidateImg');
    const confirmName = document.getElementById('confirmCandidateName');
    const confirmParty = document.getElementById('confirmCandidateParty');
    
    if (confirmImg) confirmImg.textContent = candidate.photo;
    if (confirmName) confirmName.textContent = candidate.name;
    if (confirmParty) confirmParty.textContent = candidate.party;
    
    // Store selected candidate for confirmation
    window.selectedCandidate = candidate;
    
    modal.style.display = 'flex';
}

function confirmVoteFunction() {
    console.log('Confirming vote...');
    
    if (!window.selectedCandidate) {
        console.error('No candidate selected');
        return;
    }
    
    const candidate = window.selectedCandidate;
    
    // Record the vote
    currentVoter.hasVoted[candidate.post] = {
        candidateId: candidate.id,
        candidateName: candidate.name,
        timestamp: new Date().toISOString()
    };
    
    // Update vote count
    const existingVote = votes.find(v => v.candidateId === candidate.id);
    if (existingVote) {
        existingVote.count++;
    } else {
        votes.push({ candidateId: candidate.id, count: 1 });
    }
    
    // Log activity
    addActivityLog(currentVoter.name, `Vote Cast for ${candidate.post}`, 'Success');
    
    // Close modal
    closeModalFunction();
    
    // Show thank you page
    showThankYouPage(candidate);
    
    console.log('Vote confirmed successfully');
}

function showThankYouPage(candidate) {
    console.log('Showing thank you page');
    
    // Update thank you page content
    const thankYouPage = document.getElementById('thankYouPage');
    const summaryItem = thankYouPage.querySelector('.summary-item');
    
    if (summaryItem) {
        summaryItem.innerHTML = `
            <div class="summary-candidate">
                <div class="summary-photo">${candidate.photo}</div>
                <div class="summary-details">
                    <h4>${candidate.name}</h4>
                    <p>${candidate.party}</p>
                    <span class="summary-position">${samplePosts.find(p => p.id === candidate.post)?.name || candidate.post}</span>
                </div>
            </div>
        `;
    }
    
    showPage('thankYouPage');
    
    // Auto redirect to dashboard after 5 seconds
    setTimeout(() => {
        showPage('dashboardPage');
        loadMainDashboard();
    }, 5000);
}

function closeModalFunction() {
    const modal = document.getElementById('confirmationModal');
    if (modal) {
        modal.style.display = 'none';
    }
}

// Session Management
function startSessionTimer() {
    if (sessionTimer) {
        clearInterval(sessionTimer);
    }
    
    let timeLeft = sessionTimeout / 1000;
    updateTimerDisplay(timeLeft);
    
    sessionTimer = setInterval(() => {
        timeLeft--;
        updateTimerDisplay(timeLeft);
        
        if (timeLeft <= 0) {
            sessionTimeoutFunction();
        }
    }, 1000);
}

function updateTimerDisplay(seconds) {
    const timer = document.getElementById('timer');
    if (timer) {
        const minutes = Math.floor(seconds / 60);
        const remainingSeconds = seconds % 60;
        timer.textContent = `${minutes.toString().padStart(2, '0')}:${remainingSeconds.toString().padStart(2, '0')}`;
    }
}

function sessionTimeoutFunction() {
    clearInterval(sessionTimer);
    showToast('Session expired due to inactivity', 'warning');
    logout();
}

function resetSession() {
    if (sessionTimer) {
        clearInterval(sessionTimer);
    }
    currentVoter = null;
}

function logout() {
    if (currentVoter) {
        addActivityLog(currentVoter.name, 'Logout', 'Success');
    }
    resetSession();
    showPage('welcomePage');
    showToast('Logged out successfully', 'success');
}

// Tab Management
function switchTab(tabName) {
    // Update tab buttons
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    const activeTabBtn = document.querySelector(`[data-tab="${tabName}"]`);
    if (activeTabBtn) {
        activeTabBtn.classList.add('active');
    }
    
    // Update tab panels
    document.querySelectorAll('.tab-panel').forEach(panel => {
        panel.classList.remove('active');
    });
    const activeTabPanel = document.getElementById(tabName + 'Tab');
    if (activeTabPanel) {
        activeTabPanel.classList.add('active');
    }
}

// Admin Dashboard
function loadAdminDashboard() {
    updateAdminStats();
    updateActivityLogs();
    updateResultsChart();
}

function updateAdminStats() {
    const totalVoters = sampleVoters.length;
    const totalVotes = votes.reduce((sum, vote) => sum + vote.count, 0);
    const turnoutPercentage = totalVoters > 0 ? Math.round((totalVotes / totalVoters) * 100) : 0;
    
    const totalVotersElement = document.getElementById('totalVoters');
    const totalVotesElement = document.getElementById('totalVotes');
    const turnoutPercentageElement = document.getElementById('turnoutPercentage');
    
    if (totalVotersElement) totalVotersElement.textContent = totalVoters;
    if (totalVotesElement) totalVotesElement.textContent = totalVotes;
    if (turnoutPercentageElement) turnoutPercentageElement.textContent = turnoutPercentage + '%';
}

function updateActivityLogs() {
    const tbody = document.getElementById('logsTableBody');
    if (!tbody) return;
    
    tbody.innerHTML = '';
    
    activityLogs.forEach(log => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${log.time}</td>
            <td>${log.voter}</td>
            <td>${log.action}</td>
            <td><span class="status-${log.status.toLowerCase()}">${log.status}</span></td>
        `;
        tbody.appendChild(row);
    });
}

function updateResultsChart() {
    const canvas = document.getElementById('resultsChart');
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    
    // Set canvas size
    canvas.width = 400;
    canvas.height = 300;
    
    // Simple bar chart
    const chartData = candidates.map(candidate => {
        const vote = votes.find(v => v.candidateId === candidate.id);
        return {
            name: candidate.name,
            votes: vote ? vote.count : 0
        };
    });
    
    // Clear canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    
    // Draw bars
    const barWidth = 60;
    const barSpacing = 40;
    const startX = 50;
    const maxVotes = Math.max(...chartData.map(d => d.votes), 1);
    
    chartData.forEach((data, index) => {
        const x = startX + index * (barWidth + barSpacing);
        const height = (data.votes / maxVotes) * 200;
        const y = 250 - height;
        
        // Draw bar
        ctx.fillStyle = '#2563eb';
        ctx.fillRect(x, y, barWidth, height);
        
        // Draw label
        ctx.fillStyle = '#1e293b';
        ctx.font = '12px Inter';
        ctx.textAlign = 'center';
        ctx.fillText(data.name, x + barWidth/2, 270);
        ctx.fillText(data.votes, x + barWidth/2, y - 10);
    });
}

function refreshAdminData() {
    loadAdminDashboard();
    showToast('Data refreshed successfully', 'success');
}

function generateReportsFunction() {
    showToast('Reports generated successfully', 'success');
    console.log('Generating reports...');
    console.log('Voting Results:', votes);
    console.log('Voter List:', sampleVoters);
    console.log('Activity Logs:', activityLogs);
}

// Activity Logging
function addActivityLog(voter, action, status) {
    const log = {
        time: new Date().toLocaleTimeString(),
        voter: voter,
        action: action,
        status: status
    };
    activityLogs.unshift(log);
    
    // Keep only last 50 logs
    if (activityLogs.length > 50) {
        activityLogs = activityLogs.slice(0, 50);
    }
}

// Toast Notifications
function showToast(message, type = 'success') {
    const toastContainer = document.getElementById('toastContainer');
    if (!toastContainer) return;
    
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    
    const icon = type === 'success' ? 'fas fa-check-circle' : 
                 type === 'error' ? 'fas fa-exclamation-circle' : 
                 'fas fa-exclamation-triangle';
    
    toast.innerHTML = `
        <i class="${icon}"></i>
        <span>${message}</span>
    `;
    
    toastContainer.appendChild(toast);
    
    // Remove toast after 5 seconds
    setTimeout(() => {
        if (toast.parentNode) {
            toast.remove();
        }
    }, 5000);
}

// Admin Access (for demonstration)
function showAdminDashboard() {
    showPage('adminPage');
}

// Add admin access button (for demonstration purposes)
document.addEventListener('DOMContentLoaded', function() {
    setTimeout(() => {
        const adminBtn = document.createElement('button');
        adminBtn.textContent = 'Admin';
        adminBtn.style.cssText = `
            position: fixed;
            bottom: 20px;
            left: 20px;
            background: #dc2626;
            color: white;
            border: none;
            padding: 10px 15px;
            border-radius: 25px;
            cursor: pointer;
            font-weight: 500;
            z-index: 1000;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
        `;
        adminBtn.addEventListener('click', showAdminDashboard);
        document.body.appendChild(adminBtn);
        console.log('Admin button added');
    }, 1000);
});

// Make functions globally available
window.selectCandidate = selectCandidate;
window.showAdminDashboard = showAdminDashboard; 