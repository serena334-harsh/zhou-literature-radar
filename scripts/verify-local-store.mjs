import assert from 'node:assert/strict';
import {seed} from '../src/data.ts';
import {compose,localChanges} from '../src/local-store.ts';
const publicData=structuredClone(seed),personal=structuredClone(seed);
personal.reviews=[{paperId:seed.papers[0].id,status:'精读中',note:'private-local-note',verdict:'',excludedReason:''}];personal.topics[0].privateAbstract='private-local-abstract';
const local=localChanges(publicData,personal,1);assert.equal(local.papers.length,0);assert.equal(local.topics.length,1);assert.equal(local.revision,1);
const remote=structuredClone(publicData);remote.papers[0].version='v2';const merged=compose(remote,local);assert.equal(merged.papers[0].version,'v2');assert.equal(merged.reviews[0].note,'private-local-note');assert.equal(merged.topics[0].privateAbstract,'private-local-abstract');assert.ok(!JSON.stringify(publicData).includes('private-local'));
console.log('Verified: local notes stay local and survive public-feed refresh without freezing public paper versions.');
