import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/constants/app_colors.dart';
import '../../../data/models/tag_models.dart';
import '../../../data/mock/mock_data.dart';
import '../../providers/providers.dart';
import '../../widgets/loading_widget.dart';
import '../../widgets/error_widget.dart';

/// 태그 관리 화면
class TagsScreen extends ConsumerStatefulWidget {
  const TagsScreen({super.key});

  @override
  ConsumerState<TagsScreen> createState() => _TagsScreenState();
}

class _TagsScreenState extends ConsumerState<TagsScreen> {
  AssetTag? _selectedTag;

  @override
  Widget build(BuildContext context) {
    final tagsAsync = ref.watch(tagsProvider);

    return Row(
      children: [
        // 태그 목록
        SizedBox(
          width: 350,
          child: tagsAsync.when(
            loading: () => const LoadingWidget(),
            error: (error, _) => AppErrorWidget(
              message: error.toString(),
              onRetry: () => ref.invalidate(tagsProvider),
            ),
            data: (data) => _buildTagList(data),
          ),
        ),
        const VerticalDivider(width: 1),
        // 상세/종목 영역
        Expanded(
          child: _selectedTag != null
              ? _buildTagDetail(_selectedTag!)
              : _buildEmptyState(),
        ),
      ],
    );
  }

  Widget _buildTagList(TagListResponse data) {
    // 카테고리별 그룹핑
    final tagsByCategory = <String?, List<AssetTag>>{};
    for (final tag in data.tags) {
      tagsByCategory.putIfAbsent(tag.category, () => []);
      tagsByCategory[tag.category]!.add(tag);
    }

    return Column(
      children: [
        // 헤더
        Container(
          padding: const EdgeInsets.all(20),
          color: AppColors.surface,
          child: Row(
            children: [
              const Text(
                '태그 관리',
                style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
              ),
              const Spacer(),
              IconButton(
                icon: const Icon(Icons.add),
                onPressed: () => _showTagDialog(),
                tooltip: '태그 추가',
              ),
            ],
          ),
        ),
        const Divider(height: 1),
        // 태그 목록
        Expanded(
          child: data.tags.isEmpty
              ? const Center(
                  child: Text(
                    '등록된 태그가 없습니다',
                    style: TextStyle(color: AppColors.textSecondary),
                  ),
                )
              : ListView(
                  children: tagsByCategory.entries.map((entry) {
                    final category = entry.key ?? '미분류';
                    final tags = entry.value;
                    return ExpansionTile(
                      title: Text(
                        category,
                        style: const TextStyle(fontWeight: FontWeight.w600),
                      ),
                      initiallyExpanded: true,
                      children: tags.map((tag) => _buildTagTile(tag)).toList(),
                    );
                  }).toList(),
                ),
        ),
      ],
    );
  }

