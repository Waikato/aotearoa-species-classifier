import 'package:hive/hive.dart';

part 'name_data.g.dart';

@HiveType(typeId: 3)
class NameData {
  @HiveField(0)
  final int index;
  @HiveField(1)
  final String name;
  @HiveField(2)
  final List<String> mriNames;
  @HiveField(3)
  final List<String> engNames;

  const NameData (
      this.index,
      this.name,
      this.mriNames,
      this.engNames,
      );
}