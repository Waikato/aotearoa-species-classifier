//import 'dart:html';

import 'package:camera/camera.dart';
import 'package:flutter/gestures.dart';
import 'package:flutter/material.dart';
import 'dart:io';
import 'package:intl/intl.dart';
import 'package:hive/hive.dart';
import 'package:path_provider/path_provider.dart';
import 'package:path/path.dart' as path;
import 'package:url_launcher/url_launcher.dart';
import 'package:url_launcher/url_launcher_string.dart';

import 'package:wit_app/classes/classification_result.dart';
import 'package:wit_app/utils/custom_expansion_tile.dart';

import 'package:wit_app/globals.dart';



class Classification extends StatefulWidget {
  final int classificationID;
  const Classification({Key? key, required this.classificationID}) : super(key: key);

  @override
  _Classification createState() => _Classification();
}

class _Classification extends State<Classification>{
  late final Box box;
  late final ClassificationResult classificationResult;
  late final String stringID;
  late final String speciesName;
  late final List<String> engNames;
  late final List<String> mriNames;
  late final bool isPlantOriented;  // whether or not the prediction seems likely to revolve around plants
  late final bool isUnwanted;
  late final int notifiableStatus; // -1 for not notifiable, 0 for both, 1 for notifiable
  late final String wikipediaSummary;
  late final String wikipediaLink;
  late final bool deprecatedEntry;
  //Image? image;
  final ScrollController controller = ScrollController();

  String getTitle(){
    if (classificationResult.topFivePredictions[0].probability < PROB_THRESHOLD ){
      return "Unknown";
    }
    String returnText = classificationResult.prediction;
    List<String> engNames = classificationResult.topFivePredictions[0].nameData.engNames.isEmpty ? [""] : classificationResult.topFivePredictions[0].nameData.engNames;
    List<String> mriNames = classificationResult.topFivePredictions[0].nameData.mriNames.isEmpty ? [""] : classificationResult.topFivePredictions[0].nameData.mriNames;
    //String return_text = "${getCommonName(classificationResult.prediction, engNames, mriNames)}";
    if (engNames[0] != "") {
      returnText = returnText + " | " + classificationResult.topFivePredictions[0].nameData.engNames[0];
    }
    if (mriNames[0] != "" && mriNames[0] != engNames[0]) {
      returnText = returnText + " | " + mriNames[0];
    }
    return returnText;
  }

  String probability2String(double probability){
    if (probability <= 0.001) {
      return "monstrously infinitesimal confidence";
    } else if (probability > 0.001 && probability <= 0.022) {
      return "abysmally low confidence";
    } else if (probability > 0.022 && probability <= 0.158) {
      return "very low confidence";
    } else if (probability > 0.158 && probability <= 0.50) {
      return "low confidence";
    } else if (probability > 0.50 && probability <= 0.841) {
      return "reasonable confidence";
    } else if (probability > 0.841 && probability <= 0.977) {
      return "very high confidence";
    } else if (probability > 0.977 && probability <= 0.998) {
      return "extremely high confidence";
    } else {
      return "positively overwhelming confidence";
    }
  }

  List<String> createNamesList(List<String> engNames, List<String> mriNames){
    List<String> commonNames = <String>[];
    if (engNames.isEmpty) {
      commonNames = mriNames;
    } else if (mriNames.isEmpty) {
      commonNames = engNames;
    } else {
      commonNames = List.from(engNames)..addAll(mriNames);
      commonNames = commonNames.toSet().toList();  // remove repeated names
    }
    return commonNames;
  }

  String createCommonNamesString(List<String> engNames, List<String> mriNames) {
    if (engNames.isEmpty && mriNames.isEmpty){
      return "There are no common names for this species.";
    }
    List<String> commonNames = <String>[];
    if (engNames.isEmpty) {
      commonNames = mriNames;
    } else if (mriNames.isEmpty) {
      commonNames = engNames;
    } else {
      commonNames = List.from(engNames)..addAll(mriNames);
      commonNames = commonNames.toSet().toList();  // remove repeated names
    }
    String commonName = commonNames[0];
    return "";
  }

