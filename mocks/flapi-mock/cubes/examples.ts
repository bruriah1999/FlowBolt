import { MockCube } from './cube-base.js';

// Cubes named after the examples in the real FLAPI Swagger. Like package 7,
// every parameter is optional so each one runs (and samples) without input.

export const xboard = new MockCube({
  name: 'Xboard',
  displayName: 'Xboard',
  description: 'Work items on the team board with status, owner and effort',
  fields: [
    { key: 'itemId', header: 'Item ID', dataType: 'string' },
    { key: 'title', header: 'Title', dataType: 'string' },
    { key: 'status', header: 'Status', dataType: 'string' },
    { key: 'assignee', header: 'Assignee', dataType: 'string' },
    { key: 'priority', header: 'Priority', dataType: 'string' },
    { key: 'storyPoints', header: 'Story Points', dataType: 'int' },
    { key: 'createdAt', header: 'Created At', dataType: 'datetime', ontologyType: 'TIMESTAMP' },
    { key: 'isBlocked', header: 'Blocked', dataType: 'boolean' },
  ],
  dynamicParameters: [
    {
      key: 'status',
      displayName: 'Status',
      options: { todo: 'To Do', inProgress: 'In Progress', review: 'In Review', done: 'Done' },
      isSingleValue: false,
      column: 'status',
    },
    {
      key: 'priority',
      displayName: 'Priority',
      options: { high: 'High', medium: 'Medium', low: 'Low' },
      isSingleValue: true,
      column: 'priority',
    },
  ],
  parameters: [{ key: 'fl:assignee', displayName: 'Assignee', ontology: 'ENTITY_ID', column: 'assignee' }],
  rows: [
    { itemId: 'XB-101', title: 'Login page redesign',        status: 'done',       assignee: 'Noa Levi',     priority: 'high',   storyPoints: 5, createdAt: '2026-08-03T09:12:00Z', isBlocked: false },
    { itemId: 'XB-102', title: 'Export report to PDF',        status: 'inProgress', assignee: 'Yosef Katz',   priority: 'medium', storyPoints: 3, createdAt: '2026-08-05T13:40:00Z', isBlocked: false },
    { itemId: 'XB-103', title: 'Fix timezone in charts',      status: 'review',     assignee: 'Tal Golan',    priority: 'high',   storyPoints: 2, createdAt: '2026-08-07T08:05:00Z', isBlocked: false },
    { itemId: 'XB-104', title: 'Bulk user import',            status: 'todo',       assignee: 'Maya Cohen',   priority: 'low',    storyPoints: 8, createdAt: '2026-08-10T11:22:00Z', isBlocked: true },
    { itemId: 'XB-105', title: 'Dark mode for dashboard',     status: 'inProgress', assignee: 'Noa Levi',     priority: 'medium', storyPoints: 5, createdAt: '2026-08-12T15:30:00Z', isBlocked: false },
    { itemId: 'XB-106', title: 'Audit log retention policy',  status: 'todo',       assignee: 'Avi Peretz',   priority: 'high',   storyPoints: 3, createdAt: '2026-08-14T10:00:00Z', isBlocked: true },
    { itemId: 'XB-107', title: 'Search autocomplete',         status: 'done',       assignee: 'Lior Ben-Ari', priority: 'medium', storyPoints: 5, createdAt: '2026-08-18T09:45:00Z', isBlocked: false },
    { itemId: 'XB-108', title: 'Mobile layout for map view',  status: 'review',     assignee: 'Yosef Katz',   priority: 'low',    storyPoints: 3, createdAt: '2026-08-21T14:10:00Z', isBlocked: false },
    { itemId: 'XB-109', title: 'Rate limit public API',       status: 'todo',       assignee: 'Tal Golan',    priority: 'high',   storyPoints: 5, createdAt: '2026-08-25T07:55:00Z', isBlocked: false },
    { itemId: 'XB-110', title: 'Onboarding checklist',        status: 'done',       assignee: 'Maya Cohen',   priority: 'low',    storyPoints: 2, createdAt: '2026-08-28T12:20:00Z', isBlocked: false },
  ],
});

