import type { CubeDynamicParameter, CubeField, CubeParameter, CubeStructure } from '../schemas';

type Row = Record<string, unknown>;

export interface CubeParamConfig {
  key: string;
  displayName: string;
  ontology: string;
  required?: boolean;
  visible?: boolean;
  // Row column the value filters on; omit for params that don't filter.
  column?: string;
}

export interface CubeDynamicParamConfig {
  key: string;
  displayName: string;
  // value -> display label
  options: Record<string, string>;
  isSingleValue?: boolean;
  required?: boolean;
  column?: string;
}

export interface MockCubeConfig {
  name: string;
  displayName: string;
  description: string;
  fields: Array<Pick<CubeField, 'key' | 'header' | 'dataType'> & { ontologyType?: string }>;
  parameters?: CubeParamConfig[];
  dynamicParameters?: CubeDynamicParamConfig[];
  rows: Row[];
}

// One entry of GET /cube/v1/{cubeName}/parameters.
export interface CubeParameterInfo {
  key: string;
  displayName: string;
  ontology: string | null;
  isRequired: boolean;
  isVisible: boolean;
}

export class MockCube {
  readonly name: string;
  readonly structure: CubeStructure;
  private readonly config: MockCubeConfig;

  constructor(config: MockCubeConfig) {
    this.config = config;
    this.name = config.name;
    this.structure = {
      _id: `cube-${config.name}`,
      createdTime: { $date: '2026-01-01T00:00:00.000Z' },
      cubeName: config.name,
      cubeDisplayName: config.displayName,
      cubeDescription: config.description,
      cubeOwner: 'flapi-mock',
      cubeIcon: null,
      fields: config.fields.map((f) => ({ ontologyType: 'TEXT', ...f })),
      parameters: (config.parameters ?? []).map(
        (p): CubeParameter => ({ key: p.key, displayName: p.displayName, ontology: p.ontology, value: null }),
      ),
      dynamicParameters: Object.fromEntries(
        (config.dynamicParameters ?? []).map((p): [string, CubeDynamicParameter] => [
          p.key,
          {
            isSingleValue: p.isSingleValue ?? true,
            keyDisplayName: p.displayName,
            valuesDisplayName: p.options,
            value: null,
          },
        ]),
      ),
      staticParameters: {},
      isAuthorized: true,
      triangles: [],
    };
  }

  parameterInfo(filter: { isRequired?: boolean; isVisible?: boolean } = {}): CubeParameterInfo[] {
    const all: CubeParameterInfo[] = [
      ...(this.config.parameters ?? []).map((p) => ({
        key: p.key,
        displayName: p.displayName,
        ontology: p.ontology,
        isRequired: p.required ?? false,
        isVisible: p.visible ?? true,
      })),
      ...(this.config.dynamicParameters ?? []).map((p) => ({
        key: p.key,
        displayName: p.displayName,
        ontology: null,
        isRequired: p.required ?? false,
        isVisible: true,
      })),
    ];
    return all.filter(
      (p) =>
        (filter.isRequired === undefined || p.isRequired === filter.isRequired) &&
        (filter.isVisible === undefined || p.isVisible === filter.isVisible),
    );
  }

  // Body is a flat JSON of parameter key -> value (plus cubeName).
  run(body: Record<string, unknown>): Row[] | { error: string } {
    const params = { ...body };
    delete params.cubeName;

    const missing = this.parameterInfo({ isRequired: true })
      .map((p) => p.key)
      .filter((key) => isEmpty(params[key]));
    if (missing.length > 0) {
      return { error: `Missing required parameters: ${missing.join(', ')}` };
    }

    const filters = [...(this.config.parameters ?? []), ...(this.config.dynamicParameters ?? [])].filter(
      (p) => p.column && !isEmpty(params[p.key]),
    );
    return this.config.rows.filter((row) =>
      filters.every((p) => toList(params[p.key]).includes(String(row[p.column!]))),
    );
  }
}

function isEmpty(value: unknown): boolean {
  return value === undefined || value === null || value === '' || (Array.isArray(value) && value.length === 0);
}

function toList(value: unknown): string[] {
  return (Array.isArray(value) ? value : [value]).map(String);
}
