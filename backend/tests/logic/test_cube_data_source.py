from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import pytest

from flow44.integrations.flapi import models as flapi_models
from flow44.integrations.flapi.models import QuickParams
from flow44.logic import data_source as ds_logic


def _cube(**overrides: Any) -> flapi_models.CubeStructure:
    raw: dict[str, Any] = {
        "_id": "abc",
        "createdTime": {"$date": "2026-01-01T00:00:00Z"},
        "cubeName": "PhoneLookup",
        "cubeDisplayName": "Phone Lookup",
        "cubeDescription": "Subscriber details",
        "fields": [
            {"key": "phone", "header": "Phone", "dataType": "string", "ontologyType": "CONTACT_INFO"},
            {"key": "activeSince", "header": "Active Since", "dataType": "DateTime", "ontologyType": "TIMESTAMP"},
            {"key": "isActive", "header": "Active", "dataType": "boolean", "ontologyType": "TEXT"},
        ],
        "parameters": [
            {"key": "fl:phone", "displayName": "Phone Number", "ontology": "CONTACT_INFO", "value": None},
            {"key": "fl:since", "displayName": "Active Since", "ontology": "TIMESTAMP", "value": None},
            {"key": "fl:area", "displayName": "Area", "ontology": "LOCATION", "value": None},
            {"key": "fl:hidden", "displayName": "Trace", "ontology": "TEXT", "value": None},
        ],
        "dynamicParameters": {
            "carrier": {
                "isSingleValue": False,
                "keyDisplayName": "Carrier",
                "valuesDisplayName": {"CEL": "Cellcom", "PRT": "Partner"},
                "value": None,
            }
        },
        "supplierSpecificKey": {"kept": True},
    }
    raw.update(overrides)
    return flapi_models.CubeStructure.model_validate(raw)


def _param_infos(*keys: str) -> list[flapi_models.CubeParameterInfo]:
    return [flapi_models.CubeParameterInfo(key=k) for k in keys]


class TestDataSourceIds:
    def test_cube_prefix_roundtrip(self) -> None:
        ds_id = ds_logic.cube_data_source_id("PhoneLookup")
        assert ds_id == "cube:PhoneLookup"
        assert ds_logic.parse_data_source_id(ds_id) == ("cube", "PhoneLookup")

    def test_package_ids_untouched(self) -> None:
        assert ds_logic.parse_data_source_id(7) == ("package", "7")
        assert ds_logic.parse_data_source_id("12") == ("package", "12")

    def test_storage_type(self) -> None:
        assert ds_logic.storage_type("cube:X") == "flow_cube"
        assert ds_logic.storage_type(3) == "flow_package"


class TestCubeStructureModel:
    def test_parses_underscore_id_and_keeps_extras(self) -> None:
        cube = _cube()
        assert cube.mongo_id == "abc"
        assert cube.model_extra == {"supplierSpecificKey": {"kept": True}}

    def test_minimal_structure(self) -> None:
        cube = flapi_models.CubeStructure.model_validate({"cubeName": "Bare"})
        assert cube.fields == []
        assert cube.parameters == []
        assert cube.dynamic_parameters == {}


class TestCubeToParamsInfo:
    def test_maps_types_required_and_options(self) -> None:
        info = ds_logic._cube_to_params_info(_cube(), required_keys={"fl:phone"}, visible_keys=set())
        by_name = {p.name: p for p in info.parameters}

        assert set(by_name) == {"fl:phone", "fl:since", "fl:area", "fl:hidden", "carrier"}
        assert by_name["fl:phone"].type == "string"
        assert by_name["fl:phone"].is_required is True
        assert by_name["fl:since"].type == "datetime"
        assert by_name["fl:area"].type == "geographic"
        assert by_name["fl:since"].is_required is False
        assert all(p.cube_id == "PhoneLookup" for p in info.parameters)

        carrier = by_name["carrier"]
        assert carrier.display_name == "Carrier"
        assert carrier.is_single_value is False
        assert [(o.name, o.value) for o in carrier.options] == [("Cellcom", "CEL"), ("Partner", "PRT")]

    def test_hides_invisible_but_keeps_required(self) -> None:
        info = ds_logic._cube_to_params_info(
            _cube(),
            required_keys={"fl:hidden"},
            visible_keys={"fl:phone", "carrier"},
        )
        assert {p.name for p in info.parameters} == {"fl:phone", "fl:hidden", "carrier"}


