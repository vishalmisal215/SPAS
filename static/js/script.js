let remainingSeconds = 0;
let timerInterval = null;
let tabSwitchCount = 0;

// Timer functions
function startTimer(seconds) {
    remainingSeconds = seconds;
    updateTimerDisplay();
    timerInterval = setInterval(function () {
        remainingSeconds--;
        updateTimerDisplay();
        if (remainingSeconds <= 0) {
            clearInterval(timerInterval);
            autoSubmitExam("Time is over. Your exam will be submitted.");
        }
    }, 1000);
}

function updateTimerDisplay() {
    const timerDiv = document.getElementById("timer");
    if (!timerDiv) return;
    const min = Math.floor(remainingSeconds / 60);
    const sec = remainingSeconds % 60;
    timerDiv.textContent = "Time Left: " + min + "m " + (sec < 10 ? "0" + sec : sec) + "s";
}

// Tab monitoring
function initTabMonitor() {
    document.addEventListener("visibilitychange", function () {
        if (document.visibilityState === "hidden") {
            tabSwitchCount++;
            handleTabSwitch();
        }
    });
}

function handleTabSwitch() {
    const warningDiv = document.getElementById("tab-warning");
    if (!warningDiv) return;
    
    if (tabSwitchCount === 1) {
        warningDiv.textContent = "Warning 1: Do not switch tabs during exam.";
        alert("Warning 1: Do not switch tabs during the exam.");
    } else if (tabSwitchCount === 2) {
        warningDiv.textContent = "Warning 2: Next tab change will auto-submit your exam.";
        alert("Warning 2: Next tab change will auto-submit your exam.");
    } else if (tabSwitchCount >= 3) {
        autoSubmitExam("You switched tabs too many times. Exam will be submitted.");
    }
}

function autoSubmitExam(message) {
    alert(message);
    const form = document.getElementById("examForm");
    if (form) {
        form.submit();
    }
}

// Disable copy-paste during exam
function disableCopyPaste() {
    // Disable right-click
    document.addEventListener('contextmenu', function(e) {
        e.preventDefault();
        return false;
    });
    
    // Disable Ctrl+C, Ctrl+V, Ctrl+X
    document.addEventListener('keydown', function(e) {
        if (e.ctrlKey && e.keyCode === 67) {
            e.preventDefault();
            return false;
        }
        if (e.ctrlKey && e.keyCode === 86) {
            e.preventDefault();
            return false;
        }
        if (e.ctrlKey && e.keyCode === 88) {
            e.preventDefault();
            return false;
        }
        if (e.ctrlKey && e.keyCode === 65) {
            e.preventDefault();
            return false;
        }
    });
    
    document.addEventListener('copy', function(e) {
        e.preventDefault();
        return false;
    });
    
    document.addEventListener('paste', function(e) {
        e.preventDefault();
        return false;
    });
    
    document.addEventListener('cut', function(e) {
        e.preventDefault();
        return false;
    });
}

// Dashboard Navigation
document.addEventListener('DOMContentLoaded', function() {
    const navButtons = document.querySelectorAll('.nav-btn[data-target]');
    const hamburgerInput = document.getElementById('hamburger-toggle');
    
    if (navButtons.length > 0) {
        navButtons.forEach(button => {
            button.addEventListener('click', function() {
                const targetId = this.getAttribute('data-target');
                
                document.querySelectorAll('.dashboard-section').forEach(section => {
                    section.classList.remove('active');
                });
                
                const targetSection = document.getElementById(targetId);
                if (targetSection) {
                    targetSection.classList.add('active');
                }
                
                if (hamburgerInput) {
                    hamburgerInput.checked = false;
                }
            });
        });
    }
    
    // Edit Profile
    const editProfileBtn = document.getElementById('edit-profile-btn');
    const profileForm = document.getElementById('profile-form');
    const profileInfo = document.getElementById('profile-info');
    
    if (editProfileBtn && profileForm && profileInfo) {
        editProfileBtn.addEventListener('click', function() {
            profileInfo.style.display = 'none';
            profileForm.style.display = 'block';
        });
    }
    
    const cancelEditBtn = document.getElementById('cancel-edit-btn');
    if (cancelEditBtn && profileForm && profileInfo) {
        cancelEditBtn.addEventListener('click', function() {
            profileForm.style.display = 'none';
            profileInfo.style.display = 'block';
        });
    }
});

// Password toggle
function togglePassword(fieldId) {
    const field = document.getElementById(fieldId);
    const toggle = field.nextElementSibling;
    if (field.type === "password") {
        field.type = "text";
        toggle.textContent = "🙈";
    } else {
        field.type = "password";
        toggle.textContent = "👁️";
    }
}

function showCreateForm() {
    document.getElementById('login-form').style.display = 'none';
    document.getElementById('create-form').style.display = 'block';
}

function showLoginForm() {
    document.getElementById('create-form').style.display = 'none';
    document.getElementById('login-form').style.display = 'block';
}

// Initialize exam protections if on exam page
if (document.getElementById('examForm')) {
    disableCopyPaste();
}
