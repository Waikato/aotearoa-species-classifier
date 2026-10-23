import 'package:camera/camera.dart';
import 'package:flutter/material.dart';

import 'dart:io';

import 'package:intl/intl.dart';
import 'package:hive/hive.dart';
import 'package:path_provider/path_provider.dart';
import 'package:path/path.dart' as path;

import 'package:wit_app/classes/classification_result.dart';
import 'package:wit_app/globals.dart';

import 'package:wit_app/screens/classification.dart';

class ClassificationHistory extends StatefulWidget {
  const ClassificationHistory({Key? key}) : super(key: key);

  @override
  _ClassificationHistory createState() => _ClassificationHistory();
}

class _ClassificationHistory extends State<ClassificationHistory> {
  late final Box box;

  Future<void> deleteEntry(int key) async {
    final dynamic value = box.get(key);

    if (value is! ClassificationResult) {
      return;
    }

    final ClassificationResult item = value;
    final Directory directory = await getApplicationDocumentsDirectory();
    final String localFilesPath = path.normalize(
      path.join(directory.path, 'files'),
    );
    final String imagePath = path.normalize(item.imagePath);

    if (path.isWithin(localFilesPath, imagePath)) {
      final File sourceImage = File(imagePath);

      if (await sourceImage.exists()) {
        await sourceImage.delete();
      }
    }

    await box.delete(key);

    if (!mounted) return;

    setState(() {});
  }

  Future<void> _resaveImage(String srcPath, String tgtPath) async {
    final Directory targetDirectory = Directory(path.dirname(tgtPath));

    if (!await targetDirectory.exists()) {
      await targetDirectory.create(recursive: true);
    }

    XFile image = XFile(srcPath);
    await image.saveTo(tgtPath);
    //debugPrint("image copied from \n$srcPath \nto \n$tgtPath");
  }

  Future<Image?> _getImage(String imagePath) async {
    /*
    * In new versions (1.1.0+), images are stored in {dir}/files/
    * However, in previous versions, this wasn't always the case, so try to
    * retrieve images using their file name only, and return a missing image
    * icon otherwise.
    * */
    File surfaceFile = File(imagePath);
    if (await surfaceFile.exists()) {
      //debugPrint("loaded image from $imagePath");
      return Image.file(surfaceFile, width: 64, height: 64, fit: BoxFit.cover);
    }
    Directory dir = await getApplicationDocumentsDirectory();
    final String dirPath = dir.path;
    final String tgtPath =
        '$dirPath${Platform.pathSeparator}files${Platform.pathSeparator}' +
        path.basename(imagePath);
    //debugPrint(dirPath + "\n\n" + path.dirname(dirPath) + "\n\n" + path.dirname(path.dirname(dirPath)));

    File standardFile = File(tgtPath);
    if (await standardFile.exists()) {
      //debugPrint("Loaded image from $tgtPath");
      return Image.file(standardFile, width: 64, height: 64, fit: BoxFit.cover);
    }
    if (Platform.isIOS) {
      final cacheDirectory = await getTemporaryDirectory();
      final cachePath = cacheDirectory.path;
      String tmpPath = path.dirname(
        cachePath,
      ); // /var/mobile/Containers/Data/Application/{build hash}/Library
      tmpPath = path.dirname(
        tmpPath,
      ); // /var/mobile/Containers/Data/Application/{build hash}
      File iosCacheFile = File(
        cachePath + Platform.pathSeparator + path.basename(imagePath),
      );
      if (await iosCacheFile.exists()) {
        await _resaveImage(
          cachePath + Platform.pathSeparator + path.basename(imagePath),
          tgtPath,
        );
        return Image.file(
          iosCacheFile,
          width: 64,
          height: 64,
          fit: BoxFit.cover,
        );
      }
      File iosTmpFile = File(
        tmpPath +
            Platform.pathSeparator +
            "tmp" +
            Platform.pathSeparator +
            path.basename(imagePath),
      );
      if (await iosTmpFile.exists()) {
        await _resaveImage(
          tmpPath +
              Platform.pathSeparator +
              "tmp" +
              Platform.pathSeparator +
              path.basename(imagePath),
          tgtPath,
        );
        return Image.file(iosTmpFile, width: 64, height: 64, fit: BoxFit.cover);
      }
      File iosTmpFile2 = File(
        "${Platform.pathSeparator}private$tmpPath${Platform.pathSeparator}tmp${Platform.pathSeparator}${path.basename(imagePath)}",
      );
      if (await iosTmpFile2.exists()) {
        await _resaveImage(
          "${Platform.pathSeparator}private$tmpPath${Platform.pathSeparator}tmp${Platform.pathSeparator}${path.basename(imagePath)}",
          tgtPath,
        );
        return Image.file(
          iosTmpFile2,
          width: 64,
          height: 64,
          fit: BoxFit.cover,
        );
      }
      return null;
    }
    return null;
  }

  Text getTitleName(ClassificationResult result) {
    if (result.topFivePredictions[0].probability < PROB_THRESHOLD) {
      return Text(
        "Confidence too low (${((result.topFivePredictions[0].probability * 100).toStringAsPrecision(3))}%)",
      );
    }
    if (result.topFivePredictions[0].nameData.engNames.isEmpty ||
        result.topFivePredictions[0].nameData.engNames[0] == "") {
      return Text(
        "${result.prediction} (${((result.topFivePredictions[0].probability * 100).toStringAsPrecision(3))}%)",
      );
    }
    return Text(
      "${result.topFivePredictions[0].nameData.engNames[0]} (${((result.topFivePredictions[0].probability * 100).toStringAsPrecision(3))}%)",
    );
  }

  List<Widget> _buildClassificationResults() {
    final List<dynamic> keys = box.keys.toList().reversed.toList();

    return keys.map((dynamic key) {
      if (key is! int) {
        throw StateError(
          'Expected an integer Hive key, but found ${key.runtimeType}.',
        );
      }

      final dynamic value = box.get(key);

      if (value is! ClassificationResult) {
        throw StateError('No ClassificationResult exists for Hive key $key.');
      }

      final ClassificationResult result = value;

      return ListTile(
        leading: ClipOval(
          child: FutureBuilder<Image?>(
            future: _getImage(result.imagePath),
            builder: (context, snapshot) {
              return snapshot.data ??
                  const Icon(Icons.image_not_supported_outlined);
            },
          ),
        ),
        title: getTitleName(result),
        subtitle: Text(
          DateFormat('yyyy-MM-dd - kk:mm').format(result.timestamp),
        ),
        onTap: () {
          Navigator.push(
            context,
            MaterialPageRoute(
              builder: (context) => Classification(classificationKey: key),
            ),
          );
        },
        trailing: IconButton(
          icon: const Icon(Icons.delete),
          onPressed: () => deleteEntry(key),
        ),
      );
    }).toList();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text("Classification History")),
      body: Scrollbar(
        child: ListView(
          //restorationId: 'list_demo_list_view',
          padding: const EdgeInsets.symmetric(vertical: 8),
          children: _buildClassificationResults(),
        ),
      ),
    );
  }

  @override
  void initState() {
    super.initState();
    box = Hive.box('resultsBox');
  }
}
