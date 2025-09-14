/// DB Design System v3.1.1 Components
/// 
/// This file implements reusable UI components following the 
/// Deutsche Bahn Design System specifications

import 'package:flutter/material.dart';
import 'db_theme.dart';

/// DB-styled primary button following Design System v3
class DBButton extends StatelessWidget {
  final String text;
  final VoidCallback? onPressed;
  final IconData? icon;
  final bool isLoading;
  final DBButtonType type;
  final DBButtonSize size;

  const DBButton({
    super.key,
    required this.text,
    this.onPressed,
    this.icon,
    this.isLoading = false,
    this.type = DBButtonType.primary,
    this.size = DBButtonSize.medium,
  });

  @override
  Widget build(BuildContext context) {
    Widget button;
    
    switch (type) {
      case DBButtonType.primary:
        button = _buildElevatedButton(context);
        break;
      case DBButtonType.secondary:
        button = _buildOutlinedButton(context);
        break;
      case DBButtonType.tertiary:
        button = _buildTextButton(context);
        break;
    }

    if (isLoading) {
      return Stack(
        alignment: Alignment.center,
        children: [
          button,
          SizedBox(
            width: 16,
            height: 16,
            child: CircularProgressIndicator(
              strokeWidth: 2,
              valueColor: AlwaysStoppedAnimation<Color>(
                type == DBButtonType.primary ? Colors.white : DBColors.dbRed,
              ),
            ),
          ),
        ],
      );
    }

    return button;
  }

  Widget _buildElevatedButton(BuildContext context) {
    return ElevatedButton.icon(
      onPressed: isLoading ? null : onPressed,
      icon: icon != null ? Icon(icon, size: _getIconSize()) : const SizedBox.shrink(),
      label: Text(text),
      style: ElevatedButton.styleFrom(
        backgroundColor: DBColors.dbRed,
        foregroundColor: Colors.white,
        padding: _getPadding(),
        minimumSize: _getMinimumSize(),
        textStyle: _getTextStyle(),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(DBBorderRadius.sm),
        ),
      ),
    );
  }

  Widget _buildOutlinedButton(BuildContext context) {
    return OutlinedButton.icon(
      onPressed: isLoading ? null : onPressed,
      icon: icon != null ? Icon(icon, size: _getIconSize()) : const SizedBox.shrink(),
      label: Text(text),
      style: OutlinedButton.styleFrom(
        foregroundColor: DBColors.dbRed,
        side: const BorderSide(color: DBColors.dbRed, width: 1.5),
        padding: _getPadding(),
        minimumSize: _getMinimumSize(),
        textStyle: _getTextStyle(),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(DBBorderRadius.sm),
        ),
      ),
    );
  }

  Widget _buildTextButton(BuildContext context) {
    return TextButton.icon(
      onPressed: isLoading ? null : onPressed,
      icon: icon != null ? Icon(icon, size: _getIconSize()) : const SizedBox.shrink(),
      label: Text(text),
      style: TextButton.styleFrom(
        foregroundColor: DBColors.dbRed,
        padding: _getPadding(),
        minimumSize: _getMinimumSize(),
        textStyle: _getTextStyle(),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(DBBorderRadius.sm),
        ),
      ),
    );
  }

  EdgeInsets _getPadding() {
    switch (size) {
      case DBButtonSize.small:
        return const EdgeInsets.symmetric(horizontal: DBSpacing.md, vertical: DBSpacing.sm);
      case DBButtonSize.medium:
        return const EdgeInsets.symmetric(horizontal: DBSpacing.lg, vertical: DBSpacing.md);
      case DBButtonSize.large:
        return const EdgeInsets.symmetric(horizontal: DBSpacing.xl, vertical: DBSpacing.lg);
    }
  }

  Size _getMinimumSize() {
    switch (size) {
      case DBButtonSize.small:
        return const Size(64, 32);
      case DBButtonSize.medium:
        return const Size(64, 40);
      case DBButtonSize.large:
        return const Size(64, 48);
    }
  }

  TextStyle _getTextStyle() {
    switch (size) {
      case DBButtonSize.small:
        return DBTextStyles.labelSmall;
      case DBButtonSize.medium:
        return DBTextStyles.labelMedium;
      case DBButtonSize.large:
        return DBTextStyles.labelLarge;
    }
  }

  double _getIconSize() {
    switch (size) {
      case DBButtonSize.small:
        return 16;
      case DBButtonSize.medium:
        return 18;
      case DBButtonSize.large:
        return 20;
    }
  }
}

enum DBButtonType { primary, secondary, tertiary }
enum DBButtonSize { small, medium, large }