  Widget _buildTagTile(AssetTag tag) {
    final isSelected = _selectedTag?.id == tag.id;
    return ListTile(
      leading: Container(
        width: 24,
        height: 24,
        decoration: BoxDecoration(
          color: _parseColor(tag.color),
          borderRadius: BorderRadius.circular(6),
        ),
      ),
      title: Text(tag.name),
      subtitle: tag.description != null ? Text(tag.description!, maxLines: 1) : null,
      selected: isSelected,
      selectedTileColor: AppColors.accent.withValues(alpha: 0.1),
      onTap: () => setState(() => _selectedTag = tag),
      trailing: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          IconButton(
            icon: const Icon(Icons.edit, size: 18),
            onPressed: () => _showTagDialog(tag: tag),
            tooltip: '수정',
          ),
          IconButton(
            icon: const Icon(Icons.delete, size: 18),
            onPressed: () => _confirmDeleteTag(tag),
            tooltip: '삭제',
          ),
        ],
      ),
    );
  }

  Widget _buildEmptyState() {
    return const Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(Icons.label_outline, size: 80, color: AppColors.textMuted),
          SizedBox(height: 16),
          Text(
            '태그를 선택하세요',
            style: TextStyle(color: AppColors.textSecondary, fontSize: 18),
          ),
        ],
      ),
    );
  }

  Widget _buildTagDetail(AssetTag tag) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // 태그 정보
          Card(
            child: Padding(
              padding: const EdgeInsets.all(24),
              child: Row(
                children: [
                  Container(
                    width: 48,
                    height: 48,
                    decoration: BoxDecoration(
                      color: _parseColor(tag.color),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: const Icon(Icons.label, color: Colors.white),
                  ),
                  const SizedBox(width: 20),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          tag.name,
                          style: const TextStyle(
                            fontSize: 24,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                        if (tag.category != null)
                          Text(
                            tag.category!,
                            style: const TextStyle(color: AppColors.textSecondary),
                          ),
                        if (tag.description != null)
                          Padding(
                            padding: const EdgeInsets.only(top: 8),
                            child: Text(
                              tag.description!,
                              style: const TextStyle(color: AppColors.textMuted),
                            ),
                          ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 24),

          // 연결된 종목
          const Text(
            '연결된 종목',
            style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 16),
          _buildStocksByTag(tag.id),
        ],
      ),
    );
  }

  Widget _buildStocksByTag(int tagId) {
    final future = useMockData
        ? Future.delayed(const Duration(milliseconds: 300), () => MockData.getStocksByTag(tagId))
        : ref.read(tagRepositoryProvider).getStocksByTag(tagId);

    return FutureBuilder(
      future: future,
      builder: (context, snapshot) {
        if (snapshot.connectionState == ConnectionState.waiting) {
          return const Card(
            child: Padding(
              padding: EdgeInsets.all(48),
              child: Center(child: CircularProgressIndicator()),
            ),
          );
        }

        if (snapshot.hasError) {
          return Card(
            child: Padding(
              padding: const EdgeInsets.all(24),
              child: Text('오류: ${snapshot.error}'),
            ),
          );
        }

        final data = snapshot.data!;
        if (data.stocks.isEmpty) {
          return const Card(
            child: Padding(
              padding: EdgeInsets.all(48),
              child: Center(
                child: Text(
                  '연결된 종목이 없습니다',
                  style: TextStyle(color: AppColors.textSecondary),
                ),
              ),
            ),
          );
        }

        return Card(
          child: Column(
            children: [
              Padding(
                padding: const EdgeInsets.all(16),
                child: Row(
                  children: [
                    Text(
                      '총 ${data.totalCount}개 종목',
                      style: const TextStyle(color: AppColors.textSecondary),
                    ),
                  ],
                ),
              ),
              const Divider(height: 1),
              ListView.separated(
                shrinkWrap: true,
                physics: const NeverScrollableScrollPhysics(),
                itemCount: data.stocks.length,
                separatorBuilder: (_, __) => const Divider(height: 1),
                itemBuilder: (context, index) {
                  final stock = data.stocks[index];
                  return ListTile(
                    title: Text(stock.ticker),
                    subtitle: Text(stock.stockName ?? ''),
                    trailing: Text(
                      stock.exchange ?? '',
                      style: const TextStyle(color: AppColors.textSecondary),
                    ),
                  );
                },
              ),
            ],
          ),
        );
      },
    );
  }

  Color _parseColor(String hex) {
    try {
      return Color(int.parse(hex.replaceFirst('#', '0xFF')));
    } catch (_) {
      return AppColors.accent;
    }
  }

  void _showTagDialog({AssetTag? tag}) {
    final isEditing = tag != null;
    final nameController = TextEditingController(text: tag?.name ?? '');
    final categoryController = TextEditingController(text: tag?.category ?? '');
    final descController = TextEditingController(text: tag?.description ?? '');
    String selectedColor = tag?.color ?? '#6B7280';

    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(isEditing ? '태그 수정' : '새 태그'),
        content: SizedBox(
          width: 400,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(
                controller: nameController,
                decoration: const InputDecoration(labelText: '태그 이름'),
              ),
              const SizedBox(height: 16),
              TextField(
                controller: categoryController,
                decoration: const InputDecoration(labelText: '카테고리 (선택)'),
              ),
              const SizedBox(height: 16),
              TextField(
                controller: descController,
                decoration: const InputDecoration(labelText: '설명 (선택)'),
                maxLines: 2,
              ),
              const SizedBox(height: 16),
              Row(
                children: [
                  const Text('색상: '),
                  const SizedBox(width: 8),
                  ...[
                    '#3FB950',
                    '#F85149',
                    '#58A6FF',
                    '#D29922',
                    '#A371F7',
                    '#6B7280',
                  ].map((color) {
                    return GestureDetector(
                      onTap: () {
                        selectedColor = color;
                        (context as Element).markNeedsBuild();
                      },
                      child: Container(
                        width: 32,
                        height: 32,
                        margin: const EdgeInsets.only(right: 8),
                        decoration: BoxDecoration(
                          color: _parseColor(color),
                          borderRadius: BorderRadius.circular(6),
                          border: selectedColor == color
                              ? Border.all(color: Colors.white, width: 2)
                              : null,
                        ),
                      ),
                    );
                  }),
                ],
              ),
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('취소'),
          ),
          ElevatedButton(
            onPressed: () async {
              if (nameController.text.isEmpty) return;

              final tagData = AssetTagCreate(
                name: nameController.text,
                category: categoryController.text.isEmpty ? null : categoryController.text,
                description: descController.text.isEmpty ? null : descController.text,
                color: selectedColor,
              );

              try {
                if (isEditing) {
                  await ref.read(tagRepositoryProvider).updateTag(tag.id, tagData);
                } else {
                  await ref.read(tagRepositoryProvider).createTag(tagData);
                }
                ref.invalidate(tagsProvider);
                if (mounted) Navigator.pop(context);
              } catch (e) {
                if (mounted) {
                  ScaffoldMessenger.of(context).showSnackBar(
                    SnackBar(content: Text('오류: $e')),
                  );
                }
              }
            },
            child: Text(isEditing ? '수정' : '생성'),
          ),
        ],
      ),
    );
  }

  void _confirmDeleteTag(AssetTag tag) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('태그 삭제'),
        content: Text('"${tag.name}" 태그를 삭제하시겠습니까?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('취소'),
          ),
          ElevatedButton(
            style: ElevatedButton.styleFrom(backgroundColor: AppColors.negative),
            onPressed: () async {
              try {
                await ref.read(tagRepositoryProvider).deleteTag(tag.id);
                ref.invalidate(tagsProvider);
                if (_selectedTag?.id == tag.id) {
                  setState(() => _selectedTag = null);
                }
                if (mounted) Navigator.pop(context);
              } catch (e) {
                if (mounted) {
                  ScaffoldMessenger.of(context).showSnackBar(
                    SnackBar(content: Text('오류: $e')),
                  );
                }
              }
            },
            child: const Text('삭제'),
          ),
        ],
      ),
    );
  }
}
