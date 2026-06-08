import Foundation

/// A wardrobe item — one piece of clothing. Matches the JSON returned by
/// `GET /api/v1/items` and `GET /api/v1/items/:id` on the backend.
struct WardrobeItem: Codable, Identifiable, Equatable, Hashable {
    let id: String
    let category: String      // e.g. "top" / "bottom" / "shoes"
    let title: String
    let brand: String?
    let color: String?
    let season: String?       // "spring" / "summer" / "fall" / "winter" / "all"
    let thumbnailURL: URL
    let originalURL: URL
    let createdAt: Date

    enum CodingKeys: String, CodingKey {
        case id, category, title, brand, color, season
        case thumbnailURL = "thumbnail_url"
        case originalURL = "original_url"
        case createdAt = "created_at"
    }
}

/// Category enum with display name. Add cases as backend grows.
enum WardrobeCategory: String, CaseIterable, Identifiable, Codable {
    case top
    case bottom
    case dress
    case outerwear
    case shoes
    case bag
    case accessory

    var id: String { rawValue }

    var displayName: String {
        switch self {
        case .top: return "上装"
        case .bottom: return "下装"
        case .dress: return "连衣裙"
        case .outerwear: return "外套"
        case .shoes: return "鞋子"
        case .bag: return "包包"
        case .accessory: return "配饰"
        }
    }

    var systemImage: String {
        switch self {
        case .top: return "tshirt"
        case .bottom: return "rectangle.portrait"
        case .dress: return "figure.dress"
        case .outerwear: return "jacket"
        case .shoes: return "shoe"
        case .bag: return "bag"
        case .accessory: return "eyeglasses"
        }
    }
}
