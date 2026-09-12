const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const values = new Map();
const storage = {
  getItem: key => values.get(key) ?? null,
  setItem: (key, value) => values.set(key, value),
  removeItem: key => values.delete(key),
};
const sandbox = {localStorage: storage, console};
sandbox.window = sandbox;
vm.createContext(sandbox);
vm.runInContext(fs.readFileSync('mostek_kultura/static/source-preferences.js', 'utf8'), sandbox);
const prefs = sandbox.MostkulturaSources;
const plain = value => JSON.parse(JSON.stringify(value));
const all = {disabledSources: [], disabledPlaces: []};
assert.deepEqual(plain(prefs.read()), all);
assert.equal(prefs.KEY, 'mostkultura.sourcePreferences.v1');

for (const malformed of ['{oops', 'null', '42', '[]', '"string"']) {
  values.set(prefs.KEY, malformed);
  assert.deepEqual(plain(prefs.read()), all);
}
assert.deepEqual(plain(prefs.normalize({disabledSources:['a','a',42,null,''], disabledPlaces:'HK'})),
  {disabledSources:['a'], disabledPlaces:[]});

const selected = {disabledSources:['direct'], disabledPlaces:[]};
const direct = {place:'Hradec Králové', sources:['direct']};
const shared = {...direct, sources:['direct','regional']};
assert.equal(prefs.eventAllowed(direct, selected), false);
assert.equal(prefs.eventAllowed(shared, selected), true);
assert.equal(prefs.eventAllowed(shared, {disabledSources:['direct','regional'],disabledPlaces:[]}), false);
assert.equal(prefs.eventAllowed({...direct, sources:['new-source']}, selected), true);
assert.equal(prefs.eventAllowed({place:'Hradec Králové',source:'direct'}, selected), false);
assert.equal(prefs.eventAllowed({place:'Hradec Králové'}, selected), true);
assert.equal(prefs.eventAllowed(shared, {disabledSources:[],disabledPlaces:['Hradec Králové']}), false);
assert.equal(prefs.eventAllowed({...shared,place:'Trutnov'}, {disabledSources:[],disabledPlaces:['Hradec Králové']}), true);
assert.deepEqual(selected, {disabledSources:['direct'],disabledPlaces:[]});
const compiled = prefs.compile(selected);
assert.equal(compiled(direct), false);
assert.equal(compiled(shared), true);

values.set('unrelated-setting', 'preserve');
assert.equal(prefs.save(selected), true);
assert.deepEqual(plain(prefs.read()), selected);
assert.equal(prefs.save(all), true);
assert.equal(values.get('unrelated-setting'), 'preserve');
assert.deepEqual(plain(prefs.read()), all);

Object.defineProperty(sandbox, 'localStorage', {configurable:true, get(){throw new Error('blocked storage');}});
assert.deepEqual(plain(prefs.read()), all);
assert.equal(prefs.save(selected), false);
Object.defineProperty(sandbox, 'localStorage', {value:{getItem:()=>null,setItem(){throw new Error('quota');}},configurable:true});
assert.equal(prefs.save(selected), false);
console.log('Preference contract passed: defaults, malformed storage, provenance, city gates, persistence and storage failures.');