  String getCommonName(String latinName, List<String> engNames, List<String> mriNames) {
    if (engNames.isEmpty && mriNames.isEmpty || (engNames[0] == "" && mriNames[0] == "")) { return latinName;}
    String topEngName = engNames.isEmpty ? "" : engNames[0];
    String topMriName = mriNames.isEmpty ? "" : mriNames[0];
    String returnName = (topEngName != "" && topMriName != "") ?
    ((topEngName == topMriName) ?
    topEngName :
    "${topEngName} / ${topMriName}") :
    ((topEngName != "") ?
    topEngName :
    topMriName);
    return returnName;
  }

  Future<RichText> createNameDetailsText(String prediction, List<String> engNames, List<String> mriNames, double probability) async {
    //TODO: handle this stuff when all data is loaded correctly
    String confidenceText = "With ${probability2String(probability)}, this is a ";

    // if probability is < threshold, return an "I don't know" message instead.
    if (probability < PROB_THRESHOLD){
      return RichText(
          text: TextSpan(
            children: <TextSpan>[
              const TextSpan(text: "Confidence is too low to make a strong prediction. "),
              TextSpan(text: probability > 0.1 ? "The best guess would be ${(prediction)}." : "")
            ],
            style: const TextStyle(color: Colors.black),
          )
      );
    }

    if (engNames.isEmpty && mriNames.isEmpty || (engNames[0] == "" && mriNames[0] == "")){
      return RichText(
        text: TextSpan(
          children: <TextSpan>[
            TextSpan(text: confidenceText),
            TextSpan(text: prediction, style: const TextStyle(fontWeight: FontWeight.bold)),
            const TextSpan(text: ". No common names for this species found in the database.")
          ],
          style: const TextStyle(color: Colors.black),
        ),
      );
    }

    String topEngName = engNames.isEmpty ? "" : engNames[0];
    String topMriName = mriNames.isEmpty ? "" : mriNames[0];
    /*IF neither the top eng nor top mri names are empty,
    * THEN
    *   IF top eng == top mri
    *   THEN use top eng
    *   ELSE say "top mri, or top eng"
    * ELSE
    *   IF top eng isn't empty
    *   THEN use top eng
    *   ELSE use top mri*/
    String topName = (topEngName != "" && topMriName != "") ?
    ((topEngName == topMriName) ?
    topEngName :
    "$topMriName, or $topEngName") :
    ((topEngName != "") ?
    topEngName :
    topMriName);

    List<String> remainingNames = (topEngName != "" && topMriName != "") ?
    (List.from(engNames.sublist(1))..addAll(mriNames.sublist(1))) :
    ((topEngName != "") ?
    engNames.sublist(1) :
    mriNames.sublist(1));
    remainingNames = remainingNames.toSet().toList();

    if (remainingNames.isEmpty){
      //return "This species is commonly known as a ${topName}.";
      return RichText(text: TextSpan(
        children: <TextSpan>[
          TextSpan(text: confidenceText),
          //TextSpan(text: deprecatedEntry == true ? "deprecated entry!" : "entry acceptable"),
          TextSpan(text: topName, style: const TextStyle(fontWeight: FontWeight.bold)),
          const TextSpan(text: ".")
        ],
        style: const TextStyle(color: Colors.black),
      )
      );
    } else {
      //return "This species is commonly known as a ${topName}. \n\n"
      //    "It is also known by a number of other names, such as: ${remainingNames.join(", ")}";
      return RichText(text: TextSpan(
        children: <TextSpan>[
          TextSpan(text: confidenceText),
          TextSpan(text: topName, style: const TextStyle(fontWeight: FontWeight.bold)),
          const TextSpan(text: "."),
          const TextSpan(text: "\n\nIt is also known by a number of other names, such as: \n"),
          TextSpan(text: remainingNames.join(", ")),
          const TextSpan(text: ".")
        ],
        style: const TextStyle(color: Colors.black),
      )
      );
    }
  }

