import '../../../core/constants/api_endpoints.dart';
import '../../models/screening_models.dart';
import 'api_client.dart';

/// Screening API 서비스
class ScreeningApi {
  final ApiClient _client;

  ScreeningApi(this._client);

  /// 최신 스크리닝 결과 조회 (뷰어용)
  Future<ScreeningResponse> getLatestScreening({String? filter}) async {
    final queryParams = <String, dynamic>{};
    if (filter != null) {
      queryParams['filter'] = filter;
    }
    final response = await _client.get(
      ApiEndpoints.screeningLatest,
      queryParameters: queryParams.isNotEmpty ? queryParams : null,
    );
    return ScreeningResponse.fromJson(response.data);
  }

  /// 스크리닝 실행
  Future<ScreeningResponse> runScreening(ScreeningRequest request) async {
    final response = await _client.post(
      ApiEndpoints.screeningRun,
      data: request.toJson(),
    );
    return ScreeningResponse.fromJson(response.data);
  }

  /// 일일 추천 종목 조회
  Future<DailyRecommendation> getRecommendations() async {
    final response = await _client.get(ApiEndpoints.screeningRecommendations);
    return DailyRecommendation.fromJson(response.data);
  }

  /// 스크리닝 상태 조회
  Future<Map<String, dynamic>> getStatus() async {
    final response = await _client.get(ApiEndpoints.screeningStatus);
    return response.data;
  }
}
