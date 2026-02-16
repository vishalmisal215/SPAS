// Faculty Dashboard JavaScript - CORRECTED VERSION

document.addEventListener('DOMContentLoaded', function() {
    // Navigation buttons
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

    // Add Practical Modal - FIXED
    const addBtn = document.querySelector('.add-practical-btn');
    const modal = document.getElementById('add-practical-modal');
    const closeBtn = modal ? modal.querySelector('.close') : null;
    const closeModalBtn = modal ? modal.querySelector('.close-modal') : null;
    
    if (addBtn && modal) {
        addBtn.addEventListener('click', function(e) {
            e.preventDefault();
            console.log('Add Practical button clicked'); // Debug
            modal.style.display = 'block';
        });
    }
    
    if (closeBtn) {
        closeBtn.addEventListener('click', function() {
            modal.style.display = 'none';
        });
    }
    
    if (closeModalBtn) {
        closeModalBtn.addEventListener('click', function() {
            modal.style.display = 'none';
        });
    }
    
    window.addEventListener('click', function(event) {
        if (event.target === modal) {
            modal.style.display = 'none';
        }
    });
    
    // Add Practical Form Submit - FIXED
    const addForm = document.getElementById('add-practical-form');
    
    if (addForm) {
        addForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            console.log('Form submitted'); // Debug
            
            const input = document.getElementById('practical-input');
            const subjectSelect = document.getElementById('practical-subject-select');
            const name = input.value.trim();
            const subjectId = subjectSelect ? subjectSelect.value : '1';
            
            if (!name) {
                alert('Please enter a practical name');
                return;
            }
            
            console.log('Sending:', name, 'Subject:', subjectId); // Debug
            
            try {
                const response = await fetch('/api/add_practical', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ name: name, subject_id: subjectId })
                });
                
                console.log('Response received:', response); // Debug
                
                const data = await response.json();
                console.log('Data:', data); // Debug
                
                if (data.success) {
                    alert('Practical added successfully! Page will reload.');
                    location.reload(); // Reload to show new practical
                } else {
                    alert('Failed to add practical: ' + data.message);
                }
            } catch (error) {
                console.error('Error:', error); // Debug
                alert('Error adding practical: ' + error.message);
            }
        });
    }
});

// Remove Practical Function
async function removePractical(practicalName) {
    if (!confirm(`Are you sure you want to remove "${practicalName}"?`)) {
        return;
    }
    
    try {
        const response = await fetch('/api/remove_practical', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ name: practicalName })
        });
        
        const data = await response.json();
        
        if (data.success) {
            alert('Practical removed successfully! Page will reload.');
            location.reload();
        } else {
            alert('Failed to remove practical: ' + data.message);
        }
    } catch (error) {
        alert('Error removing practical: ' + error.message);
    }
}

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

// Batch filter change
function changeBatchFilter() {
    const select = document.getElementById('batch-filter-select');
    if (select) {
        const batch = select.value;
        window.location.href = `?batch=${batch}`;
    }
}