class TestCubeToQuery:
    def test_fields_map_to_domain_types(self) -> None:
        query = ds_logic._cube_to_query(_cube())
        assert query.name == "PhoneLookup"
        assert query.display_name == "Phone Lookup"
        assert [(f.name, f.display_name, f.type) for f in query.fields] == [
            ("phone", "Phone", "string"),
            ("activeSince", "Active Since", "datetime"),
            ("isActive", "Active", "bool"),
        ]

    def test_display_name_falls_back_to_cube_name(self) -> None:
        assert ds_logic._cube_to_query(_cube(cubeDisplayName=None)).display_name == "PhoneLookup"


class TestRunCube:
    async def test_flattens_params_and_wraps_rows(self, monkeypatch: pytest.MonkeyPatch) -> None:
        rows = [{"phone": "050", "isActive": True}]
        run_cube = AsyncMock(return_value=flapi_models.CubeRunResult(rows))
        monkeypatch.setattr(ds_logic.data_source_client, "get_cube", AsyncMock(return_value=_cube()))
        monkeypatch.setattr(ds_logic.data_source_client, "run_cube", run_cube)

        result = await ds_logic.run_data_source(
            "cube:PhoneLookup",
            execute_continued_process=True,
            params=QuickParams(root={"PhoneLookup": {"fl:phone": "050", "carrier": ["CEL"]}}),
        )

        assert result.data == {"Phone Lookup": rows}
        run_cube.assert_awaited_once()
        assert run_cube.await_args.args == ("PhoneLookup",)
        assert run_cube.await_args.kwargs["params"] == {"fl:phone": "050", "carrier": ["CEL"]}

    async def test_does_not_touch_package_endpoint(self, monkeypatch: pytest.MonkeyPatch) -> None:
        package_run = AsyncMock()
        monkeypatch.setattr(ds_logic.data_source_client, "run_data_source", package_run)
        monkeypatch.setattr(ds_logic.data_source_client, "get_cube", AsyncMock(return_value=_cube()))
        monkeypatch.setattr(
            ds_logic.data_source_client, "run_cube", AsyncMock(return_value=flapi_models.CubeRunResult([]))
        )

        await ds_logic.run_data_source("cube:PhoneLookup", execute_continued_process=False)
        package_run.assert_not_awaited()


