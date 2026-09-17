/**
 * Mohtarifo Platform Official Security & Screen Capture Protection Guard
 * متوافق مع الهوية البصرية الرسمية لمنصة محترفو التعليم (Gold & Royal Dark)
 */
(function () {
    'use strict';

    const securityOverlayId = 'mohtarifo-anti-capture-overlay';

    function createSecurityOverlay() {
        if (document.getElementById(securityOverlayId)) return;

        const overlay = document.createElement('div');
        overlay.id = securityOverlayId;
        overlay.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            background: #080808;
            color: #ffffff;
            z-index: 999999999;
            display: none;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            text-align: center;
            padding: 24px;
            font-family: 'Cairo', -apple-system, BlinkMacSystemFont, sans-serif;
            direction: rtl;
            box-sizing: border-box;
            user-select: none;
            backdrop-filter: blur(25px);
        `;

        overlay.innerHTML = `
            <div style="background: rgba(15, 15, 15, 0.95); border: 2px solid #d4af37; border-radius: 28px; padding: 45px 35px; max-width: 520px; box-shadow: 0 25px 50px rgba(212, 175, 55, 0.25); text-align: center;">
                <div style="width: 80px; height: 80px; background: rgba(212, 175, 55, 0.15); border: 1px solid #d4af37; border-radius: 50%; display: flex; align-items: center; justify-content: center; margin: 0 auto 20px;">
                    <svg style="width: 44px; height: 44px; fill: none; stroke: #d4af37; stroke-width: 2.2;" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                    </svg>
                </div>
                <h2 style="font-size: 24px; font-weight: 800; margin-bottom: 12px; color: #f1d592;">التقاط وتسجيل الشاشة محظور</h2>
                <p style="font-size: 15px; color: #cbd5e1; line-height: 1.7; margin-bottom: 24px;">
                    لحماية حقوق الملكية الفكرية لمنصة <b>محترفو التعليم</b>، لا يُسمح بتسجيل الفيديو أو أخذ لقطات شاشة داخل التطبيق.
                </p>
                <div style="font-size: 13px; color: #d4af37; background: rgba(212, 175, 55, 0.08); padding: 12px 18px; border-radius: 14px; border: 1px dashed rgba(212, 175, 55, 0.3);">
                    🛡️ منصة محترفو التعليم - نظام الحماية والأمان النشط
                </div>
            </div>
        `;

        document.body.appendChild(overlay);
    }

    function showSecurityWarning() {
        createSecurityOverlay();
        const overlay = document.getElementById(securityOverlayId);
        if (overlay) {
            overlay.style.display = 'flex';
        }
    }

    function hideSecurityWarning() {
        const overlay = document.getElementById(securityOverlayId);
        if (overlay) {
            overlay.style.display = 'none';
        }
    }

    // مراقبة مفاتيح لقطات الشاشة
    window.addEventListener('keyup', function (e) {
        if (e.key === 'PrintScreen') {
            try { navigator.clipboard.writeText(''); } catch(err){}
            showSecurityWarning();
            setTimeout(hideSecurityWarning, 3500);
        }
    });

    window.addEventListener('keydown', function (e) {
        if (e.key === 'PrintScreen' || e.keyCode === 44) {
            e.preventDefault();
            try { navigator.clipboard.writeText(''); } catch(err){}
            showSecurityWarning();
            setTimeout(hideSecurityWarning, 3500);
            return false;
        }

        if (e.metaKey && e.shiftKey && ['3', '4', '5'].includes(e.key)) {
            e.preventDefault();
            showSecurityWarning();
            setTimeout(hideSecurityWarning, 3500);
            return false;
        }

        if ((e.key === 's' || e.key === 'S') && e.shiftKey && (e.metaKey || e.ctrlKey)) {
            showSecurityWarning();
            setTimeout(hideSecurityWarning, 3500);
        }

        if ((e.ctrlKey || e.metaKey) && ['p', 'P', 's', 'S', 'u', 'U'].includes(e.key)) {
            e.preventDefault();
            return false;
        }
    });

    document.addEventListener('contextmenu', function (e) {
        e.preventDefault();
        return false;
    });

    window.addEventListener('blur', function () {
        showSecurityWarning();
    });

    window.addEventListener('focus', function () {
        hideSecurityWarning();
    });

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', createSecurityOverlay);
    } else {
        createSecurityOverlay();
    }
})();
