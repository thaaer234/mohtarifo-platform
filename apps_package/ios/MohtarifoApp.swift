import SwiftUI
import WebKit

@main
struct ProAcademyApp: App {
    var body: some Scene {
        WindowGroup {
            ProContentView()
        }
    }
}

struct ProContentView: View {
    @State private var isScreenRecording = false
    let officialURL = URL(string: "https://pro-academy.pro/")!

    var body: some View {
        ZStack {
            // المتصفح المحمي (WebView)
            ProProtectedWebView(url: officialURL)
                .opacity(isScreenRecording ? 0 : 1)

            // شاشة الحظر الذهبية الملوكية عند تسجيل الشاشة أو محاولة التقاطها
            if isScreenRecording {
                ProSecurityBlockScreen()
            }
        }
        .onReceive(NotificationCenter.default.publisher(for: UIScreen.capturedDidChangeNotification)) { _ in
            withAnimation(.easeInOut(duration: 0.25)) {
                isScreenRecording = UIScreen.main.isCaptured
            }
        }
    }
}

// واجهة الحظر الرسمية المتوافقة مع ألوان المنصة (Gold & Dark)
struct ProSecurityBlockScreen: View {
    var body: some View {
        ZStack {
            Color(red: 0.03, green: 0.03, blue: 0.03).ignoresSafeArea()

            VStack(spacing: 24) {
                ZStack {
                    Circle()
                        .fill(Color(red: 0.83, green: 0.69, blue: 0.22).opacity(0.15))
                        .frame(width: 90, height: 90)
                    
                    Image(systemName: "shield.slash.fill")
                        .font(.system(size: 42))
                        .foregroundColor(Color(red: 0.83, green: 0.69, blue: 0.22))
                }

                Text("التقاط وتسجيل الشاشة محظور")
                    .font(.custom("Cairo-Bold", size: 24))
                    .foregroundColor(Color(red: 0.95, green: 0.84, blue: 0.57))

                Text("لحماية حقوق الملكية الفكرية لمنصة محترفو التعليم، تم إيقاف عرض المحتوى فوراً أثناء تفعيل تسجيل الشاشة.")
                    .font(.custom("Cairo-Regular", size: 15))
                    .foregroundColor(Color(red: 0.8, green: 0.8, blue: 0.8))
                    .multilineTextAlignment(.center)
                    .padding(.horizontal, 32)
                    .lineSpacing(6)

                Text("🛡️ منصة محترفو التعليم - Pro Academy")
                    .font(.custom("Cairo-Regular", size: 12))
                    .foregroundColor(Color(red: 0.83, green: 0.69, blue: 0.22))
                    .padding(.top, 10)
            }
        }
    }
}

// WebView الأصلي مع حقن حماية الكوكيز وإلغاء القوائم الجانبية
struct ProProtectedWebView: UIViewRepresentable {
    let url: URL

    func makeUIView(context: Context) -> WKWebView {
        let configuration = WKWebViewConfiguration()
        configuration.allowsInlineMediaPlayback = true
        
        let webView = WKWebView(frame: .zero, configuration: configuration)
        webView.scrollView.bounces = false
        webView.load(URLRequest(url: url))
        return webView
    }

    func updateUIView(_ uiView: WKWebView, context: Context) {}
}
