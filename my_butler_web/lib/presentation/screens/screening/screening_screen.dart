import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/constants/app_colors.dart';
import '../../../core/utils/formatters.dart';
import '../../../data/models/screening_models.dart';
import '../../providers/providers.dart';
import '../../widgets/loading_widget.dart';
import '../../widgets/error_widget.dart';

/// 스크리닝 뷰어 화면
class ScreeningScreen extends ConsumerStatefulWidget {
  const ScreeningScreen({super.key});

  @override
  ConsumerState<ScreeningScreen> createState() => _ScreeningScreenState();
}

class _ScreeningScreenState extends ConsumerState<ScreeningScreen>
    with SingleTickerProviderStateMixin {
  late TabController _tabController;

  static const _tabs = [
    _TabInfo('종합', Icons.dashboard_outlined),
    _TabInfo('일목균형표', Icons.show_chart),
    _TabInfo('볼린저', Icons.stacked_line_chart),
    _TabInfo('이평선', Icons.trending_up),
    _TabInfo('컵앤핸들', Icons.coffee_outlined),
  ];

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: _tabs.length, vsync: this);
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        // 헤더
        _buildHeader(),
        // 탭바
        _buildTabBar(),
        // 탭 뷰
        Expanded(
          child: TabBarView(
            controller: _tabController,
            children: [
              _ScreeningTabContent(provider: screeningResultProvider),
              _ScreeningTabContent(provider: ichimokuScreeningProvider),
              _ScreeningTabContent(provider: bollingerScreeningProvider),
              _ScreeningTabContent(provider: maAlignmentScreeningProvider),
              _ScreeningTabContent(provider: cupHandleScreeningProvider),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildHeader() {
    final screeningResult = ref.watch(screeningResultProvider);

    return Container(
      padding: const EdgeInsets.fromLTRB(24, 20, 24, 12),
      decoration: const BoxDecoration(
        color: AppColors.surface,
        border: Border(
          bottom: BorderSide(color: AppColors.border, width: 1),
        ),
      ),
      child: Row(
        children: [
          const Icon(Icons.analytics_outlined, size: 28, color: AppColors.accent),
          const SizedBox(width: 12),
          const Text(
            '스크리닝 결과',
            style: TextStyle(
              fontSize: 22,
              fontWeight: FontWeight.bold,
              color: AppColors.textPrimary,
            ),
          ),
          const Spacer(),
          screeningResult.when(
            data: (data) => Container(
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
              decoration: BoxDecoration(
                color: AppColors.surfaceLight,
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: AppColors.border),
              ),
              child: Row(
                children: [
                  const Icon(Icons.calendar_today, size: 16, color: AppColors.textSecondary),
                  const SizedBox(width: 8),
                  Text(
                    '기준일: ${Formatters.date(data.screeningDate)}',
                    style: const TextStyle(
                      color: AppColors.textSecondary,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                ],
              ),
            ),
            loading: () => const SizedBox.shrink(),
            error: (_, __) => const SizedBox.shrink(),
          ),
        ],
      ),
    );
  }

  Widget _buildTabBar() {
    return Container(
      color: AppColors.surface,
      child: TabBar(
        controller: _tabController,
        isScrollable: false,
        labelColor: AppColors.accent,
        unselectedLabelColor: AppColors.textSecondary,
        indicatorColor: AppColors.accent,
        indicatorWeight: 3,
        labelStyle: const TextStyle(fontWeight: FontWeight.w600, fontSize: 14),
        unselectedLabelStyle: const TextStyle(fontWeight: FontWeight.normal, fontSize: 14),
        tabs: _tabs.map((tab) => Tab(
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(tab.icon, size: 18),
              const SizedBox(width: 6),
              Text(tab.label),
            ],
          ),
        )).toList(),
      ),
    );
  }
}

class _TabInfo {
  final String label;
  final IconData icon;

  const _TabInfo(this.label, this.icon);
}

/// 개별 탭 컨텐츠
class _ScreeningTabContent extends ConsumerWidget {
  final FutureProvider<ScreeningResponse> provider;

  const _ScreeningTabContent({required this.provider});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final screeningResult = ref.watch(provider);

    return screeningResult.when(
      loading: () => const LoadingWidget(message: '스크리닝 결과 로딩 중...'),
      error: (error, _) => AppErrorWidget(
        message: error.toString(),
        onRetry: () => ref.invalidate(provider),
      ),
      data: (data) => _ScreeningResultsView(data: data),
    );
  }
}

