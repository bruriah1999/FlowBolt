import asyncio
import logging
from typing import Any, Literal

from pydantic import ValidationError

from flow44.config import settings
from flow44.integrations.flapi import (
    FlapiUpstreamError,
    QuickParams,
    data_source_client,
)
from flow44.integrations.flapi import models as flapi_models
from flow44.integrations.flapi.models import QuickParamValue
from flow44.logic.models import (
    CubeSchema,
    DataSource,
    DataSourceFieldSchema,
    DataSourceParamsInfo,
    DataSourceQuerySchema,
    DataSourceResult,
    DataSourceUsage,
    FieldType,
    ParamDefinition,
    ParamOption,
    ParamType,
    QuickParamInfo,
    parse_param_value,
)

logger = logging.getLogger(__name__)

__all__ = [
    "DataSource",
    "DataSourceParamsInfo",
    "DataSourceResult",
    "DataSourceUsage",
    "FlapiUpstreamError",
    "can_run_without_params",
    "cube_data_source_id",
    "get_display_name",
    "get_params_info",
    "get_usage",
    "list_cubes",
    "parse_data_source_id",
    "run_data_source",
    "search_data_sources",
    "storage_type",
]


# -- Data source ids -----------------------------------------------------

# Packages are addressed by numeric id, cubes by name. A cube's data source
# id carries a prefix so the bare id string still says which FLAPI API to
# call — it travels unchanged through the chat, agents, DB rows and the
# generated `/api/data-source/{id}/run` calls.
CUBE_ID_PREFIX = "cube:"

type DataSourceKind = Literal["package", "cube"]


def cube_data_source_id(cube_name: str) -> str:
    return f"{CUBE_ID_PREFIX}{cube_name}"


def parse_data_source_id(data_source_id: str | int) -> tuple[DataSourceKind, str]:
    raw = str(data_source_id).strip()
    if raw.startswith(CUBE_ID_PREFIX):
        return "cube", raw.removeprefix(CUBE_ID_PREFIX)
    return "package", raw


def storage_type(data_source_id: str | int) -> str:
    """The `type` column value for a data source in `project_data_sources`."""
    kind, _ = parse_data_source_id(data_source_id)
    return "flow_cube" if kind == "cube" else "flow_package"


# -- FLAPI -> domain conversions -----------------------------------------

# FLAPI speaks its own vocabulary (PascalCase quick-param types, a wider
# lowercase-plus-legacy field-type set). The rest of the app doesn't care —
# these two mappers are the single seam that translates into the narrow
# domain Literals. Keep them exhaustive; unmapped values fall back to
# "string" so the UI still renders, but should be reported and added.
_FLAPI_PARAM_TYPE: dict[flapi_models.ParamType, ParamType] = {
    "String": "string",
    "Int": "int",
    "Double": "double",
    "Boolean": "bool",
    "Datetime": "datetime",
    "Timestamp": "timestamp",
    "Haphoch": "geographic",
    "File": "string",
}

_FLAPI_FIELD_TYPE: dict[flapi_models.FieldType, FieldType] = {
    "string": "string",
    "int": "int",
    "double": "double",
    "float": "double",
    "decimal": "double",
    "bool": "bool",
    "boolean": "bool",
    "date": "datetime",
    "datetime": "datetime",
    "wkt": "wkt",
    # The following types are not specifically handled by the UI, but could at least be printed.
    "geojson": "string",
    "geoellipse": "string",
    "haphoch": "string",
    "object": "string",
    "dynamic": "string",
}


def _to_domain_field_type(t: flapi_models.FieldType) -> FieldType:
    mapped = _FLAPI_FIELD_TYPE.get(t)
    if mapped is None:
        logger.warning("Unmapped FLAPI field type %r — falling back to 'string'", t)
        return "string"
    return mapped


def _to_data_source(result: flapi_models.PackageSearchResult) -> DataSource:
    return DataSource(
        id=result.id_,
        name=result.name,
        description=result.description or None,
    )


