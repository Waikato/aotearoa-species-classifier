import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'dart:math';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:image_picker/image_picker.dart';
import 'package:camera/camera.dart';
import 'package:path/path.dart' as path;
import 'package:path_provider/path_provider.dart';
import 'package:intl/intl.dart';
import 'package:hive/hive.dart';
import 'package:hive_flutter/hive_flutter.dart';
import 'package:pytorch_mobile/pytorch_mobile.dart';
import 'package:pytorch_mobile/model.dart';
import 'package:pytorch_mobile/enums/dtype.dart';

import 'package:flutter/foundation.dart';  // for debugPrint

import 'package:shared_preferences_android/shared_preferences_android.dart';
import 'package:shared_preferences_ios/shared_preferences_ios.dart';

import 'package:path_provider_android/path_provider_android.dart';
import 'package:path_provider_ios/path_provider_ios.dart';

import 'package:image_picker/image_picker.dart';

import 'globals.dart';
import 'classes/classification_result.dart';
//import 'classes/custom_models.dart';  // potential alternative to pytorch_mobile/model.dart
import 'classes/prediction.dart';
import 'classes/name_data.dart';
import 'screens/classification_history.dart';
import 'screens/classification.dart';
import 'screens/model_manager.dart';


void main() async {

  if (Platform.isAndroid) SharedPreferencesAndroid.registerWith();
  if (Platform.isIOS) SharedPreferencesIOS.registerWith();

  if (Platform.isAndroid) PathProviderAndroid.registerWith();
  if (Platform.isIOS) PathProviderIOS.registerWith();

  // Initialize hive database and prepare it
  await Hive.initFlutter();
  Hive.registerAdapter(ClassificationResultAdapter());  // register the adapter
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
  List<double> mean =  [0.5, 0.5, 0.5]; //[0.485, 0.456, 0.406];
  List<double> std = [0.5, 0.5, 0.5]; //[0.229, 0.224, 0.225]; //
  //String modelID = "species_model_squeezenet";
  String modelID = "species_model_s";
  Map<String, String> modelPaths = {
    "species_model_s": "assets/models/20231017_species_model_s.pt",
    "species_model_squeezenet": "assets/models/species_model_squeezenet.pt"
  };
  Map<String, int> modelDims = {
    "species_model_s": 384,
    "species_model_squeezenet": 224
  };

  //File? image;// = File("assets/logos/TAIAO.png");
  Model? imageModel;
  //PostProcessingModel? imageModel;
  String? imagePrediction;
  late final Box box;
  late final Box speciesNamesBox;
  //late final Map<String, dynamic> speciesNamesMap;

  Future<List<String>> _getLabels(String labelPath) async {
    String labelsData = await rootBundle.loadString(labelPath);
    return labelsData.split(",");
  }

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

  List? applyTemperatureScaling(List? prediction) {
    return prediction!.map((x) {return x * LOGIT_CALIBRATION_SCALE;}).toList();
  }

  List? applySoftmax(List? prediction) {
    double exponentSum = 0;
    for (int i=0; i<prediction!.length; i++){
      exponentSum = exponentSum + exp(prediction[i]);
    }
    return prediction.map((x) {return exp(x) / exponentSum;}).toList();
  }

  NameData _getNameData(int ID) {
    String stringID = ID.toString();
    NameData idNameData = NameData(
        ID,
        speciesNamesMap[stringID]["scientific_name"],
        List<String>.from(speciesNamesMap[stringID]["mri"]["common_names"]),
        List<String>.from(speciesNamesMap[stringID]["eng"]["common_names"])
    );
    return idNameData;
  }

  Future<List<Prediction>> _getTopFivePredictions(List? prediction) async {
    List<Prediction> predictions = prediction!.asMap().entries.map((entry) {
      int i = entry.key;
      NameData nameData = speciesNamesBox.get(i);
      //Prediction pred = Prediction(i, labels[i], entry.value, nameData);
      Prediction pred = Prediction(i, speciesNamesMap[i.toString()]["scientific_name"], entry.value, nameData);
      return pred;
    }).toList();

    predictions.sort((a, b) => _comparePredictions(a, b));
    predictions = predictions.reversed.toList();

    return predictions.sublist(0, 5);
  }

  Future loadNamesData() async {
    /*if (speciesNamesBox.values.length != 11047) {
      debugPrint("Updating speciesNamesBox because it currently contains ${speciesNamesBox.values.length} items instead of 11047");
      String namesDataString = await rootBundle.loadString("assets/labels/class_metadata.json");
      speciesNamesMap = jsonDecode(namesDataString);

      for (int i = 0; i < 11047; i++) {
        speciesNamesBox.put(i, _getNameData(i));
      }
    } else {
      debugPrint("Loading data string");
      String namesDataString = await rootBundle.loadString("assets/labels/class_metadata.json");
      speciesNamesMap = jsonDecode(namesDataString);
    }*/
    // instead of above approach, always reload names data every time
    debugPrint("Loading species data");
    String namesDataString = await rootBundle.loadString("assets/labels/species_14991_metadata.json");
    speciesNamesMap = jsonDecode(namesDataString);

    for (int i = 0; i < numClasses; i++) {
      speciesNamesBox.put(i, _getNameData(i));
    }
  }

  Future loadModel() async {
    String? modelPath = modelPaths[modelID];

    try {
      imageModel = await PyTorchMobile.loadModel(modelPath!);
    } on PlatformException {
      debugPrint("only supported for android and ios for now");
    }
  }

  Future _pickImage(BuildContext context, ImageSource source) async {
    try {
      final XFile? predImage = await ImagePicker().pickImage(
          source: source,
          maxHeight: 768,
          maxWidth: 768
      );
      if (predImage == null) return;

      // store image locally
      Directory dir = await getApplicationDocumentsDirectory();
      //final String dirPath = dir.path;
      final String dirPath = dir.path + "${Platform.pathSeparator}files${Platform.pathSeparator}$version";
      debugPrint(dirPath);
      final Directory targetDir = Directory(dirPath);
      final String filename = "${DateFormat('yyyyMMddkkmmss').format(DateTime.now())}.png";
      // alternatively to checking if image was picked from gallery above, save a copy of the image always
      String savePath = '$dirPath${Platform.pathSeparator}' + filename;

      if (!await targetDir.exists()) {
        await targetDir.create(recursive: true);
      }

      await predImage.saveTo(savePath);

      setState(() {
        _isLoading = true;
      });

      int? modelDim = modelDims[modelID];

      List? prediction = await imageModel!.getImagePredictionList(
        File(predImage.path),
        modelDim!,
        modelDim,
        mean: mean,
        std: std,
      );
      prediction = applyTemperatureScaling(prediction);
      prediction = applySoftmax(prediction);
      List<Prediction> topFivePredictions = await _getTopFivePredictions(prediction);
      box.add(ClassificationResult(topFivePredictions[0].species, savePath, DateTime.now(), topFivePredictions));

      //setState(() => this.image = File(predImage.path));  // unecessary?
      setState(() {
        _isLoading = false;
      });

      int boxIndex = box.values.length - 1;
      Navigator.push(
          context,
          MaterialPageRoute(builder: (context) => Classification(classificationID: boxIndex,))
      );
    } on PlatformException catch (e) {
      debugPrint('Failed in picking image: $e');
    }
  }

  Widget _buildButton({
    required String title,
    required IconData icon,
    required VoidCallback onClicked,
  }) => ElevatedButton(
    style: ElevatedButton.styleFrom(
        minimumSize: const Size.fromHeight(56),
        primary: Colors.amber,
        onPrimary: Colors.white,
        textStyle: const TextStyle(fontSize: 20),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(28.0))
    ),
    child: Row(
      children: [
        Icon(icon, size: 28,),
        const SizedBox(width: 16),
        Text(title),
      ],
    ),
    onPressed: onClicked,
  );

  @override
  void initState(){
    // during initialisation, get reference to opened box
    super.initState();
    box = Hive.box('resultsBox');
    speciesNamesBox = Hive.box('namesBox');
    loadNamesData();
    loadModel();
  }

  @override
  void dispose() {
    // close the hive box properly when closing the app
    Hive.close();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: _isLoading
          ? const Center(
        child: CircularProgressIndicator(),  // when an image is being
        // processed, should display the loading wheel.
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
                Expanded(child: SizedBox(
                  //height: 64.0,
                  child: Image(image: AssetImage('assets/logos/2020_School of Comp and Math Sciences w Logo.png')),
                ),
                ),
                SizedBox(width: 6),
                Expanded(child: SizedBox(
                  //height: 64.0,
                  child: Image(image: AssetImage('assets/logos/UCBlack_cropped.png')),
                )
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
                Expanded(child: SizedBox(
                  //height: 64.0,
                  child: Image(image: AssetImage('assets/logos/TAIAO.png')),
                ),
                ),
                SizedBox(width: 6),
                Expanded(child: SizedBox(
                  //height: 64.0,
                  child: Image(image: AssetImage('assets/logos/AI_institute.png')),
                )
                ),

              ],
            ),
            const SizedBox(height: 24),
            const Row(
              mainAxisSize: MainAxisSize.max,
              mainAxisAlignment: MainAxisAlignment.spaceEvenly,
              children: [
                Expanded(child: SizedBox(
                  child: Image(image: AssetImage('assets/logos/iNaturalist_NZ_with_kahukura_cropped.png')),
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
            _buildButton(title: 'Pick Camera',
                icon: Icons.camera_alt_outlined,
                onClicked: () => _pickImage(context, ImageSource.camera)),
            const SizedBox(height: 12),
            _buildButton(title: 'Pick Gallery',
                icon: Icons.image_outlined,
                onClicked: () => _pickImage(context, ImageSource.gallery)),
            const SizedBox(height: 12),
            _buildButton(title: 'Classification History',
                icon: Icons.history_outlined,
                onClicked: () {
                  Navigator.push(
                      context,
                      MaterialPageRoute(builder: (context) => const ClassificationHistory())
                  );
                }),
            const SizedBox(height: 12),
            _buildButton(title: 'Model Manager',
                icon: Icons.manage_search_outlined,
                onClicked: () {
                  Navigator.push(
                      context,
                      MaterialPageRoute(builder: (context) => const ModelManager())
                  );
                }),

            const Spacer(),
          ],
        ),
      ),
    );
  }
}


