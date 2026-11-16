#!/usr/bin/env bash
# End-to-end test for the Real Ohio draft system. Run from ~/workspace/real-ohio.
set -u
cd ~/workspace/real-ohio
fail() { echo "FAIL: $*"; kill $SERVER_PID 2>/dev/null; exit 1; }
pass() { echo "ok: $*"; }

python3 build.py | grep -q "1 article" || fail "build should show 1 published article"
grep -q "Hartman" index.html || fail "published article missing from index.html"
pass "build shows only the published article"

bun scripts/users.mjs create testeditor --password 'TestPass123' | grep -q Created || fail "CLI create"
bun scripts/users.mjs list | grep -q testeditor || fail "CLI list"
bun scripts/users.mjs create testeditor --password 'TestPass123' 2>&1 | grep -q "already exists" || fail "CLI duplicate create should fail"
pass "CLI create/list/duplicate-guard"

PORT=3016 bun run server.mjs > /tmp/realohio-test-server.log 2>&1 &
SERVER_PID=$!
sleep 2
kill -0 $SERVER_PID 2>/dev/null || { cat /tmp/realohio-test-server.log; fail "server did not start"; }

# Masthead UI lives at /masthead (not /admin) and the old path is gone
code=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:3016/masthead)
[ "$code" = "200" ] || fail "/masthead should be 200, got $code"
curl -s http://127.0.0.1:3016/masthead | grep -q "Real Ohio — Masthead" || fail "/masthead page title"
code=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:3016/admin)
[ "$code" = "404" ] || fail "old /admin should be 404, got $code"
pass "masthead UI at /masthead, old /admin gone"

# Unauthenticated -> 401
code=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:3016/api/me)
[ "$code" = "401" ] || fail "unauthenticated /api/me should be 401, got $code"
pass "unauthenticated request rejected"

