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
const defaults = {disabledSources: [], disabledPlaces: ['Hradec Králové']};
assert.deepEqual(plain(prefs.read()), defaults);
assert.equal(values.has(prefs.KEY), false);
const temporary = prefs.read();temporary.disabledPlaces.push('Trutnov');
assert.deepEqual(plain(prefs.read()), defaults);
assert.equal(prefs.KEY, 'mostkultura.sourcePreferences.v1');

for (const malformed of ['{oops', 'null', '42', '[]', '"string"', '{}', '{"disabledPlaces":"Hradec Králové","disabledSources":[]}']) {
  values.set(prefs.KEY, malformed);
  assert.deepEqual(plain(prefs.read()), defaults);
}
assert.deepEqual(plain(prefs.normalize({disabledSources:['a','a',42,null,''], disabledPlaces:'HK'})),
  {disabledSources:['a'], disabledPlaces:[]});

const legacy = {disabledSources:['existing'], disabledPlaces:['Valdštejnská lodžie','Hradec Králové']};
const migrated = {disabledSources:['existing','valdstejnska-lodzie'], disabledPlaces:['Hradec Králové']};
values.set(prefs.KEY, JSON.stringify(legacy));
assert.deepEqual(plain(prefs.read()), migrated);
assert.equal(prefs.eventAllowed({place:'Jičín',sources:['valdstejnska-lodzie']},prefs.read()),false);
assert.equal(prefs.eventAllowed({place:'Jičín',sources:['jicin']},prefs.read()),true);
assert.equal(prefs.save(prefs.read()),true);
assert.deepEqual(plain(prefs.read()),migrated);

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

const catalog = [
  {name:'mostek', label:'Mostek', place:'Mostek', status:'ok'},
  {name:'hk-ok', label:'Hradec OK', place:'Hradec Králové', status:'ok'},
  {name:'hk-fallback', label:'Hradec záloha', place:'Hradec Králové', status:'fallback'},
  {name:'regional', label:'Regionální', place:null, status:'error'},
  {name:'zero-events', label:'Bez akcí', place:'Trutnov', status:'ok'},
];
assert.deepEqual(plain(prefs.summarizeSources(catalog, defaults)),
  {available:5, selected:3, healthy:2, issues:1, issueLabels:['Regionální']});
assert.deepEqual(plain(prefs.summarizeSources(catalog, all)),
  {available:5, selected:5, healthy:3, issues:2, issueLabels:['Hradec záloha','Regionální']});
assert.deepEqual(plain(prefs.summarizeSources(catalog, {disabledSources:['mostek','unknown'], disabledPlaces:['Trutnov']})),
  {available:5, selected:3, healthy:1, issues:2, issueLabels:['Hradec záloha','Regionální']});
assert.deepEqual(plain(prefs.summarizeSources(catalog, {disabledSources:['hk-fallback'], disabledPlaces:['Hradec Králové']})),
  {available:5, selected:3, healthy:2, issues:1, issueLabels:['Regionální']});
assert.deepEqual(plain(prefs.summarizeSources(catalog, {disabledSources:['mostek','hk-ok'], disabledPlaces:['Hradec Králové','Trutnov']})),
  {available:5, selected:1, healthy:0, issues:1, issueLabels:['Regionální']});
assert.deepEqual(plain(prefs.summarizeSources(catalog, {disabledSources:catalog.map(source=>source.name), disabledPlaces:[]})),
  {available:5, selected:0, healthy:0, issues:0, issueLabels:[]});
assert.deepEqual(plain(prefs.summarizeSources([], all)),
  {available:0, selected:0, healthy:0, issues:0, issueLabels:[]});

values.set('unrelated-setting', 'preserve');
assert.equal(prefs.save(selected), true);
assert.deepEqual(plain(prefs.read()), selected);
assert.equal(prefs.save(all), true);
assert.equal(values.get('unrelated-setting'), 'preserve');
assert.deepEqual(plain(prefs.read()), all);

values.set(prefs.KEY, JSON.stringify({disabledSources:['direct'],disabledPlaces:['Trutnov']}));
assert.deepEqual(plain(prefs.read()), {disabledSources:['direct'],disabledPlaces:['Trutnov']});

Object.defineProperty(sandbox, 'localStorage', {configurable:true, get(){throw new Error('blocked storage');}});
assert.deepEqual(plain(prefs.read()), defaults);
assert.equal(prefs.save(selected), false);
Object.defineProperty(sandbox, 'localStorage', {value:{getItem:()=>null,setItem(){throw new Error('quota');}},configurable:true});
assert.equal(prefs.save(selected), false);
console.log('Preference contract passed: defaults, malformed storage, provenance, city gates, persistence and storage failures.');
