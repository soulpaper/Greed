import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:fl_chart/fl_chart.dart';
import '../../../core/constants/app_colors.dart';
import '../../../core/utils/formatters.dart';
import '../../../data/models/history_models.dart';
import '../../providers/providers.dart';
import '../../widgets/loading_widget.dart';
import '../../widgets/error_widget.dart';

/// 히스토리 화면
class HistoryScreen extends ConsumerStatefulWidget {
  const HistoryScreen({super.key});

  @override
  ConsumerState<HistoryScreen> createState() => _HistoryScreenState();
}

class _HistoryScreenState extends ConsumerState<HistoryScreen> {
  DateTime? _startDate;
  DateTime? _endDate;
  String? _selectedExchange;
  String? _selectedTicker;

  @override
  void initState() {
    super.initState();
    final now = DateTime.now();
    _endDate = now;
    _startDate = now.subtract(const Duration(days: 30));
  }

  @override
  Widget build(BuildContext context) {
    final params = StockHistoryParams(
      startDate: _startDate,
      endDate: _endDate,
      exchange: _selectedExchange,
      ticker: _selectedTicker,
      limit: 500,
    );
    final historyData = ref.watch(stockHistoryProvider(params));

    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // 헤더
          Text(
            '히스토리',
            style: Theme.of(
              context,
            ).textTheme.headlineMedium?.copyWith(fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 24),

          // 필터 영역
          _buildFilters(),
          const SizedBox(height: 24),

          // 데이터 영역
          historyData.when(
            loading: () => const SizedBox(
              height: 400,
              child: LoadingWidget(message: '히스토리 로딩 중...'),
            ),
            error: (error, _) => AppErrorWidget(
              message: error.toString(),
              onRetry: () => ref.invalidate(stockHistoryProvider(params)),
            ),
            data: (data) => _buildContent(data),
          ),
        ],
      ),
    );
  }

  Widget _buildFilters() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Row(
          children: [
            // 시작일
            Expanded(
              child: _buildDatePicker(
                label: '시작일',
                value: _startDate,
                onChanged: (date) => setState(() => _startDate = date),
              ),
            ),
            const SizedBox(width: 16),
            // 종료일
            Expanded(
              child: _buildDatePicker(
                label: '종료일',
                value: _endDate,
                onChanged: (date) => setState(() => _endDate = date),
              ),
            ),
            const SizedBox(width: 16),
            // 거래소
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    '거래소',
                    style: TextStyle(
                      fontSize: 12,
                      color: AppColors.textSecondary,
                    ),
                  ),
                  const SizedBox(height: 4),
                  DropdownButtonFormField<String?>(
                    initialValue: _selectedExchange,
                    decoration: const InputDecoration(
                      isDense: true,
                      contentPadding: EdgeInsets.symmetric(
                        horizontal: 12,
                        vertical: 12,
                      ),
                    ),
                    items: const [
                      DropdownMenuItem(value: null, child: Text('전체')),
                      DropdownMenuItem(value: 'NASD', child: Text('NASD')),
                      DropdownMenuItem(value: 'NYSE', child: Text('NYSE')),
                      DropdownMenuItem(value: 'AMEX', child: Text('AMEX')),
                      DropdownMenuItem(value: 'TKSE', child: Text('TKSE')),
                    ],
                    onChanged: (value) =>
                        setState(() => _selectedExchange = value),
                  ),
                ],
              ),
            ),
            const SizedBox(width: 16),
            // 종목 검색
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    '종목 코드',
                    style: TextStyle(
                      fontSize: 12,
                      color: AppColors.textSecondary,
                    ),
                  ),
                  const SizedBox(height: 4),
                  TextField(
                    decoration: const InputDecoration(
                      hintText: '예: AAPL',
                      isDense: true,
                      contentPadding: EdgeInsets.symmetric(
                        horizontal: 12,
                        vertical: 12,
                      ),
                    ),
                    onChanged: (value) {
                      setState(() {
                        _selectedTicker = value.isEmpty
                            ? null
                            : value.toUpperCase();
                      });
                    },
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildDatePicker({
    required String label,
    required DateTime? value,
    required ValueChanged<DateTime> onChanged,
  }) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label,
          style: const TextStyle(fontSize: 12, color: AppColors.textSecondary),
        ),
        const SizedBox(height: 4),
        InkWell(
          onTap: () async {
            final picked = await showDatePicker(
              context: context,
              initialDate: value ?? DateTime.now(),
              firstDate: DateTime(2020),
              lastDate: DateTime.now(),
            );
            if (picked != null) {
              onChanged(picked);
            }
          },
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
            decoration: BoxDecoration(
              color: AppColors.surfaceLight,
              borderRadius: BorderRadius.circular(8),
              border: Border.all(color: AppColors.border),
            ),
            child: Row(
              children: [
                Text(
                  value != null ? Formatters.date(value) : '선택',
                  style: TextStyle(
                    color: value != null
                        ? AppColors.textPrimary
                        : AppColors.textMuted,
                  ),
                ),
                const Spacer(),
                const Icon(
                  Icons.calendar_today,
                  size: 18,
                  color: AppColors.textSecondary,
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildContent(StockHistoryResponse data) {
    if (data.records.isEmpty) {
      return const Card(
        child: Padding(
          padding: EdgeInsets.all(48),
          child: Center(
            child: Text(
              '데이터가 없습니다',
              style: TextStyle(color: AppColors.textSecondary),
            ),
          ),
        ),
      );
    }

    // 수익률 추이 데이터 준비
    final profitByDate = <DateTime, List<double>>{};
    for (final record in data.records) {
      final date = DateTime(
        record.recordDate.year,
        record.recordDate.month,
        record.recordDate.day,
      );
      profitByDate.putIfAbsent(date, () => []);
      if (record.profitLossRate != null) {
        profitByDate[date]!.add(record.profitLossRate!);
      }
    }

    return Column(
      children: [
        // 수익률 추이 차트
        if (profitByDate.length >= 2) _buildProfitChart(profitByDate),
        const SizedBox(height: 24),

        // 데이터 테이블
        Card(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Padding(
                padding: const EdgeInsets.all(20),
                child: Row(
                  children: [
                    const Text(
                      '기록 데이터',
                      style: TextStyle(
                        fontSize: 18,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    const Spacer(),
                    Text(
                      '총 ${data.totalCount}건',
                      style: const TextStyle(color: AppColors.textSecondary),
                    ),
                  ],
                ),
              ),
              const Divider(height: 1),
              SingleChildScrollView(
                scrollDirection: Axis.horizontal,
                child: DataTable(
                  columns: const [
                    DataColumn(label: Text('날짜')),
                    DataColumn(label: Text('거래소')),
                    DataColumn(label: Text('종목')),
                    DataColumn(label: Text('수량'), numeric: true),
                    DataColumn(label: Text('매입가'), numeric: true),
                    DataColumn(label: Text('현재가'), numeric: true),
                    DataColumn(label: Text('평가금액'), numeric: true),
                    DataColumn(label: Text('수익률'), numeric: true),
                  ],
                  rows: data.records.take(100).map((record) {
                    final profitRate = record.profitLossRate ?? 0;
                    return DataRow(
                      cells: [
                        DataCell(Text(Formatters.date(record.recordDate))),
                        DataCell(Text(record.exchange)),
                        DataCell(
                          Column(
                            mainAxisAlignment: MainAxisAlignment.center,
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                record.ticker,
                                style: const TextStyle(
                                  fontWeight: FontWeight.bold,
                                ),
                              ),
                              if (record.stockName != null)
                                Text(
                                  record.stockName!,
                                  style: const TextStyle(
                                    fontSize: 11,
                                    color: AppColors.textSecondary,
                                  ),
                                ),
                            ],
                          ),
                        ),
                        DataCell(Text(Formatters.number(record.quantity))),
                        DataCell(
                          Text(Formatters.decimal(record.avgPurchasePrice)),
                        ),
                        DataCell(Text(Formatters.decimal(record.currentPrice))),
                        DataCell(
                          Text(Formatters.compactAmount(record.evalAmount)),
                        ),
                        DataCell(
                          Text(
                            Formatters.profitRate(profitRate),
                            style: TextStyle(
                              color: profitRate >= 0
                                  ? AppColors.positive
                                  : AppColors.negative,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                        ),
                      ],
                    );
                  }).toList(),
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildProfitChart(Map<DateTime, List<double>> profitByDate) {
    final sortedDates = profitByDate.keys.toList()..sort();
    final spots = <FlSpot>[];

    for (var i = 0; i < sortedDates.length; i++) {
      final avgProfit =
          profitByDate[sortedDates[i]]!.reduce((a, b) => a + b) /
          profitByDate[sortedDates[i]]!.length;
      spots.add(FlSpot(i.toDouble(), avgProfit));
    }

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              '평균 수익률 추이',
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 24),
            SizedBox(
              height: 250,
              child: LineChart(
                LineChartData(
                  gridData: FlGridData(
                    show: true,
                    drawVerticalLine: false,
                    getDrawingHorizontalLine: (value) =>
                        FlLine(color: AppColors.border, strokeWidth: 1),
                  ),
                  titlesData: FlTitlesData(
                    leftTitles: AxisTitles(
                      sideTitles: SideTitles(
                        showTitles: true,
                        reservedSize: 50,
                        getTitlesWidget: (value, meta) => Text(
                          '${value.toStringAsFixed(1)}%',
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
                    topTitles: const AxisTitles(
                      sideTitles: SideTitles(showTitles: false),
                    ),
                    rightTitles: const AxisTitles(
                      sideTitles: SideTitles(showTitles: false),
                    ),
                  ),
                  borderData: FlBorderData(show: false),
                  lineBarsData: [
                    LineChartBarData(
                      spots: spots,
                      isCurved: true,
                      color: AppColors.positive,
                      barWidth: 2,
                      dotData: const FlDotData(show: false),
                      belowBarData: BarAreaData(
                        show: true,
                        color: AppColors.positive.withValues(alpha: 0.1),
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
}
