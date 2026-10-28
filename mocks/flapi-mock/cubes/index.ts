import type { MockCube } from './cube-base.js';
import { treeOfKnowledgeDynamic, treeOfKnowledgeLayers, xboard } from './examples.js';
import { cityWeather, inventory, phoneLookup } from './mocks.js';

const allCubes: MockCube[] = [
  inventory,
  cityWeather,
  phoneLookup,
  xboard,
  treeOfKnowledgeDynamic,
  treeOfKnowledgeLayers,
];

// FLAPI addresses cubes by name; lookups are exact (case-sensitive).
export const cubeByName = new Map(allCubes.map((cube) => [cube.name, cube]));
