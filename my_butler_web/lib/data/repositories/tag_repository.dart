import '../datasources/remote/tag_api.dart';
import '../models/tag_models.dart';

/// Tag Repository
class TagRepository {
  final TagApi _api;

  TagRepository(this._api);

  Future<TagListResponse> getTags({String? category}) {
    return _api.getTags(category: category);
  }

  Future<AssetTag> createTag(AssetTagCreate tag) {
    return _api.createTag(tag);
  }

  Future<AssetTag> updateTag(int id, AssetTagCreate tag) {
    return _api.updateTag(id, tag);
  }

  Future<void> deleteTag(int id) {
    return _api.deleteTag(id);
  }

  Future<List<StockWithTags>> getStockTags({String? ticker}) {
    return _api.getStockTags(ticker: ticker);
  }

  Future<StocksByTagResponse> getStocksByTag(int tagId) {
    return _api.getStocksByTag(tagId);
  }

  Future<void> addTagToStock(String ticker, int tagId) {
    return _api.addTagToStock(ticker, tagId);
  }

  Future<void> removeTagFromStock(String ticker, int tagId) {
    return _api.removeTagFromStock(ticker, tagId);
  }

  Future<void> bulkAssignTags(BulkTagAssignRequest request) {
    return _api.bulkAssignTags(request);
  }
}
