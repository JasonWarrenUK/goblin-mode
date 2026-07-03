# Stud worked example (end to end)

Agent-reference material shared by the stud skills. A full three-function feature studded across real files: shapes declared once, studs returning fake data, `should` bullets, seams, scaffold banners, and the run that proves the plumbing. Language is Python for the example; use the target language's own comment syntax (see `conventions.md`).

Feature: **ingest a webhook event and persist it**, wired into an existing `handlers.py` dispatch.

## The shapes, declared once (top of `events/models.py`)

```python
# &&&& new (scaffold)
# ServerEvent: the raw inbound shape from the webhook
#   { "id": str, "workshop": str, "start": iso8601, "end": iso8601 }
# StoredEvent: what we persist and return
#   { "id": str, "workshop_id": int, "start": datetime, "end": datetime }
```

Reference these two names everywhere below instead of re-describing the fields per function; that stops the input/output contracts drifting as the studs multiply.

## Stud 1: pure leaf (new file `events/transform.py`)

```python
# &&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&
# new chunk, scaffold, remove on implementation
# &&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&
def to_stored(ev):
    # Normalise a ServerEvent into a StoredEvent.
    # in: ServerEvent   out: StoredEvent
    # should parse ISO timestamps into datetime
    # should resolve workshop name to workshop_id via get_or_create_workshop
    # should raise on a missing id
    return {                              # fake, plausible shape
        "id": "evt_123",
        "workshop_id": 7,
        "start": "2026-01-01T09:00:00",   # stand-in for a datetime
        "end": "2026-01-01T17:00:00",
    }
# &&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&
```

## Stud 2: I/O (new file `events/store.py`)

```python
# &&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&
# new chunk, scaffold, remove on implementation
# &&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&
def upsert_event(conn, ev):
    # INSERT a new event, or UPDATE times if its id already exists.
    # in: StoredEvent   out: None
    # SEAM: workshop resolved via get_or_create_workshop
    # SCHEMA CHANGE: adds an events table
    # should INSERT for a new id
    # should UPDATE times when the id exists and they changed
    # should no-op when nothing changed
    print(f"[stud] upsert_event {ev['id']}")   # log so the skeleton shows the flow
    return None                                # fake
# &&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&
```

## Stud 3: the wiring (edit to existing `handlers.py`)

```python
def dispatch(request):
    # ... existing routing ...
    # !!!! edit (scaffold)
    if request.path == "/webhook/event":
        # HOOKS INTO: existing dispatch(); new branch for event webhooks
        # should transform then upsert, returning 200 on success
        stored = to_stored(request.json)   # HOOKS INTO: Stud 1
        upsert_event(conn, stored)         # HOOKS INTO: Stud 2
        print("[stud] handled /webhook/event")
        return 200
```

## The run (proves the plumbing)

Drive the entry point on fake data and watch the flow fire:

```
$ python -c "import handlers; handlers.dispatch(fake_request)"
[stud] upsert_event evt_123
[stud] handled /webhook/event
```

Two log lines in the right order: the skeleton walks. Nothing real happened (the store is a `print`, the transform returns a canned dict), but the calls, wiring, and return path are proven before a line of real logic exists.

## What the reviewer sees

- **Shapes** declared once, referenced by both studs.
- **Three studs** in their real files, each returning plausible fake data, never `None`-as-a-gap.
- **`should` bullets** ready to become Stage-2 tests.
- **Seams** flagged: one `SEAM:`, one `SCHEMA CHANGE:`, two `HOOKS INTO:`.
- **Banners** making the new-vs-edited split scannable, all removable by searching `&&&&`/`!!!!`.

Fill order from here (see `conventions.md`): `to_stored` first (pure leaf), then `upsert_event` (I/O), then the handler branch (orchestration).