/// 스크리닝 결과 뷰
class _ScreeningResultsView extends StatelessWidget {
  final ScreeningResponse data;

  const _ScreeningResultsView({required this.data});

  @override
  Widget build(BuildContext context) {
    final hasSignals = data.strongBuy.isNotEmpty ||
        data.buy.isNotEmpty ||
        data.weakBuy.isNotEmpty;

    if (!hasSignals) {
      return const Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.search_off, size: 64, color: AppColors.textMuted),
            SizedBox(height: 16),
            Text(
              '조건에 맞는 종목이 없습니다',
              style: TextStyle(color: AppColors.textSecondary, fontSize: 16),
            ),
          ],
        ),
      );
    }

    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // 요약 통계
          _buildSummaryStats(),
          const SizedBox(height: 24),
          // 강력 매수
          if (data.strongBuy.isNotEmpty) ...[
            _SignalGroup(
              title: '강력 매수',
              count: data.strongBuy.length,
              color: AppColors.strongBuy,
              stocks: data.strongBuy,
            ),
            const SizedBox(height: 20),
          ],
          // 매수
          if (data.buy.isNotEmpty) ...[
            _SignalGroup(
              title: '매수',
              count: data.buy.length,
              color: AppColors.buy,
              stocks: data.buy,
            ),
            const SizedBox(height: 20),
          ],
          // 약매수
          if (data.weakBuy.isNotEmpty)
            _SignalGroup(
              title: '약매수',
              count: data.weakBuy.length,
              color: AppColors.weakBuy,
              stocks: data.weakBuy,
            ),
        ],
      ),
    );
  }

  Widget _buildSummaryStats() {
    return Row(
      children: [
        _StatChip(
          label: '총 종목',
          value: '${data.totalSignals}',
          icon: Icons.assessment,
        ),
        const SizedBox(width: 12),
        _StatChip(
          label: '강력 매수',
          value: '${data.strongBuy.length}',
          color: AppColors.strongBuy,
        ),
        const SizedBox(width: 12),
        _StatChip(
          label: '매수',
          value: '${data.buy.length}',
          color: AppColors.buy,
        ),
        const SizedBox(width: 12),
        _StatChip(
          label: '약매수',
          value: '${data.weakBuy.length}',
          color: AppColors.weakBuy,
        ),
      ],
    );
  }
}

/// 통계 칩
class _StatChip extends StatelessWidget {
  final String label;
  final String value;
  final Color? color;
  final IconData? icon;

  const _StatChip({
    required this.label,
    required this.value,
    this.color,
    this.icon,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
      decoration: BoxDecoration(
        color: (color ?? AppColors.accent).withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(
          color: (color ?? AppColors.accent).withValues(alpha: 0.3),
        ),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (icon != null) ...[
            Icon(icon, size: 16, color: color ?? AppColors.accent),
            const SizedBox(width: 6),
          ],
          Text(
            label,
            style: TextStyle(
              color: color ?? AppColors.textSecondary,
              fontSize: 12,
            ),
          ),
          const SizedBox(width: 8),
          Text(
            value,
            style: TextStyle(
              color: color ?? AppColors.accent,
              fontWeight: FontWeight.bold,
              fontSize: 16,
            ),
          ),
        ],
      ),
    );
  }
}

/// 신호 강도별 그룹
class _SignalGroup extends StatelessWidget {
  final String title;
  final int count;
  final Color color;
  final List<StockSignal> stocks;

