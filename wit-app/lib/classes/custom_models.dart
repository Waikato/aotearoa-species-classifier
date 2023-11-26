import 'dart:io';

import 'package:flutter/services.dart';
import 'package:pytorch_mobile/enums/dtype.dart';

import 'package:wit_app/classes/prediction.dart';

const TORCHVISION_NORM_MEAN_RGB = [0.485, 0.456, 0.406];
const TORCHVISION_NORM_STD_RGB = [0.229, 0.224, 0.225];

class BaseModel {
  static const MethodChannel _channel = const MethodChannel('pytorch_mobile');

  final int _index;

  BaseModel(this._index);

  ///predicts abstract number input
  Future<List?> getPrediction(
      List<double> input, List<int> shape, DType dtype) async {
    final List? prediction = await _channel.invokeListMethod('predict', {
      "index": _index,
      "data": input,
      "shape": shape,
      "dtype": dtype.toString().split(".").last
    });
    return prediction;
  }

  ///predicts image and returns the supposed label belonging to it
  Future<String> getImagePrediction(
      File image, int width, int height, String labelPath,
      {List<double> mean = TORCHVISION_NORM_MEAN_RGB,
        List<double> std = TORCHVISION_NORM_STD_RGB}) async {
    // Assert mean std
    assert(mean.length == 3, "mean should have size of 3");
    assert(std.length == 3, "std should have size of 3");

    List<String> labels = await _getLabels(labelPath);
    List byteArray = image.readAsBytesSync();
    final List? prediction = await _channel.invokeListMethod("predictImage", {
      "index": _index,
      "image": byteArray,
      "width": width,
      "height": height,
      "mean": mean,
      "std": std
    });
    double maxScore = double.negativeInfinity;
    int maxScoreIndex = -1;
    for (int i = 0; i < prediction!.length; i++) {
      if (prediction[i] > maxScore) {
        maxScore = prediction[i];
        maxScoreIndex = i;
      }
    }
    return labels[maxScoreIndex];
  }

  ///predicts image but returns the raw net output
  Future<List?> getImagePredictionList(File image, int width, int height,
      {List<double> mean = TORCHVISION_NORM_MEAN_RGB,
        List<double> std = TORCHVISION_NORM_STD_RGB}) async {
    // Assert mean std
    assert(mean.length == 3, "Mean should have size of 3");
    assert(std.length == 3, "STD should have size of 3");
    final List? prediction = await _channel.invokeListMethod("predictImage", {
      "index": _index,
      "image": image.readAsBytesSync(),
      "width": width,
      "height": height,
      "mean": mean,
      "std": std
    });
    return prediction;
  }

  //get labels in csv format
  Future<List<String>> _getLabels(String labelPath) async {
    String labelsData = await rootBundle.loadString(labelPath);
    return labelsData.split(",");
  }
}

class PostProcessingModel extends BaseModel {
  PostProcessingModel(int _index) : super(_index);

  int _comparePredictions(Prediction a, Prediction b) {
    // comparator function allows sorting of Prediction class instances
    if (a.probability < b.probability){
      return -1;
    } else if (a.probability == b.probability) {
      return 0;
    } else {
      return 1;
    }
  }

  Future<List<Prediction>> getTopFiveList(File image, int width, int height, String labelPath,
      {List<double> mean = TORCHVISION_NORM_MEAN_RGB,
        List<double> std = TORCHVISION_NORM_STD_RGB}) async{

    final List? prediction = await getImagePredictionList(
        image,
        width,
        height
    );

    List<String> labels = await _getLabels(labelPath);
    List<Prediction> predictions = List<Prediction>.empty();
    /*for (int i = 0; i < prediction!.length; i++) {
      Prediction pred = Prediction(i, labels[i], prediction[i]);
      predictions.add(pred);
    }*/
    predictions.sort((a, b) => _comparePredictions(a, b));
    predictions = predictions.reversed.toList();

    return predictions.sublist(0, 5);
  }

}