def _to_params_info(info: flapi_models.QuickParamsInfo) -> DataSourceParamsInfo:
    parameters: list[ParamDefinition] = []
    require_any = False

    for cube_id, param_list in info.root.items():
        for p in param_list:
            options = [
                ParamOption(name=n, value=str(v))
                for item in (p.value if isinstance(p.value, list) else [p.value] if p.value is not None else [])
                if isinstance(n := getattr(item, "Name", None), str) and (v := getattr(item, "Value", None)) is not None
            ]
            parameters.append(
                ParamDefinition(
                    name=p.name,
                    display_name=p.display_name,
                    description=p.description,
                    quick_info=(
                        QuickParamInfo(
                            display_name=p.quick_parameter_info.display_name,
                            description=p.quick_parameter_info.description,
                        )
                        if p.quick_parameter_info
                        else None
                    ),
                    type=_FLAPI_PARAM_TYPE.get(p.type_, "string"),
                    is_required=p.is_required,
                    is_single_value=p.is_single_value,
                    is_require_any=p.is_require_any,
                    options=options,
                    cube_id=cube_id,
                )
            )
            if p.is_require_any:
                require_any = True

    return DataSourceParamsInfo(parameters=parameters, require_any=require_any)


def _to_result(raw: flapi_models.DataSourceRunResult) -> DataSourceResult:
    return DataSourceResult(data=raw.results)


# Cube parameters carry an ontology instead of a type. Anything not listed
# is free text.
_CUBE_ONTOLOGY_PARAM_TYPE: dict[str, ParamType] = {
    "TIMESTAMP": "datetime",
    "TIME": "datetime",
    "LOCATION": "geographic",
    "GEOMETRY": "geographic",
}


def _cube_display_name(cube: flapi_models.CubeStructure) -> str:
    return (cube.cube_display_name or "").strip() or cube.cube_name


def _cube_to_data_source(cube: flapi_models.CubeStructure) -> DataSource:
    return DataSource(
        id=cube_data_source_id(cube.cube_name),
        name=_cube_display_name(cube),
        description=cube.cube_description or None,
        type="cube",
    )


def _cube_to_params_info(
    cube: flapi_models.CubeStructure,
    *,
    required_keys: set[str],
    visible_keys: set[str],
) -> DataSourceParamsInfo:
    # An empty visible set means FLAPI told us nothing about visibility, not
    # that every parameter is hidden. Required params are always shown.
    def shown(key: str) -> bool:
        return not visible_keys or key in visible_keys or key in required_keys

    parameters = [
        ParamDefinition(
            name=p.key,
            display_name=p.display_name,
            type=_CUBE_ONTOLOGY_PARAM_TYPE.get((p.ontology or "").upper(), "string"),
            is_required=p.key in required_keys,
            is_single_value=False,
            cube_id=cube.cube_name,
        )
        for p in cube.parameters
        if shown(p.key)
    ]
    parameters += [
        ParamDefinition(
            name=key,
            display_name=p.key_display_name,
            type="string",
            is_required=key in required_keys,
            is_single_value=p.is_single_value,
            options=[ParamOption(name=label, value=value) for value, label in p.values_display_name.items()],
            cube_id=cube.cube_name,
        )
        for key, p in cube.dynamic_parameters.items()
        if shown(key)
    ]
    return DataSourceParamsInfo(parameters=parameters, require_any=False)


def _cube_to_query(cube: flapi_models.CubeStructure) -> DataSourceQuerySchema:
    # The run result is wrapped under the query's display name (see
    # _run_cube), which is the key the generated Results type reads.
    return DataSourceQuerySchema(
        name=cube.cube_name,
        display_name=_cube_display_name(cube),
        description=cube.cube_description or "",
        fields=[
            DataSourceFieldSchema(
                name=field.key,
                display_name=field.header,
                type=_to_domain_field_type(field.data_type.lower()),
            )
            for field in cube.fields
        ],
    )


async def _cube_params_info(
    cube: flapi_models.CubeStructure,
    *,
    authorization: str | None,
) -> DataSourceParamsInfo:
    required, visible = await asyncio.gather(
        data_source_client.get_cube_parameters(cube.cube_name, authorization=authorization, is_required=True),
        data_source_client.get_cube_parameters(cube.cube_name, authorization=authorization, is_visible=True),
    )
    return _cube_to_params_info(
        cube,
        required_keys={p.key for p in required},
        visible_keys={p.key for p in visible},
    )


