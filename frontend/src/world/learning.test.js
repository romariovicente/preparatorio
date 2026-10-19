import test from 'node:test';import assert from 'node:assert/strict';
import {grade,loadReadings,saveReadings} from './learning.js';
test('lesson assessment rejects absent, wrong and invalid choices',()=>{const lesson={quiz:{answer:1}};assert.equal(grade(lesson,1),true);for(const choice of [0,2,null,'1',undefined])assert.equal(grade(lesson,choice),false);assert.equal(grade({},1),false);});
test('reading progress filters unknown IDs and handles blocked storage',()=>{const denied={getItem(){throw Error();},setItem(){throw Error();}};assert.deepEqual(loadReadings(denied,[]),[]);assert.equal(saveReadings(denied,['page-7']),false);assert.deepEqual(loadReadings({getItem:()=>'{"read":["page-7","page-7","unknown"]}'},['page-7']),['page-7']);});