  const _SignalGroup({
    required this.title,
    required this.count,
    required this.color,
    required this.stocks,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // 그룹 헤더
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
            decoration: BoxDecoration(
              color: color.withValues(alpha: 0.08),
              borderRadius: const BorderRadius.vertical(top: Radius.circular(11)),
              border: Border(
                bottom: BorderSide(color: color.withValues(alpha: 0.2)),
              ),
            ),
            child: Row(
              children: [
                Container(
                  width: 4,
                  height: 20,
                  decoration: BoxDecoration(
                    color: color,
                    borderRadius: BorderRadius.circular(2),
                  ),
                ),
                const SizedBox(width: 10),
                Text(
                  title,
                  style: TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.bold,
                    color: color,
                  ),
                ),
                const SizedBox(width: 8),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                  decoration: BoxDecoration(
                    color: color.withValues(alpha: 0.15),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: Text(
                    '$count',
                    style: TextStyle(
                      color: color,
                      fontWeight: FontWeight.bold,
                      fontSize: 13,
                    ),
                  ),
                ),
              ],
            ),
          ),
          // 종목 리스트
          ...stocks.map((stock) => _StockRow(stock: stock, groupColor: color)),
        ],
      ),
    );
  }
}

/// 개별 종목 행
class _StockRow extends StatelessWidget {
  final StockSignal stock;
  final Color groupColor;

  const _StockRow({required this.stock, required this.groupColor});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
      decoration: const BoxDecoration(
        border: Border(
          bottom: BorderSide(color: AppColors.border, width: 0.5),
        ),
      ),
      child: Row(
        children: [
          // 티커 & 이름
          Expanded(
            flex: 3,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  stock.ticker,
                  style: const TextStyle(
                    fontWeight: FontWeight.bold,
                    fontSize: 15,
                    color: AppColors.textPrimary,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  stock.name,
                  style: const TextStyle(
                    fontSize: 12,
                    color: AppColors.textSecondary,
                  ),
                  overflow: TextOverflow.ellipsis,
                ),
              ],
            ),
          ),
          // 현재가
          Expanded(
            flex: 2,
            child: Text(
              _formatPrice(stock.currentPrice, stock.market),
              style: const TextStyle(
                fontSize: 14,
                fontWeight: FontWeight.w500,
                color: AppColors.textPrimary,
              ),
              textAlign: TextAlign.right,
            ),
          ),
          // 점수
          Expanded(
            flex: 1,
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
              decoration: BoxDecoration(
                color: _scoreColor(stock.score).withValues(alpha: 0.12),
                borderRadius: BorderRadius.circular(6),
              ),
              child: Text(
                '${stock.score}점',
                style: TextStyle(
                  color: _scoreColor(stock.score),
                  fontWeight: FontWeight.bold,
                  fontSize: 13,
                ),
                textAlign: TextAlign.center,
              ),
            ),
          ),
          const SizedBox(width: 12),
          // 패턴
          Expanded(
            flex: 3,
            child: _buildPatternChips(stock),
          ),
        ],
      ),
    );
  }

  String _formatPrice(double price, String market) {
    if (market == 'KR') {
      return '₩${Formatters.number(price.toInt())}';
    }
    return '\$${Formatters.decimal(price)}';
  }

  Color _scoreColor(int score) {
    if (score >= 80) return AppColors.strongBuy;
    if (score >= 60) return AppColors.buy;
    if (score >= 40) return AppColors.weakBuy;
    return AppColors.textPrimary;
  }

  Widget _buildPatternChips(StockSignal stock) {
    final patterns = [...stock.activePatterns, ...stock.fundamentalPatterns];
    if (patterns.isEmpty) {
      return const Text(
        '-',
        style: TextStyle(color: AppColors.textMuted),
      );
    }

    return Wrap(
      spacing: 6,
      runSpacing: 4,
      children: patterns.take(4).map((pattern) {
        return Container(
          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
          decoration: BoxDecoration(
            color: AppColors.surfaceLight,
            borderRadius: BorderRadius.circular(4),
            border: Border.all(color: AppColors.border),
          ),
          child: Text(
            pattern,
            style: const TextStyle(
              fontSize: 11,
              color: AppColors.textSecondary,
            ),
          ),
        );
      }).toList(),
    );
  }
}
