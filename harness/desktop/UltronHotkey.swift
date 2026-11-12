import Carbon
import Cocoa

/// Registers Option+Space without Accessibility or keyboard-monitoring
/// permission. Registration can fail if another app owns the combination.
final class UltronHotkey {
    private var hotKey: EventHotKeyRef?
    private var handler: EventHandlerRef?
    private let callback: () -> Void
    private static let signature: OSType = 0x554C5452 // "ULTR"
    private static let identifier: UInt32 = 1

    init(callback: @escaping () -> Void) {
        self.callback = callback
    }

    func register() -> Bool {
        let spec = EventTypeSpec(eventClass: OSType(kEventClassKeyboard),
                                 eventKind: UInt32(kEventHotKeyPressed))
        let result = InstallEventHandler(GetEventDispatcherTarget(),
            { (_, event, context) -> OSStatus in
                guard let context = context, let event = event else {
                    return OSStatus(eventNotHandledErr)
                }
                let owner = Unmanaged<UltronHotkey>.fromOpaque(context).takeUnretainedValue()
                var pressed = EventHotKeyID()
                let status = GetEventParameter(event, UInt32(kEventParamDirectObject),
                    UInt32(typeEventHotKeyID), nil,
                    UInt32(MemoryLayout<EventHotKeyID>.size), nil, &pressed)
                if status == noErr,
                   pressed.signature == UltronHotkey.signature,
                   pressed.id == UltronHotkey.identifier {
                    DispatchQueue.main.async { owner.callback() }
                    return noErr
                }
                return OSStatus(eventNotHandledErr)
            }, 1, [spec], Unmanaged.passUnretained(self).toOpaque(), &handler)
        guard result == noErr else { return false }
        let identifier = EventHotKeyID(signature: Self.signature, id: Self.identifier)
        // 49 is the virtual keycode for Space. optionKey is a Carbon modifier.
        let registered = RegisterEventHotKey(UInt32(49), UInt32(optionKey), identifier,
                                             GetEventDispatcherTarget(), 0, &hotKey)
        if registered != noErr {
            if let handler { RemoveEventHandler(handler) }
            handler = nil
            return false
        }
        return true
    }

    func unregister() {
        if let hotKey { UnregisterEventHotKey(hotKey) }
        if let handler { RemoveEventHandler(handler) }
        hotKey = nil
        handler = nil
    }

    deinit { unregister() }
}
