# -*- coding: utf-8 -*-
# Generated by Django 1.10.5 on 2017-01-31 03:16
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('observations', '0064_auto_20170123_1142'),
    ]

    operations = [
        migrations.AlterField(
            model_name='animalencounter',
            name='species',
            field=models.CharField(choices=[('na', 'not observed'), ('Natator depressus', 'Natator depressus (Flatback turtle)'), ('Chelonia mydas', 'Chelonia mydas (Green turtle)'), ('Eretmochelys imbricata', 'Eretmochelys imbricata (Hawksbill turtle)'), ('Caretta caretta', 'Caretta caretta (Loggerhead turtle)'), ('Lepidochelys olivacea', 'Lepidochelys olivacea (Olive ridley turtle)'), ('Dermochelys coriacea', 'Dermochelys coriacea (Leatherback turtle)'), ('Chelonia mydas agassazzi', 'Chelonia mydas agassazzi (Black turtle or East Pacific Green)'), ('Corolla corolla', 'Corolla corolla (Hatchback turtle)'), ('Cheloniidae fam.', 'Cheloniidae (Unidentified turtle)'), ('Delphinus delphis', 'Delphinus delphis (Short-beaked common dolphin)'), ('Grampus griseus', "Grampus griseus (Risso's dolphin)"), ('Lagenodelphis hosei', "Lagenodelphis hosei (Fraser's dolphin)"), ('Lagenorhynchus obscurus', 'Lagenorhynchus obscurus (Dusky dolphin)'), ('Orcaella heinsohni', 'Orcaella heinsohni (Australian snubfin dolphin)'), ('Sousa sahulensis', 'Sousa sahulensis (Australian humpback dolphin)'), ('Stenella attenuata', 'Stenella attenuata (Pantropical spotted dolphin)'), ('Stenella coeruleoalba', 'Stenella coeruleoalba (Striped dolphin)'), ('Stenella longirostris', 'Stenella longirostris (Spinner dolphin)'), ('Stenella sp.', 'Stenella sp. (Unidentified spotted dolphin)'), ('Steno bredanensis', 'Steno bredanensis (Rough-toothed dolphin)'), ('Tursiops aduncus', 'Tursiops aduncus (Indo-Pacific bottlenose dolphin)'), ('Tursiops truncatus', 'Tursiops truncatus (Offshore bottlenose dolphin)'), ('Tursiops sp.', 'Tursiops sp. (Unidentified bottlenose dolphin)'), ('unidentified-dolphin', 'Unidentified dolphin'), ('Balaenoptera acutorostrata', 'Balaenoptera acutorostrata (Dwarf minke whale)'), ('Balaenoptera bonaerensis', 'Balaenoptera bonaerensis (Antarctic minke whale)<'), ('Balaenoptera borealis', 'Balaenoptera borealis (Sei whale)'), ('Balaenoptera edeni', "Balaenoptera edeni (Bryde's whale)"), ('Balaenoptera musculus', 'Balaenoptera musculus (Blue whale)'), ('Balaenoptera musculus brevicauda', 'Balaenoptera musculus brevicauda (Pygmy blue whale)'), ('Balaenoptera physalus', 'Balaenoptera physalus (Fin whale)'), ('Balaenoptera sp.', 'Balaenoptera sp. (Unidentified Balaenoptera)'), ('Eubalaena australis', 'Eubalaena australis (Southern right whale)'), ('Feresa attenuata', 'Feresa attenuata (Pygmy killer whale)'), ('Globicephala macrorhynchus', 'Globicephala macrorhynchus (Short-finned pilot whale)'), ('Globicephala melas', 'Globicephala melas (Long-finned pilot whale)'), ('Globicephala sp.', 'Globicephala sp. (Unidentified pilot whale)'), ('Indopacetus pacificus', "Indopacetus pacificus (Longman's beaked whale)"), ('Kogia breviceps', 'Kogia breviceps (Pygmy sperm whale)'), ('Kogia sima', 'Kogia sima (Dwarf sperm whale)'), ('Kogia sp.', 'Kogia sp. (Unidentified small sperm whale)'), ('Megaptera novaeangliae', 'Megaptera novaeangliae (Humpback whale)'), ('Mesoplodon densirostris', "Mesoplodon densirostris (Blainville's beaked whale)"), ('Mesoplodon layardii', 'Mesoplodon layardii (Strap-toothed whale)'), ('Mesoplodon sp.', 'Mesoplodon sp. (Beaked whale)'), ('Orcinus orca', 'Orcinus orca (Killer whale)'), ('Peponocephala electra', 'Peponocephala electra (Melon-headed whale)'), ('Physeter macrocephalus', 'Physeter macrocephalus (Sperm whale)'), ('Pseudorca crassidens', 'Pseudorca crassidens (False killer whale)'), ('Ziphius cavirostris', "Ziphius cavirostris (Cuvier's beaked whale)"), ('unidentified-whale', 'Unidentified whale'), ('hydrophiinae-subfam', 'Hydrophiinae subfam. (Sea snakes and kraits)'), ('acalyptophis-sp', 'Acalyptophis sp. (Horned sea snake)'), ('aipysurus-sp', 'Aipysurus sp. (Olive sea snake)'), ('astrotia-sp', "Astrotia sp. (Stokes' sea snake)"), ('emydocephalus-sp', 'Emydocephalus sp. (Turtlehead sea snake)'), ('enhydrina-sp', 'Enhydrina sp. (Beaked sea snake)'), ('ephalophis-sp', "Ephalophis sp. (Grey's mudsnake)"), ('hydrelaps-sp', 'Hydrelaps sp. (Port Darwin mudsnake)'), ('hydrophis-sp', 'Hydrophis sp. (sea snake)'), ('kerilia-sp', "Kerilia sp. (Jerdon's sea snake)"), ('kolpophis-sp', 'Kolpophis sp. (bighead sea snake)'), ('lapemis-sp', "Lapemis sp. (Shaw's sea snake)"), ('laticauda-sp', 'Laticauda sp. (Sea krait)'), ('parahydrophis-sp', 'Parahydrophis (Northern mangrove sea snake)'), ('parapistocalamus-sp', "Parapistocalamus sp. (Hediger's snake)"), ('pelamis-sp', 'Pelamis sp. (Yellow-bellied sea snake)'), ('praescutata-sp', 'Praescutata sp. (Sea snake)'), ('thalassophis-sp', 'Thalassophis sp. (Sea snake)'), ('dugong-dugon', 'Dugong dugon (Dugong)')], default='unidentified', help_text='The species of the animal.', max_length=300, verbose_name='Species'),
        ),
    ]
