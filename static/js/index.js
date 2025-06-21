document.querySelectorAll('.priority-btn input[type="radio"]').forEach(input => {
    input.addEventListener('change', () => {
        // Remove .selected class from all labels
        document.querySelectorAll('.priority-btn').forEach(label => label.classList.remove('selected'));
        // Add .selected to the label of the checked input
        if (input.checked) {
        input.parentElement.classList.add('selected');
        }
    });
    });

    // On page load, set the .selected class correctly if any input is pre-checked
    window.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.priority-btn input[type="radio"]').forEach(input => {
        if (input.checked) {
        input.parentElement.classList.add('selected');
        }
    });
});

/*  */


/*  */

document.querySelectorAll('.recurring-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        // Remove selected class from all recurring buttons
        document.querySelectorAll('.recurring-btn').forEach(b => b.classList.remove('selected'));
        // Add selected class to clicked button
        btn.classList.add('selected');
        // Also check its input radio
        btn.querySelector('input[type="radio"]').checked = true;
    });
});


function fetchReminders() {
    fetch('/get_reminders')
    .then(response => response.json())
    .then(data => {
        const reminders = data.reminders || [];
        const count = reminders.length;
        const countBadge = document.getElementById('reminder-count');
        const reminderList = document.getElementById('reminder-list');

        // Update count
        if (count > 0) {
            countBadge.textContent = count;
            countBadge.style.display = 'inline-block';
        } else {
            countBadge.style.display = 'none';
        }

        // Update dropdown content
        reminderList.innerHTML = '';
        reminders.forEach(task => {
            const li = document.createElement('li');
            const due = new Date(task.reminder_datetime).toLocaleString();
            li.textContent = `🔸 ${task.description} – Due: ${due}`;
            li.style.padding = "5px 0";
            reminderList.appendChild(li);
        });
    });
}

// Toggle dropdown on bell click
document.addEventListener('DOMContentLoaded', function() {
    const icon = document.getElementById('reminder-icon');
    const dropdown = document.getElementById('reminder-dropdown');

    icon.addEventListener('click', function() {
        dropdown.style.display = dropdown.style.display === 'block' ? 'none' : 'block';
    });

    // Optional: Close dropdown if click outside
    document.addEventListener('click', function(e) {
        if (!document.getElementById('reminder-wrapper').contains(e.target)) {
            dropdown.style.display = 'none';
        }
    });

    fetchReminders(); // initial load
    setInterval(fetchReminders, 60000); // refresh every minute
});

document.getElementById("priorityFilter").addEventListener("change", function () {
    const selected = this.value;
    const tasks = document.querySelectorAll("#taskList .task-row");

    tasks.forEach(task => {
        if (selected === "all") {
            task.style.display = "flex";
        } else {
            task.style.display = task.classList.contains(selected) ? "flex" : "none";
        }
    });
});

document.getElementById("priorityFilter").addEventListener("change", function () {
    const selected = this.value;
    const tasks = document.querySelectorAll("#taskList1 .task-row");

    tasks.forEach(task => {
        if (selected === "all") {
            task.style.display = "flex";
        } else {
            task.style.display = task.classList.contains(selected) ? "flex" : "none";
        }
    });
});