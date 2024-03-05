use std::{collections::HashMap, env};

use rust_bert::pipelines::ner::Entity;
use serde::{Deserialize, Serialize};

use utoipa::ToSchema;

#[derive(Serialize, ToSchema)]
pub struct TextImagerCapability {
    // List of supported languages by the annotator
    // TODO how to handle language?
    // - ISO 639-1 (two letter codes) as default in meta data
    // - ISO 639-3 (three letters) optionally in extra meta to allow a finer mapping
    pub supported_languages: Vec<String>,
    // Are results on same inputs reproducible without side effects?
    pub reproducible: bool,
}

#[derive(Serialize, ToSchema)]
pub struct TextImagerDocumentation {
    // Name of this annotator
    pub annotator_name: String,

    // Version of this annotator
    pub version: String,

    // Annotator implementation language (Python, Java, ...)
    pub implementation_lang: Option<String>,

    // Optional map of additional meta data
    pub meta: Option<HashMap<String, String>>,

    // Docker container id, if any
    pub docker_container_id: Option<String>,

    // Optional map of supported parameters
    pub parameters: Option<HashMap<String, String>>,

    // Capabilities of this annotator
    pub capability: TextImagerCapability,

    // Analysis engine XML, if available
    pub implementation_specific: Option<String>,
}

impl Default for TextImagerDocumentation {
    fn default() -> Self {
        Self {
            annotator_name: env!("CARGO_PKG_NAME").into(),
            version: env!("CARGO_PKG_VERSION").into(),
            implementation_lang: Some(format!("Rust {}", env!("CARGO_PKG_RUST_VERSION"))),
            meta: None,
            docker_container_id: None,
            parameters: None,
            capability: TextImagerCapability {
                supported_languages: vec![],
                reproducible: true,
            },
            implementation_specific: None,
        }
    }
}

#[derive(Debug, Serialize, Deserialize, ToSchema)]
pub struct TextImagerRequest {
    pub text: String,
    pub language: String,
    pub sentences: Vec<SentenceOffsets>,
}

impl TextImagerRequest {
    pub fn sentences_and_offsets<'a>(&'a self) -> (Vec<String>, Vec<usize>) {
        self.sentences_with_offsets().unzip()
    }

    #[inline(always)]
    pub(crate) fn sentences_with_offsets<'a>(
        &'a self,
    ) -> impl Iterator<Item = (String, usize)> + 'a {
        let text = self.text.chars().collect::<Vec<char>>();
        self.sentences.iter().map(move |sentence| {
            (
                slice_vec_char_as_str(&text, sentence.begin, sentence.end),
                sentence.begin,
            )
        })
    }
}

fn slice_vec_char_as_str<'a>(text: &'a [char], begin: usize, end: usize) -> String {
    text[begin..end].iter().collect::<String>()
}

#[derive(Debug, Serialize, Deserialize, ToSchema)]
pub struct SentenceOffsets {
    pub begin: usize,
    pub end: usize,
}

#[derive(Debug, PartialEq, Serialize, Deserialize, ToSchema)]
pub struct TextImagerPrediction {
    pub label: String,
    pub begin: usize,
    pub end: usize,
}

impl TextImagerPrediction {
    pub fn new<T>(label: T, begin: usize, end: usize) -> Self
    where
        T: Into<String>,
    {
        Self {
            label: label.into(),
            begin,
            end,
        }
    }

    pub fn with_offset(mut self, offset: usize) -> Self {
        self.begin += offset;
        self.end += offset;
        self
    }
}

impl From<Entity> for TextImagerPrediction {
    fn from(entity: Entity) -> Self {
        let mut begin = entity.offset.begin as usize;
        let end = entity.offset.end as usize;

        let word = entity.word.as_str();
        if word.starts_with(char::is_whitespace) {
            let word_len = word.len();
            let stripped_word_len = word.trim_start().len();
            begin += word_len - stripped_word_len;
        }

        Self::new(entity.label, begin, end)
    }
}

#[derive(Debug, PartialEq, Serialize, Deserialize, Default, ToSchema)]
pub struct TextImagerResponse {
    pub predictions: Vec<TextImagerPrediction>,
    pub meta: Option<HashMap<String, String>>,
}

impl TextImagerResponse {
    pub fn new(
        predictions: Vec<TextImagerPrediction>,
        meta: Option<HashMap<String, String>>,
    ) -> Self {
        Self { predictions, meta }
    }
}