/// DB-styled input field following Design System v3
class DBTextField extends StatelessWidget {
  final String label;
  final String? hint;
  final TextEditingController? controller;
  final String? errorText;
  final bool obscureText;
  final TextInputType keyboardType;
  final void Function(String)? onChanged;
  final Widget? suffixIcon;
  final Widget? prefixIcon;
  final int maxLines;
  final bool enabled;

  const DBTextField({
    super.key,
    required this.label,
    this.hint,
    this.controller,
    this.errorText,
    this.obscureText = false,
    this.keyboardType = TextInputType.text,
    this.onChanged,
    this.suffixIcon,
    this.prefixIcon,
    this.maxLines = 1,
    this.enabled = true,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label,
          style: DBTextStyles.labelMedium.copyWith(
            color: enabled ? DBColors.dbGray700 : DBColors.dbGray500,
          ),
        ),
        const SizedBox(height: DBSpacing.sm),
        TextField(
          controller: controller,
          obscureText: obscureText,
          keyboardType: keyboardType,
          onChanged: onChanged,
          maxLines: maxLines,
          enabled: enabled,
          style: DBTextStyles.bodyMedium,
          decoration: InputDecoration(
            hintText: hint,
            hintStyle: DBTextStyles.bodyMedium.copyWith(
              color: DBColors.dbGray500,
            ),
            errorText: errorText,
            suffixIcon: suffixIcon,
            prefixIcon: prefixIcon,
            border: OutlineInputBorder(
              borderRadius: BorderRadius.circular(DBBorderRadius.sm),
              borderSide: const BorderSide(color: DBColors.dbGray400),
            ),
            enabledBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(DBBorderRadius.sm),
              borderSide: const BorderSide(color: DBColors.dbGray400),
            ),
            focusedBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(DBBorderRadius.sm),
              borderSide: const BorderSide(color: DBColors.dbRed, width: 2),
            ),
            errorBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(DBBorderRadius.sm),
              borderSide: const BorderSide(color: DBColors.dbError),
            ),
            disabledBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(DBBorderRadius.sm),
              borderSide: const BorderSide(color: DBColors.dbGray300),
            ),
            filled: true,
            fillColor: enabled ? DBColors.dbBackground : DBColors.dbGray100,
            contentPadding: const EdgeInsets.all(DBSpacing.md),
          ),
        ),
      ],
    );
  }
}

/// DB-styled card following Design System v3
class DBCard extends StatelessWidget {
  final Widget child;
  final EdgeInsetsGeometry? padding;
  final VoidCallback? onTap;
  final Color? backgroundColor;
  final double? elevation;

  const DBCard({
    super.key,
    required this.child,
    this.padding,
    this.onTap,
    this.backgroundColor,
    this.elevation,
  });

  @override
  Widget build(BuildContext context) {
    final card = Card(
      elevation: elevation ?? 2,
      color: backgroundColor ?? DBColors.dbBackground,
      shadowColor: DBColors.dbGray900.withOpacity(0.12),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(DBBorderRadius.md),
      ),
      child: Padding(
        padding: padding ?? const EdgeInsets.all(DBSpacing.md),
        child: child,
      ),
    );

    if (onTap != null) {
      return InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(DBBorderRadius.md),
        child: card,
      );
    }

    return card;
  }
}

/// DB-styled checkbox following Design System v3
class DBCheckbox extends StatelessWidget {
  final bool value;
  final void Function(bool?)? onChanged;
  final String label;
  final String? description;
  final bool enabled;

