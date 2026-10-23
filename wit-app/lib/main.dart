import 'dart:convert';
import 'dart:io';
import 'dart:math';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:image_picker/image_picker.dart';
import 'package:path/path.dart' as path;
import 'package:path_provider/path_provider.dart';
import 'package:intl/intl.dart';
import 'package:hive/hive.dart';
import 'package:hive_flutter/hive_flutter.dart';
import 'package:wit_app/classes/onnx_species_model.dart';
import 'package:wit_app/classes/prediction.dart';

import 'package:flutter/foundation.dart'; // for debugPrint

import 'globals.dart';
import 'classes/classification_result.dart';
//import 'classes/custom_models.dart';  // potential alternative to pytorch_mobile/model.dart
import 'classes/name_data.dart';
import 'screens/classification_history.dart';
import 'screens/classification.dart';
import 'screens/model_manager.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // Initialize hive database and prepare it
  await Hive.initFlutter();
  Hive.registerAdapter(ClassificationResultAdapter()); // register the adapter
  Hive.registerAdapter(PredictionAdapter());
  Hive.registerAdapter(NameDataAdapter());
  await Hive.openBox('resultsBox');
  await Hive.openBox('namesBox');

  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({Key? key}) : super(key: key);

  // This widget is the root of your application.
  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'WIT app',
      theme: ThemeData(
        primarySwatch: Colors.teal,
        scaffoldBackgroundColor: const Color(0xFFeff6e0),
        /*textTheme: TextTheme(
          bodyLarge: TextStyle(color: Colors.indigo.shade900),
          bodyMedium: TextStyle(color: Colors.indigo.shade900),
          bodySmall: TextStyle(color: Colors.indigo.shade900),
          //bodyText1: TextStyle(color: Colors.indigo.shade900),
          //bodyText2: TextStyle(color: Colors.indigo.shade900),
        )*/
      ),
      home: const MyHomePage(title: 'What Is This?'),
      debugShowCheckedModeBanner: false,
    );
  }
}

class MyHomePage extends StatefulWidget {
  const MyHomePage({Key? key, required this.title}) : super(key: key);

  final String title;

  @override
  State<MyHomePage> createState() => _MyHomePageState();
}

class _MyHomePageState extends State<MyHomePage> {
  bool _isLoading = false;
  bool _isInitialising = true;
  String? _initialisationError;

  OnnxSpeciesModel? imageModel;
  late final Box box;
  late final Box speciesNamesBox;

  int _comparePredictions(Prediction a, Prediction b) {
    // comparator function allows sorting of Prediction class instances
    if (a.probability < b.probability) {
      return -1;
    } else if (a.probability == b.probability) {
      return 0;
    } else {
      return 1;
    }
  }

  List<double> applyTemperatureScaling(List<double> prediction) {
    return prediction
        .map((double value) => value * LOGIT_CALIBRATION_SCALE)
        .toList();
  }

  List<double> applySoftmax(List<double> prediction) {
    final double maxValue = prediction.reduce((a, b) => a > b ? a : b);

    double exponentSum = 0.0;

    for (final value in prediction) {
      exponentSum += exp(value - maxValue);
    }

    return prediction
        .map((value) => exp(value - maxValue) / exponentSum)
        .toList();
  }

  NameData _getNameData(int ID) {
    String stringID = ID.toString();
    NameData idNameData = NameData(
      ID,
      speciesNamesMap[stringID]["scientific_name"],
      List<String>.from(speciesNamesMap[stringID]["mri"]["common_names"]),
      List<String>.from(speciesNamesMap[stringID]["eng"]["common_names"]),
    );
    return idNameData;
  }

  List<Prediction> _getTopFivePredictions(List<double> prediction) {
    List<Prediction> predictions = prediction.asMap().entries.map((entry) {
      int i = entry.key;
      NameData nameData = speciesNamesBox.get(i);
      //Prediction pred = Prediction(i, labels[i], entry.value, nameData);
      Prediction pred = Prediction(
        i,
        speciesNamesMap[i.toString()]["scientific_name"],
        entry.value,
        nameData,
      );
      return pred;
    }).toList();

    predictions.sort((a, b) => _comparePredictions(a, b));
    predictions = predictions.reversed.toList();

    return predictions.sublist(0, 5);
  }

