import UIKit
import WebKit

class ViewController: UIViewController, WKNavigationDelegate {

    private var webView: WKWebView!
    private var securityOverlayView: UIView!

    override func viewDidLoad() {
        super.viewDidLoad()
        
        setupWebView()
        setupSecurityOverlay()
        
        // 🔒 1. تفعيل الحماية ومنع تصوير وتسجيل الشاشة (Screen Mirroring / Recording)
        preventScreenshotAndRecording()
        
        // مراقبة بداية ونهاية تسجيل الشاشة في نظام iOS
        NotificationCenter.default.addObserver(
            self,
            selector: #selector(screenCaptureStatusChanged),
            name: UIScreen.capturedDidChangeNotification,
            object: nil
        )
    }

    private func setupWebView() {
        let config = WKWebViewConfiguration()
        webView = WKWebView(frame: view.bounds, configuration: config)
        webView.autoresizingMask = [.flexibleWidth, .flexibleHeight]
        webView.navigationDelegate = self
        
        if let url = URL(string: "https://mohtarifo.com") {
            let request = URLRequest(url: url)
            webView.load(request)
        }
        view.addSubview(webView)
    }

    private func setupSecurityOverlay() {
        // شاشة الحظر التحذيرية التي تظهر عند محاولة التسجيل
        securityOverlayView = UIView(frame: view.bounds)
        securityOverlayView.backgroundColor = UIColor(red: 0.05, green: 0.05, blue: 0.08, alpha: 1.0)
        securityOverlayView.autoresizingMask = [.flexibleWidth, .flexibleHeight]
        securityOverlayView.isHidden = true

        let label = UILabel()
        label.text = "⚠️ التقاط وتسجيل الشاشة محظور في هذا التطبيق"
        label.textColor = .systemRed
        label.font = UIFont.boldSystemFont(ofSize: 20)
        label.textAlignment = .center
        label.numberOfLines = 0
        label.translatesAutoresizingMaskIntoConstraints = false

        let subLabel = UILabel()
        subLabel.text = "لحماية خصوصية المحتوى التعليمي، لا يمكن متابعة التطبيق أثناء تفعيل تسجيل الشاشة."
        subLabel.textColor = .white
        subLabel.font = UIFont.systemFont(ofSize: 15)
        subLabel.textAlignment = .center
        subLabel.numberOfLines = 0
        subLabel.translatesAutoresizingMaskIntoConstraints = false

        let stack = UIStackView(arrangedSubviews: [label, subLabel])
        stack.axis = .vertical
        stack.spacing = 16
        stack.translatesAutoresizingMaskIntoConstraints = false

        securityOverlayView.addSubview(stack)
        view.addSubview(securityOverlayView)

        NSLayoutConstraint.activate([
            stack.centerXAnchor.constraint(equalTo: securityOverlayView.centerXAnchor),
            stack.centerYAnchor.constraint(equalTo: securityOverlayView.centerYAnchor),
            stack.leadingAnchor.constraint(equalTo: securityOverlayView.leadingAnchor, constant: 24),
            stack.trailingAnchor.constraint(equalTo: securityOverlayView.trailingAnchor, constant: -24)
        ])
    }

    private func preventScreenshotAndRecording() {
        // استخدام تقنية Secure Container عبر UITextField في iOS لإخفاء المحتوى تلقائياً من لقطات الشاشة
        let field = UITextField()
        field.isSecureTextEntry = true
        view.addSubview(field)
        field.centerYAnchor.constraint(equalTo: view.centerYAnchor).isActive = true
        field.centerXAnchor.constraint(equalTo: view.centerXAnchor).isActive = true
        view.layer.superlayer?.addSublayer(field.layer)
        field.layer.sublayers?.first?.addSublayer(view.layer)
    }

    @objc private func screenCaptureStatusChanged() {
        if UIScreen.main.isCaptured {
            // بدأ تسجيل الشاشة -> إخفاء المحتوى فوراً وإظهار شاشة الحظر
            securityOverlayView.isHidden = false
            webView.isHidden = true
        } else {
            // توقف التسجيل -> إعادة المحتوى
            securityOverlayView.isHidden = true
            webView.isHidden = false
        }
    }
}
