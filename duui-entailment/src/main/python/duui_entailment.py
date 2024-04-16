from pydantic import BaseModel
from pydantic_settings import BaseSettings
from typing import List, Optional, Dict, Union, Any
import logging
from time import time
from fastapi import FastAPI, Response
from cassis import load_typesystem
import torch
from threading import Lock
from functools import lru_cache
from entailment_check import EntailmentCheck, ChatGPT
# from sp_correction import SentenceBestPrediction

# Settings
# These are automatically loaded from env variables
from starlette.responses import PlainTextResponse

model_lock = Lock()


labels_to_name = {
    0: "Non-Entailment",
    1: "Entailment",
}

class UimaSentence(BaseModel):
    text: str
    begin: int
    end: int


class UimaSentenceSelection(BaseModel):
    selection: str
    sentences: List[UimaSentence]


class Settings(BaseSettings):
    # Name of this annotator
    annotator_name: str
    # Version of this annotator
    annotator_version: str
    # Log level
    log_level: str
    model_name: str
    model_version: str
    model_url: str
    model_lang: str
    # model_name: str
    # Name of this annotator
    model_cache_size: int
    chatgpt_key: str


# Load settings from env vars
settings = Settings()
lru_cache_with_size = lru_cache(maxsize=settings.model_cache_size)
logging.basicConfig(level=settings.log_level)
logger = logging.getLogger(__name__)

device = 0 if torch.cuda.is_available() else "cpu"
logger.info(f'USING {device}')
# Load the predefined typesystem that is needed for this annotator to work
typesystem_filename = 'TypeSystemEntailment.xml'
logger.debug("Loading typesystem from \"%s\"", typesystem_filename)
with open(typesystem_filename, 'rb') as f:
    typesystem = load_typesystem(f)
    logger.debug("Base typesystem:")
    logger.debug(typesystem.to_xml())

# Load the Lua communication script
lua_communication_script_filename = "duui_entailment.lua"
logger.debug("Loading Lua communication script from \"%s\"", lua_communication_script_filename)


# Request sent by DUUI
# Note, this is transformed by the Lua script
class TextImagerRequest(BaseModel):
    entailments: List[dict]
    #
    chatgpt_key: Optional[Any]


# UIMA type: mark modification of the document
class DocumentModification(BaseModel):
    user: str
    timestamp: int
    comment: str


# UIMA type: adds metadata to each annotation
class AnnotationMeta(BaseModel):
    name: str
    version: str
    modelName: str
    modelVersion: str


# Response sent by DUUI
# Note, this is transformed by the Lua script
class TextImagerResponse(BaseModel):
    # Symspelloutput
    # List of Sentence with every token
    # Every token is a dictionary with following Infos:
    # Symspelloutput right if the token is correct, wrong if the token is incorrect, skipped if the token was skipped, unkownn if token can corrected with Symspell
    # If token is unkown it will be predicted with BERT Three output pos:
    # 1. Best Prediction with BERT MASKED
    # 2. Best Cos-sim with Sentence-Bert and with perdicted words of BERT MASK
    # 3. Option 1 and 2 together
    meta: AnnotationMeta
    # Modification meta, one per document
    modification_meta: DocumentModification
    predictions: List[Dict[str, Union[str, float]]]
    model_name: str
    model_version: str
    model_source: str
    model_lang: str


app = FastAPI(
    openapi_url="/openapi.json",
    docs_url="/api",
    redoc_url=None,
    title=settings.annotator_name,
    description="Factuality annotator",
    version=settings.annotator_version,
    terms_of_service="https://www.texttechnologylab.org/legal_notice/",
    contact={
        "name": "TTLab Team",
        "url": "https://texttechnologylab.org",
        "email": "bagci@em.uni-frankfurt.de",
    },
    license_info={
        "name": "AGPL",
        "url": "http://www.gnu.org/licenses/agpl-3.0.en.html",
    },
)

with open(lua_communication_script_filename, 'rb') as f:
    lua_communication_script = f.read().decode("utf-8")
logger.debug("Lua communication script:")
logger.debug(lua_communication_script_filename)


