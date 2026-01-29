import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../data/datasources/remote/api_client.dart';
import '../../data/datasources/remote/history_api.dart';
import '../../data/datasources/remote/screening_api.dart';
import '../../data/datasources/remote/tag_api.dart';
import '../../data/repositories/history_repository.dart';
import '../../data/repositories/screening_repository.dart';
import '../../data/repositories/tag_repository.dart';
import '../../data/models/history_models.dart';
import '../../data/models/screening_models.dart';
import '../../data/models/tag_models.dart';
import '../../data/mock/mock_data.dart';

// ============ Mock 모드 설정 ============
// true: 가데이터 사용, false: 실제 API 사용
const bool useMockData = true;

// API Client
final apiClientProvider = Provider<ApiClient>((ref) => ApiClient());

// APIs
final historyApiProvider = Provider<HistoryApi>((ref) {
  return HistoryApi(ref.watch(apiClientProvider));
});

final screeningApiProvider = Provider<ScreeningApi>((ref) {
  return ScreeningApi(ref.watch(apiClientProvider));
});

final tagApiProvider = Provider<TagApi>((ref) {
  return TagApi(ref.watch(apiClientProvider));
});

// Repositories
final historyRepositoryProvider = Provider<HistoryRepository>((ref) {
  return HistoryRepository(ref.watch(historyApiProvider));
});

final screeningRepositoryProvider = Provider<ScreeningRepository>((ref) {
  return ScreeningRepository(ref.watch(screeningApiProvider));
});

final tagRepositoryProvider = Provider<TagRepository>((ref) {
  return TagRepository(ref.watch(tagApiProvider));
});

// ============ History Providers ============

final latestRecordsProvider = FutureProvider<LatestRecordResponse>((ref) async {
  if (useMockData) {
    await Future.delayed(const Duration(milliseconds: 500));
    return MockData.getLatestRecords();
  }
  return ref.watch(historyRepositoryProvider).getLatestRecords();
});

final summaryHistoryProvider = FutureProvider.family<SummaryHistoryResponse, SummaryHistoryParams>((ref, params) async {
  if (useMockData) {
    await Future.delayed(const Duration(milliseconds: 300));
    return MockData.getSummaryHistory();
  }
  return ref.watch(historyRepositoryProvider).getSummaryHistory(
    startDate: params.startDate,
    endDate: params.endDate,
    exchange: params.exchange,
    limit: params.limit,
    offset: params.offset,
  );
});

class SummaryHistoryParams {
  final DateTime? startDate;
  final DateTime? endDate;
  final String? exchange;
  final int limit;
  final int offset;

  SummaryHistoryParams({
    this.startDate,
    this.endDate,
    this.exchange,
    this.limit = 100,
    this.offset = 0,
  });
}

final stockHistoryProvider = FutureProvider.family<StockHistoryResponse, StockHistoryParams>((ref, params) async {
  if (useMockData) {
    await Future.delayed(const Duration(milliseconds: 500));
    return MockData.getStockHistory();
  }
  return ref.watch(historyRepositoryProvider).getStockHistory(
    startDate: params.startDate,
    endDate: params.endDate,
    exchange: params.exchange,
    ticker: params.ticker,
    limit: params.limit,
    offset: params.offset,
  );
});

class StockHistoryParams {
  final DateTime? startDate;
  final DateTime? endDate;
  final String? exchange;
  final String? ticker;
  final int limit;
  final int offset;

  StockHistoryParams({
    this.startDate,
    this.endDate,
    this.exchange,
    this.ticker,
    this.limit = 100,
    this.offset = 0,
  });
}

// ============ Screening Providers ============

/// 스크리닝 탭 타입
enum ScreeningTabType {
  overall,      // 종합
  ichimoku,     // 일목균형표
  bollinger,    // 볼린저밴드
  maAlignment,  // 이평선 정배열
  cupHandle,    // 컵앤핸들
}

