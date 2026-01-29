import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:fl_chart/fl_chart.dart';
import '../../../core/constants/app_colors.dart';
import '../../../core/utils/formatters.dart';
import '../../providers/providers.dart';
import '../../widgets/loading_widget.dart';
import '../../widgets/error_widget.dart';
import '../../widgets/stat_card.dart';
import '../../widgets/signal_badge.dart';

/// 대시보드 화면
class DashboardScreen extends ConsumerWidget {
  const DashboardScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final dashboardData = ref.watch(dashboardDataProvider);

    return dashboardData.when(
      loading: () => const LoadingWidget(message: '데이터 로딩 중...'),
      error: (error, _) => AppErrorWidget(
        message: error.toString(),
        onRetry: () => ref.invalidate(dashboardDataProvider),
      ),
      data: (data) => _DashboardContent(data: data),
    );
  }
}

class _DashboardContent extends StatelessWidget {
  final DashboardData data;

  const _DashboardContent({required this.data});

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // 헤더
          Row(
            children: [
              Text(
                '포트폴리오 대시보드',
                style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                      fontWeight: FontWeight.bold,
                    ),
              ),
              const Spacer(),
              Text(
                '기준일: ${Formatters.date(data.latestRecords.recordDate)}',
                style: const TextStyle(color: AppColors.textSecondary),
              ),
            ],
          ),
          const SizedBox(height: 24),

          // 요약 카드들
          _buildSummaryCards(),
          const SizedBox(height: 24),

          // 차트 영역
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // 자산 추이 차트
              Expanded(
                flex: 2,
                child: _buildAssetTrendChart(),
              ),
              const SizedBox(width: 24),
              // 자산 배분 차트
              Expanded(
                child: _buildAssetAllocationChart(),
              ),
            ],
          ),
          const SizedBox(height: 24),

          // 추천 종목
          if (data.recommendations != null) _buildRecommendations(),
        ],
      ),
    );
  }

  Widget _buildSummaryCards() {
    final summaries = data.summaryHistory.records;
    if (summaries.isEmpty) {
      return const Card(
        child: Padding(
          padding: EdgeInsets.all(24),
          child: Center(child: Text('기록된 데이터가 없습니다')),
        ),
      );
    }

    // 거래소별 최신 요약 계산
    final latestByExchange = <String, dynamic>{};
    double totalEval = 0;
    double totalPurchase = 0;

    for (final summary in summaries) {
      if (!latestByExchange.containsKey(summary.exchange)) {
        latestByExchange[summary.exchange] = summary;
        totalEval += summary.totalEvalAmount ?? 0;
        totalPurchase += summary.totalPurchaseAmount ?? 0;
      }
    }

    final totalProfit = totalEval - totalPurchase;
    final totalProfitRate = totalPurchase > 0 ? (totalProfit / totalPurchase) * 100 : 0.0;

    return Wrap(
      spacing: 16,
      runSpacing: 16,
      children: [
        SizedBox(
          width: 280,
          child: StatCard(
            title: '총 평가금액',
            value: Formatters.compactAmount(totalEval),
            icon: Icons.account_balance_wallet,
            subtitle: '${data.latestRecords.totalStocks}개 종목',
          ),
        ),
        SizedBox(
          width: 280,
          child: StatCard(
            title: '총 수익/손실',
            value: Formatters.compactAmount(totalProfit),
            valueColor: totalProfit >= 0 ? AppColors.positive : AppColors.negative,
            icon: Icons.trending_up,
            subtitle: Formatters.profitRate(totalProfitRate),
          ),
        ),
        SizedBox(
          width: 280,
          child: StatCard(
            title: '투자원금',
            value: Formatters.compactAmount(totalPurchase),
            icon: Icons.savings,
          ),
        ),
        SizedBox(
          width: 280,
          child: StatCard(
            title: '거래소',
            value: '${latestByExchange.length}개',
            icon: Icons.business,
            subtitle: latestByExchange.keys.join(', '),
          ),
        ),
      ],
    );
  }

  Widget _buildAssetTrendChart() {
    final summaries = data.summaryHistory.records.reversed.toList();
    if (summaries.length < 2) {
      return Card(
        child: Container(
          height: 350,
          padding: const EdgeInsets.all(24),
          child: const Center(child: Text('차트를 표시하려면 최소 2일 이상의 데이터가 필요합니다')),
        ),
      );
    }

    // 날짜별 총 평가금액 집계
    final dailyTotals = <DateTime, double>{};
    for (final summary in summaries) {
      final date = DateTime(
        summary.recordDate.year,
        summary.recordDate.month,
        summary.recordDate.day,
      );
      dailyTotals[date] = (dailyTotals[date] ?? 0) + (summary.totalEvalAmount ?? 0);
    }

    final sortedDates = dailyTotals.keys.toList()..sort();
    final spots = <FlSpot>[];
    for (var i = 0; i < sortedDates.length; i++) {
      spots.add(FlSpot(i.toDouble(), dailyTotals[sortedDates[i]]! / 1000000));
    }

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              '자산 추이',
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 24),
            SizedBox(
              height: 280,
              child: LineChart(
                LineChartData(
                  gridData: FlGridData(
                    show: true,
                    drawVerticalLine: false,
                    horizontalInterval: 1,
                    getDrawingHorizontalLine: (value) => FlLine(
                      color: AppColors.border,
                      strokeWidth: 1,
                    ),
                  ),
                  titlesData: FlTitlesData(
                    leftTitles: AxisTitles(
                      sideTitles: SideTitles(
                        showTitles: true,
                        reservedSize: 60,
                        getTitlesWidget: (value, meta) => Text(
                          '${value.toInt()}M',
                          style: const TextStyle(
                            color: AppColors.textMuted,
                            fontSize: 11,
                          ),
                        ),
                      ),
                    ),
                    bottomTitles: AxisTitles(
                      sideTitles: SideTitles(
                        showTitles: true,
                        reservedSize: 32,
                        interval: (sortedDates.length / 5).ceilToDouble(),
                        getTitlesWidget: (value, meta) {
                          final index = value.toInt();
                          if (index < 0 || index >= sortedDates.length) {
                            return const SizedBox();
                          }
                          return Padding(
                            padding: const EdgeInsets.only(top: 8),
                            child: Text(
                              '${sortedDates[index].month}/${sortedDates[index].day}',
                              style: const TextStyle(
                                color: AppColors.textMuted,
                                fontSize: 11,
                              ),
                            ),
                          );
                        },
                      ),
                    ),
                    topTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
                    rightTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
                  ),
                  borderData: FlBorderData(show: false),
                  lineBarsData: [
                    LineChartBarData(
                      spots: spots,
                      isCurved: true,
                      color: AppColors.accent,
                      barWidth: 3,
                      dotData: const FlDotData(show: false),
                      belowBarData: BarAreaData(
                        show: true,
                        color: AppColors.accent.withValues(alpha: 0.1),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildAssetAllocationChart() {
    final exchanges = data.latestRecords.exchanges;
    if (exchanges.isEmpty) {
      return Card(
        child: Container(
          height: 350,
          padding: const EdgeInsets.all(24),
          child: const Center(child: Text('데이터 없음')),
        ),
      );
    }

    final sections = <PieChartSectionData>[];
    var colorIndex = 0;

    exchanges.forEach((exchange, info) {
      final evalAmount = (info['total_eval_amount'] ?? 0).toDouble();
      if (evalAmount > 0) {
        sections.add(
          PieChartSectionData(
            value: evalAmount,
            title: exchange,
            color: AppColors.chartColors[colorIndex % AppColors.chartColors.length],
            radius: 80,
            titleStyle: const TextStyle(
              color: Colors.white,
              fontSize: 12,
              fontWeight: FontWeight.bold,
            ),
          ),
        );
        colorIndex++;
      }
    });

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              '자산 배분',
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 24),
            SizedBox(
              height: 280,
              child: PieChart(
                PieChartData(
                  sections: sections,
                  sectionsSpace: 2,
                  centerSpaceRadius: 50,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildRecommendations() {
    final rec = data.recommendations!;
    final allRecs = [...rec.usRecommendations, ...rec.krRecommendations];

    if (allRecs.isEmpty) {
      return const SizedBox();
    }

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Text(
                  '오늘의 추천 종목',
                  style: TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const Spacer(),
                Text(
                  Formatters.date(rec.date),
                  style: const TextStyle(color: AppColors.textSecondary),
                ),
              ],
            ),
            const SizedBox(height: 16),
            SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              child: DataTable(
                columns: const [
                  DataColumn(label: Text('종목')),
                  DataColumn(label: Text('시장')),
                  DataColumn(label: Text('현재가'), numeric: true),
                  DataColumn(label: Text('신호')),
                  DataColumn(label: Text('점수'), numeric: true),
                ],
                rows: allRecs.take(10).map((stock) {
                  return DataRow(cells: [
                    DataCell(Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(stock.ticker, style: const TextStyle(fontWeight: FontWeight.bold)),
                        Text(stock.name, style: const TextStyle(fontSize: 12, color: AppColors.textSecondary)),
                      ],
                    )),
                    DataCell(Text(stock.market)),
                    DataCell(Text(Formatters.decimal(stock.currentPrice))),
                    DataCell(SignalBadge(signal: stock.signalType, compact: true)),
                    DataCell(Text(
                      '${stock.score}',
                      style: TextStyle(
                        color: stock.score >= 70 ? AppColors.positive : AppColors.textPrimary,
                        fontWeight: FontWeight.bold,
                      ),
                    )),
                  ]);
                }).toList(),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
