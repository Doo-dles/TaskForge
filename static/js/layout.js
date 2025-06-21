        function toggleSidebar() {
            const sidebar = document.getElementById("mySidebar");
            const toggleBtn = document.getElementById("sidebarToggle");
    
            sidebar.classList.toggle("active");
    
            // Show/hide ☰ icon
            toggleBtn.style.display = sidebar.classList.contains("active") ? "none" : "block";
        }
        function toggleCategoryBar() {
            const bar = document.getElementById('category-bar');
            bar.classList.toggle('show');
        }

       // Get DOM elements
        const voiceModal = document.getElementById('voiceModal');
        const voiceText = document.getElementById('voiceText');
        const voiceBtn = document.getElementById('voice-btn');
        const voiceCancel = document.getElementById('voiceCancel');

        // Setup SpeechRecognition
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        const recognition = new SpeechRecognition();

        recognition.interimResults = true;   // Get live partial results
        recognition.lang = 'en-US';

        let finalTranscript = '';

        // Open modal & start recognition when mic button clicked
        voiceBtn.addEventListener('click', () => {
        finalTranscript = ''; // Reset before start
        voiceModal.style.display = 'block';
        voiceText.innerText = 'Listening...';
        recognition.start();
        });

        // Listen for speech results
        recognition.onresult = (event) => {
        let interimTranscript = '';

        for (let i = event.resultIndex; i < event.results.length; i++) {
            if (event.results[i].isFinal) {
            finalTranscript += event.results[i][0].transcript;
            } else {
            interimTranscript += event.results[i][0].transcript;
            }
        }

        // Show live combined transcript in modal
        voiceText.innerText = finalTranscript + interimTranscript;
        };

        // When speech recognition ends (user stops speaking)
        recognition.onend = () => {
        if (finalTranscript.trim().length === 0) {
            // Nothing spoken, just close modal
            voiceModal.style.display = 'none';
            voiceText.innerText = '';
            return;
        }

        // Send full transcript to Flask route
        fetch('/process-voice', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ transcript: finalTranscript })
        })
        .then(res => res.json())
        .then(data => {
            if (data.status == 'ok') {
            alert('Task added successfully!');
            } else {
            alert('Failed to add task.');
            }
            voiceModal.style.display = 'none';
            voiceText.innerText = '';
            finalTranscript = '';
        })
        .catch(() => {
            alert('Network or server error.');
            voiceModal.style.display = 'none';
            voiceText.innerText = '';
            finalTranscript = '';
        });
        };

        // Cancel button to stop recognition and close modal
        voiceCancel.addEventListener('click', () => {
        recognition.stop();
        voiceModal.style.display = 'none';
        voiceText.innerText = '';
        finalTranscript = '';
        });

        // Error handling
        recognition.onerror = (event) => {
        alert('Speech recognition error: ' + event.error);
        voiceModal.style.display = 'none';
        voiceText.innerText = '';
        finalTranscript = '';
        };

        let cachedReminders = [];
        let remindersMarkedRead = false;

        function fetchRemindersOnce() {
            fetch('/get_reminders')
                .then(res => res.json())
                .then(data => {
                    cachedReminders = data;
                    updateReminderUI(data);
                });
        }

        function updateReminderUI(data) {
            const list = document.getElementById('reminder-list');
            const badge = document.getElementById('reminder-badge');
            list.innerHTML = '';

            if (data.length === 0) {
                list.innerHTML = '<li>No reminders</li>';
                badge.style.display = 'none';
            } else {
                data.forEach(n => {
                    const li = document.createElement('li');
                    li.textContent = `${n.message} (${new Date(n.created_at).toLocaleString()})`;
                    list.appendChild(li);
                });
                badge.textContent = data.length;
                badge.style.display = 'inline';
            }
        }

        function toggleReminders() {
            const dropdown = document.getElementById('reminder-dropdown');
            const isVisible = dropdown.style.display === 'block';
            dropdown.style.display = isVisible ? 'none' : 'block';

            if (!isVisible) {
                if (cachedReminders.length === 0) {
                    fetchRemindersOnce(); // First fetch
                } else {
                    updateReminderUI(cachedReminders); // Use cached data
                }

                if (!remindersMarkedRead) {
                    // Mark notifications as read once
                    fetch('/mark_notifications_read', { method: 'POST' });
                    remindersMarkedRead = true;

                    // Hide badge immediately
                    const badge = document.getElementById('reminder-badge');
                    badge.style.display = 'none';
                }
            }
        }

        // Optional: auto-fetch on page load
        window.onload = fetchRemindersOnce;

