/* static/js/ui.js */
document.addEventListener('DOMContentLoaded', () => {
    const html = document.documentElement;
    const body = document.body;

    // ---------- Lucide Icons ----------
    const refreshIcons = () => {
        if (typeof lucide !== 'undefined') {
            lucide.createIcons();
        }
    };
    refreshIcons();

    // ---------- Theme handling ----------
    const setTheme = (theme, options = {}) => {
        const shouldAnimate = options.animate === true;
        if (shouldAnimate) {
            html.classList.add('theme-switching');
        }

        if (theme === 'dark') {
            html.classList.add('dark-theme');
        } else {
            html.classList.remove('dark-theme');
        }
        document.cookie = `theme=${theme};path=/;max-age=31536000`;
        localStorage.setItem('theme', theme);
        updateThemeIcons(theme);

        if (shouldAnimate) {
            window.setTimeout(() => html.classList.remove('theme-switching'), 220);
        }
    };

    const updateThemeIcons = (theme) => {
        const icons = document.querySelectorAll('#theme-icon, #theme-icon-profile');
        icons.forEach(icon => {
            icon.setAttribute('data-lucide', theme === 'dark' ? 'sun' : 'moon');
        });
        refreshIcons();
    };

    const saved = document.cookie.split('; ').find(row => row.startsWith('theme='));
    const savedLocal = localStorage.getItem('theme');
    const defaultTheme = saved ? saved.split('=')[1] : (savedLocal ? savedLocal : 'light');
    
    setTheme(defaultTheme);

    // Theme Toggle Listeners
    const toggles = document.querySelectorAll('#theme-toggle, #theme-toggle-profile');
    toggles.forEach(t => {
        t.addEventListener('click', (e) => {
            e.preventDefault();
            const currentTheme = html.classList.contains('dark-theme') ? 'light' : 'dark';
            setTheme(currentTheme, { animate: true });
        });
    });

    // ---------- Mobile Menu Toggle (base.html handles some, but let's sync) ----------
    const menuToggle = document.getElementById('menu-toggle');
    const menuClose = document.getElementById('menu-close');
    const mobileMenu = document.getElementById('mobile-menu');

    if (menuToggle && mobileMenu) {
        menuToggle.addEventListener('click', () => {
            mobileMenu.classList.add('active');
            body.style.overflow = 'hidden';
        });
    }

    if (menuClose && mobileMenu) {
        menuClose.addEventListener('click', () => {
            mobileMenu.classList.remove('active');
            body.style.overflow = 'auto';
        });
    }

    // ---------- Scroll Effects ----------
    const scrollProgress = document.getElementById('scroll-progress-bar');
    const navbar = document.querySelector('.navbar');

    window.addEventListener('scroll', () => {
        const winScroll = body.scrollTop || html.scrollTop;
        const height = html.scrollHeight - html.clientHeight;
        const scrolled = (winScroll / height) * 100;
        
        if (scrollProgress) scrollProgress.style.width = scrolled + "%";
        
        if (navbar) {
            if (winScroll > 50) {
                navbar.classList.add('navbar-scrolled');
            } else {
                navbar.classList.remove('navbar-scrolled');
            }
        }
    });

    // ---------- Reveal on Scroll ----------
    const revealCallback = (entries, observer) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('reveal-active');
                observer.unobserve(entry.target);
            }
        });
    };

    const revealObserver = new IntersectionObserver(revealCallback, {
        threshold: 0.1
    });

    const revealElements = document.querySelectorAll('.reveal-up, .reveal-left, .reveal-right');
    revealElements.forEach(el => revealObserver.observe(el));

    // ---------- Mobile Sync ----------
    if (window.ReactNativeWebView) {
        window.ReactNativeWebView.postMessage(JSON.stringify({ type: 'page_ready' }));
    }

    // Final Lucide refresh to catch dynamic elements
    setTimeout(refreshIcons, 100);
});
