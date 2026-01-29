import '../datasources/remote/history_api.dart';
import '../models/history_models.dart';

/// History Repository
class HistoryRepository {
  final HistoryApi _api;

  HistoryRepository(this._api);

  Future<StockHistoryResponse> getStockHistory({
    DateTime? startDate,
    DateTime? endDate,
    String? exchange,
    String? ticker,
    int limit = 100,
    int offset = 0,
  }) {
    return _api.getStockHistory(
      startDate: startDate,
      endDate: endDate,
      exchange: exchange,
      ticker: ticker,
      limit: limit,
      offset: offset,
    );
  }

  Future<SummaryHistoryResponse> getSummaryHistory({
    DateTime? startDate,
    DateTime? endDate,
    String? exchange,
    int limit = 100,
    int offset = 0,
  }) {
    return _api.getSummaryHistory(
      startDate: startDate,
      endDate: endDate,
      exchange: exchange,
      limit: limit,
      offset: offset,
    );
  }

  Future<LatestRecordResponse> getLatestRecords() {
    return _api.getLatestRecords();
  }
}
