import '../datasources/remote/screening_api.dart';
import '../models/screening_models.dart';

/// Screening Repository
class ScreeningRepository {
  final ScreeningApi _api;

  ScreeningRepository(this._api);

  /// 최신 스크리닝 결과 조회 (뷰어용)
  Future<ScreeningResponse> getLatestScreening({String? filter}) {
    return _api.getLatestScreening(filter: filter);
  }

  Future<ScreeningResponse> runScreening(ScreeningRequest request) {
    return _api.runScreening(request);
  }

  Future<DailyRecommendation> getRecommendations() {
    return _api.getRecommendations();
  }

  Future<Map<String, dynamic>> getStatus() {
    return _api.getStatus();
  }
}
