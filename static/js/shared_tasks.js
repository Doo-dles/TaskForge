const userData = document.getElementById('user-data').dataset.users;
const users = JSON.parse(userData);

const searchInput = document.getElementById('user-search');
const suggestionsBox = document.getElementById('user-suggestions');
const selectedUsersInput = document.getElementById('selected-users');
const selectedUserTags = document.getElementById('selected-user-tags');
const selectedUserIds = [];

searchInput.addEventListener('input', function () {
    const query = this.value.toLowerCase();
    suggestionsBox.innerHTML = '';

    if (!query) return;

    const matches = users.filter(user => user.username.toLowerCase().includes(query));
    matches.forEach(user => {
        const div = document.createElement('div');
        div.textContent = user.username;
        div.classList.add('suggestion-item');

        div.addEventListener('click', () => {
            if (!selectedUserIds.includes(user.id)) {
                selectedUserIds.push(user.id);
                selectedUsersInput.value = selectedUserIds.join(',');

                const tag = document.createElement('span');
                tag.textContent = user.username;
                tag.classList.add('user-tag');
                selectedUserTags.appendChild(tag);
            }

            searchInput.value = '';
            suggestionsBox.innerHTML = '';
        });

        suggestionsBox.appendChild(div);
    });
});

// Listen for changes on all priority radio buttons
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