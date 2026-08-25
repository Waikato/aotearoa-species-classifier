import 'dart:io';
import 'dart:typed_data';

import 'package:flutter/foundation.dart';
import 'package:flutter_onnxruntime/flutter_onnxruntime.dart';
import 'package:image/image.dart' as img;

import 'dart:math' as math;

/// Resize the shorter edge to [resizeSize], preserving aspect ratio,
/// using scale-aware antialiased bilinear filtering, then centre-crop
/// to [cropWidth] x [cropHeight].
///
/// This approximates:
///
///   transforms.Resize(
///       resizeSize,
///       interpolation=InterpolationMode.BILINEAR,
///       antialias=True,
///   )
///   transforms.CenterCrop((cropHeight, cropWidth))
///
/// The input should normally be an RGB or RGBA image.
img.Image resizeAndCenterCropTorchvisionStyle(
  img.Image source, {
  required int resizeSize,
  required int cropWidth,
  required int cropHeight,
}) {
  if (resizeSize <= 0 || cropWidth <= 0 || cropHeight <= 0) {
    throw ArgumentError('Resize and crop dimensions must be positive.');
  }

  // torchvision Resize(int) sets the shorter edge to resizeSize.
  //
  // It effectively uses integer truncation for the calculated longer edge,
  // rather than Dart's round().
  late final int resizedWidth;
  late final int resizedHeight;

  if (source.width <= source.height) {
    resizedWidth = resizeSize;
    resizedHeight =
        (resizeSize * source.height / source.width).floor();
  } else {
    resizedHeight = resizeSize;
    resizedWidth =
        (resizeSize * source.width / source.height).floor();
  }

  final resized = resizeBilinearAntialiased(
    source,
    resizedWidth,
    resizedHeight,
  );

  if (resized.width < cropWidth || resized.height < cropHeight) {
    throw StateError(
      'The resized image is ${resized.width}x${resized.height}, '
      'which is smaller than the requested '
      '${cropWidth}x$cropHeight crop.',
    );
  }

  // torchvision CenterCrop computes the centred crop location.
  //
  // Integer division puts the extra pixel, when present, on the
  // bottom or right side.
  final cropX = (resized.width - cropWidth) ~/ 2;
  final cropY = (resized.height - cropHeight) ~/ 2;

  return img.copyCrop(
    resized,
    x: cropX,
    y: cropY,
    width: cropWidth,
    height: cropHeight,
  );
}

/// Scale-aware antialiased bilinear resize.
///
/// Ordinary bilinear interpolation uses a triangular filter with radius 1.
/// When reducing an image, this implementation widens that filter in source
/// coordinates according to the reduction factor. This acts as the low-pass
/// filter required before downsampling.
///
/// The resize is separable:
///
///   1. horizontal filtering;
///   2. vertical filtering.
///
/// This is much closer to Pillow-style antialiased bilinear resizing than
/// package:image's ordinary Interpolation.linear downsampling.
img.Image resizeBilinearAntialiased(
  img.Image source,
  int destinationWidth,
  int destinationHeight,
) {
  if (destinationWidth <= 0 || destinationHeight <= 0) {
    throw ArgumentError('Destination dimensions must be positive.');
  }

  if (source.width == destinationWidth &&
      source.height == destinationHeight) {
    return img.Image.from(source);
  }

  final horizontalContributions = _makeContributions(
    sourceSize: source.width,
    destinationSize: destinationWidth,
  );

  final verticalContributions = _makeContributions(
    sourceSize: source.height,
    destinationSize: destinationHeight,
  );

  /*
   * Horizontal intermediate buffer.
   *
   * Layout:
   *   ((y * destinationWidth + x) * 4) + channel
   *
   * Values remain floating point until the vertical pass, avoiding
   * quantisation between the two separable filtering stages.
   */
  final intermediate = Float64List(
    source.height * destinationWidth * 4,
  );

  for (var sourceY = 0; sourceY < source.height; sourceY++) {
    for (var destinationX = 0;
        destinationX < destinationWidth;
        destinationX++) {
      final contribution =
          horizontalContributions[destinationX];

      var red = 0.0;
      var green = 0.0;
      var blue = 0.0;
      var alpha = 0.0;

      for (var i = 0; i < contribution.indices.length; i++) {
        final sourceX = contribution.indices[i];
        final weight = contribution.weights[i];
        final pixel = source.getPixel(sourceX, sourceY);

        red += pixel.r.toDouble() * weight;
        green += pixel.g.toDouble() * weight;
        blue += pixel.b.toDouble() * weight;
        alpha += pixel.a.toDouble() * weight;
      }

      final offset =
          (sourceY * destinationWidth + destinationX) * 4;

      intermediate[offset] = red;
      intermediate[offset + 1] = green;
      intermediate[offset + 2] = blue;
      intermediate[offset + 3] = alpha;
    }
  }

  final destination = img.Image(
    width: destinationWidth,
    height: destinationHeight,
    numChannels: 4,
  );

  for (var destinationY = 0;
      destinationY < destinationHeight;
      destinationY++) {
    final contribution =
        verticalContributions[destinationY];

    for (var destinationX = 0;
        destinationX < destinationWidth;
        destinationX++) {
      var red = 0.0;
      var green = 0.0;
      var blue = 0.0;
      var alpha = 0.0;

      for (var i = 0; i < contribution.indices.length; i++) {
        final sourceY = contribution.indices[i];
        final weight = contribution.weights[i];

        final offset =
            (sourceY * destinationWidth + destinationX) * 4;

        red += intermediate[offset] * weight;
        green += intermediate[offset + 1] * weight;
        blue += intermediate[offset + 2] * weight;
        alpha += intermediate[offset + 3] * weight;
      }

      destination.setPixelRgba(
        destinationX,
        destinationY,
        _toUint8(red),
        _toUint8(green),
        _toUint8(blue),
        _toUint8(alpha),
      );
    }
  }

  return destination;
}

