import Foundation

/// A recipe — one cooking recipe. Matches the JSON returned by
/// `GET /api/v1/recipes` and `GET /api/v1/recipes/:id` on the backend.
struct Recipe: Codable, Identifiable, Hashable {
    let id: String
    let title: String
    let category: String          // breakfast | lunch | dinner | snack | dessert | drink
    let difficulty: String        // easy | medium | hard
    let prepMinutes: Int?
    let cookMinutes: Int?
    let servings: Int?
    let ingredients: [String]
    let steps: [String]
    let tags: [String]
    let note: String?
    let coverURL: URL?
    let bytesCover: Int?
    let createdAt: Int
    let createdAtISO: String?
    let updatedAt: Int

    enum CodingKeys: String, CodingKey {
        case id, title, category, difficulty, ingredients, steps, tags, note
        case prepMinutes    = "prep_minutes"
        case cookMinutes    = "cook_minutes"
        case servings
        case coverURL       = "cover_url"
        case bytesCover     = "bytes_cover"
        case createdAt      = "created_at"
        case createdAtISO   = "created_at_iso"
        case updatedAt      = "updated_at"
    }

    /// Total time, in minutes (prep + cook). nil if both unknown.
    var totalMinutes: Int? {
        switch (prepMinutes, cookMinutes) {
        case let (p?, c?): return p + c
        case let (p?, nil): return p
        case let (nil, c?): return c
        default: return nil
        }
    }

    /// Display category — Chinese labels.
    var categoryDisplay: String {
        switch category {
        case "breakfast": return "早餐"
        case "lunch":     return "午餐"
        case "dinner":    return "晚餐"
        case "snack":     return "加餐"
        case "dessert":   return "甜点"
        case "drink":     return "饮品"
        default:          return category
        }
    }

    var difficultyDisplay: String {
        switch difficulty {
        case "easy":   return "简单"
        case "medium": return "中等"
        case "hard":   return "困难"
        default:       return difficulty
        }
    }
}

/// Static enums for UI pickers.
enum RecipeCategory: String, CaseIterable, Identifiable {
    case breakfast, lunch, dinner, snack, dessert, drink
    var id: String { rawValue }
    var display: String {
        switch self {
        case .breakfast: return "早餐"
        case .lunch:     return "午餐"
        case .dinner:    return "晚餐"
        case .snack:     return "加餐"
        case .dessert:   return "甜点"
        case .drink:     return "饮品"
        }
    }
}

enum RecipeDifficulty: String, CaseIterable, Identifiable {
    case easy, medium, hard
    var id: String { rawValue }
    var display: String {
        switch self {
        case .easy:   return "简单"
        case .medium: return "中等"
        case .hard:   return "困难"
        }
    }
    var emoji: String {
        switch self {
        case .easy:   return "🌱"
        case .medium: return "🔥"
        case .hard:   return "💪"
        }
    }
}