# Wrong password -> 401
code=$(curl -s -o /dev/null -w "%{http_code}" -X POST http://127.0.0.1:3016/api/login -H 'content-type: application/json' -d '{"username":"testeditor","password":"wrongpass"}')
[ "$code" = "401" ] || fail "wrong password should be 401, got $code"
pass "wrong password rejected"

# Login
curl -s -c /tmp/realohio-cookies.txt -X POST http://127.0.0.1:3016/api/login -H 'content-type: application/json' -d '{"username":"testeditor","password":"TestPass123"}' | grep -q testeditor || fail "login"
pass "login works"

# List: 1 published article
curl -s -b /tmp/realohio-cookies.txt http://127.0.0.1:3016/api/articles | grep -q "faa-ground-stop" || fail "article list"
pass "article list works"

# Edit (GET by slug) must work for the real articles, whose files are
# date-prefixed on disk (2026-11-12-microsoft-365-outage.json) while the
# slug is just "microsoft-365-outage". This is the bug that broke the
# Masthead Edit button live on Nov 15, 2026 (GET returned 404).
curl -s -b /tmp/realohio-cookies.txt http://127.0.0.1:3016/api/articles/microsoft-365-outage | grep -q "Dublin Family" || fail "GET by slug for a date-prefixed article (Edit)"
pass "edit opens a real date-prefixed article by slug"

# Create a draft — it must NOT appear on the public site
curl -s -b /tmp/realohio-cookies.txt -X POST http://127.0.0.1:3016/api/articles -H 'content-type: application/json' -d '{"slug":"test-draft-ohio","date":"2026-11-15","headline":"TEST DRAFT — do not publish","dek":"test","ohio_town":"Testville, Ohio","real_event_date":"2026-11-15","real_summary":"Real paragraph one.","ohio_story":"Ohio paragraph one.","source_name":"Associated Press","source_url":"https://example.com"}' | grep -q '"status":"draft"' || fail "new article should be draft"
grep -q "TEST DRAFT" index.html && fail "draft leaked into public index.html"
pass "new article starts as draft and stays off the public site"

# Edit the draft
curl -s -b /tmp/realohio-cookies.txt -X PUT http://127.0.0.1:3016/api/articles/test-draft-ohio -H 'content-type: application/json' -d '{"headline":"TEST DRAFT — edited headline"}' | grep -q "edited headline" || fail "edit draft"
pass "draft edit works"

# Publish — it must now appear, WITHOUT changing the draft file.
# GitHub stores drafts only: publish state lives in data/published.json
# (popcorn-local, gitignored) and the draft file stays a draft.
curl -s -b /tmp/realohio-cookies.txt -X POST http://127.0.0.1:3016/api/articles/test-draft-ohio/publish | grep -q '"status":"published"' || fail "publish"
grep -q "TEST DRAFT" index.html || fail "published article missing from index.html"
grep -q '"status": "draft"' articles/2026-11-15-test-draft-ohio.json || fail "publish must leave the draft file as draft"
python3 -c "import json; s=json.load(open('data/published.json')); assert s['test-draft-ohio']['published'] is True" || fail "publish must record state in data/published.json"
pass "publish puts it on the public site and leaves the draft file alone"

# Unpublish — it must disappear again, draft file still untouched
curl -s -b /tmp/realohio-cookies.txt -X POST http://127.0.0.1:3016/api/articles/test-draft-ohio/unpublish | grep -q '"status":"draft"' || fail "unpublish"
grep -q "TEST DRAFT" index.html && fail "unpublished article still on public site"
grep -q '"status": "draft"' articles/2026-11-15-test-draft-ohio.json || fail "unpublish must leave the draft file as draft"
pass "unpublish pulls it back off the public site and leaves the draft file alone"

# Delete the test draft, rebuild, verify clean state
curl -s -b /tmp/realohio-cookies.txt -X DELETE http://127.0.0.1:3016/api/articles/test-draft-ohio | grep -q '"ok":true' || fail "delete draft"
[ -f articles/2026-11-15-test-draft-ohio.json ] && fail "draft file still exists"
python3 build.py | grep -q "1 article" || fail "final build should show 1 article"
pass "delete works, public site back to 1 article"

# Publish all — two complete drafts publish at once, one incomplete
# draft is skipped, and no draft file is changed.
for s in test-all-one test-all-two; do
  curl -s -b /tmp/realohio-cookies.txt -X POST http://127.0.0.1:3016/api/articles -H 'content-type: application/json' -d "{\"slug\":\"$s\",\"date\":\"2026-11-15\",\"headline\":\"TEST ALL — $s\",\"dek\":\"test\",\"ohio_town\":\"Testville, Ohio\",\"real_event_date\":\"2026-11-15\",\"real_summary\":\"Real paragraph one.\",\"ohio_story\":\"Ohio paragraph one.\",\"source_name\":\"Associated Press\",\"source_url\":\"https://example.com\"}" | grep -q '"status":"draft"' || fail "create $s"
done
curl -s -b /tmp/realohio-cookies.txt -X POST http://127.0.0.1:3016/api/articles -H 'content-type: application/json' -d '{"slug":"test-all-empty","date":"2026-11-15","headline":"TEST ALL — empty","dek":"test","ohio_town":"Testville, Ohio","real_event_date":"2026-11-15","source_name":"Associated Press","source_url":"https://example.com"}' | grep -q '"status":"draft"' || fail "create test-all-empty"
RESP=$(curl -s -b /tmp/realohio-cookies.txt -X POST http://127.0.0.1:3016/api/articles/publish-all)
echo "$RESP" | grep -q "test-all-one" || fail "publish-all should publish test-all-one"
echo "$RESP" | grep -q "test-all-two" || fail "publish-all should publish test-all-two"
echo "$RESP" | grep -q "test-all-empty" || fail "publish-all should report the skipped draft"
grep -q "TEST ALL — test-all-one" index.html || fail "publish-all article one missing from index.html"
grep -q "TEST ALL — test-all-two" index.html || fail "publish-all article two missing from index.html"
grep -q "TEST ALL — empty" index.html && fail "incomplete draft must not be published by publish-all"
grep -q '"status": "draft"' articles/2026-11-15-test-all-one.json || fail "publish-all must leave draft files as draft"
# Publish-all publishes EVERY complete draft, so the count is the FAA
# article + all 26 retrospective drafts + the 2 test drafts. Compute it
# from the files + published.json instead of hardcoding it.
EXPECTED=$(python3 -c "
import json, glob
arts = [json.load(open(f)) for f in glob.glob('articles/*.json')]
try: o = json.load(open('data/published.json'))
except FileNotFoundError: o = {}
n = 0
for a in arts:
    e = o.get(a['slug'])
    pub = e['published'] if isinstance(e, dict) and isinstance(e.get('published'), bool) else a.get('status') == 'published'
    n += bool(pub)
print(n)
")
python3 build.py | grep -q "$EXPECTED article" || fail "build should show $EXPECTED published articles after publish-all"
pass "publish all publishes complete drafts, skips incomplete ones, leaves draft files alone"
for s in test-all-one test-all-two test-all-empty; do
  curl -s -b /tmp/realohio-cookies.txt -X DELETE http://127.0.0.1:3016/api/articles/$s | grep -q '"ok":true' || fail "delete $s"
done
grep -rq "TEST ALL" index.html page*.html 2>/dev/null && fail "test drafts still on the public site after cleanup"

kill $SERVER_PID
bun scripts/users.mjs delete testeditor | grep -q Deleted || fail "CLI delete"
bun scripts/users.mjs list | grep -q "No admin users" || fail "user list should be empty after delete"
rm -f /tmp/realohio-cookies.txt /tmp/realohio-test-server.log data/published.json
# Removing data/published.json restores the pre-test state (only the FAA
# article published via its file status).
python3 build.py | grep -q "1 article" || fail "final build should show 1 article after cleanup"
echo "ALL DRAFT-SYSTEM TESTS PASSED"
