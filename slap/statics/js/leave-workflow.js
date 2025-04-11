// Common utility functions
const API_ENDPOINTS = {
    GET_APPLICATIONS: '/api/get_leave_applications',
    UPDATE_STATUS: '/api/update_leave_status',
    GET_APPROVED: '/api/get_approved_applications',
    GET_REJECTED: '/api/get_rejected_applications'
};

// Utility function to format date
function formatDate(dateString) {
    return new Date(dateString).toLocaleDateString();
}

// Function to handle API errors
async function handleApiResponse(response) {
    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.message || 'Failed to process request');
    }
    return response.json();
}

// Load applications based on role and status
async function loadApplications(role) {
    try {
        const response = await fetch(API_ENDPOINTS.GET_APPLICATIONS);
        const data = await handleApiResponse(response);
        
        // Filter applications based on role and status
        applications = data.filter(app => {
            if (role === 'staff') {
                return app.status === 'pending';
            } else if (role === 'admin') {
                return app.status === 'staff_approved';
            }
            return true;
        });
        
        populateTable(applications, role);
    } catch (error) {
        console.error('Error loading applications:', error);
        showError('Failed to load applications');
    }
}

// Staff approval function
async function approveApplication(id) {
    try {
        const response = await fetch(API_ENDPOINTS.UPDATE_STATUS, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                id: id,
                status: 'staff_approved',
                role: 'staff'
            })
        });
        
        const result = await handleApiResponse(response);
        if (result.success) {
            showSuccess('Application forwarded to admin for approval');
            await loadApplications('staff');
        }
    } catch (error) {
        showError('Failed to approve application');
    }
}

// Admin approval function
async function adminApproveApplication(id) {
    try {
        const response = await fetch(API_ENDPOINTS.UPDATE_STATUS, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                id: id,
                status: 'approved',
                role: 'admin'
            })
        });
        
        const result = await handleApiResponse(response);
        if (result.success) {
            showSuccess('Application approved successfully');
            if (result.redirect) {
                window.location.href = result.redirect;
            }
        }
    } catch (error) {
        showError('Failed to approve application');
    }
}

// Rejection function (works for both staff and admin)
async function rejectApplication(id, role) {
    try {
        const response = await fetch(API_ENDPOINTS.UPDATE_STATUS, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                id: id,
                status: 'rejected',
                role: role
            })
        });
        
        const result = await handleApiResponse(response);
        if (result.success) {
            showSuccess('Application rejected');
            if (result.redirect) {
                window.location.href = result.redirect;
            }
            await loadApplications(role);
        }
    } catch (error) {
        showError('Failed to reject application');
    }
}

// Function to populate the application table
function populateTable(applications, role) {
    const tableBody = document.querySelector("#applicationTable tbody");
    if (!tableBody) return;

    if (applications.length === 0) {
        tableBody.innerHTML = "<tr><td colspan='7' style='text-align: center;'>No pending applications</td></tr>";
        return;
    }

    tableBody.innerHTML = '';
    applications.forEach(app => {
        const actions = role === 'staff' 
            ? `<button class="view-btn" onclick="viewLeaveLetter(${app.id})">View</button>
               <button class="approve-btn" onclick="approveApplication(${app.id})">Accept</button>
               <button class="reject-btn" onclick="rejectApplication(${app.id}, 'staff')">Reject</button>`
            : `<button class="view-btn" onclick="viewLeaveLetter(${app.id})">View</button>
               <button class="approve-btn" onclick="adminApproveApplication(${app.id})">Accept</button>
               <button class="reject-btn" onclick="rejectApplication(${app.id}, 'admin')">Reject</button>`;

        const row = `
            <tr>
                <td><img src="${app.photo || '/static/placeholder.jpg'}" alt="${app.name}" class="profile-img"></td>
                <td>${app.name}</td>
                <td>${app.studentId}</td>
                <td>${formatDate(app.fromDate)}</td>
                <td>${formatDate(app.toDate)}</td>
                <td>${app.category}</td>
                <td>${actions}</td>
            </tr>
        `;
        tableBody.innerHTML += row;
    });
}

// Load approved/rejected applications for student view
async function loadStudentApplications(status) {
    try {
        const response = await fetch('/api/get_rejected_applications'); // New API for rejected leaves
        if (!response.ok) throw new Error('Failed to fetch applications');
        
        const applications = await response.json();
        populateRejectedTable(applications);
    } catch (error) {
        console.error('Error loading applications:', error);
    }
}

function populateRejectedTable(applications) {
    const tableBody = document.querySelector("#applicationTable tbody");
    tableBody.innerHTML = '';

    if (applications.length === 0) {
        tableBody.innerHTML = "<tr><td colspan='8' style='text-align: center;'>No rejected applications</td></tr>";
        return;
    }

    applications.forEach(app => {
        const row = `
            <tr>
                <td><img src="${app.photo}" alt="Student Photo" class="profile-img"></td>
                <td>${app.name}</td>
                <td>${app.studentId}</td>
                <td>${app.fromDate}</td>
                <td>${app.toDate}</td>
                <td>${app.category}</td>
                <td>${app.rejectedBy}</td>
                <td>${app.rejectedAt}</td>
            </tr>
        `;
        tableBody.innerHTML += row;
    });
}

// Utility functions for notifications
function showSuccess(message) {
    alert(message); // Replace with your preferred notification system
}

function showError(message) {
    alert(message); // Replace with your preferred notification system
}

// Initialize the page based on role
function initializePage(role) {
    window.onload = async function() {
        await loadApplications(role);
        // Refresh applications every 30 seconds
        setInterval(() => loadApplications(role), 30000);
    };
}