class _Contributions {
  const _Contributions(this.indices, this.weights);

  final List<int> indices;
  final List<double> weights;
}

/// Precalculate all source indices and weights for one resize dimension.
List<_Contributions> _makeContributions({
  required int sourceSize,
  required int destinationSize,
}) {
  final scale = destinationSize / sourceSize;

  /*
   * Bilinear interpolation uses the triangular kernel:
   *
   *     triangle(x) = max(0, 1 - abs(x))
   *
   * During reduction, widen the filter by 1 / scale in source space.
   * During enlargement, retain the normal radius of 1.
   */
  final filterScale = scale < 1.0 ? 1.0 / scale : 1.0;
  final support = filterScale;

  final result = <_Contributions>[];

  for (var destinationIndex = 0;
      destinationIndex < destinationSize;
      destinationIndex++) {
    /*
     * Half-pixel/pixel-centre coordinate mapping:
     *
     * sourceCentre =
     *     (destinationIndex + 0.5) / scale - 0.5
     */
    final sourceCentre =
        (destinationIndex + 0.5) / scale - 0.5;

    final first = (sourceCentre - support).floor();
    final last = (sourceCentre + support).ceil();

    final combined = <int, double>{};

    for (var sourceIndex = first;
        sourceIndex <= last;
        sourceIndex++) {
      /*
       * Divide the distance by filterScale when downsampling.
       * Multiplying the weight by 1/filterScale is unnecessary here,
       * because the collected weights are normalized afterward.
       */
      final distance =
          (sourceCentre - sourceIndex) / filterScale;

      final weight = math.max(0.0, 1.0 - distance.abs());

      if (weight == 0.0) {
        continue;
      }

      /*
       * Edge extension by clamping.
       *
       * If several outside samples clamp to the same edge pixel,
       * combine their weights.
       */
      final clampedIndex =
          sourceIndex.clamp(0, sourceSize - 1).toInt();

      combined[clampedIndex] =
          (combined[clampedIndex] ?? 0.0) + weight;
    }

    final weightSum = combined.values.fold<double>(
      0.0,
      (sum, weight) => sum + weight,
    );

    if (weightSum == 0.0) {
      // Defensive fallback. This should not normally occur.
      final nearest =
          sourceCentre.round().clamp(0, sourceSize - 1).toInt();

      result.add(_Contributions([nearest], [1.0]));
      continue;
    }

    result.add(
      _Contributions(
        combined.keys.toList(growable: false),
        combined.values
            .map((weight) => weight / weightSum)
            .toList(growable: false),
      ),
    );
  }

  return result;
}

int _toUint8(double value) {
  if (value <= 0.0) {
    return 0;
  }
  if (value >= 255.0) {
    return 255;
  }
  return value.round();
}


/// ONNX wrapper for the Aotearoa species classifier.
///
/// The model expects:
///   input name: image
///   input shape: [1, 3, 384, 384]
///   input type: float32
///
/// Image[1, 3, 384, 384 input type: float32 to [0, 1] and then
/// normalized using:
///
///   normalized = (value - mean) / standardDeviation
///
/// With mean=0.5 and std=0.5, this produces values in [-1, 1].
class OnnxSpeciesModel {
  OnnxSpeciesModel({
    required this.assetPath,
    this.width = 384,
    this.height = 384,
    this.mean = const <double>[0.5, 0.5, 0.5],
    this.std = const <double>[0.5, 0.5, 0.5],
  })  : assert(mean.length == 3),
        assert(std.length == 3);

  final String assetPath;
  final int width;
  final int height;
  final List<double> mean;
  final List<double> std;

