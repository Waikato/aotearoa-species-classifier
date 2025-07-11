# Dataset Creation Pipeline

## Procedure
### 1. 01_inaturalist_api_retrieval.py
Retrieves every species available in the iNaturalist API along with metadata such as name, taxon rank, etc. 
(see iNat API data model ![[Refs]]) and stores everything in one large json file. Additional data files are extracted from this json file.


## Refs
### iNat API data model
---

#### `SpeciesCountsResponse`

* `total_results` (integer, optional)
* `page` (integer, optional)
* `per_page` (integer, optional)
* `results` (array of `SpeciesCountResult`)

---

##### `SpeciesCountResult` (Inline Model 1)

* `count` (integer, optional)
* `taxon` (`ShowTaxon`, optional)

---

#### `ShowTaxon`

* `id` (integer, optional)
* `iconic_taxon_id` (integer, optional)
* `iconic_taxon_name` (string, optional)
* `is_active` (boolean, optional)
* `name` (string, optional)
* `preferred_common_name` (string, optional)
* `rank` (string, optional)
* `rank_level` (number, optional)
* `ancestor_ids` (array of integers, optional)
* `colors` (array of `Color`, optional)
* `conservation_status` (`ConservationStatus`, optional)
* `conservation_statuses` (array of `TaxonConservationStatus`, optional)
* `default_photo` (`TaxonPhoto`, optional)
* `establishment_means` (`EstablishmentMeans`, optional)
* `observations_count` (integer, optional)
* `preferred_establishment_means` (string, optional)

---

#### `Color`

* `id` (integer, optional)
* `value` (string, optional)

---

#### `ConservationStatus`

* `place_id` (integer, optional)
* `place` (`CorePlace`, optional)
* `status` (string, optional)

---

#### `TaxonConservationStatus`

* `source_id` (integer, optional): Identifier for the iNat source record. [Link to source](https://www.inaturalist.org/sources/:id.json)
  *(Note: This endpoint is not part of the public API and may change or be removed)*
* `authority` (string, optional): Organization that declared this status
* `status` (string, optional): Often coded; refer to authority or status URL for details
* `status_name` (string, optional): Human-readable name of the status
* `iucn` (integer, optional): Coded IUCN status

  * Mappings:

    * `0`: NOT\_EVALUATED
    * `5`: DATA\_DEFICIENT
    * `10`: LEAST\_CONCERN
    * `20`: NEAR\_THREATENED
    * `30`: VULNERABLE
    * `40`: ENDANGERED
    * `50`: CRITICALLY\_ENDANGERED
    * `60`: EXTINCT\_IN\_THE\_WILD
    * `70`: EXTINCT
* `geoprivacy` (string, optional): Default geoprivacy in the given place
* `place` (`CorePlace`, optional)

---

#### `TaxonPhoto`

* `id` (integer, optional)
* `attribution` (string, optional)
* `license_code` (string, optional)
* `url` (string, optional)
* `medium_url` (string, optional)
* `square_url` (string, optional)

---

#### `EstablishmentMeans`

* `establishment_means` (string, optional)
* `place` (`CorePlace`, optional)

---

#### `CorePlace`

* `id` (integer, optional)
* `name` (string, optional)
* `display_name` (string, optional)

```json
SpeciesCountsResponse {
  total_results (integer, optional),
  page (integer, optional),
  per_page (integer, optional),
  results (Array[Inline Model 1])
}  

Inline Model 1 {
count (integer, optional),
taxon (ShowTaxon, optional)
}  

ShowTaxon {
id (integer, optional),
iconic_taxon_id (integer, optional),
iconic_taxon_name (string, optional),
is_active (boolean, optional),
name (string, optional),
preferred_common_name (string, optional),
rank (string, optional),
rank_level (number, optional),
ancestor_ids (Array[integer], optional),
colors (Array[Color], optional),
conservation_status (ConservationStatus, optional),
conservation_statuses (Array[TaxonConservationStatus], optional),
default_photo (TaxonPhoto, optional),
establishment_means (EstablishmentMeans, optional),
observations_count (integer, optional),
preferred_establishment_means (string, optional)
}  

Color {
id (integer, optional),
value (string, optional)
}  

ConservationStatus {
place_id (integer, optional),
place (CorePlace, optional),
status (string, optional)

}  

TaxonConservationStatus {

source_id (integer, optional):

Identifier for the iNat source record associated with this status, retrievable via [https://www.inaturalist.org/sources/:id.json](https://www.inaturalist.org/sources/:id.json) (this endpoint is not a part of our public API and is thus subject to change or removal)

,

authority (string, optional):

Organization that declared this status

,

status (string, optional):

Body of the status, often coded, particularly when the status comes from the IUCN or NatureServe. Consult the authority and/or the status URL for details about the meanings of codes.

,

status_name (string, optional):

Human-readable name of the status if it was coded.

,

iucn (integer, optional):

Coded value representing the equivalent IUCN status. Mappings: NOT_EVALUATED = 0, DATA_DEFICIENT = 5, LEAST_CONCERN = 10, NEAR_THREATENED = 20, VULNERABLE = 30, ENDANGERED = 40, CRITICALLY_ENDANGERED = 50, EXTINCT_IN_THE_WILD = 60, EXTINCT = 70

,

geoprivacy (string, optional):

Default geoprivacy for observations of this taxon in the status's place.

,

place (CorePlace, optional)

}  

TaxonPhoto {

id (integer, optional),

attribution (string, optional),

license_code (string, optional),

url (string, optional),

medium_url (string, optional),

square_url (string, optional)

}  

EstablishmentMeans {

establishment_means (string, optional),

place (CorePlace, optional)

}  

CorePlace {

id (integer, optional),

name (string, optional),

display_name (string, optional)

}
```