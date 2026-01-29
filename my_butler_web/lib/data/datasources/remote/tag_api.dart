import '../../../core/constants/api_endpoints.dart';
import '../../models/tag_models.dart';
import 'api_client.dart';

/// Tag API 서비스
class TagApi {
  final ApiClient _client;

  TagApi(this._client);

  /// 태그 목록 조회
  Future<TagListResponse> getTags({String? category}) async {
    final queryParams = <String, dynamic>{};
    if (category != null) queryParams['category'] = category;

    final response = await _client.get(
      ApiEndpoints.tags,
      queryParameters: queryParams,
    );
    return TagListResponse.fromJson(response.data);
  }

  /// 태그 생성
  Future<AssetTag> createTag(AssetTagCreate tag) async {
    final response = await _client.post(
      ApiEndpoints.tags,
      data: tag.toJson(),
    );
    return AssetTag.fromJson(response.data);
  }

  /// 태그 수정
  Future<AssetTag> updateTag(int id, AssetTagCreate tag) async {
    final response = await _client.put(
      '${ApiEndpoints.tags}/$id',
      data: tag.toJson(),
    );
    return AssetTag.fromJson(response.data);
  }

  /// 태그 삭제
  Future<void> deleteTag(int id) async {
    await _client.delete('${ApiEndpoints.tags}/$id');
  }

  /// 종목별 태그 조회
  Future<List<StockWithTags>> getStockTags({String? ticker}) async {
    final queryParams = <String, dynamic>{};
    if (ticker != null) queryParams['ticker'] = ticker;

    final response = await _client.get(
      ApiEndpoints.tagStocks,
      queryParameters: queryParams,
    );
    return (response.data as List)
        .map((e) => StockWithTags.fromJson(e))
        .toList();
  }

  /// 태그별 종목 조회
  Future<StocksByTagResponse> getStocksByTag(int tagId) async {
    final response = await _client.get('${ApiEndpoints.tags}/$tagId/stocks');
    return StocksByTagResponse.fromJson(response.data);
  }

  /// 종목에 태그 추가
  Future<void> addTagToStock(String ticker, int tagId) async {
    await _client.post(
      ApiEndpoints.tagStocks,
      data: {'ticker': ticker, 'tag_id': tagId},
    );
  }

  /// 종목에서 태그 제거
  Future<void> removeTagFromStock(String ticker, int tagId) async {
    await _client.delete('${ApiEndpoints.tagStocks}/$ticker/$tagId');
  }

  /// 일괄 태그 할당
  Future<void> bulkAssignTags(BulkTagAssignRequest request) async {
    await _client.post(
      ApiEndpoints.tagBulkAssign,
      data: request.toJson(),
    );
  }
}
