import 'package:hive/hive.dart';

import 'package:wit_app/classes/prediction.dart';

part 'classification_result.g.dart';

// regenerate g.dart code with command:
//  flutter packages pub run build_runner build --delete-conflicting-outputs

@HiveType(typeId: 1)
class ClassificationResult {
  @HiveField(0)
  final String prediction;
  @HiveField(1)
  final String imagePath;
  @HiveField(2)
  final DateTime timestamp;
  @HiveField(3)
  final List<Prediction> topFivePredictions;

  const ClassificationResult(
    this.prediction,
    this.imagePath,
    this.timestamp,
      this.topFivePredictions,
  );
}
