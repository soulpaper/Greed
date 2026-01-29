import 'package:flutter/material.dart';

/// 앱 색상 상수 - 다크 테마 금융 대시보드 스타일
class AppColors {
  AppColors._();

  // 배경색
  static const Color background = Color(0xFF0D1117);
  static const Color surface = Color(0xFF161B22);
  static const Color surfaceLight = Color(0xFF21262D);
  static const Color border = Color(0xFF30363D);

  // 텍스트
  static const Color textPrimary = Color(0xFFE6EDF3);
  static const Color textSecondary = Color(0xFF8B949E);
  static const Color textMuted = Color(0xFF6E7681);

  // 시맨틱 색상
  static const Color positive = Color(0xFF3FB950); // 상승
  static const Color negative = Color(0xFFF85149); // 하락
  static const Color accent = Color(0xFF58A6FF); // 액센트
  static const Color warning = Color(0xFFD29922);
  static const Color info = Color(0xFF79C0FF);

  // 신호 강도 색상
  static const Color strongBuy = Color(0xFF238636);
  static const Color buy = Color(0xFF3FB950);
  static const Color weakBuy = Color(0xFF7EE787);
  static const Color neutral = Color(0xFF8B949E);
  static const Color weakSell = Color(0xFFFFA657);
  static const Color sell = Color(0xFFF85149);
  static const Color strongSell = Color(0xFFDA3633);

  // 차트 색상
  static const List<Color> chartColors = [
    Color(0xFF58A6FF),
    Color(0xFF3FB950),
    Color(0xFFF85149),
    Color(0xFFD29922),
    Color(0xFFA371F7),
    Color(0xFF79C0FF),
    Color(0xFF7EE787),
    Color(0xFFFFA657),
  ];
}
