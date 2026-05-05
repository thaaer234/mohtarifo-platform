document.addEventListener('DOMContentLoaded', () => {
    // Custom Cursor
    const cursor = document.querySelector('.cursor');
    const follower = document.querySelector('.cursor-follower');
    let mouseX = 0, mouseY = 0;
    let posX = 0, posY = 0;

    document.addEventListener('mousemove', (e) => {
        mouseX = e.clientX;
        mouseY = e.clientY;
        
        cursor.style.transform = `translate3d(${mouseX}px, ${mouseY}px, 0)`;
    });

    function animateCursor() {
        posX += (mouseX - posX) / 8;
        posY += (mouseY - posY) / 8;
        
        follower.style.transform = `translate3d(${posX - 15}px, ${posY - 15}px, 0)`;
        requestAnimationFrame(animateCursor);
    }
    animateCursor();

    // Hover effect for links
    const links = document.querySelectorAll('a, button, .feature-card');
    links.forEach(link => {
        link.addEventListener('mouseenter', () => {
            follower.style.transform += ' scale(1.5)';
            follower.style.background = 'rgba(255, 225, 53, 0.1)';
            follower.style.borderColor = 'var(--banana-yellow)';
        });
        link.addEventListener('mouseleave', () => {
            follower.style.transform = follower.style.transform.replace(' scale(1.5)', '');
            follower.style.background = 'transparent';
            follower.style.borderColor = 'var(--text-dark)';
        });
    });

    // Navbar Scroll Effect
    const navbar = document.querySelector('.navbar');
    window.addEventListener('scroll', () => {
        if (window.scrollY > 50) {
            navbar.classList.add('scrolled');
        } else {
            navbar.classList.remove('scrolled');
        }
    });

    // Reveal on Scroll
    const observerOptions = {
        threshold: 0.1
    };

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('active');
            }
        });
    }, observerOptions);

    document.querySelectorAll('.reveal, .reveal-text, .fade-up').forEach(el => {
        observer.observe(el);
    });

    // Simple Parallax for Hero
    const parallaxImg = document.querySelector('.parallax-img');
    window.addEventListener('scroll', () => {
        const scrolled = window.pageYOffset;
        if (parallaxImg) {
            parallaxImg.style.transform = `scale(1.1) translateY(${scrolled * 0.1}px)`;
        }
    });

    // Text Split Animation (Simple version)
    // In a real agency site we'd use SplitType + GSAP
    // Here we just use the reveal-text class already handled by the observer
});