async def _run_cube(
    cube_name: str,
    *,
    authorization: str | None,
    params: QuickParams | None,
) -> DataSourceResult:
    # Callers send the package-shaped {cubeId: {key: value}}; a cube takes
    # a flat {key: value}.
    flat: dict[str, Any] = {}
    for cube_params in (params.root if params else {}).values():
        flat.update(cube_params)
    cube, rows = await asyncio.gather(
        data_source_client.get_cube(cube_name, authorization=authorization),
        data_source_client.run_cube(cube_name, authorization=authorization, params=flat),
    )
    return DataSourceResult(data={_cube_display_name(cube): rows.root})


async def _search_cube(name: str, *, authorization: str | None) -> list[DataSource]:
    # FLAPI has no cube search; an exact-name lookup is the best we can do.
    if not name:
        return []
    try:
        cube = await data_source_client.get_cube(name, authorization=authorization)
    except FlapiUpstreamError as err:
        if err.status_code != 404:
            logger.warning("Cube lookup for %r failed: %s", name, err)
        return []
    except ValidationError as err:
        logger.warning("Cube %r returned an unexpected structure: %s", name, err)
        return []
    return [_cube_to_data_source(cube)]


# -- Public API ----------------------------------------------------------


async def search_data_sources(
    query_or_id: str | int,
    *,
    authorization: str | None = None,
) -> list[DataSource]:
    kind, key = parse_data_source_id(query_or_id)
    if kind == "cube":
        return await _search_cube(key, authorization=authorization)
    cubes, packages = await asyncio.gather(
        _search_cube(key, authorization=authorization),
        data_source_client.search(key, authorization=authorization),
    )
    return cubes + [_to_data_source(r) for r in packages]


async def list_cubes(*, authorization: str | None = None) -> list[CubeSchema]:
    """Every configured cube with its fields and parameters.

    FLAPI can't list cubes, so the names come from FLAPI_CUBE_NAMES. A cube
    that is missing or malformed is skipped; an auth failure is raised.
    """

    async def describe(name: str) -> CubeSchema:
        cube = await data_source_client.get_cube(name, authorization=authorization)
        params = await _cube_params_info(cube, authorization=authorization)
        query = _cube_to_query(cube)
        return CubeSchema(
            id=cube_data_source_id(cube.cube_name),
            cube_name=cube.cube_name,
            name=query.display_name,
            description=cube.cube_description or None,
            fields=query.fields,
            params=params,
        )

    names = settings.FLAPI_CUBE_NAMES
    results = await asyncio.gather(*(describe(n) for n in names), return_exceptions=True)
    cubes: list[CubeSchema] = []
    for name, result in zip(names, results, strict=True):
        if isinstance(result, CubeSchema):
            cubes.append(result)
        elif isinstance(result, FlapiUpstreamError) and result.status_code == 401:
            raise result
        elif isinstance(result, FlapiUpstreamError | ValidationError):
            logger.warning("Skipping cube %r: %s", name, result)
        else:
            raise result
    return cubes


async def get_params_info(
    data_source_id: str | int,
    *,
    authorization: str | None = None,
) -> DataSourceParamsInfo:
    kind, key = parse_data_source_id(data_source_id)
    if kind == "cube":
        cube = await data_source_client.get_cube(key, authorization=authorization)
        return await _cube_params_info(cube, authorization=authorization)
    info = await data_source_client.get_quick_params_info(key, authorization=authorization)
    return _to_params_info(info)


async def run_data_source(
    data_source_id: str | int,
    *,
    execute_continued_process: bool,
    authorization: str | None = None,
    params: QuickParams | None = None,
) -> DataSourceResult:
    kind, key = parse_data_source_id(data_source_id)
    if kind == "cube":
        return await _run_cube(key, authorization=authorization, params=params)
    raw = await data_source_client.run_data_source(
        key,
        authorization=authorization,
        quick_params=params,
        all_queries=True,
        execute_continued_process=execute_continued_process,
    )
    return _to_result(raw)


async def get_display_name(
    data_source_id: str | int,
    *,
    authorization: str | None = None,
) -> str:
    kind, key = parse_data_source_id(data_source_id)
    if kind == "cube":
        results = await _search_cube(key, authorization=authorization)
    else:
        results = [_to_data_source(r) for r in await data_source_client.search(key, authorization=authorization)]
    if not results:
        raise LookupError(f"Data source {data_source_id} not found")
    name = results[0].name.strip()
    if not name:
        raise LookupError(f"Data source {data_source_id} has no display name")
    return name


