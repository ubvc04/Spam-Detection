// Theme Toggle Functionality with Local Storage
(function() {
    'use strict';
    
    // Get theme from localStorage or default to 'light'
    const currentTheme = localStorage.getItem('theme') || 'light';
    
    // Apply theme on page load
    document.documentElement.setAttribute('data-theme', currentTheme);
    
    // Wait for DOM to be ready
    document.addEventListener('DOMContentLoaded', function() {
        // Create theme toggle button
        const toggleButton = document.createElement('button');
        toggleButton.className = 'theme-toggle';
        toggleButton.setAttribute('aria-label', 'Toggle theme');
        toggleButton.innerHTML = currentTheme === 'dark' 
            ? '<i class="fas fa-sun"></i>' 
            : '<i class="fas fa-moon"></i>';
        
        document.body.appendChild(toggleButton);
        
        // Toggle theme on button click
        toggleButton.addEventListener('click', function() {
            const currentTheme = document.documentElement.getAttribute('data-theme');
            const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
            
            // Apply theme with animation
            document.documentElement.style.transition = 'background-color 0.5s ease, color 0.5s ease';
            document.documentElement.setAttribute('data-theme', newTheme);
            localStorage.setItem('theme', newTheme);
            
            // Update button icon with rotation animation
            toggleButton.style.transform = 'rotate(360deg)';
            setTimeout(() => {
                toggleButton.innerHTML = newTheme === 'dark' 
                    ? '<i class="fas fa-sun"></i>' 
                    : '<i class="fas fa-moon"></i>';
                toggleButton.style.transform = 'rotate(0deg)';
            }, 150);
            
            // Remove transition after animation
            setTimeout(() => {
                document.documentElement.style.transition = '';
            }, 500);
        });
        
        // Optional: Listen to system theme changes
        if (window.matchMedia) {
            const darkModeQuery = window.matchMedia('(prefers-color-scheme: dark)');
            darkModeQuery.addEventListener('change', function(e) {
                // Only auto-switch if user hasn't manually set a preference
                if (!localStorage.getItem('theme')) {
                    const newTheme = e.matches ? 'dark' : 'light';
                    document.documentElement.setAttribute('data-theme', newTheme);
                    toggleButton.innerHTML = newTheme === 'dark' 
                        ? '<i class="fas fa-sun"></i>' 
                        : '<i class="fas fa-moon"></i>';
                }
            });
        }
    });
})();
