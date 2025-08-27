// This script injects a data privacy notice above the Microsoft SSO button
document.addEventListener('DOMContentLoaded', function() {
  // Function to check if we're on the login page
  function isLoginPage() {
    return window.location.pathname.includes('/login');
  }

  // Function to inject the privacy notice
  function injectPrivacyNotice() {
    // Check if we're on the login page
    if (!isLoginPage()) return;
    
    // Wait for the Microsoft SSO button to be rendered
    const checkInterval = setInterval(function() {
      const ssoButton = document.querySelector('a[href*="openid"]') || 
                        document.querySelector('button:has-text("Login with Microsoft SSO")') ||
                        Array.from(document.querySelectorAll('button')).find(el => el.textContent.includes('Microsoft SSO'));
      
      if (ssoButton) {
        clearInterval(checkInterval);
        
        // Create the privacy notice element
        const privacyNotice = document.createElement('div');
        privacyNotice.className = 'mb-4 mt-2 rounded-md border border-yellow-500 bg-yellow-50 p-3 text-sm text-gray-800 dark:border-yellow-600 dark:bg-yellow-900/30 dark:text-gray-200';
        privacyNotice.innerHTML = `
          <p class="font-semibold">⚠️ Important Data Privacy Notice</p>
          <p class="mt-1">
            Please do not upload, enter, or paste any patient information or other personal, confidential, or private data into this AI system. This chatbot is designed for general internal use and is not approved for handling protected health information (PHI) or any data subject to privacy regulations such as HIPAA, GDPR, or similar frameworks. By continuing, you acknowledge your responsibility to comply with BeiGene's data privacy and information security policies.
          </p>
        `;
        
        // Insert the privacy notice before the SSO button
        ssoButton.parentNode.insertBefore(privacyNotice, ssoButton);
      }
    }, 500); // Check every 500ms
  }

  // Run the injection function
  injectPrivacyNotice();
});