/// 종합 스크리닝 결과 (뷰어용)
final screeningResultProvider = FutureProvider<ScreeningResponse>((ref) async {
  if (useMockData) {
    await Future.delayed(const Duration(milliseconds: 500));
    return MockData.getScreeningResult();
  }
  return ref.watch(screeningRepositoryProvider).getLatestScreening();
});

/// 일목균형표 스크리닝 결과
final ichimokuScreeningProvider = FutureProvider<ScreeningResponse>((ref) async {
  if (useMockData) {
    await Future.delayed(const Duration(milliseconds: 300));
    return MockData.getIchimokuScreeningResult();
  }
  return ref.watch(screeningRepositoryProvider).getLatestScreening(filter: 'ichimoku');
});

/// 볼린저밴드 스크리닝 결과
final bollingerScreeningProvider = FutureProvider<ScreeningResponse>((ref) async {
  if (useMockData) {
    await Future.delayed(const Duration(milliseconds: 300));
    return MockData.getBollingerScreeningResult();
  }
  return ref.watch(screeningRepositoryProvider).getLatestScreening(filter: 'bollinger');
});

/// 이평선 정배열 스크리닝 결과
final maAlignmentScreeningProvider = FutureProvider<ScreeningResponse>((ref) async {
  if (useMockData) {
    await Future.delayed(const Duration(milliseconds: 300));
    return MockData.getMAAlignmentScreeningResult();
  }
  return ref.watch(screeningRepositoryProvider).getLatestScreening(filter: 'ma_alignment');
});

/// 컵앤핸들 스크리닝 결과
final cupHandleScreeningProvider = FutureProvider<ScreeningResponse>((ref) async {
  if (useMockData) {
    await Future.delayed(const Duration(milliseconds: 300));
    return MockData.getCupHandleScreeningResult();
  }
  return ref.watch(screeningRepositoryProvider).getLatestScreening(filter: 'cup_handle');
});

final recommendationsProvider = FutureProvider<DailyRecommendation>((ref) async {
  if (useMockData) {
    await Future.delayed(const Duration(milliseconds: 300));
    return MockData.getRecommendations();
  }
  return ref.watch(screeningRepositoryProvider).getRecommendations();
});

// ============ Tag Providers ============

final tagsProvider = FutureProvider<TagListResponse>((ref) async {
  if (useMockData) {
    await Future.delayed(const Duration(milliseconds: 300));
    return MockData.getTags();
  }
  return ref.watch(tagRepositoryProvider).getTags();
});

final stockTagsProvider = FutureProvider<List<StockWithTags>>((ref) async {
  if (useMockData) {
    await Future.delayed(const Duration(milliseconds: 300));
    return [];
  }
  return ref.watch(tagRepositoryProvider).getStockTags();
});

// ============ Dashboard Providers ============

final dashboardDataProvider = FutureProvider<DashboardData>((ref) async {
  if (useMockData) {
    await Future.delayed(const Duration(milliseconds: 600));
    return DashboardData(
      latestRecords: MockData.getLatestRecords(),
      summaryHistory: MockData.getSummaryHistory(),
      recommendations: MockData.getRecommendations(),
    );
  }

  final historyRepo = ref.watch(historyRepositoryProvider);
  final screeningRepo = ref.watch(screeningRepositoryProvider);

  final latestRecords = await historyRepo.getLatestRecords();
  final summaryHistory = await historyRepo.getSummaryHistory(limit: 30);

  DailyRecommendation? recommendations;
  try {
    recommendations = await screeningRepo.getRecommendations();
  } catch (_) {
    recommendations = null;
  }

  return DashboardData(
    latestRecords: latestRecords,
    summaryHistory: summaryHistory,
    recommendations: recommendations,
  );
});

class DashboardData {
  final LatestRecordResponse latestRecords;
  final SummaryHistoryResponse summaryHistory;
  final DailyRecommendation? recommendations;

  DashboardData({
    required this.latestRecords,
    required this.summaryHistory,
    this.recommendations,
  });
}
