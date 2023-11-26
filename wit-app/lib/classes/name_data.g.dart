// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'name_data.dart';

// **************************************************************************
// TypeAdapterGenerator
// **************************************************************************

class NameDataAdapter extends TypeAdapter<NameData> {
  @override
  final int typeId = 3;

  @override
  NameData read(BinaryReader reader) {
    final numOfFields = reader.readByte();
    final fields = <int, dynamic>{
      for (int i = 0; i < numOfFields; i++) reader.readByte(): reader.read(),
    };
    return NameData(
      fields[0] as int,
      fields[1] as String,
      (fields[2] as List).cast<String>(),
      (fields[3] as List).cast<String>(),
    );
  }

  @override
  void write(BinaryWriter writer, NameData obj) {
    writer
      ..writeByte(4)
      ..writeByte(0)
      ..write(obj.index)
      ..writeByte(1)
      ..write(obj.name)
      ..writeByte(2)
      ..write(obj.mriNames)
      ..writeByte(3)
      ..write(obj.engNames);
  }

  @override
  int get hashCode => typeId.hashCode;

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is NameDataAdapter &&
          runtimeType == other.runtimeType &&
          typeId == other.typeId;
}
