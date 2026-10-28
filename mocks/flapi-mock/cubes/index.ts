import type { MockCube } from './cube-base.js';
import { cityWeather, inventory, phoneLookup } from './mocks.js';

const allCubes: MockCube[] = [inventory, cityWeather, phoneLookup];

// FLAPI addresses cubes by name; lookups are exact (case-sensitive).
export const cubeByName = new Map(allCubes.map((cube) => [cube.name, cube]));