  Future<RichText> createWikipediaText() async {
    // return nothing if the entry is deprecated or there isn't enough confidence for a prediction
    if (deprecatedEntry == true || classificationResult.topFivePredictions[0].probability < PROB_THRESHOLD){
      return RichText(text: const TextSpan(text: ""));
    }

    // otherwise, respond with wikipedia summaries
    List<TextSpan> wikiResponses = [];
    if (speciesNamesMap[stringID]["eng"]["wikipedia_link"] != "") {
      wikiResponses.add(
          const TextSpan(
            text: "\nFrom ",
            style: TextStyle(
              fontWeight: FontWeight.bold,
              fontSize: 24.0,
              color: Colors.black,
            ),
          )
      );
      wikiResponses.add(
        TextSpan(
          text: "Wikipedia:",
          style: const TextStyle(
              fontWeight: FontWeight.bold,
              fontSize: 24.0,
              color: Colors.amber,
              decoration: TextDecoration.underline
          ),
          recognizer: TapGestureRecognizer()..onTap = () { launchUrlString(speciesNamesMap[stringID]["eng"]["wikipedia_link"]);},
        ),
      );
      wikiResponses.add(
          TextSpan(
              text: "\n\n" + speciesNamesMap[stringID]["eng"]["wikipedia_summary"]
          )
      );
      // add some extra newlines if mri entries exist as well
      if (speciesNamesMap[stringID]["mri"]["wikipedia_link"] != "") {
        wikiResponses.add(const TextSpan(text: "\n\n",));
      }
    }
    if (speciesNamesMap[stringID]["mri"]["wikipedia_link"] != ""){
      wikiResponses.add(
        const TextSpan(
          text: "\nMai i te ",
          style: TextStyle(
            fontWeight: FontWeight.bold,
            fontSize: 24.0,
            color: Colors.black,
          ),
        ),
      );
      wikiResponses.add(
          TextSpan(
            text: "Wikipedia:",
            style: const TextStyle(
                fontWeight: FontWeight.bold,
                fontSize: 24.0,
                color: Colors.amber,
                decoration: TextDecoration.underline
            ),
            recognizer: TapGestureRecognizer()..onTap = () { launchUrlString(speciesNamesMap[stringID]["mri"]["wikipedia_link"]);},
          )
      );
      wikiResponses.add(
          TextSpan(
            text: "\n\n" + speciesNamesMap[stringID]["mri"]["wikipedia_summary"],
          )
      );
    }

    return RichText(text: TextSpan(
      children: wikiResponses,
      style: const TextStyle(color: Colors.black),
    ));
  }

  Card createBasicCard(){
    List<TextSpan> placeholder = [const TextSpan(text: "")];
    return Card(
      elevation: 0,
      color: const Color(0xFFeff6e0),
      child: Container(
          padding: const EdgeInsets.all(8),
          child: RichText(
            text: TextSpan(
                children: placeholder,
                style: const TextStyle(color: Colors.teal)
            ),
          )
      ),
      shape: const RoundedRectangleBorder(
          side: BorderSide(
            color: Colors.teal,
          ),
          borderRadius: BorderRadius.all(Radius.circular(12))
      ),
    );
  }

