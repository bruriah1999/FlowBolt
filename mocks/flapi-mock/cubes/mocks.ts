import { MockCube } from './cube-base.js';

// No parameters at all — runs as-is.
export const inventory = new MockCube({
  name: 'Inventory',
  displayName: 'Warehouse Inventory',
  description: 'Current stock levels per item and warehouse',
  fields: [
    { key: 'sku', header: 'SKU', dataType: 'string' },
    { key: 'item', header: 'Item', dataType: 'string' },
    { key: 'warehouse', header: 'Warehouse', dataType: 'string' },
    { key: 'quantity', header: 'Quantity', dataType: 'int' },
    { key: 'unitPrice', header: 'Unit Price', dataType: 'double' },
    { key: 'lastCounted', header: 'Last Counted', dataType: 'datetime', ontologyType: 'TIMESTAMP' },
  ],
  rows: [
    { sku: 'A-100', item: 'Cable', warehouse: 'North', quantity: 420, unitPrice: 3.5, lastCounted: '2026-09-01T08:00:00Z' },
    { sku: 'A-101', item: 'Adapter', warehouse: 'North', quantity: 75, unitPrice: 12.9, lastCounted: '2026-09-01T08:00:00Z' },
    { sku: 'B-200', item: 'Router', warehouse: 'South', quantity: 18, unitPrice: 89.0, lastCounted: '2026-09-03T10:30:00Z' },
    { sku: 'B-201', item: 'Switch', warehouse: 'South', quantity: 32, unitPrice: 59.0, lastCounted: '2026-09-03T10:30:00Z' },
    { sku: 'C-300', item: 'Antenna', warehouse: 'East', quantity: 140, unitPrice: 24.0, lastCounted: '2026-09-05T14:15:00Z' },
  ],
});

// Required dynamic (option) parameter + optional free parameter of another ontology.
export const cityWeather = new MockCube({
  name: 'CityWeather',
  displayName: 'City Weather',
  description: 'Daily weather readings per city',
  fields: [
    { key: 'city', header: 'City', dataType: 'string' },
    { key: 'date', header: 'Date', dataType: 'date', ontologyType: 'TIMESTAMP' },
    { key: 'tempC', header: 'Temperature (C)', dataType: 'double' },
    { key: 'condition', header: 'Condition', dataType: 'string' },
    { key: 'station', header: 'Station Location', dataType: 'wkt', ontologyType: 'LOCATION' },
  ],
  dynamicParameters: [
    {
      key: 'city',
      displayName: 'City',
      options: { TLV: 'Tel Aviv', JLM: 'Jerusalem', HFA: 'Haifa' },
      isSingleValue: true,
      required: true,
      column: 'city',
    },
  ],
  parameters: [{ key: 'fl:area', displayName: 'Area', ontology: 'LOCATION' }],
  rows: [
    { city: 'TLV', date: '2026-10-01', tempC: 29.5, condition: 'Sunny', station: 'POINT(34.78 32.08)' },
    { city: 'TLV', date: '2026-10-02', tempC: 28.1, condition: 'Cloudy', station: 'POINT(34.78 32.08)' },
    { city: 'JLM', date: '2026-10-01', tempC: 24.0, condition: 'Sunny', station: 'POINT(35.21 31.77)' },
    { city: 'JLM', date: '2026-10-02', tempC: 22.3, condition: 'Windy', station: 'POINT(35.21 31.77)' },
    { city: 'HFA', date: '2026-10-01', tempC: 27.2, condition: 'Humid', station: 'POINT(34.99 32.79)' },
  ],
});

// Required free parameter without options — cannot run without user input.
export const phoneLookup = new MockCube({
  name: 'PhoneLookup',
  displayName: 'Phone Lookup',
  description: 'Subscriber details by phone number',
  fields: [
    { key: 'phone', header: 'Phone', dataType: 'string', ontologyType: 'CONTACT_INFO' },
    { key: 'owner', header: 'Owner', dataType: 'string' },
    { key: 'carrier', header: 'Carrier', dataType: 'string' },
    { key: 'activeSince', header: 'Active Since', dataType: 'datetime', ontologyType: 'TIMESTAMP' },
    { key: 'isActive', header: 'Active', dataType: 'boolean' },
  ],
  parameters: [
    { key: 'fl:phone', displayName: 'Phone Number', ontology: 'CONTACT_INFO', required: true, column: 'phone' },
    { key: 'fl:since', displayName: 'Active Since', ontology: 'TIMESTAMP' },
    { key: 'fl:internalTrace', displayName: 'Trace Id', ontology: 'TEXT', visible: false },
  ],
  dynamicParameters: [
    {
      key: 'carrier',
      displayName: 'Carrier',
      options: { Cellcom: 'Cellcom', Partner: 'Partner', Pelephone: 'Pelephone' },
      isSingleValue: false,
      column: 'carrier',
    },
  ],
  rows: [
    { phone: '0501234567', owner: 'Dana Levi', carrier: 'Cellcom', activeSince: '2019-04-12T00:00:00Z', isActive: true },
    { phone: '0527654321', owner: 'Amir Cohen', carrier: 'Partner', activeSince: '2021-11-30T00:00:00Z', isActive: true },
    { phone: '0549998877', owner: 'Noa Peretz', carrier: 'Pelephone', activeSince: '2016-07-08T00:00:00Z', isActive: false },
  ],
});
