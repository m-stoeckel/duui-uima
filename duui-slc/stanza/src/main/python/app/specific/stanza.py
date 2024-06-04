import logging
from typing import Self

import stanza
from app.abc import ModelProxyABC, ProcessorABC, SentenceValidatorABC
from app.model import DuuiRequest, DuuiResponse, Offset, UimaDependency, UimaToken
from app.utils import EOS_MARKERS, TokenToId
from stanza import Pipeline
from stanza.models.common.doc import Document, Sentence, Token, Word
from stanza.pipeline.core import DownloadMethod

logger = logging.getLogger(__name__)

model_map = {
    "en": "en",
    "en_US": "en",
    "en_GB": "en",
    "en_AU": "en",
    "en_CA": "en",
    "de": "de",
    "de_DE": "de",
    "de_AT": "de",
    "de_CH": "de",
}


class StanzaModelProxy(ModelProxyABC[Pipeline]):
    def __init__(self):
        self.models = {}

    def __getitem__(self, lang: str):
        lang = model_map.get(lang.replace("-", "_"), lang)
        if self.models.get(lang) is None:
            logger.info(f"load({lang})")
            nlp = stanza.Pipeline(
                lang=lang,
                processors="tokenize,mwt,pos,lemma,depparse",
                tokenize_no_ssplit=True,
                download_method=DownloadMethod.REUSE_RESOURCES,
            )
            self.models[lang] = nlp
            logger.info(f"load({lang}): done")
        return self.models[lang]


class StanzaSentenceValidator(SentenceValidatorABC[Sentence]):
    @classmethod
    def check(cls, sentence: Sentence):
        if not sentence.text.strip()[0].isupper():
            return cls(False)
        if sentence.text.strip()[-1] not in EOS_MARKERS:
            return cls(True, False)
        words: list[Word] = sentence.words
        if not any((word.upos == "VERB" or word.upos == "AUX" for word in words)):
            return cls(True, True, False)
        if sentence.text.count('"') % 2 != 0:
            return cls(True, True, True, False)
        if sentence.text.count("(") != sentence.text.count(")"):
            return cls(True, True, True, True, False)
        return cls(True, True, True, True, True)


class StanzaProcessor(ProcessorABC[Document]):
    def __init__(self, proxy: StanzaModelProxy) -> None:
        super().__init__()
        self.proxy = proxy

    @classmethod
    def with_proxy(cls, proxy: ModelProxyABC) -> Self:
        return cls(proxy)

    def process(self, request: DuuiRequest):
        if request.sentences is None:
            raise ValueError("Sentences offsets are required for Stanza")

        nlp = self.proxy[request.language]

        annotations = []
        offsets = request.sentences
        for offset in offsets:
            annotations.append(nlp(request.text[offset.begin : offset.end]))

        return self.post_process(
            annotations,
            offsets,
        )

    @staticmethod
    def post_process(annotations: list[Document], offsets: list[Offset]):
        word_to_id = TokenToId()
        results = DuuiResponse(sentences=None, tokens=[], dependencies=[])
        for doc, offset in zip(annotations, offsets):
            logger.info(doc)  # TODO: Remove this line

            # Add a None to the end of the iterator to include the last sentence if it ends with a semicolon.
            for sentence in doc.sentences:
                if not bool(StanzaSentenceValidator.check(sentence).is_standalone()):
                    continue

                tokens: list[Token] = sentence.tokens
                for token in tokens:
                    # intra_token_offset = 0
                    # token_len = len(token.text)
                    words: list[Word] = token.words
                    for word in words:
                        try:
                            word_idx = word_to_id.add(word)

                            begin = word.start_char + offset.begin
                            end = begin + len(word.text)
                            results.tokens.append(
                                UimaToken(
                                    begin=begin,
                                    end=end,
                                    pos=word.upos,
                                    tag=word.xpos,
                                    lemma=word.lemma,
                                    morph=(
                                        {
                                            k.lower(): v
                                            for k, v in (
                                                feat.split("=")
                                                for feat in word.feats.split("|")
                                                if "=" in feat
                                            )
                                        }
                                        if word.feats
                                        else None
                                    ),
                                    idx=word_idx,
                                )
                            )
                        except Exception as e:
                            logger.error(
                                f"Error processing word:  \n{word}\n"
                                f"in sentence: \n{sentence}"
                            )
                            raise e

                for token in tokens:
                    words: list[Word] = token.words
                    for word in words:
                        begin = word.start_char + offset.begin
                        end = begin + len(word.text)
                        results.dependencies.append(
                            UimaDependency(
                                begin=begin,
                                end=end,
                                governor=word_to_id[sentence.words[word.head]],
                                dependent=word_to_id[word],
                                type=word.deprel.upper(),
                                flavor="basic",
                            )
                        )

        return results
