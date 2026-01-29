import 'package:intl/intl.dart';

/// 포맷팅 유틸리티
class Formatters {
  Formatters._();

  static final _currencyKRW = NumberFormat.currency(locale: 'ko_KR', symbol: '₩');
  static final _currencyUSD = NumberFormat.currency(locale: 'en_US', symbol: '\$');
  static final _number = NumberFormat('#,###', 'ko_KR');
  static final _percent = NumberFormat('0.00%', 'ko_KR');
  static final _decimal = NumberFormat('#,##0.00', 'ko_KR');
  static final _dateFormat = DateFormat('yyyy-MM-dd');
  static final _dateTimeFormat = DateFormat('yyyy-MM-dd HH:mm');

  /// 통화 포맷 (원화)
  static String currencyKRW(num? value) {
    if (value == null) return '-';
    return _currencyKRW.format(value);
  }

  /// 통화 포맷 (달러)
  static String currencyUSD(num? value) {
    if (value == null) return '-';
    return _currencyUSD.format(value);
  }

  /// 통화 포맷 (자동 선택)
  static String currency(num? value, String? currencyCode) {
    if (currencyCode == 'KRW') return currencyKRW(value);
    return currencyUSD(value);
  }

  /// 숫자 포맷 (천단위 콤마)
  static String number(num? value) {
    if (value == null) return '-';
    return _number.format(value);
  }

  /// 퍼센트 포맷
  static String percent(num? value) {
    if (value == null) return '-';
    return _percent.format(value / 100);
  }

  /// 소수점 포맷
  static String decimal(num? value) {
    if (value == null) return '-';
    return _decimal.format(value);
  }

  /// 날짜 포맷
  static String date(DateTime? value) {
    if (value == null) return '-';
    return _dateFormat.format(value);
  }

  /// 날짜시간 포맷
  static String dateTime(DateTime? value) {
    if (value == null) return '-';
    return _dateTimeFormat.format(value);
  }

  /// 수익률 포맷 (부호 포함)
  static String profitRate(num? value) {
    if (value == null) return '-';
    final sign = value >= 0 ? '+' : '';
    return '$sign${percent(value)}';
  }

  /// 금액 축약 (억, 만)
  static String compactAmount(num? value) {
    if (value == null) return '-';
    if (value >= 100000000) {
      return '${_decimal.format(value / 100000000)}억';
    } else if (value >= 10000) {
      return '${_decimal.format(value / 10000)}만';
    }
    return _number.format(value);
  }
}