  const DBCheckbox({
    super.key,
    required this.value,
    required this.onChanged,
    required this.label,
    this.description,
    this.enabled = true,
  });

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: enabled ? () => onChanged?.call(!value) : null,
      borderRadius: BorderRadius.circular(DBBorderRadius.sm),
      child: Padding(
        padding: const EdgeInsets.all(DBSpacing.sm),
        child: Row(
          children: [
            Checkbox(
              value: value,
              onChanged: enabled ? onChanged : null,
              fillColor: MaterialStateProperty.resolveWith<Color>((states) {
                if (states.contains(MaterialState.disabled)) {
                  return DBColors.dbGray300;
                }
                if (states.contains(MaterialState.selected)) {
                  return DBColors.dbRed;
                }
                return Colors.transparent;
              }),
              checkColor: Colors.white,
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(DBBorderRadius.xs),
              ),
            ),
            const SizedBox(width: DBSpacing.sm),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    label,
                    style: DBTextStyles.bodyMedium.copyWith(
                      color: enabled ? DBColors.dbGray900 : DBColors.dbGray500,
                    ),
                  ),
                  if (description != null) ...[
                    const SizedBox(height: DBSpacing.xs),
                    Text(
                      description!,
                      style: DBTextStyles.bodySmall.copyWith(
                        color: enabled ? DBColors.dbGray600 : DBColors.dbGray400,
                      ),
                    ),
                  ],
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// DB-styled dropdown following Design System v3
class DBDropdown<T> extends StatelessWidget {
  final String label;
  final T? value;
  final List<DBDropdownItem<T>> items;
  final void Function(T?)? onChanged;
  final String? hint;
  final bool enabled;

  const DBDropdown({
    super.key,
    required this.label,
    this.value,
    required this.items,
    this.onChanged,
    this.hint,
    this.enabled = true,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label,
          style: DBTextStyles.labelMedium.copyWith(
            color: enabled ? DBColors.dbGray700 : DBColors.dbGray500,
          ),
        ),
        const SizedBox(height: DBSpacing.sm),
        DropdownButtonFormField<T>(
          value: value,
          onChanged: enabled ? onChanged : null,
          hint: hint != null 
              ? Text(
                  hint!,
                  style: DBTextStyles.bodyMedium.copyWith(
                    color: DBColors.dbGray500,
                  ),
                )
              : null,
          items: items.map((item) => DropdownMenuItem<T>(
            value: item.value,
            child: Text(
              item.label,
              style: DBTextStyles.bodyMedium,
            ),
          )).toList(),
          decoration: InputDecoration(
            border: OutlineInputBorder(
              borderRadius: BorderRadius.circular(DBBorderRadius.sm),
              borderSide: const BorderSide(color: DBColors.dbGray400),
            ),
            enabledBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(DBBorderRadius.sm),
              borderSide: const BorderSide(color: DBColors.dbGray400),
            ),
            focusedBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(DBBorderRadius.sm),
              borderSide: const BorderSide(color: DBColors.dbRed, width: 2),
            ),
            disabledBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(DBBorderRadius.sm),
              borderSide: const BorderSide(color: DBColors.dbGray300),
            ),
            filled: true,
            fillColor: enabled ? DBColors.dbBackground : DBColors.dbGray100,
            contentPadding: const EdgeInsets.all(DBSpacing.md),
          ),
          style: DBTextStyles.bodyMedium,
          icon: Icon(
            Icons.keyboard_arrow_down,
            color: enabled ? DBColors.dbGray700 : DBColors.dbGray400,
          ),
        ),
      ],
    );
  }
}

class DBDropdownItem<T> {
  final T value;
  final String label;

  const DBDropdownItem({
    required this.value,
    required this.label,
  });
}

/// DB-styled progress indicator following Design System v3
class DBProgressIndicator extends StatelessWidget {
  final double? value;
  final String? label;
  final Color? color;

  const DBProgressIndicator({
    super.key,
    this.value,
    this.label,
    this.color,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (label != null) ...[
          Text(
            label!,
            style: DBTextStyles.bodySmall.copyWith(color: DBColors.dbGray700),
          ),
          const SizedBox(height: DBSpacing.sm),
        ],
        LinearProgressIndicator(
          value: value,
          backgroundColor: DBColors.dbGray300,
          valueColor: AlwaysStoppedAnimation<Color>(
            color ?? DBColors.dbRed,
          ),
          minHeight: 4,
        ),
      ],
    );
  }
}

/// DB-styled snackbar following Design System v3
class DBSnackBar {
  static void show(
    BuildContext context, {
    required String message,
    DBSnackBarType type = DBSnackBarType.info,
    Duration duration = const Duration(seconds: 4),
    String? actionLabel,
    VoidCallback? onAction,
  }) {
    Color backgroundColor;
    Color textColor = Colors.white;
    IconData? icon;

    switch (type) {
      case DBSnackBarType.success:
        backgroundColor = DBColors.dbSuccess;
        icon = Icons.check_circle;
        break;
      case DBSnackBarType.warning:
        backgroundColor = DBColors.dbWarning;
        icon = Icons.warning;
        textColor = DBColors.dbGray900;
        break;
      case DBSnackBarType.error:
        backgroundColor = DBColors.dbError;
        icon = Icons.error;
        break;
      case DBSnackBarType.info:
        backgroundColor = DBColors.dbGray800;
        icon = Icons.info;
        break;
    }

    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Row(
          children: [
            if (icon != null) ...[
              Icon(icon, color: textColor, size: 20),
              const SizedBox(width: DBSpacing.sm),
            ],
            Expanded(
              child: Text(
                message,
                style: DBTextStyles.bodyMedium.copyWith(color: textColor),
              ),
            ),
          ],
        ),
        backgroundColor: backgroundColor,
        duration: duration,
        behavior: SnackBarBehavior.floating,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(DBBorderRadius.sm),
        ),
        action: actionLabel != null && onAction != null
            ? SnackBarAction(
                label: actionLabel,
                textColor: textColor,
                onPressed: onAction,
              )
            : null,
      ),
    );
  }
}

enum DBSnackBarType { success, warning, error, info }