  final OnnxRuntime _runtime = OnnxRuntime();

  OrtSession? _session;
  String? _inputName;
  String? _outputName;

  bool get isLoaded => _session != null;

  /// Loads the ONNX model from the Flutter asset bundle.
  Future<void> load() async {
    if (_session != null) {
      return;
    }

    final session = await _runtime.createSessionFromAsset(assetPath);

    if (session.inputNames.isEmpty) {
      await session.close();
      throw StateError('The ONNX model has no input tensors.');
    }

    if (session.outputNames.isEmpty) {
      await session.close();
      throw StateError('The ONNX model has no output tensors.');
    }

    _session = session;
    _inputName = session.inputNames.first;
    _outputName = session.outputNames.first;
    debugPrint("Loading model: $assetPath");
    debugPrint("Configured width=$width height=$height");
    debugPrint('ONNX species model loaded');
    debugPrint('Input names: ${session.inputNames}');
    debugPrint('Output names: ${session.outputNames}');
  }

  /// Runs image classification and returns the raw model logits.
  ///
  /// The returned list has one score for each of the 14,991 classes.
  Future<List<double>> getImagePredictionList(File imageFile) async {
    final session = _session;

    if (session == null || _inputName == null || _outputName == null) {
      throw StateError(
        'The ONNX model has not been loaded. Call load() first.',
      );
    }

    final inputData = await _prepareImage(imageFile);

    OrtValue? inputTensor;
    Map<String, OrtValue>? outputTensors;

    try {
      inputTensor = await OrtValue.fromList(
        inputData,
        <int>[1, 3, height, width],
      );

      outputTensors = await session.run(
        <String, OrtValue>{
          _inputName!: inputTensor,
        },
      );

      final outputTensor = outputTensors[_outputName];

      if (outputTensor == null) {
        throw StateError(
          'The ONNX session did not return output "$_outputName". '
          'Returned outputs: ${outputTensors.keys.join(", ")}',
        );
      }

      final dynamic outputData = await outputTensor.asList();
      final scores = _flattenNumericOutput(outputData);

      if (scores.length != 14991) {
        throw StateError(
          'Expected 14,991 model scores, but received ${scores.length}.',
        );
      }

      return scores;
    } finally {
      if (inputTensor != null) {
        await inputTensor.dispose();
      }

      if (outputTensors != null) {
        for (final tensor in outputTensors.values) {
          await tensor.dispose();
        }
      }
    }
  }

  Future<Float32List> _prepareImage(File imageFile) async {
    final encodedBytes = await imageFile.readAsBytes();

    img.Image? decodedImage = img.decodeImage(encodedBytes);

    if (decodedImage == null) {
      throw FormatException(
        'Unable to decode image: ${imageFile.path}',
      );
    }

    // Correct photographs according to their EXIF orientation.
    decodedImage = img.bakeOrientation(decodedImage);
    final img.Image croppedImage = resizeAndCenterCropTorchvisionStyle(decodedImage, resizeSize: 416, cropWidth: 384, cropHeight: 384);

    final int planeSize = width * height;
    final Float32List input = Float32List(3 * planeSize);

    for (int y = 0; y < height; y++) {
      for (int x = 0; x < width; x++) {
        final pixel = croppedImage.getPixel(x, y);
        final int pixelIndex = y * width + x;

        // Match ToTensor(): convert channel values from [0, 255]
        // to floating-point values in [0, 1].
        final double red = pixel.r.toDouble() / 255.0;
        final double green = pixel.g.toDouble() / 255.0;
        final double blue = pixel.b.toDouble() / 255.0;

        // Match Normalize(mean=0.5, std=0.5) and create NCHW
        // layout: all red values, then green, then blue.
        input[pixelIndex] = (red - mean[0]) / std[0];
        input[planeSize + pixelIndex] = (green - mean[1]) / std[1];

        input[(2 * planeSize) + pixelIndex] = (blue - mean[2]) / std[2];
      }
    }

    return input;
  }

  /// The ONNX output may be returned either as:
  ///
  ///   [score0, score1, ...]
  ///
  /// or:
  ///
  ///	[[score0, score1, ...]]
  ///
  /// This method handles both representations.
  List<double> _flattenNumericOutput(dynamic value) {
    final result = <double>[];

    void append(dynamic item) {
      if (item is num) {
        result.add(item.toDouble());
        return;
      }

      if (item is List) {
        for (final child in item) {
          append(child);
        }
        return;
      }

      throw StateError(
        'Unexpected ONNX output value of type ${item.runtimeType}.',
      );
    }

    append(value);
    return result;
  }

  /// Releases native ONNX resources.
  Future<void> dispose() async {
    final session = _session;

    _session = null;
    _inputName = null;
    _outputName = null;

    if (session != null) {
      await session.close();
    }
  }
}
