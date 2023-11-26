
import 'package:flutter/material.dart';

class CustomExpansionTile extends StatefulWidget {
  final Text title;
  final List<Widget> children;
  const CustomExpansionTile({Key?key, required this.title, required this.children}) : super (key: key);

  @override
  _CustomExpansionTile createState() => _CustomExpansionTile();
}

class _CustomExpansionTile extends State<CustomExpansionTile> {
  bool _expanded = false;

  @override
  Widget build(BuildContext context){
    final theme = Theme.of(context).copyWith(dividerColor: Colors.transparent);
    /*return Card(
      elevation: 1,
      color: Colors.amber,
      child: ClipRRect(
        borderRadius: const BorderRadius.all(Radius.circular(12)),
        child: ExpansionTile(
          title: widget.title,
          trailing: Icon(_expanded ? Icons.remove_circle_outline_rounded : Icons.add_circle_outline_rounded),
          children: widget.children,
          onExpansionChanged: (bool expanded) {
            setState(() => _expanded = expanded);
          },
          //collapsedBackgroundColor: Colors.amber,
          //backgroundColor: Colors.amber,
          textColor: const Color(0xFFeff6e0),
          collapsedTextColor: const Color(0xFFeff6e0),
          iconColor: const Color(0xFFeff6e0),
          collapsedIconColor: const Color(0xFFeff6e0),
        ),,
      ),
      shape: const RoundedRectangleBorder(
          borderRadius: BorderRadius.all(Radius.circular(12))
      ),
    );*/
    /*return ClipRRect(
        borderRadius: const BorderRadius.all(Radius.circular(12)),
        child: ExpansionTile(
          title: widget.title,
          trailing: Icon(_expanded ? Icons.remove_circle_outline_rounded : Icons.add_circle_outline_rounded),
          children: widget.children,
          onExpansionChanged: (bool expanded) {
            setState(() => _expanded = expanded);
          },
          collapsedBackgroundColor: Colors.amber,
          backgroundColor: Colors.amber,
          textColor: const Color(0xFFeff6e0),
          collapsedTextColor: const Color(0xFFeff6e0),
          iconColor: const Color(0xFFeff6e0),
          collapsedIconColor: const Color(0xFFeff6e0),
        ),
    );*/
    return Card(
      elevation: 2,
      color: Colors.amber,
      child: ClipRRect(
          borderRadius: const BorderRadius.all(Radius.circular(12)),
          child: Theme(
            data: theme,
            child: ExpansionTile(
              title: widget.title,
              trailing: Icon(_expanded ? Icons.remove_circle_outline_rounded : Icons.add_circle_outline_rounded),
              children: widget.children,
              onExpansionChanged: (bool expanded) {
                setState(() => _expanded = expanded);
              },
              //collapsedBackgroundColor: Colors.amber,
              //backgroundColor: Colors.amber,
              textColor: const Color(0xFFeff6e0),
              collapsedTextColor: const Color(0xFFeff6e0),
              iconColor: const Color(0xFFeff6e0),
              collapsedIconColor: const Color(0xFFeff6e0),
            )
          ),
      ),
      shape: const RoundedRectangleBorder(
          borderRadius: BorderRadius.all(Radius.circular(12))
      ),
    );
  }
}