import 'package:flutter/material.dart';
import 'dart:io';
import 'package:intl/intl.dart';
import 'package:hive/hive.dart';

class ModelManager extends StatefulWidget {
  const ModelManager({Key? key}) : super(key: key);

  @override
  _ModelManager createState() => _ModelManager();

}

class _ModelManager extends State<ModelManager> {
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text("Model Manager"),
      ),
      body: Scrollbar(
          child: ListView(
            //restorationId: 'list_demo_list_view',
            padding: const EdgeInsets.symmetric(vertical: 8),
            children: const [
               ListTile(
                leading: Icon(Icons.lightbulb_outline),
                title: Text("EfficientNetV2_small"),
                subtitle: Text("137.1 MB : 00:00s"),
              ),
            ],
          )
      ),
    );
  }

  @override
  void initState() {
    super.initState();
  }
}