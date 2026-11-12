import Cocoa
import WebKit

/// A deliberately small GPU-rendered floating orb. Unlike the full dashboard,
/// the orb doesn't consume remote messages or SDK tool contents.
final class UltronOrb: NSObject {
    private let panel: NSPanel
    private let webView: WKWebView
    private let onOpen: () -> Void
    private var lastState = "paused"
    var visible: Bool { panel.isVisible }

    init(onOpen: @escaping () -> Void) {
        self.onOpen = onOpen
        let rect = NSRect(x: 0, y: 0, width: 144, height: 144)
        panel = NSPanel(
            contentRect: rect,
            styleMask: [.borderless, .nonactivatingPanel],
            backing: .buffered, defer: false
        )
        panel.isOpaque = false
        panel.backgroundColor = .clear
        panel.hasShadow = false
        panel.level = .floating
        panel.hidesOnDeactivate = false
        panel.collectionBehavior = [.canJoinAllSpaces, .fullScreenAuxiliary]
        panel.isMovableByWindowBackground = true
        let config = WKWebViewConfiguration()
        config.websiteDataStore = .nonPersistent()
        webView = WKWebView(frame: rect, configuration: config)
        webView.underPageBackgroundColor = .clear
        webView.autoresizingMask = [.width, .height]
        panel.contentView = webView
        super.init()

        let gesture = NSClickGestureRecognizer(target: self, action: #selector(openMain))
        webView.addGestureRecognizer(gesture)
        if let url = Bundle.main.url(forResource: "Orb", withExtension: "html"),
           let html = try? String(contentsOf: url, encoding: .utf8) {
            webView.loadHTMLString(html, baseURL: nil)
        } else {
            webView.loadHTMLString("<html><body style='background:transparent;color:#65f2ef;font-size:60px;text-align:center'>◇</body></html>", baseURL: nil)
        }
        if let screen = NSScreen.main?.visibleFrame {
            panel.setFrameOrigin(NSPoint(x: screen.maxX - 176, y: screen.minY + 80))
        }
    }

    @objc private func openMain() { onOpen() }

    func show() { panel.orderFrontRegardless() }
    func hide() { panel.orderOut(nil) }

    func setState(_ state: String) {
        guard state != lastState else { return }
        lastState = state
        let literal = state == "listening" ? "listening" :
            state == "thinking" ? "thinking" :
            state == "speaking" ? "speaking" :
            state == "ready" ? "ready" : "paused"
        webView.evaluateJavaScript("window.ultronOrbState && window.ultronOrbState('\(literal)');", completionHandler: nil)
    }
}