export const treeOfKnowledgeDynamic = new MockCube({
  name: 'TreeOfKnowledgeDynamic',
  displayName: 'Tree of Knowledge (Dynamic)',
  description: 'Knowledge topics as a parent/child tree with category and usage counts',
  fields: [
    { key: 'nodeId', header: 'Node ID', dataType: 'string' },
    { key: 'parentId', header: 'Parent ID', dataType: 'string' },
    { key: 'label', header: 'Label', dataType: 'string' },
    { key: 'category', header: 'Category', dataType: 'string' },
    { key: 'depth', header: 'Depth', dataType: 'int' },
    { key: 'documents', header: 'Documents', dataType: 'int' },
    { key: 'score', header: 'Relevance Score', dataType: 'double' },
    { key: 'updatedAt', header: 'Updated At', dataType: 'datetime', ontologyType: 'TIMESTAMP' },
  ],
  dynamicParameters: [
    {
      // Same parameter name as the FLAPI Swagger autocomplete example.
      key: 'fl:dynamic',
      displayName: 'Category',
      options: { science: 'Science', technology: 'Technology', history: 'History', geography: 'Geography' },
      isSingleValue: false,
      column: 'category',
    },
  ],
  rows: [
    { nodeId: 'N1',  parentId: null, label: 'Knowledge',          category: 'root',       depth: 0, documents: 1240, score: 1.0,  updatedAt: '2026-09-01T00:00:00Z' },
    { nodeId: 'N2',  parentId: 'N1', label: 'Science',            category: 'science',    depth: 1, documents: 410,  score: 0.92, updatedAt: '2026-09-02T08:00:00Z' },
    { nodeId: 'N3',  parentId: 'N2', label: 'Physics',            category: 'science',    depth: 2, documents: 160,  score: 0.88, updatedAt: '2026-09-03T10:30:00Z' },
    { nodeId: 'N4',  parentId: 'N2', label: 'Biology',            category: 'science',    depth: 2, documents: 145,  score: 0.84, updatedAt: '2026-09-03T11:15:00Z' },
    { nodeId: 'N5',  parentId: 'N1', label: 'Technology',         category: 'technology', depth: 1, documents: 380,  score: 0.95, updatedAt: '2026-09-04T09:00:00Z' },
    { nodeId: 'N6',  parentId: 'N5', label: 'Machine Learning',   category: 'technology', depth: 2, documents: 190,  score: 0.97, updatedAt: '2026-09-05T13:20:00Z' },
    { nodeId: 'N7',  parentId: 'N5', label: 'Networking',         category: 'technology', depth: 2, documents: 95,   score: 0.71, updatedAt: '2026-09-05T14:45:00Z' },
    { nodeId: 'N8',  parentId: 'N1', label: 'History',            category: 'history',    depth: 1, documents: 260,  score: 0.66, updatedAt: '2026-09-06T07:40:00Z' },
    { nodeId: 'N9',  parentId: 'N8', label: 'Ancient Near East',  category: 'history',    depth: 2, documents: 88,   score: 0.62, updatedAt: '2026-09-07T16:05:00Z' },
    { nodeId: 'N10', parentId: 'N1', label: 'Geography',          category: 'geography',  depth: 1, documents: 190,  score: 0.58, updatedAt: '2026-09-08T12:00:00Z' },
    { nodeId: 'N11', parentId: 'N10', label: 'Rivers and Lakes',  category: 'geography',  depth: 2, documents: 61,   score: 0.49, updatedAt: '2026-09-09T09:30:00Z' },
  ],
});

export const treeOfKnowledgeLayers = new MockCube({
  name: 'TreeOfKnowledgeLayers',
  displayName: 'Tree of Knowledge (Layers)',
  description: 'Map layers of the knowledge tree with geometry and feature counts',
  fields: [
    { key: 'layerId', header: 'Layer ID', dataType: 'string' },
    { key: 'name', header: 'Layer Name', dataType: 'string' },
    { key: 'layerType', header: 'Layer Type', dataType: 'string' },
    { key: 'featureCount', header: 'Features', dataType: 'int' },
    { key: 'coverageKm2', header: 'Coverage (km²)', dataType: 'double' },
    { key: 'centroid', header: 'Centroid', dataType: 'wkt', ontologyType: 'LOCATION' },
    { key: 'isPublic', header: 'Public', dataType: 'boolean' },
    { key: 'updatedAt', header: 'Updated At', dataType: 'datetime', ontologyType: 'TIMESTAMP' },
  ],
  dynamicParameters: [
    {
      key: 'fl:layerType',
      displayName: 'Layer Type',
      options: { points: 'Points', lines: 'Lines', polygons: 'Polygons' },
      isSingleValue: false,
      column: 'layerType',
    },
  ],
  parameters: [{ key: 'fl:area', displayName: 'Area', ontology: 'LOCATION' }],
  rows: [
    { layerId: 'L1', name: 'Universities',      layerType: 'points',   featureCount: 64,  coverageKm2: 21500.0, centroid: 'POINT(34.85 31.95)', isPublic: true,  updatedAt: '2026-09-10T08:00:00Z' },
    { layerId: 'L2', name: 'Research Labs',     layerType: 'points',   featureCount: 212, coverageKm2: 18200.5, centroid: 'POINT(34.80 32.05)', isPublic: false, updatedAt: '2026-09-11T09:30:00Z' },
    { layerId: 'L3', name: 'Rail Lines',        layerType: 'lines',    featureCount: 38,  coverageKm2: 9800.0,  centroid: 'POINT(34.95 32.20)', isPublic: true,  updatedAt: '2026-09-12T10:15:00Z' },
    { layerId: 'L4', name: 'Fiber Backbone',    layerType: 'lines',    featureCount: 17,  coverageKm2: 7600.25, centroid: 'POINT(35.00 31.80)', isPublic: false, updatedAt: '2026-09-13T11:45:00Z' },
    { layerId: 'L5', name: 'Nature Reserves',   layerType: 'polygons', featureCount: 143, coverageKm2: 5400.75, centroid: 'POINT(35.10 31.30)', isPublic: true,  updatedAt: '2026-09-14T07:20:00Z' },
    { layerId: 'L6', name: 'Municipal Borders', layerType: 'polygons', featureCount: 257, coverageKm2: 22070.0, centroid: 'POINT(34.90 31.60)', isPublic: true,  updatedAt: '2026-09-15T13:00:00Z' },
    { layerId: 'L7', name: 'Archaeology Sites', layerType: 'polygons', featureCount: 96,  coverageKm2: 1250.4,  centroid: 'POINT(35.20 31.75)', isPublic: false, updatedAt: '2026-09-16T15:35:00Z' },
  ],
});
