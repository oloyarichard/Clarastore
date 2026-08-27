import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/api_client.dart';
import '../../providers/auth_provider.dart';
import '../../widgets/loading_button.dart';

class ProfileScreen extends ConsumerStatefulWidget {
  const ProfileScreen({super.key});

  @override
  ConsumerState<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends ConsumerState<ProfileScreen> {
  final _formKey = GlobalKey<FormState>();
  late TextEditingController _firstNameController;
  late TextEditingController _lastNameController;
  late TextEditingController _phoneController;
  int? _selectedDistrict;
  bool _saving = false;
  bool _initialized = false;

  @override
  Widget build(BuildContext context) {
    final userAsync = ref.watch(authProvider);
    final districtsAsync = ref.watch(districtsProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Profile'),
        actions: [
          IconButton(
            icon: const Icon(Icons.logout),
            onPressed: () async {
              await ref.read(authProvider.notifier).logout();
              if (context.mounted) context.go('/login');
            },
          ),
        ],
      ),
      body: userAsync.when(
        data: (user) {
          if (user == null) return const Center(child: Text('Not logged in.'));
          if (!_initialized) {
            _firstNameController = TextEditingController(text: user.firstName);
            _lastNameController = TextEditingController(text: user.lastName);
            _phoneController = TextEditingController(text: user.phone);
            _selectedDistrict = user.district;
            _initialized = true;
          }
          return Padding(
            padding: const EdgeInsets.all(20),
            child: Form(
              key: _formKey,
              child: ListView(
                children: [
                  Text(user.email, style: TextStyle(color: Colors.grey.shade600)),
                  const SizedBox(height: 20),
                  TextFormField(
                    controller: _firstNameController,
                    decoration: const InputDecoration(labelText: 'First name'),
                  ),
                  const SizedBox(height: 12),
                  TextFormField(
                    controller: _lastNameController,
                    decoration: const InputDecoration(labelText: 'Last name'),
                  ),
                  const SizedBox(height: 12),
                  TextFormField(
                    controller: _phoneController,
                    keyboardType: TextInputType.phone,
                    decoration: const InputDecoration(labelText: 'Phone'),
                  ),
                  const SizedBox(height: 12),
                  districtsAsync.when(
                    data: (districts) => DropdownButtonFormField<int>(
                      value: _selectedDistrict,
                      decoration: const InputDecoration(labelText: 'District'),
                      items: districts
                          .map((d) => DropdownMenuItem(value: d.id, child: Text(d.name)))
                          .toList(),
                      onChanged: (v) => setState(() => _selectedDistrict = v),
                    ),
                    loading: () => const LinearProgressIndicator(),
                    error: (e, _) => Text(apiErrorMessage(e)),
                  ),
                  const SizedBox(height: 24),
                  LoadingButton(
                    label: 'Save changes',
                    isLoading: _saving,
                    onPressed: () async {
                      setState(() => _saving = true);
                      try {
                        await ref.read(authServiceProvider).updateProfile({
                          'first_name': _firstNameController.text.trim(),
                          'last_name': _lastNameController.text.trim(),
                          'phone': _phoneController.text.trim(),
                          'district': _selectedDistrict,
                        });
                        await ref.read(authProvider.notifier).refreshProfile();
                        if (context.mounted) {
                          ScaffoldMessenger.of(context)
                              .showSnackBar(const SnackBar(content: Text('Profile updated')));
                        }
                      } catch (e) {
                        if (context.mounted) {
                          ScaffoldMessenger.of(context)
                              .showSnackBar(SnackBar(content: Text(apiErrorMessage(e))));
                        }
                      } finally {
                        if (mounted) setState(() => _saving = false);
                      }
                    },
                  ),
                ],
              ),
            ),
          );
        },
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(child: Text(apiErrorMessage(e))),
      ),
    );
  }
}