class TestCubeUsage:
    async def test_required_param_without_options_cannot_run(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(ds_logic.data_source_client, "get_cube", AsyncMock(return_value=_cube()))

        async def get_params(_name: str, **kwargs: Any) -> list[flapi_models.CubeParameterInfo]:
            return _param_infos("fl:phone") if kwargs.get("is_required") else []

        monkeypatch.setattr(ds_logic.data_source_client, "get_cube_parameters", get_params)
        run_cube = AsyncMock()
        monkeypatch.setattr(ds_logic.data_source_client, "run_cube", run_cube)

        usage = await ds_logic.get_usage("cube:PhoneLookup")

        assert usage.can_run is False
        assert usage.sample is None
        assert [q.name for q in usage.queries] == ["PhoneLookup"]
        run_cube.assert_not_awaited()

    async def test_no_required_params_fetches_sample(self, monkeypatch: pytest.MonkeyPatch) -> None:
        rows = [{"phone": "050"}]
        monkeypatch.setattr(ds_logic.data_source_client, "get_cube", AsyncMock(return_value=_cube()))
        monkeypatch.setattr(ds_logic.data_source_client, "get_cube_parameters", AsyncMock(return_value=[]))
        monkeypatch.setattr(
            ds_logic.data_source_client, "run_cube", AsyncMock(return_value=flapi_models.CubeRunResult(rows))
        )

        usage = await ds_logic.get_usage("cube:PhoneLookup")

        assert usage.can_run is True
        assert usage.sample == {"Phone Lookup": rows}


class TestSearch:
    async def test_includes_exact_cube_match_before_packages(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(ds_logic.data_source_client, "get_cube", AsyncMock(return_value=_cube()))
        monkeypatch.setattr(
            ds_logic.data_source_client,
            "search",
            AsyncMock(return_value=[flapi_models.PackageSearchResult(Id=5, Name="Phones")]),
        )

        results = await ds_logic.search_data_sources("PhoneLookup")

        assert [(r.id, r.type) for r in results] == [("cube:PhoneLookup", "cube"), (5, "package")]

    async def test_missing_cube_is_not_an_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            ds_logic.data_source_client,
            "get_cube",
            AsyncMock(side_effect=ds_logic.FlapiUpstreamError("nope", status_code=404)),
        )
        monkeypatch.setattr(ds_logic.data_source_client, "search", AsyncMock(return_value=[]))

        assert await ds_logic.search_data_sources("Nothing") == []

    async def test_cube_prefixed_query_skips_package_search(self, monkeypatch: pytest.MonkeyPatch) -> None:
        package_search = AsyncMock()
        monkeypatch.setattr(ds_logic.data_source_client, "get_cube", AsyncMock(return_value=_cube()))
        monkeypatch.setattr(ds_logic.data_source_client, "search", package_search)

        results = await ds_logic.search_data_sources("cube:PhoneLookup")

        assert [r.id for r in results] == ["cube:PhoneLookup"]
        package_search.assert_not_awaited()

    async def test_display_name_for_cube(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(ds_logic.data_source_client, "get_cube", AsyncMock(return_value=_cube()))
        assert await ds_logic.get_display_name("cube:PhoneLookup") == "Phone Lookup"


class TestListCubes:
    async def test_lists_configured_cubes_with_schema(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(ds_logic.settings, "FLAPI_CUBE_NAMES", ["PhoneLookup", "Other"])

        async def get_cube(name: str, **_: Any) -> flapi_models.CubeStructure:
            return _cube(cubeName=name, cubeDisplayName=f"{name} cube")

        async def get_params(_name: str, **kwargs: Any) -> list[flapi_models.CubeParameterInfo]:
            return _param_infos("fl:phone") if kwargs.get("is_required") else []

        monkeypatch.setattr(ds_logic.data_source_client, "get_cube", get_cube)
        monkeypatch.setattr(ds_logic.data_source_client, "get_cube_parameters", get_params)

        cubes = await ds_logic.list_cubes()

        assert [(c.id, c.name) for c in cubes] == [
            ("cube:PhoneLookup", "PhoneLookup cube"),
            ("cube:Other", "Other cube"),
        ]
        assert [f.name for f in cubes[0].fields] == ["phone", "activeSince", "isActive"]
        assert {p.name for p in cubes[0].params.parameters if p.is_required} == {"fl:phone"}

    async def test_skips_missing_cube(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(ds_logic.settings, "FLAPI_CUBE_NAMES", ["Gone", "PhoneLookup"])

        async def get_cube(name: str, **_: Any) -> flapi_models.CubeStructure:
            if name == "Gone":
                raise ds_logic.FlapiUpstreamError("not found", status_code=404)
            return _cube()

        monkeypatch.setattr(ds_logic.data_source_client, "get_cube", get_cube)
        monkeypatch.setattr(ds_logic.data_source_client, "get_cube_parameters", AsyncMock(return_value=[]))

        assert [c.cube_name for c in await ds_logic.list_cubes()] == ["PhoneLookup"]

    async def test_auth_failure_is_raised(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(ds_logic.settings, "FLAPI_CUBE_NAMES", ["PhoneLookup"])
        monkeypatch.setattr(
            ds_logic.data_source_client,
            "get_cube",
            AsyncMock(side_effect=ds_logic.FlapiUpstreamError("denied", status_code=401)),
        )

        with pytest.raises(ds_logic.FlapiUpstreamError):
            await ds_logic.list_cubes()