  Future<Card> createDetailsCard(List<TextSpan> details, String detailType) async {
    Color tileColor = const Color(0xFFeff6e0);
    Color textColor = Colors.teal;
    switch (detailType) {
      case "helper":
        tileColor = const Color(0xFFeff6e0);
        textColor = Colors.teal;
        break;
      case "warning":
        tileColor = Colors.teal;
        textColor = const Color(0xFFeff6e0);
        break;
      case "alert":
        tileColor = Colors.deepOrange;
        textColor = const Color(0xFFeff6e0);
        break;
    }

    if (detailType == "helper"){
      return Card(
        elevation: 0,
        color: tileColor,
        child: Container(
            padding: const EdgeInsets.all(8),
            child: RichText(
              text: TextSpan(
                  children: details,
                  style: TextStyle(color: textColor)
              ),
            )
        ),
        shape: const RoundedRectangleBorder(
            side: BorderSide(
              color: Colors.teal,
            ),
            borderRadius: BorderRadius.all(Radius.circular(12))
        ),
      );
    }

    return Card(
        elevation: 2,
        color: tileColor,
        child: Container(
            padding: const EdgeInsets.all(8),
            child: RichText(
              text: TextSpan(
                  children: details,
                  style: TextStyle(color: textColor)
              ),
            )
        ),
        shape: const RoundedRectangleBorder(
            borderRadius: BorderRadius.all(Radius.circular(12))
        )
    );
  }


  ListTile createTopFiveListTile(int index){
    String numberString = "${index + 1}. ";
    return ListTile(
      leading: Text(numberString),
      title: SelectableText(classificationResult.topFivePredictions[index].species),
      trailing: Text((classificationResult.topFivePredictions[index].probability).toStringAsPrecision(3)),
      textColor: const Color(0xFFeff6e0).withOpacity(classificationResult.topFivePredictions[index].probability / 4 + 0.75),
    );
  }

  Future loadSpeciesData() async {
    stringID = classificationResult.topFivePredictions[0].index.toString();
    //engNames = List<String>.from(speciesNamesMap[stringID]["eng"]);
    //mriNames = List<String>.from(speciesNamesMap[stringID]["mri"]);
    engNames = classificationResult.topFivePredictions[0].nameData.engNames;
    mriNames = classificationResult.topFivePredictions[0].nameData.mriNames;
    bool acceptPred = classificationResult.topFivePredictions[0].probability >= PROB_THRESHOLD;  // no need to display notifications if confidence is too low
    // set plant status
    List<String> topFiveIndices = [
      classificationResult.topFivePredictions[0].index.toString(),
      classificationResult.topFivePredictions[1].index.toString(),
      classificationResult.topFivePredictions[2].index.toString(),
      classificationResult.topFivePredictions[3].index.toString(),
      classificationResult.topFivePredictions[4].index.toString(),
    ];

    // check if this information was saved with the current database
    String imagePath = classificationResult.imagePath;
    List<String> pathComponents = path.split(imagePath);
    String usedVersion = pathComponents[pathComponents.length - 2];
    //debugPrint("getting last element of split...");
    //debugPrint(usedVersion);
    deprecatedEntry = usedVersion != version;  // if usedVersion != current version, then the entry is deprecated and some data cannot be reliably retrieved.

    if (deprecatedEntry == false) {
      int plantCount = 0;
      int nonEmptyCount = 0;
      for (int i = 0; i < 5; i++) {
        nonEmptyCount += speciesNamesMap[topFiveIndices[i]]["kingdom"] == ""
            ? 0
            : 1; // if the kingdom string is empty, add nothing to the count, else 1
        plantCount +=
        speciesNamesMap[topFiveIndices[i]]["kingdom"] == "Plantae" ? 1 : 0;
      }
      if (plantCount > nonEmptyCount ~/ 2 ||
          speciesNamesMap[stringID]["kingdom"] ==
              "Plantae") { // if most top 5 species are plants or the top prediction is a plant, the prediction is plant oriented
        isPlantOriented = true; // needs to be redone
      } else {
        isPlantOriented = false;
      }
      // set notifiable status
      if (speciesNamesMap[stringID]["notifiable"] == "Yes" && speciesNamesMap[stringID]["unwanted"] != "No,Yes" && acceptPred) {
        notifiableStatus = 1;
      } else
      if ((speciesNamesMap[stringID]["notifiable"] == "No,Yes" || speciesNamesMap[stringID]["unwanted"] == "No,Yes") && acceptPred) {
        notifiableStatus = 0;
      } else {
        notifiableStatus = -1;
      }
      // set unwanted status
      if (speciesNamesMap[stringID]["unwanted"] == "Yes" &&
          notifiableStatus == -1 && acceptPred) {
        isUnwanted = true;
      } else {
        isUnwanted = false;
      }
    } else {
      isPlantOriented = false;
      notifiableStatus = -1;
      isUnwanted = false;
    }
    //debugPrint("deprecatedEntry: $deprecatedEntry");
    //debugPrint("notifiableStatus: $notifiableStatus");
  }

