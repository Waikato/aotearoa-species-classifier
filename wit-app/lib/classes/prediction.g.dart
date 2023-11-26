// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'prediction.dart';

// **************************************************************************
// TypeAdapterGenerator
// **************************************************************************

class PredictionAdapter extends TypeAdapter<Prediction> {
  @override
  final int typeId = 2;

  @override
  Prediction read(BinaryReader reader) {
    final numOfFields = reader.readByte();
    final fields = <int, dynamic>{
      for (int i = 0; i < numOfFields; i++) reader.readByte(): reader.read(),
    };
    return Prediction(
      fields[0] as int,
      fields[1] as String,
      fields[2] as double,
      fields[3] as NameData,
    );
  }

  @override
  void write(BinaryWriter writer, Prediction obj) {
    writer
      ..writeByte(4)
      ..writeByte(0)
      ..write(obj.index)
      ..writeByte(1)
      ..write(obj.species)
      ..writeByte(2)
      ..write(obj.probability)
      ..writeByte(3)
      ..write(obj.nameData);
  }

  @override
  int get hashCode => typeId.hashCode;

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is PredictionAdapter &&
          runtimeType == other.runtimeType &&
          typeId == other.typeId;
}
