import Foundation

/// Wardrobe-specific API surface. All methods talk to laopodada-api :8097.
struct WardrobeAPI {
    let client: APIClient

    init(client: APIClient) { self.client = client }

    func list(category: WardrobeCategory? = nil) async throws -> [WardrobeItem] {
        var q: [String: String] = [:]
        if let category { q["category"] = category.rawValue }
        return try await client.get("/api/v1/items", query: q)
    }

    func get(id: String) async throws -> WardrobeItem {
        try await client.get("/api/v1/items/\(id)")
    }

    struct CreateResponse: Codable { let item: WardrobeItem }

    func upload(
        imageData: Data,
        category: WardrobeCategory,
        title: String,
        brand: String? = nil,
        color: String? = nil
    ) async throws -> WardrobeItem {
        var fields: [String: String] = [
            "category": category.rawValue,
            "title": title,
        ]
        if let brand { fields["brand"] = brand }
        if let color { fields["color"] = color }
        let resp: CreateResponse = try await client.uploadImage(
            path: "/api/v1/items",
            imageData: imageData,
            filename: "wardrobe-\(Int(Date().timeIntervalSince1970)).jpg",
            extraFields: fields
        )
        return resp.item
    }

    func delete(id: String) async throws {
        try await client.delete("/api/v1/items/\(id)")
    }
}
