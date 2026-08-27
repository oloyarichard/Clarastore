import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../providers/auth_provider.dart';
import '../screens/agent/agent_dashboard_screen.dart';
import '../screens/agent/agent_shell.dart';
import '../screens/agent/agent_topup_customer_screen.dart';
import '../screens/agent/agent_wallet_screen.dart';
import '../screens/auth/login_screen.dart';
import '../screens/auth/signup_screen.dart';
import '../screens/customer/cart_screen.dart';
import '../screens/customer/checkout_screen.dart';
import '../screens/customer/customer_shell.dart';
import '../screens/customer/home_screen.dart';
import '../screens/customer/order_detail_screen.dart';
import '../screens/customer/orders_screen.dart';
import '../screens/customer/product_detail_screen.dart';
import '../screens/customer/profile_screen.dart';
import '../screens/customer/wallet_screen.dart';
import '../screens/splash_screen.dart';

/// Bridges Riverpod's async auth state to go_router's imperative
/// refreshListenable — a route re-evaluation is triggered any time login
/// state changes (login, logout, token expiry detected).
class _RouterRefreshNotifier extends ChangeNotifier {
  _RouterRefreshNotifier(Ref ref) {
    ref.listen(authProvider, (previous, next) {
      if (previous?.valueOrNull != next.valueOrNull || previous?.isLoading != next.isLoading) {
        notifyListeners();
      }
    });
  }
}

const _customerTabs = ['/home', '/orders', '/cart', '/wallet'];
const _agentTabs = ['/agent/dashboard', '/agent/orders', '/agent/wallet', '/agent/profile'];

final routerProvider = Provider<GoRouter>((ref) {
  final refreshNotifier = _RouterRefreshNotifier(ref);

  return GoRouter(
    initialLocation: '/splash',
    refreshListenable: refreshNotifier,
    redirect: (context, state) {
      final authState = ref.read(authProvider);
      final loc = state.matchedLocation;

      // Still checking for a stored session — hold on splash.
      if (authState.isLoading) {
        return loc == '/splash' ? null : '/splash';
      }

      final user = authState.valueOrNull;
      final loggedIn = user != null;
      final isAuthRoute = loc == '/login' || loc == '/signup';

      if (loc == '/splash') {
        if (!loggedIn) return '/home';
        return user.isAgent ? '/agent/dashboard' : '/home';
      }

      // Guests can browse and cart, per the guest-browsing decision —
      // everything else (checkout, orders, wallet, profile, agent screens)
      // requires being signed in.
      final guestAllowedPrefixes = ['/product/', '/login', '/signup'];
      final isGuestAllowed = loc == '/home' ||
          loc == '/cart' ||
          guestAllowedPrefixes.any((p) => loc.startsWith(p));

      if (!loggedIn && !isGuestAllowed) {
        return '/login';
      }

      if (loggedIn && isAuthRoute) {
        return user.isAgent ? '/agent/dashboard' : '/home';
      }

      // Keep customers out of the agent area and vice versa.
      if (loggedIn && user.isAgent && (loc == '/home' || loc == '/cart' || loc == '/checkout')) {
        return '/agent/dashboard';
      }
      if (loggedIn && !user.isAgent && loc.startsWith('/agent')) {
        return '/home';
      }

      return null;
    },
    routes: [
      GoRoute(path: '/splash', builder: (context, state) => const SplashScreen()),
      GoRoute(path: '/login', builder: (context, state) => const LoginScreen()),
      GoRoute(path: '/signup', builder: (context, state) => const SignupScreen()),

      // --- Customer shell (bottom nav) ---
      ShellRoute(
        builder: (context, state, child) => CustomerShell(
          currentIndex: _tabIndex(_customerTabs, state.matchedLocation),
          child: child,
        ),
        routes: [
          GoRoute(path: '/home', builder: (context, state) => const HomeScreen()),
          GoRoute(path: '/orders', builder: (context, state) => const OrdersScreen()),
          GoRoute(path: '/cart', builder: (context, state) => const CartScreen()),
          GoRoute(path: '/wallet', builder: (context, state) => const WalletScreen()),
        ],
      ),

      // --- Agent shell (bottom nav) ---
      ShellRoute(
        builder: (context, state, child) => AgentShell(
          currentIndex: _tabIndex(_agentTabs, state.matchedLocation),
          child: child,
        ),
        routes: [
          GoRoute(path: '/agent/dashboard', builder: (context, state) => const AgentDashboardScreen()),
          GoRoute(path: '/agent/orders', builder: (context, state) => const OrdersScreen()),
          GoRoute(path: '/agent/wallet', builder: (context, state) => const AgentWalletScreen()),
          GoRoute(path: '/agent/profile', builder: (context, state) => const ProfileScreen()),
        ],
      ),

      // --- Full-screen routes (pushed on top, not part of a tab shell) ---
      GoRoute(
        path: '/product/:id',
        builder: (context, state) =>
            ProductDetailScreen(productId: int.parse(state.pathParameters['id']!)),
      ),
      GoRoute(path: '/checkout', builder: (context, state) => const CheckoutScreen()),
      GoRoute(
        path: '/orders/:id',
        builder: (context, state) =>
            OrderDetailScreen(orderId: int.parse(state.pathParameters['id']!)),
      ),
      GoRoute(path: '/profile', builder: (context, state) => const ProfileScreen()),
      GoRoute(
        path: '/agent/topup-customer',
        builder: (context, state) => const AgentTopUpCustomerScreen(),
      ),
    ],
  );
});

int _tabIndex(List<String> tabs, String location) {
  final index = tabs.indexWhere((t) => location.startsWith(t));
  return index == -1 ? 0 : index;
}
