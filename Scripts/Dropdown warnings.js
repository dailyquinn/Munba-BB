document.addEventListener("DOMContentLoaded", () => {
    const dropdown = document.getElementById("location");
    const warning = document.getElementById("location-warning");
    const TenerifisWarning = document.getElementById("Tenerifis-warning");
  
    // Ensure all elements exist before adding listeners
    if (dropdown && warning && TenerifisWarning) {
      dropdown.addEventListener("change", () => {
        // Hide all warnings by default
        warning.style.display = "none";
        TenerifisWarning.style.display = "none";
  
        const selectedOption = dropdown.options[dropdown.selectedIndex];
        if (!selectedOption || !dropdown.value) return;

        const fee = selectedOption ? parseFloat(selectedOption.getAttribute('data-fee') || '0') : 0;
        if (fee > 0) {
          TenerifisWarning.textContent = `Selecting this will deduct ${fee.toLocaleString()} ISK from the payout.`;
          TenerifisWarning.style.display = "inline-block";
        }
      });
      dropdown.dispatchEvent(new Event("change")); // Trigger change event on page load to set initial state
    }
});