# Get typesystem of this annotator
@app.get("/v1/typesystem")
def get_typesystem() -> Response:
    # TODO remove cassis dependency, as only needed for typesystem at the moment?
    xml = typesystem.to_xml()
    xml_content = xml.encode("utf-8")

    return Response(
        content=xml_content,
        media_type="application/xml"
    )


# Return Lua communication script
@app.get("/v1/communication_layer", response_class=PlainTextResponse)
def get_communication_layer() -> str:
    return lua_communication_script


# Return documentation info
@app.get("/v1/documentation")
def get_documentation():
    return "Test"


@lru_cache_with_size
def load_model(model_name, chatgpt_key=""):
    model_i = None
    match model_name:
        case "gpt4":
            model_i = ChatGPT("gpt-4", chatgpt_key)
        case  "gpt3.5":
            model_i = ChatGPT("gpt-3.5-turbo", chatgpt_key)
        case _:
            model_i = EntailmentCheck(model_name, device)
    return model_i

model = load_model(settings.model_name, settings.chatgpt_key)


def fix_unicode_problems(text):
    # fix emoji in python string and prevent json error on response
    # File "/usr/local/lib/python3.8/site-packages/starlette/responses.py", line 190, in render
    # UnicodeEncodeError: 'utf-8' codec can't encode characters in position xx-yy: surrogates not allowed
    clean_text = text.encode('utf-16', 'surrogatepass').decode('utf-16', 'surrogateescape')
    return clean_text


def process_selection(entailments, model_i: Union[EntailmentCheck, ChatGPT]):
    output = []
    premises = []
    hypothesis = []
    for entailment in entailments:
        premises.append(entailment["premise"])
        hypothesis.append(entailment["hypothesis"])
    chunks = 50
    premises = [premises[i * chunks:(i + 1) * chunks] for i in range((len(premises) + chunks - 1) // chunks )]
    hypothesis = [hypothesis[i * chunks:(i + 1) * chunks] for i in range((len(hypothesis) + chunks - 1) // chunks )]
    for c, premise in enumerate(premises):
        output_c = model_i.entailment_check(premise, hypothesis[c])
        if settings.model_name == "gpt4" or settings.model_name == "gpt3.5":
            for pred in output_c:
                dict_i = {}
                label = pred["label"]
                dict_i["label"] = labels_to_name[label]
                if "confidence" in pred:
                    dict_i["confidence"] = pred["confidence"]
                else:
                    dict_i["confidence"] = 1
                if "reason" in pred:
                    dict_i["reason"] = pred["reason"]
                else:
                    dict_i["reason"] = ""
                output.append(dict_i)
        else:
            output += output_c

    return output


# Process request from DUUI
@app.post("/v1/process")
def post_process(request: TextImagerRequest):
    # Return data
    meta = None
    begin = []
    end = []
    len_results = []
    results = []
    factors = []
    # Save modification start time for later
    modification_timestamp_seconds = int(time())
    chatgpt_key = ""
    if isinstance(chatgpt_key, str):
        chatgpt_key = request.chatgpt_key
    try:
        model_source = settings.model_url
        model_version = settings.model_version
        model_lang = settings.model_lang
        # set meta Informations
        meta = AnnotationMeta(
            name=settings.annotator_name,
            version=settings.annotator_version,
            modelName=settings.model_name,
            modelVersion=model_version,
        )
        # Add modification info
        modification_meta_comment = f"{settings.annotator_name} ({settings.annotator_version}))"
        modification_meta = DocumentModification(
            user=settings.annotator_name,
            timestamp=modification_timestamp_seconds,
            comment=modification_meta_comment
        )
        mv = ""
        if settings.model_name == "gpt4" or settings.model_name == "gpt3.5":
            model_i = load_model(settings.model_name, chatgpt_key)
        else:
            model_i = model
        outputs = process_selection(request.entailments, model_i)
    except Exception as ex:
        logger.exception(ex)
    return TextImagerResponse(meta=meta, modification_meta=modification_meta, predictions=outputs, model_name=settings.model_name, model_version=model_version, model_source=model_source, model_lang=model_lang)
