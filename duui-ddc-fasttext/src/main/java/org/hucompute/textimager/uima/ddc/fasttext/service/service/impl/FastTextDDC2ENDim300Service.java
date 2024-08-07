package org.hucompute.textimager.uima.ddc.fasttext.service.service.impl;

import io.quarkus.arc.Lock;
import org.hucompute.textimager.uima.ddc.fasttext.service.service.FastTextDDC2Service;

import javax.annotation.PreDestroy;
import javax.inject.Singleton;

@Lock
@Singleton
public class FastTextDDC2ENDim300Service extends FastTextDDC2Service {
    FastTextDDC2ENDim300Service() throws Exception {
        this(
                "",
                "",
                ""
        );
    }

    FastTextDDC2ENDim300Service(String disambigTag, String disambigLabelReplace, String disambigLabelReplaceWith) throws Exception {
        // TODO paths in container are absolute!
        // TODO WICHTIG die parameter weiter anpassen an die Daten aus der TI Config
        super(
                "/home/stud_homes/baumartz/mnt/resources/nlp/bin/categorization/fastText_modern_for_duui_annotators/fasttext",
                "en,/home/stud_homes/baumartz/mnt/resources/nlp/models/categorization/ddc/ddc_2023/wikipedia_en.v8.lemma.nopunct_gnd_ddc.v3.with_wikidata_dim300_lr0.2_lrur150_mincount5_epoch100.bin,95",
                true,
                1,
                true,
                false,
                "/home/stud_homes/baumartz/mnt/resources/nlp/models/categorization/am_posmap.txt",
                true,
                false,
                false, // TODO was true originally
                false,
                100,
                "ddc2;dim300;ddc_2023/wikipedia_en.v8.lemma.nopunct_gnd_ddc.v3.with_wikidata_dim300_lr0.2_lrur150_mincount5_epoch100.bin",
                disambigTag,
                disambigLabelReplace,
                disambigLabelReplaceWith
        );
    }

    @PreDestroy
    void preDestroy() {
        this.exit();
    }
}
