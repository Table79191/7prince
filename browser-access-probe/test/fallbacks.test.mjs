import test from 'node:test';
import assert from 'node:assert/strict';
import { buildPublicFallbacks, isBlockedClassification } from '../src/fallbacks.mjs';

test('builds public mirrors for namu.wiki paths', () => {
  const list = buildPublicFallbacks('https://namu.wiki/w/%EC%9D%B4%EC%9E%AC%EB%AA%85%20%ED%94%BC%EC%8A%B5');
  assert.deepEqual(list.map((u) => u.hostname), ['d.namu.moe', 'www.namu.moe', 'm.namu.moe']);
  assert.ok(list.every((u) => u.pathname.includes('%EC%9D%B4%EC%9E%AC%EB%AA%85')));
});

test('does not invent mirrors for unrelated domains', () => {
  assert.deepEqual(buildPublicFallbacks('https://example.com/x'), []);
});

test('recognizes blocked classifications', () => {
  assert.equal(isBlockedClassification('access-blocked'), true);
  assert.equal(isBlockedClassification('challenge-detected'), true);
  assert.equal(isBlockedClassification('navigation-failed'), true);
  assert.equal(isBlockedClassification('reachable'), false);
});
