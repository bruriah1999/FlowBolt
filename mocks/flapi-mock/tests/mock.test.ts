#!/usr/bin/env tsx

const baseUrl = process.argv[2] || 'http://localhost:6001';
const AUTH_HEADER = { Authorization: 'Bearer mock-test-token' };

const parseBody = async (response: Response): Promise<unknown> => {
  const text = await response.text();
  if (!text) return '';
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
};

const get = (path: string) =>
  fetch(`${baseUrl}${path}`, { headers: AUTH_HEADER }).then(async (r) => ({
    status: r.status,
    body: await parseBody(r),
  }));

const post = (path: string, body: unknown) =>
  fetch(`${baseUrl}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...AUTH_HEADER },
    body: JSON.stringify(body),
  }).then(async (r) => ({
    status: r.status,
    body: await parseBody(r),
  }));

const assert = (cond: boolean, msg: string) => {
  if (!cond) throw new Error(msg);
};

const run = async () => {
  // Health (no auth needed)
  const health = await get('/health');
  assert(health.status === 200, `GET /health expected 200, got ${health.status}`);
  const healthBody = await health.body as { ok?: boolean };
  assert(healthBody?.ok === true, 'GET /health body.ok should be true');
  console.log('✓ GET /health OK');

  // Search — by name
  const search = await get('/package/v1/search/Sales');
  assert(search.status === 200, `GET search expected 200, got ${search.status}`);
  const searchBody = await search.body;
  assert(Array.isArray(searchBody), 'search must return array');
  assert(Array.isArray(searchBody) && searchBody.every((p: { Type?: string }) => p.Type === 'Package'), 'search must return only Type===Package');
  console.log('✓ GET /package/v1/search/:partial OK');

  // Search — by ID
  const searchById = await get('/package/v1/search/7');
  assert(searchById.status === 200, `GET search by ID expected 200, got ${searchById.status}`);
  const searchByIdBody = await searchById.body;
  assert(Array.isArray(searchByIdBody) && searchByIdBody.length === 1, 'search by ID must return single-element array');
  const first = searchByIdBody as Array<{ Id?: number; Name?: string }>;
  assert(first[0].Id === 7 && first[0].Name != null, 'search by ID must return correct package');
  console.log('✓ GET /package/v1/search/:id OK');

  // Package metadata
  const metadata = await get('/package/v2/7');
  assert(metadata.status === 200, `GET metadata expected 200, got ${metadata.status}`);
  const metadataBody = await metadata.body as { Id?: number; Name?: string; Queries?: unknown[] };
  assert(typeof metadataBody === 'object' && metadataBody?.Id === 7 && metadataBody?.Name != null, 'metadata must have Id and Name');
  assert(Array.isArray(metadataBody?.Queries) && metadataBody.Queries.length > 0, 'metadata must have Queries array');
  console.log('✓ GET /package/v2/:id OK (metadata)');

  // Run package
  const flapi = await post('/package/v3/7', {});
  assert(flapi.status === 200, `POST run expected 200, got ${flapi.status}`);
  const flapiBody = await flapi.body as { results?: unknown };
  assert(typeof flapiBody === 'object' && flapiBody != null && 'results' in flapiBody && typeof flapiBody.results === 'object', 'run body must have results');
  console.log('✓ POST /package/v3/:id OK');

  // Run package — not found
  const notFoundPkg = await post('/package/v3/99999', {});
  assert(notFoundPkg.status === 404, `POST run unknown ID expected 404, got ${notFoundPkg.status}`);
  console.log('✓ POST /package/v3/:id 404 for unknown ID OK');

  // Metadata — not found
  const notFoundMeta = await get('/package/v2/99999');
  assert(notFoundMeta.status === 404, `GET metadata unknown ID expected 404, got ${notFoundMeta.status}`);
  console.log('✓ GET /package/v2/:id 404 for unknown ID OK');

  // Quick params info
  const quick = await get('/package/v1/quick/7');
  assert(quick.status === 200, `GET quick params expected 200, got ${quick.status}`);
  const quickBody = await quick.body;
  assert(typeof quickBody === 'object' && quickBody !== null, 'quick params must return object');
  console.log('✓ GET /package/v1/quick/:id OK');

  // Run with quick params (package 20 — person by ID)
  const personRun = await post('/package/v3/20', { 'person-query-1': { personId: 2 } });
  assert(personRun.status === 200, `POST run with quick params expected 200, got ${personRun.status}`);
  const personBody = await personRun.body as { results?: { Person?: { name?: string } } };
  assert(personBody?.results?.Person?.name === 'Nora T', `Expected person name 'Nora T', got ${personBody?.results?.Person?.name}`);
  console.log('✓ POST /package/v3/20 with quick params OK');

  // Auth required
  const noAuth = await fetch(`${baseUrl}/package/v1/search/test`, { headers: {} });
  assert(noAuth.status === 401, `GET search without auth expected 401, got ${noAuth.status}`);
  console.log('✓ GET /package/v1/search/:partial 401 without auth OK');

  // Validation: missing required param (package 18 requires 'status' without default)
  const missingRequired = await post('/package/v3/18', {});
  assert(missingRequired.status === 421, `POST with missing required param expected 421, got ${missingRequired.status}`);
  const missingRequiredBody = await missingRequired.body as { error?: { message?: string } };
  assert(
    typeof missingRequiredBody === 'object' && !!missingRequiredBody?.error?.message?.includes('status'),
    `Expected error about 'status', got: ${missingRequiredBody?.error?.message}`,
  );
  console.log('✓ POST /package/v3/18 rejects missing required param OK');

  // Validation: missing requireAny params (package 16 requires at least one of region/department)
  const missingRequireAny = await post('/package/v3/16', {});
  assert(missingRequireAny.status === 421, `POST with missing requireAny param expected 421, got ${missingRequireAny.status}`);
  console.log('✓ POST /package/v3/16 rejects missing requireAny params OK');

  // Validation: valid requireAny param (package 16 with only region)
  const validRequireAny = await post('/package/v3/16', { 'requireany-query-1': { region: 'North' } });
  assert(validRequireAny.status === 200, `POST with valid requireAny param expected 200, got ${validRequireAny.status}`);
  const validRequireAnyBody = await validRequireAny.body as { results?: { 'Filters Cube'?: unknown[] } };
  const hasFilters = typeof validRequireAnyBody === 'object' && validRequireAnyBody?.results?.['Filters Cube'];
  assert(!!hasFilters && Array.isArray(validRequireAnyBody.results!['Filters Cube']) && validRequireAnyBody.results!['Filters Cube'].length > 0, 'Expected filtered results');
  console.log('✓ POST /package/v3/16 accepts valid requireAny param OK');

  // Validation: missing multiple required params (package 17 requires type and year)
  const missingMultiple = await post('/package/v3/17', {});
  assert(missingMultiple.status === 421, `POST with missing multiple params expected 421, got ${missingMultiple.status}`);
  console.log('✓ POST /package/v3/17 rejects missing required params OK');

  // Validation: valid required param (package 18 with status)
  const validRequired = await post('/package/v3/18', { 'required-query-18': { status: 'Active' } });
  assert(validRequired.status === 200, `POST with valid required param expected 200, got ${validRequired.status}`);
  const validRequiredBody = await validRequired.body as { results?: { 'Required Cube'?: unknown[] } };
  const hasCube = typeof validRequiredBody === 'object' && validRequiredBody?.results?.['Required Cube'];
  assert(!!hasCube && Array.isArray(validRequiredBody.results!['Required Cube']) && validRequiredBody.results!['Required Cube'].length > 0, 'Expected filtered results');
  console.log('✓ POST /package/v3/18 accepts valid required param OK');

  // Validation: package 14 (required with default) works without params
  const requiredWithDefault = await post('/package/v3/14', {});
  assert(requiredWithDefault.status === 200, `POST with default param expected 200, got ${requiredWithDefault.status}`);
  const requiredWithDefaultBody = await requiredWithDefault.body as { results?: { 'Required Cube'?: unknown[] } };
  assert(!!requiredWithDefaultBody?.results?.['Required Cube'] && Array.isArray(requiredWithDefaultBody.results['Required Cube']), 'Expected default results');
  console.log('✓ POST /package/v3/14 uses default value OK');

  // Cube structure
  const cube = await get('/cube/v1/PhoneLookup');
  assert(cube.status === 200, `GET cube expected 200, got ${cube.status}`);
  const cubeBody = cube.body as { cubeName?: string; fields?: unknown[]; parameters?: unknown[] };
  assert(cubeBody.cubeName === 'PhoneLookup', 'cube structure must echo cubeName');
  assert(Array.isArray(cubeBody.fields) && cubeBody.fields.length > 0, 'cube structure must have fields');
  assert(Array.isArray(cubeBody.parameters) && cubeBody.parameters.length > 1, 'cube structure must have parameters');
  console.log('✓ GET /cube/v1/:cubeName OK');

  const unknownCube = await get('/cube/v1/NoSuchCube');
  assert(unknownCube.status === 404, `GET unknown cube expected 404, got ${unknownCube.status}`);
  console.log('✓ GET /cube/v1/:cubeName 404 for unknown cube OK');

  // Cube parameters — required filter
  const required = await get('/cube/v1/PhoneLookup/parameters?isRequired=true');
  assert(required.status === 200, `GET cube parameters expected 200, got ${required.status}`);
  const requiredKeys = (required.body as Array<{ key: string }>).map((p) => p.key);
  assert(requiredKeys.length === 1 && requiredKeys[0] === 'fl:phone', `Expected only fl:phone required, got ${requiredKeys}`);
  console.log('✓ GET /cube/v1/:cubeName/parameters?isRequired=true OK');

  // Cube run — rows are a flat list
  const inventoryRun = await post('/cube/v1/Inventory', { cubeName: 'Inventory' });
  assert(inventoryRun.status === 200, `POST cube run expected 200, got ${inventoryRun.status}`);
  assert(Array.isArray(inventoryRun.body) && inventoryRun.body.length === 5, 'cube run must return all rows');
  console.log('✓ POST /cube/v1/:cubeName OK');

  const phoneRun = await post('/cube/v1/PhoneLookup', { cubeName: 'PhoneLookup', 'fl:phone': '0527654321' });
  const phoneRows = phoneRun.body as Array<{ owner?: string }>;
  assert(phoneRun.status === 200 && phoneRows.length === 1 && phoneRows[0].owner === 'Amir Cohen', 'cube run must filter by param');
  console.log('✓ POST /cube/v1/:cubeName filters by parameter OK');

  const phoneMissing = await post('/cube/v1/PhoneLookup', { cubeName: 'PhoneLookup' });
  assert(phoneMissing.status === 400, `POST cube without required param expected 400, got ${phoneMissing.status}`);
  console.log('✓ POST /cube/v1/:cubeName rejects missing required param OK');

  // Example cubes (named after the FLAPI Swagger examples) run without input
  for (const name of ['Xboard', 'TreeOfKnowledgeDynamic', 'TreeOfKnowledgeLayers']) {
    const run = await post(`/cube/v1/${name}`, { cubeName: name });
    assert(run.status === 200 && Array.isArray(run.body) && run.body.length > 0, `${name} must run without params`);
  }
  const blocked = await post('/cube/v1/Xboard', { cubeName: 'Xboard', status: ['todo'], priority: 'high' });
  const blockedRows = blocked.body as Array<{ itemId?: string }>;
  assert(blocked.status === 200 && blockedRows.length === 2, `Xboard filter expected 2 rows, got ${blockedRows.length}`);
  console.log('✓ Example cubes run and filter OK');

  console.log('\n✅ All mock tests passed.');
};

run().catch((e) => {
  console.error('❌ Test failed:', e.message);
  process.exit(1);
});
