import Cocoa
import WebKit
import Security

// A native macOS desktop shell for the existing private VoiceOS Python runtime.
// Never place the OpenAI API key in argv, URLs, logs, or the .app bundle.
final class UltronApp: NSObject, NSApplicationDelegate, WKNavigationDelegate {
    private var window: NSWindow!
    private var webView: WKWebView!
    private var label: NSTextField!
    private var process: Process?
    private var pipe: Pipe?
    private var pending = ""
    private var statusItem: NSStatusItem?
    private var didLoad = false
    private var closing = false
    private var settingsItem: NSMenuItem?
    private let keychainService = "com.ultron.voiceos.desktop"
    private let keychainAccount = "OPENAI_API_KEY"

    func applicationDidFinishLaunching(_ notification: Notification) {
        NSApp.setActivationPolicy(.regular)
        installMainMenu()
        createWindow()
        createStatusItem()
        NSApp.activate(ignoringOtherApps: true)
        if credentials() == nil {
            showCredentialPrompt(firstRun: true)
        } else {
            startVoiceOS()
        }
    }

    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool {
        // A desktop companion remains available from the menu bar when the
        // window is closed. Quit via the Dock or status-menu Quit.
        return false
    }

    func applicationWillTerminate(_ notification: Notification) {
        closing = true
        stopWorker()
    }

