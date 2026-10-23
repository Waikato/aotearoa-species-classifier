# Aotearoa Species Classifier

A species classifier for Aotearoa New Zealand and the corresponding applications:

* [Web classifier](https://what-is-this.cms.waikato.ac.nz/)
* [Google Play](https://play.google.com/store/apps/details?id=nz.ac.waikato.cms.ml.wit_app)
* [Apple App Store](https://apps.apple.com/nz/app/aotearoa-species-classifier/id6806519964)

## Licence

The iNaturalist images used to train the model were made available under the following licences:

* CC0
* CC BY
* CC BY-NC

The Aotearoa Species Classifier model weights are licensed under the [Creative Commons Attribution-NonCommercial 4.0 International licence (CC BY-NC 4.0)](https://creativecommons.org/licenses/by-nc/4.0/).

The classifier was initialised from the [`timm/tf_efficientnetv2_s.in21k`](https://huggingface.co/timm/tf_efficientnetv2_s.in21k) checkpoint, which is distributed under the [Apache License 2.0](https://www.apache.apache.org/licenses/LICENSE-2.0). The Apache-2.0 licence and applicable upstream notices continue to apply to that component.

The training images are not covered by the model licence and remain subject to their respective licences.
