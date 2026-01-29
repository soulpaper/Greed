import '../../../core/constants/api_endpoints.dart';
import '../../models/history_models.dart';
import 'api_client.dart';

/// History API 서비스
class HistoryApi {
  final ApiClient _client;

  HistoryApi(this._client);

  /// 종목 히스토리 조회
  Future<StockHistoryResponse> getStockHistory({
    DateTime? startDate,
    DateTime? endDate,
    String? exchange,
    String? ticker,
    int limit = 100,
    int offset = 0,
  }) async {
    final queryParams = <String, dynamic>{
      'limit': limit,
      'offset': offset,
    };
    if (startDate != null) {
      queryParams['start_date'] = startDate.toIso8601String().split('T')[0];
    }
    if (endDate != null) {
      queryParams['end_date'] = endDate.toIso8601String().split('T')[0];
    }
    if (exchange != null) queryParams['exchange'] = exchange;
    if (ticker != null) queryParams['ticker'] = ticker;

    final response = await _client.get(
      ApiEndpoints.historyStocks,
      queryParameters: queryParams,
    );
    return StockHistoryResponse.fromJson(response.data);
  }

  /// 계좌 요약 히스토리 조회
  Future<SummaryHistoryResponse> getSummaryHistory({
    DateTime? startDate,
    DateTime? endDate,
    String? exchange,
    int limit = 100,
    int offset = 0,
  }) async {
    final queryParams = <String, dynamic>{
      'limit': limit,
      'offset': offset,
    };
    if (startDate != null) {
      queryParams['start_date'] = startDate.toIso8601String().split('T')[0];
    }
    if (endDate != null) {
      queryParams['end_date'] = endDate.toIso8601String().split('T')[0];
    }
    if (exchange != null) queryParams['exchange'] = exchange;

    final response = await _client.get(
      ApiEndpoints.historySummaries,
      queryParameters: queryParams,
    );
    return SummaryHistoryResponse.fromJson(response.data);
  }

  /// 최근 기록 조회
  Future<LatestRecordResponse> getLatestRecords() async {
    final response = await _client.get(ApiEndpoints.historyLatest);
    return LatestRecordResponse.fromJson(response.data);
  }
}
