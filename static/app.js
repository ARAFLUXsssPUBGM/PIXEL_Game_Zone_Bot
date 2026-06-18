// Shared JavaScript utilities for PIXEL Game Zone Web Apps
/**
 * Displays a toast notification on the screen.
 * @param {string} message - The message to show.
 * @param {'info'|'success'|'error'} type - The type of toast.
 */
function showToast(message, type = 'info') {
    const toast = document.getElementById('toast');
    if (!toast) return;
    // Reset classes
    toast.className = 'toast';
    
    // Add type class
    toast.classList.add(type);
    
    // Set message
    toast.innerHTML = `<span>${type === 'success' ? '✅' : type === 'error' ? '❌' : 'ℹ️'}</span> ${message}`;
    
    // Show toast
    toast.classList.add('show');
    
    // Hide toast after 3 seconds
    setTimeout(() => {
        toast.classList.remove('show');
    }, 3000);
}
