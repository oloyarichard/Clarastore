import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/api_client.dart';
import '../../providers/auth_provider.dart';
import '../../widgets/loading_button.dart';

class SignupScreen extends ConsumerStatefulWidget {
  const SignupScreen({super.key});

  @override
  ConsumerState<SignupScreen> createState() => _SignupScreenState();
}

class _SignupScreenState extends ConsumerState<SignupScreen> {
  final _formKey = GlobalKey<FormState>();
  final _firstNameController = TextEditingController();
  final _lastNameController = TextEditingController();
  final _emailController = TextEditingController();
  final _phoneController = TextEditingController();
  final _passwordController = TextEditingController();
  final _confirmController = TextEditingController();
  int? _selectedDistrict;

  @override
  Widget build(BuildContext context) {
    final authState = ref.watch(authProvider);
    final isLoading = authState.isLoading;
    final districtsAsync = ref.watch(districtsProvider);

    ref.listen(authProvider, (previous, next) {
      next.whenOrNull(
        error: (error, _) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text(apiErrorMessage(error))),
          );
        },
      );
    });

    return Scaffold(
      appBar: AppBar(title: const Text('Create account')),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Form(
            key: _formKey,
            child: ListView(
              children: [
                Row(
                  children: [
                    Expanded(
                      child: TextFormField(
                        controller: _firstNameController,
                        decoration: const InputDecoration(labelText: 'First name'),
                        validator: (v) => (v == null || v.isEmpty) ? 'Required' : null,
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: TextFormField(
                        controller: _lastNameController,
                        decoration: const InputDecoration(labelText: 'Last name'),
                        validator: (v) => (v == null || v.isEmpty) ? 'Required' : null,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 16),
                TextFormField(
                  controller: _emailController,
                  keyboardType: TextInputType.emailAddress,
                  decoration: const InputDecoration(labelText: 'Email'),
                  validator: (v) => (v == null || !v.contains('@')) ? 'Enter a valid email' : null,
                ),
                const SizedBox(height: 16),
                TextFormField(
                  controller: _phoneController,
                  keyboardType: TextInputType.phone,
                  decoration: const InputDecoration(labelText: 'Phone number', hintText: '07XXXXXXXX'),
                  validator: (v) => (v == null || v.length < 9) ? 'Enter a valid phone number' : null,
                ),
                const SizedBox(height: 16),
                districtsAsync.when(
                  data: (districts) => DropdownButtonFormField<int>(
                    value: _selectedDistrict,
                    decoration: const InputDecoration(labelText: 'Delivery district'),
                    items: districts
                        .map((d) => DropdownMenuItem(
                              value: d.id,
                              child: Text(d.isHub ? '${d.name} (Hub)' : d.name),
                            ))
                        .toList(),
                    onChanged: (v) => setState(() => _selectedDistrict = v),
                    validator: (v) => v == null ? 'Select your district' : null,
                  ),
                  loading: () => const LinearProgressIndicator(),
                  error: (e, _) => Text('Could not load districts: ${apiErrorMessage(e)}'),
                ),
                const SizedBox(height: 16),
                TextFormField(
                  controller: _passwordController,
                  obscureText: true,
                  decoration: const InputDecoration(labelText: 'Password'),
                  validator: (v) => (v == null || v.length < 8) ? 'At least 8 characters' : null,
                ),
                const SizedBox(height: 16),
                TextFormField(
                  controller: _confirmController,
                  obscureText: true,
                  decoration: const InputDecoration(labelText: 'Confirm password'),
                  validator: (v) =>
                      v != _passwordController.text ? 'Passwords do not match' : null,
                ),
                const SizedBox(height: 24),
                LoadingButton(
                  label: 'Create account',
                  isLoading: isLoading,
                  onPressed: () {
                    if (_formKey.currentState!.validate()) {
                      ref.read(authProvider.notifier).register(
                            email: _emailController.text.trim(),
                            password: _passwordController.text,
                            passwordConfirm: _confirmController.text,
                            firstName: _firstNameController.text.trim(),
                            lastName: _lastNameController.text.trim(),
                            phone: _phoneController.text.trim(),
                            districtId: _selectedDistrict!,
                          );
                    }
                  },
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
