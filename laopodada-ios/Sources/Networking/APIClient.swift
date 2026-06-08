import Foundation

/// HTTP error returned by the API. Decoded from JSON `{"error": "..."}` bodies.
struct APIError: LocalizedError, Decodable {
    let error: String
    var errorDescription: String? { error }
}

/// Networking client for laopodada-api (port 8097 on 123.57.107.21).
/// Uses async/await throughout. Multipart upload handled separately.
final class APIClient {
    let baseURL: URL
    private let session: URLSession
    private let decoder: JSONDecoder
    private let encoder: JSONEncoder

    init(baseURL: URL, session: URLSession = .shared) {
        self.baseURL = baseURL
        self.session = session
        self.decoder = JSONDecoder()
        self.encoder = JSONEncoder()
    }

    // MARK: - JSON

    func get<T: Decodable>(_ path: String, query: [String: String] = [:]) async throws -> T {
        var req = try makeRequest(path: path, method: "GET", query: query)
        req.setValue("application/json", forHTTPHeaderField: "Accept")
        return try await perform(req)
    }

    @discardableResult
    func post<T: Decodable, B: Encodable>(_ path: String, body: B) async throws -> T {
        var req = try makeRequest(path: path, method: "POST")
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        req.setValue("application/json", forHTTPHeaderField: "Accept")
        req.httpBody = try encoder.encode(body)
        return try await perform(req)
    }

    @discardableResult
    func delete(_ path: String) async throws {
        let req = try makeRequest(path: path, method: "DELETE")
        let _: Empty = try await perform(req)
    }

    // MARK: - Multipart upload

    /// Upload a single image file as `multipart/form-data` with field name `file`.
    /// `extraFields` lets the caller attach additional form parts (e.g. `category`).
    func uploadImage<T: Decodable>(
        path: String,
        imageData: Data,
        filename: String = "upload.jpg",
        mimeType: String = "image/jpeg",
        extraFields: [String: String] = [:]
    ) async throws -> T {
        let boundary = "Boundary-\(UUID().uuidString)"
        var req = try makeRequest(path: path, method: "POST")
        req.setValue("multipart/form-data; boundary=\(boundary)", forHTTPHeaderField: "Content-Type")

        var body = Data()
        for (key, value) in extraFields.sorted(by: { $0.key < $1.key }) {
            body.append("--\(boundary)\r\n")
            body.append("Content-Disposition: form-data; name=\"\(key)\"\r\n\r\n")
            body.append("\(value)\r\n")
        }
        body.append("--\(boundary)\r\n")
        body.append("Content-Disposition: form-data; name=\"file\"; filename=\"\(filename)\"\r\n")
        body.append("Content-Type: \(mimeType)\r\n\r\n")
        body.append(imageData)
        body.append("\r\n--\(boundary)--\r\n")

        req.httpBody = body
        return try await perform(req)
    }

    // MARK: - Internals

    private func makeRequest(path: String, method: String, query: [String: String] = [:]) throws -> URLRequest {
        var components = URLComponents(url: baseURL.appendingPathComponent(path), resolvingAgainstBaseURL: false)
        if !query.isEmpty {
            components?.queryItems = query.map { URLQueryItem(name: $0.key, value: $0.value) }
        }
        guard let url = components?.url else {
            throw URLError(.badURL)
        }
        var req = URLRequest(url: url)
        req.httpMethod = method
        req.timeoutInterval = 30
        return req
    }

    private func perform<T: Decodable>(_ request: URLRequest) async throws -> T {
        let (data, response) = try await session.data(for: request)
        guard let http = response as? HTTPURLResponse else {
            throw URLError(.badServerResponse)
        }
        if !(200..<300).contains(http.statusCode) {
            if let apiErr = try? decoder.decode(APIError.self, from: data) {
                throw apiErr
            }
            throw URLError(.init(rawValue: http.statusCode))
        }
        if T.self == Empty.self {
            return Empty() as! T
        }
        // Handle empty 204 bodies for non-Empty decoders
        if data.isEmpty, let empty = try? decoder.decode(Empty.self, from: Data("{}".utf8)) as? T {
            return empty
        }
        return try decoder.decode(T.self, from: data)
    }
}

struct Empty: Codable {}

private extension Data {
    mutating func append(_ string: String) {
        if let d = string.data(using: .utf8) { append(d) }
    }
}
