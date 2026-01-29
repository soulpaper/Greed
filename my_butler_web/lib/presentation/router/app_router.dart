import 'package:go_router/go_router.dart';
import '../screens/dashboard/dashboard_screen.dart';
import '../screens/screening/screening_screen.dart';
import '../screens/history/history_screen.dart';
import '../screens/tags/tags_screen.dart';
import '../widgets/app_scaffold.dart';

/// 앱 라우터 설정
final appRouter = GoRouter(
  initialLocation: '/',
  routes: [
    ShellRoute(
      builder: (context, state, child) => AppScaffold(child: child),
      routes: [
        GoRoute(
          path: '/',
          name: 'dashboard',
          pageBuilder: (context, state) => const NoTransitionPage(
            child: DashboardScreen(),
          ),
        ),
        GoRoute(
          path: '/screening',
          name: 'screening',
          pageBuilder: (context, state) => const NoTransitionPage(
            child: ScreeningScreen(),
          ),
        ),
        GoRoute(
          path: '/history',
          name: 'history',
          pageBuilder: (context, state) => const NoTransitionPage(
            child: HistoryScreen(),
          ),
        ),
        GoRoute(
          path: '/tags',
          name: 'tags',
          pageBuilder: (context, state) => const NoTransitionPage(
            child: TagsScreen(),
          ),
        ),
      ],
    ),
  ],
);
