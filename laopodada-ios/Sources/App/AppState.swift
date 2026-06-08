import Foundation
import Combine

/// Process-wide app state. Owns the API client and any cross-tab shared data.
@MainActor
final class AppState: ObservableObject {
    /// Backend base URL. laopodada-api runs on :8097 behind Nginx :8088 prefix /laopodada/.
    /// iOS app talks to :8088 (the public reverse-proxy entry) and Nginx strips the prefix.
    let apiBaseURL: URL = URL(string: "http://123.57.107.21:8088/laopodada")!

    /// Single API client for the whole app.
    let api: APIClient

    /// Currently signed-in user (nil = offline / single-user mode for v0.1).
    @Published var currentUser: User?

    init() {
        self.api = APIClient(baseURL: apiBaseURL)
    }
}

struct User: Codable, Equatable, Identifiable {
    let id: String
    let name: String
}
