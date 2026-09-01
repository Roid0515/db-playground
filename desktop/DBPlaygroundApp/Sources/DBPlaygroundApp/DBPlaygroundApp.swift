import SwiftUI

@main
struct DBPlaygroundApp: App {
    @NSApplicationDelegateAdaptor(AppDelegate.self) private var appDelegate

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(appDelegate.runtime)
        }
        .windowResizability(.contentSize)
        .defaultSize(width: 1180, height: 800)
    }
}
