// This script manages the display of warning messages based on the selected
// option in the location dropdown on the quote calculator page.
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
  
        if (dropdown.value === "Tenerifis L/XL Structure") {
          TenerifisWarning.style.display = "block"; // Show specific Tenerifis warning
        } else if (dropdown.value !== "UALX-3" && dropdown.value !== "ABE-M2" && dropdown.value) {
          warning.style.display = "block"; // Show generic warning for other non-standard locations
        }
      });
      dropdown.dispatchEvent(new Event("change")); // Trigger change event on page load to set initial state
    }
});