  Future<void> loadNamesData() async {
    //debugPrint("Loading species data");
    String namesDataString = await rootBundle.loadString(
      "assets/labels/species_14991_metadata.json",
    );

    speciesNamesMap = jsonDecode(namesDataString);

    final Map<int, NameData> nameData = {
      for (int i = 0; i < numClasses; i++) i: _getNameData(i),
    };

    await speciesNamesBox.putAll(nameData);
  }

  Future<void> loadModel() async {
    imageModel = OnnxSpeciesModel(
      assetPath: 'assets/models/species_classifier_fp32_384_384.onnx',
      width: 384,
      height: 384,
      mean: const <double>[0.5, 0.5, 0.5],
      std: const <double>[0.5, 0.5, 0.5],
    );

    await imageModel!.load();

    //debugPrint("ONNX model loaded");
  }

  Future<void> _pickImage(ImageSource source) async {
    try {
      final XFile? predImage = await ImagePicker().pickImage(
        source: source,
      ); //, maxHeight: 768, maxWidth: 768);
      if (predImage == null) return;

      // store image locally
      Directory dir = await getApplicationDocumentsDirectory();
      //final String dirPath = dir.path +
      //    "${Platform.pathSeparator}files${Platform.pathSeparator}$version";
      final String dirPath = path.join(dir.path, 'files', version);
      final Directory targetDir = Directory(dirPath);
      final String filename =
          "${DateFormat('yyyyMMddkkmmss_SSS').format(DateTime.now())}.png";
      // alternatively to checking if image was picked from gallery above, save a copy of the image always
      //String savePath = '$dirPath${Platform.pathSeparator}' + filename;
      final String savePath = path.join(dirPath, filename);

      if (!await targetDir.exists()) {
        await targetDir.create(recursive: true);
      }

      await predImage.saveTo(savePath);

      if (!mounted) return;

      setState(() {
        _isLoading = true;
      });

      List<double> prediction = await imageModel!.getImagePredictionList(
        File(savePath),
      );

      prediction = applyTemperatureScaling(prediction);
      prediction = applySoftmax(prediction);
      List<Prediction> topFivePredictions = _getTopFivePredictions(prediction);
      final int classificationKey = await box.add(
        ClassificationResult(
          topFivePredictions[0].species,
          savePath,
          DateTime.now(),
          topFivePredictions,
        ),
      );

      if (!mounted) return;

      setState(() {
        _isLoading = false;
      });

      Navigator.push(
        context,
        MaterialPageRoute(
          builder: (context) =>
              Classification(classificationKey: classificationKey),
        ),
      );
    } on PlatformException catch (e) {
      debugPrint('Platform operation failed: $e');

      if (mounted) {
        setState(() {
          _isLoading = false;
        });

        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('The image could not be processed.')),
        );
      }
    } catch (e, stackTrace) {
      debugPrint('Classification failed: $e');
      debugPrintStack(stackTrace: stackTrace);

      if (mounted) {
        setState(() {
          _isLoading = false;
        });
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('The image could not be classified.')),
        );
      }
    }
  }

  Widget _buildButton({
    required String title,
    required IconData icon,
    required VoidCallback onClicked,
  }) => ElevatedButton(
    style: ElevatedButton.styleFrom(
      minimumSize: const Size.fromHeight(56),
      backgroundColor: Colors.amber,
      foregroundColor: Colors.white,
      textStyle: const TextStyle(fontSize: 20),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(28.0)),
    ),
    child: Row(
      children: [Icon(icon, size: 28), const SizedBox(width: 16), Text(title)],
    ),
    onPressed: onClicked,
  );

  @override
  void initState() {
    // during initialisation, get reference to opened box
    super.initState();
    box = Hive.box('resultsBox');
    speciesNamesBox = Hive.box('namesBox');
    _initialise();
  }

  Future<void> _initialise() async {
    try {
      await Future.wait([loadNamesData(), loadModel()]);

      if (!mounted) return;

      setState(() {
        _isInitialising = false;
      });
    } catch (e, stackTrace) {
      debugPrint('Initialization failed: $e');
      debugPrintStack(stackTrace: stackTrace);

      if (!mounted) return;

      setState(() {
        _isInitialising = false;
        _initialisationError = 'The classification model could not be loaded.';
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: _isInitialising || _isLoading
          ? const Center(
              child: CircularProgressIndicator(), // when an image is being
              // processed, should display the loading wheel.
            )
          : _initialisationError != null
          ? Center(
              child: Padding(
                padding: const EdgeInsets.all(32),
                child: Text(_initialisationError!, textAlign: TextAlign.center),
              ),
            )
          : Container(
              padding: const EdgeInsets.all(32),
              child: Column(
                children: <Widget>[
                  const Spacer(),
                  const Row(
                    mainAxisSize: MainAxisSize.max,
                    mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                    children: [
                      //Image(image: AssetImage('assets/logos/Waikato Regional Council logo.jpg'),),
                      //Image(image: AssetImage('assets/logos/TAIAO.png')),
                      Expanded(
                        child: SizedBox(
                          //height: 64.0,
                          child: Image(
                            image: AssetImage(
                              'assets/logos/2020_School of Comp and Math Sciences w Logo.png',
                            ),
                          ),
                        ),
                      ),
                      SizedBox(width: 6),
                      Expanded(
                        child: SizedBox(
                          //height: 64.0,
                          child: Image(
                            image: AssetImage(
                              'assets/logos/UCBlack_cropped.png',
                            ),
                          ),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 24),
                  const Row(
                    mainAxisSize: MainAxisSize.max,
                    mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                    children: [
                      //Image(image: AssetImage('assets/logos/Waikato Regional Council logo.jpg'),),
                      //Image(image: AssetImage('assets/logos/TAIAO.png')),
                      Expanded(
                        child: SizedBox(
                          //height: 64.0,
                          child: Image(
                            image: AssetImage('assets/logos/TAIAO.png'),
                          ),
                        ),
                      ),
                      SizedBox(width: 6),
                      Expanded(
                        child: SizedBox(
                          //height: 64.0,
                          child: Image(
                            image: AssetImage('assets/logos/AI_institute.png'),
                          ),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 24),
                  const Row(
                    mainAxisSize: MainAxisSize.max,
                    mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                    children: [
                      Expanded(
                        child: SizedBox(
                          child: Image(
                            image: AssetImage(
                              'assets/logos/iNaturalist_NZ_with_kahukura_cropped.png',
                            ),
                          ),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 36),
                  /*image != null ? ClipOval(
                child: Image.file(
                  image!,
                  width: 224,
                  height: 224,
                  fit: BoxFit.cover,)
            )
                : const SizedBox.shrink(),/*Container(
              margin: const EdgeInsets.symmetric(horizontal: 20),
              child: const Image(image: AssetImage('assets/logos/TAIAO.png')),
            ),*/
            const SizedBox(height: 12),*/
                  _buildButton(
                    title: 'Pick Camera',
                    icon: Icons.camera_alt_outlined,
                    onClicked: () => _pickImage(ImageSource.camera),
                  ),
                  const SizedBox(height: 12),
                  _buildButton(
                    title: 'Pick Gallery',
                    icon: Icons.image_outlined,
                    onClicked: () => _pickImage(ImageSource.gallery),
                  ),
                  const SizedBox(height: 12),
                  _buildButton(
                    title: 'Classification History',
                    icon: Icons.history_outlined,
                    onClicked: () {
                      Navigator.push(
                        context,
                        MaterialPageRoute(
                          builder: (context) => const ClassificationHistory(),
                        ),
                      );
                    },
                  ),
                  const SizedBox(height: 12),
                  _buildButton(
                    title: 'Model Manager',
                    icon: Icons.manage_search_outlined,
                    onClicked: () {
                      Navigator.push(
                        context,
                        MaterialPageRoute(
                          builder: (context) => const ModelManager(),
                        ),
                      );
                    },
                  ),
                  const Spacer(),
                ],
              ),
            ),
    );
  }
}
