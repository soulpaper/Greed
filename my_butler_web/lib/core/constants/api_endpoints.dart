/// API 엔드포인트 상수
class ApiEndpoints {
  ApiEndpoints._();

  static const String baseUrl = 'http://localhost:8000';
  static const String apiVersion = '/api/v1';

  // History API
  static const String historyStocks = '$apiVersion/history/stocks';
  static const String historySummaries = '$apiVersion/history/summaries';
  static const String historyLatest = '$apiVersion/history/latest';
  static const String historyCompare = '$apiVersion/history/compare';

  // Screening API
  static const String screeningRun = '$apiVersion/screening/run';
  static const String screeningLatest = '$apiVersion/screening/latest';
  static const String screeningRecommendations = '$apiVersion/screening/recommendations';
  static const String screeningHistory = '$apiVersion/screening/history';
  static const String screeningStatus = '$apiVersion/screening/status';

  // Tags API
  static const String tags = '$apiVersion/tags';
  static const String tagStocks = '$apiVersion/tags/stocks';
  static const String tagBulkAssign = '$apiVersion/tags/bulk-assign';
}
