import SwiftUI
import WebKit

struct ContentView: View {
    @EnvironmentObject private var runtime: BackendRuntime

    var body: some View {
        switch runtime.status {
        case .starting:
            StatusScreen(message: "PostgreSQL과 MongoDB를 시작하는 중입니다…")
        case .failed(let message):
            StatusScreen(title: "문제가 발생했습니다", message: message, isError: true)
        case .ready:
            WebView(url: BackendRuntime.baseURL)
        }
    }
}

private struct StatusScreen: View {
    var title: String = "DB Playground 준비 중"
    let message: String
    var isError: Bool = false

    var body: some View {
        VStack(spacing: 16) {
            if !isError {
                ProgressView()
            }
            Text(title)
                .font(.headline)
            Text(message)
                .font(.callout)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
                .frame(maxWidth: 420)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }
}

private struct WebView: NSViewRepresentable {
    let url: URL

    func makeNSView(context: Context) -> WKWebView {
        let view = WKWebView()
        view.load(URLRequest(url: url))
        return view
    }

    func updateNSView(_ nsView: WKWebView, context: Context) {}
}
