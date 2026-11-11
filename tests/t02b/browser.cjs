/* Real browser acceptance. No fixtures are created through the SDK or network mocks. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {launch, sha} = require('../t02a/browser-lib.cjs');

const ROOT = path.resolve(__dirname, '../..');
const EVIDENCE = path.join(ROOT, 'infra/evidence/t02b');
const BASE = 'http://127.0.0.1:18080';
const API = '/data-entry/api';
const oldLedger = JSON.parse(fs.readFileSync(path.join(ROOT, 'infra/evidence/t02a/ledger.json')));
const oldSmoke = JSON.parse(fs.readFileSync(path.join(EVIDENCE, 'inventory-before.json'))).tasks.d13dc5bcdbc248f0bb80509eb66b9b36;
const contracts = JSON.parse(fs.readFileSync(path.join(__dirname, '../c3b/readonly-contracts.json')));
const nativeReads = new Set(contracts.allowed.map(item => item.endpoint));
const mode = process.argv[2];
const label = process.argv[3];
assert(['preflight', 'full', 'resume', 'regression', 'rollback', 'restored'].includes(mode));
assert(/^[a-z0-9-]+$/.test(label));
const state = {mode, label, steps: [], network: [], blocked: [], errors: []};

const rows = Array.from({length: 7}, (_, index) => ({
  id: 't02b-browser-' + index,
  source_id: 't02b-source-' + Math.floor(index / 2),
  messages: [
    {role: 'user', content: '合成浏览器验收问题 ' + index},
    {role: 'assistant', content: '合成浏览器验收回答 ' + index},
  ],
}));
rows.push({...rows[1], id: 't02b-browser-duplicate'});
const valid = Buffer.from(rows.map(row => JSON.stringify(row)).join('\n') + '\n');
const invalidJson = Buffer.from('{broken\n');
const invalidFields = Buffer.from('{"messages":"wrong"}\n');
const uploadHashes = new Set([valid, invalidJson, invalidFields].map(sha));
const allowedDatasetIds = new Set([oldLedger.output_dataset_id]);
let activeRequest;
let stage;
const responseFor = (page, endpoint) => page.waitForResponse(response => new URL(response.url()).pathname === API + endpoint);
const visible = (page, text) => page.getByText(text, {exact: true}).filter({visible: true});
const save = () => fs.writeFileSync(path.join(EVIDENCE, label + '-browser.json'), JSON.stringify(state, null, 2) + '\n');

async function browserTest() {
  const browser = await launch();
  const context = await browser.newContext({viewport: {width: 1440, height: 1030}, acceptDownloads: true});
  const page = await context.newPage();
  page.setDefaultTimeout(15000);
  await context.route('**/*', async route => {
    const request = route.request();
    const url = new URL(request.url());
    const method = request.method();
    const endpoint = url.pathname.split('/').pop();
    let reason;
    if (url.origin !== BASE) {
      reason = 'third-party';
    } else if (url.pathname.startsWith('/api/') && (!nativeReads.has(endpoint) || endpoint === 'events.debug_images')) {
      reason = contracts.blocked[endpoint] || 'not on native read allowlist';
    } else if (url.pathname.startsWith(API + '/')) {
      if (method === 'GET') {
        if (!['bootstrap', 'catalog'].includes(endpoint) && !/^\/data-entry\/api\/requests\/[a-f0-9-]{36}$/.test(url.pathname)) {
          reason = 'unexpected adapter read';
        }
      } else if (method === 'POST' && ['full', 'resume'].includes(mode)) {
        const body = request.postDataJSON();
        if (endpoint === 'upload' && stage === 'upload-validation') {
          if (!uploadHashes.has(sha(Buffer.from(body.content_base64, 'base64')))) {
            reason = 'unexpected upload content';
          }
        } else if (endpoint === 'upload' && ['upload', 'same-request-retry'].includes(stage)) {
          if (sha(Buffer.from(body.content_base64, 'base64')) !== sha(valid) || !body.synthetic_fixture) {
            reason = 'unexpected fixture';
          }
        } else if (endpoint === 'submit' && ['submit', 'same-request-retry'].includes(stage)) {
          if (body.request_id !== activeRequest || body.seed !== 73 || body.validation_fraction !== 0.34) {
            reason = 'unexpected submit target or parameters';
          }
        } else if (!['select', 'archive'].includes(endpoint) || !allowedDatasetIds.has(body.dataset_id)) {
          reason = 'unexpected adapter mutation';
        }
      } else {
        reason = 'adapter write outside acceptance flow';
      }
    } else if (!['GET', 'HEAD'].includes(method) && !url.pathname.startsWith('/api/')) {
      reason = 'unexpected write';
    }
    if (reason) {
      state.blocked.push({stage, method, path: url.origin + url.pathname, reason});
      return route.abort('blockedbyclient');
    }
    return route.continue();
  });
  context.on('response', response => {
    const url = new URL(response.url());
    if (url.pathname.startsWith('/api/') || url.pathname.startsWith(API + '/') || url.pathname.startsWith('/files/') || response.status() >= 400) {
      state.network.push({stage, method: response.request().method(), path: url.pathname, status: response.status()});
    }
  });
  page.on('pageerror', error => state.errors.push({stage, name: error.name, message: error.message}));
  const step = async (name, action) => {
    stage = name;
    try {
      await action();
      await page.screenshot({path: path.join(EVIDENCE, label + '-' + name + '.png')});
      state.steps.push({name, pass: true});
    } catch (error) {
      state.steps.push({name, pass: false, error: String(error)});
      await page.screenshot({path: path.join(EVIDENCE, label + '-' + name + '-failed.png')}).catch(() => {});
      throw error;
    } finally {
      save();
    }
  };
  const browserFetch = (endpoint, body) => page.evaluate(async ([prefix, endpoint, body]) => {
    const response = await fetch(prefix + endpoint, body ? {
      method: 'POST', headers: {'Content-Type': 'application/json', 'X-TieSheAI-Request': '1'}, body: JSON.stringify(body),
    } : {});
    return {status: response.status, body: await response.json()};
  }, [API, endpoint, body]);
  const fileInput = page.getByLabel('JSONL 文件');
  const uploadButton = page.getByRole('button', {name: '上传并登记 Dataset'});
  const submitButton = page.getByRole('button', {name: '提交 CPU 处理'});
  const dataCard = id => page.locator('article[data-dataset-id="' + id + '"]');
  const changeFile = (name, buffer) => fileInput.setInputFiles({name, mimeType: 'application/jsonl', buffer});
  const awaitState = text => page.getByText(text, {exact: true}).waitFor();
  try {
    if (['preflight', 'full'].includes(mode)) {
      await step('anonymous-rejected', async () => {
        const response = await page.goto(BASE + API + '/bootstrap');
        assert.equal(response.status(), 401);
      });
    }
    await step('login', async () => {
      await page.goto(BASE);
      await page.locator('input[formcontrolname="name"]').fill('TieSheAI T01-B CPU');
      await page.getByRole('option', {name: 'TieSheAI T01-B CPU', exact: true}).click();
      await page.getByRole('button', {name: /start|sign in|login|connect/i}).click();
      await page.waitForURL(url => !url.pathname.includes('login'));
    });
    if (['rollback', 'regression'].includes(mode)) {
      await step('legacy-artifact', async () => {
        if (mode === 'rollback') {
          assert.equal(await page.getByRole('link', {name: '数据准备', exact: true}).count(), 0);
        }
        await page.goto(BASE + '/projects/' + oldSmoke.project + '/tasks/' + oldSmoke.id + '/output/artifacts');
        await visible(page, 'cpu-smoke-json').click();
        const [download] = await Promise.all([
          page.waitForEvent('download'),
          page.locator('sm-labeled-row[data-id="filePathId"] button').first().click(),
        ]);
        const bytes = fs.readFileSync(await download.path());
        const expected = oldSmoke.execution.artifacts.find(item => item.key === 'cpu-smoke-json');
        assert.equal(sha(bytes), expected.hash);
        assert.equal(bytes.length, expected.content_size);
        await download.saveAs(path.join(EVIDENCE, label + '-legacy-artifact.json'));
        state.legacyDownload = {sha256: sha(bytes), bytes: bytes.length};
      });
    } else {
      await step('data-entry', async () => {
        await page.getByRole('link', {name: '数据准备', exact: true}).click();
        await page.getByRole('heading', {name: '数据准备', exact: true}).waitFor();
        await dataCard(oldLedger.output_dataset_id).waitFor({timeout: 30000});
        const response = await browserFetch('/bootstrap');
        assert.equal(response.status, 200);
        state.initial = {requests: response.body.requests.map(item => item.request_id), selected: response.body.selected};
        if (mode === 'full') {
          assert.equal(state.initial.requests.length, 0, 'Existing requests require resume mode');
        }
      });

      if (mode === 'full') {
        await step('upload-validation', async () => {
          for (const [name, buffer, message] of [
            ['empty.jsonl', Buffer.alloc(0), '文件为空'],
            ['oversize.jsonl', Buffer.alloc(1048577), '文件超过 1 MiB 限制'],
            ['invalid-json.jsonl', invalidJson, '第 1 行不符合 conversation-v1 格式'],
            ['invalid-fields.jsonl', invalidFields, '第 1 行不符合 conversation-v1 格式'],
          ]) {
            await changeFile(name, buffer);
            await uploadButton.click();
            await visible(page, message).waitFor();
          }
          assert.equal((await browserFetch('/bootstrap')).body.requests.length, 0);
        });
        await step('upload', async () => {
          await changeFile('t02b-browser-conversations.jsonl', valid);
          await page.getByLabel('合成测试数据').check();
          const [response] = await Promise.all([responseFor(page, '/upload'), uploadButton.click()]);
          assert.equal(response.status(), 200, await response.text());
          state.upload = await response.json();
          activeRequest = state.upload.request_id;
          assert.equal(state.upload.input_sha256, sha(valid));
          assert(state.upload.input_dataset_id);
          fs.writeFileSync(path.join(EVIDENCE, 'browser-input.jsonl'), valid);
          await awaitState('状态 uploaded');
        });
        await step('reload-after-upload', async () => {
          await page.reload();
          await awaitState('状态 uploaded');
          assert.equal(await page.locator('#active-request').inputValue(), activeRequest);
          await page.getByLabel('随机种子').fill('42.5');
          await submitButton.click();
          await visible(page, 'seed 必须为 32 位整数').waitFor();
          await page.getByLabel('随机种子').fill('73');
          await page.getByLabel('验证组比例').fill('1');
          await submitButton.click();
          await visible(page, '验证组比例必须大于 0 且小于 1').waitFor();
        });
      } else if (mode === 'resume') {
        const current = (await browserFetch('/bootstrap')).body.requests[0];
        assert(current, 'No browser-created request to resume');
        activeRequest = current.request_id;
        state.upload = current;
      }
      if (['full', 'resume'].includes(mode)) {
        if (!state.upload.submitted) {
          await step('submit', async () => {
            await page.getByLabel('随机种子').fill('73');
            await page.getByLabel('验证组比例').fill('0.34');
            const [response] = await Promise.all([responseFor(page, '/submit'), submitButton.click()]);
            assert.equal(response.status(), 200, await response.text());
            state.submission = await response.json();
            assert(state.submission.processing_task_id);
          });
        } else {
          state.submission = state.upload;
        }
        await step('same-request-retry', async () => {
          const upload = {request_id: activeRequest, filename: 't02b-browser-conversations.jsonl',
                          synthetic_fixture: true, content_base64: valid.toString('base64')};
          const submit = {request_id: activeRequest, seed: 73, validation_fraction: 0.34};
          const results = await Promise.all([
            browserFetch('/upload', upload), browserFetch('/upload', upload),
            browserFetch('/submit', submit), browserFetch('/submit', submit),
          ]);
          for (const result of results) {
            assert.equal(result.status, 200, JSON.stringify(result.body));
            assert.equal(result.body.input_dataset_id, state.upload.input_dataset_id);
            assert.equal(result.body.processing_task_id, state.submission.processing_task_id);
          }
          state.retries = results.map(result => ({status: result.status, request_id: result.body.request_id,
                                                 task_id: result.body.processing_task_id}));
          await page.reload();
          await page.locator('#active-request').waitFor();
          assert.equal(await page.locator('#active-request').inputValue(), activeRequest);
        });
        await step('completed', async () => {
          await page.getByText('状态 completed', {exact: true}).waitFor({timeout: 150000});
          const response = await browserFetch('/requests/' + activeRequest);
          assert.equal(response.status, 200, JSON.stringify(response.body));
          state.completed = response.body;
          assert.equal(state.completed.status, 'completed');
          assert(state.completed.output_dataset_id);
          const stats = state.completed.statistics;
          assert.equal(stats.unique_records, 7);
          assert.equal(stats.duplicates_removed, 1);
          assert.equal(stats.train_records + stats.validation_records, 7);
          allowedDatasetIds.add(state.completed.output_dataset_id);
          await page.getByText(/唯一 7 · 重复 1/).waitFor();
        });
        await step('select-and-download', async () => {
          const id = state.completed.output_dataset_id;
          await dataCard(id).waitFor({timeout: 30000});
          for (const target of [oldLedger.output_dataset_id, id]) {
            const [response] = await Promise.all([
              responseFor(page, '/select'),
              dataCard(target).getByRole('button', {name: '选择 Dataset'}).click(),
            ]);
            assert.equal(response.status(), 200, await response.text());
            const selected = (await response.json()).selected;
            assert.equal(selected.id, target);
            await page.locator('[data-id=selected-dataset]').getByText(target, {exact: true}).waitFor();
            (state.selections ||= []).push(selected);
          }
          const [download] = await Promise.all([
            page.waitForEvent('download'),
            dataCard(id).getByRole('button', {name: '下载结果'}).click(),
          ]);
          const file = label + '-output.zip';
          await download.saveAs(path.join(EVIDENCE, file));
          const bytes = fs.readFileSync(path.join(EVIDENCE, file));
          state.download = {file, bytes: bytes.length, sha256: sha(bytes)};
        });
        await step('reload-and-native-log', async () => {
          await page.reload();
          const id = state.completed.output_dataset_id;
          await page.locator('[data-id=selected-dataset]').getByText(id, {exact: true}).waitFor();
          await page.getByRole('link', {name: '任务日志', exact: true}).click();
          await page.getByText('T02B_PREPARATION_OK', {exact: false}).filter({visible: true}).waitFor({timeout: 30000});
          assert(page.url().includes(state.completed.processing_task_id));
        });
      } else if (mode === 'restored') {
        await step('restored-selection', async () => {
          assert(state.initial.selected?.id && state.initial.requests.length === 1);
          await page.locator('[data-id=selected-dataset]').getByText(state.initial.selected.id, {exact: true}).waitFor();
          await awaitState('状态 completed');
        });
        await step('native-dataset-and-artifacts', async () => {
          const id = state.initial.selected.id;
          await dataCard(id).getByRole('link', {name: '查看 Dataset', exact: true}).click();
          await page.waitForURL(url => url.pathname.includes('/datasets/simple/') && url.pathname.includes(id));
          await page.locator('sm-dataset-version-step').filter({hasText: 'v1.0.0'}).waitFor();
          await page.goBack();
          await page.getByRole('link', {name: '任务产物', exact: true}).click();
          await page.getByText('manifest.json', {exact: true}).filter({visible: true}).waitFor();
        });
      }
    }
    const unexpected = state.blocked.filter(item => !['third-party', 'server.report_stats_option', 'users.set_preferences'].some(
      marker => marker === 'third-party' ? item.reason === marker : item.path.endsWith('/' + marker)));
    assert.deepEqual(unexpected, []);
    state.pass = true;
  } catch (error) {
    state.pass = false;
    state.failure = String(error.stack || error);
    process.exitCode = 1;
  } finally {
    save();
    await browser.close();
    console.log(JSON.stringify({pass: state.pass, steps: state.steps, failure: state.failure}, null, 2));
  }
}

void browserTest();
