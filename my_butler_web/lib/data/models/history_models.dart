/// History API 데이터 모델
class StockRecord {
  final int id;
  final DateTime recordDate;
  final String exchange;
  final String currency;
  final String ticker;
  final String? stockName;
  final double? quantity;
  final double? avgPurchasePrice;
  final double? currentPrice;
  final double? purchaseAmount;
  final double? evalAmount;
  final double? profitLossAmount;
  final double? profitLossRate;
  final DateTime createdAt;

  StockRecord({
    required this.id,
    required this.recordDate,
    required this.exchange,
    required this.currency,
    required this.ticker,
    this.stockName,
    this.quantity,
    this.avgPurchasePrice,
    this.currentPrice,
    this.purchaseAmount,
    this.evalAmount,
    this.profitLossAmount,
    this.profitLossRate,
    required this.createdAt,
  });

  factory StockRecord.fromJson(Map<String, dynamic> json) {
    return StockRecord(
      id: json['id'],
      recordDate: DateTime.parse(json['record_date']),
      exchange: json['exchange'],
      currency: json['currency'],
      ticker: json['ticker'],
      stockName: json['stock_name'],
      quantity: json['quantity']?.toDouble(),
      avgPurchasePrice: json['avg_purchase_price']?.toDouble(),
      currentPrice: json['current_price']?.toDouble(),
      purchaseAmount: json['purchase_amount']?.toDouble(),
      evalAmount: json['eval_amount']?.toDouble(),
      profitLossAmount: json['profit_loss_amount']?.toDouble(),
      profitLossRate: json['profit_loss_rate']?.toDouble(),
      createdAt: DateTime.parse(json['created_at']),
    );
  }
}

class SummaryRecord {
  final int id;
  final DateTime recordDate;
  final String exchange;
  final String currency;
  final double? totalPurchaseAmount;
  final double? totalEvalAmount;
  final double? totalProfitLoss;
  final double? totalProfitRate;
  final int? stockCount;
  final DateTime createdAt;

  SummaryRecord({
    required this.id,
    required this.recordDate,
    required this.exchange,
    required this.currency,
    this.totalPurchaseAmount,
    this.totalEvalAmount,
    this.totalProfitLoss,
    this.totalProfitRate,
    this.stockCount,
    required this.createdAt,
  });

  factory SummaryRecord.fromJson(Map<String, dynamic> json) {
    return SummaryRecord(
      id: json['id'],
      recordDate: DateTime.parse(json['record_date']),
      exchange: json['exchange'],
      currency: json['currency'],
      totalPurchaseAmount: json['total_purchase_amount']?.toDouble(),
      totalEvalAmount: json['total_eval_amount']?.toDouble(),
      totalProfitLoss: json['total_profit_loss']?.toDouble(),
      totalProfitRate: json['total_profit_rate']?.toDouble(),
      stockCount: json['stock_count'],
      createdAt: DateTime.parse(json['created_at']),
    );
  }
}

class StockHistoryResponse {
  final List<StockRecord> records;
  final int totalCount;
  final int limit;
  final int offset;

  StockHistoryResponse({
    required this.records,
    required this.totalCount,
    required this.limit,
    required this.offset,
  });

  factory StockHistoryResponse.fromJson(Map<String, dynamic> json) {
    return StockHistoryResponse(
      records: (json['records'] as List)
          .map((e) => StockRecord.fromJson(e))
          .toList(),
      totalCount: json['total_count'],
      limit: json['limit'],
      offset: json['offset'],
    );
  }
}

class SummaryHistoryResponse {
  final List<SummaryRecord> records;
  final int totalCount;
  final int limit;
  final int offset;

  SummaryHistoryResponse({
    required this.records,
    required this.totalCount,
    required this.limit,
    required this.offset,
  });

  factory SummaryHistoryResponse.fromJson(Map<String, dynamic> json) {
    return SummaryHistoryResponse(
      records: (json['records'] as List)
          .map((e) => SummaryRecord.fromJson(e))
          .toList(),
      totalCount: json['total_count'],
      limit: json['limit'],
      offset: json['offset'],
    );
  }
}

class LatestRecordResponse {
  final DateTime recordDate;
  final Map<String, dynamic> exchanges;
  final int totalStocks;

  LatestRecordResponse({
    required this.recordDate,
    required this.exchanges,
    required this.totalStocks,
  });

  factory LatestRecordResponse.fromJson(Map<String, dynamic> json) {
    return LatestRecordResponse(
      recordDate: DateTime.parse(json['record_date']),
      exchanges: json['exchanges'] ?? {},
      totalStocks: json['total_stocks'],
    );
  }
}
