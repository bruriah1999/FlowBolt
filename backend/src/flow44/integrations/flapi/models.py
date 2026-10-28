# Mirrors mocks/flapi-mock/schemas.ts. Contract tests in
# tests/integrations/flapi/test_models_contract.py guard against drift.
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, RootModel, field_validator
from pydantic.alias_generators import to_camel, to_pascal

# Wire vocabulary — authoritative per FLAPI. Quick-params types are
# PascalCase; schema field types are lowercase with a few legacy tags.
ParamType = Literal["String", "Int", "Double", "Boolean", "Datetime", "Timestamp", "Haphoch", "File"] | str
FieldType = (
    Literal[
        "string",
        "datetime",
        "boolean",
        "int",
        "double",
        "float",
        "geojson",
        "wkt",
        "geoellipse",
        "object",
        # Non standard but existant types:
        "bool",
        "date",
        "haphoch",
        "decimal",
        "dynamic",
        "number",
        "html",
        "range",
        "boundingrectangle",
        "spatial",
        "relative",
        "long",
        "time",
        "text",
        "date",
        "pid",
        "",
    ]
    | str
)
# OntologyType = Literal["TEXT", "LOCATION", "ENTITY_ID", "CONTACT_INFO", "DEVICE_ID", "TIMESTAMP"]

type CubeId = str
type QueryDisplayName = str


class PascalCaseBaseModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_pascal,
        populate_by_name=True,
    )


# -- Search: GET /package/v1/search/{query} ------------------------------


class PackageSearchResult(PascalCaseBaseModel):
    # Trailing underscore avoids shadowing the `id`/`type` builtins.
    id_: int = Field(alias="Id")
    name: str
    type_: Literal["Package"] = Field(default="Package", alias="Type")
    purpose: str | None = None
    description: str | None = ""


# -- Run: POST /package/v3/{id} ------------------------------------------


class _OptionValueItem(BaseModel):
    Name: str | None
    Value: int | float | str | None = None


class _GeoOptionValueItem(BaseModel):
    Name: str | None
    Type: str
    Value: Any


class _DateRangeValue(BaseModel):
    From: str
    To: str


class _TimebackValue(BaseModel):
    TimeBackValue: int | float
    TimeBackUnit: Literal["second", "minute", "hour", "day", "week", "month", "year"]


class _TimestampRelative(BaseModel):
    Unit: Literal["seconds", "minutes", "hours", "days", "weeks", "months", "years"]
    Value: int
    Direction: Literal["before", "after"]


class _GeographicValueItem(BaseModel):
    value: str | list[str]
    radius: float | None = None


type QuickParamScalar = str | int | float | bool

type _TimestampValue = datetime | Literal["now"] | _TimestampRelative

type QuickParamValue = (
    _OptionValueItem
    | list[_OptionValueItem]
    | _DateRangeValue
    | list[_DateRangeValue]
    | _TimebackValue
    | list[_TimebackValue]
    | _GeographicValueItem
    | list[_GeographicValueItem]
    | _GeoOptionValueItem
    | list[_GeoOptionValueItem]
    | _TimestampValue
    | list[_TimestampValue]
    | QuickParamScalar
    | list[QuickParamScalar]
)


class QuickParams(RootModel[dict[CubeId, dict[str, QuickParamValue]]]):
    pass


class DataSourceRunResult(BaseModel):
    results: dict[QueryDisplayName, Any]


# -- Quick params info: GET /package/v1/quick/{id} -----------------------


class QuickParameterInfo(PascalCaseBaseModel):
    display_name: str | None = None
    description: str | None = None


class QuickParamDefinition(PascalCaseBaseModel):
    name: str
    display_name: str
    description: str | None = None
    type_: ParamType = Field(alias="Type")
    # ontology_type: OntologyType
    is_single_value: bool
    is_required: bool
    is_require_any: bool = False
    value: QuickParamValue | None = None
    quick_parameter_info: QuickParameterInfo | None = Field(default=None, alias="quickParameterInfo")

    @field_validator("type_", mode="before")
    def _normalize_type(cls, v: object) -> object:
        return v.capitalize() if isinstance(v, str) else v


