# Aotearoa Species Classifier
Aotearoa species classifier and the corresponding apps:
* [what-is-this.cms.waikato.ac.nz](https://what-is-this.cms.waikato.ac.nz/)
* [Google Play](https://play.google.com/store/apps/details?id=com.waikatolink.wit_app)
* [Apple App Store](https://apps.apple.com/nz/app/aotearoa-species-classifier/id1633570014)

## License

The iNaturalist data used for training the models was released under the following licenses:
* CC0
* CC-BY
* CC-BY-NC

There is, of course, the ImageNet issue:

**Pretrained Weights**

So far all of the pretrained weights available here are pretrained on ImageNet with a select few that have some additional pretraining (see extra note below). ImageNet was released for non-commercial research purposes only (https://image-net.org/download). It's not clear what the implications of that are for the use of pretrained weights from that dataset. Any models I have trained with ImageNet are done for research purposes and one should assume that the original dataset license applies to the weights. It's best to seek legal advice if you intend to use the pretrained weights in a commercial product.

Source: https://github.com/huggingface/pytorch-image-models#licenses
