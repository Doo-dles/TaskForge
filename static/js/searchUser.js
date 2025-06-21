// Get the modal and button
var modal = document.getElementById("taskModal");
var btn = document.getElementById("openModalBtn");
var span = document.getElementsByClassName("close")[0];
// When the user clicks the button, open the modal
btn.onclick = function() {
    modal.style.display = "block";
}

    // When the user clicks on <span> (x), close the modal
    span.onclick = function() {
        modal.style.display = "none";
    }

    // When the user clicks anywhere outside of the modal, close it
    window.onclick = function(event) {
        if (event.target == modal) {
            modal.style.display = "none";
        }
    }

    // Fetch users dynamically for the search functionality
    document.addEventListener('DOMContentLoaded', function() {
        const users = { all_users,tojson };
        const userSelect = document.getElementById('shared_users');

        // Initialize the select input with users
        users.forEach(function(user) {
            let option = document.createElement("option");
            option.value = user.id;
            option.textContent = user.username;
            userSelect.appendChild(option);
        });

        // Initialize the search feature for user select
        $('#shared_users').select2({
            placeholder: 'Search users...',
            allowClear: true,
            width: '100%'
        });
    });