/// Tag API 데이터 모델
library;

class AssetTag {
  final int id;
  final String name;
  final String? category;
  final String color;
  final String? description;
  final DateTime createdAt;

  AssetTag({
    required this.id,
    required this.name,
    this.category,
    this.color = '#6B7280',
    this.description,
    required this.createdAt,
  });

  factory AssetTag.fromJson(Map<String, dynamic> json) {
    return AssetTag(
      id: json['id'],
      name: json['name'],
      category: json['category'],
      color: json['color'] ?? '#6B7280',
      description: json['description'],
      createdAt: DateTime.parse(json['created_at']),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'name': name,
      'category': category,
      'color': color,
      'description': description,
    };
  }
}

class AssetTagCreate {
  final String name;
  final String? category;
  final String color;
  final String? description;

  AssetTagCreate({
    required this.name,
    this.category,
    this.color = '#6B7280',
    this.description,
  });

  Map<String, dynamic> toJson() {
    return {
      'name': name,
      'category': category,
      'color': color,
      'description': description,
    };
  }
}

class StockWithTags {
  final String ticker;
  final String? stockName;
  final String? exchange;
  final List<AssetTag> tags;

  StockWithTags({
    required this.ticker,
    this.stockName,
    this.exchange,
    this.tags = const [],
  });

  factory StockWithTags.fromJson(Map<String, dynamic> json) {
    return StockWithTags(
      ticker: json['ticker'],
      stockName: json['stock_name'],
      exchange: json['exchange'],
      tags:
          (json['tags'] as List?)?.map((e) => AssetTag.fromJson(e)).toList() ??
          [],
    );
  }
}

class TagWithStocks {
  final AssetTag tag;
  final List<String> tickers;
  final int stockCount;

  TagWithStocks({
    required this.tag,
    this.tickers = const [],
    this.stockCount = 0,
  });

  factory TagWithStocks.fromJson(Map<String, dynamic> json) {
    return TagWithStocks(
      tag: AssetTag.fromJson(json['tag']),
      tickers: List<String>.from(json['tickers'] ?? []),
      stockCount: json['stock_count'] ?? 0,
    );
  }
}

class TagListResponse {
  final List<AssetTag> tags;
  final int totalCount;

  TagListResponse({required this.tags, required this.totalCount});

  factory TagListResponse.fromJson(Map<String, dynamic> json) {
    return TagListResponse(
      tags: (json['tags'] as List).map((e) => AssetTag.fromJson(e)).toList(),
      totalCount: json['total_count'],
    );
  }
}

class StocksByTagResponse {
  final AssetTag tag;
  final List<StockWithTags> stocks;
  final int totalCount;

  StocksByTagResponse({
    required this.tag,
    required this.stocks,
    required this.totalCount,
  });

  factory StocksByTagResponse.fromJson(Map<String, dynamic> json) {
    return StocksByTagResponse(
      tag: AssetTag.fromJson(json['tag']),
      stocks: (json['stocks'] as List)
          .map((e) => StockWithTags.fromJson(e))
          .toList(),
      totalCount: json['total_count'],
    );
  }
}

class BulkTagAssignRequest {
  final List<String> tickers;
  final List<int> tagIds;

  BulkTagAssignRequest({required this.tickers, required this.tagIds});

  Map<String, dynamic> toJson() {
    return {'tickers': tickers, 'tag_ids': tagIds};
  }
}
