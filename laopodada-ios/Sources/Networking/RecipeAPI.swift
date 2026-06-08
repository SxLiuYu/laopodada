import Foundation

/// Recipe-specific API surface. Mirrors WardrobeAPI.
struct RecipeAPI {
    let client: APIClient

    init(client: APIClient) { self.client = client }

    /// GET /api/v1/recipes[?category=...&difficulty=...&tag=...]
    func list(category: String? = nil, difficulty: String? = nil, tag: String? = nil) async throws -> [Recipe] {
        var q: [URLQueryItem] = []
        if let category, !category.isEmpty { q.append(URLQueryItem(name: "category", value: category)) }
        if let difficulty, !difficulty.isEmpty { q.append(URLQueryItem(name: "difficulty", value: difficulty)) }
        if let tag, !tag.isEmpty { q.append(URLQueryItem(name: "tag", value: tag)) }
        struct Resp: Decodable { let recipes: [Recipe] }
        let resp: Resp = try await client.get("/api/v1/recipes", query: q)
        return resp.recipes
    }

    /// GET /api/v1/recipes/:id
    func get(_ id: String) async throws -> Recipe {
        try await client.get("/api/v1/recipes/\(id)")
    }

    /// POST /api/v1/recipes (no cover image)
    func create(
        title: String,
        category: String,
        difficulty: String,
        prepMinutes: Int?,
        cookMinutes: Int?,
        servings: Int?,
        ingredients: [String],
        steps: [String],
        tags: [String],
        note: String?
    ) async throws -> Recipe {
        var body: [String: Any] = [
            "title": title,
            "category": category,
            "difficulty": difficulty,
            "ingredients": ingredients,
            "steps": steps,
        ]
        if let prepMinutes { body["prep_minutes"] = prepMinutes }
        if let cookMinutes { body["cook_minutes"] = cookMinutes }
        if let servings    { body["servings"] = servings }
        if !tags.isEmpty   { body["tags"] = tags }
        if let note, !note.isEmpty { body["note"] = note }
        struct Resp: Decodable { let recipe: Recipe }
        let resp: Resp = try await client.post("/api/v1/recipes", json: body)
        return resp.recipe
    }

    /// DELETE /api/v1/recipes/:id
    func delete(_ id: String) async throws {
        try await client.delete("/api/v1/recipes/\(id)")
    }
}
