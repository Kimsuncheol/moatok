#!/usr/bin/env python3
"""Local, at-most-once Open Chat sender. Python 3.9+, macOS Accessibility required."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
import subprocess
import time
import uuid

DB = Path.home() / 'Library/Application Support/Moatok/openchat.sqlite3'


def connect(path=DB):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    db = sqlite3.connect(path)
    path.chmod(0o600)
    db.execute('CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY, room TEXT, message TEXT, due REAL, status TEXT, detail TEXT)')
    return db


def import_jobs(db, payload):
    if payload.get('version') != 1 or not isinstance(payload.get('jobs'), list):
        raise ValueError('Unsupported schedule file')
    rows = []
    for job in payload['jobs']:
        ident = str(uuid.UUID(job['id']))
        room, message = job['room'], job['message']
        if not isinstance(room, str) or not room.strip() or len(room) > 200:
            raise ValueError('Invalid room title')
        if not isinstance(message, str) or not message.strip() or len(message) > 4000:
            raise ValueError('Invalid message')
        due = datetime.fromisoformat(job['due'].replace('Z', '+00:00'))
        if due.tzinfo is None:
            raise ValueError('Schedule needs timezone')
        rows.append((ident, room, message, due.timestamp(), 'pending', ''))
    with db:
        for row in rows:
            existing = db.execute('SELECT room,message,due FROM jobs WHERE id=?', (row[0],)).fetchone()
            if existing and existing != row[1:4]:
                raise ValueError('An existing schedule cannot be changed; cancel it and create a new one')
            db.execute('INSERT OR IGNORE INTO jobs VALUES (?,?,?,?,?,?)', row)


# No search, coordinates or clipboard: require one exact visible window and one empty AXTextArea.
# A UI change fails closed. Return only means the key was issued, not confirmed delivery.
SCRIPT = r'''
on run argv
  set roomTitle to item 1 of argv
  set messageText to item 2 of argv
  tell application "System Events"
    if not (exists process "KakaoTalk") then error "KakaoTalk is not running"
    tell process "KakaoTalk"
      set targets to every window whose name is roomTitle
      if (count of targets) is not 1 then error "Expected one exact room window"
      set targetWindow to item 1 of targets
      if minimized of targetWindow then error "Room is minimized"
      set fields to {}
      repeat with elementRef in entire contents of targetWindow
        if role of elementRef is "AXTextArea" then set end of fields to contents of elementRef
      end repeat
      if (count of fields) is not 1 then error "Cannot uniquely identify composer"
      set composer to item 1 of fields
      if (value of composer as text) is not "" then error "Composer has a draft"
      set frontmost to true
      perform action "AXRaise" of targetWindow
      set focused of composer to true
      set value of composer to messageText
      if (value of composer as text) is not messageText then error "Composer verification failed"
      if not frontmost then error "KakaoTalk lost foreground"
      if name of front window is not roomTitle then error "Room changed"
      if not (focused of composer) then error "Composer lost focus"
      key code 36
    end tell
  end tell
end run
'''


def send(room, message):
    subprocess.run(['osascript', '-e', SCRIPT, room, message], check=True, capture_output=True, timeout=20)


def tick(db, sender=send, now=None):
    now = time.time() if now is None else now
    rows = db.execute("SELECT id,room,message,due FROM jobs WHERE status='pending' AND due<=? ORDER BY due", (now,)).fetchall()
    for ident, room, message, due in rows:
        # Atomic durable claim before any UI I/O; competing helpers and restarts cannot resend.
        with db:
            claimed = db.execute("UPDATE jobs SET status='review_required',detail='Attempt claimed; inspect KakaoTalk before scheduling again' WHERE id=? AND status='pending'", (ident,)).rowcount
        if not claimed:
            continue
        if now - due > 300:
            with db:
                db.execute("UPDATE jobs SET status='missed',detail='Over five minutes late; not sent' WHERE id=?", (ident,))
            continue
        try:
            sender(room, message)
            detail = 'Send key issued; delivery is unconfirmed. Inspect the room. No automatic retry.'
        except Exception:
            detail = 'UI check or send failed. Inspect the room and draft. No automatic retry.'
        with db:
            db.execute('UPDATE jobs SET detail=? WHERE id=?', (detail, ident))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('import').add_argument('file')
    sub.add_parser('list')
    sub.add_parser('cancel').add_argument('id')
    sub.add_parser('confirm').add_argument('id')
    sub.add_parser('run').add_argument('--send', action='store_true', required=True)
    args = parser.parse_args()
    db = connect()
    if args.command == 'import':
        import_jobs(db, json.loads(Path(args.file).read_text()))
        print('Imported. Use list to review; run --send enables sending.')
    elif args.command in ('cancel', 'confirm'):
        with db:
            db.execute('UPDATE jobs SET status=? WHERE id=? AND status=?', ('cancelled' if args.command == 'cancel' else 'confirmed', args.id, 'pending' if args.command == 'cancel' else 'review_required'))
    elif args.command == 'list':
        for row in db.execute('SELECT id,room,due,status,detail FROM jobs ORDER BY due'):
            print(json.dumps(dict(zip(('id', 'room', 'due_epoch', 'status', 'detail'), row)), ensure_ascii=False))
    else:
        print('Sender active. Keep Mac awake and unlocked, and target room windows open. Ctrl-C stops.')
        try:
            while True:
                tick(db)
                time.sleep(5)
        except KeyboardInterrupt:
            pass


if __name__ == '__main__':
    main()
