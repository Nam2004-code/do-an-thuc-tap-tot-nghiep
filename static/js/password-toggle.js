document.addEventListener('DOMContentLoaded', function() {
    const pwInputs = document.querySelectorAll('input[type="password"]');
    pwInputs.forEach(function(input) {
        // Avoid adding multiple toggles for same input
        if (input.dataset.hasToggle === 'true') return;
        input.dataset.hasToggle = 'true';

        // Ensure the parent can position absolute children
        const parent = input.parentElement;
        if (parent) parent.style.position = parent.style.position || 'relative';

        // Make room on the right for the toggle
        const currentPaddingRight = parseInt(window.getComputedStyle(input).paddingRight) || 0;
        input.style.paddingRight = (currentPaddingRight + 36) + 'px';

        // Create button
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'password-toggle-btn';
        btn.setAttribute('aria-label', 'Toggle password visibility');
        btn.style.position = 'absolute';
        btn.style.top = '50%';
        btn.style.right = '10px';
        btn.style.transform = 'translateY(-50%)';
        btn.style.border = 'none';
        btn.style.background = 'transparent';
        btn.style.cursor = 'pointer';
        btn.style.fontSize = '1.05rem';
        btn.style.color = '#6c757d';
        btn.style.padding = '0';
        btn.innerHTML = '<i class="fas fa-eye"></i>';

        btn.addEventListener('click', function(e) {
            e.preventDefault();
            if (input.type === 'password') {
                input.type = 'text';
                btn.innerHTML = '<i class="fas fa-eye-slash"></i>';
            } else {
                input.type = 'password';
                btn.innerHTML = '<i class="fas fa-eye"></i>';
            }
        });

        // Insert the button after the input
        parent.appendChild(btn);
    });
});