def _default_for(param: ParamDefinition) -> QuickParamValue | None:
    # Returns the smallest concrete value we can send: a scalar for single-value
    # params, a one-element list for multi-value params. None means the options
    # list is empty or the first option can't be parsed.
    if not param.options:
        return None
    try:
        parsed = parse_param_value(param.options[0].value, param.type)
    except ValueError:
        return None
    return parsed if param.is_single_value else [parsed]


def _minimal_params_for(params_info: DataSourceParamsInfo) -> QuickParams | None:  # noqa: C901
    if not params_info.parameters:
        return QuickParams(root={})

    defaults: dict[str, tuple[str, QuickParamValue]] = {}

    if params_info.require_any:
        satisfied = False
        for param in params_info.parameters:
            if not param.is_require_any:
                continue
            value = _default_for(param)
            if value is None:
                continue
            defaults[param.name] = (param.cube_id, value)
            satisfied = True
            break
        if not satisfied:
            return None

    for param in params_info.parameters:
        if not param.is_required or param.name in defaults:
            continue
        value = _default_for(param)
        if value is None:
            return None
        defaults[param.name] = (param.cube_id, value)

    grouped: dict[str, dict[str, QuickParamValue]] = {}
    for name, (cube_id, value) in defaults.items():
        grouped.setdefault(cube_id, {})[name] = value
    return QuickParams(root=grouped)


async def can_run_without_params(
    data_source_id: str | int,
    *,
    authorization: str | None = None,
) -> tuple[bool, QuickParams | None]:
    params_info = await get_params_info(data_source_id, authorization=authorization)
    minimal = _minimal_params_for(params_info)
    return minimal is not None, minimal


async def get_usage(
    data_source_id: str | int,
    *,
    authorization: str | None = None,
) -> DataSourceUsage:
    kind, key = parse_data_source_id(data_source_id)
    if kind == "cube":
        cube = await data_source_client.get_cube(key, authorization=authorization)
        queries = [_cube_to_query(cube)]
        params_info = await _cube_params_info(cube, authorization=authorization)
    else:
        queries, params_info = await _package_usage_schema(key, authorization=authorization)
    return await _usage_with_sample(data_source_id, queries, params_info, authorization=authorization)


async def _package_usage_schema(
    data_source_id: str,
    *,
    authorization: str | None,
) -> tuple[list[DataSourceQuerySchema], DataSourceParamsInfo]:
    metadata, params_info = await asyncio.gather(
        data_source_client.get_metadata(data_source_id, authorization=authorization),
        get_params_info(data_source_id, authorization=authorization),
    )

    if not metadata.queries:
        # Planner relies on at least one query for its schema-only TS fallback.
        raise FlapiUpstreamError(
            f"Data source {data_source_id} has no queries in metadata",
        )

    queries = [
        DataSourceQuerySchema(
            # `original_name` is what the run endpoint returns as the cube key
            # in `results`; `name` is its display form. Don't mix them up — the
            # codegen uses `name` as a TS property key and a mismatch yields
            # a Response type whose fields never resolve at runtime.
            name=query.original_name,
            display_name=query.name,
            description=query.description,
            fields=[
                DataSourceFieldSchema(
                    name=field.name,
                    display_name=field.display_name,
                    type=_to_domain_field_type(field.type_),
                    description=field.description,
                )
                for field in query.fields
            ],
        )
        for query in metadata.queries
    ]
    return queries, params_info


async def _usage_with_sample(
    data_source_id: str | int,
    queries: list[DataSourceQuerySchema],
    params_info: DataSourceParamsInfo,
    *,
    authorization: str | None,
) -> DataSourceUsage:
    minimal = _minimal_params_for(params_info)
    can_run = minimal is not None

    sample: dict[str, object] | None = None
    if minimal is not None:
        try:
            result = await run_data_source(
                data_source_id,
                execute_continued_process=False,
                authorization=authorization,
                params=minimal,
            )
            sample = result.data
        except (FlapiUpstreamError, ValidationError) as exc:
            logger.debug("Skipping sample for data source %s: %s", data_source_id, exc)

    return DataSourceUsage(
        queries=queries,
        params=params_info,
        can_run=can_run,
        sample=sample,
    )
