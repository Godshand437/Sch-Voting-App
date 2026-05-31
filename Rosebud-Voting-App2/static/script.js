// --- LOGIN LOGIC ---
async function handleLogin() {
    const user = document.getElementById('username').value;
    const pass = document.getElementById('password').value;

    const response = await fetch('/api/login', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({username: user, password: pass})
    });

    const result = await response.json();

    if (result.status === "success") {
        if (result.role === "admin") {
            // Send Admin to the Control Panel
            window.location.href = "/admin_panel";
        } else {
            // Send Student to their specific portal with their ID
            window.location.href = "/student_portal/" + result.user;
        }
    } else {
        alert(result.message);
    }
}

// --- ADMIN: REGISTER STUDENT (With Image Support) ---
async function registerStudent() {
    const id = document.getElementById('reg_id').value;
    const name = document.getElementById('reg_name').value;
    const s_class = document.getElementById('reg_class').value;
    const imageFile = document.getElementById('reg_image').files[0];

    // Check if ID and Name are filled
    if (!id || !name) return alert("Please enter both ID and Name!");

    // We use FormData to send files (images) to Python
    const formData = new FormData();
    formData.append('student_id', id);
    formData.append('name', name);
    formData.append('class', s_class);
    formData.append('image', imageFile);

    const response = await fetch('/api/admin/add_student', {
        method: 'POST',
        body: formData
    });

    const result = await response.json();
    alert(result.message);
    
    // If the function refreshStudentList exists on the page, run it
    if (typeof refreshStudentList === "function") refreshStudentList();
}

// --- ADMIN: APPOINT CANDIDATE ---
async function registerCandidate() {
    const select = document.getElementById('cand_student_select');
    const position = document.getElementById('cand_position').value;
    
    if (!select.value || !position) return alert("Select a student and a position!");

    const data = {
        student_id: select.value,
        name: select.options[select.selectedIndex].text.split(' (')[0], // Gets name from "Name (ID)"
        position: position,
        class_room: 'Assigned' 
    };

    const response = await fetch('/api/admin/add_candidate', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(data)
    });

    const result = await response.json();
    if (result.status === "success") {
        alert("Candidate Added to Ballot!");
    }
}