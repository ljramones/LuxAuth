# LeaData: a novel reference data of digital microscopic leather images for automatic species identification

[https://doi.org/10.5061/dryad.12jm63z6s](https://doi.org/10.5061/dryad.12jm63z6s)

### Anjli Varghese, Malathy Jawahar, A. Amalin Prince

## Description of the data and file structure

LeaData is a unique image data introduced to digital image processing (DIP) and computer vision fields to establish digitalization in leather technology. It is created to develop a smart identification technique that can quickly determine the animal species in leather without human intervention. This data thereby has a great impact on assisting the leather specialists, customs officials, and leather product manufacturers for quick and easy decision-making. Moreover, the outcome of this data can take part in maintaining biodiversity preservation and consumer protection.

The LeaData spans images of the leather surface background with species-distinct hair pore patterns. It captures the hair-pore behavior of the four most commonly used leather species: buffalo, cow, goat, and sheep. Although these patterns undergo vivid characteristics between species, different leather samples belong to different regions of location, breeds, ages, genders, different parts of the body, etc. Hence, for better species distinction, LeaData encloses leather images with diverse pore characteristics and groups them into different versions.

1. LeaData-V1: A small-scale version of LeaData with 1200 leather images of four species exhibiting ideal characteristics. The theoretical features of leather samples learned and surveyed over generations are termed as the ideal characteristics.  
2. LeaData-V2: A comparatively large-scale version of LeaData with 7600 leather images of four species exhibiting non-ideal characteristics. The leather images with pore features different from the ideal behavior are termed as the non-ideal characteristics. It is practically challenging to determine the animal species accurately from the leather images with non-ideal behavior.
3. LeaData-V3: A very large-scale version of LeaData with 10000 leather images with body part-specific characteristics. The pore features ideally posses varied distribution among different parts of the body which are called as the body part-specific characteristics. Learning from diverse pore behavior can enhance the image understanding for reliable decision-making.

Currently, the images in LeaData-V1 and LeaData-V2 are uploaded, meanwhile the images in LeaData-V3 will be uploaded in future.

##### The images in LeaData-V1 and LeaData-V2 can be used for research purposes and the authors must cite the database and related papers in their articles. Meanwhile, a written permission is required for any modifications or commercial work.&#x20;

### Files and variables

#### File: LeaData-V1.zip

**Description:** It is a small-scale data of leather images with ideal behavior. It consists of 1200 leather images grouped into four species. The main folder has four sub-folders: Buffalo, Cow, Goat, and Sheep, and each sub-folder has 300 leather images. The filename of each image in every folder starts with the first letter of the folder describing its species, followed by its body part, sample number, and image number. Also, the images are saved in JPG format with a .jpg extension.

For example, in the filename **BBTS1 (1).jpg**:

* **B** indicates the species **B**uffalo
* **BT** indicates the body part **B**u**T**t
* **S1** indicates the leather **S**ample number **1**
* **(1)** indicates image number **1** captured from sample S1
* **.jpg** indicates the **JPG** **format** in which the image is saved

###### The images of the butt region with ideal characteristics are selected and grouped under LeaData-V1. Hence, the image number may not be consistent.  

##### Researchers can use LeaData-V1 to apply different digital image processing and machine learning techniques to mathematically learn and quantify the ideal features of species' images.&#x20;

#### File: LeaData-V2.zip

**Description:** It is a large-scale data of leather images with non-ideal behavior. It consists of 7600 leather images grouped into four species. The main folder has four sub-folders: Buffalo, Cow, Goat, and Sheep, and each sub-folder has 1900 leather images. The filename of each image in every folder starts with the first letter of the folder describing its species, followed by its body part, sample number, and image number. Also, the images are saved in JPG format with a .jpg extension.

###### The images of the butt region with non-ideal characteristics are selected and grouped under LeaData-V2. Hence, the image number may not be consistent.  

##### Researchers can use LeaData-V2 to apply different digital image processing and machine learning techniques to mathematically learn and quantify the ideal features of species' images. Moreover, it is suitable to explore deep learning techniques to develop an automatic species identification model. Indeed, combining and learning from LeaData-V1 and LeaData-V2 can further enhance the species-specific pore description with diverse behavior for efficient species prediction. 
