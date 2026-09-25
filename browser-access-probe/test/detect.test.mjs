import test from 'node:test';
import assert from 'node:assert/strict';
import { classifyResponse, validateTarget } from '../src/detect.mjs';

test('accepts public http/https URL', () => {
  assert.equal(validateTarget('https://example.com/a').hostname, 'example.com');
});

test('rejects non-http schemes', () => {
  assert.throws(() => validateTarget('file:///etc/passwd'), /Only http/);
});

test('rejects localhost targets', () => {
  assert.throws(() => validateTarget('http://127.0.0.1:8080'), /Local\/private/);
  assert.throws(() => validateTarget('http://localhost:3000'), /Local\/private/);
});

test('rejects private IP literals', () => {
  assert.throws(() => validateTarget('http://10.0.0.4'), /Local\/private/);
  assert.throws(() => validateTarget('http://192.168.1.10'), /Local\/private/);
  assert.throws(() => validateTarget('http://172.20.0.1'), /Local\/private/);
  assert.throws(() => validateTarget('http://[::1]/'), /Local\/private/);
});

test('classifies 403 as access-blocked', () => {
  const result = classifyResponse({ status: 403, title: 'Forbidden', bodyText: '' });
  assert.equal(result.classification, 'access-blocked');
  assert.ok(result.signals.includes('http:403'));
});

test('detects browser challenge text', () => {
  const result = classifyResponse({ status: 200, title: 'Just a moment...', bodyText: 'Checking your browser before accessing the site.' });
  assert.equal(result.classification, 'challenge-detected');
});

test('classifies 429 as rate-limited', () => {
  const result = classifyResponse({ status: 429, title: '', bodyText: '' });
  assert.equal(result.classification, 'rate-limited');
});
