import 'package:hive/hive.dart';
import 'package:wit_app/classes/name_data.dart';

part 'prediction.g.dart';

@HiveType(typeId: 2)
class Prediction {
  @HiveField(0)
  final int index;
  @HiveField(1)
  final String species;
  @HiveField(2)
  final double probability;
  @HiveField(3)
  final NameData nameData;

  const Prediction (
      this.index,
      this.species,
      this.probability,
      this.nameData,
      );
}

