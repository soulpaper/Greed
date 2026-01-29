import 'package:flutter/material.dart';
import '../../core/constants/app_colors.dart';
import '../../data/models/screening_models.dart';

/// 신호 강도 배지
class SignalBadge extends StatelessWidget {
  final SignalStrength signal;
  final bool compact;

  const SignalBadge({
    super.key,
    required this.signal,
    this.compact = false,
  });

  Color get _color {
    switch (signal) {
      case SignalStrength.strongBuy:
        return AppColors.strongBuy;
      case SignalStrength.buy:
        return AppColors.buy;
      case SignalStrength.weakBuy:
        return AppColors.weakBuy;
      case SignalStrength.neutral:
        return AppColors.neutral;
      case SignalStrength.weakSell:
        return AppColors.weakSell;
      case SignalStrength.sell:
        return AppColors.sell;
      case SignalStrength.strongSell:
        return AppColors.strongSell;
    }
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: EdgeInsets.symmetric(
        horizontal: compact ? 8 : 12,
        vertical: compact ? 4 : 6,
      ),
      decoration: BoxDecoration(
        color: _color.withValues(alpha: 0.15),
        borderRadius: BorderRadius.circular(6),
        border: Border.all(color: _color.withValues(alpha: 0.5)),
      ),
      child: Text(
        signal.displayName,
        style: TextStyle(
          color: _color,
          fontSize: compact ? 11 : 13,
          fontWeight: FontWeight.w600,
        ),
      ),
    );
  }
}