  /*Future<Text> _getSearchPath(String imagePath) async {
    /*
    * For debugging purposes, get the paths images are being searched for...
    * */
    Directory dir = await getApplicationDocumentsDirectory();
    final String dirPath = dir.path;

    File standardFile = File(imagePath);
    if (await standardFile.exists()) {
      return Text(imagePath);
    }
    File legacyFile = File('$dirPath${Platform.pathSeparator}files${Platform.pathSeparator}' + path.basename(imagePath));
    if (await legacyFile.exists()) {
      return Text('$dirPath${Platform.pathSeparator}files${Platform.pathSeparator}' + path.basename(imagePath));
    }
    if (Platform.isIOS) {
      final cacheDirectory = await getTemporaryDirectory();
      final cachePath = cacheDirectory.path; // /var/mobile/Containers/Data/Application/{build hash}/Library/Caches
      String tmpPath = path.dirname(cachePath);  // /var/mobile/Containers/Data/Application/{build hash}/Library
      tmpPath = path.dirname(tmpPath);  // /var/mobile/Containers/Data/Application/{build hash}
      File iosCacheFile = File(cachePath + Platform.pathSeparator + path.basename(imagePath));
      if (await iosCacheFile.exists()) {
        return Text(cachePath + Platform.pathSeparator + path.basename(imagePath));
      }
      File iosTmpFile = File(tmpPath + Platform.pathSeparator + "tmp" + Platform.pathSeparator + path.basename(imagePath));
      if (await iosTmpFile.exists()){
        return Text(tmpPath + Platform.pathSeparator + "tmp" + Platform.pathSeparator + path.basename(imagePath));
      }
      File iosTmpFile2 = File("${Platform.pathSeparator}private$tmpPath${Platform.pathSeparator}tmp${Platform.pathSeparator}${path.basename(imagePath)}");
      if (await iosTmpFile2.exists()){
        return Text("${Platform.pathSeparator}private$tmpPath${Platform.pathSeparator}tmp${Platform.pathSeparator}${path.basename(imagePath)}");
      }
      return Text("Looked for " + cachePath + Platform.pathSeparator + path.basename(imagePath) + "\nand " +
          tmpPath + Platform.pathSeparator + "tmp" + Platform.pathSeparator + path.basename(imagePath) +
          "\nand ${Platform.pathSeparator}private$tmpPath${Platform.pathSeparator}tmp${Platform.pathSeparator}${path.basename(imagePath)}" + " but found nothing");
    }
    return Text("Nothing at " + imagePath + "\nor at " + '$dirPath${Platform.pathSeparator}files${Platform.pathSeparator}' + path.basename(imagePath));
  }*/

  Future<void> _resaveImage(String srcPath, String tgtPath) async {
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
    debugPrint(imagePath);
    Directory dir = await getApplicationDocumentsDirectory();
    final String dirPath = dir.path;
    final String tgtPath = '$dirPath${Platform.pathSeparator}files${Platform.pathSeparator}' + path.basename(imagePath);
    //debugPrint(dirPath + "\n\n" + path.dirname(dirPath) + "\n\n" + path.dirname(path.dirname(dirPath)));

    File standardFile = File(tgtPath);
    if (await standardFile.exists()) {
      //debugPrint("Loaded image from $tgtPath");
      return Image.file(standardFile);
      //opacity: const AlwaysStoppedAnimation(0.5),);
    }
    File surfaceFile = File(imagePath);
    if (await surfaceFile.exists()) {
      //debugPrint("loaded image from $imagePath");
      await _resaveImage(imagePath, tgtPath);
      return Image.file(surfaceFile);
    }
    if (Platform.isIOS) {
      final cacheDirectory = await getTemporaryDirectory();
      final cachePath = cacheDirectory.path;
      String tmpPath = path.dirname(cachePath);  // /var/mobile/Containers/Data/Application/{build hash}/Library
      tmpPath = path.dirname(tmpPath);  // /var/mobile/Containers/Data/Application/{build hash}
      File iosCacheFile = File(cachePath + Platform.pathSeparator + path.basename(imagePath));
      if (await iosCacheFile.exists()) {
        await _resaveImage(cachePath + Platform.pathSeparator + path.basename(imagePath), tgtPath);
        return Image.file(iosCacheFile);
      }
      File iosTmpFile = File(tmpPath + Platform.pathSeparator + "tmp" + Platform.pathSeparator + path.basename(imagePath));
      if (await iosTmpFile.exists()){
        await _resaveImage(tmpPath + Platform.pathSeparator + "tmp" + Platform.pathSeparator + path.basename(imagePath), tgtPath);
        return Image.file(iosTmpFile);
      }
      File iosTmpFile2 = File("${Platform.pathSeparator}private$tmpPath${Platform.pathSeparator}tmp${Platform.pathSeparator}${path.basename(imagePath)}");
      if (await iosTmpFile2.exists()){
        await _resaveImage("${Platform.pathSeparator}private$tmpPath${Platform.pathSeparator}tmp${Platform.pathSeparator}${path.basename(imagePath)}", tgtPath);
        return Image.file(iosTmpFile2);
      }
      return null;
    }
    return null;
  }

  @override
  void initState() {
    super.initState();
    box = Hive.box('resultsBox');
    //debugPrint("${widget.classificationID}");
    classificationResult = box.getAt(widget.classificationID);  // for demo purposes, select first(?) entry for now.
    loadSpeciesData();
  }

  @override
  Widget build(BuildContext context){
    return Scaffold(
        appBar: AppBar(
          title: Text(classificationResult.topFivePredictions[0].probability >= PROB_THRESHOLD ? getCommonName(classificationResult.prediction, engNames, mriNames) : "Unknown"),
        ),
        body: SingleChildScrollView(
            child: ListView(
              controller: controller,
              physics: const ScrollPhysics(),
              shrinkWrap: true,
              children: [
                FittedBox(
                  child: FutureBuilder<Image?>(  // wait for image to be found/loaded and display icon in the meantime
                    future: _getImage(classificationResult.imagePath),
                    builder: (context, snapshot) {
                      if (snapshot.hasData) {
                        return snapshot.data ?? const Icon(Icons.image_not_supported_outlined);
                      } else {
                        return const Icon(Icons.image_not_supported_outlined);
                      }
                    },
                  ),
                  fit: BoxFit.fill,
                ),
                Container(
                  padding: const EdgeInsets.all(32),
                  child: Row(
                    children: [
                      Expanded(child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Container(
                            padding: const EdgeInsets.only(bottom: 8),
                            child: SelectableText(
                              getTitle(),
                              style: const TextStyle(
                                fontWeight: FontWeight.bold,
                                fontSize: 32.0,
                              ),
                            ),
                          ),
                          const SizedBox(height: 12),
                          Text(
                            "Prediction probability: ${(classificationResult.topFivePredictions[0].probability).toStringAsPrecision(3)}",
                            style: const TextStyle(
                              fontWeight: FontWeight.bold,
                              fontSize: 16.0,
                            ),
                          ),
                          Visibility(
                              visible: isPlantOriented,
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  const SizedBox(height: 12),
                                  FutureBuilder<Card>(
                                    future: createDetailsCard(<TextSpan>[
                                      const TextSpan(text: "Are you trying to classify plants?\t"),
                                      const TextSpan(text: "We recommend taking close-up photographs of individual leaves, rather than "
                                          "images of the whole plant - the model tends to perform better that way.")
                                    ], "helper"),
                                    builder: (context, snapshot) {
                                      if (snapshot.hasData) {
                                        return snapshot.data ?? createBasicCard();
                                      } else {
                                        return createBasicCard();
                                      }
                                    },
                                  )
                                ],
                              )
                          ),
                          const SizedBox(height: 12),
                          FutureBuilder<RichText>(
                            future: createNameDetailsText(
                                classificationResult.prediction,
                                engNames,
                                mriNames,
                                classificationResult.topFivePredictions[0].probability
                            ),
                            builder: (context, snapshot){
                              if (snapshot.hasData) {
                                return snapshot.data ?? const Text("");
                              } else {
                                return const Text("");
                              }
                            },
                          ),
                          const SizedBox(height: 12),
                          FutureBuilder<RichText>(
                              future: createWikipediaText(),
                              builder: (context, snapshot){
                                if (snapshot.hasData) {
                                  return snapshot.data ?? const Text("");
                                } else {
                                  return const Text("");
                                }
                              }
                          ),
                          const SizedBox(height: 12),
                          Visibility(
                              visible: isUnwanted,
                              child: FutureBuilder<Card>(
                                future: createDetailsCard(
                                    <TextSpan>[
                                      const TextSpan(text: "The Ministry of Primary Industries (MPI) considers this to be an "),
                                      const TextSpan(text: "unwanted ", style: TextStyle(fontWeight: FontWeight.bold)),
                                      const TextSpan(text: "organism.")
                                    ], "warning"),
                                builder: (context, snapshot) {
                                  if (snapshot.hasData) {
                                    return snapshot.data ?? createBasicCard();
                                  } else {
                                    return createBasicCard();
                                  }
                                },
                              )
                          ),
                          Visibility(
                            visible: notifiableStatus == 0,
                            child: FutureBuilder<Card>(
                              future: createDetailsCard(
                                  <TextSpan>[
                                    const TextSpan(text: "There are multiple variants of this species, some of which are "
                                        "considered notifiable pests. Unfortunately, the classifier cannot distinguish between these variants."),
                                    const TextSpan(text: "\n\n"),
                                    const TextSpan(text: "A notifiable organism could seriously harm New Zealand's primary production or our "
                                        "trade and market access. If you suspect this is a notifiable variant, consider following the steps "
                                        "outlined by the "),
                                    TextSpan(
                                        text: "Ministry of Primary Industries.",
                                        style: const TextStyle(color: Colors.amber),
                                        recognizer: TapGestureRecognizer()..onTap = () { launchUrlString("https://www.mpi.govt.nz/biosecurity/how-to-find-report-and-prevent-pests-and-diseases/report-a-pest-or-disease/");}
                                      //recognizer: TapGestureRecognizer()..onTap = () {launch} // link here, based on https://stackoverflow.com/questions/43583411/how-to-create-a-hyperlink-in-flutter-widget
                                    )
                                  ], "warning"),
                              builder: (context, snapshot) {
                                if (snapshot.hasData) {
                                  return snapshot.data ?? createBasicCard();
                                } else {
                                  return createBasicCard();
                                }
                              },
                            ),
                          ),
                          Visibility(
                            visible: notifiableStatus == 1,
                            child: FutureBuilder<Card>(
                              future: createDetailsCard(
                                  <TextSpan>[
                                    const TextSpan(text: "Warning! This appears to be a "),
                                    const TextSpan(text: "notifiable organism!", style: TextStyle(fontWeight: FontWeight.bold)),
                                    const TextSpan(text: "\n\n"),
                                    const TextSpan(text: "Notifiable organisms could seriously harm New Zealand's primary production or our "
                                        "trade and market access."),
                                    const TextSpan(text: "\n\n"),
                                    const TextSpan(text: "If the model's assessment seems reasonable, we strongly recommend reporting this "
                                        "organism by following the steps outlined by the Ministry of Primary Industries (MPI) "),
                                    TextSpan(
                                        text: "here.",
                                        style: const TextStyle(color: Colors.amber),
                                        recognizer: TapGestureRecognizer()..onTap = () { launchUrlString("https://www.mpi.govt.nz/biosecurity/how-to-find-report-and-prevent-pests-and-diseases/report-a-pest-or-disease/");}
                                      //recognizer: TapGestureRecognizer()..onTap = () {launch} // link here, based on https://stackoverflow.com/questions/43583411/how-to-create-a-hyperlink-in-flutter-widget
                                    ),
                                    const TextSpan(text: "\n\n"),
                                    const TextSpan(text: "Please note that if you spot a notifiable organism, you have a legal obligation to "
                                        "report it under the "),
                                    TextSpan(
                                        text: "Biosecurity Act 1993",
                                        style: const TextStyle(color: Colors.amber),
                                        recognizer: TapGestureRecognizer()..onTap = () { launchUrlString("https://www.legislation.govt.nz/act/public/1993/0095/latest/DLM314623.html");}
                                      //recognizer: TapGestureRecognizer()..onTap = () {launch} // link here, based on https://stackoverflow.com/questions/43583411/how-to-create-a-hyperlink-in-flutter-widget
                                    ),
                                    const TextSpan(text: " ("),
                                    TextSpan(
                                        text: "Section 44",
                                        style: const TextStyle(color: Colors.amber),
                                        recognizer: TapGestureRecognizer()..onTap = () { launchUrlString("https://www.legislation.govt.nz/act/public/1993/0095/latest/DLM315343.html");}
                                      //recognizer: TapGestureRecognizer()..onTap = () {launch} // link here, based on https://stackoverflow.com/questions/43583411/how-to-create-a-hyperlink-in-flutter-widget
                                    ),
                                    const TextSpan(text: " and "),
                                    TextSpan(
                                        text: "46",
                                        style: const TextStyle(color: Colors.amber),
                                        recognizer: TapGestureRecognizer()..onTap = () { launchUrlString("https://www.legislation.govt.nz/act/public/1993/0095/latest/DLM315349.html");}
                                      //recognizer: TapGestureRecognizer()..onTap = () {launch} // link here, based on https://stackoverflow.com/questions/43583411/how-to-create-a-hyperlink-in-flutter-widget
                                    ),
                                    const TextSpan(text: ").")
                                  ], "alert"),
                              builder: (context, snapshot) {
                                if (snapshot.hasData) {
                                  return snapshot.data ?? createBasicCard();
                                } else {
                                  return createBasicCard();
                                }
                              },
                            ),
                          ),
                          const SizedBox(height: 12),
                          CustomExpansionTile(
                            title: const Text("Top Five Predictions", style: TextStyle(fontWeight: FontWeight.bold)),
                            children: [
                              createTopFiveListTile(0),
                              createTopFiveListTile(1),
                              createTopFiveListTile(2),
                              createTopFiveListTile(3),
                              createTopFiveListTile(4),
                            ],
                          ),
                          /*const SizedBox(height: 12),
                          Text(
                            classificationResult.imagePath,
                            style: TextStyle(
                              color: Colors.grey[500],
                            ),
                          ),*/
                          const SizedBox(height: 12),
                          Text(
                            "This image was taken on ${DateFormat('yyyy-MM-dd - kk:mm').format(classificationResult.timestamp)}",
                            style: TextStyle(
                              color: Colors.grey[500],
                            ),
                          )
                        ],
                      ))
                    ],
                  ),
                ),
              ],
            )
        )
    );

  }
}

