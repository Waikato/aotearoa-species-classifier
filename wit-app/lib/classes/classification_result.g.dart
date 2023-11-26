// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'classification_result.dart';

// **************************************************************************
// TypeAdapterGenerator
// **************************************************************************

class ClassificationResultAdapter extends TypeAdapter<ClassificationResult> {
  @override
  final int typeId = 1;

  @override
  ClassificationResult read(BinaryReader reader) {
    final numOfFields = reader.readByte();
    final fields = <int, dynamic>{
      for (int i = 0; i < numOfFields; i++) reader.readByte(): reader.read(),
    };
    return ClassificationResult(
      fields[0] as String,
      fields[1] as String,
      fields[2] as DateTime,
      (fields[3] as List).cast<Prediction>(),
    );
  }

  @override
  void write(BinaryWriter writer, ClassificationResult obj) {
    writer
      ..writeByte(4)
      ..writeByte(0)
      ..write(obj.prediction)
      ..writeByte(1)
      ..write(obj.imagePath)
      ..writeByte(2)
      ..write(obj.timestamp)
      ..writeByte(3)
      ..write(obj.topFivePredictions);
  }

  @override
  int get hashCode => typeId.hashCode;

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is ClassificationResultAdapter &&
          runtimeType == other.runtimeType &&
          typeId == other.typeId;
}