    private func installMainMenu() {
        let bar = NSMenu()
        let app = NSMenu()
        let appItem = NSMenuItem()
        appItem.submenu = app
        bar.addItem(appItem)
        app.addItem(NSMenuItem(title: "About Ultron", action: #selector(about), keyEquivalent: ""))
        app.addItem(NSMenuItem(title: "API Key Settings…", action: #selector(editCredentials), keyEquivalent: ","))
        app.addItem(NSMenuItem(title: "Restart VoiceOS", action: #selector(restartWorker), keyEquivalent: "r"))
        app.addItem(NSMenuItem(title: "Show Ultron", action: #selector(showWindow), keyEquivalent: "1"))
        app.addItem(NSMenuItem.separator())
        app.addItem(NSMenuItem(title: "Quit Ultron", action: #selector(quitApp), keyEquivalent: "q"))
        NSApp.mainMenu = bar
        for menuItem in app.items { menuItem.target = self }
    }

    private func createWindow() {
        let rect = NSRect(x: 0, y: 0, width: 560, height: 640)
        window = NSWindow(contentRect: rect,
                          styleMask: [.titled, .closable, .miniaturizable, .resizable, .fullSizeContentView],
                          backing: .buffered, defer: false)
        window.title = "ULTRON · Cognitive Cortex"
        window.center()
        window.minSize = NSSize(width: 440, height: 480)
        window.backgroundColor = NSColor(red: 0.015, green: 0.045, blue: 0.075, alpha: 1)
        window.titlebarAppearsTransparent = true
        window.titleVisibility = .hidden
        let configuration = WKWebViewConfiguration()
        configuration.websiteDataStore = .nonPersistent()
        webView = WKWebView(frame: rect, configuration: configuration)
        webView.navigationDelegate = self
        webView.setValue(false, forKey: "drawsBackground")
        window.contentView = webView
        window.makeKeyAndOrderFront(nil)
        showLaunchState("INITIALIZING ULTRON", "Starting private VoiceOS runtime…")
    }

    private func createStatusItem() {
        statusItem = NSStatusBar.system.statusItem(withLength: NSStatusItem.variableLength)
        statusItem?.button?.title = "◇ ULTRON"
        let menu = NSMenu()
        let show = NSMenuItem(title: "Show Neural Core", action: #selector(showWindow), keyEquivalent: "")
        let restart = NSMenuItem(title: "Restart Agent", action: #selector(restartWorker), keyEquivalent: "")
        let settings = NSMenuItem(title: "API Key Settings…", action: #selector(editCredentials), keyEquivalent: "")
        let quit = NSMenuItem(title: "Quit Ultron", action: #selector(quitApp), keyEquivalent: "")
        for item in [show, restart, settings, quit] { item.target = self; menu.addItem(item) }
        statusItem?.menu = menu
    }

    private func showLaunchState(_ title: String, _ detail: String) {
        // Only constant, internal strings reach this HTML. Never interpolate
        // user requests, returned model content or API credentials.
        let page = """
        <!doctype html><html><head><meta name="viewport" content="width=device-width, initial-scale=1">
        <style>html,body{height:100%;margin:0;background:#030b15;color:#9bf8f5;font-family:-apple-system,system-ui}
        main{height:100%;display:flex;align-items:center;justify-content:center;flex-direction:column;text-align:center}
        .ring{width:156px;height:156px;border:1px solid #2a8dab;border-radius:50%;box-shadow:0 0 38px #16476c;
        display:flex;align-items:center;justify-content:center;font-size:60px;margin-bottom:30px;color:#80edee}
        h1{font-size:15px;letter-spacing:.24em;font-weight:600}p{color:#7f9aaa;font-size:13px;max-width:310px;line-height:1.8}</style>
        </head><body><main><div class="ring">◇</div><h1>\(title)</h1><p>\(detail)</p></main></body></html>
        """
        webView.loadHTMLString(page, baseURL: nil)
    }

    private func credentials() -> String? {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: keychainService,
            kSecAttrAccount as String: keychainAccount,
            kSecReturnData as String: true,
            kSecMatchLimit as String: kSecMatchLimitOne
        ]
        var result: CFTypeRef?
        let status = SecItemCopyMatching(query as CFDictionary, &result)
        if status != errSecSuccess { return nil }
        guard let data = result as? Data, let value = String(data: data, encoding: .utf8),
              !value.isEmpty else { return nil }
        return value
    }

    private func storeCredentials(_ value: String) -> Bool {
        let base: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: keychainService,
            kSecAttrAccount as String: keychainAccount
        ]
        let secret = Data(value.utf8)
        let update = SecItemUpdate(base as CFDictionary,
                                   [kSecValueData as String: secret] as CFDictionary)
        if update == errSecSuccess { return true }
        if update != errSecItemNotFound { return false }
        var creation = base
        creation[kSecValueData as String] = secret
        creation[kSecAttrAccessible as String] = kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly
        return SecItemAdd(creation as CFDictionary, nil) == errSecSuccess
    }

    private func showCredentialPrompt(firstRun: Bool) {
        let alert = NSAlert()
        alert.messageText = firstRun ? "Connect Ultron to OpenAI" : "Update API Key"
        alert.informativeText = "Your OpenAI Platform API key is stored in macOS Keychain and passed only to the local VoiceOS process. No key is saved in the application bundle."
        let field = NSSecureTextField(frame: NSRect(x: 0, y: 0, width: 380, height: 26))
        field.placeholderString = "sk-…"
        alert.accessoryView = field
        alert.addButton(withTitle: "Save & Start")
        alert.addButton(withTitle: "Cancel")
        NSApp.activate(ignoringOtherApps: true)
        if alert.runModal() != .alertFirstButtonReturn {
            if firstRun { showLaunchState("SETUP REQUIRED", "Open ULTRON → API Key Settings to continue.") }
            return
        }
        let value = field.stringValue.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !value.isEmpty, !value.contains("\n") else {
            showError("Please enter a valid nonempty API key.")
            return
        }
        guard storeCredentials(value) else {
            showError("Could not save the key in macOS Keychain.")
            return
        }
        restartWorker(nil)
    }

    @objc private func editCredentials(_ sender: Any?) { showCredentialPrompt(firstRun: false) }
    @objc private func restartWorker(_ sender: Any?) {
        stopWorker()
        startVoiceOS()
    }
    @objc private func showWindow(_ sender: Any?) {
        window.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)
    }
    @objc private func quitApp(_ sender: Any?) { NSApp.terminate(nil) }
    @objc private func about(_ sender: Any?) {
        let alert = NSAlert()
        alert.messageText = "ULTRON VoiceOS Desktop"
        alert.informativeText = "Local 3D Cognitive Cortex • GLACIAL voice • DSH Agent\nRuns on your Mac; no external dashboard server."
        alert.runModal()
    }
    private func showError(_ message: String) {
        showLaunchState("ACTION REQUIRED", "Use the ULTRON menu to check settings or restart.")
        let alert = NSAlert()
        alert.messageText = "Ultron could not start"
        alert.informativeText = message
        alert.alertStyle = .warning
        alert.addButton(withTitle: "OK")
        alert.runModal()
    }

    private func startVoiceOS() {
        guard !closing else { return }
        guard let key = credentials() else { showCredentialPrompt(firstRun: true); return }
        guard let harness = Bundle.main.object(forInfoDictionaryKey: "UltronHarnessPath") as? String,
              let python = Bundle.main.object(forInfoDictionaryKey: "UltronPythonPath") as? String else {
            showError("Installation settings are incomplete. Rebuild the app.")
            return
        }
        let pythonURL = URL(fileURLWithPath: python)
        let rootURL = URL(fileURLWithPath: harness)
        guard FileManager.default.isExecutableFile(atPath: python),
              FileManager.default.fileExists(atPath: rootURL.appendingPathComponent("voiceos/core.py").path) else {
            showError("Python environment or project moved. Re-run build-macos-app.sh from the project folder.")
            return
        }
        didLoad = false
        pending = ""
        showLaunchState("INITIALIZING ULTRON", "Preparing GLACIAL voice and the neural interface…")
        let worker = Process()
        worker.executableURL = pythonURL
        worker.currentDirectoryURL = rootURL
        worker.arguments = ["-u", "voiceos/core.py", "--hands-free",
                            "--tts", "openai", "--persona", "glacial", "--reply-language", "en",
                            "--robotic", "55", "--dashboard", "--dashboard-port", "0"]
        var environment = ProcessInfo.processInfo.environment
        environment["OPENAI_API_KEY"] = key
        environment["PATH"] = "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:" + (environment["PATH"] ?? "")
        environment["PYTHONUNBUFFERED"] = "1"
        environment["NO_PROXY"] = "localhost,127.0.0.1,::1"
        worker.environment = environment
        let combined = Pipe()
        worker.standardOutput = combined
        worker.standardError = combined
        pipe = combined
        process = worker
        combined.fileHandleForReading.readabilityHandler = { [weak self] handle in
            let bytes = handle.availableData
            if bytes.isEmpty { return }
            guard let chunk = String(data: bytes, encoding: .utf8) else { return }
            DispatchQueue.main.async { self?.consumeLog(chunk) }
        }
        worker.terminationHandler = { [weak self, weak worker] finished in
            DispatchQueue.main.async {
                guard let self = self, !self.closing, self.process === worker else { return }
                self.pipe?.fileHandleForReading.readabilityHandler = nil
                self.process = nil
                self.showLaunchState("VOICEOS STOPPED", "Open ULTRON → Restart VoiceOS to try again.")
                self.showError("VoiceOS exited (code \(finished.terminationStatus)). Verify your SDK setup, network access and microphone permission. To diagnose, run core.py --doctor in the existing environment.")
            }
        }
        do {
            try worker.run()
        } catch {
            combined.fileHandleForReading.readabilityHandler = nil
            process = nil
            showError("Unable to start local Python VoiceOS runtime: \(error.localizedDescription)")
        }
    }

    private func consumeLog(_ chunk: String) {
        // Never save or echo spoken words / agent responses to persistent logs.
        pending += chunk
        if pending.count > 16000 { pending = String(pending.suffix(2000)) }
        while let end = pending.firstIndex(of: "\n") {
            let line = String(pending[..<end])
            pending = String(pending[pending.index(after: end)...])
            let prefix = "[VoiceOS] Cognitive dashboard: http://127.0.0.1:"
            if line.hasPrefix(prefix), !didLoad {
                let suffix = String(line.dropFirst(prefix.count))
                if let port = Int(suffix), port > 0 && port < 65536 {
                    didLoad = true
                    webView.load(URLRequest(url: URL(string: "http://127.0.0.1:\(port)/")!))
                }
            }
        }
    }

    private func stopWorker() {
        guard let worker = process else { return }
        pipe?.fileHandleForReading.readabilityHandler = nil
        worker.terminationHandler = nil
        process = nil
        if worker.isRunning {
            worker.terminate()
            // VoiceOS may be in the middle of an external model request;
            // allow cleanup without freezing the macOS UI thread.
            DispatchQueue.global(qos: .utility).async {
                worker.waitUntilExit()
            }
        }
        pipe = nil
    }
}

let app = NSApplication.shared
let delegate = UltronApp()
app.delegate = delegate
app.run()