class QuickParamsInfo(RootModel[dict[CubeId, list[QuickParamDefinition]]]):
    pass


# -- Package metadata: GET /package/v3/{id} ------------------------------


# class FieldAttributes(PascalCaseBaseModel):
#     ontology_type: OntologyType | None = None
#     original_ontology_type: OntologyType | None = None
#
#     @field_validator("ontology_type", "original_ontology_type", mode="before")
#     def _normalize_ontology_type(cls, v: object) -> object:
#         return v.upper() if isinstance(v, str) else v


class QueryField(PascalCaseBaseModel):
    name: str
    display_name: str
    type_: FieldType = Field(alias="Type")
    is_dynamic: bool | None = None
    # attributes: FieldAttributes = Field(default_factory=FieldAttributes)
    description: str | None = None

    @field_validator("type_", mode="before")
    def _normalize_type(cls, v: object) -> object:
        return v.lower() if isinstance(v, str) else v


class Query(PascalCaseBaseModel):
    # uniqueName/originalName are camelCase on the wire, not PascalCase.
    unique_name: str = Field(alias="uniqueName")
    original_name: str = Field(alias="originalName")
    name: str
    results_limit: int
    data_source_name: str
    description: str
    id_: str = Field(alias="id")
    fields: list[QueryField]


class PackageMetadata(PascalCaseBaseModel):
    id_: int = Field(alias="Id")
    name: str
    description: str | None = None
    # output_queries_id: list[Any]
    queries: list[Query]


# -- Cubes: /cube/v1/{cubeName} -------------------------------------------
#
# Cubes are addressed by name and speak camelCase. Each cube's supplier can
# add its own keys, so every model allows extras; only what we read is typed.


class CamelCaseBaseModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        extra="allow",
    )


class CubeSpan(BaseModel):
    start: int = 0
    end: int = 0


class CubeValueItem(CamelCaseBaseModel):
    value: str
    raw_value: str
    ontology: str
    span: CubeSpan = Field(default_factory=CubeSpan)
    optional_ontologies: list[Any] = Field(default_factory=list)
    enrichments: list[Any] = Field(default_factory=list)
    domains: list[Any] = Field(default_factory=list)


class CubeParameter(CamelCaseBaseModel):
    """A free-value parameter; its type is implied by `ontology`."""

    key: str
    display_name: str
    ontology: str | None = None
    value: list[CubeValueItem] | None = None


class CubeDynamicParameter(CamelCaseBaseModel):
    """A pick-from-options parameter; `values_display_name` maps value -> label."""

    is_single_value: bool = False
    key_display_name: str
    values_display_name: dict[str, str] = Field(default_factory=dict)
    value: list[str] | str | None = None


class CubeField(CamelCaseBaseModel):
    key: str
    header: str
    data_type: str
    ontology_type: str | None = None


class CubeTriangle(BaseModel):
    model_config = ConfigDict(extra="allow")
    Id: int
    Clearance: int


# GET /cube/v1/{cubeName} — a.k.a. CubeExecutionPayload.
class CubeStructure(CamelCaseBaseModel):
    # `_id` would be a private attribute in pydantic; keep it under an alias.
    mongo_id: str | None = Field(default=None, alias="_id")
    created_time: dict[str, Any] | None = None
    cube_name: str
    cube_display_name: str | None = None
    cube_description: str | None = None
    cube_owner: str | None = None
    cube_icon: str | None = None
    cube_columns_api: list[str] | str | None = None
    fields: list[CubeField] = Field(default_factory=list)
    parameters: list[CubeParameter] = Field(default_factory=list)
    dynamic_parameters: dict[str, CubeDynamicParameter] = Field(default_factory=dict)
    static_parameters: dict[str, Any] | None = None
    execution_parameters: dict[str, Any] | None = None
    is_authorized: bool | None = None
    triangles: list[CubeTriangle] | None = None


# GET /cube/v1/{cubeName}/parameters — one entry per parameter.
class CubeParameterInfo(CamelCaseBaseModel):
    key: str
    display_name: str | None = None
    is_required: bool = False
    is_visible: bool = True


# POST /cube/v1/{cubeName} — one JSON object per table row.
class CubeRunResult(RootModel[list[dict[str, Any]]]):
    pass
